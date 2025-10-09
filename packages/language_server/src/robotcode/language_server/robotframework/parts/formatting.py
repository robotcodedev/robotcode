import io
import os
from typing import TYPE_CHECKING, Any, List, Optional, cast

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    FormattingOptions,
    MessageType,
    Position,
    Range,
    TextEdit,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.utils import get_robot_version

from ..configuration import RoboCopConfig
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotFormattingProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.formatting.format.add(self.format)

        if self.parent.robocop_helper.robocop_installed and self.parent.robocop_helper.robocop_version >= (6, 0):
            parent.formatting.format_range.add(self.format_range)

        self.space_count = 4
        self.use_pipes = False
        self.line_separator = os.linesep
        self.short_test_name_length = 18
        self.setting_and_variable_name_length = 14
        self.is_robocop_notification_shown = False

    def get_robocop_config(self, document: TextDocument) -> RoboCopConfig:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return RoboCopConfig()

        return self.parent.workspace.get_configuration(RoboCopConfig, folder.uri)

    @language_id("robotframework")
    @_logger.call
    def format(
        self,
        sender: Any,
        document: TextDocument,
        options: FormattingOptions,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        if self.parent.robocop_helper.robocop_installed and self.parent.robocop_helper.robocop_version >= (6, 0):
            return self.format_robocop(document, options, **further_options)

        if get_robot_version() < (5, 0):
            return self.format_internal(document, options, **further_options)

        self.parent.window.show_message(
            "RobotFramework formatter is not available, please install 'robotframework-robocop'.",
            MessageType.ERROR,
        )

        return None

    def format_robocop(
        self,
        document: TextDocument,
        options: FormattingOptions,
        range: Optional[Range] = None,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        from robocop.formatter.runner import RobocopFormatter

        workspace_folder = self.parent.workspace.get_workspace_folder(document.uri)
        if workspace_folder is None:
            return None

        config_manager = self.parent.robocop_helper.get_config_manager(workspace_folder)

        config = config_manager.get_config_for_source_file(document.uri.to_path())

        if range is not None:
            config.formatter.start_line = range.start.line + 1
            config.formatter.end_line = range.end.line + 1

        runner = RobocopFormatter(config_manager)
        runner.config = config

        model = self.parent.documents_cache.get_model(document, False)
        _, _, new, _ = runner.format_until_stable(model)

        if new.text == document.text():
            return None

        return [
            TextEdit(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=len(document.get_lines()), character=0),
                ),
                new_text=new.text,
            )
        ]

    def format_internal(
        self,
        document: TextDocument,
        options: FormattingOptions,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        from robot.parsing.model.blocks import File
        from robot.tidypkg import (  # pyright: ignore [reportMissingImports]
            Aligner,
            Cleaner,
            NewlineNormalizer,
            SeparatorNormalizer,
        )

        model = cast(File, self.parent.documents_cache.get_model(document, False))

        Cleaner().visit(model)
        NewlineNormalizer(self.line_separator, self.short_test_name_length).visit(model)
        SeparatorNormalizer(self.use_pipes, self.space_count).visit(model)
        Aligner(
            self.short_test_name_length,
            self.setting_and_variable_name_length,
            self.use_pipes,
        ).visit(model)

        with io.StringIO() as s:
            model.save(s)

            return [
                TextEdit(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=len(document.get_lines()), character=0),
                    ),
                    new_text=s.getvalue(),
                )
            ]

    @language_id("robotframework")
    def format_range(
        self,
        sender: Any,
        document: TextDocument,
        range: Range,
        options: FormattingOptions,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        if self.parent.robocop_helper.robocop_installed and self.parent.robocop_helper.robocop_version >= (6, 0):
            return self.format_robocop(document, options, range=range, **further_options)

        return None
