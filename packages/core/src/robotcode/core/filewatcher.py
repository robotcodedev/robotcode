from abc import ABC, abstractmethod
from typing import Any, Callable, List, NamedTuple, Optional, Tuple, Union
from uuid import uuid4

from robotcode.core.event import event
from robotcode.core.lsp.types import FileEvent, WatchKind


class FileWatcher(NamedTuple):
    glob_pattern: str
    kind: Optional[WatchKind] = None


class FileWatcherEntry:
    def __init__(
        self,
        id: str,
        callback: Callable[[Any, List[FileEvent]], None],
        watchers: List[FileWatcher],
    ) -> None:
        self.id = id
        self.callback = callback
        self.watchers = watchers
        self.parent: Optional[FileWatcherEntry] = None
        self.finalizer: Any = None

    @event
    def child_callbacks(sender, changes: List[FileEvent]) -> None: ...

    def call_childrens(self, sender: Any, changes: List[FileEvent]) -> None:
        self.child_callbacks(sender, changes)

    def __str__(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(id={self.id!r}, watchers={self.watchers!r})"


class FileWatcherManagerBase(ABC):
    def add_file_watcher(
        self,
        callback: Callable[[Any, List[FileEvent]], None],
        glob_pattern: str,
        kind: Optional[WatchKind] = None,
    ) -> FileWatcherEntry:
        return self.add_file_watchers(callback, [(glob_pattern, kind)])

    @abstractmethod
    def add_file_watchers(
        self,
        callback: Callable[[Any, List[FileEvent]], None],
        watchers: List[Union[FileWatcher, str, Tuple[str, Optional[WatchKind]]]],
    ) -> FileWatcherEntry: ...

    @abstractmethod
    def remove_file_watcher_entry(self, entry: FileWatcherEntry) -> None: ...


class FileWatcherManagerDummy(FileWatcherManagerBase):
    def add_file_watchers(
        self,
        callback: Callable[[Any, List[FileEvent]], None],
        watchers: List[Union[FileWatcher, str, Tuple[str, Optional[WatchKind]]]],
    ) -> FileWatcherEntry:
        _watchers = [
            e if isinstance(e, FileWatcher) else FileWatcher(*e) if isinstance(e, tuple) else FileWatcher(e)
            for e in watchers
        ]

        return FileWatcherEntry(f"dummy-{uuid4()}", callback, _watchers)

    def remove_file_watcher_entry(self, entry: FileWatcherEntry) -> None:
        pass
