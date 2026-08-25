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

import subprocess


def run_uv_sync() -> None:
    print("\n" * 2, "=" * 10, "     Installing dependencies     ", "=" * 10, "\n" * 2)
    subprocess.run(["uv", "venv"], check=True)
    subprocess.run(["uv", "sync", "--all-groups", "--all-extras"], check=True)


def install_pre_commit() -> None:
    print("\n" * 2, "=" * 10, "      Initialising git repo      ", "=" * 10, "\n" * 2)
    subprocess.run(["git", "init"], check=True)

    print("\n" * 2, "=" * 10, " Installing git pre-commit hooks ", "=" * 10, "\n" * 2)
    subprocess.run(["uv", "run", "pre-commit", "install"], check=True)


def run_db_init() -> None:
    print("\n" * 2, "=" * 10, " Initializing DB migration files ", "=" * 10, "\n" * 2)
    subprocess.run(["uv", "run", "{{ cookiecutter.project_slug }}/main.py", "db", "init"], check=True)


if __name__ == "__main__":
    run_uv_sync()
    install_pre_commit()
    run_db_init()
    print("\n" * 2, "=" * 10, " Completed cookiecutter install ", "=" * 11, "\n" * 2)
