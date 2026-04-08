"""Tests for the layered Run Keyword detection strategy.

Tests are organized by detection layer:
- Layer 1: Type hint detection (RF 7.4+) via is_keyword_name / is_keyword_argument
- Layer 2: RUN_KW_REGISTER (third-party libraries registered via register_run_keyword)
- Layer 3: Hardcoded name lists (BuiltIn fallback, used on RF < 7.4)

Priority: Layer 1 > Layer 2 > Layer 3.
"""

import pytest

from robotcode.robot.diagnostics.library_doc import (
    ALL_RUN_KEYWORDS,
    BUILTIN_LIBRARY_NAME,
    ArgumentInfo,
    KeywordArgumentKind,
    KeywordDoc,
)
from robotcode.robot.diagnostics.semantic_analyzer.run_keyword import (
    KeywordArgumentStrategy,
    get_keyword_argument_strategy,
)
from robotcode.robot.utils import RF_VERSION


def _make_kw(
    name: str = "My Keyword",
    libname: str = "MyLib",
    arguments: list[ArgumentInfo] | None = None,
    is_registered_run_keyword: bool = False,
) -> KeywordDoc:
    """Build a minimal KeywordDoc for testing."""
    return KeywordDoc(
        line_no=-1,
        col_offset=-1,
        end_line_no=-1,
        end_col_offset=-1,
        source=None,
        name=name,
        libname=libname,
        arguments=arguments or [],
        is_registered_run_keyword=is_registered_run_keyword,
    )


def _arg(name: str, is_keyword_name: bool = False, is_keyword_argument: bool = False) -> ArgumentInfo:
    """Build a minimal ArgumentInfo for testing."""
    return ArgumentInfo(
        name=name,
        str_repr=name,
        kind=KeywordArgumentKind.POSITIONAL_OR_NAMED,
        required=True,
        is_keyword_name=is_keyword_name,
        is_keyword_argument=is_keyword_argument,
    )


class TestLayer1TypeHints:
    """Layer 1: any argument annotated with KeywordName or KeywordArgument → TYPE_HINTS."""

    def test_keyword_name_arg_detected(self) -> None:
        kw = _make_kw(arguments=[_arg("name", is_keyword_name=True)])
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_keyword_argument_arg_detected(self) -> None:
        kw = _make_kw(arguments=[_arg("args", is_keyword_argument=True)])
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_union_arg_both_flags_detected(self) -> None:
        # KeywordName | KeywordArgument union → both flags True
        kw = _make_kw(arguments=[_arg("names_and_args", is_keyword_name=True, is_keyword_argument=True)])
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_regular_arg_before_keyword_name_ignored(self) -> None:
        # condition (plain) + name (KeywordName) + args (KeywordArgument)
        kw = _make_kw(
            arguments=[
                _arg("condition"),
                _arg("name", is_keyword_name=True),
                _arg("args", is_keyword_argument=True),
            ]
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_no_type_hints_does_not_trigger_layer1(self) -> None:
        kw = _make_kw(arguments=[_arg("condition"), _arg("name"), _arg("args")])
        # Falls through to Layer 3 (or None if not a BuiltIn keyword)
        assert get_keyword_argument_strategy(kw) is None


class TestLayer2RegisteredRunKeyword:
    """Layer 2: is_registered_run_keyword=True and no type hints → REGISTERED."""

    def test_registered_keyword_detected(self) -> None:
        kw = _make_kw(is_registered_run_keyword=True)
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.REGISTERED

    def test_registered_with_plain_args_detected(self) -> None:
        kw = _make_kw(
            arguments=[_arg("name"), _arg("args")],
            is_registered_run_keyword=True,
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.REGISTERED

    def test_not_registered_does_not_trigger_layer2(self) -> None:
        kw = _make_kw(is_registered_run_keyword=False)
        assert get_keyword_argument_strategy(kw) is None


class TestLayer3Hardcoded:
    """Layer 3: BuiltIn Run Keyword variants detected by name when no type hints or register."""

    @pytest.mark.parametrize("kw_name", list(ALL_RUN_KEYWORDS))
    def test_all_builtin_run_keywords_detected(self, kw_name: str) -> None:
        kw = _make_kw(name=kw_name, libname=BUILTIN_LIBRARY_NAME)
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.HARDCODED

    def test_builtin_log_not_detected(self) -> None:
        kw = _make_kw(name="Log", libname=BUILTIN_LIBRARY_NAME)
        assert get_keyword_argument_strategy(kw) is None

    def test_non_builtin_run_keyword_name_not_detected(self) -> None:
        # Same name as BuiltIn, but from a different library → not hardcoded
        kw = _make_kw(name="Run Keyword", libname="MyCustomLib")
        assert get_keyword_argument_strategy(kw) is None


class TestLayerPriority:
    """Layer 1 beats Layer 2 beats Layer 3."""

    def test_type_hints_beat_registered(self) -> None:
        kw = _make_kw(
            arguments=[_arg("name", is_keyword_name=True)],
            is_registered_run_keyword=True,
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_type_hints_beat_hardcoded(self) -> None:
        kw = _make_kw(
            name="Run Keyword",
            libname=BUILTIN_LIBRARY_NAME,
            arguments=[_arg("name", is_keyword_name=True)],
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_registered_beats_hardcoded(self) -> None:
        kw = _make_kw(
            name="Run Keyword",
            libname=BUILTIN_LIBRARY_NAME,
            is_registered_run_keyword=True,
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.REGISTERED


class TestRegularKeywords:
    """Regular keywords (no Run Keyword variant) → None."""

    def test_empty_arguments(self) -> None:
        assert get_keyword_argument_strategy(_make_kw()) is None

    def test_plain_positional_args(self) -> None:
        kw = _make_kw(arguments=[_arg("message"), _arg("level")])
        assert get_keyword_argument_strategy(kw) is None


@pytest.mark.skipif(RF_VERSION < (7, 4), reason="KeywordName/KeywordArgument type hints require RF >= 7.4")
class TestBuiltinTypeHintsRF74:
    """Integration tests: BuiltIn Run Keyword variants parsed from real RF 7.4+ type hints.

    Verifies the full chain: PythonArgumentParser → ArgumentInfo.from_robot()
    → get_keyword_argument_strategy().
    """

    def _builtin_args(self, method: object) -> list[ArgumentInfo]:
        from robot.running.arguments.argumentparser import PythonArgumentParser

        parser = PythonArgumentParser(type="LIBRARY")
        return [ArgumentInfo.from_robot(a) for a in parser.parse(method)]

    def test_run_keyword_is_type_hints(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn

        kw = _make_kw(
            name="Run Keyword",
            libname=BUILTIN_LIBRARY_NAME,
            arguments=self._builtin_args(BuiltIn.run_keyword),
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_run_keywords_is_type_hints(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn

        kw = _make_kw(
            name="Run Keywords",
            libname=BUILTIN_LIBRARY_NAME,
            arguments=self._builtin_args(BuiltIn.run_keywords),
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_run_keyword_if_is_type_hints(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn

        kw = _make_kw(
            name="Run Keyword If",
            libname=BUILTIN_LIBRARY_NAME,
            arguments=self._builtin_args(BuiltIn.run_keyword_if),
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_wait_until_keyword_succeeds_is_type_hints(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn

        kw = _make_kw(
            name="Wait Until Keyword Succeeds",
            libname=BUILTIN_LIBRARY_NAME,
            arguments=self._builtin_args(BuiltIn.wait_until_keyword_succeeds),
        )
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.TYPE_HINTS

    def test_log_is_none(self) -> None:
        from robot.libraries.BuiltIn import BuiltIn

        kw = _make_kw(
            name="Log",
            libname=BUILTIN_LIBRARY_NAME,
            arguments=self._builtin_args(BuiltIn.log),
        )
        assert get_keyword_argument_strategy(kw) is None


@pytest.mark.skipif(RF_VERSION >= (7, 4), reason="Tests RF < 7.4 fallback to hardcoded layer")
class TestBuiltinHardcodedFallbackPreRF74:
    """On RF < 7.4, type hints are absent; BuiltIn Run Keywords must be detected via Layer 3."""

    @pytest.mark.parametrize("kw_name", list(ALL_RUN_KEYWORDS))
    def test_all_builtin_run_keywords_use_hardcoded(self, kw_name: str) -> None:
        from robot.libraries.BuiltIn import BuiltIn  # pyright: ignore[reportMissingImports]
        from robot.running.arguments.argumentparser import PythonArgumentParser

        method_name = kw_name.lower().replace(" ", "_")
        method = getattr(BuiltIn, method_name, None)
        if method is None:
            pytest.skip(f"BuiltIn.{method_name} not found")

        parser = PythonArgumentParser(type="LIBRARY")
        args = [ArgumentInfo.from_robot(a) for a in parser.parse(method)]

        kw = _make_kw(name=kw_name, libname=BUILTIN_LIBRARY_NAME, arguments=args)
        # On RF < 7.4, no type hints → should fall through to Layer 3
        assert get_keyword_argument_strategy(kw) == KeywordArgumentStrategy.HARDCODED
