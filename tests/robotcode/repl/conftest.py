"""Shared fixtures for the REPL test suite.

Provides a prompt_toolkit `AppSession` with dummy I/O for every test —
without it, instantiating `PromptSession` on Windows CI runners crashes
in `Win32Output` because the runners advertise themselves as
`xterm-256color` but don't expose a real Windows console screen buffer.
The fixture is a no-op when `prompt_toolkit` isn't installed.
"""

from typing import Iterator

import pytest


@pytest.fixture(autouse=True)
def _prompt_toolkit_dummy_session() -> Iterator[None]:
    try:
        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput
    except ImportError:
        yield
        return

    with create_pipe_input() as inp:
        with create_app_session(input=inp, output=DummyOutput()):
            yield
