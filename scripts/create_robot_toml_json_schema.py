import json
import pathlib
import typing
from dataclasses import fields, is_dataclass
from typing import Any, Callable, Optional

import apischema

from robotcode.robot.config.model import RobotConfig

if __name__ == "__main__":

    def type_base_schema(tp: Any) -> Optional[apischema.schemas.Schema]:
        if not is_dataclass(tp):
            return None
        return apischema.schema(
            title=apischema.type_names.get_type_name(tp).json_schema,
            description=tp.__doc__,
        )

    def field_base_schema(tp: Any, name: str, alias: str) -> Optional[apischema.schemas.Schema]:
        title = alias.replace("_", " ").capitalize()
        tp = typing.get_origin(tp) or tp  # tp can be generic
        if is_dataclass(tp):
            field = next((x for x in fields(tp) if x.name == name), None)
            description = ""
            if field is not None:
                if "description" in field.metadata:
                    description = field.metadata["description"]
                if "robot_name" in field.metadata and field.metadata["robot_name"]:
                    description += (
                        ("\n" if description else "")
                        + "Corresponds to the "
                        + (
                            field.metadata["robot_name"][1:]
                            if field.metadata["robot_name"].startswith("+")
                            else field.metadata["robot_name"]
                        )
                        + "option of __robot__."
                    )

            if description:
                return apischema.schema(title=title, description=description)

        return apischema.schema(title=title)

    def method_base_schema(tp: Any, method: Callable[..., Any], alias: str) -> Optional[apischema.schemas.Schema]:
        return apischema.schema(
            title=alias.replace("_", " ").capitalize(),
            description=method.__doc__,
        )

    apischema.settings.base_schema.type = type_base_schema
    apischema.settings.base_schema.field = field_base_schema
    apischema.settings.base_schema.method = method_base_schema

    base_schema = apischema.schema(
        extra={
            "x-taplo-info": {
                "authors": ["d-biehl (https://github.com/d-biehl)"],
                "patterns": ["^(.*(/|\\\\)robot\\.toml|robot\\.toml)$"],
            }
        }
    )
    schema = apischema.json_schema.deserialization_schema(
        RobotConfig,
        additional_properties=False,
        aliaser=lambda x: x.replace("_", "-"),
        version=apischema.json_schema.JsonSchemaVersion.DRAFT_7,
        all_refs=True,
        schema=base_schema,
    )

    # schema["x-taplo-info"] = {
    #     "authors": ["d-biehl (https://github.com/d-biehl)"],
    #     "patterns": ["^(.*(/|\\\\)robot\\.toml|robot\\.toml)$"],
    # }

    json_str = json.dumps(schema, indent=2, sort_keys=True)
    pathlib.Path("etc", "robot.toml.json").write_text(json_str, "utf-8")
