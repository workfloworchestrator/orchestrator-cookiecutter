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

"""The Celery worker entrypoint for {{ cookiecutter.project_name }}, used when EXECUTOR="celery"."""

from celery import Celery
from orchestrator.core import app_settings
from orchestrator.core.db import init_database
from orchestrator.core.services.tasks import initialise_celery

import {{ cookiecutter.project_slug }}.products
import {{ cookiecutter.project_slug }}.workflows  # noqa: F401

init_database(app_settings)

celery = Celery(
    f"{app_settings.SERVICE_NAME}-worker",
    broker=str(app_settings.CACHE_URI.get_secret_value()),
    backend=str(app_settings.CACHE_URI.get_secret_value()),
    include=["orchestrator.core.services.tasks"],
)

initialise_celery(celery)
