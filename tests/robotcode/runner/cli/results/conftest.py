"""Acceptance-test fixtures for `robotcode results`.

These tests spawn a real `robotcode` subprocess (so the bundled-script /
quoting layer is exercised too) and feed it `output.xml` files that are
generated *once per pytest session* by running the matching Robot Framework
suite under `tests/.../suites/` with the currently installed RF version.

Three architectural choices, set by the plan:

1. **subprocess** for CLI invocation — real process, real exit codes.
2. **Live fixture generation** — RF runs the suites once per session, so the
   test matrix automatically covers every supported RF version.
3. **JSON-structural + selective text snapshots** — parse `--format json`
   output and assert on fields; only specific text-render cases are pinned
   with regtest2.
"""

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

import pytest

from robotcode.core.utils.version import Version
from robotcode.robot.utils import RF_VERSION

SUITES_DIR = Path(__file__).parent / "suites"


# ---------------------------------------------------------------------------
# RF-version markers
# ---------------------------------------------------------------------------

needs_rf_52 = pytest.mark.skipif(
    RF_VERSION < (5, 2),
    reason="requires Robot Framework 5.2+ (WHILE / TRY / RETURN / BREAK / CONTINUE)",
)
needs_rf_61 = pytest.mark.skipif(
    RF_VERSION < (6, 1),
    reason="requires Robot Framework 6.1+ (VAR statement)",
)
needs_rf_70 = pytest.mark.skipif(
    RF_VERSION < (7, 0),
    reason="requires Robot Framework 7.0+ (GROUP statement, JSON output, attribute renames)",
)


# ---------------------------------------------------------------------------
# Subprocess wiring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CliResult:
    """Outcome of one `robotcode` invocation."""

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

    def expect_fail(self) -> "CliResult":
        if self.returncode == 0:
            raise AssertionError(
                f"robotcode exited 0 but a failure was expected\nargs:   {list(self.args)}\nstdout: {self.stdout!r}"
            )
        return self


def _clean_env() -> Dict[str, str]:
    """Environment that suppresses color/pager so output is deterministic."""
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"
    # Belt and braces: also tell `less` not to spawn even if something tries.
    env["PAGER"] = "cat"
    env.pop("FORCE_COLOR", None)
    return env


def _run(
    python_args: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    check: bool = False,
    timeout: float = 60.0,
) -> "subprocess.CompletedProcess[str]":
    """Run `python -m <module> <args>` with the cleaned env."""
    full_env = _clean_env()
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, *python_args],
        cwd=str(cwd) if cwd else None,
        env=full_env,
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
    )


CliRunner = Callable[..., CliResult]
JsonRunner = Callable[..., Any]


@pytest.fixture
def robotcode_cli() -> CliRunner:
    """Callable: `(args, *, cwd=None, expect_ok=True) -> CliResult`.

    Runs `python -m robotcode.cli` so the test never depends on the
    `robotcode` script being on PATH. The global flags `--no-color` and
    `--no-pager` are pre-injected.
    """

    def run(
        args: Sequence[str],
        *,
        cwd: Optional[Path] = None,
        expect_ok: bool = True,
        timeout: float = 60.0,
    ) -> CliResult:
        full = ["-m", "robotcode.cli", "--no-color", "--no-pager", *args]
        proc = _run(full, cwd=cwd, timeout=timeout)
        result = CliResult(
            args=full,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
        if expect_ok:
            result.expect_ok()
        return result

    return run


@pytest.fixture
def json_result(robotcode_cli: CliRunner) -> JsonRunner:
    """Callable: `(subcommand, *args, output_path) -> dict`.

    Wraps `robotcode --format json results <subcommand> ... --output <path>`
    and returns the parsed JSON object (or list).
    """

    def run(
        subcommand: str,
        *extra: str,
        output_path: Optional[Path] = None,
        cwd: Optional[Path] = None,
        expect_ok: bool = True,
    ) -> Any:
        args: List[str] = ["--format", "json", "results", subcommand]
        args.extend(extra)
        if output_path is not None:
            args.extend(["--output", str(output_path)])
        result = robotcode_cli(args, cwd=cwd, expect_ok=expect_ok)
        if not expect_ok or not result.stdout.strip():
            return result
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise AssertionError(f"failed to parse JSON output of {args!r}: {e}\nstdout was: {result.stdout!r}") from e

    return run


@pytest.fixture
def text_result(robotcode_cli: CliRunner) -> CliRunner:
    """Callable: `(subcommand, *args, output_path) -> CliResult`.

    Always uses the default TEXT format. The caller is responsible for
    `strip_ansi(...)` if they want plain text.
    """

    def run(
        subcommand: str,
        *extra: str,
        output_path: Optional[Path] = None,
        cwd: Optional[Path] = None,
        expect_ok: bool = True,
    ) -> CliResult:
        args: List[str] = ["results", subcommand, *extra]
        if output_path is not None:
            args.extend(["--output", str(output_path)])
        return robotcode_cli(args, cwd=cwd, expect_ok=expect_ok)

    return run


# ---------------------------------------------------------------------------
# Session-scoped output generators
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def session_output_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One temp dir to hold every generated `output.xml` of the session."""
    return tmp_path_factory.mktemp("results_acceptance")


def _run_robot(suite_path: Path, output_dir: Path, name: str) -> Path:
    """Run RF once and return the path to the generated `output.xml`."""
    output_xml = output_dir / f"{name}.xml"
    # Don't bother generating html/log/report — we only need output.xml.
    proc = _run(
        [
            "-m",
            "robot",
            "--output",
            str(output_xml),
            "--report",
            "NONE",
            "--log",
            "NONE",
            str(suite_path),
        ],
        timeout=120.0,
    )
    # Robot exits non-zero on test failures, which is *expected* for our
    # mixed-outcome fixture suites. We only care that the output.xml is
    # produced and well-formed.
    if not output_xml.exists():
        raise AssertionError(
            f"Robot failed to produce {output_xml} for {suite_path}.\n"
            f"returncode: {proc.returncode}\n"
            f"stdout: {proc.stdout!r}\n"
            f"stderr: {proc.stderr!r}"
        )
    return output_xml


@pytest.fixture(scope="session")
def basic_output(session_output_dir: Path) -> Path:
    """`output.xml` from running `suites/basic.robot` once per session."""
    return _run_robot(SUITES_DIR / "basic.robot", session_output_dir, "basic")


@pytest.fixture(scope="session")
def tagged_output(session_output_dir: Path) -> Path:
    """`output.xml` from running `suites/tagged.robot` once per session."""
    return _run_robot(SUITES_DIR / "tagged.robot", session_output_dir, "tagged")


@pytest.fixture(scope="session")
def nested_output(session_output_dir: Path) -> Path:
    """`output.xml` from running the `suites/nested/` 3-level hierarchy."""
    return _run_robot(SUITES_DIR / "nested", session_output_dir, "nested")


@pytest.fixture(scope="session")
def loops_and_branches_output(session_output_dir: Path) -> Path:
    """`output.xml` from the cross-version FOR/IF/ELSE suite."""
    return _run_robot(SUITES_DIR / "loops_and_branches.robot", session_output_dir, "loops_and_branches")


@pytest.fixture(scope="session")
def statements_output(session_output_dir: Path) -> Path:
    """`output.xml` from the RF 7+ statements suite. Skips on older RF."""
    if RF_VERSION < (7, 0):
        pytest.skip("statements.robot requires Robot Framework 7.0+")
    return _run_robot(SUITES_DIR / "statements.robot", session_output_dir, "statements")


@pytest.fixture(scope="session")
def artifacts_output(session_output_dir: Path) -> Path:
    """`output.xml` from the artifacts suite (embedded + external refs)."""
    return _run_robot(SUITES_DIR / "artifacts.robot", session_output_dir, "artifacts")


# ---------------------------------------------------------------------------
# Misc helpers exposed as fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _ensure_robot_available() -> None:
    """Skip the whole module gracefully if `robot` cannot be imported."""
    if shutil.which(sys.executable) is None:
        pytest.skip("python executable unavailable")
    try:
        import robot  # noqa: F401
    except ImportError:
        pytest.skip("Robot Framework is not importable in this environment")


@pytest.fixture
def rf_version() -> Version:
    """The currently installed RF version, for inline gating.

    `Version` is a `NamedTuple(major, minor)` — compares against `(7, 0)`
    etc. straight out of the box.
    """
    return RF_VERSION
