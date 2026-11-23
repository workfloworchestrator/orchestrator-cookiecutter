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

## Dependency updates and the template boundary

Renovate manages the generator root only (`pyproject.toml`/`uv.lock`, the workflows, and the root pin on the
`astral-sh/uv` toolchain), using the shared `renovate-config` presets in `renovate.json`. Root dependencies are
exact runtime pins of the published generator, and the root `uv.lock` uses a three-day `exclude-newer` cutoff
(`[tool.uv]` in `pyproject.toml`) that matches the presets' release age.

The generated project under `{{ cookiecutter.package_name }}/` is **not** covered by automated dependency or
security updates:

- Its `pyproject.toml` contains Jinja directives inside the TOML arrays, so Renovate cannot parse it; version
  bumps there would be guessed, not resolved.
- `renovate.json` therefore ignores it with the literal `ignorePaths` entry `cookiecutter.package_name` (a
  substring match on the template directory name; the braces of a Jinja name are glob characters and would not
  match as written). That entry also applies to custom managers. It also ignores the template's
  `docker-compose.yml`, `.pre-commit-config.yaml` and `.python-version`, which Renovate would otherwise update
  without knowing which executor variant a change belongs to.
- Root vulnerability alerts cover the generator's own dependencies, not the runtime, dev, build, pre-commit and
  Compose dependencies the template ships (the template is in the sdist and force-included in the wheel).

**Manual recurring review.** At least monthly, and after each generator release:

1. Render both executor variants (`Threadpool` and `Celery`), for example
   `uv run cookiecutter . --no-input executor=Celery use_docker=yes -o /tmp/review`.
2. Inspect the rendered `pyproject.toml`, `uv.lock` (generate it with the same three-day cutoff), `.pre-commit-config.yaml`
   and `docker-compose.yml` against open advisories.
3. Record the date, reviewer, rendered variants and findings in an issue, and propagate every remediation back into
   the Jinja sources and their constraints instead of only into the rendered output.

Rendered-project dependency automation is intentionally not part of this boundary: it needs generated
`Threadpool`/`Celery` fixtures, a way to propagate updates back to the Jinja sources, and CI that exercises
integration and end-to-end tests on the rendered output. Until that exists, template security coverage stays manual.
