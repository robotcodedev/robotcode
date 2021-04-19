from __future__ import annotations

import io
import os
from typing import TYPE_CHECKING, Any, List, Optional, cast

from ....utils.logging import LoggingDescriptor
from ...common.language import language_id
from ...common.text_document import TextDocument
from ...common.types import FormattingOptions, Position, Range, TextEdit

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart


class RobotFormattingProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.formatting.format.add(self.format)
        parent.formatting.format_range.add(self.format_range)

        self.space_count = 4
        self.use_pipes = False
        self.line_separator = os.linesep
        self.short_test_name_length = 18
        self.setting_and_variable_name_length = 14

    @language_id("robotframework")
    async def format(
        self, sender: Any, document: TextDocument, options: FormattingOptions, **further_options: Any
    ) -> Optional[List[TextEdit]]:

        from robot.parsing.model.blocks import File
        from robot.tidypkg import (
            Aligner,
            Cleaner,
            NewlineNormalizer,
            SeparatorNormalizer,
        )

        model = cast(File, await self.parent.documents_cache.get_model(document))

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
                        end=Position(line=len(document.lines), character=len(document.lines[-1])),
                    ),
                    new_text=s.getvalue(),
                )
            ]

    @language_id("robotframework")
    async def format_range(
        self, sender: Any, document: TextDocument, range: Range, options: FormattingOptions, **further_options: Any
    ) -> Optional[List[TextEdit]]:
        return None
