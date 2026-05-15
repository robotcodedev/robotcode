"""Acceptance-test fixtures for `robotcode discover`.

Mirrors the in-process `CliRunner` approach from
[tests/robotcode/runner/cli/results/conftest.py](../results/conftest.py)
but stays leaner: `discover` consumes `.robot` files directly, so there
is no need to run Robot once per session to generate `output.xml`
artefacts — the fixture suites *are* the inputs.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence

import pytest
from click.testing import CliRunner as _ClickCliRunner

from robotcode.cli import robotcode as _robotcode_group

SUITES_DIR = Path(__file__).parent / "suites"


@dataclass(frozen=True)
class CliResult:
    args: Sequence[str]
    returncode: int
    stdout: str
    stderr: str

    def expect_ok(self) -> "CliResult":
        if self.returncode != 0:
            raise AssertionError(
                f"robotcode exited with {self.returncode}\n"
                f"args:   {list(self.args)}\n"
                f"stdout: {self.stdout!r}\n"
                f"stderr: {self.stderr!r}"
            )
        return self


CliRunner = Callable[..., CliResult]
JsonRunner = Callable[..., Any]


@pytest.fixture
def robotcode_cli() -> CliRunner:
    """Callable: `(args, *, expect_ok=True) -> CliResult`. In-process."""
    runner = _ClickCliRunner()

    def run(args: Sequence[str], *, expect_ok: bool = True) -> CliResult:
        full = ["--no-color", "--no-pager", *args]
        result = runner.invoke(_robotcode_group, full)
        cli_result = CliResult(
            args=full,
            returncode=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr or "",
        )
        if expect_ok:
            if result.exception is not None and not isinstance(result.exception, SystemExit):
                raise AssertionError(
                    f"robotcode raised {type(result.exception).__name__}: {result.exception}\n"
                    f"args:   {full}\n"
                    f"stdout: {cli_result.stdout!r}\n"
                    f"stderr: {cli_result.stderr!r}"
                ) from result.exception
            cli_result.expect_ok()
        return cli_result

    return run


@pytest.fixture
def json_discover(robotcode_cli: CliRunner) -> JsonRunner:
    """Callable: `(subcommand, *args, suite_path) -> dict`.

    Wraps `robotcode --format json discover <subcommand> ... <path>` and
    returns the parsed JSON object.
    """

    def run(
        subcommand: str,
        *extra: str,
        suite_path: Path,
        expect_ok: bool = True,
    ) -> Any:
        args: List[str] = ["--format", "json", "discover", subcommand, *extra, str(suite_path)]
        result = robotcode_cli(args, expect_ok=expect_ok)
        if not expect_ok or not result.stdout.strip():
            return result
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"failed to parse JSON output of {args!r}: {e}\nstdout was: {result.stdout!r}") from e

    return run


@pytest.fixture
def text_discover(robotcode_cli: CliRunner) -> CliRunner:
    """Callable: `(subcommand, *args, suite_path) -> CliResult`. Default TEXT format."""

    def run(
        subcommand: str,
        *extra: str,
        suite_path: Optional[Path] = None,
        expect_ok: bool = True,
    ) -> CliResult:
        args: List[str] = ["discover", subcommand, *extra]
        if suite_path is not None:
            args.append(str(suite_path))
        return robotcode_cli(args, expect_ok=expect_ok)

    return run


# ---------------------------------------------------------------------------
# Suite paths
# ---------------------------------------------------------------------------


@pytest.fixture
def flat_suite() -> Path:
    return SUITES_DIR / "flat.robot"


@pytest.fixture
def nested_suite() -> Path:
    return SUITES_DIR / "nested"
