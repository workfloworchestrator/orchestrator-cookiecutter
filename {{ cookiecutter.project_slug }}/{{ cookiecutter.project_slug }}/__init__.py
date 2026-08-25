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

"""The main entrypoint for {{ cookiecutter.project_name }}, and the different ways in which it can be run."""

from importlib import metadata
from os import getenv

import typer
from celery import Celery
from orchestrator.core import OrchestratorCore, app_settings
from orchestrator.core.cli.main import app as cli_app
from orchestrator.core.graphql import SCALAR_OVERRIDES
from orchestrator.core.graphql.resolvers.version import VERSIONS
from orchestrator.core.services.tasks import initialise_celery

import {{ cookiecutter.project_slug }}.products
import {{ cookiecutter.project_slug }}.workflows  # noqa: F401

# SCALAR_OVERRIDES.update(LOCAL_SCALAR_OVERRIDES)
VERSIONS.extend(
    [
        f"Custom Orchestrator: {metadata.version('{{ cookiecutter.project_slug }}')}",
    ]
)

def init_app() -> OrchestratorCore:
    """Initialise the {{ cookiecutter.project_name }} app."""
    app = OrchestratorCore(base_settings=app_settings)

    # app.register_authentication(oidc_instance)
    # app.register_authorization(opa_instance)
    # app.register_graphql_authorization(graphql_opa_instance)
    # app.register_graphql(subscription_interface=custom_subscription_interface)

    # app.include_router(custom_api_router, prefix="/api")

    return app


def init_cli_app() -> typer.Typer:
    """Initialise {{ cookiecutter.project_name }} as a CLI application."""
    return cli_app()


__all__ = ["gso_initialise_celery", "init_cli_app", "init_gso_app", "init_sentry"]
