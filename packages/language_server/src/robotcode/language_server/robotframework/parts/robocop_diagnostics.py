import io
from typing import TYPE_CHECKING, Any, List, Optional
from weakref import WeakKeyDictionary

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    CodeDescription,
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.core.utils.version import Version, create_version_from_str
from robotcode.core.workspace import WorkspaceFolder

from ...common.parts.diagnostics import DiagnosticsCollectType, DiagnosticsResult
from ..configuration import RoboCopConfig
from .protocol_part import RobotLanguageServerProtocolPart
from .robocop_tidy_mixin import RoboCopTidyMixin

if TYPE_CHECKING:
    from robocop.linter.runner import RobocopLinter

    from ..protocol import RobotLanguageServerProtocol


class RobotRoboCopDiagnosticsProtocolPart(RobotLanguageServerProtocolPart, RoboCopTidyMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        self.source_name = "robocop"
        self._robocop_linters: WeakKeyDictionary[WorkspaceFolder, "RobocopLinter"] = WeakKeyDictionary()

        if self.robocop_installed:
            parent.diagnostics.collect.add(self.collect_diagnostics)

    def get_config(self, document: TextDocument) -> Optional[RoboCopConfig]:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return None

        return self.parent.workspace.get_configuration(RoboCopConfig, folder.uri)

    @language_id("robotframework")
    @_logger.call
    def collect_diagnostics(
        self, sender: Any, document: TextDocument, diagnostics_type: DiagnosticsCollectType
    ) -> Optional[DiagnosticsResult]:
        if self.robocop_installed:
            workspace_folder = self.parent.workspace.get_workspace_folder(document.uri)
            if workspace_folder is not None:
                config = self.get_config(document)

                if config is not None and config.enabled:
                    if self.robocop_version >= (6, 0):
                        # In Robocop 6.0, the diagnostics are collected in a different way
                        return DiagnosticsResult(
                            self.collect_diagnostics,
                            self.collect(document, workspace_folder, config),
                        )

                    return DiagnosticsResult(
                        self.collect_diagnostics,
                        self.collect_old(document, workspace_folder, config),
                    )

        return None

    @_logger.call
    def collect(
        self,
        document: TextDocument,
        workspace_folder: WorkspaceFolder,
        extension_config: RoboCopConfig,
    ) -> List[Diagnostic]:
        from robocop.config import ConfigManager
        from robocop.linter.rules import RuleSeverity
        from robocop.linter.runner import RobocopLinter

        linter = self._robocop_linters.get(workspace_folder, None)

        if linter is None:
            config_manager = ConfigManager(
                [],
                root=workspace_folder.uri.to_path(),
                config=extension_config.config_file,
                ignore_git_dir=extension_config.ignore_git_dir,
                ignore_file_config=extension_config.ignore_file_config,
            )
            linter = RobocopLinter(config_manager)
            self._robocop_linters[workspace_folder] = linter

        source = document.uri.to_path()

        config = linter.config_manager.get_config_for_source_file(source)
        model = self.parent.documents_cache.get_model(document, False)
        diagnostics = linter.run_check(model, source, config)

        return [
            Diagnostic(
                range=Range(
                    start=Position(
                        line=diagnostic.range.start.line - 1,
                        character=diagnostic.range.start.character - 1,
                    ),
                    end=Position(
                        line=max(0, diagnostic.range.end.line - 1),
                        character=max(0, diagnostic.range.end.character - 1),
                    ),
                ),
                message=diagnostic.message,
                severity=(
                    DiagnosticSeverity.INFORMATION
                    if diagnostic.severity == RuleSeverity.INFO
                    else (
                        DiagnosticSeverity.WARNING
                        if diagnostic.severity == RuleSeverity.WARNING
                        else (
                            DiagnosticSeverity.ERROR
                            if diagnostic.severity == RuleSeverity.ERROR
                            else DiagnosticSeverity.HINT
                        )
                    )
                ),
                source=self.source_name,
                code=f"{diagnostic.rule.rule_id}-{diagnostic.rule.name}",
                code_description=self.get_code_description(self.robocop_version, diagnostic),
            )
            for diagnostic in diagnostics
        ]

    @_logger.call
    def collect_old(
        self,
        document: TextDocument,
        workspace_folder: WorkspaceFolder,
        extension_config: RoboCopConfig,
    ) -> List[Diagnostic]:
        from robocop import __version__
        from robocop.config import Config
        from robocop.rules import RuleSeverity
        from robocop.run import Robocop
        from robocop.utils.misc import is_suite_templated

        robocop_version = create_version_from_str(__version__)
        result: List[Diagnostic] = []

        with io.StringIO() as output:
            config = Config(str(workspace_folder.uri.to_path()))

            config.exec_dir = str(workspace_folder.uri.to_path())

            config.output = output

            if extension_config.include:
                config.include = set(extension_config.include)
            if extension_config.exclude:
                config.exclude = set(extension_config.exclude)
            if extension_config.configurations:
                config.configure = extension_config.configurations

            # TODO: do we need this?
            class MyRobocop(Robocop):
                def run_check(self, ast_model, filename, source=None):  # type: ignore
                    if robocop_version >= (4, 0):
                        from robocop.utils.disablers import DisablersFinder

                        disablers = DisablersFinder(ast_model)
                    elif robocop_version >= (2, 4):
                        from robocop.utils import DisablersFinder

                        disablers = DisablersFinder(filename=filename, source=source)

                    else:
                        self.register_disablers(filename, source)
                        disablers = self.disabler

                    if disablers.file_disabled:
                        return []

                    found_issues = []  # type: ignore

                    templated = is_suite_templated(ast_model)

                    for checker in self.checkers:
                        if len(found_issues) >= 1000:
                            break

                        if checker.disabled:
                            continue
                        found_issues += [
                            issue
                            for issue in checker.scan_file(ast_model, filename, source, templated)
                            if not disablers.is_rule_disabled(issue)
                        ]

                    return found_issues

            analyser = MyRobocop(from_cli=False, config=config)
            analyser.reload_config()

            # TODO find a way to cancel the run_check
            issues = analyser.run_check(
                self.parent.documents_cache.get_model(document, False),
                str(document.uri.to_path()),
                document.text(),
            )  # type: ignore[no-untyped-call]

            for issue in issues:
                d = Diagnostic(
                    range=Range(
                        start=Position(
                            line=max(0, issue.line - 1),
                            character=max(0, issue.col - 1),
                        ),
                        end=Position(
                            line=max(0, issue.end_line - 1),
                            character=max(0, issue.end_col - 1),
                        ),
                    ),
                    message=issue.desc,
                    severity=(
                        DiagnosticSeverity.INFORMATION
                        if issue.severity == RuleSeverity.INFO
                        else (
                            DiagnosticSeverity.WARNING
                            if issue.severity == RuleSeverity.WARNING
                            else (
                                DiagnosticSeverity.ERROR
                                if issue.severity == RuleSeverity.ERROR
                                else DiagnosticSeverity.HINT
                            )
                        )
                    ),
                    source=self.source_name,
                    code=f"{issue.name}-{issue.severity.value}{issue.rule_id}",
                    code_description=self.get_code_description(robocop_version, issue),
                )

                result.append(d)

        return result

    def get_code_description(self, version: Version, issue: Any) -> Optional[CodeDescription]:
        if version < (3, 0):
            return None

        version_letter = "v" if version.major >= 6 else ""

        base = f"https://robocop.readthedocs.io/en/{version_letter}{version.major}.{version.minor}.{version.patch}"

        if version < (4, 0):
            return CodeDescription(href=f"{base}/rules.html#{issue.name}".lower())

        if version < (4, 1):
            return CodeDescription(href=f"{base}/rules.html#{issue.name}-{issue.severity.value}{issue.rule_id}".lower())

        if version < (4, 1, 1):
            return CodeDescription(
                href=f"{base}/rules_list.html#{issue.name}-{issue.severity.value}{issue.rule_id}".lower()
            )

        if version < (6, 0):
            return CodeDescription(href=f"{base}/rules_list.html#{issue.name}".lower())

        return CodeDescription(href=f"{base}/rules/rules_list.html#{issue.rule.rule_id}-{issue.rule.name}".lower())
