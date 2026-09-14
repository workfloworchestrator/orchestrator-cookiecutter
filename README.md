# Workflow Orchestrator Cookiecutter Template

A [Cookiecutter](https://github.com/cookiecutter/cookiecutter) template repository for creating an implementation of
the Workflow Orchestrator.

## What You Get

This cookiecutter template includes the following tools to help you get started to implement your own Workflow
Orchestrator.

- `uv` as package manager
- `ruff` as Python linter and formatter
- `mypy` as type checker
- `pre-commit` hooks wired up to run linting, formatting and type checking
- `pytest` as unit testing framework, with boilerplate code for test cases
- A choice of `Threadpool` or `Celery` as task executor
- A GraphQL API registered alongside the REST API out of the box
- An optional `docker-compose.yml` to run Postgres (and Redis, when using Celery) locally

## Quickstart

[Install `uv`](https://docs.astral.sh/uv/getting-started/installation/) and run:

```shell
uvx orchestrator-cookiecutter
```

This will take you through the generation of a boilerplate project for Workflow Orchestrator.

for development use:

```shell
uv run cookiecutter .
```
