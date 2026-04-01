"""Tests for BDD prefix handling with multi-word and multi-language prefixes.

Verifies that build_bdd_prefix_regexp correctly sorts by length (longest first)
and that model_helper methods (split_bdd_prefix, strip_bdd_prefix, is_bdd_token)
work correctly with non-English BDD prefixes like French.
"""

from typing import Optional, Set
from unittest.mock import MagicMock

import pytest
from robot.parsing.lexer.tokens import Token

from robotcode.robot.diagnostics.keyword_finder import (
    DEFAULT_BDD_PREFIX_REGEXP,
    build_bdd_prefix_regexp,
)
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.utils import RF_VERSION

# --- French BDD prefixes (as Robot Framework defines them via Languages("Fr")) ---
FRENCH_BDD_PREFIXES: Set[str] = {
    "Étant Donné",
    "Étant Donné Que",
    "Étant Donné Qu'",
    "Soit",
    "Sachant Que",
    "Sachant Qu'",
    "Sachant",
    "Etant Donné",
    "Etant Donné Que",
    "Etant Donné Qu'",
    "Etant Donnée",
    "Etant Données",
    "Lorsque",
    "Quand",
    "Lorsqu'",
    "Alors",
    "Donc",
    "Et",
    "Et Que",
    "Et Qu'",
    "Mais",
    "Mais Que",
    "Mais Qu'",
}

GERMAN_BDD_PREFIXES: Set[str] = {
    "Angenommen",
    "Wenn",
    "Dann",
    "Und",
    "Aber",
}

FINNISH_BDD_PREFIXES: Set[str] = {
    "Oletetaan",
    "Kun",
    "Niin",
    "Ja",
    "Mutta",
}


def _mock_namespace(bdd_prefixes: Optional[Set[str]] = None) -> MagicMock:
    ns = MagicMock()
    if bdd_prefixes is not None:
        ns.languages.bdd_prefixes = bdd_prefixes
    else:
        ns.languages = None
    return ns


def _make_token(value: str) -> Token:
    return Token(Token.KEYWORD, value, 1, 0)


# =============================================================================
# Tests for build_bdd_prefix_regexp
# =============================================================================


class TestBuildBddPrefixRegexp:
    def test_default_prefixes_match(self) -> None:
        regexp = DEFAULT_BDD_PREFIX_REGEXP
        for prefix in ["Given", "When", "Then", "And", "But"]:
            m = regexp.match(f"{prefix} something")
            assert m is not None, f"Should match '{prefix} something'"
            assert m.group(1).lower() == prefix.lower()

    def test_default_prefixes_case_insensitive(self) -> None:
        regexp = DEFAULT_BDD_PREFIX_REGEXP
        for text in ["given something", "WHEN action", "tHeN result"]:
            m = regexp.match(text)
            assert m is not None, f"Should match case-insensitively: '{text}'"

    def test_default_prefixes_no_match_without_space(self) -> None:
        regexp = DEFAULT_BDD_PREFIX_REGEXP
        assert regexp.match("Givenno_space") is None
        assert regexp.match("Given") is None

    @pytest.mark.parametrize(
        ("text", "expected_prefix"),
        [
            ("Et que My Keyword", "Et que"),
            ("Et My Keyword", "Et"),
            ("Étant donné que My Keyword", "Étant donné que"),
            ("Étant donné My Keyword", "Étant donné"),
            ("Mais que My Keyword", "Mais que"),
            ("Mais My Keyword", "Mais"),
            ("Lorsque My Keyword", "Lorsque"),
            ("Alors My Keyword", "Alors"),
            ("Sachant que My Keyword", "Sachant que"),
            ("Sachant My Keyword", "Sachant"),
            ("Etant donné que My Keyword", "Etant donné que"),
        ],
    )
    def test_french_longest_prefix_wins(self, text: str, expected_prefix: str) -> None:
        regexp = build_bdd_prefix_regexp(frozenset(FRENCH_BDD_PREFIXES))
        m = regexp.match(text)
        assert m is not None, f"Should match: '{text}'"
        assert m.group(1).lower() == expected_prefix.lower(), (
            f"Expected prefix '{expected_prefix}' but got '{m.group(1)}' for '{text}'"
        )

    @pytest.mark.parametrize(
        "text",
        [
            "Et",
            "Mais",
            "NotAPrefix something",
            "",
        ],
    )
    def test_french_no_match(self, text: str) -> None:
        regexp = build_bdd_prefix_regexp(frozenset(FRENCH_BDD_PREFIXES))
        assert regexp.match(text) is None, f"Should NOT match: '{text}'"

    def test_french_case_insensitive(self) -> None:
        regexp = build_bdd_prefix_regexp(frozenset(FRENCH_BDD_PREFIXES))
        m = regexp.match("ET QUE My Keyword")
        assert m is not None
        assert m.group(1).lower() == "et que"

    def test_german_prefixes(self) -> None:
        regexp = build_bdd_prefix_regexp(frozenset(GERMAN_BDD_PREFIXES))
        for prefix in ["Angenommen", "Wenn", "Dann", "Und", "Aber"]:
            m = regexp.match(f"{prefix} etwas tun")
            assert m is not None, f"Should match German prefix '{prefix}'"
            assert m.group(1).lower() == prefix.lower()

    def test_finnish_prefixes(self) -> None:
        regexp = build_bdd_prefix_regexp(frozenset(FINNISH_BDD_PREFIXES))
        for prefix in ["Oletetaan", "Kun", "Niin", "Ja", "Mutta"]:
            m = regexp.match(f"{prefix} jotain")
            assert m is not None, f"Should match Finnish prefix '{prefix}'"

    def test_caching(self) -> None:
        prefixes = frozenset(FRENCH_BDD_PREFIXES)
        r1 = build_bdd_prefix_regexp(prefixes)
        r2 = build_bdd_prefix_regexp(prefixes)
        assert r1 is r2, "Same frozenset should return cached regexp"

    def test_sorted_longest_first(self) -> None:
        regexp = build_bdd_prefix_regexp(frozenset({"Et", "Et Que", "Et Qu'"}))
        # "Et que" should be matched, not just "Et"
        m = regexp.match("Et que keyword")
        assert m is not None
        assert m.group(1).lower() == "et que"

        # "Et" alone should still work when followed by non-"que" word
        m = regexp.match("Et keyword")
        assert m is not None
        assert m.group(1).lower() == "et"


# =============================================================================
# Tests for ModelHelper BDD methods with languages
# =============================================================================


class TestModelHelperSplitBddPrefix:
    def test_english_default(self) -> None:
        ns = _mock_namespace(None)
        token = _make_token("Given something happens")
        bdd, rest = ModelHelper.split_bdd_prefix(ns, token)
        assert bdd is not None
        assert bdd.value == "Given"
        assert rest is not None
        assert rest.value == "something happens"
        assert rest.col_offset == 6

    def test_no_prefix(self) -> None:
        ns = _mock_namespace(None)
        token = _make_token("Do Something")
        bdd, rest = ModelHelper.split_bdd_prefix(ns, token)
        assert bdd is None
        assert rest is not None
        assert rest.value == "Do Something"

    def test_single_word_no_split(self) -> None:
        ns = _mock_namespace(None)
        token = _make_token("Keyword")
        bdd, rest = ModelHelper.split_bdd_prefix(ns, token)
        assert bdd is None
        assert rest is not None
        assert rest.value == "Keyword"

    @pytest.mark.skipif(RF_VERSION < (6, 0), reason="Language support requires RF >= 6.0")
    @pytest.mark.parametrize(
        ("text", "expected_prefix", "expected_rest"),
        [
            ("Et que My Keyword", "Et que", "My Keyword"),
            ("Et My Keyword", "Et", "My Keyword"),
            ("Étant donné que My Keyword", "Étant donné que", "My Keyword"),
            ("Étant donné My Keyword", "Étant donné", "My Keyword"),
            ("Mais que My Keyword", "Mais que", "My Keyword"),
            ("Mais My Keyword", "Mais", "My Keyword"),
            ("Sachant que My Keyword", "Sachant que", "My Keyword"),
            ("Sachant My Keyword", "Sachant", "My Keyword"),
        ],
    )
    def test_french_split(self, text: str, expected_prefix: str, expected_rest: str) -> None:
        ns = _mock_namespace(FRENCH_BDD_PREFIXES)
        token = _make_token(text)
        bdd, rest = ModelHelper.split_bdd_prefix(ns, token)
        assert bdd is not None, f"Should find BDD prefix in '{text}'"
        assert bdd.value.lower() == expected_prefix.lower(), f"Expected prefix '{expected_prefix}', got '{bdd.value}'"
        assert rest is not None
        assert rest.value == expected_rest
        assert rest.col_offset == len(expected_prefix) + 1

    @pytest.mark.skipif(RF_VERSION < (6, 0), reason="Language support requires RF >= 6.0")
    def test_french_no_prefix(self) -> None:
        ns = _mock_namespace(FRENCH_BDD_PREFIXES)
        token = _make_token("My Keyword")
        bdd, rest = ModelHelper.split_bdd_prefix(ns, token)
        assert bdd is None
        assert rest is not None
        assert rest.value == "My Keyword"


class TestModelHelperStripBddPrefix:
    def test_english_default(self) -> None:
        ns = _mock_namespace(None)
        token = _make_token("Given something happens")
        result = ModelHelper.strip_bdd_prefix(ns, token)
        assert result.value == "something happens"
        assert result.col_offset == 6

    def test_no_prefix_unchanged(self) -> None:
        ns = _mock_namespace(None)
        token = _make_token("Do Something")
        result = ModelHelper.strip_bdd_prefix(ns, token)
        assert result.value == "Do Something"

    @pytest.mark.skipif(RF_VERSION < (6, 0), reason="Language support requires RF >= 6.0")
    @pytest.mark.parametrize(
        ("text", "expected_rest"),
        [
            ("Et que My Keyword", "My Keyword"),
            ("Et My Keyword", "My Keyword"),
            ("Étant donné que My Keyword", "My Keyword"),
            ("Mais que My Keyword", "My Keyword"),
        ],
    )
    def test_french_strip(self, text: str, expected_rest: str) -> None:
        ns = _mock_namespace(FRENCH_BDD_PREFIXES)
        token = _make_token(text)
        result = ModelHelper.strip_bdd_prefix(ns, token)
        assert result.value == expected_rest


class TestModelHelperIsBddToken:
    @pytest.mark.skipif(RF_VERSION < (6, 0), reason="Language support requires RF >= 6.0")
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Et", True),
            ("Et Que", True),
            ("Mais", True),
            ("Mais Que", True),
            ("Étant Donné", True),
            ("Étant Donné Que", True),
            ("Sachant", True),
            ("Sachant Que", True),
            ("Lorsque", True),
            ("NotAPrefix", False),
            ("Et que keyword", False),
        ],
    )
    def test_french_is_bdd_token(self, text: str, expected: bool) -> None:
        ns = _mock_namespace(FRENCH_BDD_PREFIXES)
        token = _make_token(text)
        assert ModelHelper.is_bdd_token(ns, token) == expected, f"is_bdd_token('{text}') should be {expected}"

    def test_english_default(self) -> None:
        ns = _mock_namespace(None)
        for prefix in ["Given", "When", "Then", "And", "But"]:
            token = _make_token(prefix)
            assert ModelHelper.is_bdd_token(ns, token) is True, f"'{prefix}' should be a BDD token"

        token = _make_token("NotBdd")
        assert ModelHelper.is_bdd_token(ns, token) is False

    @pytest.mark.skipif(RF_VERSION < (6, 0), reason="Language support requires RF >= 6.0")
    def test_german_prefixes(self) -> None:
        ns = _mock_namespace(GERMAN_BDD_PREFIXES)
        for prefix in ["Angenommen", "Wenn", "Dann", "Und", "Aber"]:
            token = _make_token(prefix)
            assert ModelHelper.is_bdd_token(ns, token) is True, f"'{prefix}' should be a BDD token"
