"""Pickle support for the Semantic Model.

Provides resolve_references() for post-unpickle resolution of
stable_id strings back to live objects, and pickle helper utilities.

The SemanticModel is designed to be pickle-friendly:
- SemanticToken is a pure value object (no live references) - pickles natively
- SemanticStatement subclasses hold keyword_doc/lib_entry references which
  are live objects that cannot survive pickle/unpickle across sessions

For serialization:
1. Before pickling: replace live object references with stable_id strings
2. Pickle normally
3. After unpickling: call resolve_references() to restore live objects
"""

from typing import TYPE_CHECKING, Dict, Optional

from .nodes import (
    DefinitionBlock,
    DefinitionStatement,
    ImportStatement,
    KeywordCallStatement,
    RunKeywordCallStatement,
    SemanticBlock,
    SemanticStatement,
)

if TYPE_CHECKING:
    from ..entities import LibraryEntry
    from ..library_doc import KeywordDoc
    from .model import SemanticModel


def resolve_references(
    model: "SemanticModel",
    kw_by_id: Dict[str, "KeywordDoc"],
    entry_by_key: Dict[str, "LibraryEntry"],
) -> None:
    """Resolve stable_id strings back to live objects after unpickling.

    After unpickling a SemanticModel, keyword_doc and lib_entry fields
    contain stable_id strings instead of live objects. This function
    walks the model and replaces them with the actual objects from the
    provided lookup dicts.

    Args:
        model: The unpickled SemanticModel to resolve.
        kw_by_id: Mapping from KeywordDoc.stable_id to live KeywordDoc.
        entry_by_key: Mapping from LibraryEntry key to live LibraryEntry.
    """
    for stmt in model.statements:
        _resolve_statement(stmt, kw_by_id, entry_by_key)

    # Also resolve references in tree structure (blocks)
    if model.root is not None:
        _resolve_block(model.root, kw_by_id, entry_by_key)


def _resolve_block(
    block: SemanticBlock,
    kw_by_id: Dict[str, "KeywordDoc"],
    entry_by_key: Dict[str, "LibraryEntry"],
) -> None:
    """Resolve references in a block and its children."""
    if block.header is not None:
        _resolve_statement(block.header, kw_by_id, entry_by_key)
    if isinstance(block, DefinitionBlock):
        if isinstance(block.arguments_spec, str):
            block.arguments_spec = None  # type: ignore[unreachable]
    for child in block.body:
        if isinstance(child, SemanticStatement):
            _resolve_statement(child, kw_by_id, entry_by_key)
        elif isinstance(child, SemanticBlock):
            _resolve_block(child, kw_by_id, entry_by_key)


def _resolve_statement(
    stmt: SemanticStatement,
    kw_by_id: Dict[str, "KeywordDoc"],
    entry_by_key: Dict[str, "LibraryEntry"],
) -> None:
    """Resolve references in a single statement."""
    if isinstance(stmt, KeywordCallStatement):
        _resolve_keyword_call(stmt, kw_by_id, entry_by_key)
    elif isinstance(stmt, ImportStatement):
        stmt.lib_entry = _resolve_entry(stmt.lib_entry, entry_by_key)
    elif isinstance(stmt, DefinitionStatement):
        if isinstance(stmt.arguments_spec, str):
            # arguments_spec should not be serialized as string,
            # but handle gracefully
            stmt.arguments_spec = None  # type: ignore[unreachable]


def _resolve_keyword_call(
    stmt: KeywordCallStatement,
    kw_by_id: Dict[str, "KeywordDoc"],
    entry_by_key: Dict[str, "LibraryEntry"],
) -> None:
    """Resolve references in a keyword call statement."""
    if isinstance(stmt.keyword_doc, str):
        stmt.keyword_doc = kw_by_id.get(stmt.keyword_doc)  # type: ignore[unreachable]

    stmt.lib_entry = _resolve_entry(stmt.lib_entry, entry_by_key)

    if isinstance(stmt, RunKeywordCallStatement):
        for inner in stmt.inner_calls:
            _resolve_keyword_call(inner, kw_by_id, entry_by_key)


def _resolve_entry(
    entry: Optional["LibraryEntry"],
    entry_by_key: Dict[str, "LibraryEntry"],
) -> Optional["LibraryEntry"]:
    """Resolve a single library entry reference."""
    if isinstance(entry, str):
        return entry_by_key.get(entry)  # type: ignore[unreachable]
    return entry
