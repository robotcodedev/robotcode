from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterable,
    Optional,
    Set,
    TypeVar,
)

from robotcode.core.lsp.types import Location

from ..utils.match import normalize_metadata_name
from .entities import LibraryEntry, VariableDefinition
from .library_doc import KeywordDoc

if TYPE_CHECKING:
    from .namespace import Namespace


_K = TypeVar("_K")


@dataclass
class _FileRefs:
    """Tracks which references a single file contributed to the global index."""

    uris: Set[str] = field(default_factory=set)
    keyword_references: Dict[KeywordDoc, Set[Location]] = field(default_factory=dict)
    variable_references: Dict[VariableDefinition, Set[Location]] = field(default_factory=dict)
    namespace_references: Dict[LibraryEntry, Set[Location]] = field(default_factory=dict)
    keyword_tag_references: Dict[str, Set[Location]] = field(default_factory=dict)
    testcase_tag_references: Dict[str, Set[Location]] = field(default_factory=dict)
    metadata_references: Dict[str, Set[Location]] = field(default_factory=dict)
    testcase_metadata_references: Dict[str, Set[Location]] = field(default_factory=dict)


class ProjectIndex:
    """Workspace-wide inverse reference index.

    Incrementally maintained: on file change only the affected file is
    removed and re-inserted. All lookups are O(1).

    Lookups count only the files that `is_known_source` accepts. They leave
    out the locations of the other files and remove these files, so that a
    file that is gone leaves nothing behind, also when its analysis ended
    after it went away.

    Thread-safety: An RLock protects all mutation operations (update_file,
    remove_file). Reads use the same lock — since writes are rare (only on
    file changes) and short, they block reads minimally.
    """

    def __init__(self, is_known_source: Optional[Callable[[str], bool]] = None) -> None:
        self._lock = threading.RLock()
        self._is_known_source = is_known_source

        self._keyword_references: Dict[KeywordDoc, Set[Location]] = defaultdict(set)
        self._variable_references: Dict[VariableDefinition, Set[Location]] = defaultdict(set)
        self._namespace_references: Dict[LibraryEntry, Set[Location]] = defaultdict(set)
        self._keyword_tag_references: Dict[str, Set[Location]] = defaultdict(set)
        self._testcase_tag_references: Dict[str, Set[Location]] = defaultdict(set)
        self._metadata_references: Dict[str, Set[Location]] = defaultdict(set)
        self._testcase_metadata_references: Dict[str, Set[Location]] = defaultdict(set)

        self._refs_by_file: Dict[str, _FileRefs] = {}
        # the file of a location, without converting its URI to a path
        self._source_by_uri: Dict[str, str] = {}

    def update_file(self, source: str, namespace: Namespace) -> None:
        """After NamespaceBuilder.build(): update this file's references."""
        with self._lock:
            self._remove_file_unlocked(source)

            file_refs = _FileRefs()

            self._merge_refs(
                namespace.keyword_references,
                self._keyword_references,
                file_refs.keyword_references,
                file_refs.uris,
            )
            self._merge_refs(
                namespace.variable_references,
                self._variable_references,
                file_refs.variable_references,
                file_refs.uris,
            )
            self._merge_refs(
                namespace.namespace_references,
                self._namespace_references,
                file_refs.namespace_references,
                file_refs.uris,
            )
            self._merge_refs(
                namespace.keyword_tag_references,
                self._keyword_tag_references,
                file_refs.keyword_tag_references,
                file_refs.uris,
            )
            self._merge_refs(
                namespace.testcase_tag_references,
                self._testcase_tag_references,
                file_refs.testcase_tag_references,
                file_refs.uris,
            )
            self._merge_refs(
                namespace.metadata_references,
                self._metadata_references,
                file_refs.metadata_references,
                file_refs.uris,
            )
            self._merge_refs(
                namespace.testcase_metadata_references,
                self._testcase_metadata_references,
                file_refs.testcase_metadata_references,
                file_refs.uris,
            )

            self._refs_by_file[source] = file_refs
            for uri in file_refs.uris:
                self._source_by_uri[uri] = source

    def remove_file(self, source: str) -> None:
        """File deleted or invalidated: remove all its references."""
        with self._lock:
            self._remove_file_unlocked(source)

    def _remove_file_unlocked(self, source: str) -> None:
        file_refs = self._refs_by_file.pop(source, None)
        if file_refs is None:
            return

        for uri in file_refs.uris:
            if self._source_by_uri.get(uri) == source:
                del self._source_by_uri[uri]

        self._subtract_refs(file_refs.keyword_references, self._keyword_references)
        self._subtract_refs(file_refs.variable_references, self._variable_references)
        self._subtract_refs(file_refs.namespace_references, self._namespace_references)
        self._subtract_refs(file_refs.keyword_tag_references, self._keyword_tag_references)
        self._subtract_refs(file_refs.testcase_tag_references, self._testcase_tag_references)
        self._subtract_refs(file_refs.metadata_references, self._metadata_references)
        self._subtract_refs(file_refs.testcase_metadata_references, self._testcase_metadata_references)

    @staticmethod
    def _merge_refs(
        source_refs: Dict[_K, Set[Location]],
        global_refs: Dict[_K, Set[Location]],
        file_refs: Dict[_K, Set[Location]],
        uris: Set[str],
    ) -> None:
        for key, locations in source_refs.items():
            if locations:
                copied = set(locations)
                global_refs[key].update(copied)
                file_refs[key] = copied
                uris.update(location.uri for location in copied)

    @staticmethod
    def _subtract_refs(
        file_refs: Dict[_K, Set[Location]],
        global_refs: Dict[_K, Set[Location]],
    ) -> None:
        for key, locations in file_refs.items():
            bucket = global_refs.get(key)
            if bucket is not None:
                bucket -= locations
                if not bucket:
                    del global_refs[key]

    def _known(self, locations: Iterable[Location]) -> Set[Location]:
        """The locations in files that still count; removes the files that do not. Called under the lock."""
        if self._is_known_source is None:
            return set(locations)

        result: Set[Location] = set()
        known_sources: Dict[str, bool] = {}
        for location in locations:
            source = self._source_by_uri.get(location.uri)
            if source is not None:
                known = known_sources.get(source)
                if known is None:
                    known = known_sources[source] = self._is_known_source(source)
                if not known:
                    continue
            result.add(location)

        for source, known in known_sources.items():
            if not known:
                self._remove_file_unlocked(source)

        return result

    def find_keyword_references(self, kw: KeywordDoc) -> Set[Location]:
        """O(1) lookup instead of O(N) workspace scan."""
        with self._lock:
            return self._known(self._keyword_references.get(kw, ()))

    def find_variable_references(self, var: VariableDefinition) -> Set[Location]:
        """O(1) lookup instead of O(N) workspace scan."""
        with self._lock:
            return self._known(self._variable_references.get(var, ()))

    def find_namespace_references(self, entry: LibraryEntry) -> Set[Location]:
        """O(1) lookup instead of O(N) workspace scan."""
        with self._lock:
            return self._known(self._namespace_references.get(entry, ()))

    def find_keyword_tag_references(self, tag: str) -> Set[Location]:
        with self._lock:
            return self._known(self._keyword_tag_references.get(tag, ()))

    def find_testcase_tag_references(self, tag: str) -> Set[Location]:
        with self._lock:
            return self._known(self._testcase_tag_references.get(tag, ()))

    def find_metadata_references(self, key: str) -> Set[Location]:
        """References to a suite metadata name, in any spelling Robot Framework treats as the same name."""
        with self._lock:
            return self._known(self._metadata_references.get(normalize_metadata_name(key), ()))

    def find_testcase_metadata_references(self, key: str) -> Set[Location]:
        """References to a test metadata name, in any spelling Robot Framework treats as the same name."""
        with self._lock:
            return self._known(self._testcase_metadata_references.get(normalize_metadata_name(key), ()))

    @property
    def keyword_references(self) -> Dict[KeywordDoc, Set[Location]]:
        with self._lock:
            return dict(self._keyword_references)

    @property
    def variable_references(self) -> Dict[VariableDefinition, Set[Location]]:
        with self._lock:
            return dict(self._variable_references)

    @property
    def namespace_references(self) -> Dict[LibraryEntry, Set[Location]]:
        with self._lock:
            return dict(self._namespace_references)

    def clear(self) -> None:
        with self._lock:
            self._keyword_references.clear()
            self._variable_references.clear()
            self._namespace_references.clear()
            self._keyword_tag_references.clear()
            self._testcase_tag_references.clear()
            self._metadata_references.clear()
            self._testcase_metadata_references.clear()
            self._refs_by_file.clear()
            self._source_by_uri.clear()
