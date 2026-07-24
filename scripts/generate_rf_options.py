import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from robot.conf import RebotSettings, RobotSettings
from robot.libdoc import USAGE as LIBDOC_USAGE
from robot.rebot import USAGE as REBOT_USAGE
from robot.run import USAGE as ROBOT_USAGE
from robot.testdoc import USAGE as TESTDOC_USAGE

from robotcode.core.utils.dataclasses import to_snake_case

EXAMPLES_RE = re.compile(r"(?P<spaces>^\s*)Examples:\s*(?P<rest>.*)", re.MULTILINE)
OPTIONS_RE = re.compile(
    r"^(\s*(?P<short>-\S+))?(\s*(?P<short1>-\S+))?(\s*(?P<long>--\w+))(\s+(?P<param>\S+))?(\s+(?P<star>\*))?((\s\s)|\n)+\s*(?P<desc>.+)",
    re.DOTALL | re.MULTILINE,
)

# Robot Framework's CLI help embeds example blocks of the form
#   Examples:
#   ```
#   --foo bar
#   ```
# When these descriptions are surfaced in `robot.toml` documentation we want
# the examples to use TOML syntax instead of CLI flags. The mapping below holds
# one or more curated TOML snippets per long option; the generator drops the
# original CLI examples and emits these snippets as ```toml fenced blocks.
TOML_EXAMPLES: Dict[str, List[str]] = {
    # --- options that already had CLI examples in Robot Framework's help ---
    "--doc": [
        'doc = "Very *good* example"',
        '# read documentation from a file\ndoc = "doc_from_file.txt"',
    ],
    "--expandkeywords": [
        'expand-keywords = ["name:BuiltIn.Log", "tag:expand"]',
    ],
    "--include": [
        '# match tests tagged "foo" or "bar*"\nincludes = ["foo", "bar*"]',
        '# tests with both "foo" and "bar*" tags\nincludes = ["fooANDbar*"]',
    ],
    "--listener": [
        '[listeners]\nMyListener = []\n"path/to/Listener.py" = ["arg1", "arg2"]',
    ],
    "--loglevel": [
        'log-level = "DEBUG"',
        '# explicit visible level (default: INFO)\nlog-level = "DEBUG:INFO"',
    ],
    "--pythonpath": [
        'python-path = ["libs/", "/opt/libs", "libraries.zip"]',
    ],
    "--randomize": [
        'randomize = "all"',
        '# randomize tests with a fixed seed\nrandomize = "tests:1234"',
    ],
    "--removekeywords": [
        '# match by keyword name\nremove-keywords = ["name:Lib.HugeKw", "name:myresource.*"]',
        '# match by tag pattern (same rules as --include)\nremove-keywords = ["foo", "fooANDbar*"]',
    ],
    "--reportbackground": [
        '# pass:fail:skip colours\nreport-background = "green:red:yellow"',
        '# pass:fail (skip uses the fail colour)\nreport-background = "#00E:#E00"',
    ],
    "--tagdoc": [
        '[tag-doc]\nmytag = "Example"\n"owner-*" = "Original author"',
    ],
    "--tagstatcombine": [
        'tag-stat-combine = ["requirement-*", { "tag1ANDtag2" = "My_name" }]',
    ],
    "--tagstatlink": [
        '[tag-stat-link]\nmytag = "http://my.domain:Title"\n"bug-*" = "http://url/id=%1:Issue Tracker"',
    ],
    "--variable": [
        '# sets ${name} to "Robot"\n[variables]\nname = "Robot"',
    ],
    "--variablefile": [
        'variable-files = ["path/vars.yaml", "environment.py:testing"]',
    ],
    # --- literal/enum options (one-of values) ---
    "--console": ['console = "dotted"'],
    "--consolecolors": ['console-colors = "on"'],
    "--consolelinks": ['console-links = "off"'],
    "--consolemarkers": ['console-markers = "off"'],
    "--docformat": ['doc-format = "REST"'],
    "--format": ['format = "HTML"'],
    "--specdocformat": ['spec-doc-format = "HTML"'],
    "--theme": ['theme = "DARK"'],
    # --- numeric options ---
    "--consolewidth": ["console-width = 100"],
    "--maxassignlength": ["max-assign-length = 200"],
    "--maxerrorlines": ["max-error-lines = 40", 'max-error-lines = "NONE"'],
    "--suitestatlevel": ["suite-stat-level = 2"],
    # --- single-string options (paths, names, titles, timestamps) ---
    "--debugfile": ['debug-file = "debug.log"'],
    "--extension": [
        'extensions = "txt"',
        '# parse multiple extensions (separator: colon)\nextensions = "robot:txt"',
    ],
    "--log": [
        'log = "mylog.html"',
        '# disable log file generation\nlog = "NONE"',
    ],
    "--logtitle": ['log-title = "My Project Log"'],
    "--name": ['name = "My Project"'],
    "--output": ['output = "output.xml"'],
    "--outputdir": ['output-dir = "results"'],
    "--report": ['report = "report.html"'],
    "--reporttitle": ['report-title = "My Project Report"'],
    "--rerunfailed": ['re-run-failed = "output.xml"'],
    "--rerunfailedsuites": ['re-run-failed-suites = "output.xml"'],
    "--starttime": ['start-time = "2024-12-15 14:30:00.000"'],
    "--endtime": ['end-time = "2024-12-15 14:35:42.123"'],
    "--title": ['title = "My Library"'],
    "--xunit": ['xunit = "xunit.xml"'],
    # --- list-of-strings options ---
    "--exclude": ['excludes = ["smoke", "wip*"]'],
    "--language": ['languages = ["German", "Finnish"]'],
    "--parseinclude": ['parse-include = ["*.robot", "tests/**/*.robot"]'],
    "--settag": ['set-tag = ["my-suite-tag", "ci"]'],
    "--skip": ['skip = ["bug-*", "wip"]'],
    "--skiponfailure": ['skip-on-failure = ["unstable"]'],
    "--suite": [
        '# match a suite by name or by parent.child path\nsuites = ["MySuite", "Tests.SubSuite"]',
    ],
    "--task": ['tasks = ["My Task", "Smoke*"]'],
    "--test": ['tests = ["My Test", "Smoke*"]'],
    "--tagstatexclude": ['tag-stat-exclude = ["bug-*"]'],
    "--tagstatinclude": ['tag-stat-include = ["owner-*", "feature-*"]'],
    "--flattenkeywords": [
        'flatten-keywords = ["for", "name:Lib.HugeKw", "tag:flatten"]',
    ],
    # --- dict options (metadata, parsers, modifiers) ---
    "--metadata": [
        (
            "[metadata]\n"
            'Version = "1.2"\n'
            "# value can be read from a file (same rules as --doc)\n"
            'ReleaseNotes = "release_notes.txt"'
        ),
    ],
    "--parser": [
        '[parsers]\nMyParser = []\n"path/to/MyParser.py" = ["arg1", "arg2"]',
    ],
    "--prerebotmodifier": [
        '[pre-rebot-modifiers]\n"path/to/Modifier.py" = ["arg1"]',
    ],
    "--prerunmodifier": [
        '[pre-run-modifiers]\nMyModifier = []\n"path/to/Modifier.py" = ["arg1"]',
    ],
    # --- boolean flag options ---
    "--dotted": ["dotted = true"],
    "--dryrun": ["dry-run = true"],
    "--exitonerror": ["exit-on-error = true"],
    "--exitonfailure": ["exit-on-failure = true"],
    "--legacyoutput": ["legacy-output = true"],
    "--merge": ["merge = true"],
    "--processemptysuite": ["process-empty-suite = true"],
    "--quiet": ["quiet = true"],
    "--rpa": ["rpa = true"],
    "--runemptysuite": ["run-empty-suite = true"],
    "--skipteardownonexit": ["skip-teardown-on-exit = true"],
    "--splitlog": ["split-log = true"],
    "--nostatusrc": [
        "# always exit 0 regardless of failed tests\nno-status-rc = true",
        "# decide from the current branch\nno-status-rc = { if = \"environ.get('CI_COMMIT_REF_NAME') == 'main'\" }",
    ],
    "--timestampoutputs": ["timestamp-outputs = true"],
}

# Matches an "Examples:" block parsed from the RF help text — see how the
# generator builds these in the loop below.
EXAMPLES_BLOCK_RE = re.compile(
    r"\n*Examples:\s*\n+```[a-zA-Z]*\n.*?\n```",
    re.DOTALL,
)


def rewrite_for_extend(snippet: str, base_kebab: str) -> str:
    """Rewrite a TOML example snippet so its top-level key/table uses the
    `extend-` prefix. Only the canonical field name is rewritten — nested
    keys inside a table (like inner listener/variable names) are left alone.
    """
    escaped = re.escape(base_kebab)
    # `key = ...` at the start of a line
    after_assign = re.sub(rf"^{escaped}(\s*=)", rf"extend-{base_kebab}\1", snippet, flags=re.MULTILINE)
    # `[key]` table header at the start of a line
    return re.sub(rf"^\[{escaped}\]", f"[extend-{base_kebab}]", after_assign, flags=re.MULTILINE)


MAX_LINE_LENGTH = 120


def format_field_decl(name: str, type_str: str) -> str:
    """Render a `<name>: <type_str> = field(` line, breaking the type
    annotation across lines when the single-line form would exceed
    MAX_LINE_LENGTH. Wrapping happens inside the outermost `Optional[...]`
    bracket — the same form the existing model.py used by hand.
    """
    one_line = f"    {name}: {type_str} = field("
    if len(one_line) <= MAX_LINE_LENGTH:
        return one_line
    if type_str.startswith("Optional[") and type_str.endswith("]"):
        inner = type_str[len("Optional[") : -1]
        return f"    {name}: Optional[\n        {inner}\n    ] = field("
    # No structural break point we know how to handle — leave it long and
    # let ruff format decide.
    return one_line


def apply_toml_examples(desc: str, long: str, base_kebab: str, extend: bool) -> str:
    if long not in TOML_EXAMPLES:
        return desc
    cleaned = EXAMPLES_BLOCK_RE.sub("", desc).rstrip()
    snippets = TOML_EXAMPLES[long]
    if extend and base_kebab:
        snippets = [rewrite_for_extend(s, base_kebab) for s in snippets]
    blocks = "\n\n".join(f"```toml\n{snippet}\n```" for snippet in snippets)
    return f"{cleaned}\n\nExamples:\n\n{blocks}\n"


type_templates = {
    "console": 'Literal["verbose", "dotted", "skipped", "quiet", "none"]',
    "listeners": "Dict[str, List[Union[str, StringExpression]]]",
    "max_error_lines": 'Union[int, Literal["NONE"]]',
    "parsers": "Dict[str, List[Union[str, StringExpression]]]",
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

RE_LIST_MATCHER = re.compile(r"^\s*([a-zA-Z0-9_]+)((:)(<[a-zA-Z0-9_]+>))?:\s+(.*$)")


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
            m = RE_LIST_MATCHER.match(line)
            if not in_examples and m:
                p = ":\\\\"
                line = f"**{m.group(1)}{p + m.group(4) if m.group(4) else ''}:** {m.group(5)}"
                current_line += "\n\n" + line.strip()
            else:
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

    def create_desc(v: Dict[str, str], extra: bool = False, base_kebab: str = "") -> str:
        if extra:
            result = f"            Appends entries to the {v['long']} option.\n\n"
        else:
            result = ""
        desc = apply_toml_examples(v["desc"], v["long"], base_kebab, extra)
        result += (
            "\n".join(f"            {line}".rstrip() for line in desc.splitlines()) + "\n\n"
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

    def get_type(
        name: str,
        value: Any,
        option: Dict[str, str],
        is_flag: bool = False,
        extra: bool = False,
    ) -> str:
        if not option.get("param"):
            if is_flag:
                if name == "no_status_rc":
                    return "Union[bool, Flag, Condition, None]"
                return "Union[bool, Flag, None]"

            return "Optional[bool]"

        template_name = name
        if extra:
            template_name = name.replace("extend_", "")

        if template_name in type_templates:
            return f"Optional[{type_templates[template_name]}]"

        base_type = "str" if value is None or isinstance(value, (tuple, list)) else type(value).__name__

        if base_type == "str":
            base_type = "Union[str, StringExpression]"

        if param := option.get("param"):
            if len(param_splitted := param.split("|")) > 1:
                has_literal = [x for x in param_splitted if ":" not in x]
                has_pattern = [x for x in param_splitted if ":" in x]
                base_type = (
                    ("Union[str, " if (has_literal and has_pattern) or len(has_pattern) > 1 else "")
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
                    + ("]" if (has_literal and has_pattern) or len(has_pattern) > 1 else "")
                )

            elif len(param_splitted := param.split(":")) > 1:
                return f"Optional[Dict[str, {base_type}]]"

        if option.get("star"):
            return f"Optional[List[{base_type}]]"

        return f"Optional[{base_type}]"

    def build_class_fields(output: List[str], opts: Dict[str, Any], extend: bool = False) -> Dict[str, Any]:
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

                base_name = to_snake_case(name_corrections.get(long_name) or internal_options[long_name]["option"])
                name = ("extend_" if extend else "") + base_name
                base_kebab = base_name.replace("_", "-")
                type_str = get_type(name, internal_options[long_name]["default"], v, is_flag, extend)
                field_decl = format_field_decl(name, type_str)
                output.append(
                    f'{field_decl}\n        description="""\\\n{create_desc(v, extend, base_kebab)}\n            """,'
                )
                if not extend:
                    output.append(f'        robot_name="{long_name}",')
                    output.append("        robot_priority=500,")
                    if v["short"] is not None:
                        output.append(f'        robot_short_name="{v["short"][1:]}",')
                    if is_flag:
                        output.append("        robot_is_flag=True,")
                        if not flag_default:
                            output.append(f"        robot_flag_default={flag_default},")
                alias = name.replace("_", "-")
                if alias != name:
                    output.append(f'        alias="{alias}",')
                output.append("    )")

        return result

    return build_class_fields(output, cmd_options, extend=extra)


output = []


output.append("")
output.append("")
output.append("@dataclass")
output.append("class CommonOptions(RobotBaseOptions):")
output.append('    """Common options for all _robot_ commands."""')
output.append("")
extra_cmd_options = generate(output, ROBOT_USAGE, RobotSettings._cli_opts, None, extra=False)

output.append("")
output.append("")
output.append("@dataclass")
output.append("class CommonExtendOptions(RobotBaseOptions):")
output.append('    """Extra common options for all _robot_ commands."""')
output.append("")
generate(output, ROBOT_USAGE, RobotSettings._cli_opts, extra_cmd_options, extra=True)

output.append("")
output.append("")
output.append("@dataclass")
output.append("class RobotOptions(RobotBaseOptions):")
output.append('    """Options for _robot_ command."""')
output.append("")
extra_cmd_options = generate(output, ROBOT_USAGE, RobotSettings._extra_cli_opts, None, extra=False)

output.append("")
output.append("")
output.append("@dataclass")
output.append("class RobotExtendOptions(RobotBaseOptions):")
output.append('    """Extra options for _robot_ command."""')
output.append("")
generate(
    output,
    ROBOT_USAGE,
    RobotSettings._extra_cli_opts,
    extra_cmd_options,
    extra=True,
    tool="rebot",
)

output.append("")
output.append("")
output.append("@dataclass")
output.append("class RebotOptions(RobotBaseOptions):")
output.append('    """Options for _rebot_ command."""')
output.append("")
extra_cmd_options = generate(
    output,
    REBOT_USAGE,
    RebotSettings._extra_cli_opts,
    None,
    extra=False,
    tool="rebot",
)


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
output.append("class LibDocOptions(RobotBaseOptions):")
output.append('    """Options for _libdoc_ command."""')
output.append("")
extra_cmd_options = generate(output, LIBDOC_USAGE, libdoc_options, None, extra=False, tool="libdoc")

output.append("")
output.append("")
output.append("@dataclass")
output.append("class LibDocExtendOptions(RobotBaseOptions):")
output.append('    """Extra options for _libdoc_ command."""')
output.append("")
generate(
    output,
    LIBDOC_USAGE,
    libdoc_options,
    extra_cmd_options,
    extra=True,
    tool="libdoc",
)


testdoc_options: Dict[str, Tuple[str, Any]] = {
    "Title": ("title", None),
    "Name": ("name", None),
    "Format": ("format", None),
    **RobotSettings._cli_opts,
}
output.append("")
output.append("")
output.append("@dataclass")
output.append("class TestDocOptions(RobotBaseOptions):")
output.append('    """Options for _testdoc_ command."""')
output.append("")
extra_cmd_options = generate(output, TESTDOC_USAGE, testdoc_options, None, extra=False, tool="testdoc")

output.append("")
output.append("")
output.append("@dataclass")
output.append("class TestDocExtendOptions(RobotBaseOptions):")
output.append('    """Extra options for _testdoc_ command."""')
output.append("")
generate(
    output,
    TESTDOC_USAGE,
    testdoc_options,
    extra_cmd_options,
    extra=True,
    tool="testdoc",
)

output.extend(["", ""])

model_file = Path("packages/robot/src/robotcode/robot/config/model.py")
original_lines = model_file.read_text().splitlines()

start_line = original_lines.index("# start generated code")
end_line = original_lines.index("# end generated code")

original_lines[start_line + 1 : end_line] = output
original_lines.append("")
model_file.write_text("\n".join(original_lines))
