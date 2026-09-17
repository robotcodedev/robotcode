import json
from pathlib import Path


def test_shared_condition_has_no_context_specific_documentation_link() -> None:
    schema_path = Path(__file__).parents[4] / "docs/public/schemas/robot.toml.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    condition_if = schema["definitions"]["Condition"]["properties"]["if"]

    assert "x-taplo" not in condition_if
