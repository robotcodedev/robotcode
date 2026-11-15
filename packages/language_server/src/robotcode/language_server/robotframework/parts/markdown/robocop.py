"""Robocop's checks and formatting of a Markdown document, with Robocop's own support for Markdown files."""

from typing import TYPE_CHECKING, Any, List, Optional

from robotcode.core.language import language_id
from robotcode.core.lsp.types import FormattingOptions, MessageType, Range, TextEdit
from robotcode.core.text_document import TextDocument
from robotcode.robot.document_formats import MARKDOWN_LANGUAGE_ID

from ....common.parts.diagnostics import DiagnosticsCollectType, DiagnosticsResult
from ..formatting import RobotFormattingProtocolPart
from ..robocop_diagnostics import RobotRoboCopDiagnosticsProtocolPart

if TYPE_CHECKING:
    from robocop.formatter.runner import RobocopFormatter
    from robocop.linter.runner import RobocopLinter

# Robocop reads the code blocks of Markdown files itself since 9.2
ROBOCOP_MARKDOWN_VERSION = (9, 2)


def _source_file(document: TextDocument, config: Any) -> Any:
    # Robocop's source file of a Markdown document, from the current text of the document
    from robocop.source_file import EmbeddedSourceFile

    source_file = EmbeddedSourceFile(
        path=document.uri.to_path(), config=config, _source_lines=document.text().splitlines(keepends=True)
    )
    # builds the models of the code blocks from the given lines, not from the file on disk
    source_file.reload_model()
    return source_file


class MarkdownRoboCopDiagnosticsProtocolPart(RobotRoboCopDiagnosticsProtocolPart):
    @language_id(MARKDOWN_LANGUAGE_ID)
    def collect_diagnostics(
        self, sender: Any, document: TextDocument, diagnostics_type: DiagnosticsCollectType
    ) -> Optional[DiagnosticsResult]:
        if self.parent.robocop_helper.robocop_version < ROBOCOP_MARKDOWN_VERSION:
            return None

        return super().collect_diagnostics(sender, document, diagnostics_type)

    def run_check(self, linter: "RobocopLinter", document: TextDocument, config: Any) -> Any:
        return linter.run_check(_source_file(document, config))


class MarkdownFormattingProtocolPart(RobotFormattingProtocolPart):
    @language_id(MARKDOWN_LANGUAGE_ID)
    def format(
        self,
        sender: Any,
        document: TextDocument,
        options: FormattingOptions,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        helper = self.parent.robocop_helper
        if not helper.robocop_installed or helper.robocop_version < ROBOCOP_MARKDOWN_VERSION:
            self.parent.window.show_message(
                "Formatting Markdown files needs 'robotframework-robocop' 9.2 or newer.", MessageType.ERROR
            )
            return None

        return self.format_robocop(document, options, **further_options)

    @language_id(MARKDOWN_LANGUAGE_ID)
    def format_range(
        self,
        sender: Any,
        document: TextDocument,
        range: Range,
        options: FormattingOptions,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        # Robocop formats each code block on its own and counts the lines of a range per block
        return None

    def formatted_text(self, runner: "RobocopFormatter", document: TextDocument, config: Any) -> str:
        _, _, new_text = runner.format_embedded(_source_file(document, config))
        return str(new_text)
