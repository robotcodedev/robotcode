from __future__ import annotations

import asyncio
import io
import os
import re
from typing import TYPE_CHECKING, Any, List, Optional, cast

from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import (
    FormattingOptions,
    MessageType,
    Position,
    Range,
    TextEdit,
)
from ...common.text_document import TextDocument
from ..utils.version import get_robot_version

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from ..configuration import RoboTidyConfig
from ..utils.version import create_version_from_str
from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart


def robotidy_installed() -> bool:
    try:
        __import__("robotidy")
    except ImportError:
        return False
    return True


class RobotFormattingProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.formatting.format.add(self.format)

        if robotidy_installed():
            parent.formatting.format_range.add(self.format_range)

        self.space_count = 4
        self.use_pipes = False
        self.line_separator = os.linesep
        self.short_test_name_length = 18
        self.setting_and_variable_name_length = 14

    async def get_config(self, document: TextDocument) -> Optional[RoboTidyConfig]:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return None

        return await self.parent.workspace.get_configuration(RoboTidyConfig, folder.uri)

    @language_id("robotframework")
    @_logger.call
    async def format(
        self, sender: Any, document: TextDocument, options: FormattingOptions, **further_options: Any
    ) -> Optional[List[TextEdit]]:
        config = await self.get_config(document)

        if config and (config.enabled or get_robot_version() >= (5, 0)) and robotidy_installed():
            return await self.format_robot_tidy(document, options, **further_options)

        if get_robot_version() < (5, 0):
            return await self.format_internal(document, options, **further_options)

        self.parent.window.show_message(
            "RobotFramework formatter is not available, please install 'robotframework-tidy'.", MessageType.ERROR
        )

        return None

    RE_LINEBREAKS = re.compile(r"\r\n|\r|\n")

    async def format_robot_tidy(
        self, document: TextDocument, options: FormattingOptions, range: Optional[Range] = None, **further_options: Any
    ) -> Optional[List[TextEdit]]:

        from difflib import SequenceMatcher

        from robotidy.version import __version__

        try:
            robotidy_version = create_version_from_str(__version__)

            model = await self.parent.documents_cache.get_model(document, False)
            if model is None:
                return None

            if robotidy_version >= (3, 0):
                from robotidy.api import get_robotidy
                from robotidy.disablers import RegisterDisablers

                robot_tidy = get_robotidy(document.uri.to_path(), None)

                if range is not None:
                    robot_tidy.config.formatting.start_line = range.start.line
                    robot_tidy.config.formatting.end_line = range.end.line + 1

                disabler_finder = RegisterDisablers(
                    robot_tidy.config.formatting.start_line, robot_tidy.config.formatting.end_line
                )
                disabler_finder.visit(model)
                if disabler_finder.file_disabled:
                    return None
                changed, _, new = robot_tidy.transform(model, disabler_finder.disablers)

            else:
                from robotidy.api import RobotidyAPI

                robot_tidy = RobotidyAPI(document.uri.to_path(), None)

                if range is not None:
                    robot_tidy.formatting_config.start_line = range.start.line
                    robot_tidy.formatting_config.end_line = range.end.line + 1

                if robotidy_version >= (2, 2):
                    from robotidy.disablers import RegisterDisablers

                    disabler_finder = RegisterDisablers(
                        robot_tidy.formatting_config.start_line, robot_tidy.formatting_config.end_line
                    )
                    disabler_finder.visit(model)
                    if disabler_finder.file_disabled:
                        return None
                    changed, _, new = robot_tidy.transform(model, disabler_finder.disablers)
                else:
                    changed, _, new = robot_tidy.transform(model)

            if not changed:
                return None

            new_lines = self.RE_LINEBREAKS.split(new.text)

            result: List[TextEdit] = []
            matcher = SequenceMatcher(a=document.get_lines(), b=new_lines, autojunk=False)
            for code, old_start, old_end, new_start, new_end in matcher.get_opcodes():
                if code == "insert" or code == "replace":
                    result.append(
                        TextEdit(
                            range=Range(
                                start=Position(line=old_start, character=0),
                                end=Position(line=old_end, character=0),
                            ),
                            new_text=os.linesep.join(new_lines[new_start:new_end]) + os.linesep,
                        )
                    )

                elif code == "delete":
                    result.append(
                        TextEdit(
                            range=Range(
                                start=Position(line=old_start, character=0),
                                end=Position(line=old_end, character=0),
                            ),
                            new_text="",
                        )
                    )

            if result:
                return result

        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)
        return None

    async def format_internal(
        self, document: TextDocument, options: FormattingOptions, **further_options: Any
    ) -> Optional[List[TextEdit]]:

        from robot.parsing.model.blocks import File
        from robot.tidypkg import (
            Aligner,
            Cleaner,
            NewlineNormalizer,
            SeparatorNormalizer,
        )

        model = cast(File, await self.parent.documents_cache.get_model(document, False))

        Cleaner().visit(model)
        NewlineNormalizer(self.line_separator, self.short_test_name_length).visit(model)
        SeparatorNormalizer(self.use_pipes, self.space_count).visit(model)
        Aligner(self.short_test_name_length, self.setting_and_variable_name_length, self.use_pipes).visit(model)

        with io.StringIO() as s:
            model.save(s)

            return [
                TextEdit(
                    range=Range(
                        start=Position(line=0, character=0),
                        end=Position(line=len(document.get_lines()), character=len((document.get_lines())[-1])),
                    ),
                    new_text=s.getvalue(),
                )
            ]

    @language_id("robotframework")
    async def format_range(
        self, sender: Any, document: TextDocument, range: Range, options: FormattingOptions, **further_options: Any
    ) -> Optional[List[TextEdit]]:

        config = await self.get_config(document)
        if config and config.enabled and robotidy_installed():
            return await self.format_robot_tidy(document, options, range=range, **further_options)

        return None
