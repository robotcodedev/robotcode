"""Generates the reference of the VS Code settings, `docs/src/content/docs/reference/vscode-settings.md`, from the
settings the extension's `package.json` contributes. The frontmatter of the page is kept."""

import json
import re
import textwrap
from pathlib import Path
from typing import Any, Dict, List

PACKAGE_JSON = Path("package.json")
SETTINGS_DOC = Path("docs/src/content/docs/reference/vscode-settings.md")

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

INTRO = """\
These are the settings of the RobotCode extension for VS Code, in the categories the Settings editor shows. To list
them in VS Code, open the Settings editor with **Preferences: Open Settings (UI)** and filter it with
`@ext:d-biehl.robotcode`. Which options belong into `robot.toml` and which into the settings of VS Code is explained in
[Configuring RobotCode in VS Code](/guides/vscode/configuration/)."""

# Where a setting can be set, by its scope, as VS Code's extension API describes the scopes; `window` is the default.
SCOPES = {
    "application": "user settings only",
    "machine": "user or remote settings only",
    "machine-overridable": "user, remote, workspace and folder settings",
    "window": "user, remote and workspace settings",
    "resource": "user, remote, workspace and folder settings",
    "language-overridable": "user, remote, workspace and folder settings, also per language",
}

# Defaults longer than this are shown as a JSON block instead of inline code.
INLINE_DEFAULT_LENGTH = 60


def _value(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _type(setting: Dict[str, Any]) -> str:
    types = setting["type"] if isinstance(setting["type"], list) else [setting["type"]]
    result = []
    for t in types:
        items = setting.get("items")
        values = setting.get("additionalProperties")
        if t == "array" and isinstance(items, dict) and "type" in items:
            result.append(f"`array` of `{items['type']}`")
        elif t == "object" and isinstance(values, dict) and "type" in values:
            result.append(f"`object` with `{values['type']}` values")
        else:
            result.append(f"`{t}`")
    return " or ".join(result)


def _default(setting: Dict[str, Any]) -> List[str]:
    text = json.dumps(setting["default"], ensure_ascii=False)
    if len(text) <= INLINE_DEFAULT_LENGTH:
        return [f"- **Default:** `{text}`"]
    block = json.dumps(setting["default"], ensure_ascii=False, indent=2)
    return ["- **Default:**", "", "  ```json", textwrap.indent(block, "  "), "  ```"]


def _allowed_values(setting: Dict[str, Any]) -> List[str]:
    if "enum" not in setting:
        return []
    descriptions = setting.get("markdownEnumDescriptions") or setting.get("enumDescriptions") or []
    lines = ["- **Allowed values:**"]
    for index, value in enumerate(setting["enum"]):
        description = descriptions[index] if index < len(descriptions) else ""
        lines.append(f"  - `{_value(value)}`" + (f": {description}" if description else ""))
    return lines


def _setting(key: str, setting: Dict[str, Any]) -> List[str]:
    lines = [f"### `{key}` {{#{key}}}", ""]

    deprecation = setting.get("markdownDeprecationMessage") or setting.get("deprecationMessage")
    if deprecation:
        lines += [":::caution[Deprecated]", deprecation, ":::", ""]

    description = setting.get("markdownDescription") or setting.get("description")
    if description:
        lines += [description.strip(), ""]

    lines.append(f"- **Type:** {_type(setting)}")
    lines += _default(setting)
    lines += _allowed_values(setting)
    if "minimum" in setting:
        lines.append(f"- **Minimum:** `{_value(setting['minimum'])}`")
    if "maximum" in setting:
        lines.append(f"- **Maximum:** `{_value(setting['maximum'])}`")
    lines.append(f"- **Can be set in:** {SCOPES[setting.get('scope', 'window')]}")
    lines.append("")
    return lines


def generate() -> str:
    """The body of the page: one section per setting category of `package.json`, in the declared order, and in it one
    section per setting, whose heading ID is the setting's name."""
    configuration = json.loads(PACKAGE_JSON.read_text("utf-8"))["contributes"]["configuration"]
    categories = configuration if isinstance(configuration, list) else [configuration]

    lines = [INTRO, ""]
    for category in categories:
        lines += [f"## {category['title']}", ""]
        for key, setting in category.get("properties", {}).items():
            lines += _setting(key, setting)

    return "\n".join(lines).strip("\n") + "\n"


def main() -> None:
    # The frontmatter is maintained in the page.
    frontmatter = FRONTMATTER.match(SETTINGS_DOC.read_text("utf-8"))
    if frontmatter is None:
        raise SystemExit(f"{SETTINGS_DOC}: no frontmatter")

    SETTINGS_DOC.write_text(f"{frontmatter.group(0)}\n{generate()}", "utf-8")


if __name__ == "__main__":
    main()
