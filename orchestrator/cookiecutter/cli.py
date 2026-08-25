# Copyright (c) 2025 Audrey M. Roy Greenfeld
# Copyright (c) 2026 GÉANT Orchestration and Automation Team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""CLI for orchestrator-cookiecutter.

Usage:
    `uvx orchestrator-cookiecutter` will default to the current directory.
    `uvx orchestrator-cookiecutter /path/to/output` to point to a different output directory.
    `uvx orchestrator-cookiecutter --no-input` to use default values for everything.
"""

from pathlib import Path
from typing import Annotated

import typer

from cookiecutter.main import cookiecutter

app = typer.Typer(help="Generate a Python package from the orchestrator-cookiecutter template.", add_completion=False)


@app.command(context_settings={"allow_extra_args": False})
def main(
    output_dir: Annotated[Path, typer.Argument(help="Where to output the generated project")] = Path.cwd(),  # noqa: B008
    no_input: bool = typer.Option(False, "--no-input", help="Do not prompt for parameters, use defaults"),
) -> None:
    """Generate a new Python package from the orchestrator-cookiecutter template."""
    # Template is bundled inside the package
    template_dir = Path(__file__).parent.parent.parent

    # Run cookiecutter with the bundled template
    cookiecutter(str(template_dir), output_dir=str(output_dir), no_input=no_input)


if __name__ == "__main__":
    app()
