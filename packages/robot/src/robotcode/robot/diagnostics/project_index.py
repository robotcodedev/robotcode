from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Dict,
    Set,
    TypeVar,
)

from robotcode.core.lsp.types import Location

from .entities import LibraryEntry, VariableDefinition
from .library_doc import KeywordDoc

if TYPE_CHECKING:
    from .namespace import Namespace


_K = TypeVar("_K")


@dataclass
class _FileRefs:
    """Tracks which references a single file contributed to the global index."""

    keyword_references: Dict[KeywordDoc, Set[Location]] = field(default_factory=dict)
    variable_references: Dict[VariableDefinition, Set[Location]] = field(default_factory=dict)
    namespace_references: Dict[LibraryEntry, Set[Location]] = field(default_factory=dict)
    keyword_tag_references: Dict[str, Set[Location]] = field(default_factory=dict)
    testcase_tag_references: Dict[str, Set[Location]] = field(default_factory=dict)
    metadata_references: Dict[str, Set[Location]] = field(default_factory=dict)


class ProjectIndex:
    """Workspace-wide inverse reference index.

    Incrementally maintained: on file change only the affected file is
    removed and re-inserted. All lookups are O(1).

    Thread-safety: An RLock protects all mutation operations (update_file,
    remove_file). Reads use the same lock — since writes are rare (only on
    file changes) and short, they block reads minimally.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        self._keyword_references: Dict[KeywordDoc, Set[Location]] = defaultdict(set)
        self._variable_references: Dict[VariableDefinition, Set[Location]] = defaultdict(set)
        self._namespace_references: Dict[LibraryEntry, Set[Location]] = defaultdict(set)
        self._keyword_tag_references: Dict[str, Set[Location]] = defaultdict(set)
        self._testcase_tag_references: Dict[str, Set[Location]] = defaultdict(set)
        self._metadata_references: Dict[str, Set[Location]] = defaultdict(set)

        self._refs_by_file: Dict[str, _FileRefs] = {}

    def update_file(self, source: str, namespace: Namespace) -> None:
        """After NamespaceBuilder.build(): update this file's references."""
        with self._lock:
            self._remove_file_unlocked(source)

            file_refs = _FileRefs()

            self._merge_refs(
                namespace.keyword_references,
                self._keyword_references,
                file_refs.keyword_references,
            )
            self._merge_refs(
                namespace.variable_references,
                self._variable_references,
                file_refs.variable_references,
            )
            self._merge_refs(
                namespace.namespace_references,
                self._namespace_references,
                file_refs.namespace_references,
            )
            self._merge_refs(
                namespace.keyword_tag_references,
                self._keyword_tag_references,
                file_refs.keyword_tag_references,
            )
            self._merge_refs(
                namespace.testcase_tag_references,
                self._testcase_tag_references,
                file_refs.testcase_tag_references,
            )
            self._merge_refs(
                namespace.metadata_references,
                self._metadata_references,
                file_refs.metadata_references,
            )

            self._refs_by_file[source] = file_refs

    def remove_file(self, source: str) -> None:
        """File deleted or invalidated: remove all its references."""
        with self._lock:
            self._remove_file_unlocked(source)

    def _remove_file_unlocked(self, source: str) -> None:
        file_refs = self._refs_by_file.pop(source, None)
        if file_refs is None:
            return

        self._subtract_refs(file_refs.keyword_references, self._keyword_references)
        self._subtract_refs(file_refs.variable_references, self._variable_references)
        self._subtract_refs(file_refs.namespace_references, self._namespace_references)
        self._subtract_refs(file_refs.keyword_tag_references, self._keyword_tag_references)
        self._subtract_refs(file_refs.testcase_tag_references, self._testcase_tag_references)
        self._subtract_refs(file_refs.metadata_references, self._metadata_references)

    @staticmethod
    def _merge_refs(
        source_refs: Dict[_K, Set[Location]],
        global_refs: Dict[_K, Set[Location]],
        file_refs: Dict[_K, Set[Location]],
    ) -> None:
        for key, locations in source_refs.items():
            if locations:
                copied = set(locations)
                global_refs[key].update(copied)
                file_refs[key] = copied

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

    def find_keyword_references(self, kw: KeywordDoc) -> Set[Location]:
        """O(1) lookup instead of O(N) workspace scan."""
        with self._lock:
            return set(self._keyword_references.get(kw, ()))

    def find_variable_references(self, var: VariableDefinition) -> Set[Location]:
        """O(1) lookup instead of O(N) workspace scan."""
        with self._lock:
            return set(self._variable_references.get(var, ()))

    def find_namespace_references(self, entry: LibraryEntry) -> Set[Location]:
        """O(1) lookup instead of O(N) workspace scan."""
        with self._lock:
            return set(self._namespace_references.get(entry, ()))

    def find_keyword_tag_references(self, tag: str) -> Set[Location]:
        with self._lock:
            return set(self._keyword_tag_references.get(tag, ()))

    def find_testcase_tag_references(self, tag: str) -> Set[Location]:
        with self._lock:
            return set(self._testcase_tag_references.get(tag, ()))

    def find_metadata_references(self, key: str) -> Set[Location]:
        with self._lock:
            return set(self._metadata_references.get(key, ()))

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
            self._refs_by_file.clear()
