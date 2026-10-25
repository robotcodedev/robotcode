import os
from concurrent.futures import CancelledError
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Sequence, Set, Tuple

from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import CamelSnakeMixin
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.robot.diagnostics.library_doc import BUILTIN_LIBRARY_NAME, CompleteResult, CompleteResultKind

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

PATH_SEPARATORS = ("/", os.sep)

# Of two equal labels, a module comes before a file and a file before a directory, as in the editor's completion.
KIND_ORDER = {CompleteResultKind.MODULE_INTERNAL: 0, CompleteResultKind.MODULE: 0, CompleteResultKind.FOLDER: 2}


@dataclass(repr=False)
class CompleteTargetParams(CamelSnakeMixin):
    workspace_folder_uri: str
    text: str


@dataclass(repr=False)
class TargetCompletion(CamelSnakeMixin):
    label: str
    # the name of the `CompleteResultKind`, and its value as the editor's completion shows it
    kind: str
    detail: str
    # the index in the text from which the label replaces it, in UTF-16 code units as the page counts
    start: int


def split_at_last_separator(text: str, separators: Sequence[str]) -> Tuple[Optional[str], int]:
    """The text up to and with its last separator, or None without one, and the length of that prefix."""
    index = max(text.rfind(separator) for separator in separators)
    return (text[: index + 1], index + 1) if index >= 0 else (None, 0)


def utf16_length(text: str) -> int:
    """The length of `text` in UTF-16 code units, as LSP positions count."""
    return len(text.encode("utf-16-le")) // 2


def completion_order(text: str, result: CompleteResult, start: int) -> Tuple[int, str, int, str]:
    """The order of the editor's completion: first the labels that continue the typed part in the same case, then the
    others, each by label without regard to case."""
    same_case = result.label.startswith(text[start:])
    return (0 if same_case else 1, result.label.lower(), KIND_ORDER.get(result.kind, 1), result.label)


class RobotDocumentationViewerPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

    @rpc_method(name="robot/documentationViewer/completeTarget", param_type=CompleteTargetParams, threaded=True)
    @_logger.call
    def _complete_target(
        self,
        workspace_folder_uri: str,
        text: str,
        *args: Any,
        **kwargs: Any,
    ) -> List[TargetCompletion]:
        # The arguments of an import are not completed, nor a text of dots only, as in the editor.
        if "::" in text or (text and all(c == "." for c in text)):
            return []

        folder = Uri(workspace_folder_uri)
        imports_manager = self.parent.documents_cache.get_imports_manager_for_uri(folder)
        base_dir = str(folder.to_path())

        results: Set[Tuple[CompleteResult, int]] = set()

        # Libraries are completed as in the editor: a name with a path separator as a path, any other as a module.
        library_prefix, library_start = split_at_last_separator(
            text, PATH_SEPARATORS if any(s in text for s in PATH_SEPARATORS) else (".",)
        )
        for result in self._completions(imports_manager.complete_library_import, library_prefix, base_dir):
            results.add((result, library_start))
        # The editor leaves out BuiltIn, which every file imports already; for the viewer it is a target like any other.
        if library_prefix is None:
            results.add((CompleteResult(BUILTIN_LIBRARY_NAME, CompleteResultKind.MODULE_INTERNAL), 0))

        # Resources are looked up in the base directory only for names that start with `.` or a path separator, but
        # the target field writes paths relative to the workspace folder without `./`.
        resource_prefix, resource_start = split_at_last_separator(text, PATH_SEPARATORS)
        resource_names = [resource_prefix]
        if (
            resource_prefix is not None
            and not resource_prefix.startswith((".", *PATH_SEPARATORS))
            and not Path(resource_prefix).is_absolute()
        ):
            resource_names.append(f"./{resource_prefix}")
        for name in resource_names:
            for result in self._completions(imports_manager.complete_resource_import, name, base_dir):
                results.add((result, resource_start))

        matching = [(r, start) for r, start in results if r.label.lower().startswith(text[start:].lower())]
        matching.sort(key=lambda item: completion_order(text, *item))
        return [
            TargetCompletion(result.label, result.kind.name, result.kind.value, utf16_length(text[:start]))
            for result, start in matching
        ]

    def _completions(
        self,
        complete: Callable[[Optional[str], str], Optional[List[CompleteResult]]],
        name: Optional[str],
        base_dir: str,
    ) -> List[CompleteResult]:
        # A side that fails, such as on a directory without read permission, leaves the other side's results.
        try:
            return complete(name, base_dir) or []
        except (SystemExit, KeyboardInterrupt, CancelledError):
            raise
        except BaseException as e:
            self._logger.exception(e)
            return []
