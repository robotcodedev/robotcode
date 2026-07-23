import ast
from concurrent.futures import CancelledError
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    cast,
)

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import Statement

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    MarkupContent,
    MarkupKind,
    ParameterInformation,
    Position,
    SignatureHelp,
    SignatureHelpContext,
    SignatureInformation,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.library_doc import (
    ArgumentInfo,
    KeywordArgumentKind,
    KeywordDoc,
    LibraryDoc,
)
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, NodeKind, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    ImportStatement,
    KeywordCallStatement,
    SemanticStatement,
    SemanticToken,
)
from robotcode.robot.utils.ast import (
    get_node_at_position,
    get_tokens_at_position,
    range_from_token,
)

from ...common.decorators import (
    retrigger_characters,
    trigger_characters,
)
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

_SignatureHelpMethod = Callable[
    [ast.AST, TextDocument, Position, Optional[SignatureHelpContext]],
    Optional[SignatureHelp],
]


# --- Pure helpers used by the model-based path ---


def _is_named_arg(tok: SemanticToken) -> bool:
    """An ARGUMENT SemanticToken whose first sub_token is NAMED_ARGUMENT_NAME
    (the analyzer pre-detects `name=value` syntax). Cheaper than
    `split_from_equals` at request time."""
    return bool(tok.sub_tokens and any(st.kind is TokenKind.NAMED_ARGUMENT_NAME for st in tok.sub_tokens))


def _is_dict_or_list_spread(tok: SemanticToken) -> bool:
    """Detect `@{vars}` / `&{vars}` spread arguments — they collapse to
    "could be anything" and force VAR_NAMED on subsequent positional slots
    (matches legacy `get_argument_info_at_position`'s `need_named` branch)."""
    return tok.value.startswith(("@{", "&{")) and tok.value.endswith("}")


def _named_arg_name(tok: SemanticToken) -> Optional[str]:
    """The `name` part of a `name=value` ARGUMENT token, or None if not
    a named argument."""
    if not tok.sub_tokens:
        return None
    name_st = next((st for st in tok.sub_tokens if st.kind is TokenKind.NAMED_ARGUMENT_NAME), None)
    return name_st.value if name_st is not None else None


def _active_argument_from_semantic_tokens(
    arg_tokens: List[SemanticToken],
    kw_doc: KeywordDoc,
    position: Position,
) -> Tuple[int, List[ArgumentInfo]]:
    """Compute `(argument_index, kw_arguments)` for cursor at `position`.

    SemanticModel-based replacement for the legacy
    `ModelHelper.get_argument_info_at_position`. The return tuple matches
    the legacy two relevant fields — `argument_token` was unused by the
    signature-help caller, so it's dropped here.

    `argument_index = -1` means "cursor isn't on a positional slot we can
    map to a parameter" — caller still builds a SignatureHelp but with
    `active_parameter = -1` (legacy parity).
    """
    kw_arguments = [
        a
        for a in kw_doc.arguments
        if a.kind
        not in (
            KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
            KeywordArgumentKind.NAMED_ONLY_MARKER,
        )
    ]
    if not kw_arguments:
        return -1, kw_arguments

    # Locate which "slot" the cursor sits in. Slot N means "the cursor is
    # logically on the Nth ARGUMENT position" — N may be `len(arg_tokens)`
    # when the cursor is in trailing whitespace past the last arg.
    slot: int = -1
    cursor_token: Optional[SemanticToken] = None

    for i, tok in enumerate(arg_tokens):
        if position in tok.range:
            slot = i
            cursor_token = tok
            break

        if not position < tok.range.start:
            continue

        # Cursor falls in the gap before this arg. Determine whether it's
        # already "in this slot" or still hugging the previous arg.
        if i == 0:
            slot = 0
            cursor_token = None
        else:
            prev = arg_tokens[i - 1]
            if tok.range.start.line != prev.range.end.line:
                # Different line → cursor is past the previous arg's end;
                # it belongs to the slot of `tok`.
                slot = i
                cursor_token = None
            else:
                gap = tok.range.start.character - prev.range.end.character
                # In RF, valid separators are ≥ 2 spaces or 1 tab. Tab
                # collapses to a 1-char gap, spaces to ≥ 2. The cursor
                # crosses into the next slot once it's past the *minimum*
                # separator (1 char for tab, 2 chars for spaces).
                threshold = prev.range.end.character + (1 if gap == 1 else 2)
                if position.character >= threshold:
                    slot = i
                    cursor_token = None
                else:
                    slot = i - 1
                    cursor_token = prev
        break
    else:
        # Cursor is past every ARGUMENT token (or there are none).
        if not arg_tokens:
            slot = 0
            cursor_token = None
        else:
            last = arg_tokens[-1]
            if position in last.range:
                slot = len(arg_tokens) - 1
                cursor_token = last
            elif position.line == last.range.end.line:
                # Same line, past last arg's end → stay on the last arg.
                # Legacy walks back from the EOL token to the previous
                # ARGUMENT and reports its index; we mirror that with no
                # SEPARATOR token to drive an "advance" decision.
                slot = len(arg_tokens) - 1
                cursor_token = last
            else:
                # Different line from the last arg (continuation line) —
                # cursor isn't reliably mappable to a slot without the
                # CONTINUATION / EOL tokens; bail out as -1.
                slot = -1
                cursor_token = None

    # Cursor inside an `@{vars}` / `&{vars}` spread — there's no specific
    # parameter to highlight (legacy returns -1 here too).
    if cursor_token is not None and _is_dict_or_list_spread(cursor_token):
        return -1, kw_arguments

    # Named arg under cursor → look up by name. If the name doesn't match a
    # declared parameter, fall back to VAR_NAMED if present.
    if cursor_token is not None:
        name = _named_arg_name(cursor_token)
        if name is not None:
            idx = next((j for j, a in enumerate(kw_arguments) if a.name == name), -1)
            if idx >= 0:
                return idx, kw_arguments
            return (
                next(
                    (j for j, a in enumerate(kw_arguments) if a.kind == KeywordArgumentKind.VAR_NAMED),
                    -1,
                ),
                kw_arguments,
            )

    # `need_named`: once a previous positional slot was filled with a
    # `name=value` arg or a spread, every subsequent slot must also be
    # named (positional ordering is broken).
    need_named = any(
        _is_named_arg(prev) or _is_dict_or_list_spread(prev) for prev in arg_tokens[: min(slot, len(arg_tokens))]
    )

    if slot < 0:
        return -1, kw_arguments

    # Within positional range and no named-only mode required → use the slot.
    if slot < len(kw_arguments) and not need_named:
        kind = kw_arguments[slot].kind
        if kind in (
            KeywordArgumentKind.POSITIONAL_ONLY,
            KeywordArgumentKind.POSITIONAL_OR_NAMED,
        ):
            return slot, kw_arguments

    # Past the named slots, or named mode required → land on the catch-all.
    if need_named:
        idx = next(
            (j for j, a in enumerate(kw_arguments) if a.kind == KeywordArgumentKind.VAR_NAMED),
            -1,
        )
    else:
        idx = next(
            (j for j, a in enumerate(kw_arguments) if a.kind == KeywordArgumentKind.VAR_POSITIONAL),
            -1,
        )
    return idx, kw_arguments


def _cursor_within_line_extent(stmt: SemanticStatement, position: Position) -> bool:
    """Cursor is at or before the rightmost SemanticToken end on its line
    (with a +1 grace covering the EOL token that the SemanticModel filters
    out). Mirrors the legacy `get_tokens_at_position()` returning empty
    when the cursor is past every token of a node — signature help is
    suppressed in that case."""
    line1 = position.line + 1  # SemanticToken.line is 1-indexed
    rightmost = max(
        (t.range.end.character for t in stmt.tokens if t.line == line1),
        default=-1,
    )
    if rightmost < 0:
        return False
    return position.character <= rightmost + 1


def _cursor_past_keyword_name(stmt: KeywordCallStatement, position: Position) -> bool:
    """Cursor is at or past `KEYWORD.range.end + 2` (the legacy 2-char grace
    period that lets the user finish typing the name + one space before a
    signature popup appears)."""
    keyword_tok = next((t for t in stmt.tokens if t.kind is TokenKind.KEYWORD), None)
    if keyword_tok is None:
        return False
    return position >= keyword_tok.range.extend(end_character=2).end


def _with_name_marker(stmt: ImportStatement) -> Optional[SemanticToken]:
    """The `WITH NAME` / `AS` alias marker: the SETTING_IMPORT token after the
    import path (the import word itself is SETTING_IMPORT too, but precedes
    the IMPORT_NAME token)."""
    seen_import_name = False
    for tok in stmt.tokens:
        if tok.kind is TokenKind.IMPORT_NAME:
            seen_import_name = True
        elif seen_import_name and tok.kind is TokenKind.SETTING_IMPORT:
            return tok
    return None


def _cursor_at_or_past_with_name(stmt: ImportStatement, position: Position) -> bool:
    """Cursor is at or past the WITH NAME marker on a Library import —
    past here means the user is on the alias, not on the library args,
    so signature help should be suppressed."""
    with_name_tok = _with_name_marker(stmt)
    if with_name_tok is None:
        return False
    return position >= with_name_tok.range.start


def _cursor_past_import_name(stmt: ImportStatement, position: Position) -> bool:
    """Cursor is strictly past `IMPORT_NAME.range.end + 1` — same `+ 1`
    grace legacy uses for `LibraryImport.NAME` / `VariablesImport.NAME`."""
    if not stmt.import_name:
        return False
    name_tok = next((t for t in stmt.tokens if t.kind is TokenKind.IMPORT_NAME), None)
    if name_tok is None:
        return False
    return position > name_tok.range.extend(end_character=1).end


def _import_arg_tokens(stmt: ImportStatement) -> List[SemanticToken]:
    """ARGUMENT SemanticTokens of an import statement up to (but excluding)
    the optional `WITH NAME` marker. Anything past WITH NAME is the alias
    and is not part of the init signature."""
    marker = _with_name_marker(stmt)
    out: List[SemanticToken] = []
    for tok in stmt.tokens:
        if marker is not None and tok is marker:
            break
        if tok.kind is TokenKind.ARGUMENT:
            out.append(tok)
    return out


def _build_signature_help(
    kw_doc: KeywordDoc,
    arg_tokens: List[SemanticToken],
    position: Position,
) -> Optional[SignatureHelp]:
    """SemanticModel-based replacement for `_get_signature_help`.

    Renders one `SignatureInformation` from the keyword's parameter spec
    and marks the parameter the cursor is on as active. Pure function so
    it can be unit-tested without the LSP protocol stack.
    """
    argument_index, kw_arguments = _active_argument_from_semantic_tokens(arg_tokens, kw_doc, position)
    if not kw_arguments:
        return None

    signature = SignatureInformation(
        label=kw_doc.parameter_signature(),
        parameters=[
            ParameterInformation(
                label=p.signature(),
                documentation=(
                    MarkupContent(
                        kind=MarkupKind.MARKDOWN,
                        value="\n\n---\n\n".join(t.to_markdown() for t in kw_doc.parent.get_types(p.types)),
                    )
                    if p.types and kw_doc.parent is not None
                    else None
                ),
            )
            for p in kw_arguments
        ],
        active_parameter=argument_index,
        documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=kw_doc.to_markdown(False)),
    )
    return SignatureHelp(
        signatures=[signature],
        active_signature=0,
        active_parameter=argument_index,
    )


class RobotSignatureHelpProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.signature_help.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_SignatureHelpMethod]:
        if cls is ast.AST:
            return None
        method_name = "signature_help_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_SignatureHelpMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return method
        return None

    @language_id("robotframework")
    @trigger_characters([" ", "\t"])
    @retrigger_characters([" ", "\t"])
    @_logger.call
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        namespace = self.parent.documents_cache.get_namespace(document)

        # Tier 2 model-based path — used when the experimental SemanticAnalyzer
        # is enabled (semantic_model is populated). The arg-index math still
        # uses the RF token list (battle-tested via `get_argument_info_at_position`);
        # the model's contribution is skipping the second `find_keyword` /
        # libdoc lookup and reading the pre-resolved `keyword_doc` /
        # `init_keyword_doc` directly off the statement.
        semantic_model = namespace.semantic_model
        if semantic_model is not None:
            return self._collect_from_model(document, position, namespace, semantic_model)

        return self._collect_legacy(document, position, context)

    def _collect_legacy(
        self,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext],
    ) -> Optional[SignatureHelp]:
        result_node = get_node_at_position(
            self.parent.documents_cache.get_model(document),
            position,
            include_end=True,
        )
        if result_node is None:
            return None

        method = self._find_method(type(result_node))
        if method is None:
            return None

        return method(result_node, document, position, context)

    # ------------------------------------------------------------------
    # Tier 2 model-based collection
    # ------------------------------------------------------------------

    def _collect_from_model(
        self,
        document: TextDocument,
        position: Position,
        namespace: Namespace,
        model: SemanticModel,
    ) -> Optional[SignatureHelp]:
        """Pure SemanticModel path: dispatch by SemanticStatement type, read
        the pre-resolved `keyword_doc` / `init_keyword_doc`, and compute the
        active parameter from SemanticTokens. No AST walks, no `find_keyword`,
        no `ModelHelper` calls."""
        # SemanticModel uses 1-indexed lines; LSP positions are 0-indexed.
        stmt = model.statement_at(position.line + 1)
        if stmt is None:
            return None

        if isinstance(stmt, KeywordCallStatement):
            return self._keyword_call_signature_help(stmt, position)

        if isinstance(stmt, ImportStatement) and stmt.import_type in (
            ImportType.LIBRARY,
            ImportType.VARIABLES,
        ):
            return self._import_signature_help(stmt, position)

        return None

    # NodeKinds for which signature help is offered. Legacy has handlers for
    # `signature_help_KeywordCall` (KEYWORD_CALL) and `signature_help_Fixture`
    # (SETUP / TEARDOWN). TEMPLATE_KEYWORD (TestTemplate / Template) has no
    # legacy handler, so the model path must skip it for parity.
    _SUPPORTED_KEYWORD_CALL_KINDS: frozenset[NodeKind] = frozenset(
        {NodeKind.KEYWORD_CALL, NodeKind.SETUP, NodeKind.TEARDOWN}
    )

    def _keyword_call_signature_help(
        self,
        stmt: KeywordCallStatement,
        position: Position,
    ) -> Optional[SignatureHelp]:
        if stmt.kind not in self._SUPPORTED_KEYWORD_CALL_KINDS:
            return None

        kw_doc = stmt.keyword_doc
        if kw_doc is None:
            return None

        # Suppress the popup while the cursor is still on the keyword name
        # (legacy uses a 2-char grace past the keyword end so the user can
        # finish typing the keyword + the first separator space).
        if not _cursor_past_keyword_name(stmt, position):
            return None

        # Cursor past every visible token on its line → no popup (mirrors
        # legacy `get_tokens_at_position` returning empty in that case).
        if not _cursor_within_line_extent(stmt, position):
            return None

        arg_tokens = [t for t in stmt.tokens if t.kind is TokenKind.ARGUMENT]
        return _build_signature_help(kw_doc, arg_tokens, position)

    def _import_signature_help(
        self,
        stmt: ImportStatement,
        position: Position,
    ) -> Optional[SignatureHelp]:
        kw_doc = stmt.init_keyword_doc
        if kw_doc is None:
            return None

        # Cursor must be past the import path (legacy: `+ 1` grace past
        # the NAME end, exclusive lower bound matches `position <= …` legacy
        # check via the `>` we use here).
        if not _cursor_past_import_name(stmt, position):
            return None

        # WITH NAME (Library imports only) — anything from the marker onward
        # is the alias, not the init signature.
        if _cursor_at_or_past_with_name(stmt, position):
            return None

        return _build_signature_help(kw_doc, _import_arg_tokens(stmt), position)

    def _signature_help_KeywordCall_or_Fixture(  # noqa: N802
        self,
        keyword_name_token_type: str,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        kw_node = cast(Statement, node)

        tokens_at_position = get_tokens_at_position(kw_node, position, include_end=True)

        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [
            RobotToken.ARGUMENT,
            RobotToken.EOL,
            RobotToken.SEPARATOR,
        ]:
            return None

        keyword_doc_and_token: Optional[Tuple[Optional[KeywordDoc], Token]] = None

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        keyword_doc_and_token = self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            [t for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            range_from_token(keyword_token).end,
            analyse_run_keywords=False,
        )

        if keyword_doc_and_token is None:
            return None

        keyword_doc, keyword_token = keyword_doc_and_token
        if keyword_doc is None:
            return None

        if keyword_token is not None and position < range_from_token(keyword_token).extend(end_character=2).end:
            return None

        if keyword_doc.is_any_run_keyword():
            # TODO
            pass

        return self._get_signature_help(keyword_doc, kw_node.tokens, token_at_position, position)

    def _get_signature_help(
        self,
        keyword_doc: KeywordDoc,
        tokens: Sequence[Token],
        token_at_position: Token,
        position: Position,
    ) -> Optional[SignatureHelp]:
        argument_index, kw_arguments, _ = self.get_argument_info_at_position(
            keyword_doc, tokens, token_at_position, position
        )
        if kw_arguments is None:
            return None

        signature = SignatureInformation(
            label=keyword_doc.parameter_signature(),
            parameters=[
                ParameterInformation(
                    label=p.signature(),
                    documentation=(
                        MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value="\n\n---\n\n".join([t.to_markdown() for t in keyword_doc.parent.get_types(p.types)]),
                        )
                        if p.types and keyword_doc.parent is not None
                        else None
                    ),
                )
                for i, p in enumerate(kw_arguments)
            ],
            active_parameter=argument_index,
            documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=keyword_doc.to_markdown(False)),
        )

        return SignatureHelp(
            signatures=[signature],
            active_signature=0,
            active_parameter=argument_index,
        )

    def signature_help_KeywordCall(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        return self._signature_help_KeywordCall_or_Fixture(RobotToken.KEYWORD, node, document, position, context)

    def signature_help_Fixture(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        name_token = cast(Fixture, node).get_token(RobotToken.NAME)
        if name_token is None or name_token.value is None or name_token.value.upper() in ("", "NONE"):
            return None

        return self._signature_help_KeywordCall_or_Fixture(RobotToken.NAME, node, document, position, context)

    def signature_help_LibraryImport(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        library_node = cast(LibraryImport, node)

        if (
            not library_node.name
            or position <= range_from_token(library_node.get_token(RobotToken.NAME)).extend(end_character=1).end
        ):
            return None

        lib_doc: Optional[LibraryDoc] = None
        try:
            namespace = self.parent.documents_cache.get_namespace(document)

            lib_doc = namespace.get_imported_library_libdoc(library_node.name, library_node.args, library_node.alias)

            if lib_doc is None or lib_doc.errors:
                lib_doc = namespace.imports_manager.get_libdoc_for_library_import(
                    str(library_node.name),
                    (),
                    str(document.uri.to_path().parent),
                    variables=namespace.get_resolvable_variables(),
                )

        except (CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return None

        with_name_token = next((v for v in library_node.tokens if v.value == "WITH NAME"), None)
        if with_name_token is not None and position >= range_from_token(with_name_token).start:
            return None

        tokens_at_position = tokens_at_position = get_tokens_at_position(library_node, position)
        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [
            RobotToken.ARGUMENT,
            RobotToken.EOL,
            RobotToken.SEPARATOR,
        ]:
            return None

        if not lib_doc.inits:
            return None

        tokens = (
            library_node.tokens
            if with_name_token is None
            else library_node.tokens[: library_node.tokens.index(with_name_token)]
        )
        for kw_doc in lib_doc.inits:
            return self._get_signature_help(kw_doc, tokens, token_at_position, position)

        return None

    def signature_help_VariablesImport(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        context: Optional[SignatureHelpContext] = None,
    ) -> Optional[SignatureHelp]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import VariablesImport

        variables_node = cast(VariablesImport, node)

        name_token = variables_node.get_token(RobotToken.NAME)
        if name_token is None:
            return None

        if variables_node.name is None or position <= range_from_token(name_token).extend(end_character=1).end:
            return None

        lib_doc: Optional[LibraryDoc] = None
        try:
            namespace = self.parent.documents_cache.get_namespace(document)

            lib_doc = namespace.get_variables_import_libdoc(variables_node.name, variables_node.args)

            if lib_doc is None or lib_doc.errors:
                lib_doc = namespace.imports_manager.get_libdoc_for_variables_import(
                    str(variables_node.name),
                    (),
                    str(document.uri.to_path().parent),
                    variables=namespace.get_resolvable_variables(),
                )

        except (CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return None

        tokens_at_position = tokens_at_position = get_tokens_at_position(variables_node, position)
        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [
            RobotToken.ARGUMENT,
            RobotToken.EOL,
            RobotToken.SEPARATOR,
        ]:
            return None

        if not lib_doc.inits:
            return None

        for kw_doc in lib_doc.inits:
            return self._get_signature_help(kw_doc, variables_node.tokens, token_at_position, position)

        return None
