import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from robot.conf import RebotSettings, RobotSettings
from robot.libdoc import USAGE as LIBDOC_USAGE
from robot.rebot import USAGE as REBOT_USAGE
from robot.run import USAGE as ROBOT_USAGE
from robot.testdoc import USAGE as TESTDOC_USAGE
from robotcode.core.dataclasses import to_snake_case

EXAMPLES_RE = re.compile(r"(?P<spaces>^\s*)Examples:\s*(?P<rest>.*)", re.MULTILINE)
OPTIONS_RE = re.compile(
    r"^(\s*(?P<short>-\S+))?(\s*(?P<short1>-\S+))?(\s*(?P<long>--\w+))(\s+(?P<param>\S+))?(\s+(?P<star>\*))?((\s\s)|\n)+\s*(?P<desc>.+)",
    re.DOTALL | re.MULTILINE,
)


type_templates = {
    "console": 'Literal["verbose", "dotted", "skipped", "quiet", "none"]',
    "listeners": "Dict[str, List[Union[str, StringExpression]]]",
    "parser": "Dict[str, List[Union[str, StringExpression]]]",
    "pre_rebot_modifiers": "Dict[str, List[Union[str, StringExpression]]]",
    "pre_run_modifiers": "Dict[str, List[Union[str, StringExpression]]]",
    "randomize": 'Union[str, Literal["all", "suites", "tests", "none"]]',
    "tag_stat_combine": "List[Union[str, Dict[str, str]]]",
}

name_corrections = {
    "console": "Console",
    "dotted": "Dotted",
    "exclude": "Excludes",
    "extension": "Extensions",
    "include": "Includes",
    "language": "Languages",
    "quiet": "Quiet",
    "rpa": "rpa",
    "suite": "Suites",
    "task": "Tasks",
    "test": "Tests",
    "xunit": "xunit",
    "statusrc": "NoStatusRc",
}

LF = "\n"


def generate(
    output: List[str],
    usage: str,
    options: Dict[str, Any],
    cmd_options: Optional[Dict[str, Dict[str, str]]] = None,
    extra: bool = False,
    tool: str = "robot",
) -> Optional[Dict[str, Dict[str, str]]]:
    usage_splitted = usage.splitlines()

    while not usage_splitted[0].startswith("======="):
        usage_splitted.pop(0)

    usage_splitted.pop(1)
    usage_splitted.pop(0)

    lines: List[str] = []
    current_line: Optional[str] = None
    in_examples = False

    for line in usage_splitted:
        if line.startswith((" -", "  -", "    --")):
            if current_line is not None:
                if in_examples:
                    in_examples = False
                    current_line += "\n```"
                lines.append(current_line.strip())

            current_line = line.strip()
        else:
            if current_line:
                if in_examples:
                    if not line.strip().startswith("-"):
                        in_examples = False
                        current_line += "\n```\n\n"
                else:
                    ex = EXAMPLES_RE.match(line)
                    if "Examples:" in line.strip():
                        current_line += (
                            f"\n\nExamples:\n\n```{LF if ex and ex.group('rest') else ''}"
                            f"{ex.group('rest') if ex else ''}"
                        )
                        in_examples = True
                        continue
            if current_line is None:
                current_line = ""
            current_line += "\n" + line.strip()

    if cmd_options is None:
        cmd_options = {}
        for line in lines:
            match = OPTIONS_RE.match(line)
            if match is None:
                print("No match", line)
            else:
                cmd_options[match.group("long")] = dict(**match.groupdict())

    internal_options = {}
    for k, v in options.items():
        internal_options[v[0]] = {"option": k, "long": v[0], "default": v[1]}

    def create_desc(v: Dict[str, str], extra: bool = False) -> str:
        if extra:
            result = f"            Appends entries to the {v['long']} option.\n\n"
        else:
            result = ""
        result += (
            "\n".join(f"            {v}".rstrip() for v in v["desc"].splitlines()) + "\n\n"
            "            corresponds to the "
            f"`{v['short'] or ''}"
            f"{' ' if v['short'] else ''}"
            f"{v['long']}"
            f"{' ' if v['param'] else ''}"
            f"{v['param'] or ''}"
            f"{' ' if v['star'] else ''}"
            f"{v['star'] or ''}`"
            f" option of _{tool}_"
        )

        return result

    def get_type(name: str, value: Any, option: Dict[str, str], is_flag: bool = False, extra: bool = False) -> str:
        if not option.get("param", None):
            if is_flag:
                return "Union[bool, Flag, None]"

            return "Optional[bool]"

        template_name = name
        if extra:
            template_name = name.replace("extra_", "")

        if template_name in type_templates:
            return f"Optional[{type_templates[template_name]}]"

        base_type = "str" if value is None or isinstance(value, (tuple, list)) else type(value).__name__

        if base_type == "str":
            base_type = "Union[str, StringExpression]"

        if param := option.get("param", None):
            if len((param_splitted := param.split("|"))) > 1:
                has_literal = [x for x in param_splitted if ":" not in x]
                has_pattern = [x for x in param_splitted if ":" in x]
                base_type = (
                    ("Union[str, " if has_literal and has_pattern or len(has_pattern) > 1 else "")
                    + (("Literal[" + ", ".join([f'"{x}"' for x in has_literal]) + "]") if has_literal else "")
                    + (
                        (
                            (", " if has_literal else "")
                            + ", ".join(
                                (x.split(":")[0].capitalize() + x.split(":")[1][1:-1].capitalize()) for x in has_pattern
                            )
                        )
                        if has_pattern
                        else ""
                    )
                    + ("]" if has_literal and has_pattern or len(has_pattern) > 1 else "")
                )

            elif len((param_splitted := param.split(":"))) > 1:
                return f"Optional[Dict[str, {base_type}]]"

        if option.get("star", None):
            return f"Optional[List[{base_type}]]"

        return f"Optional[{base_type}]"

    def build_class_fields(output: List[str], opts: Dict[str, Any], extra: bool = False) -> Dict[str, Any]:
        result = {}

        for k, v in sorted(opts.items(), key=lambda x: x[0]):
            is_flag = v.get("param", None) is None
            flag_default = True
            long_name = k[2:]
            if is_flag and long_name.startswith("no"):
                long_name = long_name[2:]
                flag_default = False

            if long_name in internal_options:
                if isinstance(internal_options[long_name]["default"], (list, dict)):
                    result.update({k: v})

                name = ("extra_" if extra else "") + to_snake_case(
                    name_corrections.get(long_name, None) or internal_options[long_name]["option"]
                )
                output.append(
                    f"    {name}"
                    f': {get_type(name, internal_options[long_name]["default"], v, is_flag, extra)} = field(\n'
                    f'        description="""\\\n{create_desc(v, extra)}\n            """,'
                )
                if not extra:
                    output.append(f'        robot_name="{long_name}",')
                    output.append("        robot_priority=500,")
                    if v["short"] is not None:
                        output.append(f'        robot_short_name="{v["short"][1:]}",')
                    if is_flag:
                        output.append("        robot_is_flag=True,")
                        if not flag_default:
                            output.append(f"        robot_flag_default={flag_default},")
                output.append("    )")

        return result

    return build_class_fields(output, cmd_options, extra=extra)


output = []


output.append("")
output.append("")
output.append("@dataclass")
output.append("class CommonOptions(BaseOptions):")
output.append('    """Common options for all _robot_ commands."""')
output.append("")
extra_cmd_options = generate(output, ROBOT_USAGE, RobotSettings._cli_opts, None, extra=False)

output.append("")
output.append("")
output.append("@dataclass")
output.append("class CommonExtraOptions(BaseOptions):")
output.append('    """Extra common options for all _robot_ commands."""')
output.append("")
generate(output, ROBOT_USAGE, RobotSettings._cli_opts, extra_cmd_options, extra=True)

output.append("")
output.append("")
output.append("@dataclass")
output.append("class RobotOptions(BaseOptions):")
output.append('    """Options for _robot_ command."""')
output.append("")
extra_cmd_options = generate(output, ROBOT_USAGE, RobotSettings._extra_cli_opts, None, extra=False)

output.append("")
output.append("")
output.append("@dataclass")
output.append("class RobotExtraOptions(BaseOptions):")
output.append('    """Extra options for _robot_ command."""')
output.append("")
generate(output, ROBOT_USAGE, RobotSettings._extra_cli_opts, extra_cmd_options, extra=True, tool="rebot")

output.append("")
output.append("")
output.append("@dataclass")
output.append("class RebotOptions(BaseOptions):")
output.append('    """Options for _rebot_ command."""')
output.append("")
extra_cmd_options = generate(output, REBOT_USAGE, RebotSettings._extra_cli_opts, None, extra=False, tool="rebot")


libdoc_options: Dict[str, Tuple[str, Any]] = {
    "Name": ("name", None),
    "Format": ("format", None),
    "DocFormat": ("docformat", None),
    "SpecDocFormat": ("specdocformat", None),
    "Theme": ("theme", None),
    "PythonPath": ("pythonpath", []),
    "Quiet": ("quiet", False),
}

output.append("")
output.append("")
output.append("@dataclass")
output.append("class LibDocOptions(BaseOptions):")
output.append('    """Options for _libdoc_ command."""')
output.append("")
extra_cmd_options = generate(output, LIBDOC_USAGE, libdoc_options, None, extra=False, tool="libdoc")

output.append("")
output.append("")
output.append("@dataclass")
output.append("class LibDocExtraOptions(BaseOptions):")
output.append('    """Extra options for _libdoc_ command."""')
output.append("")
generate(output, LIBDOC_USAGE, libdoc_options, extra_cmd_options, extra=True, tool="libdoc")


testdoc_options: Dict[str, Tuple[str, Any]] = {
    "Title": ("title", None),
    "Name": ("name", None),
    "Format": ("format", None),
    **RobotSettings._cli_opts,
}
output.append("")
output.append("")
output.append("@dataclass")
output.append("class TestDocOptions(BaseOptions):")
output.append('    """Options for _testdoc_ command."""')
output.append("")
extra_cmd_options = generate(output, TESTDOC_USAGE, testdoc_options, None, extra=False, tool="testdoc")

output.append("")
output.append("")
output.append("@dataclass")
output.append("class TestDocExtraOptions(BaseOptions):")
output.append('    """Extra options for _testdoc_ command."""')
output.append("")
generate(output, TESTDOC_USAGE, testdoc_options, extra_cmd_options, extra=True, tool="testdoc")

model_file = Path("packages/robot/src/robotcode/robot/config/model.py")
original_lines = model_file.read_text().splitlines()

start_line = original_lines.index("# start generated code")
end_line = original_lines.index("# end generated code")

original_lines[start_line + 1 : end_line] = output
original_lines.append("")
model_file.write_text("\n".join(original_lines))
