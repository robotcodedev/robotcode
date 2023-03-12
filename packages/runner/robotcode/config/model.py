from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Union


@dataclass
class ValidateMixin:
    def validate(self) -> None:
        for f in fields(self):
            if f.default_factory is not None:
                continue

    def convert(self) -> None:
        for f in fields(self):
            converter = f.metadata.get("convert")
            if converter is not None:
                setattr(self, f.name, converter(getattr(self, f.name)))

    def __post_init__(self) -> None:
        self.convert()
        self.validate()


def combine_dict(list_of_dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    combined_dict: Dict[str, Any] = {}
    for d in list_of_dicts:
        combined_dict.update(d)
    return combined_dict


@dataclass
class RobotConfig(ValidateMixin):
    args: List[str] = field(default_factory=list)
    python_path: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    variables: Union[Dict[str, Any], List[Dict[str, Any]], None] = field(
        default=None, metadata={"convert": combine_dict}
    )
    variable_files: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    output_dir: Optional[str] = None
    output_file: Optional[str] = None
    log_file: Optional[str] = None
    debug_file: Optional[str] = None
    log_level: Optional[str] = None
    # mode: Optional[RpaMode] = None
    languages: Optional[List[str]] = None
    parsers: Optional[List[str]] = None
    console: Optional[str] = None
