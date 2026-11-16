import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from robot.running.builder import TestSuiteBuilder
from robotcode.core.utils.dataclasses import CamelSnakeMixin

from .config.model import RobotBaseProfile, StringExpression
from .utils import RF_VERSION

# Robot Framework reads Markdown files since 7.5, with line and column numbers of the file since 7.5.1
MARKDOWN_SUPPORTED = RF_VERSION >= (7, 5, 1)

if MARKDOWN_SUPPORTED:
    from robot.parsing.suitestructure import IncludedFiles

ROBOT_FORMAT_NAME = "robot"
MARKDOWN_FORMAT_NAME = "markdown"


# TODO: with Gherkin, also list the formats of the custom parsers in the profile's `parsers`, from
# `TestSuiteBuilder(custom_parsers=...).custom_parsers` per profile (each parser's `name` and `extensions`)
def _robot_framework_formats() -> Tuple[Tuple[str, ...], Dict[str, str]]:
    """Robot Framework's default extensions, and the format of each extension it has a parser for."""
    builder = TestSuiteBuilder()
    defaults = tuple(e.lower().lstrip(".") for e in builder.included_extensions)
    if RF_VERSION < (6, 1):
        return defaults, {"rst": "rest", "rest": "rest"}
    return defaults, {e: type(p).__name__.removesuffix("Parser").lower() for e, p in builder.standard_parsers.items()}


DEFAULT_EXTENSIONS, _FORMAT_OF_EXTENSION = _robot_framework_formats()


@dataclass(frozen=True)
class DocumentFormat(CamelSnakeMixin):
    """A document format Robot Framework parses, with the extensions it parses with it (lower case, no dot)."""

    name: str
    extensions: List[str]


def _evaluated(value: Union[str, StringExpression]) -> str:
    return value if isinstance(value, str) else value.evaluate()


def _parse_include_patterns(profile: RobotBaseProfile) -> List[str]:
    return [_evaluated(p) for p in profile.parse_include or []]


def _robot_framework_extensions(profile: RobotBaseProfile) -> List[str]:
    """Robot Framework's extension list for the profile: `extensions`, or the default extensions when it is not set,
    plus the extension of each `parse-include` pattern, normalised like Robot Framework (lower case, no dot)."""
    entries = _evaluated(profile.extensions).split(":") if profile.extensions else list(DEFAULT_EXTENSIONS)
    entries += [os.path.splitext(p)[1] for p in _parse_include_patterns(profile)]

    result: List[str] = []
    for entry in entries:
        extension = entry.lower().lstrip(".")
        if extension and extension not in result:
            result.append(extension)
    return result


def document_formats(profile: RobotBaseProfile) -> List[DocumentFormat]:
    """The document formats Robot Framework parses with the evaluated profile, in the order of their first extension."""
    formats: Dict[str, List[str]] = {}
    for extension in _robot_framework_extensions(profile):
        formats.setdefault(_FORMAT_OF_EXTENSION.get(extension, ROBOT_FORMAT_NAME), []).append(extension)
    return [DocumentFormat(name, extensions) for name, extensions in formats.items()]


def markdown_extensions(profile: RobotBaseProfile) -> List[str]:
    """The extensions of the Markdown files RobotCode serves, from Robot Framework 7.5.1 on."""
    if not MARKDOWN_SUPPORTED:
        return []
    return [e for f in document_formats(profile) if f.name == MARKDOWN_FORMAT_NAME for e in f.extensions]


def _pattern_from_root(pattern: str, root: Path) -> str:
    # Robot Framework resolves a pattern that holds a `/`, has no `.` or names an existing path from its working
    # directory, the project root for `robotcode robot`; other patterns match file names
    normalized = os.path.normpath(pattern).replace("\\", "/")
    if "/" in normalized or "." not in normalized or (root / normalized).exists():
        return str(root / normalized)
    return pattern


def parse_include_condition(profile: RobotBaseProfile, root: Path) -> Optional[Callable[[Path], bool]]:
    """Whether Robot Framework parses a file of a valid extension, by the `parse-include` patterns of the profile;
    `None` when it sets none. An `__init__` file needs no pattern, as in Robot Framework."""
    patterns = _parse_include_patterns(profile)
    if not MARKDOWN_SUPPORTED or not patterns:
        return None

    included = IncludedFiles([_pattern_from_root(p, root) for p in patterns])

    def condition(path: Path) -> bool:
        return path.stem.lower() == "__init__" or bool(included.match(path))

    return condition


def is_markdown_file(path: Path) -> bool:
    """Whether Robot Framework reads the file with its Markdown parser, from its code blocks.

    Robot Framework picks the parser of a resource file by its suffix, so this holds also without an active format.
    """
    return MARKDOWN_SUPPORTED and path.suffix.lower() in (".md", ".markdown")
