"""Acceptance-test fixtures for `robotcode results`.

The tests feed the `robotcode` Click group via `click.testing.CliRunner`
(in-process — no Python-startup overhead per call) with `output.xml`
files that are generated *once per pytest session* by running the
matching Robot Framework suite under `tests/.../suites/` with the
currently installed RF version.

Three architectural choices:

1. **CliRunner** for CLI invocation — in-process invocation of the
   actual `robotcode` Click group. Cuts test runtime from ~50 s to a
   few seconds; trade-off: doesn't exercise the bundled-script
   shell wrapper.
2. **Live fixture generation** — `python -m robot` runs the fixture
   suites once per session via subprocess (only ~11 calls total).
3. **JSON-structural + selective text snapshots** — parse `--format
   json` output and assert on fields; only specific text-render cases
   are pinned with regtest2.
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
from click.testing import CliRunner as _ClickCliRunner

from robotcode.cli import robotcode as _robotcode_group
from robotcode.core.utils.version import Version
from robotcode.robot.utils import RF_VERSION

SUITES_DIR = Path(__file__).parent / "suites"


# ---------------------------------------------------------------------------
# RF-version markers
# ---------------------------------------------------------------------------

needs_rf_70 = pytest.mark.skipif(
    RF_VERSION < (7, 0),
    reason="requires Robot Framework 7.0+ (VAR, JSON output, attribute renames)",
)
needs_rf_72 = pytest.mark.skipif(
    RF_VERSION < (7, 2),
    reason="requires Robot Framework 7.2+ (GROUP block)",
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
    """Callable: `(args, *, expect_ok=True) -> CliResult`.

    Invokes the `robotcode` Click group in-process via
    `click.testing.CliRunner` — no Python startup per call, so the suite
    runs in seconds instead of minutes. The global flags `--no-color`
    and `--no-pager` are pre-injected so output is deterministic.

    Unexpected exceptions (i.e. bugs inside the CLI, not regular
    UsageErrors) propagate when `expect_ok=True` so they fail loudly
    instead of being masked as a non-zero exit.
    """
    runner = _ClickCliRunner()

    def run(
        args: Sequence[str],
        *,
        expect_ok: bool = True,
    ) -> CliResult:
        full = ["--no-color", "--no-pager", *args]
        result = runner.invoke(_robotcode_group, full)
        cli_result = CliResult(
            args=full,
            returncode=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr or "",
        )
        if expect_ok:
            # Surface unexpected exceptions (anything other than SystemExit
            # raised inside the command) so they don't disguise themselves
            # as a "just" non-zero exit.
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
def json_result(robotcode_cli: CliRunner) -> JsonRunner:
    """Callable: `(subcommand, *args, output_path) -> dict`.

    Wraps `robotcode --format json results <subcommand> ... --output <path>`
    and returns the parsed JSON object (or list).
    """

    def run(
        subcommand: str,
        *extra: str,
        output_path: Optional[Path] = None,
        expect_ok: bool = True,
    ) -> Any:
        args: List[str] = ["--format", "json", "results", subcommand]
        args.extend(extra)
        if output_path is not None:
            args.extend(["--output", str(output_path)])
        result = robotcode_cli(args, expect_ok=expect_ok)
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
        expect_ok: bool = True,
    ) -> CliResult:
        args: List[str] = ["results", subcommand, *extra]
        if output_path is not None:
            args.extend(["--output", str(output_path)])
        return robotcode_cli(args, expect_ok=expect_ok)

    return run


# ---------------------------------------------------------------------------
# Session-scoped output generators
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def session_output_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One temp dir to hold every generated `output.xml` of the session."""
    return tmp_path_factory.mktemp("results_acceptance")


def _run_robot(suite_path: Path, output_dir: Path, name: str, *, suite_name: Optional[str] = None) -> Path:
    """Run RF once and return the path to the generated `output.xml`.

    Passing `suite_name` overrides the top-level suite name via `--name`
    (useful for the diff fixtures, where baseline and current must share
    a longname prefix so diffing can match tests across both runs).
    """
    output_xml = output_dir / f"{name}.xml"
    # Don't bother generating html/log/report — we only need output.xml.
    args = [
        "-m",
        "robot",
        "--output",
        str(output_xml),
        "--report",
        "NONE",
        "--log",
        "NONE",
    ]
    if suite_name is not None:
        args.extend(["--name", suite_name])
    args.append(str(suite_path))
    proc = _run(args, timeout=120.0)
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
def statements_modern_output(session_output_dir: Path) -> Path:
    """WHILE / TRY / RETURN / BREAK / CONTINUE — available on every supported RF."""
    return _run_robot(SUITES_DIR / "statements_modern.robot", session_output_dir, "statements_modern")


@pytest.fixture(scope="session")
def keyword_meta_output(session_output_dir: Path) -> Path:
    """Suite/keyword documentation/metadata fixture for search tests."""
    return _run_robot(SUITES_DIR / "keyword_meta.robot", session_output_dir, "keyword_meta")


@pytest.fixture(scope="session")
def statements_var_output(session_output_dir: Path) -> Path:
    """RF 7.0+ VAR statement."""
    if RF_VERSION < (7, 0):
        pytest.skip("statements_var.robot requires Robot Framework 7.0+")
    return _run_robot(SUITES_DIR / "statements_var.robot", session_output_dir, "statements_var")


@pytest.fixture(scope="session")
def statements_group_output(session_output_dir: Path) -> Path:
    """RF 7.2+ GROUP block."""
    if RF_VERSION < (7, 2):
        pytest.skip("statements_group.robot requires Robot Framework 7.2+")
    return _run_robot(SUITES_DIR / "statements_group.robot", session_output_dir, "statements_group")


@pytest.fixture(scope="session")
def artifacts_output(session_output_dir: Path) -> Path:
    """`output.xml` from the artifacts suite (embedded + external refs)."""
    return _run_robot(SUITES_DIR / "artifacts.robot", session_output_dir, "artifacts")


@pytest.fixture(scope="session")
def errors_output(session_output_dir: Path) -> Path:
    """`output.xml` from a suite with a deliberate import error."""
    return _run_robot(SUITES_DIR / "errors.robot", session_output_dir, "errors")


@pytest.fixture(scope="session")
def diff_baseline_output(session_output_dir: Path) -> Path:
    """Baseline `output.xml` for the diff tests — A,B,C all pass."""
    return _run_robot(
        SUITES_DIR / "diff_baseline.robot",
        session_output_dir,
        "diff_baseline",
        suite_name="Diff",
    )


@pytest.fixture(scope="session")
def diff_current_output(session_output_dir: Path) -> Path:
    """Current `output.xml` for the diff tests — A passes, B fails, C gone, D added."""
    return _run_robot(
        SUITES_DIR / "diff_current.robot",
        session_output_dir,
        "diff_current",
        suite_name="Diff",
    )


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
