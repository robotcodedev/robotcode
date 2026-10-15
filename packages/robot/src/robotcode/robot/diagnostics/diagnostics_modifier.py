import functools
import re as re
from ast import AST
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import Block, File
from robot.parsing.model.statements import Comment, Statement
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity

from ..utils.visitor import Visitor

# The long names come before their short forms, the pattern takes the first alternative that matches.
ACTIONS = ["ignore", "error", "warning", "warn", "information", "info", "hint", "reset"]

ROBOTCODE_ACTION_AND_CODES_PATTERN = re.compile(rf"(?P<action>{'|'.join(ACTIONS)})(\[(?P<codes>[^\]]*?)\])?")


class ModifierAction(Enum):
    IGNORE = "ignore"
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"
    HINT = "hint"
    RESET = "reset"

    @classmethod
    def from_str(cls, value: str) -> "ModifierAction":
        if value == "warn":
            value = "warning"
        elif value == "info":
            value = "information"
        return cls(value)


# How near a modifier is to the line it affects: an inline modifier at the end of the line, an indented comment in
# a block, or a top-level comment of the file.
_FILE_LEVEL = 0
_BLOCK_LEVEL = 1
_INLINE_LEVEL = 2

# The rank of a modifier: its level, then the line of its comment, then its position in the comment. The higher rank
# wins, also between a modifier for a code and one without a list (`*`).
Rank = Tuple[int, int, int]


@dataclass
class RulesAndCodes:
    codes: Dict[Union[str, int], Set[int]]
    actions: Dict[int, Dict[Union[str, int], ModifierAction]]
    ranks: Dict[int, Dict[Union[str, int], Rank]] = field(default_factory=lambda: defaultdict(dict))


_translation_table = str.maketrans("", "", "_- ")

ROBOTCODE_MARKER = "robotcode:"


def text_contains_diagnostic_modifier(text: str) -> bool:
    return ROBOTCODE_MARKER in text


class ModifiersVisitor(Visitor):
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
        # Restored afterwards, so that a modifier after a nested block (IF, FOR, ...) belongs to the outer block.
        parent_block = self.current_block
        self.current_block = node
        self.generic_visit(node)
        self.current_block = parent_block

    def visit_Statement(self, node: Statement) -> None:  # noqa: N802
        self._handle_statement_comments(node)
        self.generic_visit(node)

    def _parse_actions(self, comment: str) -> List[Tuple[ModifierAction, str]]:
        """The actions of a modifier comment and their codes, in the order they are written."""
        result: List[Tuple[ModifierAction, str]] = []

        comment = comment.strip()
        m = ROBOTCODE_ACTION_AND_CODES_PATTERN.match(comment)
        if m is None:
            return result

        for m in ROBOTCODE_ACTION_AND_CODES_PATTERN.finditer(comment):
            action_str = m.group("action")
            action = ModifierAction.from_str(action_str)
            messages = m.group("codes")
            codes = (
                [m.strip().translate(_translation_table).lower() for m in messages.split(",")]
                if messages is not None
                else ["*"]
            )
            for code in codes:
                # A code belongs to the rightmost action that names it, also when an action appears more than once.
                result = [entry for entry in result if entry[1] != code]
                result.append((action, code))

        return result

    def _parse_robotcode_disabler(self, comment: str) -> Dict[ModifierAction, List[str]]:
        result: Dict[ModifierAction, List[str]] = {}
        for action, code in self._parse_actions(comment):
            result.setdefault(action, []).append(code)
        return result

    def _add_rule(self, lineno: int, code: str, action: ModifierAction, rank: Rank) -> None:
        self.rules_and_codes.codes[code].add(lineno)
        current = self.rules_and_codes.ranks[lineno].get(code)
        if current is None or rank >= current:
            self.rules_and_codes.actions[lineno][code] = action
            self.rules_and_codes.ranks[lineno][code] = rank

    def _handle_statement_comments(self, node: Statement) -> None:
        first_comment = True
        has_marker = False
        position = 0

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
                actions = self._parse_actions(value)

                if not actions:
                    break

                lineno = token.lineno - 1
                for action, code in actions:
                    self._add_rule(lineno, code, action, (_INLINE_LEVEL, lineno, position))
                    position += 1

    def _handle_comment(self, node: Comment) -> None:
        first_comment = True
        has_marker = False

        start_lineno = node.lineno - 1
        end_lineno = self.file_end_lineno
        level = _FILE_LEVEL
        position = 0

        if node.tokens[0].type == Token.SEPARATOR and self.current_block is not None:
            end_lineno = self.current_block.end_lineno - 1
            level = _BLOCK_LEVEL
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
                actions = self._parse_actions(value)

                if not actions:
                    break

                for action, code in actions:
                    rank = (level, start_lineno, position)
                    position += 1
                    for i in range(start_lineno, end_lineno + 1):
                        self._add_rule(i, code, action, rank)


@dataclass
class DiagnosticModifiersConfig:
    ignore: List[str] = field(default_factory=list)
    error: List[str] = field(default_factory=list)
    warning: List[str] = field(default_factory=list)
    information: List[str] = field(default_factory=list)
    hint: List[str] = field(default_factory=list)


class DiagnosticsModifier:
    def __init__(self, model: Optional[AST], config: Optional[DiagnosticModifiersConfig] = None) -> None:
        self.config = config or DiagnosticModifiersConfig()

        self.config.ignore = [i.translate(_translation_table).lower() for i in self.config.ignore]
        self.config.error = [i.translate(_translation_table).lower() for i in self.config.error]
        self.config.warning = [i.translate(_translation_table).lower() for i in self.config.warning]
        self.config.information = [i.translate(_translation_table).lower() for i in self.config.information]
        self.config.hint = [i.translate(_translation_table).lower() for i in self.config.hint]

        self._model = model

    @functools.cached_property
    def rules_and_codes(self) -> RulesAndCodes:
        visitor = ModifiersVisitor()
        if self._model is not None:
            visitor.visit(self._model)
        return visitor.rules_and_codes

    def modify_diagnostic(self, diagnostic: Diagnostic) -> Optional[Diagnostic]:
        if diagnostic.code is not None:
            code = orig_code = (
                str(diagnostic.code).translate(_translation_table).lower()
                if diagnostic.code is not None
                else "unknowncode"
            )

            modified = False
            action = self._action_for(diagnostic.range.start.line, code)
            if action is not None:
                if action == ModifierAction.IGNORE:
                    return None
                if action == ModifierAction.RESET:
                    pass
                elif action == ModifierAction.ERROR:
                    modified = True
                    diagnostic.severity = DiagnosticSeverity.ERROR
                elif action == ModifierAction.WARNING:
                    modified = True
                    diagnostic.severity = DiagnosticSeverity.WARNING
                elif action == ModifierAction.INFORMATION:
                    modified = True
                    diagnostic.severity = DiagnosticSeverity.INFORMATION
                elif action == ModifierAction.HINT:
                    modified = True
                    diagnostic.severity = DiagnosticSeverity.HINT

            if not modified:
                if orig_code in self.config.ignore:
                    return None
                if orig_code in self.config.error:
                    diagnostic.severity = DiagnosticSeverity.ERROR
                elif orig_code in self.config.warning:
                    diagnostic.severity = DiagnosticSeverity.WARNING
                elif orig_code in self.config.information:
                    diagnostic.severity = DiagnosticSeverity.INFORMATION
                elif orig_code in self.config.hint:
                    diagnostic.severity = DiagnosticSeverity.HINT
                elif "*" in self.config.hint:
                    diagnostic.severity = DiagnosticSeverity.HINT
                elif "*" in self.config.information:
                    diagnostic.severity = DiagnosticSeverity.INFORMATION
                elif "*" in self.config.warning:
                    diagnostic.severity = DiagnosticSeverity.WARNING
                elif "*" in self.config.error:
                    diagnostic.severity = DiagnosticSeverity.ERROR
                elif "*" in self.config.ignore:
                    return None

        return diagnostic

    def _action_for(self, line: int, code: str) -> Optional[ModifierAction]:
        """The action of the nearest modifier on `line` for `code`: one that names the code, or one without a list."""
        actions = self.rules_and_codes.actions.get(line)
        if not actions:
            return None
        ranks = self.rules_and_codes.ranks.get(line, {})
        keys = [key for key in (code, "*") if key in actions]
        if not keys:
            return None
        return actions[max(keys, key=lambda key: ranks.get(key, (-1, -1, -1)))]

    def modify_diagnostics(self, diagnostics: List[Diagnostic]) -> List[Diagnostic]:
        return [d for d in map(self.modify_diagnostic, diagnostics) if d is not None]
