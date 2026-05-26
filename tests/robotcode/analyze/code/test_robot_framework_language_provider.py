from typing import Any, List, Set

from pytest_mock import MockerFixture

from robotcode.analyze.code.robot_framework_language_provider import RobotFrameworkLanguageProvider


def _registered_handlers(mocker: MockerFixture, collect_unused: bool) -> Set[str]:
    """
    Instantiate the provider with a mocked DiagnosticsContext and return the
    names of the methods that ended up registered as document_collectors.
    """
    mocker.patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
    mocker.patch.object(RobotFrameworkLanguageProvider, "_update_python_path")

    ctx = mocker.MagicMock()
    ctx.collect_unused = collect_unused

    collectors: List[Any] = []
    ctx.diagnostics.document_collectors.add.side_effect = lambda h: collectors.append(h)

    RobotFrameworkLanguageProvider(ctx)

    return {getattr(h, "__name__", repr(h)) for h in collectors}


class TestConditionalHandlerRegistration:
    def test_collect_unused_false_only_registers_base_collector(self, mocker: MockerFixture) -> None:
        names = _registered_handlers(mocker, collect_unused=False)

        assert "collect_diagnostics" in names
        assert "collect_unused_keywords" not in names
        assert "collect_unused_variables" not in names

    def test_collect_unused_true_registers_all_three_collectors(self, mocker: MockerFixture) -> None:
        names = _registered_handlers(mocker, collect_unused=True)

        assert {"collect_diagnostics", "collect_unused_keywords", "collect_unused_variables"} <= names

    def test_folder_and_document_analyzers_always_registered(self, mocker: MockerFixture) -> None:
        mocker.patch("robotcode.analyze.code.robot_framework_language_provider.DocumentsCacheHelper")
        mocker.patch.object(RobotFrameworkLanguageProvider, "_update_python_path")

        ctx = mocker.MagicMock()
        ctx.collect_unused = False

        RobotFrameworkLanguageProvider(ctx)

        ctx.diagnostics.folder_analyzers.add.assert_called_once()
        ctx.diagnostics.document_analyzers.add.assert_called_once()
