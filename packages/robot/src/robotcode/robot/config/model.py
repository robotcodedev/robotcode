# ruff: noqa: RUF009
import dataclasses
import datetime
import fnmatch
import os
import pathlib
import platform
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    get_type_hints,
)

import tomli_w
from robotcode.core.dataclasses import TypeValidationError, ValidateMixin, as_dict, validate_types
from robotcode.core.utils.safe_eval import safe_eval
from typing_extensions import Self

EXTEND_PREFIX_LEN = len("extend_")


class Flag(str, Enum):
    ON = "on"
    OFF = "off"
    DEFAULT = "default"

    def __str__(self) -> str:
        return self.value

    def __bool__(self) -> bool:
        if self == Flag.ON:
            return True

        return False


def field(
    *args: Any,
    description: Optional[str] = None,
    robot_name: Optional[str] = None,
    robot_short_name: Optional[str] = None,
    robot_is_flag: Optional[bool] = None,
    robot_flag_default: Optional[bool] = None,
    robot_priority: Optional[int] = None,
    alias: Optional[str] = None,
    convert: Optional[Callable[[Any, Any], Any]] = None,
    no_default: bool = False,
    **kwargs: Any,
) -> Any:
    metadata = kwargs.get("metadata", {})
    if description:
        metadata["description"] = "\n".join(line.strip() for line in description.splitlines())

    if convert is not None:
        metadata["convert"] = convert

    if robot_name is not None:
        metadata["robot_name"] = robot_name

    if robot_short_name is not None:
        metadata["robot_short_name"] = robot_short_name

    if robot_is_flag is not None:
        metadata["robot_is_flag"] = robot_is_flag

    if robot_flag_default is not None:
        metadata["robot_flag_default"] = robot_flag_default

    if robot_priority is not None:
        metadata["robot_priority"] = robot_priority

    if alias is not None:
        metadata["alias"] = alias
        metadata["_apischema_alias"] = alias

    if metadata:
        kwargs["metadata"] = metadata

    if "default_factory" not in kwargs and not no_default:
        kwargs["default"] = None

    return dataclasses.field(*args, **kwargs)


class EvaluationError(Exception):
    """Evaluation error."""

    def __init__(self, expression: str, message: str):
        super().__init__(f"Evaluation of {expression!r} failed: {message}")
        self.expr = expression


SAFE_GLOBALS = {
    "environ": os.environ,
    "re": re,
    "platform": platform,
    "datetime": datetime.datetime,
    "date": datetime.date,
    "time": datetime.time,
    "timedelta": datetime.timedelta,
    "timezone": datetime.timezone,
    "Path": pathlib.Path,
}


@dataclass
class Expression:
    """Expression to evaluate."""

    expr: str = field(
        description="""\
            Expression to evaluate. This must be a Python "eval" expression.
            For security reasons, only certain expressions and functions are allowed.

            Examples:
            ```toml
            expr = "re.match(r'^\\d+$', environ.get('TEST_VAR', ''))"
            expr = "platform.system() == 'Linux'"
            expr = "Path.cwd() / 'app'"
            ```

            Allowed global names (the name and the corresponding python module/name):

            - `environ` -> os.environ
            - `re` -> re
            - `platform` -> platform
            - `datetime` -> datetime.datetime
            - `date` -> datetime.date
            - `time` -> datetime.time
            - `timedelta` -> datetime.timedelta
            - `timezone` -> datetime.timezone
            - `Path` -> pathlib.Path
            """,
        no_default=True,
    )

    def evaluate(self) -> Any:
        try:
            return safe_eval(self.expr, SAFE_GLOBALS)
        except Exception as e:
            raise EvaluationError(self.expr, str(e)) from e


@dataclass
class StringExpression(Expression):
    """Expression to evaluate to a string."""

    def evaluate(self) -> str:
        return str(super().evaluate())

    def __str__(self) -> str:
        return self.evaluate()


@dataclass
class Condition:
    """Condition to evaluate."""

    if_: str = field(
        description="""\
            Condition to evaluate. This must be a Python "eval" expression.
            For security reasons, only certain expressions and functions are allowed.

            Examples:
            ```toml
            if = "re.match(r'^\\d+$', environ.get('TEST_VAR', ''))"
            if = "platform.system() == 'Linux'"
            ```

            see also `expr` for allowed global names.
            """,
        alias="if",
        no_default=True,
    )

    def evaluate(self) -> bool:
        try:
            return bool(safe_eval(self.if_, SAFE_GLOBALS))
        except Exception as e:
            raise EvaluationError(self.if_, str(e)) from e

    def __bool__(self) -> bool:
        return self.evaluate()


@dataclass()
class NamePattern(ValidateMixin):
    """Name pattern to match."""

    name: str = field(
        description="""\
            Name pattern to match. This is a glob pattern, where ``*`` matches any number of characters
            """,
        no_default=True,
    )

    def __str__(self) -> str:
        return f"name:{self.name}"


@dataclass()
class TagPattern(ValidateMixin):
    """Tag pattern to match."""

    tag: str = field(
        description="""\
            Tag pattern to match. This is a glob pattern, where ``*`` matches any number of characters
            """,
        no_default=True,
    )

    def __str__(self) -> str:
        return f"tag:{self.tag}"


@dataclass
class BaseOptions(ValidateMixin):
    @classmethod
    def _encode_case(cls, s: str) -> str:
        return s.replace("_", "-")

    @classmethod
    def _decode_case(cls, s: str) -> str:
        return s.replace("-", "_")

    """Base class for all options."""

    def build_command_line(self) -> List[str]:
        """Build the arguments to pass to Robot Framework."""
        result = []

        sorted_fields = sorted(
            (f for f in dataclasses.fields(self) if f.metadata.get("robot_priority", -1) > -1),
            key=lambda f: f.metadata.get("robot_priority", 0),
        )

        def append_name(field: "dataclasses.Field[Any]", add_flag: Optional[str] = None) -> None:
            if "robot_short_name" in field.metadata:
                result.append(f"-{field.metadata['robot_short_name']}")
            elif "robot_name" in field.metadata:
                result.append(f"--{'no' if add_flag else ''}{field.metadata['robot_name']}")

        for field in sorted_fields:
            try:
                value = getattr(self, field.name)
                if value is None:
                    continue

                if field.metadata.get("robot_is_flag", False):
                    if value is None or value == Flag.DEFAULT:
                        continue

                    append_name(field, bool(value) != field.metadata.get("robot_flag_default", True))

                    continue

                if isinstance(value, list):
                    for item in value:
                        append_name(field)
                        if isinstance(item, dict):
                            for k, v in item.items():
                                result.append(f"{k}:{v}")
                        else:
                            result.append(str(item))
                elif isinstance(value, dict):
                    for key, item in value.items():
                        append_name(field)
                        if isinstance(item, list):
                            separator = ";" if any(True for s in item if ":" in s) else ":"
                            result.append(f"{key}{separator if item else ''}{separator.join(item)}")
                        else:
                            result.append(f"{key}:{item}")
                else:
                    append_name(field)
                    result.append(str(value))
            except EvaluationError as e:
                raise ValueError(f"Evaluation of '{field.name}' failed: {e!s}") from e

        return result

    @staticmethod
    def _verified_value(name: str, value: Any, types: Union[type, Tuple[type, ...]], target: Any) -> Any:
        errors = validate_types(types, value)
        if errors:
            raise TypeValidationError("Dataclass Type Validation Error", target=target, errors={name: errors})
        return value

    def add_options(self, config: "BaseOptions", combine_extras: bool = False) -> None:
        type_hints = get_type_hints(type(self))
        base_field_names = [f.name for f in dataclasses.fields(self)]

        for f in dataclasses.fields(config):
            if f.name.startswith("extend_"):
                if f.name not in base_field_names:
                    continue

                new = self._verified_value(
                    f.name, getattr(config, f.name), type_hints[f.name[EXTEND_PREFIX_LEN:]], config
                )
                if new is None:
                    continue

                old_field_name = f.name if combine_extras else f.name[EXTEND_PREFIX_LEN:]

                old = getattr(self, old_field_name)
                if old is None:
                    setattr(self, old_field_name, new)
                else:
                    if isinstance(old, dict):
                        if any(True for e in new.values() if isinstance(e, BaseOptions)):
                            for key, value in new.items():
                                if isinstance(value, BaseOptions) and key in old:
                                    old[key].add_options(value, True)
                                else:
                                    old[key] = value
                        else:
                            setattr(self, old_field_name, {**old, **new})
                    elif isinstance(old, list):
                        setattr(self, old_field_name, [*old, *new])
                    elif isinstance(old, tuple):
                        setattr(self, old_field_name, (*old, *new))
                    else:
                        setattr(self, old_field_name, new)
                continue

            if f.name not in base_field_names:
                continue

            if combine_extras:
                if "extend_" + f.name in base_field_names and getattr(config, f.name, None) is not None:
                    setattr(self, "extend_" + f.name, None)

            if getattr(config, f"extend_{f.name}", None) is not None and not combine_extras:
                continue

            new = self._verified_value(f.name, getattr(config, f.name), type_hints[f.name], config)
            if new is not None:
                setattr(self, f.name, new)

    def evaluated(self) -> Self:
        result = dataclasses.replace(self)
        for f in dataclasses.fields(result):
            try:
                if isinstance(getattr(result, f.name), Condition):
                    setattr(result, f.name, getattr(result, f.name).evaluate())
                elif isinstance(getattr(result, f.name), Expression):
                    setattr(result, f.name, getattr(result, f.name).evaluate())
                elif isinstance(getattr(result, f.name), list):
                    setattr(
                        result,
                        f.name,
                        [e.evaluate() if isinstance(e, Expression) else e for e in getattr(result, f.name)],
                    )
                elif isinstance(getattr(result, f.name), dict):
                    setattr(
                        result,
                        f.name,
                        {
                            k: e.evaluate() if isinstance(e, Expression) else e
                            for k, e in getattr(result, f.name).items()
                        },
                    )
            except EvaluationError as e:
                raise ValueError(f"Evaluation of '{f.name}' failed: {e!s}") from e
        return result


# start generated code


@dataclass
class CommonOptions(BaseOptions):
    """Common options for all _robot_ commands."""

    console_colors: Optional[Literal["auto", "on", "ansi", "off"]] = field(
        description="""\
            Use colors on console output or not.
            auto: use colors when output not redirected (default)
            on:   always use colors
            ansi: like `on` but use ANSI colors also on Windows
            off:  disable colors altogether

            corresponds to the `-C --consolecolors auto|on|ansi|off` option of _robot_
            """,
        robot_name="consolecolors",
        robot_priority=500,
        robot_short_name="C",
    )
    doc: Optional[Union[str, StringExpression]] = field(
        description="""\
            Set the documentation of the top level suite.
            Simple formatting is supported (e.g. *bold*). If the
            documentation contains spaces, it must be quoted.
            If the value is path to an existing file, actual
            documentation is read from that file.

            Examples:

            ```
            --doc "Very *good* example"
            --doc doc_from_file.txt
            ```

            corresponds to the `-D --doc documentation` option of _robot_
            """,
        robot_name="doc",
        robot_priority=500,
        robot_short_name="D",
    )
    excludes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Select test cases not to run by tag. These tests are
            not run even if included with --include. Tags are
            matched using same rules as with --include.

            corresponds to the `-e --exclude tag *` option of _robot_
            """,
        robot_name="exclude",
        robot_priority=500,
        robot_short_name="e",
    )
    expand_keywords: Optional[List[Union[str, NamePattern, TagPattern]]] = field(
        description="""\
            Matching keywords will be automatically expanded in
            the log file. Matching against keyword name or tags
            work using same rules as with --removekeywords.

            Examples:

            ```
            --expandkeywords name:BuiltIn.Log
            --expandkeywords tag:expand
            ```

            corresponds to the `--expandkeywords name:<pattern>|tag:<pattern> *` option of _robot_
            """,
        robot_name="expandkeywords",
        robot_priority=500,
    )
    flatten_keywords: Optional[List[Union[str, Literal["for", "while", "iteration"], NamePattern, TagPattern]]] = field(
        description="""\
            Flattens matching keywords in the generated log file.
            Matching keywords get all log messages from their
            child keywords and children are discarded otherwise.
            for:     flatten FOR loops fully
            while:   flatten WHILE loops fully
            iteration: flatten FOR/WHILE loop iterations
            foritem: deprecated alias for `iteration`
            name:<pattern>:  flatten matched keywords using same
            matching rules as with
            `--removekeywords name:<pattern>`
            tag:<pattern>:  flatten matched keywords using same
            matching rules as with
            `--removekeywords tag:<pattern>`

            corresponds to the `--flattenkeywords for|while|iteration|name:<pattern>|tag:<pattern> *` option of _robot_
            """,
        robot_name="flattenkeywords",
        robot_priority=500,
    )
    includes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Select tests by tag. Similarly as name with --test,
            tag is case and space insensitive and it is possible
            to use patterns with `*`, `?` and `[]` as wildcards.
            Tags and patterns can also be combined together with
            `AND`, `OR`, and `NOT` operators.

            Examples:

            ```
            --include foo --include bar*
            --include fooANDbar*
            ```

            corresponds to the `-i --include tag *` option of _robot_
            """,
        robot_name="include",
        robot_priority=500,
        robot_short_name="i",
    )
    log: Optional[Union[str, StringExpression]] = field(
        description="""\
            HTML log file. Can be disabled by giving a special
            value `NONE`. Default: log.html

            Examples:

            ```
            `--log mylog.html`, `-l NONE`
            ```

            corresponds to the `-l --log file` option of _robot_
            """,
        robot_name="log",
        robot_priority=500,
        robot_short_name="l",
    )
    log_title: Optional[Union[str, StringExpression]] = field(
        description="""\
            Title for the generated log file. The default title
            is `<SuiteName> Log`.

            corresponds to the `--logtitle title` option of _robot_
            """,
        robot_name="logtitle",
        robot_priority=500,
    )
    metadata: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Set metadata of the top level suite. Value can
            contain formatting and be read from a file similarly
            as --doc. Example: --metadata Version:1.2

            corresponds to the `-M --metadata name:value *` option of _robot_
            """,
        robot_name="metadata",
        robot_priority=500,
        robot_short_name="M",
    )
    name: Optional[Union[str, StringExpression]] = field(
        description="""\
            Set the name of the top level suite. By default the
            name is created based on the executed file or
            directory.

            corresponds to the `-N --name name` option of _robot_
            """,
        robot_name="name",
        robot_priority=500,
        robot_short_name="N",
    )
    no_status_rc: Union[bool, Flag, None] = field(
        description="""\
            Sets the return code to zero regardless of failures
            in test cases. Error codes are returned normally.

            corresponds to the `--nostatusrc` option of _robot_
            """,
        robot_name="statusrc",
        robot_priority=500,
        robot_is_flag=True,
        robot_flag_default=False,
    )
    output_dir: Optional[Union[str, StringExpression]] = field(
        description="""\
            Where to create output files. The default is the
            directory where tests are run from and the given path
            is considered relative to that unless it is absolute.

            corresponds to the `-d --outputdir dir` option of _robot_
            """,
        robot_name="outputdir",
        robot_priority=500,
        robot_short_name="d",
    )
    parse_include: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Parse only files matching `pattern`. It can be:
            - a file name or pattern like `example.robot` or
            `*.robot` to parse all files matching that name,
            - a file path like `path/to/example.robot`, or
            - a directory path like `path/to/example` to parse
            all files in that directory, recursively.

            corresponds to the `-I --parseinclude pattern *` option of _robot_
            """,
        robot_name="parseinclude",
        robot_priority=500,
        robot_short_name="I",
    )
    pre_rebot_modifiers: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Class to programmatically modify the result
            model before creating reports and logs. Accepts
            arguments the same way as with --listener.

            corresponds to the `--prerebotmodifier modifier *` option of _robot_
            """,
        robot_name="prerebotmodifier",
        robot_priority=500,
    )
    python_path: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Additional locations (directories, ZIPs) where to
            search libraries and other extensions when they are
            imported. Multiple paths can be given by separating
            them with a colon (`:`) or by using this option
            several times. Given path can also be a glob pattern
            matching multiple paths.

            Examples:

            ```
            --pythonpath libs/
            --pythonpath /opt/libs:libraries.zip
            ```

            corresponds to the `-P --pythonpath path *` option of _robot_
            """,
        robot_name="pythonpath",
        robot_priority=500,
        robot_short_name="P",
    )
    remove_keywords: Optional[
        List[Union[str, Literal["all", "passed", "for", "wuks"], NamePattern, TagPattern]]
    ] = field(
        description="""\
            Remove keyword data from the generated log file.
            Keywords containing warnings are not removed except
            in the `all` mode.
            all:     remove data from all keywords
            passed:  remove data only from keywords in passed
            test cases and suites
            for:     remove passed iterations from for loops
            while:   remove passed iterations from while loops
            wuks:    remove all but the last failing keyword
            inside `BuiltIn.Wait Until Keyword Succeeds`
            name:<pattern>:  remove data from keywords that match
            the given pattern. The pattern is matched
            against the full name of the keyword (e.g.
            'MyLib.Keyword', 'resource.Second Keyword'),
            is case, space, and underscore insensitive,
            and may contain `*`, `?` and `[]` wildcards.

            Examples:

            ```
            --removekeywords name:Lib.HugeKw
            --removekeywords name:myresource.*
            ```


            tag:<pattern>:  remove data from keywords that match
            the given pattern. Tags are case and space
            insensitive and patterns can contain `*`,
            `?` and `[]` wildcards. Tags and patterns
            can also be combined together with `AND`,
            `OR`, and `NOT` operators.

            Examples:

            ```
            --removekeywords foo
            --removekeywords fooANDbar*
            ```

            corresponds to the `--removekeywords all|passed|for|wuks|name:<pattern>|tag:<pattern> *` option of _robot_
            """,
        robot_name="removekeywords",
        robot_priority=500,
    )
    report: Optional[Union[str, StringExpression]] = field(
        description="""\
            HTML report file. Can be disabled with `NONE`
            similarly as --log. Default: report.html

            corresponds to the `-r --report file` option of _robot_
            """,
        robot_name="report",
        robot_priority=500,
        robot_short_name="r",
    )
    report_background: Optional[Union[str, StringExpression]] = field(
        description="""\
            Background colors to use in the report file.
            Given in format `passed:failed:skipped` where the
            `:skipped` part can be omitted. Both color names and
            codes work.

            Examples:

            ```
            --reportbackground green:red:yellow
            --reportbackground #00E:#E00
            ```

            corresponds to the `--reportbackground colors` option of _robot_
            """,
        robot_name="reportbackground",
        robot_priority=500,
    )
    report_title: Optional[Union[str, StringExpression]] = field(
        description="""\
            Title for the generated report file. The default
            title is `<SuiteName> Report`.

            corresponds to the `--reporttitle title` option of _robot_
            """,
        robot_name="reporttitle",
        robot_priority=500,
    )
    rpa: Union[bool, Flag, None] = field(
        description="""\
            Turn on the generic automation mode. Mainly affects
            terminology so that "test" is replaced with "task"
            in logs and reports. By default the mode is got
            from test/task header in data files.

            corresponds to the `--rpa` option of _robot_
            """,
        robot_name="rpa",
        robot_priority=500,
        robot_is_flag=True,
    )
    set_tag: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Sets given tag(s) to all executed tests.

            corresponds to the `-G --settag tag *` option of _robot_
            """,
        robot_name="settag",
        robot_priority=500,
        robot_short_name="G",
    )
    split_log: Union[bool, Flag, None] = field(
        description="""\
            Split the log file into smaller pieces that open in
            browsers transparently.

            corresponds to the `--splitlog` option of _robot_
            """,
        robot_name="splitlog",
        robot_priority=500,
        robot_is_flag=True,
    )
    suites: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Select suites by name. When this option is used with
            --test, --include or --exclude, only tests in
            matching suites and also matching other filtering
            criteria are selected. Name can be a simple pattern
            similarly as with --test and it can contain parent
            name separated with a dot. For example, `-s X.Y`
            selects suite `Y` only if its parent is `X`.

            corresponds to the `-s --suite name *` option of _robot_
            """,
        robot_name="suite",
        robot_priority=500,
        robot_short_name="s",
    )
    suite_stat_level: Optional[int] = field(
        description="""\
            How many levels to show in `Statistics by Suite`
            in log and report. By default all suite levels are
            shown. Example:  --suitestatlevel 3

            corresponds to the `--suitestatlevel level` option of _robot_
            """,
        robot_name="suitestatlevel",
        robot_priority=500,
    )
    tag_doc: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Add documentation to tags matching the given
            pattern. Documentation is shown in `Test Details` and
            also as a tooltip in `Statistics by Tag`. Pattern can
            use `*`, `?` and `[]` as wildcards like --test.
            Documentation can contain formatting like --doc.

            Examples:

            ```
            --tagdoc mytag:Example
            --tagdoc "owner-*:Original author"
            ```

            corresponds to the `--tagdoc pattern:doc *` option of _robot_
            """,
        robot_name="tagdoc",
        robot_priority=500,
    )
    tag_stat_combine: Optional[List[Union[str, Dict[str, str]]]] = field(
        description="""\
            Create combined statistics based on tags.
            These statistics are added into `Statistics by Tag`.
            If the optional `name` is not given, name of the
            combined tag is got from the specified tags. Tags are
            matched using the same rules as with --include.

            Examples:

            ```
            --tagstatcombine requirement-*
            --tagstatcombine tag1ANDtag2:My_name
            ```

            corresponds to the `--tagstatcombine tags:name *` option of _robot_
            """,
        robot_name="tagstatcombine",
        robot_priority=500,
    )
    tag_stat_exclude: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Exclude matching tags from `Statistics by Tag`.
            This option can be used with --tagstatinclude
            similarly as --exclude is used with --include.

            corresponds to the `--tagstatexclude tag *` option of _robot_
            """,
        robot_name="tagstatexclude",
        robot_priority=500,
    )
    tag_stat_include: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Include only matching tags in `Statistics by Tag`
            in log and report. By default all tags are shown.
            Given tag can be a pattern like with --include.

            corresponds to the `--tagstatinclude tag *` option of _robot_
            """,
        robot_name="tagstatinclude",
        robot_priority=500,
    )
    tag_stat_link: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Add external links into `Statistics by
            Tag`. Pattern can use `*`, `?` and `[]` as wildcards
            like --test. Characters matching to `*` and `?`
            wildcards can be used in link and title with syntax
            %N, where N is index of the match (starting from 1).

            Examples:

            ```
            --tagstatlink mytag:http://my.domain:Title
            --tagstatlink "bug-*:http://url/id=%1:Issue Tracker"
            ```

            corresponds to the `--tagstatlink pattern:link:title *` option of _robot_
            """,
        robot_name="tagstatlink",
        robot_priority=500,
    )
    tasks: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Alias to --test. Especially applicable with --rpa.

            corresponds to the `--task name *` option of _robot_
            """,
        robot_name="task",
        robot_priority=500,
    )
    tests: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Select tests by name or by long name containing also
            parent suite name like `Parent.Test`. Name is case
            and space insensitive and it can also be a simple
            pattern where `*` matches anything, `?` matches any
            single character, and `[chars]` matches one character
            in brackets.

            corresponds to the `-t --test name *` option of _robot_
            """,
        robot_name="test",
        robot_priority=500,
        robot_short_name="t",
    )
    timestamp_outputs: Union[bool, Flag, None] = field(
        description="""\
            When this option is used, timestamp in a format
            `YYYYMMDD-hhmmss` is added to all generated output
            files between their basename and extension. For
            example `-T -o output.xml -r report.html -l none`
            creates files like `output-20070503-154410.xml` and
            `report-20070503-154410.html`.

            corresponds to the `-T --timestampoutputs` option of _robot_
            """,
        robot_name="timestampoutputs",
        robot_priority=500,
        robot_short_name="T",
        robot_is_flag=True,
    )
    xunit: Optional[Union[str, StringExpression]] = field(
        description="""\
            xUnit compatible result file. Not created unless this
            option is specified.

            corresponds to the `-x --xunit file` option of _robot_
            """,
        robot_name="xunit",
        robot_priority=500,
        robot_short_name="x",
    )


@dataclass
class CommonExtraOptions(BaseOptions):
    """Extra common options for all _robot_ commands."""

    extend_excludes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --exclude option.

            Select test cases not to run by tag. These tests are
            not run even if included with --include. Tags are
            matched using same rules as with --include.

            corresponds to the `-e --exclude tag *` option of _robot_
            """,
    )
    extend_expand_keywords: Optional[List[Union[str, NamePattern, TagPattern]]] = field(
        description="""\
            Appends entries to the --expandkeywords option.

            Matching keywords will be automatically expanded in
            the log file. Matching against keyword name or tags
            work using same rules as with --removekeywords.

            Examples:

            ```
            --expandkeywords name:BuiltIn.Log
            --expandkeywords tag:expand
            ```

            corresponds to the `--expandkeywords name:<pattern>|tag:<pattern> *` option of _robot_
            """,
    )
    extend_flatten_keywords: Optional[
        List[Union[str, Literal["for", "while", "iteration"], NamePattern, TagPattern]]
    ] = field(
        description="""\
            Appends entries to the --flattenkeywords option.

            Flattens matching keywords in the generated log file.
            Matching keywords get all log messages from their
            child keywords and children are discarded otherwise.
            for:     flatten FOR loops fully
            while:   flatten WHILE loops fully
            iteration: flatten FOR/WHILE loop iterations
            foritem: deprecated alias for `iteration`
            name:<pattern>:  flatten matched keywords using same
            matching rules as with
            `--removekeywords name:<pattern>`
            tag:<pattern>:  flatten matched keywords using same
            matching rules as with
            `--removekeywords tag:<pattern>`

            corresponds to the `--flattenkeywords for|while|iteration|name:<pattern>|tag:<pattern> *` option of _robot_
            """,
    )
    extend_includes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --include option.

            Select tests by tag. Similarly as name with --test,
            tag is case and space insensitive and it is possible
            to use patterns with `*`, `?` and `[]` as wildcards.
            Tags and patterns can also be combined together with
            `AND`, `OR`, and `NOT` operators.

            Examples:

            ```
            --include foo --include bar*
            --include fooANDbar*
            ```

            corresponds to the `-i --include tag *` option of _robot_
            """,
    )
    extend_metadata: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --metadata option.

            Set metadata of the top level suite. Value can
            contain formatting and be read from a file similarly
            as --doc. Example: --metadata Version:1.2

            corresponds to the `-M --metadata name:value *` option of _robot_
            """,
    )
    extend_parse_include: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --parseinclude option.

            Parse only files matching `pattern`. It can be:
            - a file name or pattern like `example.robot` or
            `*.robot` to parse all files matching that name,
            - a file path like `path/to/example.robot`, or
            - a directory path like `path/to/example` to parse
            all files in that directory, recursively.

            corresponds to the `-I --parseinclude pattern *` option of _robot_
            """,
    )
    extend_pre_rebot_modifiers: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Appends entries to the --prerebotmodifier option.

            Class to programmatically modify the result
            model before creating reports and logs. Accepts
            arguments the same way as with --listener.

            corresponds to the `--prerebotmodifier modifier *` option of _robot_
            """,
    )
    extend_python_path: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --pythonpath option.

            Additional locations (directories, ZIPs) where to
            search libraries and other extensions when they are
            imported. Multiple paths can be given by separating
            them with a colon (`:`) or by using this option
            several times. Given path can also be a glob pattern
            matching multiple paths.

            Examples:

            ```
            --pythonpath libs/
            --pythonpath /opt/libs:libraries.zip
            ```

            corresponds to the `-P --pythonpath path *` option of _robot_
            """,
    )
    extend_remove_keywords: Optional[
        List[Union[str, Literal["all", "passed", "for", "wuks"], NamePattern, TagPattern]]
    ] = field(
        description="""\
            Appends entries to the --removekeywords option.

            Remove keyword data from the generated log file.
            Keywords containing warnings are not removed except
            in the `all` mode.
            all:     remove data from all keywords
            passed:  remove data only from keywords in passed
            test cases and suites
            for:     remove passed iterations from for loops
            while:   remove passed iterations from while loops
            wuks:    remove all but the last failing keyword
            inside `BuiltIn.Wait Until Keyword Succeeds`
            name:<pattern>:  remove data from keywords that match
            the given pattern. The pattern is matched
            against the full name of the keyword (e.g.
            'MyLib.Keyword', 'resource.Second Keyword'),
            is case, space, and underscore insensitive,
            and may contain `*`, `?` and `[]` wildcards.

            Examples:

            ```
            --removekeywords name:Lib.HugeKw
            --removekeywords name:myresource.*
            ```


            tag:<pattern>:  remove data from keywords that match
            the given pattern. Tags are case and space
            insensitive and patterns can contain `*`,
            `?` and `[]` wildcards. Tags and patterns
            can also be combined together with `AND`,
            `OR`, and `NOT` operators.

            Examples:

            ```
            --removekeywords foo
            --removekeywords fooANDbar*
            ```

            corresponds to the `--removekeywords all|passed|for|wuks|name:<pattern>|tag:<pattern> *` option of _robot_
            """,
    )
    extend_set_tag: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --settag option.

            Sets given tag(s) to all executed tests.

            corresponds to the `-G --settag tag *` option of _robot_
            """,
    )
    extend_suites: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --suite option.

            Select suites by name. When this option is used with
            --test, --include or --exclude, only tests in
            matching suites and also matching other filtering
            criteria are selected. Name can be a simple pattern
            similarly as with --test and it can contain parent
            name separated with a dot. For example, `-s X.Y`
            selects suite `Y` only if its parent is `X`.

            corresponds to the `-s --suite name *` option of _robot_
            """,
    )
    extend_tag_doc: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --tagdoc option.

            Add documentation to tags matching the given
            pattern. Documentation is shown in `Test Details` and
            also as a tooltip in `Statistics by Tag`. Pattern can
            use `*`, `?` and `[]` as wildcards like --test.
            Documentation can contain formatting like --doc.

            Examples:

            ```
            --tagdoc mytag:Example
            --tagdoc "owner-*:Original author"
            ```

            corresponds to the `--tagdoc pattern:doc *` option of _robot_
            """,
    )
    extend_tag_stat_combine: Optional[List[Union[str, Dict[str, str]]]] = field(
        description="""\
            Appends entries to the --tagstatcombine option.

            Create combined statistics based on tags.
            These statistics are added into `Statistics by Tag`.
            If the optional `name` is not given, name of the
            combined tag is got from the specified tags. Tags are
            matched using the same rules as with --include.

            Examples:

            ```
            --tagstatcombine requirement-*
            --tagstatcombine tag1ANDtag2:My_name
            ```

            corresponds to the `--tagstatcombine tags:name *` option of _robot_
            """,
    )
    extend_tag_stat_exclude: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --tagstatexclude option.

            Exclude matching tags from `Statistics by Tag`.
            This option can be used with --tagstatinclude
            similarly as --exclude is used with --include.

            corresponds to the `--tagstatexclude tag *` option of _robot_
            """,
    )
    extend_tag_stat_include: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --tagstatinclude option.

            Include only matching tags in `Statistics by Tag`
            in log and report. By default all tags are shown.
            Given tag can be a pattern like with --include.

            corresponds to the `--tagstatinclude tag *` option of _robot_
            """,
    )
    extend_tag_stat_link: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --tagstatlink option.

            Add external links into `Statistics by
            Tag`. Pattern can use `*`, `?` and `[]` as wildcards
            like --test. Characters matching to `*` and `?`
            wildcards can be used in link and title with syntax
            %N, where N is index of the match (starting from 1).

            Examples:

            ```
            --tagstatlink mytag:http://my.domain:Title
            --tagstatlink "bug-*:http://url/id=%1:Issue Tracker"
            ```

            corresponds to the `--tagstatlink pattern:link:title *` option of _robot_
            """,
    )
    extend_tasks: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --task option.

            Alias to --test. Especially applicable with --rpa.

            corresponds to the `--task name *` option of _robot_
            """,
    )
    extend_tests: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --test option.

            Select tests by name or by long name containing also
            parent suite name like `Parent.Test`. Name is case
            and space insensitive and it can also be a simple
            pattern where `*` matches anything, `?` matches any
            single character, and `[chars]` matches one character
            in brackets.

            corresponds to the `-t --test name *` option of _robot_
            """,
    )


@dataclass
class RobotOptions(BaseOptions):
    """Options for _robot_ command."""

    console: Optional[Literal["verbose", "dotted", "skipped", "quiet", "none"]] = field(
        description="""\
            How to report execution on the console.
            verbose:  report every suite and test (default)
            dotted:   only show `.` for passed test, `s` for
            skipped tests, and `F` for failed tests
            quiet:    no output except for errors and warnings
            none:     no output whatsoever

            corresponds to the `--console type` option of _robot_
            """,
        robot_name="console",
        robot_priority=500,
    )
    console_markers: Optional[Literal["auto", "on", "off"]] = field(
        description="""\
            Show markers on the console when top level
            keywords in a test case end. Values have same
            semantics as with --consolecolors.

            corresponds to the `-K --consolemarkers auto|on|off` option of _robot_
            """,
        robot_name="consolemarkers",
        robot_priority=500,
        robot_short_name="K",
    )
    console_width: Optional[int] = field(
        description="""\
            Width of the console output. Default is 78.

            corresponds to the `-W --consolewidth chars` option of _robot_
            """,
        robot_name="consolewidth",
        robot_priority=500,
        robot_short_name="W",
    )
    debug_file: Optional[Union[str, StringExpression]] = field(
        description="""\
            Debug file written during execution. Not created
            unless this option is specified.

            corresponds to the `-b --debugfile file` option of _robot_
            """,
        robot_name="debugfile",
        robot_priority=500,
        robot_short_name="b",
    )
    dotted: Union[bool, Flag, None] = field(
        description="""\
            Shortcut for `--console dotted`.

            corresponds to the `-. --dotted` option of _robot_
            """,
        robot_name="dotted",
        robot_priority=500,
        robot_short_name=".",
        robot_is_flag=True,
    )
    dry_run: Union[bool, Flag, None] = field(
        description="""\
            Verifies test data and runs tests so that library
            keywords are not executed.

            corresponds to the `--dryrun` option of _robot_
            """,
        robot_name="dryrun",
        robot_priority=500,
        robot_is_flag=True,
    )
    exit_on_error: Union[bool, Flag, None] = field(
        description="""\
            Stops test execution if any error occurs when parsing
            test data, importing libraries, and so on.

            corresponds to the `--exitonerror` option of _robot_
            """,
        robot_name="exitonerror",
        robot_priority=500,
        robot_is_flag=True,
    )
    exit_on_failure: Union[bool, Flag, None] = field(
        description="""\
            Stops test execution if any test fails.

            corresponds to the `-X --exitonfailure` option of _robot_
            """,
        robot_name="exitonfailure",
        robot_priority=500,
        robot_short_name="X",
        robot_is_flag=True,
    )
    extensions: Optional[Union[str, StringExpression]] = field(
        description="""\
            Parse only files with this extension when executing
            a directory. Has no effect when running individual
            files or when using resource files. If more than one
            extension is needed, separate them with a colon.

            Examples:

            ```
            `--extension txt`, `--extension robot:txt`
            ```


            Only `*.robot` files are parsed by default.

            corresponds to the `-F --extension value` option of _robot_
            """,
        robot_name="extension",
        robot_priority=500,
        robot_short_name="F",
    )
    languages: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Activate localization. `lang` can be a name or a code
            of a built-in language, or a path or a module name of
            a custom language file.

            corresponds to the `--language lang *` option of _robot_
            """,
        robot_name="language",
        robot_priority=500,
    )
    listeners: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Class or module for monitoring test execution.
            Gets notifications e.g. when tests start and end.
            Arguments to the listener class can be given after
            the name using a colon or a semicolon as a separator.

            Examples:

            ```
            --listener MyListener
            --listener path/to/Listener.py:arg1:arg2
            ```

            corresponds to the `--listener listener *` option of _robot_
            """,
        robot_name="listener",
        robot_priority=500,
    )
    log_level: Optional[Union[str, StringExpression]] = field(
        description="""\
            Threshold level for logging. Available levels: TRACE,
            DEBUG, INFO (default), WARN, NONE (no logging). Use
            syntax `LOGLEVEL:DEFAULT` to define the default
            visible log level in log files.

            Examples:

            ```
            --loglevel DEBUG
            --loglevel DEBUG:INFO
            ```

            corresponds to the `-L --loglevel level` option of _robot_
            """,
        robot_name="loglevel",
        robot_priority=500,
        robot_short_name="L",
    )
    max_assign_length: Optional[int] = field(
        description="""\
            Maximum number of characters to show in log
            when variables are assigned. Zero or negative values
            can be used to avoid showing assigned values at all.
            Default is 200.

            corresponds to the `--maxassignlength characters` option of _robot_
            """,
        robot_name="maxassignlength",
        robot_priority=500,
    )
    max_error_lines: Optional[int] = field(
        description="""\
            Maximum number of error message lines to show in
            report when tests fail. Default is 40, minimum is 10
            and `NONE` can be used to show the full message.

            corresponds to the `--maxerrorlines lines` option of _robot_
            """,
        robot_name="maxerrorlines",
        robot_priority=500,
    )
    output: Optional[Union[str, StringExpression]] = field(
        description="""\
            XML output file. Given path, similarly as paths given
            to --log, --report, --xunit, and --debugfile, is
            relative to --outputdir unless given as an absolute
            path. Other output files are created based on XML
            output files after the test execution and XML outputs
            can also be further processed with Rebot tool. Can be
            disabled by giving a special value `NONE`.
            Default: output.xml

            corresponds to the `-o --output file` option of _robot_
            """,
        robot_name="output",
        robot_priority=500,
        robot_short_name="o",
    )
    parsers: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Custom parser class or module. Parser classes accept
            arguments the same way as with --listener.

            corresponds to the `--parser parser *` option of _robot_
            """,
        robot_name="parser",
        robot_priority=500,
    )
    pre_run_modifiers: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Class to programmatically modify the suite
            structure before execution. Accepts arguments the
            same way as with --listener.

            corresponds to the `--prerunmodifier modifier *` option of _robot_
            """,
        robot_name="prerunmodifier",
        robot_priority=500,
    )
    quiet: Union[bool, Flag, None] = field(
        description="""\
            Shortcut for `--console quiet`.

            corresponds to the `--quiet` option of _robot_
            """,
        robot_name="quiet",
        robot_priority=500,
        robot_is_flag=True,
    )
    randomize: Optional[Union[str, Literal["all", "suites", "tests", "none"]]] = field(
        description="""\
            Randomizes the test execution order.
            all:    randomizes both suites and tests
            suites: randomizes suites
            tests:  randomizes tests
            none:   no randomization (default)
            Use syntax `VALUE:SEED` to give a custom random seed.
            The seed must be an integer.

            Examples:

            ```
            --randomize all
            --randomize tests:1234
            ```

            corresponds to the `--randomize all|suites|tests|none` option of _robot_
            """,
        robot_name="randomize",
        robot_priority=500,
    )
    re_run_failed: Optional[Union[str, StringExpression]] = field(
        description="""\
            Select failed tests from an earlier output file to be
            re-executed. Equivalent to selecting same tests
            individually using --test.

            corresponds to the `-R --rerunfailed output` option of _robot_
            """,
        robot_name="rerunfailed",
        robot_priority=500,
        robot_short_name="R",
    )
    re_run_failed_suites: Optional[Union[str, StringExpression]] = field(
        description="""\
            Select failed suites from an earlier output
            file to be re-executed.

            corresponds to the `-S --rerunfailedsuites output` option of _robot_
            """,
        robot_name="rerunfailedsuites",
        robot_priority=500,
        robot_short_name="S",
    )
    run_empty_suite: Union[bool, Flag, None] = field(
        description="""\
            Executes suite even if it contains no tests. Useful
            e.g. with --include/--exclude when it is not an error
            that no test matches the condition.

            corresponds to the `--runemptysuite` option of _robot_
            """,
        robot_name="runemptysuite",
        robot_priority=500,
        robot_is_flag=True,
    )
    skip: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Tests having given tag will be skipped. Tag can be
            a pattern.

            corresponds to the `--skip tag *` option of _robot_
            """,
        robot_name="skip",
        robot_priority=500,
    )
    skip_on_failure: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Tests having given tag will be skipped if they fail.
            Tag can be a pattern

            corresponds to the `--skiponfailure tag *` option of _robot_
            """,
        robot_name="skiponfailure",
        robot_priority=500,
    )
    skip_teardown_on_exit: Union[bool, Flag, None] = field(
        description="""\
            Causes teardowns to be skipped if test execution is
            stopped prematurely.

            corresponds to the `--skipteardownonexit` option of _robot_
            """,
        robot_name="skipteardownonexit",
        robot_priority=500,
        robot_is_flag=True,
    )
    variables: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Set variables in the test data. Only scalar
            variables with string value are supported and name is
            given without `${}`. See --variablefile for a more
            powerful variable setting mechanism.

            Examples:

            ```
            --variable name:Robot  =>  ${name} = `Robot`
            -v "hello:Hello world" =>  ${hello} = `Hello world`
            -v x: -v y:42          =>  ${x} = ``, ${y} = `42`
            ```

            corresponds to the `-v --variable name:value *` option of _robot_
            """,
        robot_name="variable",
        robot_priority=500,
        robot_short_name="v",
    )
    variable_files: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Python or YAML file file to read variables from.
            Possible arguments to the variable file can be given
            after the path using colon or semicolon as separator.

            Examples:

            ```
            --variablefile path/vars.yaml
            --variablefile environment.py:testing
            ```

            corresponds to the `-V --variablefile path *` option of _robot_
            """,
        robot_name="variablefile",
        robot_priority=500,
        robot_short_name="V",
    )


@dataclass
class RobotExtraOptions(BaseOptions):
    """Extra options for _robot_ command."""

    extend_languages: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --language option.

            Activate localization. `lang` can be a name or a code
            of a built-in language, or a path or a module name of
            a custom language file.

            corresponds to the `--language lang *` option of _rebot_
            """,
    )
    extend_listeners: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Appends entries to the --listener option.

            Class or module for monitoring test execution.
            Gets notifications e.g. when tests start and end.
            Arguments to the listener class can be given after
            the name using a colon or a semicolon as a separator.

            Examples:

            ```
            --listener MyListener
            --listener path/to/Listener.py:arg1:arg2
            ```

            corresponds to the `--listener listener *` option of _rebot_
            """,
    )
    extend_parsers: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Appends entries to the --parser option.

            Custom parser class or module. Parser classes accept
            arguments the same way as with --listener.

            corresponds to the `--parser parser *` option of _rebot_
            """,
    )
    extend_pre_run_modifiers: Optional[Dict[str, List[Union[str, StringExpression]]]] = field(
        description="""\
            Appends entries to the --prerunmodifier option.

            Class to programmatically modify the suite
            structure before execution. Accepts arguments the
            same way as with --listener.

            corresponds to the `--prerunmodifier modifier *` option of _rebot_
            """,
    )
    extend_skip: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --skip option.

            Tests having given tag will be skipped. Tag can be
            a pattern.

            corresponds to the `--skip tag *` option of _rebot_
            """,
    )
    extend_skip_on_failure: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --skiponfailure option.

            Tests having given tag will be skipped if they fail.
            Tag can be a pattern

            corresponds to the `--skiponfailure tag *` option of _rebot_
            """,
    )
    extend_variables: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --variable option.

            Set variables in the test data. Only scalar
            variables with string value are supported and name is
            given without `${}`. See --variablefile for a more
            powerful variable setting mechanism.

            Examples:

            ```
            --variable name:Robot  =>  ${name} = `Robot`
            -v "hello:Hello world" =>  ${hello} = `Hello world`
            -v x: -v y:42          =>  ${x} = ``, ${y} = `42`
            ```

            corresponds to the `-v --variable name:value *` option of _rebot_
            """,
    )
    extend_variable_files: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --variablefile option.

            Python or YAML file file to read variables from.
            Possible arguments to the variable file can be given
            after the path using colon or semicolon as separator.

            Examples:

            ```
            --variablefile path/vars.yaml
            --variablefile environment.py:testing
            ```

            corresponds to the `-V --variablefile path *` option of _rebot_
            """,
    )


@dataclass
class RebotOptions(BaseOptions):
    """Options for _rebot_ command."""

    end_time: Optional[Union[str, StringExpression]] = field(
        description="""\
            Same as --starttime but for end time. If both options
            are used, elapsed time of the suite is calculated
            based on them. For combined suites, it is otherwise
            calculated by adding elapsed times of the combined
            suites together.

            corresponds to the `--endtime timestamp` option of _rebot_
            """,
        robot_name="endtime",
        robot_priority=500,
    )
    log_level: Optional[Union[str, StringExpression]] = field(
        description="""\
            Threshold for selecting messages. Available levels:
            TRACE (default), DEBUG, INFO, WARN, NONE (no msgs).
            Use syntax `LOGLEVEL:DEFAULT` to define the default
            visible log level in log files.

            Examples:

            ```
            --loglevel DEBUG
            --loglevel DEBUG:INFO
            ```

            corresponds to the `-L --loglevel level` option of _rebot_
            """,
        robot_name="loglevel",
        robot_priority=500,
        robot_short_name="L",
    )
    merge: Union[bool, Flag, None] = field(
        description="""\
            When combining results, merge outputs together
            instead of putting them under a new top level suite.
            Example: rebot --merge orig.xml rerun.xml

            corresponds to the `-R --merge` option of _rebot_
            """,
        robot_name="merge",
        robot_priority=500,
        robot_short_name="R",
        robot_is_flag=True,
    )
    output: Optional[Union[str, StringExpression]] = field(
        description="""\
            XML output file. Not created unless this option is
            specified. Given path, similarly as paths given to
            --log, --report and --xunit, is relative to
            --outputdir unless given as an absolute path.

            corresponds to the `-o --output file` option of _rebot_
            """,
        robot_name="output",
        robot_priority=500,
        robot_short_name="o",
    )
    process_empty_suite: Union[bool, Flag, None] = field(
        description="""\
            Processes output also if the top level suite is
            empty. Useful e.g. with --include/--exclude when it
            is not an error that there are no matches.
            Use --skiponfailure when starting execution instead.

            corresponds to the `--processemptysuite` option of _rebot_
            """,
        robot_name="processemptysuite",
        robot_priority=500,
        robot_is_flag=True,
    )
    start_time: Optional[Union[str, StringExpression]] = field(
        description="""\
            Set execution start time. Timestamp must be given in
            format `2007-10-01 15:12:42.268` where all separators
            are optional (e.g. `20071001151242268` is ok too) and
            parts from milliseconds to hours can be omitted if
            they are zero (e.g. `2007-10-01`). This can be used
            to override start time of a single suite or to set
            start time for a combined suite, which would
            otherwise be `N/A`.

            corresponds to the `--starttime timestamp` option of _rebot_
            """,
        robot_name="starttime",
        robot_priority=500,
    )


@dataclass
class LibDocOptions(BaseOptions):
    """Options for _libdoc_ command."""

    doc_format: Optional[Literal["ROBOT", "HTML", "TEXT", "REST"]] = field(
        description="""\
            Specifies the source documentation format. Possible
            values are Robot Framework's documentation format,
            HTML, plain text, and reStructuredText. The default
            value can be specified in library source code and
            the initial default value is ROBOT.

            corresponds to the `-F --docformat ROBOT|HTML|TEXT|REST` option of _libdoc_
            """,
        robot_name="docformat",
        robot_priority=500,
        robot_short_name="F",
    )
    format: Optional[Literal["HTML", "XML", "JSON", "LIBSPEC"]] = field(
        description="""\
            Specifies whether to generate an HTML output for
            humans or a machine readable spec file in XML or JSON
            format. The LIBSPEC format means XML spec with
            documentations converted to HTML. The default format
            is got from the output file extension.

            corresponds to the `-f --format HTML|XML|JSON|LIBSPEC` option of _libdoc_
            """,
        robot_name="format",
        robot_priority=500,
        robot_short_name="f",
    )
    name: Optional[Union[str, StringExpression]] = field(
        description="""\
            Sets the name of the documented library or resource.

            corresponds to the `-n --name name` option of _libdoc_
            """,
        robot_name="name",
        robot_priority=500,
        robot_short_name="n",
    )
    python_path: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Additional locations where to search for libraries
            and resources.

            corresponds to the `-P --pythonpath path *` option of _libdoc_
            """,
        robot_name="pythonpath",
        robot_priority=500,
        robot_short_name="P",
    )
    quiet: Union[bool, Flag, None] = field(
        description="""\
            Do not print the path of the generated output file
            to the console. New in RF 4.0.

            corresponds to the `--quiet` option of _libdoc_
            """,
        robot_name="quiet",
        robot_priority=500,
        robot_is_flag=True,
    )
    spec_doc_format: Optional[Literal["RAW", "HTML"]] = field(
        description="""\
            Specifies the documentation format used with XML and
            JSON spec files. RAW means preserving the original
            documentation format and HTML means converting
            documentation to HTML. The default is RAW with XML
            spec files and HTML with JSON specs and when using
            the special LIBSPEC format. New in RF 4.0.

            corresponds to the `-s --specdocformat RAW|HTML` option of _libdoc_
            """,
        robot_name="specdocformat",
        robot_priority=500,
        robot_short_name="s",
    )
    theme: Optional[Literal["DARK", "LIGHT", "NONE"]] = field(
        description="""\
            Use dark or light HTML theme. If this option is not
            used, or the value is NONE, the theme is selected
            based on the browser color scheme. New in RF 6.0.

            corresponds to the `--theme DARK|LIGHT|NONE` option of _libdoc_
            """,
        robot_name="theme",
        robot_priority=500,
    )


@dataclass
class LibDocExtraOptions(BaseOptions):
    """Extra options for _libdoc_ command."""

    extend_python_path: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --pythonpath option.

            Additional locations where to search for libraries
            and resources.

            corresponds to the `-P --pythonpath path *` option of _libdoc_
            """,
    )


@dataclass
class TestDocOptions(BaseOptions):
    """Options for _testdoc_ command."""

    doc: Optional[Union[str, StringExpression]] = field(
        description="""\
            Override the documentation of the top level suite.

            corresponds to the `-D --doc document` option of _testdoc_
            """,
        robot_name="doc",
        robot_priority=500,
        robot_short_name="D",
    )
    excludes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Exclude tests by tags.

            corresponds to the `-e --exclude tag *` option of _testdoc_
            """,
        robot_name="exclude",
        robot_priority=500,
        robot_short_name="e",
    )
    includes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Include tests by tags.

            corresponds to the `-i --include tag *` option of _testdoc_
            """,
        robot_name="include",
        robot_priority=500,
        robot_short_name="i",
    )
    metadata: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Set/override metadata of the top level suite.

            corresponds to the `-M --metadata name:value *` option of _testdoc_
            """,
        robot_name="metadata",
        robot_priority=500,
        robot_short_name="M",
    )
    name: Optional[Union[str, StringExpression]] = field(
        description="""\
            Override the name of the top level suite.

            corresponds to the `-N --name name` option of _testdoc_
            """,
        robot_name="name",
        robot_priority=500,
        robot_short_name="N",
    )
    set_tag: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Set given tag(s) to all test cases.

            corresponds to the `-G --settag tag *` option of _testdoc_
            """,
        robot_name="settag",
        robot_priority=500,
        robot_short_name="G",
    )
    suites: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Include suites by name.

            corresponds to the `-s --suite name *` option of _testdoc_
            """,
        robot_name="suite",
        robot_priority=500,
        robot_short_name="s",
    )
    tests: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Include tests by name.

            corresponds to the `-t --test name *` option of _testdoc_
            """,
        robot_name="test",
        robot_priority=500,
        robot_short_name="t",
    )
    title: Optional[Union[str, StringExpression]] = field(
        description="""\
            Set the title of the generated documentation.
            Underscores in the title are converted to spaces.
            The default title is the name of the top level suite.

            corresponds to the `-T --title title` option of _testdoc_
            """,
        robot_name="title",
        robot_priority=500,
        robot_short_name="T",
    )


@dataclass
class TestDocExtraOptions(BaseOptions):
    """Extra options for _testdoc_ command."""

    extend_excludes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --exclude option.

            Exclude tests by tags.

            corresponds to the `-e --exclude tag *` option of _testdoc_
            """,
    )
    extend_includes: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --include option.

            Include tests by tags.

            corresponds to the `-i --include tag *` option of _testdoc_
            """,
    )
    extend_metadata: Optional[Dict[str, Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --metadata option.

            Set/override metadata of the top level suite.

            corresponds to the `-M --metadata name:value *` option of _testdoc_
            """,
    )
    extend_set_tag: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --settag option.

            Set given tag(s) to all test cases.

            corresponds to the `-G --settag tag *` option of _testdoc_
            """,
    )
    extend_suites: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --suite option.

            Include suites by name.

            corresponds to the `-s --suite name *` option of _testdoc_
            """,
    )
    extend_tests: Optional[List[Union[str, StringExpression]]] = field(
        description="""\
            Appends entries to the --test option.

            Include tests by name.

            corresponds to the `-t --test name *` option of _testdoc_
            """,
    )


# end generated code


@dataclass
class RebotProfile(RebotOptions, CommonOptions, CommonExtraOptions):
    """Profile for _rebot_ command."""


@dataclass
class LibDocProfile(LibDocOptions, LibDocExtraOptions):
    """Profile for _libdoc_ command."""


@dataclass
class TestDocProfile(TestDocOptions, TestDocExtraOptions):
    """Profile for _testdoc_ command."""


@dataclass
class RobotBaseProfile(CommonOptions, CommonExtraOptions, RobotOptions, RobotExtraOptions):
    """Base profile for Robot Framework."""

    args: Optional[List[str]] = field(
        description="""\
            Arguments to be passed to _robot_.

            Examples:
            ```toml
            args = ["-t", "abc"]
            ```
            """,
        robot_priority=1000,
    )
    paths: Union[str, List[str], None] = field(
        description="""\
            Specifies the paths where robot/robotcode should discover tests.
            If no paths are given at the command line this value is used.

            Examples:
            ```toml
            paths = ["tests"]
            ```

            Corresponds to the `paths` argument of __robot__.
            """
    )
    env: Optional[Dict[str, str]] = field(
        description="""\
            Define environment variables to be set before running tests.

            Examples:
            ```toml
            [env]
            TEST_VAR = "test"
            SECRET = "password"
            ```
            """,
    )

    rebot: Optional[RebotProfile] = field(
        description="""\
            Options to be passed to _rebot_.
            """
    )

    libdoc: Optional[LibDocProfile] = field(
        description="""\
            Options to be passed to _libdoc_.
        """
    )

    testdoc: Optional[TestDocProfile] = field(
        description="""\
            Options to be passed to _testdoc_.
        """
    )

    def save(self, path: "os.PathLike[str]") -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("w", encoding="utf-8") as f:
            f.write(tomli_w.dumps(as_dict(self, remove_defaults=True)))


@dataclass
class RobotExtraBaseProfile(RobotBaseProfile):
    """Base profile for Robot Framework with Extras."""

    extend_args: Optional[List[str]] = field(
        description="""\
            Append extra arguments to be passed to _robot_.
            """,
    )

    extend_env: Optional[Dict[str, str]] = field(
        description="""\
            Append extra environment variables to be set before tests.
            """,
    )

    extend_paths: Union[str, List[str], None] = field(
        description="""\
            Append extra entries to the paths argument.

            Examples:
            ```toml
            paths = ["tests"]
            ```
            """
    )


@dataclass
class RobotProfile(RobotExtraBaseProfile):
    """Robot Framework configuration profile."""

    description: Optional[str] = field(description="Description of the profile.")

    detached: Optional[bool] = field(
        description="""\
            The profile should be detached.
            Detached means it is not inherited from the main profile.
            """,
    )

    enabled: Union[bool, Condition, None] = field(
        description="""\
            If enabled the profile is used. You can also use and `if` condition
            to calculate the enabled state.

            Examples:
            ```toml
            # alway disabled
            enabled = false
            ```

            ```toml
            # enabled if TEST_VAR is set
            enabled = { if = 'environ.get("CI") == "true"' }
            ```
            """
    )

    precedence: Optional[int] = field(
        description="""\
        Precedence of the profile. Lower values are executed first. If not set the order is undefined.
        """
    )


@dataclass
class RobotConfig(RobotExtraBaseProfile):
    """Robot Framework configuration."""

    default_profiles: Union[str, List[str], None] = field(
        description="""\
            Selects the Default profile if no profile is given at command line.

            Examples:
            ```toml
            default_profiles = "default"
            ```

            ```toml
            default_profiles = ["default", "Firefox"]
            ```
            """,
    )
    profiles: Optional[Dict[str, RobotProfile]] = field(
        description="Execution profiles.",
    )

    extend_profiles: Optional[Dict[str, RobotProfile]] = field(
        description="Extra execution profiles.",
    )

    tool: Any = field(
        description="Tool configurations.",
    )

    def select_profiles(
        self, *names: str, verbose_callback: Optional[Callable[..., None]] = None
    ) -> Dict[str, RobotProfile]:
        result: Dict[str, RobotProfile] = {}

        profiles = self.profiles or {}

        if not names:
            if verbose_callback:
                verbose_callback("No profiles given, try to check if there are default profiles specified.")

            default_profile = (
                [self.default_profiles] if isinstance(self.default_profiles, str) else self.default_profiles
            )

            if verbose_callback and default_profile:
                verbose_callback(f"Using default profiles: {', '.join( default_profile)}.")

            names = (*(default_profile or ()),)

        for name in names:
            profile_names = [p for p in profiles.keys() if fnmatch.fnmatchcase(p, name)]

            if not profile_names:
                raise ValueError(f"Can't find any profiles matching the pattern '{name}'.")

            for v in profile_names:
                result.update({v: profiles[v]})

        return result

    def combine_profiles(self, *names: str, verbose_callback: Optional[Callable[..., None]] = None) -> RobotBaseProfile:
        type_hints = get_type_hints(RobotBaseProfile)
        base_field_names = [f.name for f in dataclasses.fields(RobotBaseProfile)]

        result = RobotBaseProfile(
            **{
                f.name: self._verified_value(f.name, new, type_hints[f.name], self)
                for f in dataclasses.fields(RobotBaseProfile)
                if (new := getattr(self, f.name)) is not None
            }
        )

        selected_profiles = self.select_profiles(*names, verbose_callback=verbose_callback)
        if verbose_callback:
            if selected_profiles:
                verbose_callback(f"Select profiles: {', '.join(selected_profiles.keys())}")
            else:
                verbose_callback("No profiles selected.")

        for profile_name, profile in sorted(selected_profiles.items(), key=lambda x: x[1].precedence or 0):
            try:
                if profile.enabled is not None and not bool(profile.enabled):
                    if verbose_callback:
                        verbose_callback(f'Skipping profile "{profile_name}" because it\'s disabled.')
                    continue
            except EvaluationError as e:
                raise ValueError(f'Error evaluating "enabled" condition for profile "{profile_name}": {e}') from e

            if verbose_callback:
                verbose_callback(f'Using profile "{profile_name}".')

            if profile.detached:
                result = RobotBaseProfile()

            for f in dataclasses.fields(profile):
                if f.name.startswith("extend_"):
                    new = self._verified_value(
                        f.name, getattr(profile, f.name), type_hints[f.name[EXTEND_PREFIX_LEN:]], profile
                    )
                    if new is None:
                        continue

                    old = getattr(result, f.name[EXTEND_PREFIX_LEN:])
                    if old is None:
                        setattr(result, f.name[EXTEND_PREFIX_LEN:], new)
                    else:
                        if isinstance(old, dict):
                            setattr(result, f.name[EXTEND_PREFIX_LEN:], {**old, **new})
                        elif isinstance(old, list):
                            setattr(result, f.name[EXTEND_PREFIX_LEN:], [*old, *new])
                        elif isinstance(old, tuple):
                            setattr(result, f.name[EXTEND_PREFIX_LEN:], (*old, *new))
                        else:
                            setattr(result, f.name[EXTEND_PREFIX_LEN:], new)
                    continue

                if f.name not in base_field_names:
                    continue

                if getattr(profile, f"extend_{f.name}", None) is not None:
                    continue

                new = self._verified_value(f.name, getattr(profile, f.name), type_hints[f.name], profile)
                if new is not None:
                    setattr(result, f.name, new)

        return result
