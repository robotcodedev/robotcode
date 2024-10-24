from __future__ import annotations

import ast
import re
import token as python_token
from io import StringIO
from tokenize import TokenError, generate_tokens
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from robot.errors import VariableError
from robot.parsing.lexer.tokens import Token
from robot.utils.escaping import unescape
from robot.variables.finders import NOT_FOUND, NumberFinder
from robotcode.core.lsp.types import Position

from ..utils import get_robot_version
from ..utils.ast import (
    iter_over_keyword_names_and_owners,
    range_from_token,
    strip_variable_token,
    tokenize_variables,
    whitespace_at_begin_of_token,
    whitespace_from_begin_of_token,
)
from ..utils.variables import contains_variable, search_variable, split_from_equals
from .entities import (
    LibraryEntry,
    VariableDefinition,
    VariableNotFoundDefinition,
)
from .keyword_finder import DEFAULT_BDD_PREFIXES
from .library_doc import (
    ArgumentInfo,
    KeywordArgumentKind,
    KeywordDoc,
    LibraryDoc,
)

if TYPE_CHECKING:
    from .namespace import Namespace


class ModelHelper:
    @classmethod
    def get_run_keyword_keyworddoc_and_token_from_position(
        cls,
        keyword_doc: Optional[KeywordDoc],
        argument_tokens: List[Token],
        namespace: "Namespace",
        position: Position,
    ) -> Tuple[Optional[Tuple[Optional[KeywordDoc], Token]], List[Token]]:
        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return None, argument_tokens

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0:
            result = cls.get_keyworddoc_and_token_from_position(
                unescape(argument_tokens[0].value),
                argument_tokens[0],
                argument_tokens[1:],
                namespace,
                position,
            )
            return result, argument_tokens[1:]

        if keyword_doc.is_run_keyword_with_condition() and len(argument_tokens) > (
            cond_count := keyword_doc.run_keyword_condition_count()
        ):
            result = cls.get_keyworddoc_and_token_from_position(
                unescape(argument_tokens[cond_count].value),
                argument_tokens[cond_count],
                argument_tokens[cond_count + 1 :],
                namespace,
                position,
            )

            return result, argument_tokens[cond_count + 1 :]

        if keyword_doc.is_run_keywords():
            has_and = False
            while argument_tokens:
                t = argument_tokens[0]
                argument_tokens = argument_tokens[1:]
                if t.value == "AND":
                    continue

                and_token = next((e for e in argument_tokens if e.value == "AND"), None)
                if and_token is not None:
                    args = argument_tokens[: argument_tokens.index(and_token)]
                    has_and = True
                else:
                    if has_and:
                        args = argument_tokens
                    else:
                        args = []

                result = cls.get_keyworddoc_and_token_from_position(unescape(t.value), t, args, namespace, position)
                if result is not None and result[0] is not None:
                    return result, []

                if and_token is not None:
                    argument_tokens = argument_tokens[argument_tokens.index(and_token) + 1 :]
                elif has_and:
                    argument_tokens = []

            return None, []

        if keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1:

            def skip_args() -> None:
                nonlocal argument_tokens

                while argument_tokens:
                    if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                        break
                    argument_tokens = argument_tokens[1:]

            inner_keyword_doc = namespace.find_keyword(argument_tokens[1].value, raise_keyword_error=False)

            if position.is_in_range(range_from_token(argument_tokens[1])):
                return (inner_keyword_doc, argument_tokens[1]), argument_tokens[2:]

            argument_tokens = argument_tokens[2:]

            inner_keyword_doc_and_args = cls.get_run_keyword_keyworddoc_and_token_from_position(
                inner_keyword_doc, argument_tokens, namespace, position
            )

            if inner_keyword_doc_and_args[0] is not None:
                return inner_keyword_doc_and_args

            argument_tokens = inner_keyword_doc_and_args[1]

            skip_args()

            while argument_tokens:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:
                    inner_keyword_doc = namespace.find_keyword(unescape(argument_tokens[1].value))

                    if position.is_in_range(range_from_token(argument_tokens[1])):
                        return (
                            inner_keyword_doc,
                            argument_tokens[1],
                        ), argument_tokens[2:]

                    argument_tokens = argument_tokens[2:]

                    inner_keyword_doc_and_args = cls.get_run_keyword_keyworddoc_and_token_from_position(
                        inner_keyword_doc,
                        argument_tokens,
                        namespace,
                        position,
                    )

                    if inner_keyword_doc_and_args[0] is not None:
                        return inner_keyword_doc_and_args

                    argument_tokens = inner_keyword_doc_and_args[1]

                    skip_args()

                    break
                if argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:
                    inner_keyword_doc = namespace.find_keyword(unescape(argument_tokens[2].value))

                    if position.is_in_range(range_from_token(argument_tokens[2])):
                        return (
                            inner_keyword_doc,
                            argument_tokens[2],
                        ), argument_tokens[3:]

                    argument_tokens = argument_tokens[3:]

                    inner_keyword_doc_and_args = cls.get_run_keyword_keyworddoc_and_token_from_position(
                        inner_keyword_doc,
                        argument_tokens,
                        namespace,
                        position,
                    )

                    if inner_keyword_doc_and_args[0] is not None:
                        return inner_keyword_doc_and_args

                    argument_tokens = inner_keyword_doc_and_args[1]

                    skip_args()
                else:
                    break

        return None, argument_tokens

    @classmethod
    def get_keyworddoc_and_token_from_position(
        cls,
        keyword_name: Optional[str],
        keyword_token: Token,
        argument_tokens: List[Token],
        namespace: "Namespace",
        position: Position,
        analyse_run_keywords: bool = True,
    ) -> Optional[Tuple[Optional[KeywordDoc], Token]]:
        finder = namespace.get_finder()
        keyword_doc = finder.find_keyword(keyword_name, raise_keyword_error=False)
        if keyword_doc is None:
            return None

        if finder.result_bdd_prefix:
            keyword_token = ModelHelper.strip_bdd_prefix(namespace, keyword_token)

        if position.is_in_range(range_from_token(keyword_token)):
            return keyword_doc, keyword_token

        if analyse_run_keywords:
            return (
                cls.get_run_keyword_keyworddoc_and_token_from_position(
                    keyword_doc, argument_tokens, namespace, position
                )
            )[0]

        return None

    @classmethod
    def get_namespace_info_from_keyword_token(
        cls, namespace: "Namespace", keyword_token: Token
    ) -> Tuple[Optional[LibraryEntry], Optional[str]]:
        lib_entry: Optional[LibraryEntry] = None
        kw_namespace: Optional[str] = None

        for lib, keyword in iter_over_keyword_names_and_owners(keyword_token.value):
            if lib is not None:
                lib_entries = next(
                    (v for k, v in (namespace.get_namespaces()).items() if k == lib),
                    None,
                )
                if lib_entries is not None:
                    kw_namespace = lib
                    lib_entry = next(
                        (v for v in lib_entries if keyword in v.library_doc.keywords),
                        lib_entries[0] if lib_entries else None,
                    )
                    break

        return lib_entry, kw_namespace

    match_extended = re.compile(
        r"""
    (.+?)          # base name (group 1)
    ([^\s\w].+)    # extended part (group 2)
    """,
        re.UNICODE | re.VERBOSE,
    )

    @staticmethod
    def iter_expression_variables_from_token(
        expression: Token,
        namespace: "Namespace",
        nodes: Optional[List[ast.AST]],
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        skip_local_variables: bool = False,
        return_not_found: bool = False,
    ) -> Iterator[Tuple[Token, VariableDefinition]]:
        variable_started = False
        try:
            for toknum, tokval, (_, tokcol), _, _ in generate_tokens(StringIO(expression.value).readline):
                if variable_started:
                    if toknum == python_token.NAME:
                        var = namespace.find_variable(
                            f"${{{tokval}}}",
                            nodes,
                            position,
                            skip_commandline_variables=skip_commandline_variables,
                            skip_local_variables=skip_local_variables,
                            ignore_error=True,
                        )
                        sub_token = Token(
                            expression.type,
                            tokval,
                            expression.lineno,
                            expression.col_offset + tokcol,
                            expression.error,
                        )
                        if var is not None:
                            yield sub_token, var
                        elif return_not_found:
                            yield (
                                sub_token,
                                VariableNotFoundDefinition(
                                    sub_token.lineno,
                                    sub_token.col_offset,
                                    sub_token.lineno,
                                    sub_token.end_col_offset,
                                    namespace.source,
                                    f"${{{tokval}}}",
                                    sub_token,
                                ),
                            )
                    variable_started = False
                if tokval == "$":
                    variable_started = True
        except TokenError:
            pass

    @staticmethod
    def remove_index_from_variable_token(
        token: Token,
    ) -> Tuple[Token, Optional[Token]]:
        def escaped(i: int) -> bool:
            return bool(token.value[-i - 3 : -i - 2] == "\\")

        if token.type != Token.VARIABLE or not token.value.endswith("]"):
            return (token, None)

        braces = 1
        curly_braces = 0
        index = 0
        for i, c in enumerate(reversed(token.value[:-1])):
            if c == "}" and not escaped(i):
                curly_braces += 1
            elif c == "{" and not escaped(i):
                curly_braces -= 1
            elif c == "]" and curly_braces == 0 and not escaped(i):
                braces += 1

                if braces == 0:
                    index = i
            elif c == "[" and curly_braces == 0 and not escaped(i):
                braces -= 1

                if braces == 0:
                    index = i

        if braces != 0 or curly_braces != 0:
            return (token, None)

        value = token.value[: -index - 2]
        var = Token(token.type, value, token.lineno, token.col_offset, token.error) if len(value) > 0 else None
        rest = Token(
            Token.ARGUMENT,
            token.value[-index - 2 :],
            token.lineno,
            token.col_offset + len(value),
            token.error,
        )

        return (var, rest)

    @classmethod
    def tokenize_variables(
        cls,
        token: Token,
        identifiers: str = "$@&%",
        ignore_errors: bool = False,
        *,
        extra_types: Optional[Set[str]] = None,
        exception_handler: Optional[Callable[[Exception, Token], None]] = None,
    ) -> Iterator[Token]:
        if exception_handler is not None:
            ignore_errors = False
        try:
            for t in tokenize_variables(token, identifiers, ignore_errors, extra_types=extra_types):
                if t.type == Token.VARIABLE:
                    var, rest = cls.remove_index_from_variable_token(t)
                    if var is not None:
                        yield var
                    if rest is not None:
                        yield from cls.tokenize_variables(
                            rest,
                            identifiers,
                            ignore_errors,
                            extra_types=extra_types,
                        )
                else:
                    yield t
        except VariableError as e:
            if exception_handler is not None:
                exception_handler(e, token)
            elif not ignore_errors:
                raise

    @classmethod
    def iter_variables_from_token(
        cls,
        token: Token,
        namespace: "Namespace",
        nodes: Optional[List[ast.AST]],
        position: Optional[Position] = None,
        skip_commandline_variables: bool = False,
        skip_local_variables: bool = False,
        return_not_found: bool = False,
    ) -> Iterator[Tuple[Token, VariableDefinition]]:
        def is_number(name: str) -> bool:
            if name.startswith("$"):
                finder = NumberFinder()
                return bool(finder.find(name) != NOT_FOUND)
            return False

        def iter_token(
            to: Token, ignore_errors: bool = False
        ) -> Iterator[Union[Token, Tuple[Token, VariableDefinition]]]:
            for sub_token in cls.tokenize_variables(to, ignore_errors=ignore_errors):
                if sub_token.type == Token.VARIABLE:
                    base = sub_token.value[2:-1]
                    if base and not (base[0] == "{" and base[-1] == "}"):
                        yield sub_token
                    elif base:
                        for v in cls.iter_expression_variables_from_token(
                            Token(
                                sub_token.type,
                                base[1:-1],
                                sub_token.lineno,
                                sub_token.col_offset + 3,
                                sub_token.error,
                            ),
                            namespace,
                            nodes,
                            position,
                            skip_commandline_variables=skip_commandline_variables,
                            skip_local_variables=skip_local_variables,
                            return_not_found=return_not_found,
                        ):
                            yield v
                    elif base == "" and return_not_found:
                        yield (  # TODO: robotframework ignores this case, should we do the same or raise an error/hint?
                            sub_token,
                            VariableNotFoundDefinition(
                                sub_token.lineno,
                                sub_token.col_offset,
                                sub_token.lineno,
                                sub_token.end_col_offset,
                                namespace.source,
                                sub_token.value,
                                sub_token,
                            ),
                        )
                        return

                    if contains_variable(base, "$@&%"):
                        for sub_token_or_var in iter_token(
                            Token(
                                to.type,
                                base,
                                sub_token.lineno,
                                sub_token.col_offset + 2,
                            ),
                            ignore_errors=ignore_errors,
                        ):
                            if isinstance(sub_token_or_var, Token):
                                if sub_token_or_var.type == Token.VARIABLE:
                                    yield sub_token_or_var
                            else:
                                yield sub_token_or_var

        if token.type == Token.VARIABLE and token.value.endswith("="):
            match = search_variable(token.value, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            token = Token(
                token.type,
                token.value[:-1].strip(),
                token.lineno,
                token.col_offset,
                token.error,
            )

        for token_or_var in iter_token(token, ignore_errors=True):
            if isinstance(token_or_var, Token):
                sub_token = token_or_var
                name = sub_token.value
                var = namespace.find_variable(
                    name,
                    nodes,
                    position,
                    skip_commandline_variables=skip_commandline_variables,
                    skip_local_variables=skip_local_variables,
                    ignore_error=True,
                )
                if var is not None:
                    yield strip_variable_token(sub_token), var
                    continue

                if is_number(sub_token.value):
                    continue

                if (
                    sub_token.type == Token.VARIABLE
                    and sub_token.value[:1] in "$@&%"
                    and sub_token.value[1:2] == "{"
                    and sub_token.value[-1:] == "}"
                ):
                    match = cls.match_extended.match(name[2:-1])
                    if match is not None:
                        base_name, _ = match.groups()
                        name = f"{name[0]}{{{base_name.strip()}}}"
                        var = namespace.find_variable(
                            name,
                            nodes,
                            position,
                            skip_commandline_variables=skip_commandline_variables,
                            skip_local_variables=skip_local_variables,
                            ignore_error=True,
                        )
                        sub_sub_token = Token(
                            sub_token.type,
                            name,
                            sub_token.lineno,
                            sub_token.col_offset,
                        )
                        if var is not None:
                            yield strip_variable_token(sub_sub_token), var
                            continue
                        if is_number(name):
                            continue
                        elif return_not_found:
                            if contains_variable(sub_token.value[2:-1]):
                                continue
                            else:
                                yield (
                                    strip_variable_token(sub_sub_token),
                                    VariableNotFoundDefinition(
                                        sub_sub_token.lineno,
                                        sub_sub_token.col_offset,
                                        sub_sub_token.lineno,
                                        sub_sub_token.end_col_offset,
                                        namespace.source,
                                        name,
                                        sub_sub_token,
                                    ),
                                )
                if return_not_found:
                    yield (
                        strip_variable_token(sub_token),
                        VariableNotFoundDefinition(
                            sub_token.lineno,
                            sub_token.col_offset,
                            sub_token.lineno,
                            sub_token.end_col_offset,
                            namespace.source,
                            sub_token.value,
                            sub_token,
                        ),
                    )
            else:
                yield token_or_var

    __expression_statement_types: Optional[Tuple[Type[Any]]] = None

    @classmethod
    def get_expression_statement_types(cls) -> Tuple[Type[Any]]:
        import robot.parsing.model.statements

        if cls.__expression_statement_types is None:
            cls.__expression_statement_types = (robot.parsing.model.statements.IfHeader,)

            if get_robot_version() >= (5, 0):
                cls.__expression_statement_types = (  # type: ignore[assignment]
                    robot.parsing.model.statements.IfElseHeader,
                    robot.parsing.model.statements.WhileHeader,
                )

        return cls.__expression_statement_types

    BDD_TOKEN_REGEX = re.compile(r"^(Given|When|Then|And|But)\s", flags=re.IGNORECASE)
    BDD_TOKEN = re.compile(r"^(Given|When|Then|And|But)$", flags=re.IGNORECASE)

    @classmethod
    def split_bdd_prefix(cls, namespace: "Namespace", token: Token) -> Tuple[Optional[Token], Optional[Token]]:
        bdd_token = None

        parts = token.value.split()
        if len(parts) < 2:
            return None, token

        for index in range(1, len(parts)):
            prefix = " ".join(parts[:index]).title()
            if prefix in (
                namespace.languages.bdd_prefixes if namespace.languages is not None else DEFAULT_BDD_PREFIXES
            ):
                bdd_len = len(prefix)
                bdd_token = Token(
                    token.type,
                    token.value[:bdd_len],
                    token.lineno,
                    token.col_offset,
                    token.error,
                )

                token = Token(
                    token.type,
                    token.value[bdd_len + 1 :],
                    token.lineno,
                    token.col_offset + bdd_len + 1,
                    token.error,
                )
                break

        return bdd_token, token

    @classmethod
    def strip_bdd_prefix(cls, namespace: "Namespace", token: Token) -> Token:
        if get_robot_version() < (6, 0):
            bdd_match = cls.BDD_TOKEN_REGEX.match(token.value)
            if bdd_match:
                bdd_len = len(bdd_match.group(1))

                token = Token(
                    token.type,
                    token.value[bdd_len + 1 :],
                    token.lineno,
                    token.col_offset + bdd_len + 1,
                    token.error,
                )
            return token

        parts = token.value.split()
        if len(parts) < 2:
            return token

        for index in range(1, len(parts)):
            prefix = " ".join(parts[:index]).title()
            if prefix in (
                namespace.languages.bdd_prefixes if namespace.languages is not None else DEFAULT_BDD_PREFIXES
            ):
                bdd_len = len(prefix)
                token = Token(
                    token.type,
                    token.value[bdd_len + 1 :],
                    token.lineno,
                    token.col_offset + bdd_len + 1,
                    token.error,
                )
                break

        return token

    @classmethod
    def is_bdd_token(cls, namespace: "Namespace", token: Token) -> bool:
        if get_robot_version() < (6, 0):
            bdd_match = cls.BDD_TOKEN.match(token.value)
            return bool(bdd_match)

        parts = token.value.split()

        for index in range(len(parts)):
            prefix = " ".join(parts[: index + 1]).title()

            if prefix.title() in (
                namespace.languages.bdd_prefixes if namespace.languages is not None else DEFAULT_BDD_PREFIXES
            ):
                return True

        return False

    @classmethod
    def get_keyword_definition_at_token(cls, library_doc: LibraryDoc, token: Token) -> Optional[KeywordDoc]:
        return cls.get_keyword_definition_at_line(library_doc, token.value, token.lineno)

    @classmethod
    def get_keyword_definition_at_line(cls, library_doc: LibraryDoc, value: str, line: int) -> Optional[KeywordDoc]:
        return next(
            (k for k in library_doc.keywords.iter_all(value) if k.line_no == line),
            None,
        )

    def get_argument_info_at_position(
        self,
        keyword_doc: KeywordDoc,
        tokens: Sequence[Token],
        token_at_position: Token,
        position: Position,
    ) -> Tuple[int, Optional[List[ArgumentInfo]], Optional[Token]]:
        argument_index = -1
        named_arg = False

        kw_arguments = [
            a
            for a in keyword_doc.arguments
            if a.kind
            not in [
                KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
                KeywordArgumentKind.NAMED_ONLY_MARKER,
            ]
        ]

        token_at_position_index = tokens.index(token_at_position)

        if (
            token_at_position.type in [Token.EOL, Token.SEPARATOR]
            and token_at_position_index > 2
            and tokens[token_at_position_index - 1].type == Token.CONTINUATION
            and position.character < range_from_token(tokens[token_at_position_index - 1]).end.character + 2
        ):
            return -1, None, None

        token_at_position_index = tokens.index(token_at_position)

        argument_token_index = token_at_position_index
        while argument_token_index >= 0 and tokens[argument_token_index].type != Token.ARGUMENT:
            argument_token_index -= 1

        if (
            token_at_position.type == Token.EOL
            and len(tokens) > 1
            and tokens[argument_token_index - 1].type == Token.CONTINUATION
        ):
            argument_token_index -= 2
            while argument_token_index >= 0 and tokens[argument_token_index].type != Token.ARGUMENT:
                argument_token_index -= 1

        arguments = [a for a in tokens if a.type == Token.ARGUMENT]

        argument_token: Optional[Token] = None

        if argument_token_index >= 0:
            argument_token = tokens[argument_token_index]
            if argument_token is not None and argument_token.type == Token.ARGUMENT:
                argument_index = arguments.index(argument_token)
            else:
                argument_index = 0
        else:
            argument_index = -1

        if whitespace_at_begin_of_token(token_at_position) > 1:
            r = range_from_token(token_at_position)

            ws_b = whitespace_from_begin_of_token(token_at_position)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r, True):
                argument_index += 1
                argument_token = None

            if argument_token is None:
                r.end.character = r.start.character + whitespace_at_begin_of_token(token_at_position) - 3
                if not position.is_in_range(r, False):
                    argument_token_index += 2
                    if argument_token_index < len(tokens) and tokens[argument_token_index].type == Token.ARGUMENT:
                        argument_token = tokens[argument_token_index]

        if (
            argument_index < 0
            or argument_token is not None
            and argument_token.type == Token.ARGUMENT
            and argument_token.value.startswith(("@{", "&{"))
            and argument_token.value.endswith("}")
        ):
            return -1, kw_arguments, argument_token

        if argument_token is not None and argument_token.type == Token.ARGUMENT:
            arg_name_or_value, arg_value = split_from_equals(argument_token.value)
            if arg_value is not None:
                old_argument_index = argument_index
                argument_index = next(
                    (
                        i
                        for i, v in enumerate(kw_arguments)
                        if v.name == arg_name_or_value or v.kind == KeywordArgumentKind.VAR_NAMED
                    ),
                    -1,
                )

                if argument_index == -1:
                    argument_index = old_argument_index
                else:
                    named_arg = True

        if not named_arg and argument_index >= 0:
            need_named = False
            for i, a in enumerate(arguments):
                if i == argument_index:
                    break
                arg_name_or_value, arg_value = split_from_equals(a.value)
                if arg_value is not None and any(
                    (k for k, v in enumerate(kw_arguments) if v.name == arg_name_or_value)
                ):
                    need_named = True
                    break
                if arg_name_or_value.startswith(("@{", "&{")) and arg_name_or_value.endswith("}"):
                    need_named = True
                    break

            a_index = next(
                (
                    i
                    for i, v in enumerate(kw_arguments)
                    if v.kind
                    in [
                        KeywordArgumentKind.POSITIONAL_ONLY,
                        KeywordArgumentKind.POSITIONAL_OR_NAMED,
                    ]
                    and i == argument_index
                ),
                -1,
            )
            if a_index >= 0 and not need_named:
                argument_index = a_index
            else:
                if need_named:
                    argument_index = next(
                        (i for i, v in enumerate(kw_arguments) if v.kind == KeywordArgumentKind.VAR_NAMED),
                        -1,
                    )
                else:
                    argument_index = next(
                        (i for i, v in enumerate(kw_arguments) if v.kind == KeywordArgumentKind.VAR_POSITIONAL),
                        -1,
                    )

        if argument_index >= len(kw_arguments):
            argument_index = -1

        return argument_index, kw_arguments, argument_token
