"""Read-only JSON serialization of a built `SemanticModel`.

Developer/diagnostic surface: `model_to_dict` converts the complete model —
block tree, flat statement list with full token trees, file scope, and
per-definition local scopes — into a JSON-compatible dict for manual
inspection and diffing. The output is deterministic (stable ordering,
workspace-relative sources, no object identities) and is NOT designed to be
deserialized back into a model. The format carries no stability guarantee.

The walkers are explicit per class instead of `dataclasses.asdict` because
`parent` back-pointers create cycles, resolved references must become compact
stubs, and enums serialize as names. `_SERIALIZED_FIELDS` / `_SKIPPED_FIELDS`
document that contract per class; a drift-guard test compares them against
`dataclasses.fields()` so new node fields cannot be forgotten silently.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, List, Optional, Tuple

from .model import SemanticModel
from .nodes import (
    DefinitionBlock,
    DefinitionStatement,
    ExceptStatement,
    ForBlock,
    ForStatement,
    GroupBlock,
    IfBlock,
    IfStatement,
    ImportStatement,
    InlineIfStatement,
    KeywordCallStatement,
    ReturnStatement,
    RunKeywordCallStatement,
    SemanticBlock,
    SemanticNode,
    SemanticStatement,
    SemanticToken,
    SettingStatement,
    TemplateDataStatement,
    TryBlock,
    VarStatement,
    WhileBlock,
    WhileStatement,
)

if TYPE_CHECKING:
    from ..entities import LibraryEntry, VariableDefinition
    from ..library_doc import ArgumentSpec, KeywordDoc

_RelFn = Callable[[Optional[str]], Optional[str]]

# Per-class contract of the dump format: which dataclass fields (declared on
# that class itself, not inherited) appear in the output and which are
# intentionally left out. Checked against `dataclasses.fields()` by the
# drift-guard test.
_SERIALIZED_FIELDS: Dict[type, FrozenSet[str]] = {
    SemanticToken: frozenset({"kind", "value", "line", "col_offset", "length", "sub_tokens", "modifiers"}),
    SemanticNode: frozenset({"kind", "line_start", "line_end"}),
    SemanticStatement: frozenset({"tokens"}),
    KeywordCallStatement: frozenset({"keyword_doc", "lib_entry", "assign_variables"}),
    RunKeywordCallStatement: frozenset({"inner_calls"}),
    ForStatement: frozenset(),
    WhileStatement: frozenset(),
    IfStatement: frozenset(),
    InlineIfStatement: frozenset({"condition", "assign_variable"}),
    ExceptStatement: frozenset(),
    VarStatement: frozenset({"variable_name", "scope", "separator", "values"}),
    ReturnStatement: frozenset({"return_values"}),
    ImportStatement: frozenset({"import_type", "import_name", "alias", "arguments", "lib_entry", "init_keyword_doc"}),
    SettingStatement: frozenset({"setting_name", "argument_definitions", "tag_values"}),
    DefinitionStatement: frozenset({"name", "arguments_spec", "return_type", "tags", "local_variables"}),
    TemplateDataStatement: frozenset({"template_keyword_doc"}),
    SemanticBlock: frozenset({"header", "body"}),
    # `local_variables` of DefinitionBlock appears in the top-level
    # `local_scopes` section instead of inline in the tree.
    DefinitionBlock: frozenset({"name", "arguments_spec", "return_type", "tags", "local_variables"}),
    ForBlock: frozenset({"flavor", "loop_variables", "start", "mode", "fill"}),
    WhileBlock: frozenset({"condition", "limit", "on_limit", "on_limit_message"}),
    IfBlock: frozenset({"condition"}),
    TryBlock: frozenset(),
    GroupBlock: frozenset(),
}

_SKIPPED_FIELDS: Dict[type, FrozenSet[str]] = {
    # `range` is derived from line/col_offset/length in __post_init__.
    SemanticToken: frozenset({"range"}),
    # `parent` back-pointers create cycles; structure is implicit in nesting.
    SemanticNode: frozenset({"parent"}),
}


def model_to_dict(
    model: SemanticModel,
    workspace_root: Optional[Path] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Serialize a built `SemanticModel` into a JSON-compatible dict.

    Read-only: the model is not mutated. `workspace_root` controls source-path
    relativization; sources outside it are rendered as `<external>/<basename>`.
    `source` is the dumped file itself (relativized the same way).
    """
    rel = _make_rel(workspace_root)
    return {
        "source": rel(source),
        "tree": _block(model.root, rel) if model.root is not None else None,
        "statements": [_statement(stmt, rel) for stmt in model.statements],
        "file_scope": _file_scope(model, rel),
        "local_scopes": _local_scopes(model, rel),
    }


def _make_rel(workspace_root: Optional[Path]) -> _RelFn:
    resolved_root = workspace_root.resolve() if workspace_root is not None else None

    def rel(source: Optional[str]) -> Optional[str]:
        if source is None:
            return None
        path = Path(source)
        if resolved_root is not None:
            try:
                return path.resolve().relative_to(resolved_root).as_posix()
            except ValueError:
                pass
        return f"<external>/{path.name}"

    return rel


# --- Tokens ---


def _token(token: SemanticToken) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "kind": token.kind.name,
        "value": token.value,
        "line": token.line,
        "col_offset": token.col_offset,
        "length": token.length,
    }
    if token.modifiers:
        result["modifiers"] = sorted(modifier.name for modifier in token.modifiers)
    if token.sub_tokens:
        result["sub_tokens"] = [_token(sub) for sub in token.sub_tokens]
    return result


def _tokens(tokens: List[SemanticToken]) -> List[Dict[str, Any]]:
    return [_token(token) for token in tokens]


# --- Reference stubs ---


def _range_str(range_: Any) -> str:
    return f"{range_.start.line}:{range_.start.character}-{range_.end.line}:{range_.end.character}"


def _variable_stub(var: "VariableDefinition", rel: _RelFn) -> Dict[str, Any]:
    return {
        "class": type(var).__name__,
        "name": var.name,
        "type": var.type.name,
        "range": _range_str(var.range),
        "source": rel(var.source),
    }


def _keyword_stub(keyword_doc: Optional["KeywordDoc"], rel: _RelFn) -> Optional[Dict[str, Any]]:
    if keyword_doc is None:
        return None
    return {
        "name": keyword_doc.name,
        "source": rel(keyword_doc.source),
        "line": keyword_doc.line_no,
    }


def _lib_entry_stub(entry: Optional["LibraryEntry"], rel: _RelFn) -> Optional[Dict[str, Any]]:
    if entry is None:
        return None
    return {
        "name": entry.name,
        "alias": entry.alias,
        "source": rel(entry.library_doc.source),
    }


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(val) for key, val in value.items()}
    return str(value)


def _argument_spec(spec: Optional["ArgumentSpec"]) -> Optional[Dict[str, Any]]:
    if spec is None:
        return None
    return {
        "name": spec.name,
        "positional_only": list(spec.positional_only),
        "positional_or_named": list(spec.positional_or_named),
        "var_positional": _jsonable(spec.var_positional),
        "named_only": _jsonable(spec.named_only),
        "var_named": _jsonable(spec.var_named),
        "embedded": _jsonable(spec.embedded),
        "defaults": _jsonable(spec.defaults),
        "types": spec.types,
        "return_type": spec.return_type,
    }


def _local_variables(local_variables: List[Tuple["VariableDefinition", int]], rel: _RelFn) -> List[Dict[str, Any]]:
    return [
        {"variable": _variable_stub(var, rel), "visible_from_line": visible_from_line}
        for var, visible_from_line in local_variables
    ]


# --- Statements ---


def _statement(stmt: SemanticStatement, rel: _RelFn) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "kind": stmt.kind.name,
        "class": type(stmt).__name__,
        "line_start": stmt.line_start,
        "line_end": stmt.line_end,
    }

    if isinstance(stmt, KeywordCallStatement):
        result["keyword_doc"] = _keyword_stub(stmt.keyword_doc, rel)
        result["lib_entry"] = _lib_entry_stub(stmt.lib_entry, rel)
        if stmt.assign_variables:
            result["assign_variables"] = _tokens(stmt.assign_variables)
        if isinstance(stmt, RunKeywordCallStatement):
            result["inner_calls"] = [_statement(inner, rel) for inner in stmt.inner_calls]
    elif isinstance(stmt, InlineIfStatement):
        result["condition"] = stmt.condition
        if stmt.assign_variable is not None:
            result["assign_variable"] = _token(stmt.assign_variable)
    elif isinstance(stmt, VarStatement):
        result["variable_name"] = _token(stmt.variable_name) if stmt.variable_name is not None else None
        result["scope"] = stmt.scope.name if stmt.scope is not None else None
        result["separator"] = stmt.separator
        if stmt.values:
            result["values"] = _tokens(stmt.values)
    elif isinstance(stmt, ReturnStatement):
        if stmt.return_values:
            result["return_values"] = _tokens(stmt.return_values)
    elif isinstance(stmt, ImportStatement):
        result["import_type"] = stmt.import_type.name if stmt.import_type is not None else None
        result["import_name"] = stmt.import_name
        result["alias"] = stmt.alias
        if stmt.arguments:
            result["arguments"] = _tokens(stmt.arguments)
        result["lib_entry"] = _lib_entry_stub(stmt.lib_entry, rel)
        result["init_keyword_doc"] = _keyword_stub(stmt.init_keyword_doc, rel)
    elif isinstance(stmt, SettingStatement):
        result["setting_name"] = stmt.setting_name
        if stmt.argument_definitions:
            result["argument_definitions"] = _tokens(stmt.argument_definitions)
        if stmt.tag_values:
            result["tag_values"] = list(stmt.tag_values)
    elif isinstance(stmt, DefinitionStatement):
        result["name"] = stmt.name
        result["arguments_spec"] = _argument_spec(stmt.arguments_spec)
        result["return_type"] = stmt.return_type
        if stmt.tags:
            result["tags"] = list(stmt.tags)
        # Populated only in legacy flat mode (no tree); tree mode keeps local
        # variables on the DefinitionBlock, dumped under `local_scopes`.
        if stmt.local_variables:
            result["local_variables"] = _local_variables(stmt.local_variables, rel)
    elif isinstance(stmt, TemplateDataStatement):
        result["template_keyword_doc"] = _keyword_stub(stmt.template_keyword_doc, rel)

    result["tokens"] = _tokens(stmt.tokens)
    return result


# --- Blocks ---


def _block(block: SemanticBlock, rel: _RelFn) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "kind": block.kind.name,
        "class": type(block).__name__,
        "line_start": block.line_start,
        "line_end": block.line_end,
    }

    if isinstance(block, DefinitionBlock):
        result["name"] = block.name
        result["arguments_spec"] = _argument_spec(block.arguments_spec)
        result["return_type"] = block.return_type
        if block.tags:
            result["tags"] = list(block.tags)
    elif isinstance(block, ForBlock):
        result["flavor"] = block.flavor.name if block.flavor is not None else None
        result["loop_variables"] = _tokens(block.loop_variables)
        result["start"] = block.start
        result["mode"] = block.mode.name if block.mode is not None else None
        result["fill"] = block.fill
    elif isinstance(block, WhileBlock):
        result["condition"] = block.condition
        result["limit"] = block.limit
        result["on_limit"] = block.on_limit.name if block.on_limit is not None else None
        result["on_limit_message"] = block.on_limit_message
    elif isinstance(block, IfBlock):
        result["condition"] = block.condition

    result["header"] = _statement(block.header, rel) if block.header is not None else None
    body: List[Dict[str, Any]] = []
    for child in block.body:
        if isinstance(child, SemanticBlock):
            body.append(_block(child, rel))
        elif isinstance(child, SemanticStatement):
            body.append(_statement(child, rel))
    result["body"] = body
    return result


# --- Scopes ---


def _file_scope(model: SemanticModel, rel: _RelFn) -> Optional[Dict[str, Any]]:
    scope = model.file_scope
    if scope is None:
        return None
    return {
        "command_line": [_variable_stub(var, rel) for var in scope.command_line_variables],
        "own": [_variable_stub(var, rel) for var in scope.own_variables],
        "imported": [_variable_stub(var, rel) for var in scope.imported_variables],
        "builtin": [_variable_stub(var, rel) for var in scope.builtin_variables],
    }


def _iter_definition_blocks(block: SemanticBlock) -> List[DefinitionBlock]:
    result: List[DefinitionBlock] = []
    for child in block.body:
        if isinstance(child, DefinitionBlock):
            result.append(child)
        if isinstance(child, SemanticBlock):
            result.extend(_iter_definition_blocks(child))
    return result


def _local_scopes(model: SemanticModel, rel: _RelFn) -> List[Dict[str, Any]]:
    if model.root is None:
        return []
    return [
        {
            "name": definition.name,
            "line_start": definition.line_start,
            "line_end": definition.line_end,
            "local_variables": _local_variables(definition.local_variables, rel),
        }
        for definition in _iter_definition_blocks(model.root)
    ]
