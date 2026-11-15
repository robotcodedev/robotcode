from pathlib import Path
from typing import Iterable, List

from robotcode.core.language import LanguageDefinition
from robotcode.core.workspace import WorkspaceFolder
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.document_formats import MARKDOWN_LANGUAGE_ID, markdown_extensions, markdown_language_definition

from .language_provider import LanguageProvider


class MarkdownLanguageProvider(LanguageProvider):
    """The Markdown files Robot Framework parses; the Robot Framework provider analyses them like `.robot` files."""

    @classmethod
    def get_language_definitions(cls, profile: RobotBaseProfile, root: Path) -> List[LanguageDefinition]:
        definition = markdown_language_definition(profile, root)
        return [definition] if definition is not None else []

    def collect_workspace_folder_files(self, folder: WorkspaceFolder) -> Iterable[Path]:
        if not markdown_extensions(self.diagnostics_context.profile):
            return []

        documents = self.diagnostics_context.workspace.documents
        return filter(
            lambda f: documents.detect_language_id(f) == MARKDOWN_LANGUAGE_ID, self.iter_workspace_folder_files(folder)
        )
