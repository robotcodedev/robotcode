import functools
import re as re
from ast import AST
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Union

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import Block, File
from robot.parsing.model.statements import Comment, Statement
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity

from ..utils.visitor import Visitor

ACTIONS = ["ignore", "error", "warn", "information", "hint", "reset"]

ROBOTCODE_ACTION_AND_CODES_PATTERN = re.compile(rf"(?P<action>{'|'.join(ACTIONS)})(\[(?P<codes>[^\]]*?)\])?")


@dataclass
class RulesAndCodes:
    codes: Dict[Union[str, int], Set[int]]
    actions: Dict[int, Dict[Union[str, int], str]]


_translation_table = str.maketrans("", "", "_- ")

ROBOTCODE_MARKER = "robotcode:"


class DisablersVisitor(Visitor):

    def __init__(self) -> None:
        super().__init__()

        self._file_lineno = 0
        self._file_end_lineno = 0
        self.current_block: Optional[Block] = None
        self.rules_and_codes: RulesAndCodes = RulesAndCodes(defaultdict(set), defaultdict(dict))

    @property
    def file_lineno(self) -> int:
        return self._file_lineno

    @property
    def file_end_lineno(self) -> int:
        return self._file_end_lineno

    def visit_File(self, node: File) -> None:  # noqa: N802
        self._file_lineno = node.lineno - 1
        self._file_end_lineno = node.end_lineno - 1

        self.generic_visit(node)

    def visit_Comment(self, node: Comment) -> None:  # noqa: N802
        self._handle_comment(node)

        self.generic_visit(node)

    def visit_Block(self, node: Block) -> None:  # noqa: N802
        self.current_block = node
        self.generic_visit(node)

    def visit_Statement(self, node: Statement) -> None:  # noqa: N802
        self._handle_statement_comments(node)
        self.generic_visit(node)

    def _parse_robotcode_disabler(self, comment: str) -> Dict[str, List[str]]:
        result: Dict[str, List[str]] = {}

        comment = comment.strip()
        m = ROBOTCODE_ACTION_AND_CODES_PATTERN.match(comment)
        if m is None:
            return result

        for m in ROBOTCODE_ACTION_AND_CODES_PATTERN.finditer(comment):
            action = m.group("action")
            messages = m.group("codes")
            result[action] = (
                [m.strip().translate(_translation_table).lower() for m in messages.split(",")]
                if messages is not None
                else ["*"]
            )

        return result

    def _handle_statement_comments(self, node: Statement) -> None:
        first_comment = True
        has_marker = False

        for token in node.get_tokens(Token.COMMENT):
            value = token.value.strip()
            if first_comment and value.startswith("#"):
                value = value[1:].strip()
                first_comment = False

            if not value:
                continue

            if not has_marker and value.startswith(ROBOTCODE_MARKER):
                has_marker = True
                value = value[10:]

            if not value:
                continue

            if has_marker:
                actions = self._parse_robotcode_disabler(value)

                if not actions:
                    break

                for action, codes in actions.items():
                    for code in codes:
                        self.rules_and_codes.codes[code].add(token.lineno - 1)
                        self.rules_and_codes.actions[token.lineno - 1][code] = action

    def _handle_comment(self, node: Comment) -> None:
        first_comment = True
        has_marker = False

        start_lineno = node.lineno - 1
        end_lineno = self.file_end_lineno

        if node.tokens[0].type == Token.SEPARATOR and self.current_block is not None:
            end_lineno = self.current_block.end_lineno - 1
        for token in node.get_tokens(Token.COMMENT):
            value = token.value.strip()
            if first_comment and value.startswith("#"):
                value = value[1:].strip()
                first_comment = False

            if not value:
                continue

            if not has_marker and value.startswith(ROBOTCODE_MARKER):
                has_marker = True
                value = value[10:]

            if not value:
                continue

            if has_marker:
                actions = self._parse_robotcode_disabler(value)

                if not actions:
                    break

                for action, codes in actions.items():
                    for code in codes:
                        self.rules_and_codes.codes[code].update(range(start_lineno, end_lineno + 1))
                        for i in range(start_lineno, end_lineno + 1):
                            self.rules_and_codes.actions[i][code] = action


class DiagnosticsModifier:
    def __init__(self, model: AST) -> None:
        self.model = model

    @functools.cached_property
    def rules_and_codes(self) -> RulesAndCodes:
        visitor = DisablersVisitor()
        visitor.visit(self.model)
        return visitor.rules_and_codes

    def modify_diagnostic(self, diagnostic: Diagnostic) -> Optional[Diagnostic]:
        if diagnostic.code is not None:
            code = (
                str(diagnostic.code).translate(_translation_table).lower()
                if diagnostic.code is not None
                else "unknowncode"
            )

            lines = self.rules_and_codes.codes.get(code)

            if lines is None or lines is not None and diagnostic.range.start.line not in lines:
                code = "*"
                lines = self.rules_and_codes.codes.get(code)

            if lines is not None and diagnostic.range.start.line in lines:
                actions = self.rules_and_codes.actions.get(diagnostic.range.start.line)
                if actions is not None:
                    action = actions.get(code)
                    if action is not None:
                        if action == "ignore":
                            return None
                        if action == "reset":
                            pass  # do nothing
                        elif action == "error":
                            diagnostic.severity = DiagnosticSeverity.ERROR
                        elif action == "warn":
                            diagnostic.severity = DiagnosticSeverity.WARNING
                        elif action == "information":
                            diagnostic.severity = DiagnosticSeverity.INFORMATION
                        elif action == "hint":
                            diagnostic.severity = DiagnosticSeverity.HINT

        return diagnostic

    def modify_diagnostics(self, diagnostics: List[Diagnostic]) -> List[Diagnostic]:
        return [d for d in map(self.modify_diagnostic, diagnostics) if d is not None]
