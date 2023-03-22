import json
import pathlib
from typing import Any, Dict

import pydantic

from robotcode.robot.config.model import RobotConfig

if __name__ == "__main__":

    class Config:
        @staticmethod
        def schema_extra(schema: Dict[str, Any], model: Any) -> None:
            if "additionalProperties" not in schema:
                schema["additionalProperties"] = False

            for prop, value in schema.get("properties", {}).items():
                if isinstance(value, dict):
                    to_remove = []
                    for key, val in value.items():
                        if callable(val):
                            to_remove.append(key)
                        if key.startswith("robot_"):
                            to_remove.append(key)
                    for key in to_remove:
                        value.pop(key)

                field = [x for x in model.__fields__.values() if x.alias == prop][0]
                if field.allow_none:
                    if "type" in value:
                        value["anyOf"] = [{"type": value.pop("type")}]

                    elif "$ref" in value:
                        if issubclass(field.type_, pydantic.BaseModel):
                            value["title"] = field.type_.__config__.title or field.type_.__name__
                        value["anyOf"] = [{"$ref": value.pop("$ref")}]
                    elif "anyOf" not in value:
                        value["anyOf"] = []
                    value["anyOf"].append({"type": "null"})

        @classmethod
        def alias_generator(cls, string: str) -> str:
            return string.replace("_", "-")

    model = pydantic.dataclasses.create_pydantic_model_from_dataclass(RobotConfig, config=Config)  # type: ignore
    schema = model.schema()

    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["$id"] = "robotframework:https://raw.githubusercontent.com/d-biehl/robotcode/main/etc/robot.json"
    schema["x-taplo-info"] = {
        "authors": ["d-biehl (https://github.com/d-biehl)"],
        "patterns": ["^(.*(/|\\\\)robot\\.toml|robot\\.toml)$"],
    }
    json_str = json.dumps(schema, indent=2, sort_keys=True)
    pathlib.Path("etc", "robot.toml.json").write_text(json_str, "utf-8")
