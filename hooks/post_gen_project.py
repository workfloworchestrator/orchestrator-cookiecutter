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
    subprocess.run(["uv", "venv"])
    subprocess.run(["uv", "sync", "--all-groups", "--all-extras"])


def install_pre_commit() -> None:
    print("\n" * 2, "=" * 10, "      Initialising git repo      ", "=" * 10, "\n" * 2)
    subprocess.run(["git", "init"])

    print("\n" * 2, "=" * 10, " Installing git pre-commit hooks ", "=" * 10, "\n" * 2)
    subprocess.run(["uv", "run", "pre-commit", "install"])


if __name__ == "__main__":
    run_uv_sync()
    install_pre_commit()
    print("\n" * 2, "=" * 10, " Completed cookiecutter install ", "=" * 11, "\n" * 2)
