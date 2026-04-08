"""Tests for ArgumentInfo.is_keyword_name / is_keyword_argument fields.

Tests the RF 7.4+ type hint detection for KeywordName and KeywordArgument
on ArgumentInfo, including the from_robot() factory method.
"""

import pytest

from robotcode.robot.diagnostics.library_doc import ArgumentInfo, KeywordArgumentKind
from robotcode.robot.utils import RF_VERSION


class TestArgumentInfoDefaults:
    def test_is_keyword_name_default_false(self) -> None:
        info = ArgumentInfo(
            name="arg",
            str_repr="arg",
            kind=KeywordArgumentKind.POSITIONAL_OR_NAMED,
            required=True,
        )
        assert info.is_keyword_name is False

    def test_is_keyword_argument_default_false(self) -> None:
        info = ArgumentInfo(
            name="arg",
            str_repr="arg",
            kind=KeywordArgumentKind.POSITIONAL_OR_NAMED,
            required=True,
        )
        assert info.is_keyword_argument is False

    def test_explicit_keyword_name_true(self) -> None:
        info = ArgumentInfo(
            name="name",
            str_repr="name: KeywordName",
            kind=KeywordArgumentKind.POSITIONAL_ONLY,
            required=True,
            is_keyword_name=True,
        )
        assert info.is_keyword_name is True
        assert info.is_keyword_argument is False

    def test_explicit_keyword_argument_true(self) -> None:
        info = ArgumentInfo(
            name="args",
            str_repr="*args: KeywordArgument",
            kind=KeywordArgumentKind.VAR_POSITIONAL,
            required=False,
            is_keyword_argument=True,
        )
        assert info.is_keyword_name is False
        assert info.is_keyword_argument is True


@pytest.mark.skipif(RF_VERSION < (7, 4), reason="KeywordName/KeywordArgument requires RF >= 7.4")
class TestFromRobotKeywordTypes:
    """Test from_robot() detection of KeywordName/KeywordArgument types on RF 7.4+."""

    def test_run_keyword_has_keyword_name(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn
        from robot.running.arguments.argumentparser import PythonArgumentParser

        parser = PythonArgumentParser(type="LIBRARY")
        spec = parser.parse(BuiltIn.run_keyword)
        args = [ArgumentInfo.from_robot(a) for a in spec]

        # Find 'name' argument (positional-only KeywordName)
        name_arg = next(a for a in args if a.name == "name")
        assert name_arg.is_keyword_name is True
        assert name_arg.is_keyword_argument is False

    def test_run_keyword_has_keyword_argument(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn
        from robot.running.arguments.argumentparser import PythonArgumentParser

        parser = PythonArgumentParser(type="LIBRARY")
        spec = parser.parse(BuiltIn.run_keyword)
        args = [ArgumentInfo.from_robot(a) for a in spec]

        # Find 'args' argument (var-positional KeywordArgument)
        args_arg = next(a for a in args if a.name == "args")
        assert args_arg.is_keyword_name is False
        assert args_arg.is_keyword_argument is True

    def test_run_keywords_union_type(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn
        from robot.running.arguments.argumentparser import PythonArgumentParser

        parser = PythonArgumentParser(type="LIBRARY")
        spec = parser.parse(BuiltIn.run_keywords)
        args = [ArgumentInfo.from_robot(a) for a in spec]

        # 'names_and_args' has union type KeywordName | KeywordArgument
        na_arg = next(a for a in args if a.name == "names_and_args")
        assert na_arg.is_keyword_name is True
        assert na_arg.is_keyword_argument is True

    def test_run_keyword_if_condition_not_keyword(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn
        from robot.running.arguments.argumentparser import PythonArgumentParser

        parser = PythonArgumentParser(type="LIBRARY")
        spec = parser.parse(BuiltIn.run_keyword_if)
        args = [ArgumentInfo.from_robot(a) for a in spec]

        # 'condition' is plain Expression, not KeywordName
        cond_arg = next(a for a in args if a.name == "condition")
        assert cond_arg.is_keyword_name is False
        assert cond_arg.is_keyword_argument is False

        # 'name' is KeywordName
        name_arg = next(a for a in args if a.name == "name")
        assert name_arg.is_keyword_name is True

    def test_wait_until_keyword_succeeds(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn
        from robot.running.arguments.argumentparser import PythonArgumentParser

        parser = PythonArgumentParser(type="LIBRARY")
        spec = parser.parse(BuiltIn.wait_until_keyword_succeeds)
        args = [ArgumentInfo.from_robot(a) for a in spec]

        # retry and retry_interval are regular
        retry_arg = next(a for a in args if a.name == "retry")
        assert retry_arg.is_keyword_name is False
        assert retry_arg.is_keyword_argument is False

        # name is KeywordName
        name_arg = next(a for a in args if a.name == "name")
        assert name_arg.is_keyword_name is True


@pytest.mark.skipif(RF_VERSION >= (7, 4), reason="Test verifies behavior on RF < 7.4")
class TestFromRobotPreRF74:
    """On RF < 7.4, all args should have is_keyword_name=False, is_keyword_argument=False."""

    def test_run_keyword_no_detection(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn
        from robot.running.arguments.argumentparser import PythonArgumentParser

        parser = PythonArgumentParser(type="LIBRARY")
        spec = parser.parse(BuiltIn.run_keyword)
        args = [ArgumentInfo.from_robot(a) for a in spec]

        for a in args:
            assert a.is_keyword_name is False
            assert a.is_keyword_argument is False
