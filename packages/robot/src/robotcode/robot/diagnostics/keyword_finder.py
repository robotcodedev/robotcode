import functools
import re
from itertools import chain
from typing import TYPE_CHECKING, Dict, Iterable, Iterator, List, NamedTuple, Optional, Sequence, Tuple

from robot.libraries import STDLIBS
from robotcode.core.lsp.types import (
    DiagnosticSeverity,
)

from ..utils import get_robot_version
from ..utils.match import eq_namespace
from .entities import (
    LibraryEntry,
    ResourceEntry,
)
from .errors import Error
from .library_doc import (
    KeywordDoc,
    KeywordError,
    LibraryDoc,
)

if TYPE_CHECKING:
    from .namespace import Namespace


class DiagnosticsEntry(NamedTuple):
    message: str
    severity: DiagnosticSeverity
    code: Optional[str] = None


class CancelSearchError(Exception):
    pass


DEFAULT_BDD_PREFIXES = {"Given ", "When ", "Then ", "And ", "But "}


class KeywordFinder:
    def __init__(self, namespace: "Namespace", library_doc: LibraryDoc) -> None:
        self.namespace = namespace
        self.self_library_doc = library_doc

        self.diagnostics: List[DiagnosticsEntry] = []
        self.result_bdd_prefix: Optional[str] = None

        self.multiple_keywords_result: Optional[List[KeywordDoc]] = None
        self._cache: Dict[
            Tuple[Optional[str], bool],
            Tuple[
                Optional[KeywordDoc],
                List[DiagnosticsEntry],
                Optional[List[KeywordDoc]],
                Optional[str],
            ],
        ] = {}

        self._all_keywords: Optional[List[LibraryEntry]] = None
        self._resource_keywords: Optional[List[ResourceEntry]] = None
        self._library_keywords: Optional[List[LibraryEntry]] = None

    def reset_diagnostics(self) -> None:
        self.diagnostics = []
        self.multiple_keywords_result = None
        self.result_bdd_prefix = None

    # TODO: make this threadsafe
    def find_keyword(
        self,
        name: Optional[str],
        *,
        raise_keyword_error: bool = False,
        handle_bdd_style: bool = True,
    ) -> Optional[KeywordDoc]:
        try:
            self.reset_diagnostics()

            cached = self._cache.get((name, handle_bdd_style), None)

            if cached is not None:
                self.diagnostics = cached[1]
                self.multiple_keywords_result = cached[2]
                self.result_bdd_prefix = cached[3]
                return cached[0]

            try:
                result = self._find_keyword(name, handle_bdd_style)
                if result is None:
                    self.diagnostics.append(
                        DiagnosticsEntry(
                            f"No keyword with name '{name}' found.",
                            DiagnosticSeverity.ERROR,
                            Error.KEYWORD_NOT_FOUND,
                        )
                    )
            except KeywordError as e:
                if e.multiple_keywords:
                    self._add_to_multiple_keywords_result(e.multiple_keywords)

                if raise_keyword_error:
                    raise

                result = None
                self.diagnostics.append(DiagnosticsEntry(str(e), DiagnosticSeverity.ERROR, Error.KEYWORD_ERROR))

            self._cache[(name, handle_bdd_style)] = (
                result,
                self.diagnostics,
                self.multiple_keywords_result,
                self.result_bdd_prefix,
            )

            return result
        except CancelSearchError:
            return None

    def _find_keyword(
        self,
        name: Optional[str],
        handle_bdd_style: bool = True,
    ) -> Optional[KeywordDoc]:
        if not name:
            self.diagnostics.append(
                DiagnosticsEntry(
                    "Keyword name cannot be empty.",
                    DiagnosticSeverity.ERROR,
                    Error.KEYWORD_ERROR,
                )
            )
            raise CancelSearchError
        if not isinstance(name, str):
            self.diagnostics.append(  # type: ignore
                DiagnosticsEntry(
                    "Keyword name must be a string.",
                    DiagnosticSeverity.ERROR,
                    Error.KEYWORD_ERROR,
                )
            )
            raise CancelSearchError

        result: Optional[KeywordDoc] = None

        if get_robot_version() >= (7, 0) and handle_bdd_style:
            result = self._get_bdd_style_keyword(name)

        if not result:
            result = self._get_keyword_from_self(name)

        if not result and "." in name:
            result = self._get_explicit_keyword(name)

        if not result:
            result = self._get_implicit_keyword(name)

        if get_robot_version() < (7, 0) and not result and handle_bdd_style:
            return self._get_bdd_style_keyword(name)

        return result

    def _get_keyword_from_self(self, name: str) -> Optional[KeywordDoc]:
        if get_robot_version() >= (6, 0):
            found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = [
                (None, v) for v in self.self_library_doc.keywords.iter_all(name)
            ]
            if len(found) > 1:
                found = self._select_best_matches(found)
                if len(found) > 1:
                    self.diagnostics.append(
                        DiagnosticsEntry(
                            self._create_multiple_keywords_found_message(name, found, implicit=False),
                            DiagnosticSeverity.ERROR,
                            Error.MULTIPLE_KEYWORDS,
                        )
                    )
                    raise CancelSearchError

            if len(found) == 1:
                # TODO warning if keyword found is defined in resource and suite
                return found[0][1]

            return None

        try:
            return self.self_library_doc.keywords.get(name, None)
        except KeywordError as e:
            self.diagnostics.append(DiagnosticsEntry(str(e), DiagnosticSeverity.ERROR, Error.KEYWORD_ERROR))
            raise CancelSearchError from e

    def _yield_owner_and_kw_names(self, full_name: str) -> Iterator[Tuple[str, ...]]:
        tokens = full_name.split(".")
        for i in range(1, len(tokens)):
            yield ".".join(tokens[:i]), ".".join(tokens[i:])

    def _get_explicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = []
        for owner_name, kw_name in self._yield_owner_and_kw_names(name):
            found.extend(self.find_keywords(owner_name, kw_name))

        if get_robot_version() >= (6, 0) and len(found) > 1:
            found = self._select_best_matches(found)

        if len(found) > 1:
            self.diagnostics.append(
                DiagnosticsEntry(
                    self._create_multiple_keywords_found_message(name, found, implicit=False),
                    DiagnosticSeverity.ERROR,
                    Error.MULTIPLE_KEYWORDS,
                )
            )
            raise CancelSearchError

        return found[0][1] if found else None

    def find_keywords(self, owner_name: str, name: str) -> List[Tuple[LibraryEntry, KeywordDoc]]:
        if self._all_keywords is None:
            self._all_keywords = list(
                chain(
                    self.namespace._libraries.values(),
                    self.namespace._resources.values(),
                )
            )

        if get_robot_version() >= (6, 0):
            result: List[Tuple[LibraryEntry, KeywordDoc]] = []
            for v in self._all_keywords:
                if eq_namespace(v.alias or v.name, owner_name):
                    result.extend((v, kw) for kw in v.library_doc.keywords.iter_all(name))
            return result

        result = []
        for v in self._all_keywords:
            if eq_namespace(v.alias or v.name, owner_name):
                kw = v.library_doc.keywords.get(name, None)
                if kw is not None:
                    result.append((v, kw))
        return result

    def _add_to_multiple_keywords_result(self, kw: Iterable[KeywordDoc]) -> None:
        if self.multiple_keywords_result is None:
            self.multiple_keywords_result = list(kw)
        else:
            self.multiple_keywords_result.extend(kw)

    def _create_multiple_keywords_found_message(
        self,
        name: str,
        found: Sequence[Tuple[Optional[LibraryEntry], KeywordDoc]],
        implicit: bool = True,
    ) -> str:
        self._add_to_multiple_keywords_result([k for _, k in found])

        if any(e[1].is_embedded for e in found):
            error = f"Multiple keywords matching name '{name}' found"
        else:
            error = f"Multiple keywords with name '{name}' found"

            if implicit:
                error += ". Give the full name of the keyword you want to use"

        names = sorted(f"{e[1].name if e[0] is None else f'{e[0].alias or e[0].name}.{e[1].name}'}" for e in found)
        return "\n    ".join([f"{error}:", *names])

    def _get_implicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        result = self._get_keyword_from_resource_files(name)
        if not result:
            return self._get_keyword_from_libraries(name)
        return result

    def _prioritize_same_file_or_public(
        self, entries: List[Tuple[Optional[LibraryEntry], KeywordDoc]]
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        matches = [h for h in entries if h[1].source == self.namespace.source]
        if matches:
            return matches

        matches = [handler for handler in entries if not handler[1].is_private()]

        return matches or entries

    def _select_best_matches(
        self, entries: List[Tuple[Optional[LibraryEntry], KeywordDoc]]
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        if len(entries) < 2:
            return entries

        normal = [hand for hand in entries if not hand[1].is_embedded]
        if normal:
            return normal

        matches = [hand for hand in entries if not self._is_worse_match_than_others(hand, entries)]
        return matches or entries

    def _is_worse_match_than_others(
        self,
        candidate: Tuple[Optional[LibraryEntry], KeywordDoc],
        alternatives: List[Tuple[Optional[LibraryEntry], KeywordDoc]],
    ) -> bool:
        for other in alternatives:
            if (
                candidate[1] is not other[1]
                and self._is_better_match(other, candidate)
                and not self._is_better_match(candidate, other)
            ):
                return True
        return False

    def _is_better_match(
        self,
        candidate: Tuple[Optional[LibraryEntry], KeywordDoc],
        other: Tuple[Optional[LibraryEntry], KeywordDoc],
    ) -> bool:
        return (
            other[1].matcher.embedded_arguments.match(candidate[1].name) is not None
            and candidate[1].matcher.embedded_arguments.match(other[1].name) is None
        )

    def _get_keyword_from_resource_files(self, name: str) -> Optional[KeywordDoc]:
        if self._resource_keywords is None:
            self._resource_keywords = list(chain(self.namespace._resources.values()))

        if get_robot_version() >= (6, 0):
            found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = []
            for v in self._resource_keywords:
                r = v.library_doc.keywords.get_all(name)
                if r:
                    found.extend([(v, k) for k in r])
        else:
            found = []
            for k in self._resource_keywords:
                s = k.library_doc.keywords.get(name, None)
                if s is not None:
                    found.append((k, s))

        if not found:
            return None

        if get_robot_version() >= (6, 0):
            if len(found) > 1:
                found = self._prioritize_same_file_or_public(found)

                if len(found) > 1:
                    found = self._select_best_matches(found)

                    if len(found) > 1:
                        found = self._get_keyword_based_on_search_order(found)

        else:
            if len(found) > 1:
                found = self._get_keyword_based_on_search_order(found)

        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                Error.MULTIPLE_KEYWORDS,
            )
        )
        raise CancelSearchError

    def _get_keyword_based_on_search_order(
        self, entries: List[Tuple[Optional[LibraryEntry], KeywordDoc]]
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        for libname in self.namespace.search_order:
            for e in entries:
                if e[0] is not None and eq_namespace(libname, e[0].alias or e[0].name):
                    return [e]

        return entries

    def _get_keyword_from_libraries(self, name: str) -> Optional[KeywordDoc]:
        if self._library_keywords is None:
            self._library_keywords = list(chain(self.namespace._libraries.values()))

        if get_robot_version() >= (6, 0):
            found: List[Tuple[Optional[LibraryEntry], KeywordDoc]] = []
            for v in self._library_keywords:
                r = v.library_doc.keywords.get_all(name)
                if r:
                    found.extend([(v, k) for k in r])
        else:
            found = []

            for k in self._library_keywords:
                s = k.library_doc.keywords.get(name, None)
                if s is not None:
                    found.append((k, s))

        if not found:
            return None

        if get_robot_version() >= (6, 0):
            if len(found) > 1:
                found = self._select_best_matches(found)
                if len(found) > 1:
                    found = self._get_keyword_based_on_search_order(found)
        else:
            if len(found) > 1:
                found = self._get_keyword_based_on_search_order(found)
            if len(found) == 2:
                found = self._filter_stdlib_runner(*found)

        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                Error.MULTIPLE_KEYWORDS,
            )
        )
        raise CancelSearchError

    def _filter_stdlib_runner(
        self,
        entry1: Tuple[Optional[LibraryEntry], KeywordDoc],
        entry2: Tuple[Optional[LibraryEntry], KeywordDoc],
    ) -> List[Tuple[Optional[LibraryEntry], KeywordDoc]]:
        stdlibs_without_remote = STDLIBS - {"Remote"}
        if entry1[0] is not None and entry1[0].name in stdlibs_without_remote:
            standard, custom = entry1, entry2
        elif entry2[0] is not None and entry2[0].name in stdlibs_without_remote:
            standard, custom = entry2, entry1
        else:
            return [entry1, entry2]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_custom_and_standard_keyword_conflict_warning_message(custom, standard),
                DiagnosticSeverity.WARNING,
                Error.CONFLICTING_LIBRARY_KEYWORDS,
            )
        )

        return [custom]

    def _create_custom_and_standard_keyword_conflict_warning_message(
        self,
        custom: Tuple[Optional[LibraryEntry], KeywordDoc],
        standard: Tuple[Optional[LibraryEntry], KeywordDoc],
    ) -> str:
        custom_with_name = standard_with_name = ""
        if custom[0] is not None and custom[0].alias is not None:
            custom_with_name = " imported as '%s'" % custom[0].alias
        if standard[0] is not None and standard[0].alias is not None:
            standard_with_name = " imported as '%s'" % standard[0].alias
        return (
            f"Keyword '{standard[1].name}' found both from a custom test library "
            f"'{'' if custom[0] is None else custom[0].name}'{custom_with_name} "
            f"and a standard library '{standard[1].name}'{standard_with_name}. "
            f"The custom keyword is used. To select explicitly, and to get "
            f"rid of this warning, use either "
            f"'{'' if custom[0] is None else custom[0].alias or custom[0].name}.{custom[1].name}' "
            f"or '{'' if standard[0] is None else standard[0].alias or standard[0].name}.{standard[1].name}'."
        )

    @functools.cached_property
    def bdd_prefix_regexp(self) -> "re.Pattern[str]":
        prefixes = (
            "|".join(
                self.namespace.languages.bdd_prefixes
                if self.namespace.languages is not None
                else ["given", "when", "then", "and", "but"]
            )
            .replace(" ", r"\s")
            .lower()
        )
        return re.compile(rf"({prefixes})\s", re.IGNORECASE)

    def _get_bdd_style_keyword(self, name: str) -> Optional[KeywordDoc]:
        match = self.bdd_prefix_regexp.match(name)
        if match:
            result = self._find_keyword(
                name[match.end() :], handle_bdd_style=False if get_robot_version() >= (7, 0) else True
            )
            if result:
                self.result_bdd_prefix = str(match.group(0))

            return result
        return None
