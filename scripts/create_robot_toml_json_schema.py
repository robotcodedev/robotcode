import json
import pathlib

import pydantic

from robotcode.robot.config.model import MainProfile

if __name__ == "__main__":

    class Config:
        title = "robot.toml"
        description = "Configuration for Robot Framework."
        schema_extra = {
            "additionalProperties": False,
        }

        @classmethod
        def alias_generator(cls, string: str) -> str:
            # this is the same as `alias_generator = to_camel` above
            return string.replace("_", "-")

    model = pydantic.dataclasses.create_pydantic_model_from_dataclass(MainProfile, config=Config)  # type: ignore
    schema = model.schema()

    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["$id"] = "robotframework:https://raw.githubusercontent.com/d-biehl/robotcode/main/etc/robot.json"
    schema["x-taplo-info"] = {
        "authors": ["d-biehl (https://github.com/d-biehl)"],
        "patterns": ["^(.*(/|\\\\)robot\\.toml|robot\\.toml)$"],
    }
    json_str = json.dumps(schema, indent=2, sort_keys=True)
    pathlib.Path("etc", "robot.toml.json").write_text(json_str, "utf-8")
