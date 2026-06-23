"""Tests for the ``@wrappable`` command marker."""

import click

from robotcode.plugin.click_helper.wrappable import is_wrappable, wrappable


def test_unmarked_command_is_not_wrappable() -> None:
    @click.command()
    def cmd() -> None:
        pass

    assert is_wrappable(cmd) is False


def test_wrappable_marks_the_command() -> None:
    @wrappable
    @click.command()
    def cmd() -> None:
        pass

    assert is_wrappable(cmd) is True


def test_wrappable_returns_the_same_command_object() -> None:
    @click.command()
    def cmd() -> None:
        pass

    assert wrappable(cmd) is cmd
