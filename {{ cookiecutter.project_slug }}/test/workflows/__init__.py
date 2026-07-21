# Copyright 2019-2026 SURF, GÉANT.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import difflib
import pprint
from collections.abc import Callable
from copy import deepcopy
from typing import cast

import structlog
from orchestrator.core.db import ProcessTable, WorkflowTable, db
from orchestrator.core.services.input_state import store_input_state
from orchestrator.core.services.processes import StateMerger, create_process
from orchestrator.core.targets import Target
from orchestrator.core.utils.json import json_dumps, json_loads
from orchestrator.core.workflow import Process as WFProcess
from orchestrator.core.workflow import ProcessStat, Step, Success, Workflow, runwf
from orchestrator.core.workflows import ALL_WORKFLOWS, LazyWorkflowInstance
from pydantic_forms.core import post_form
from pydantic_forms.types import State

logger = structlog.get_logger(__name__)


def store_workflow(wf: Workflow, name: str | None = None) -> WorkflowTable:
    is_task = wf.target in [Target.VALIDATE, Target.SYSTEM]
    wf_table = WorkflowTable(name=name or wf.name, target=wf.target, is_task=is_task, description=wf.description)
    db.session.add(wf_table)
    db.session.commit()
    return wf_table


def delete_workflow(wf: WorkflowTable) -> None:
    db.session.delete(wf)
    db.session.commit()


def _raise_exception(state):
    if isinstance(state, Exception):
        raise state
    return state


def assert_success(result):
    assert result.on_failed(_raise_exception).on_waiting(_raise_exception).issuccess(), (
        f"Unexpected process status. Expected Success, but was: {result}"
    )


def assert_waiting(result):
    assert result.on_failed(_raise_exception).iswaiting(), (
        f"Unexpected process status. Expected Waiting, but was: {result}"
    )


def assert_awaiting_callback(result):
    assert result.on_failed(_raise_exception).isawaitingcallback(), (
        f"Unexpected process status. Expected AwaitingCallback, but was: {result}"
    )


def assert_suspended(result):
    assert result.on_failed(_raise_exception).issuspend(), (
        f"Unexpected process status. Expected Suspend, but was: {result}"
    )


def assert_aborted(result):
    assert result.on_failed(_raise_exception).isabort(), f"Unexpected process status. Expected Abort, but was: {result}"


def assert_failed(result):
    assert result.isfailed(), f"Unexpected process status. Expected Failed, but was: {result}"


def assert_complete(result):
    assert result.on_failed(_raise_exception).iscomplete(), (
        f"Unexpected process status. Expected Complete, but was: {result}"
    )


def assert_state(result, expected):
    state = result.unwrap()
    actual = {}
    for key in expected:
        actual[key] = state[key]
    assert expected == actual, f"Invalid state. Expected superset of: {expected}, but was: {actual}"


def assert_state_equal(result: ProcessTable, expected: dict, excluded_keys: list[str] | None = None) -> None:
    """Test state with certain keys excluded from both actual and expected state."""
    if excluded_keys is None:
        excluded_keys = ["process_id", "workflow_target", "workflow_name"]
    state = deepcopy(extract_state(result))
    expected_state = deepcopy(expected)
    for key in excluded_keys:
        if key in state:
            del state[key]
        if key in expected_state:
            del expected_state[key]

    assert state == expected_state, "Unexpected state:\n" + "\n".join(
        difflib.ndiff(pprint.pformat(state).splitlines(), pprint.pformat(expected_state).splitlines())
    )


def assert_assignee(log, expected):
    actual = log[-1][0].assignee
    assert expected == actual, f"Unexpected assignee. Expected {expected}, but was: {actual}"


def assert_step_name(log, expected):
    actual = log[-1][0]
    assert actual.name == expected, f"Unexpected name. Expected {expected}, but was: {actual}"


def extract_state(result):
    return result.unwrap()


def extract_error(result):
    from orchestrator.core.workflow import Process

    assert isinstance(result, Process), f"Expected a Process, but got {result!r} of type {type(result)}"
    assert not isinstance(result.s, Process), "Result contained a Process in a Process, this should not happen"

    return extract_state(result).get("error")


class WorkflowInstanceForTests(LazyWorkflowInstance):
    """Register Test workflows.

    Similar to `LazyWorkflowInstance` but does not require an import during instantiate
    Used for creating test workflows
    """

    package: str
    function: str
    is_callable: bool

    def __init__(self, workflow: Workflow, name: str) -> None:
        super().__init__("orchestrator.test", name)
        self.workflow = workflow
        self.name = name

    def __enter__(self):
        ALL_WORKFLOWS[self.name] = self
        self.workflow_instance = store_workflow(self.workflow, name=self.name)
        return self.workflow_instance

    def __exit__(self, _exc_type, _exc_value, _traceback):
        del ALL_WORKFLOWS[self.name]
        delete_workflow(self.workflow_instance)
        del self.workflow_instance

    def instantiate(self) -> Workflow:
        """Import and instantiate a workflow and return it.

        This can be as simple as merely importing a workflow function. However, if it concerns a workflow generating
        function, that function will be called with or without arguments as specified.

        Returns:
            A workflow function.

        """
        self.workflow.name = self.name
        return self.workflow

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"WorkflowInstanceForTests('{self.workflow}','{self.name}')"


def _store_step(step_log: list[tuple[Step, WFProcess]]) -> Callable[[ProcessStat, Step, WFProcess], WFProcess]:
    def __store_step(_: ProcessStat, step: Step, process: WFProcess) -> WFProcess:
        try:
            process = process.map(lambda s: json_loads(json_dumps(s)))
        except Exception:
            logger.exception("Step state is not valid json", process=process)

        state = process.unwrap()
        state.pop("__step_name_override", None)
        for k in [*state.get("__remove_keys", []), "__remove_keys"]:
            state.pop(k, None)
        if state.pop("__replace_last_state", None):
            step_log[-1] = (step, process)
        else:
            step_log.append((step, process))
        return process

    return __store_step


def _sanitise_input(input_data: State | list[State]) -> list[State]:
    # To be backwards compatible convert single dict to list
    if not isinstance(input_data, list):
        input_data = [input_data]

    # We need a copy here and we want to mimic the actual code that returns a serialized version of the state
    return cast(list[State], json_loads(json_dumps(input_data)))


def run_workflow(
    workflow_key: str, input_data: State | list[State]
) -> tuple[WFProcess, ProcessStat, list[tuple[Step, WFProcess]]]:
    # ATTENTION!! This code needs to be as similar as possible to `server.services.processes.start_process`
    # The main differences are: we use a different step log function, and we don't run in
    # a separate thread. Note: run_predicate evaluation happens inside create_process.
    user_data = _sanitise_input(input_data)
    user = "john.doe"

    pstat = create_process(workflow_key, user_data, user)

    step_log: list[tuple[Step, WFProcess]] = []
    result = runwf(pstat, _store_step(step_log))
    return result, pstat, step_log


def resume_workflow(
    process: ProcessStat, step_log: list[tuple[Step, WFProcess]], input_data: State
) -> tuple[WFProcess, list]:
    # ATTENTION!! This code needs to be as similar as possible to `server.services.processes.resume_process`
    # The main differences are: we use a different step log function, and we don't run in a separate thread
    user_data = _sanitise_input(input_data)

    persistent = list(
        filter(
            lambda p: not (p[1].isfailed() or p[1].issuspend() or p[1].iswaiting() or p[1].isawaitingcallback()),
            step_log,
        )
    )
    nr_of_steps_done = len(persistent)
    remaining_steps = process.workflow.steps[nr_of_steps_done:]

    if step_log and (step_log[-1][1].issuspend() or step_log[-1][1].isawaitingcallback()):
        _, current_state = step_log[-1]
    elif persistent:
        _, current_state = persistent[-1]
    else:
        current_state = Success({})

    user_input = post_form(remaining_steps[0].form, current_state.unwrap(), user_data)
    state = current_state.map(lambda state: StateMerger.merge(deepcopy(state), user_input))
    store_input_state(process.process_id, user_input, "user_input")

    updated_process = process.update(log=remaining_steps, state=state)
    result = runwf(updated_process, _store_step(step_log))
    return result, step_log
