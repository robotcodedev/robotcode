"""The languages RobotCode serves: their ids and their language definitions."""

from pathlib import Path
from typing import Final, Optional

from robotcode.core.language import LanguageDefinition

from .config.model import RobotBaseProfile
from .document_formats import markdown_extensions, parse_include_condition

ROBOTFRAMEWORK_LANGUAGE_ID = "robotframework"

ROBOTFRAMEWORK_LANGUAGE = LanguageDefinition(
    id=ROBOTFRAMEWORK_LANGUAGE_ID,
    extensions=[".robot", ".resource"],
    extensions_ignore_case=True,
    aliases=["Robot Framework", "robotframework"],
)

# the language of the Markdown files Robot Framework parses; no editor sends it, the server detects it by file name
MARKDOWN_LANGUAGE_ID = "robotframework-markdown"

# the languages whose documents hold Robot Framework data
ROBOT_LANGUAGE_IDS: Final = (ROBOTFRAMEWORK_LANGUAGE_ID, MARKDOWN_LANGUAGE_ID)


def markdown_language_definition(profile: RobotBaseProfile, root: Path) -> Optional[LanguageDefinition]:
    """The language of the Markdown files Robot Framework parses with the profile in the project `root`; `None` when
    no Markdown extension is active."""
    extensions = [f".{e}" for e in markdown_extensions(profile)]
    if not extensions:
        return None

    return LanguageDefinition(
        id=MARKDOWN_LANGUAGE_ID,
        extensions=extensions,
        extensions_ignore_case=True,
        file_condition=parse_include_condition(profile, root),
    )
