import io
import os
from concurrent.futures import CancelledError
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

from ..configuration import RoboCopConfig, RoboTidyConfig
from .protocol_part import RobotLanguageServerProtocolPart
from .robocop_tidy_mixin import RoboCopTidyMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotFormattingProtocolPart(RobotLanguageServerProtocolPart, RoboCopTidyMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.formatting.format.add(self.format)

        if self.robotidy_installed or (self.robocop_installed and self.robocop_version >= (6, 0)):
            parent.formatting.format_range.add(self.format_range)

        self.space_count = 4
        self.use_pipes = False
        self.line_separator = os.linesep
        self.short_test_name_length = 18
        self.setting_and_variable_name_length = 14
        self.is_robocop_notification_shown = False

    def get_tidy_config(self, document: TextDocument) -> RoboTidyConfig:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return RoboTidyConfig()

        return self.parent.workspace.get_configuration(RoboTidyConfig, folder.uri)

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
        if self.robocop_installed and self.robocop_version >= (6, 0):
            if not self.is_robocop_notification_shown and self.robotidy_installed:
                self.parent.window.show_message(
                    "`robotframework-robocop >= 6.0` is installed and will be used for formatting.\n\n"
                    "`robotframework-tidy` is also detected in the workspace, but its use is redundant.\n"
                    "Robocop fully supports all formatting tasks and provides a more comprehensive solution.\n\n"
                    "Note: The use of `robotframework-tidy` is deprecated and should be avoided in favor of Robocop.",
                    MessageType.INFO,
                )
                self.is_robocop_notification_shown = True

            return self.format_robocop(document, options, **further_options)

        tidy_config = self.get_tidy_config(document)
        if (tidy_config.enabled or get_robot_version() >= (5, 0)) and self.robotidy_installed:
            return self.format_robot_tidy(document, options, config=tidy_config, **further_options)

        if get_robot_version() < (5, 0):
            return self.format_internal(document, options, **further_options)

        self.parent.window.show_message(
            "RobotFramework formatter is not available, please install 'robotframework-robocop'.",
            MessageType.ERROR,
        )

        return None

    def format_robot_tidy(
        self,
        document: TextDocument,
        options: FormattingOptions,
        range: Optional[Range] = None,
        config: Optional[RoboTidyConfig] = None,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        try:
            if config is None:
                config = self.get_tidy_config(document)

            model = self.parent.documents_cache.get_model(document, False)

            if self.robotidy_version >= (3, 0):
                from robotidy.api import get_robotidy
                from robotidy.disablers import RegisterDisablers

                if self.robotidy_version >= (4, 2):
                    robot_tidy = get_robotidy(
                        document.uri.to_path(),
                        None,
                        ignore_git_dir=config.ignore_git_dir,
                        config=config.config,
                    )
                elif self.robotidy_version >= (4, 1):
                    robot_tidy = get_robotidy(
                        document.uri.to_path(),
                        None,
                        ignore_git_dir=config.ignore_git_dir,
                    )
                else:
                    robot_tidy = get_robotidy(document.uri.to_path(), None)

                if range is not None:
                    robot_tidy.config.formatting.start_line = range.start.line + 1
                    robot_tidy.config.formatting.end_line = range.end.line + 1

                disabler_finder = RegisterDisablers(
                    robot_tidy.config.formatting.start_line,
                    robot_tidy.config.formatting.end_line,
                )
                disabler_finder.visit(model)

                if self.robotidy_version >= (4, 11):
                    if disabler_finder.is_disabled_in_file():
                        return None
                else:
                    if disabler_finder.file_disabled:
                        return None

                if self.robotidy_version >= (4, 0):
                    _, _, new, _ = robot_tidy.transform_until_stable(model, disabler_finder)
                else:
                    _, _, new = robot_tidy.transform(model, disabler_finder.disablers)

            else:
                from robotidy.api import RobotidyAPI

                robot_tidy = RobotidyAPI(document.uri.to_path(), None)

                if range is not None:
                    robot_tidy.formatting_config.start_line = range.start.line + 1
                    robot_tidy.formatting_config.end_line = range.end.line + 1

                if self.robotidy_version >= (2, 2):
                    from robotidy.disablers import RegisterDisablers

                    disabler_finder = RegisterDisablers(
                        robot_tidy.formatting_config.start_line,
                        robot_tidy.formatting_config.end_line,
                    )
                    disabler_finder.visit(model)
                    if disabler_finder.file_disabled:
                        return None
                    _, _, new = robot_tidy.transform(model, disabler_finder.disablers)
                else:
                    _, _, new = robot_tidy.transform(model)

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

        except (SystemExit, KeyboardInterrupt, CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)
            self.parent.window.show_message(f"Executing `robotidy` failed: {e}", MessageType.ERROR)
        return None

    def format_robocop(
        self,
        document: TextDocument,
        options: FormattingOptions,
        range: Optional[Range] = None,
        **further_options: Any,
    ) -> Optional[List[TextEdit]]:
        from robocop.config import ConfigManager
        from robocop.formatter.runner import RobocopFormatter

        robocop_config = self.get_robocop_config(document)
        workspace_folder = self.parent.workspace.get_workspace_folder(document.uri)

        config_manager = ConfigManager(
            [document.uri.to_path()],
            root=workspace_folder.uri.to_path() if workspace_folder else None,
            config=robocop_config.config_file,
            ignore_git_dir=robocop_config.ignore_git_dir,
            ignore_file_config=robocop_config.ignore_file_config,
        )

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
        config = self.get_tidy_config(document)
        if (config.enabled and self.robotidy_installed) or (self.robocop_installed and self.robocop_version >= (6, 0)):
            return self.format_robot_tidy(document, options, range=range, config=config, **further_options)

        return None
