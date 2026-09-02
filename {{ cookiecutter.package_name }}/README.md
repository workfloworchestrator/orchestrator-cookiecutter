# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

This project was bootstrapped with [`orchestrator-cookiecutter`](https://github.com/workfloworchestrator/orchestrator-cookiecutter):

```shell
uvx orchestrator-cookiecutter
```

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- A PostgreSQL database
{%- if cookiecutter.executor == "Celery" %}
- A Redis instance, used as the Celery broker and result backend
{%- endif %}
{% if cookiecutter.use_docker == "yes" %}
A `docker-compose.yml` is included to run these locally:

```shell
docker compose up -d
```
{% endif %}
## Getting started

Install the dependencies:

```shell
uv sync --all-groups --all-extras
```

Point the app at your database, then initialise the migration environment and create the schema. `main.py` and `wsgi.py` live in the `{{ cookiecutter.project_slug }}` package directory, so run these from there:

```shell
export DATABASE_URI=postgresql+psycopg://nwa:nwa@localhost:5432/{{ cookiecutter.project_slug }}

uv run main.py db init
uv run main.py db upgrade heads
```

Run the API:

```shell
uv run uvicorn --reload --host 127.0.0.1 --port 8080 wsgi:app
```

Visit the [OpenAPI docs](http://127.0.0.1:8080/api/docs) or [ReDoc](http://127.0.0.1:8080/api/redoc) to interact with the API.
{% if cookiecutter.executor == "Celery" %}
## Running with Celery

This project can run workflows and tasks on Celery workers instead of the default threadpool. Both the API and the
worker need to know this, and where to find Redis (used as the Celery broker and result backend):

```shell
export EXECUTOR=celery
export CACHE_URI=redis://localhost:6379/0
```

With those set, run the API as usual (see above), and start a worker listening on the default queues:

```shell
uv run celery -A {{ cookiecutter.project_slug }}.celery_worker worker -E -l INFO -Q new_tasks,resume_tasks,new_workflows,resume_workflows
```

See the [Scaling the Orchestrator](https://workfloworchestrator.org/orchestrator-core/guides/scaling/) guide for more on splitting workers across queues.
{% endif %}
## Running the tests

```shell
uv run pytest
```
