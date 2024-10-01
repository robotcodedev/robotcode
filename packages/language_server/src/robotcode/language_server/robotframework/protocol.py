import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Final,
    List,
    Optional,
)

from robotcode.core.event import event
from robotcode.core.language import LanguageDefinition
from robotcode.core.lsp.types import InitializeError
from robotcode.core.utils.dataclasses import CamelSnakeMixin, from_dict
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import JsonRPCErrorException, JsonRPCErrors, ProtocolPartDescriptor
from robotcode.language_server.common.parts.document_symbols import symbol_information_label
from robotcode.language_server.common.protocol import LanguageServerProtocol
from robotcode.robot.config.model import RobotBaseProfile
from robotcode.robot.diagnostics.workspace_config import RobotConfig, WorkspaceAnalysisConfig
from robotcode.robot.utils import get_robot_version

from ..__version__ import __version__
from .parts.code_action_documentation import RobotCodeActionDocumentationProtocolPart
from .parts.code_action_quick_fixes import RobotCodeActionQuickFixesProtocolPart
from .parts.code_action_refactor import RobotCodeActionRefactorProtocolPart
from .parts.code_lens import RobotCodeLensProtocolPart
from .parts.completion import RobotCompletionProtocolPart
from .parts.debugging_utils import RobotDebuggingUtilsProtocolPart
from .parts.diagnostics import RobotDiagnosticsProtocolPart
from .parts.document_highlight import RobotDocumentHighlightProtocolPart
from .parts.document_symbols import RobotDocumentSymbolsProtocolPart
from .parts.documents_cache import DocumentsCachePart
from .parts.folding_range import RobotFoldingRangeProtocolPart
from .parts.formatting import RobotFormattingProtocolPart
from .parts.goto import RobotGotoProtocolPart
from .parts.hover import RobotHoverProtocolPart
from .parts.http_server import HttpServerProtocolPart
from .parts.inlay_hint import RobotInlayHintProtocolPart
from .parts.inline_value import RobotInlineValueProtocolPart
from .parts.keywords_treeview import RobotKeywordsTreeViewPart
from .parts.project_info import ProjectInfoPart
from .parts.references import RobotReferencesProtocolPart
from .parts.rename import RobotRenameProtocolPart
from .parts.robocop_diagnostics import RobotRoboCopDiagnosticsProtocolPart
from .parts.robot_workspace import RobotWorkspaceProtocolPart
from .parts.selection_range import RobotSelectionRangeProtocolPart
from .parts.semantic_tokens import RobotSemanticTokenProtocolPart
from .parts.signature_help import RobotSignatureHelpProtocolPart

if TYPE_CHECKING:
    from .server import RobotLanguageServer


class RobotCodeError(Exception):
    pass


class RobotModuleNotFoundError(RobotCodeError):
    pass


class RobotVersionDontMatchError(RobotCodeError):
    pass


def check_robotframework() -> None:
    try:
        __import__("robot")
    except ImportError as e:
        raise RobotModuleNotFoundError(
            "RobotFramework not installed in current Python environment, please install it."
        ) from e

    if get_robot_version() < (4, 1):
        raise RobotVersionDontMatchError("Wrong RobotFramework version. Expect version >= 4.1")


@dataclass
class RobotInitializationOptions(CamelSnakeMixin):
    storage_uri: Optional[str] = None
    global_storage_uri: Optional[str] = None
    python_path: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)


@symbol_information_label("robotframework")
class RobotLanguageServerProtocol(LanguageServerProtocol):
    _logger: Final = LoggingDescriptor()

    # documents_cache = ProtocolPartDescriptor(DocumentsCachePart)
    robot_workspace = ProtocolPartDescriptor(RobotWorkspaceProtocolPart)
    robot_diagnostics = ProtocolPartDescriptor(RobotDiagnosticsProtocolPart)
    robot_folding_ranges = ProtocolPartDescriptor(RobotFoldingRangeProtocolPart)
    robot_goto = ProtocolPartDescriptor(RobotGotoProtocolPart)
    robot_hover = ProtocolPartDescriptor(RobotHoverProtocolPart)
    robot_completion = ProtocolPartDescriptor(RobotCompletionProtocolPart)
    robot_signature_help = ProtocolPartDescriptor(RobotSignatureHelpProtocolPart)
    robot_document_symbols = ProtocolPartDescriptor(RobotDocumentSymbolsProtocolPart)
    robot_robocop_diagnostics = ProtocolPartDescriptor(RobotRoboCopDiagnosticsProtocolPart)
    robot_formatting = ProtocolPartDescriptor(RobotFormattingProtocolPart)
    robot_semantic_tokens = ProtocolPartDescriptor(RobotSemanticTokenProtocolPart)
    robot_references = ProtocolPartDescriptor(RobotReferencesProtocolPart)
    robot_document_highlight = ProtocolPartDescriptor(RobotDocumentHighlightProtocolPart)
    robot_codelens = ProtocolPartDescriptor(RobotCodeLensProtocolPart)
    robot_selection_range = ProtocolPartDescriptor(RobotSelectionRangeProtocolPart)
    robot_rename = ProtocolPartDescriptor(RobotRenameProtocolPart)
    robot_inline_value = ProtocolPartDescriptor(RobotInlineValueProtocolPart)
    robot_inlay_hint = ProtocolPartDescriptor(RobotInlayHintProtocolPart)
    robot_code_action_documentation = ProtocolPartDescriptor(RobotCodeActionDocumentationProtocolPart)
    robot_code_action_quick_fixes = ProtocolPartDescriptor(RobotCodeActionQuickFixesProtocolPart)
    robot_code_action_refactor = ProtocolPartDescriptor(RobotCodeActionRefactorProtocolPart)

    robot_debugging_utils = ProtocolPartDescriptor(RobotDebuggingUtilsProtocolPart)
    robot_keywords_treeview = ProtocolPartDescriptor(RobotKeywordsTreeViewPart)
    robot_project_info = ProtocolPartDescriptor(ProjectInfoPart)

    http_server = ProtocolPartDescriptor(HttpServerProtocolPart)

    name = "RobotCode Language Server"
    short_name = "RobotCode"
    version = __version__

    file_extensions: ClassVar = {
        "robot",
        "resource",
        "py",
        "yaml",
        "yml",
    }

    languages: ClassVar[List[LanguageDefinition]] = [
        LanguageDefinition(
            id="robotframework",
            extensions=[".robot", ".resource"],
            extensions_ignore_case=True,
            aliases=["Robot Framework", "robotframework"],
        ),
        # LanguageDefinition(
        #     id="feature",
        #     extensions=[".feature", ".md"],
        #     aliases=["feature", "gherkin", "Gherkin", "cucumber"],
        # ),
        # LanguageDefinition(id="markdown", extensions=[".md"]),
    ]

    def __init__(
        self,
        server: "RobotLanguageServer",
        profile: Optional[RobotBaseProfile] = None,
        analysis_config: Optional[WorkspaceAnalysisConfig] = None,
    ):
        super().__init__(server)
        self.robot_profile = profile if profile is not None else RobotBaseProfile()
        self.analysis_config = analysis_config if analysis_config is not None else WorkspaceAnalysisConfig()
        self.robot_initialization_options = RobotInitializationOptions()
        self.on_initialize.add(self._on_initialize)
        self.on_initialized.add(self.server_initialized)
        self._documents_cache: Optional[DocumentsCachePart] = None

    @_logger.call
    def _on_initialize(self, sender: Any, initialization_options: Optional[Any] = None) -> None:
        if initialization_options is not None:
            self.robot_initialization_options = from_dict(initialization_options, RobotInitializationOptions)

        if self.robot_initialization_options.env:
            for k, v in self.robot_initialization_options.env.items():
                os.environ[k] = v

        if self.robot_initialization_options.python_path:
            for folder in self.workspace.workspace_folders:
                for p in self.robot_initialization_options.python_path:
                    pa = Path(p)
                    if not pa.is_absolute():
                        pa = Path(folder.uri.to_path(), pa)

                    absolute_path = str(pa.absolute())
                    if absolute_path not in sys.path:
                        sys.path.insert(0, absolute_path)

        try:
            check_robotframework()
        except RobotCodeError as e:
            raise JsonRPCErrorException(
                JsonRPCErrors.INTERNAL_ERROR,
                f"Can't start language server: {e}",
                InitializeError(retry=False),
            ) from e

        self.workspace.did_change_configuration.add(self._on_did_change_configuration)

        if self.client_info is not None and self.client_info.name == "Visual Studio Code":
            self.progress_title = "$(robotcode-robot)"

        self._documents_cache = DocumentsCachePart(self)

        self._logger.info(lambda: f"initialized with {self.robot_initialization_options!r}")

    @property
    def documents_cache(self) -> DocumentsCachePart:
        if self._documents_cache is None:
            raise RuntimeError("DocumentsCachePart not initialized")

        return self._documents_cache

    def _on_did_change_configuration(self, sender: Any, settings: Dict[str, Any]) -> None:
        pass

    @event
    def on_robot_initialized(sender) -> None: ...

    def server_initialized(self, sender: Any) -> None:
        for folder in self.workspace.workspace_folders:
            config: RobotConfig = self.workspace.get_configuration(RobotConfig, folder.uri)

            for p in self.robot_profile.python_path or []:
                pa = Path(str(p))
                if not pa.is_absolute():
                    pa = Path(folder.uri.to_path(), pa)

                absolute_path = str(pa.absolute())
                if absolute_path not in sys.path:
                    sys.path.insert(0, absolute_path)

            if config is not None:
                if config.env:
                    for k, v in config.env.items():
                        os.environ[k] = v

                if config.python_path:
                    for p in config.python_path:
                        pa = Path(p)
                        if not pa.is_absolute():
                            pa = Path(folder.uri.to_path(), pa)

                        absolute_path = str(pa.absolute())
                        if absolute_path not in sys.path:
                            sys.path.insert(0, absolute_path)

        self.on_robot_initialized(self)
