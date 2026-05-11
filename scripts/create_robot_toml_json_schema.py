import json
import pathlib
import re
from dataclasses import dataclass, is_dataclass
from inspect import cleandoc
from typing import Any, Dict, Optional, Union

from mashumaro.jsonschema import build_json_schema
from mashumaro.jsonschema.plugins import BasePlugin
from mashumaro.jsonschema.schema import Instance

from robotcode.analyze.config import AnalyzeConfig
from robotcode.robot.config.model import RobotConfig as OrigRobotConfig
from robotcode.robot.config.model import field


@dataclass
class ToolConfig:
    """Tool configurations."""

    robotcode_analyze: Optional[AnalyzeConfig] = field(
        description=AnalyzeConfig.__doc__,
        alias="robotcode-analyze",
    )


@dataclass
class RobotConfig(OrigRobotConfig):
    tool: Union[ToolConfig, Dict[str, Any], None] = field(description="Tool configurations.")


RobotConfig.__doc__ = OrigRobotConfig.__doc__


class DefsOnlyDocstringDescriptionPlugin(BasePlugin):
    """Apply dataclass docstrings to $defs entries instead of each $ref use site."""

    def get_schema(self, instance: Instance, ctx: Any, schema: Any = None) -> None:
        if not (schema and is_dataclass(instance.type) and instance.type.__doc__):
            return
        description = cleandoc(instance.type.__doc__)
        reference = getattr(schema, "reference", None)
        if reference:
            def_name = reference.rsplit("/", 1)[-1]
            def_schema = ctx.definitions.get(def_name)
            if def_schema is not None and not def_schema.description:
                def_schema.description = description
        else:
            if not schema.description:
                schema.description = description
        return


class DefsPropertyTitlePlugin(BasePlugin):
    """Apply human-readable titles to dataclass definition properties in $defs."""

    def get_schema(self, instance: Instance, ctx: Any, schema: Any = None) -> None:
        if not (schema and is_dataclass(instance.type)):
            return

        reference = getattr(schema, "reference", None)
        if reference:
            def_name = reference.rsplit("/", 1)[-1]
            target_schema = ctx.definitions.get(def_name)
            if target_schema is None:
                return
        else:
            target_schema = schema

        if not target_schema.title:
            target_schema.title = _to_title(instance.type.__name__)

        properties = getattr(target_schema, "properties", None)
        if isinstance(properties, dict):
            for key, prop_schema in properties.items():
                if not prop_schema.title and not getattr(prop_schema, "reference", None):
                    prop_schema.title = _to_title(key)
        return


def _to_title(name: str) -> str:
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", name.replace("-", " ").replace("_", " ")).split()
    if not words:
        return name
    return " ".join(word[0].upper() + word[1:] for word in words if word)


def _extract_toml_examples(description: str) -> list[str]:
    """Extract TOML code blocks from markdown description."""
    if not description:
        return []

    examples = []
    # Match ```toml ... ``` blocks (handles variable whitespace and line endings)
    pattern = r"```toml\s*\n([\s\S]*?)\n```"
    for match in re.finditer(pattern, description, re.MULTILINE):
        toml_code = match.group(1).strip()
        if toml_code:
            examples.append(toml_code)

    return examples


def _to_anchor(value: str) -> str:
    """Create a stable markdown anchor from a heading-like value."""
    anchor = value.strip().lower().replace(".", "-")
    anchor = re.sub(r"[^\w\s-]", "", anchor)
    anchor = re.sub(r"[-\s]+", "-", anchor)
    return anchor.strip("-")


def _post_process_schema(
    schema_dict: dict,
    base_url: str = "https://robotcode.io/03_reference/config",
) -> None:
    """Add markdownDescription, x-taplo links, and examples to schema.

    Modifies schema_dict in place.
    """

    defs = schema_dict.get("$defs", {})
    visited: set[tuple[str, str]] = set()

    def add_common_metadata(node: dict) -> None:
        """Add markdownDescription and examples from description field."""
        # Add markdownDescription from description
        if "description" in node and "markdownDescription" not in node:
            node["markdownDescription"] = node["description"]

        # Extract examples from description
        if "description" in node and "examples" not in node:
            examples = _extract_toml_examples(node["description"])
            if examples:
                node["examples"] = examples

    def add_link(node: dict, path: str) -> None:
        """Add x-taplo link to documentation for this property."""
        # Taplo ignores custom fields on objects that have direct $ref.
        if not path or "x-taplo" in node or "$ref" in node:
            return
        node["x-taplo"] = {
            "links": {
                "key": f"{base_url}#{_to_anchor(path)}",
            }
        }

    def extract_ref_names(node: dict) -> list[str]:
        """Extract all referenced definition names from a schema node."""
        ref_names = []

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            ref_names.append(ref.rsplit("/", 1)[-1])

        for combinator in ("anyOf", "oneOf", "allOf"):
            entries = node.get(combinator)
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        sub_ref = entry.get("$ref")
                        if isinstance(sub_ref, str) and sub_ref.startswith("#/$defs/"):
                            ref_names.append(sub_ref.rsplit("/", 1)[-1])

        items = node.get("items")
        if isinstance(items, dict):
            item_ref = items.get("$ref")
            if isinstance(item_ref, str) and item_ref.startswith("#/$defs/"):
                ref_names.append(item_ref.rsplit("/", 1)[-1])

        return ref_names

    def mapped_child_path(path: str) -> str:
        """Map property path to documentation anchor path (handles special cases)."""
        # Docs describe profile entries as [profile].* even though the key is profiles/extend-profiles.
        if path in {"profiles", "extend-profiles"}:
            return "profile"
        return path

    def process_schema(node: dict, path_prefix: str) -> None:
        """Recursively process schema node to add metadata and links."""
        add_common_metadata(node)

        properties = node.get("properties")
        if isinstance(properties, dict):
            process_properties(properties, path_prefix)

        for ref_name in extract_ref_names(node):
            process_def(ref_name, path_prefix)

        items = node.get("items")
        if isinstance(items, dict):
            process_schema(items, path_prefix)

        additional_properties = node.get("additionalProperties")
        if isinstance(additional_properties, dict):
            process_schema(additional_properties, mapped_child_path(path_prefix))

        pattern_properties = node.get("patternProperties")
        if isinstance(pattern_properties, dict):
            for schema in pattern_properties.values():
                if isinstance(schema, dict):
                    process_schema(schema, mapped_child_path(path_prefix))

        for combinator in ("anyOf", "oneOf", "allOf"):
            entries = node.get(combinator)
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        process_schema(entry, path_prefix)

    def process_properties(properties_dict: dict, path_prefix: str) -> None:
        """Process all properties in a properties dictionary."""
        for prop_name, prop_schema in properties_dict.items():
            if not isinstance(prop_schema, dict):
                continue

            prop_path = f"{path_prefix}.{prop_name}" if path_prefix else prop_name
            add_common_metadata(prop_schema)
            add_link(prop_schema, prop_path)
            process_schema(prop_schema, prop_path)

    def process_def(def_name: str, path_prefix: str) -> None:
        """Process a definition from $defs, avoiding infinite recursion via visited tracking."""
        visit_key = (def_name, path_prefix)
        if visit_key in visited:
            return
        visited.add(visit_key)

        def_schema = defs.get(def_name)
        if not isinstance(def_schema, dict):
            return

        add_common_metadata(def_schema)
        process_schema(def_schema, path_prefix)

    # Process all defs for markdownDescription/examples on definition level.
    for def_schema in defs.values():
        if isinstance(def_schema, dict):
            add_common_metadata(def_schema)

    # Process inline root properties.
    root_properties = schema_dict.get("properties")
    if isinstance(root_properties, dict):
        process_properties(root_properties, "")

    # Process referenced root definition when all_refs=True.
    root_ref = schema_dict.get("$ref")
    if isinstance(root_ref, str) and root_ref.startswith("#/$defs/"):
        process_def(root_ref.rsplit("/", 1)[-1], "")


def _convert_to_draft7_schema(schema_dict: dict) -> None:
    """Convert generated schema to draft-07 compatible structure in-place."""

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if "$defs" in node:
                defs_value = node.pop("$defs")
                if "definitions" not in node:
                    node["definitions"] = defs_value
                elif isinstance(node["definitions"], dict) and isinstance(defs_value, dict):
                    merged = dict(defs_value)
                    merged.update(node["definitions"])
                    node["definitions"] = merged

            for value in list(node.values()):
                visit(value)

            reference = node.get("$ref")
            if isinstance(reference, str):
                node["$ref"] = reference.replace("#/$defs/", "#/definitions/")

        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(schema_dict)
    schema_dict["$schema"] = "http://json-schema.org/draft-07/schema#"


if __name__ == "__main__":
    schema_dict = build_json_schema(
        RobotConfig,
        all_refs=True,
        with_dialect_uri=True,
        plugins=[DefsOnlyDocstringDescriptionPlugin(), DefsPropertyTitlePlugin()],
    ).to_dict()

    schema_dict.update(
        {
            "$comment": "Schema for RobotCode's robot.toml configuration. "
            "See https://robotcode.io/03_reference/config for full documentation.",
            "$id": "https://www.robotcode.io/schemas/robot.toml.json",
            "title": "JSON schema for RobotCode's Robot Framework configuration",
            "description": OrigRobotConfig.__doc__,
            "x-taplo-info": {
                "authors": ["robotcodedev (https://github.com/robotcodedev)"],
                "patterns": ["^(.*(/|\\\\)robot\\.toml|robot\\.toml)$"],
            },
            "additionalProperties": False,
        }
    )

    # Apply enhancements: markdownDescription, x-taplo links, examples
    _post_process_schema(schema_dict)

    # Convert to draft-07 for SchemaStore compatibility.
    _convert_to_draft7_schema(schema_dict)

    json_str = json.dumps(schema_dict, indent=2, sort_keys=True)
    pathlib.Path("docs", "public", "schemas", "robot.toml.json").write_text(json_str, "utf-8")
