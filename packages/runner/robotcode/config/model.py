from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RobotConfig:
    args: List[str] = field(default_factory=list)
    python_path: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    variables: List[Dict[str, Any]] = field(default_factory=list)
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
