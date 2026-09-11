# Copyright 2026 GÉANT
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

import os
import subprocess
from pathlib import Path

#: We add `VIRTUAL_ENV` to the environment to prevent a UV warning from popping up.
UV_ENV = os.environ | {"VIRTUAL_ENV": "{{ cookiecutter._output_dir }}/{{ cookiecutter.package_name }}/.venv"}


def prune_unused_files() -> None:
    """Delete files that were generated for a wizard choice the user didn't make.

    Cookiecutter has no native way to skip generating a single file based on a variable, so the
    standard pattern is to generate it unconditionally and remove it here.
    """
    if "{{ cookiecutter.executor }}" != "Celery":
        Path("{{ cookiecutter.project_slug }}/celery_worker.py").unlink(missing_ok=True)

    if "{{ cookiecutter.use_docker }}" != "yes":
        Path("docker-compose.yml").unlink(missing_ok=True)


def run_uv_sync() -> None:
    print("\n" * 2, "=" * 10, "     Installing dependencies     ", "=" * 10, "\n" * 2)
    subprocess.run(["uv", "venv"], check=True, env=UV_ENV)
    subprocess.run(["uv", "sync", "--all-groups", "--all-extras"], check=True, env=UV_ENV)


def install_pre_commit() -> None:
    print("\n" * 2, "=" * 10, "      Initialising git repo      ", "=" * 10, "\n" * 2)
    subprocess.run(["git", "init"], check=True)

    print("\n" * 2, "=" * 10, " Installing git pre-commit hooks ", "=" * 10, "\n" * 2)
    subprocess.run(["uv", "run", "pre-commit", "install"], check=True, env=UV_ENV)


def run_db_init() -> None:
    print("\n" * 2, "=" * 10, " Initializing DB migration files ", "=" * 10, "\n" * 2)
    subprocess.run(
        ["uv", "run", "main.py", "db", "init"], cwd="{{ cookiecutter.project_slug }}", check=True, env=UV_ENV
    )


def print_next_steps() -> None:
    print("""
==========  Completed cookiecutter install  ===========

You now have a minimal but functional Orchestrator implementation!

To interact with it, use the following commands:

  # Activate the Python runtime in the generated project
  cd {{ cookiecutter._output_dir }}/{{ cookiecutter.package_name }}
  source .venv/bin/activate

  # Start the API (note: you will need a database setup for the calls to work, see next steps)
  uvicorn --reload --host 127.0.0.1 --port 8080 {{ cookiecutter.project_slug }}.wsgi:app

  # Access the CLI
  python {{ cookiecutter.project_slug }}/main.py --help

============= Next steps =============

1. Setup the database
{%- if cookiecutter.use_docker == "yes" %}

  Start the local docker-compose.yml services (this already creates the database orchestrator-core
  expects by default, so no DATABASE_URI export is needed):

  docker compose up --detach

  Create the schema:

  uv run main.py db upgrade heads

  # Stop the databases and remove their volumes
  docker compose down --volumes
{%- else %}

  Point the app at your own PostgreSQL database, then create the schema:

  export DATABASE_URI=postgresql+psycopg://<user>:<password>@<host>:<port>/<database>
  uv run main.py db upgrade heads

  See https://workfloworchestrator.org/orchestrator-core/getting-started/base/ for more on setting up a database.
{%- endif %}

2. Generate a product

  (some basic instructions here, preferably directing the user to documentation)
""")


if __name__ == "__main__":
    prune_unused_files()
    run_uv_sync()
    install_pre_commit()
    run_db_init()
    print_next_steps()
