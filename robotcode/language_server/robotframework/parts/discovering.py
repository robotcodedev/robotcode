from __future__ import annotations

import ast
import asyncio
import time
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, List, Optional, cast

from ....jsonrpc2.protocol import rpc_method
from ....utils.async_tools import check_canceled, check_canceled_sync, threaded
from ....utils.logging import LoggingDescriptor
from ....utils.uri import Uri
from ...common.lsp_types import (
    DocumentUri,
    Model,
    Position,
    Range,
    TextDocumentIdentifier,
)
from ..configuration import RobotConfig
from ..utils.async_ast import AsyncVisitor
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class GetAllTestsParams(Model):
    workspace_folder: str
    paths: Optional[List[str]] = None
    suites: Optional[List[str]] = None


@dataclass(repr=False)
class GetTestsParams(Model):
    text_document: TextDocumentIdentifier
    base_name: Optional[str]


@dataclass(repr=False)
class GetTestsFromDocumentParams(Model):
    text_document: TextDocumentIdentifier


@dataclass(repr=False)
class TestItem(Model):
    type: str
    id: str
    label: str
    longname: str
    uri: Optional[DocumentUri] = None
    children: Optional[List[TestItem]] = None
    description: Optional[str] = None
    range: Optional[Range] = None
    tags: Optional[List[str]] = None
    error: Optional[str] = None


class FindTestCasesVisitor(AsyncVisitor):
    async def get(self, source: DocumentUri, model: ast.AST, base_name: Optional[str]) -> List[TestItem]:
        self._results: List[TestItem] = []
        self.source = source
        self.path = Uri(source).to_path().resolve()
        self.base_name = base_name
        await self.visit(model)
        return self._results

    async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import TestCaseSection

        if isinstance(node, TestCaseSection):
            await self.generic_visit(node)

    async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import TestCase
        from robot.parsing.model.statements import Tags

        test_case = cast(TestCase, node)
        longname = f"{self.base_name}.{test_case.name}" if self.base_name else test_case.name
        self._results.append(
            TestItem(
                type="test",
                id=f"{self.path};{longname};{test_case.lineno}",
                longname=longname,
                label=test_case.name,
                uri=self.source,
                range=Range(
                    start=Position(line=test_case.lineno - 1, character=test_case.col_offset),
                    end=Position(
                        line=(test_case.end_lineno if test_case.end_lineno != -1 else test_case.lineno) - 1,
                        character=test_case.end_col_offset if test_case.end_col_offset != -1 else test_case.col_offset,
                    ),
                ),
                tags=[str(tag) for tag in chain(*[tags.values for tags in test_case.body if isinstance(tags, Tags)])],
            )
        )


class DiscoveringProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        self._patch()

    def _patch(self) -> None:
        from robot.api.parsing import File, get_model
        from robot.running import TestSuite
        from robot.running.builder.builders import RobotParser, TestSuiteBuilder

        from ..utils.version import get_robot_version

        def get_document_text(source: str) -> str:
            check_canceled_sync()

            if self.parent.loop:
                doc = self.parent.documents.get_sync(Uri.from_path(source).normalized())
                if doc is not None:
                    return doc.text_sync()

            return source

        def get_source(self: Any, source: str) -> str:
            return get_document_text(source)

        RobotParser._get_source = get_source

        orig = RobotParser._build

        def my_get_model_v4(source: str, data_only: bool = False, curdir: Optional[str] = None) -> Any:
            check_canceled_sync()
            try:
                return get_model(source, data_only, curdir)
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self._logger.critical(f"Can't parse {source}: {e}")
                return File(source=source)

        def my_get_model_v6(
            source: str, data_only: bool = False, curdir: Optional[str] = None, lang: Any = None
        ) -> Any:
            check_canceled_sync()
            try:
                return get_model(source, data_only, curdir, lang)
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self._logger.critical(f"Can't parse {source}: {e}")
                return File(source=source)

        my_get_model = my_get_model_v4 if get_robot_version() < (6, 0) else my_get_model_v6

        def build(
            self: Any,
            suite: TestSuite,
            source: str,
            defaults: Any,
            model: Any = None,
            get_model: Any = my_get_model,
        ) -> TestSuite:
            check_canceled_sync()

            return orig(self, suite, source, defaults, model, get_model)

        RobotParser._build = build

        def _validate_test_counts(self: Any, suite: TestSuite, multisource: bool = False) -> None:
            # we don't need this
            pass

        TestSuiteBuilder._validate_test_counts = _validate_test_counts

    async def get_config(self, workspace_uri: str) -> Optional[RobotConfig]:
        folder = self.parent.workspace.get_workspace_folder(workspace_uri)
        if folder is None:
            return None

        return await self.parent.workspace.get_configuration(RobotConfig, folder.uri)

    @rpc_method(name="robot/discovering/getTestsFromWorkspace", param_type=GetAllTestsParams)
    @threaded()
    async def get_tests_from_workspace(
        self,
        workspace_folder: str,
        paths: Optional[List[str]] = None,
        suites: Optional[List[str]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> List[TestItem]:
        from robot.output.logger import LOGGER
        from robot.running import TestCase, TestSuite
        from robot.running.builder.builders import TestSuiteBuilder

        from ..utils.version import get_robot_version

        async def generate(suite: TestSuite) -> TestItem:
            children: List[TestItem] = []

            await check_canceled()

            test: TestCase
            for test in suite.tests:
                children.append(
                    TestItem(
                        type="test",
                        id=f"{Path(test.source).resolve() if test.source is not None else ''};"
                        f"{test.longname};{test.lineno}",
                        label=test.name,
                        longname=test.longname,
                        uri=str(Uri.from_path(test.source)) if test.source else None,
                        range=Range(
                            start=Position(line=test.lineno - 1, character=0),
                            end=Position(line=test.lineno - 1, character=0),
                        ),
                        tags=[t for t in test.tags],
                    )
                )

            for s in suite.suites:
                children.append(await generate(s))

            return TestItem(
                type="suite",
                id=f"{Path(suite.source).resolve() if suite.source is not None else ''};{suite.longname}",
                label=suite.name,
                longname=suite.longname,
                uri=str(Uri.from_path(suite.source)) if suite.source else None,
                children=children,
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=0, character=0),
                )
                if suite.source
                else None,
            )

        await self.parent.robot_workspace.documents_loaded.wait()

        start = time.monotonic()

        self._logger.info("Start discovering tests")

        workspace_path = Uri(workspace_folder).to_path()
        canceled = False
        LOGGER._cache_only = True
        try:
            config = await self.get_config(workspace_folder)
            rpa_mode = config.get_rpa_mode() if config is not None else None
            languages = await self.parent.documents_cache.get_workspace_languages(workspace_folder)
            parsers = config.parsers if config is not None else None

            if paths is None and config is not None:
                paths = config.paths

            if paths and len(paths):

                def normalize_paths(paths: List[str]) -> Iterator[str]:

                    for path in paths:

                        p = Path(path)

                        if not p.is_absolute():
                            p = Path(workspace_path, p)

                        if p.exists():
                            yield str(p)

                def nonexisting_paths(paths: List[str]) -> Iterator[str]:

                    for path in paths:

                        p = Path(path)

                        if not p.is_absolute():
                            p = Path(workspace_path, p)

                        if not p.exists():
                            yield str(p)

                valid_paths = [i for i in normalize_paths(paths)]

                if get_robot_version() >= (6, 1):
                    builder = TestSuiteBuilder(
                        included_suites=suites if suites else None,
                        rpa=rpa_mode,
                        lang=languages,
                        parsers=parsers,
                    )
                elif get_robot_version() >= (6, 0):
                    builder = TestSuiteBuilder(
                        included_suites=suites if suites else None,
                        rpa=rpa_mode,
                        lang=languages,
                    )
                else:
                    builder = TestSuiteBuilder(included_suites=suites if suites else None, rpa=rpa_mode)

                suite: Optional[TestSuite] = builder.build(*valid_paths) if valid_paths else None
                suite_item = [await generate(suite)] if suite else []

                return [
                    TestItem(
                        type="workspace",
                        id=str(Path.cwd().resolve()),
                        label=Path.cwd().name,
                        longname=Path.cwd().name,
                        uri=str(Uri.from_path(Path.cwd())),
                        children=[
                            *suite_item,
                            *[
                                TestItem(
                                    type="error",
                                    id=f"{i};ERROR",
                                    longname="error",
                                    label=i,
                                    error=f"Parsing '{i}' failed: File or directory to does not exist.",
                                )
                                for i in nonexisting_paths(paths)
                            ],
                        ],
                    )
                ]
            else:
                if get_robot_version() >= (6, 1):
                    builder = TestSuiteBuilder(
                        included_suites=suites if suites else None,
                        rpa=rpa_mode,
                        lang=languages,
                        parsers=parsers,
                    )
                elif get_robot_version() >= (6, 0):
                    builder = TestSuiteBuilder(included_suites=suites if suites else None, rpa=rpa_mode, lang=languages)
                else:
                    builder = TestSuiteBuilder(included_suites=suites if suites else None, rpa=rpa_mode)
                return [await generate(builder.build(str(workspace_path)))]
        except (SystemExit, KeyboardInterrupt):
            raise
        except asyncio.CancelledError:
            canceled = True
            self._logger.info("Tests discovery canceled")
            raise
        except BaseException as e:
            self._logger.info(f"Failed to discover tests: {e}")
            return [
                TestItem(
                    type="error",
                    id=str(Uri.from_path(Path.cwd().resolve())),
                    longname="error",
                    label=Path.cwd().name,
                    error=str(e),
                )
            ]
        finally:
            if not canceled:
                self._logger.info(f"Tests discovery took {time.monotonic() - start}s")

    @rpc_method(name="robot/discovering/getTestsFromDocument", param_type=GetTestsParams)
    @threaded()
    async def get_tests_from_document(
        self, text_document: TextDocumentIdentifier, base_name: Optional[str], *args: Any, **kwargs: Any
    ) -> List[TestItem]:

        try:
            return await FindTestCasesVisitor().get(
                text_document.uri,
                await self.parent.documents_cache.get_model(
                    await self.parent.documents.get_or_open_document(
                        Uri(text_document.uri).to_path(), language_id="robotframework"
                    )
                ),
                base_name,
            )
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return []
