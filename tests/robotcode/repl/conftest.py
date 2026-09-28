"""Shared fixtures for the REPL test suite.

Provides a prompt_toolkit `AppSession` with dummy I/O for every test —
without it, instantiating `PromptSession` on Windows CI runners crashes
in `Win32Output` because the runners advertise themselves as
`xterm-256color` but don't expose a real Windows console screen buffer.
`project` gives a test its own project directory, out of reach of the
developer's Robot configuration.
"""

import importlib
import sys
from pathlib import Path
from typing import Any, Iterator, List

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from robot.output import LOGGER

from robotcode.robot.config import utils as config_utils

# `robotcode.runner.cli.robot` is shadowed by the re-exported click command, so
# fetch the submodule itself to patch its global.
_runner_robot = importlib.import_module("robotcode.runner.cli.robot")


@pytest.fixture(autouse=True)
def _prompt_toolkit_dummy_session() -> Iterator[None]:
    with create_pipe_input() as inp:
        with create_app_session(input=inp, output=DummyOutput()):
            yield


@pytest.fixture(autouse=True)
def _unregister_robot_loggers(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Every interpreter registers a logger on Robot's global `LOGGER`. Left
    registered, it opens a real prompt — and blocks the test run — as soon as
    a later test executes the `repl` keyword, so drop them after each test."""
    registered: List[Any] = []
    # Patched on the class: monkeypatch restores it cleanly from the class `__dict__`.
    logger_class = type(LOGGER)
    register_logger = logger_class.register_logger

    def _register_logger(self: Any, *loggers: Any) -> None:
        registered.extend(loggers)
        register_logger(self, *loggers)

    monkeypatch.setattr(logger_class, "register_logger", _register_logger)
    yield
    LOGGER.unregister_logger(*registered)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    # `run_repl` prepends the profile's python-path to `sys.path`.
    monkeypatch.setattr(sys, "path", list(sys.path))
    # `handle_robot_options` stashes the app in a module global.
    monkeypatch.setattr(_runner_robot, "_app", _runner_robot._app)
    # Keep a developer's user-level robot.toml and ROBOT_OPTIONS out of the test.
    monkeypatch.setattr(config_utils, "get_user_config_file", lambda *args, **kwargs: None)
    monkeypatch.delenv("ROBOT_OPTIONS", raising=False)
    return tmp_path
