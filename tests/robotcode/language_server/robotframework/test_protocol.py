from robotcode.core.utils.dataclasses import from_dict
from robotcode.language_server.robotframework.protocol import RobotInitializationOptions


def test_documentation_viewer_links_are_off_by_default() -> None:
    assert from_dict({}, RobotInitializationOptions).documentation_viewer_links is False


def test_documentation_viewer_links_option() -> None:
    options = from_dict(
        {
            "pythonPath": ["lib"],
            "documentationViewerLinks": True,
            "settings": {"robotcode": {}},
        },
        RobotInitializationOptions,
    )

    assert options.documentation_viewer_links is True
    assert options.python_path == ["lib"]
