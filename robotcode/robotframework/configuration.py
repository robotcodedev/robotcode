from typing import List, Tuple
from pydantic import BaseModel


class Model(BaseModel):
    class Config:

        allow_population_by_field_name = True
        # use_enum_values = True

        @classmethod
        def alias_generator(cls, string: str) -> str:
            return string.replace("_", "-")


class LanguageServerConfig(Model):
    mode: str
    tcp_port: int
    args: Tuple[str, ...]
    python: str


class RobotConfig(Model):
    args: Tuple[str, ...]
    pythonpath: List[str]


class RobotCodeConfig(Model):
    language_server: LanguageServerConfig
    robot: RobotConfig
