from types import SimpleNamespace
from typing import Any, cast

from pytest_mock import MockerFixture
from robot.parsing.lexer.tokens import Token

from robotcode.analyze.code.robot_framework_language_provider import RobotFrameworkLanguageProvider
from robotcode.core.lsp.types import Diagnostic
from robotcode.robot.diagnostics.entities import LocalVariableDefinition
from robotcode.robot.diagnostics.namespace import DocumentType

SOURCE = "/suite.robot"


def _local_variable(name_base: str, line_no: int) -> LocalVariableDefinition:
    name_token = Token(Token.VARIABLE, name_base, line_no, 0)
    return LocalVariableDefinition(
        name=f"${{{name_base}}}",
        name_token=name_token,
        line_no=line_no,
        col_offset=0,
        end_line_no=line_no,
        end_col_offset=len(name_base),
        source=SOURCE,
    )


def test_cli_unused_variable_diagnostics_ignore_intentionally_unused_variables(mocker: MockerFixture) -> None:
    intentionally_unused = _local_variable("_", 1)
    prefixed_intentionally_unused = _local_variable("_ignored", 2)
    unused = _local_variable("unused", 3)

    variable_references: dict[LocalVariableDefinition, set[Any]] = {
        intentionally_unused: set(),
        prefixed_intentionally_unused: set(),
        unused: set(),
    }
    namespace = SimpleNamespace(source=SOURCE, variable_references=variable_references)
    document_cache = mocker.Mock()
    document_cache.get_namespace.return_value = namespace
    document_cache.get_project_index.return_value = mocker.Mock()
    document_cache.get_document_type.return_value = DocumentType.GENERAL

    provider = cast(Any, object.__new__(RobotFrameworkLanguageProvider))
    provider._document_cache = document_cache

    diagnostics = cast(list[Diagnostic], provider.collect_unused_variables(mocker.Mock(), mocker.Mock()))

    assert [diagnostic.message for diagnostic in diagnostics] == ["Variable '${unused}' is not used."]
    assert [diagnostic.code for diagnostic in diagnostics] == ["VariableNotUsed"]
