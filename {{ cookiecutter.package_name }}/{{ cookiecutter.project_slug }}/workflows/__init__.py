# Copyright {% now 'local', '%Y' %} {{ cookiecutter.author }}
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Initialisation class that imports all workflows into {{ cookiecutter.project_name }}."""

from orchestrator.core.services.subscriptions import WF_USABLE_MAP, WF_USABLE_WHILE_OUT_OF_SYNC
from orchestrator.core.types import SubscriptionLifecycle  # noqa: F401
from orchestrator.core.workflows import LazyWorkflowInstance  # noqa: F401

WF_USABLE_MAP.update(
    {
        # "workflow_only_for_provisioning_product": [SubscriptionLifecycle.PROVISIONING],
        # "workflow_that_can_always_run": [
        #     SubscriptionLifecycle.INITIAL,
        #     SubscriptionLifecycle.PROVISIONING,
        #     SubscriptionLifecycle.ACTIVE,
        #     SubscriptionLifecycle.TERMINATED,
        # ],
    }
)

WF_USABLE_WHILE_OUT_OF_SYNC.extend(
    [
        # "safe_workflow_for_out_of_sync_product",
    ]
)

# LazyWorkflowInstance("{{ cookiecutter.project_slug }}.workflows.tasks.send_email_notifications", "task_send_email_notifications")
# LazyWorkflowInstance("{{ cookiecutter.project_slug }}.workflows.my_product.create_my_product", "create_my_product")
# LazyWorkflowInstance("{{ cookiecutter.project_slug }}.workflows.my_product.modify_my_product", "modify_my_product")
# LazyWorkflowInstance("{{ cookiecutter.project_slug }}.workflows.my_product.terminate_my_product", "terminate_my_product")
# LazyWorkflowInstance("{{ cookiecutter.project_slug }}.workflows.my_product.migrate_my_product", "migrate_my_product")
# LazyWorkflowInstance("{{ cookiecutter.project_slug }}.workflows.my_product.validate_my_product", "validate_my_product")
