from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import List, Optional, Tuple

from robotcode.core.lsp.types import DocumentUri, Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.utils.ast import range_from_node
from robotcode.robot.utils.visitor import Visitor

SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND = "_robotcode.codeActionShowDocumentSelectAndRename"


@dataclass
class CodeActionDataBase:
    type: str
    method: str
    document_uri: DocumentUri
    range: Range


class FindSectionsVisitor(Visitor):
    def __init__(self) -> None:
        super().__init__()
        self.keyword_sections: List[ast.AST] = []
        self.variable_sections: List[ast.AST] = []
        self.setting_sections: List[ast.AST] = []
        self.testcase_sections: List[ast.AST] = []
        self.sections: List[ast.AST] = []

    def visit_KeywordSection(self, node: ast.AST) -> None:  # noqa: N802
        self.keyword_sections.append(node)
        self.sections.append(node)

    def visit_VariableSection(self, node: ast.AST) -> None:  # noqa: N802
        self.variable_sections.append(node)
        self.sections.append(node)

    def visit_SettingSection(self, node: ast.AST) -> None:  # noqa: N802
        self.setting_sections.append(node)
        self.sections.append(node)

    def visit_TestCaseSection(self, node: ast.AST) -> None:  # noqa: N802
        self.testcase_sections.append(node)
        self.sections.append(node)

    def visit_CommentSection(self, node: ast.AST) -> None:  # noqa: N802
        self.sections.append(node)


def find_keyword_sections(node: ast.AST) -> Optional[List[ast.AST]]:
    visitor = FindSectionsVisitor()
    visitor.visit(node)
    return visitor.keyword_sections if visitor.keyword_sections else None


class CodeActionHelperMixin:
    def create_insert_keyword_workspace_edit(
        self,
        document: TextDocument,
        model: ast.AST,
        namespace: Namespace,
        insert_text: str,
    ) -> Tuple[str, Range]:
        keyword_sections = find_keyword_sections(model)
        keyword_section = keyword_sections[-1] if keyword_sections else None

        lines = document.get_lines()

        if keyword_section is not None:
            node_range = range_from_node(keyword_section, skip_non_data=True, allow_comments=True)
            insert_pos = Position(node_range.end.line + 1, 0)
            insert_range = Range(insert_pos, insert_pos)
            insert_text = f"\n\n{insert_text}"
        else:
            if namespace.languages is None or not namespace.languages.languages:
                keywords_text = "Keywords"
            else:
                keywords_text = namespace.languages.languages[-1].keywords_header

            insert_text = f"\n\n*** {keywords_text} ***\n{insert_text}"

            end_line = len(lines) - 1
            while end_line >= 0 and not lines[end_line].strip():
                end_line -= 1
            doc_pos = Position(end_line + 1, 0)

            insert_range = Range(doc_pos, doc_pos)

        if insert_range.start.line >= len(lines) and lines[-1].strip():
            doc_pos = Position(len(lines) - 1, len(lines[-1]))
            insert_range = Range(doc_pos, doc_pos)
            insert_text = "\n" + insert_text

        if insert_range.start.line <= len(lines) and lines[insert_range.start.line].startswith("*"):
            insert_text = insert_text + "\n\n"
        if (
            insert_range.start.line + 1 < len(lines)
            and not lines[insert_range.start.line].strip()
            and lines[insert_range.start.line + 1].startswith("*")
        ):
            insert_text = insert_text + "\n"
        return insert_text, insert_range
