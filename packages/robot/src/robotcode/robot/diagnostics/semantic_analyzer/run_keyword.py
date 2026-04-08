"""Layered Run Keyword detection strategy.

Detection layers (checked in order):
1. Type Hints - RF 7.4+ KeywordName/KeywordArgument type annotations
2. RUN_KW_REGISTER - Robot Framework's built-in keyword register
3. Hardcoded - known Run Keyword variants from library_doc.py

Determines which arguments of a keyword are themselves keyword names
(inner keywords) vs. regular arguments. Critical for correct inner keyword
resolution and RunKeywordCallStatement.inner_calls construction.
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..library_doc import KeywordDoc


class KeywordArgumentStrategy(Enum):
    """Which detection layer identified this as a Run Keyword variant."""

    TYPE_HINTS = "type_hints"
    REGISTERED = "registered"
    HARDCODED = "hardcoded"


def get_keyword_argument_strategy(keyword_doc: "KeywordDoc") -> Optional[KeywordArgumentStrategy]:
    """Determine which detection layer applies for a given keyword.

    Returns None if the keyword is a regular keyword (not a Run Keyword variant).
    Layers are checked in priority order — first match wins.
    """
    # Layer 1: Type hint detection (RF 7.4+)
    # Any argument annotated with KeywordName or KeywordArgument signals that
    # this keyword executes other keywords. Works for any library, not just BuiltIn.
    if any(arg.is_keyword_name or arg.is_keyword_argument for arg in keyword_doc.arguments):
        return KeywordArgumentStrategy.TYPE_HINTS

    # Layer 2: RUN_KW_REGISTER
    # Third-party libraries that called register_run_keyword() at import time.
    if keyword_doc.is_registered_run_keyword:
        return KeywordArgumentStrategy.REGISTERED

    # Layer 3: Hardcoded name lists (BuiltIn fallback for RF < 7.4)
    if keyword_doc.is_any_run_keyword():
        return KeywordArgumentStrategy.HARDCODED

    return None
