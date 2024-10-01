# robot.toml configuration settings

## [profile].description

Type: `str | None`

Description of the profile.

## [profile].detached

Type: `bool | None`

The profile should be detached.
Detached means it is not inherited from the main profile.

## [profile].enabled

Type: `bool | Condition | None`

If enabled the profile is used. You can also use and `if` condition
to calculate the enabled state.

Examples:
```toml
# always disabled
enabled = false
```

```toml
# enabled if TEST_VAR is set
enabled = { if = 'environ.get("CI") == "true"' }
```

## [profile].hidden

Type: `bool | Condition | None`

The profile should be hidden.
Hidden means it is not shown in the list of available profiles.

Examples:
```toml
hidden = true
```

```toml
hidden = { if = 'environ.get("CI") == "true"' }
```

## [profile].inherits

Type: `str | StringExpression | list[str | StringExpression] | None`

Profiles to inherit from.

Examples:
```toml
inherits = ["default", "Firefox"]
```

## [profile].precedence

Type: `int | None`

Precedence of the profile. Lower values are executed first. If not set the order is undefined.

## args

Type: `list[str] | None`

Arguments to be passed to _robot_.

Examples:
```toml
args = ["-t", "abc"]
```

## console

Type: `Literal['verbose', 'dotted', 'skipped', 'quiet', 'none'] | None`

How to report execution on the console.

**verbose:** report every suite and test (default)

**dotted:** only show `.` for passed test, `s` for
skipped tests, and `F` for failed tests

**quiet:** no output except for errors and warnings

**none:** no output whatsoever

corresponds to the `--console type` option of _robot_

## console-colors

Type: `Literal['auto', 'on', 'ansi', 'off'] | None`

Use colors on console output or not.

**auto:** use colors when output not redirected (default)

**on:** always use colors

**ansi:** like `on` but use ANSI colors also on Windows

**off:** disable colors altogether

corresponds to the `-C --consolecolors auto|on|ansi|off` option of _robot_

## console-links

Type: `Literal['auto', 'off'] | None`

Control making paths to results files hyperlinks.

**auto:** use links when colors are enabled (default)

**off:** disable links unconditionally

corresponds to the `--consolelinks auto|off` option of _robot_

## console-markers

Type: `Literal['auto', 'on', 'off'] | None`

Show markers on the console when top level
keywords in a test case end. Values have same
semantics as with --consolecolors.

corresponds to the `-K --consolemarkers auto|on|off` option of _robot_

## console-width

Type: `int | None`

Width of the console output. Default is 78.

corresponds to the `-W --consolewidth chars` option of _robot_

## debug-file

Type: `str | StringExpression | None`

Debug file written during execution. Not created
unless this option is specified.

corresponds to the `-b --debugfile file` option of _robot_

## default-profiles

Type: `str | list[str] | None`

Selects the Default profile if no profile is given at command line.

Examples:
```toml
default_profiles = "default"
```

```toml
default_profiles = ["default", "Firefox"]
```

## doc

Type: `str | StringExpression | None`

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

## dotted

Type: `bool | Flag | None`

Shortcut for `--console dotted`.

corresponds to the `-. --dotted` option of _robot_

## dry-run

Type: `bool | Flag | None`

Verifies test data and runs tests so that library
keywords are not executed.

corresponds to the `--dryrun` option of _robot_

## env

Type: `dict[str, str | StringExpression] | None`

Define environment variables to be set before running tests.

Examples:
```toml
[env]
TEST_VAR = "test"
SECRET = "password"
```

## excludes

Type: `list[str | StringExpression] | None`

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## exit-on-error

Type: `bool | Flag | None`

Stops test execution if any error occurs when parsing
test data, importing libraries, and so on.

corresponds to the `--exitonerror` option of _robot_

## exit-on-failure

Type: `bool | Flag | None`

Stops test execution if any test fails.

corresponds to the `-X --exitonfailure` option of _robot_

## expand-keywords

Type: `list[str | NamePattern | TagPattern] | None`

Matching keywords will be automatically expanded in
the log file. Matching against keyword name or tags
work using same rules as with --removekeywords.

Examples:

```
--expandkeywords name:BuiltIn.Log
--expandkeywords tag:expand
```

corresponds to the `--expandkeywords name:<pattern>|tag:<pattern> *` option of _robot_

## extend-args

Type: `list[str] | None`

Append extra arguments to be passed to _robot_.

Examples:
```toml
extend-args = ["-t", "abc"]
```

## extend-env

Type: `dict[str, str | StringExpression] | None`

Append extra environment variables to be set before run.

Examples:
```toml
[extend-env]
EXTRA_VAR = "value"

```

## extend-excludes

Type: `list[str | StringExpression] | None`

Appends entries to the --exclude option.

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## extend-expand-keywords

Type: `list[str | NamePattern | TagPattern] | None`

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

## extend-flatten-keywords

Type: `list[str | Literal['for', 'while', 'iteration'] | NamePattern | TagPattern] | None`

Appends entries to the --flattenkeywords option.

Flattens matching keywords in the generated log file.
Matching keywords get all log messages from their
child keywords and children are discarded otherwise.

**for:** flatten FOR loops fully

**while:** flatten WHILE loops fully

**iteration:** flatten FOR/WHILE loop iterations

**foritem:** deprecated alias for `iteration`

**name:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords name:<pattern>`

**tag:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords tag:<pattern>`

corresponds to the `--flattenkeywords for|while|iteration|name:<pattern>|tag:<pattern> *` option of _robot_

## extend-includes

Type: `list[str | StringExpression] | None`

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

## extend-languages

Type: `list[str | StringExpression] | None`

Appends entries to the --language option.

Activate localization. `lang` can be a name or a code
of a built-in language, or a path or a module name of
a custom language file.

corresponds to the `--language lang *` option of _rebot_

## extend-listeners

Type: `dict[str, list[str | StringExpression]] | None`

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

## extend-metadata

Type: `dict[str, str | StringExpression] | None`

Appends entries to the --metadata option.

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## extend-parse-include

Type: `list[str | StringExpression] | None`

Appends entries to the --parseinclude option.

Parse only files matching `pattern`. It can be:
- a file name or pattern like `example.robot` or
`*.robot` to parse all files matching that name,
- a file path like `path/to/example.robot`, or
- a directory path like `path/to/example` to parse
all files in that directory, recursively.

corresponds to the `-I --parseinclude pattern *` option of _robot_

## extend-parsers

Type: `dict[str, list[str | StringExpression]] | None`

Appends entries to the --parser option.

Custom parser class or module. Parser classes accept
arguments the same way as with --listener.

corresponds to the `--parser parser *` option of _rebot_

## extend-paths

Type: `str | list[str] | None`

Append extra entries to the paths argument.

Examples:
```toml
extend-paths = ["tests"]
```

## extend-pre-rebot-modifiers

Type: `dict[str, list[str | StringExpression]] | None`

Appends entries to the --prerebotmodifier option.

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## extend-pre-run-modifiers

Type: `dict[str, list[str | StringExpression]] | None`

Appends entries to the --prerunmodifier option.

Class to programmatically modify the suite
structure before execution. Accepts arguments the
same way as with --listener.

corresponds to the `--prerunmodifier modifier *` option of _rebot_

## extend-profiles

Type: `dict[str, RobotProfile] | None`

Extra execution profiles.

## extend-python-path

Type: `list[str | StringExpression] | None`

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

## extend-remove-keywords

Type: `list[str | Literal['all', 'passed', 'for', 'wuks'] | NamePattern | TagPattern] | None`

Appends entries to the --removekeywords option.

Remove keyword data from the generated log file.
Keywords containing warnings are not removed except
in the `all` mode.

**all:** remove data from all keywords

**passed:** remove data only from keywords in passed
test cases and suites

**for:** remove passed iterations from for loops

**while:** remove passed iterations from while loops

**wuks:** remove all but the last failing keyword
inside `BuiltIn.Wait Until Keyword Succeeds`

**name:\<pattern>:** remove data from keywords that match
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



**tag:\<pattern>:** remove data from keywords that match
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

## extend-set-tag

Type: `list[str | StringExpression] | None`

Appends entries to the --settag option.

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## extend-skip

Type: `list[str | StringExpression] | None`

Appends entries to the --skip option.

Tests having given tag will be skipped. Tag can be
a pattern.

corresponds to the `--skip tag *` option of _rebot_

## extend-skip-on-failure

Type: `list[str | StringExpression] | None`

Appends entries to the --skiponfailure option.

Tests having given tag will be skipped if they fail.
Tag can be a pattern

corresponds to the `--skiponfailure tag *` option of _rebot_

## extend-suites

Type: `list[str | StringExpression] | None`

Appends entries to the --suite option.

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## extend-tag-doc

Type: `dict[str, str | StringExpression] | None`

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

## extend-tag-stat-combine

Type: `list[str | dict[str, str]] | None`

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

## extend-tag-stat-exclude

Type: `list[str | StringExpression] | None`

Appends entries to the --tagstatexclude option.

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## extend-tag-stat-include

Type: `list[str | StringExpression] | None`

Appends entries to the --tagstatinclude option.

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## extend-tag-stat-link

Type: `dict[str, str | StringExpression] | None`

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

## extend-tasks

Type: `list[str | StringExpression] | None`

Appends entries to the --task option.

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## extend-tests

Type: `list[str | StringExpression] | None`

Appends entries to the --test option.

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## extend-variable-files

Type: `list[str | StringExpression] | None`

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

## extend-variables

Type: `dict[str, str | StringExpression] | None`

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

## extensions

Type: `str | StringExpression | None`

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

## flatten-keywords

Type: `list[str | Literal['for', 'while', 'iteration'] | NamePattern | TagPattern] | None`

Flattens matching keywords in the generated log file.
Matching keywords get all log messages from their
child keywords and children are discarded otherwise.

**for:** flatten FOR loops fully

**while:** flatten WHILE loops fully

**iteration:** flatten FOR/WHILE loop iterations

**foritem:** deprecated alias for `iteration`

**name:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords name:<pattern>`

**tag:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords tag:<pattern>`

corresponds to the `--flattenkeywords for|while|iteration|name:<pattern>|tag:<pattern> *` option of _robot_

## includes

Type: `list[str | StringExpression] | None`

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

## languages

Type: `list[str | StringExpression] | None`

Activate localization. `lang` can be a name or a code
of a built-in language, or a path or a module name of
a custom language file.

corresponds to the `--language lang *` option of _robot_

## legacy-output

Type: `bool | Flag | None`

Create XML output file in format compatible with
Robot Framework 6.x and earlier.

corresponds to the `--legacyoutput` option of _robot_

## libdoc

Type: `LibDocProfile | None`

Options to be passed to _libdoc_.

## libdoc.doc-format

Type: `Literal['ROBOT', 'HTML', 'TEXT', 'REST'] | None`

Specifies the source documentation format. Possible
values are Robot Framework's documentation format,
HTML, plain text, and reStructuredText. The default
value can be specified in library source code and
the initial default value is ROBOT.

corresponds to the `-F --docformat ROBOT|HTML|TEXT|REST` option of _libdoc_

## libdoc.extend-python-path

Type: `list[str | StringExpression] | None`

Appends entries to the --pythonpath option.

Additional locations where to search for libraries
and resources.

corresponds to the `-P --pythonpath path *` option of _libdoc_

## libdoc.format

Type: `Literal['HTML', 'XML', 'JSON', 'LIBSPEC'] | None`

Specifies whether to generate an HTML output for
humans or a machine readable spec file in XML or JSON
format. The LIBSPEC format means XML spec with
documentations converted to HTML. The default format
is got from the output file extension.

corresponds to the `-f --format HTML|XML|JSON|LIBSPEC` option of _libdoc_

## libdoc.name

Type: `str | StringExpression | None`

Sets the name of the documented library or resource.

corresponds to the `-n --name name` option of _libdoc_

## libdoc.python-path

Type: `list[str | StringExpression] | None`

Additional locations where to search for libraries
and resources.

corresponds to the `-P --pythonpath path *` option of _libdoc_

## libdoc.quiet

Type: `bool | Flag | None`

Do not print the path of the generated output file
to the console. New in RF 4.0.

corresponds to the `--quiet` option of _libdoc_

## libdoc.spec-doc-format

Type: `Literal['RAW', 'HTML'] | None`

Specifies the documentation format used with XML and
JSON spec files. RAW means preserving the original
documentation format and HTML means converting
documentation to HTML. The default is RAW with XML
spec files and HTML with JSON specs and when using
the special LIBSPEC format. New in RF 4.0.

corresponds to the `-s --specdocformat RAW|HTML` option of _libdoc_

## libdoc.theme

Type: `Literal['DARK', 'LIGHT', 'NONE'] | None`

Use dark or light HTML theme. If this option is not
used, or the value is NONE, the theme is selected
based on the browser color scheme. New in RF 6.0.

corresponds to the `--theme DARK|LIGHT|NONE` option of _libdoc_

## listeners

Type: `dict[str, list[str | StringExpression]] | None`

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

## log

Type: `str | StringExpression | None`

HTML log file. Can be disabled by giving a special
value `NONE`. Default: log.html

Examples:

```
`--log mylog.html`, `-l NONE`
```

corresponds to the `-l --log file` option of _robot_

## log-level

Type: `str | StringExpression | None`

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

## log-title

Type: `str | StringExpression | None`

Title for the generated log file. The default title
is `<SuiteName> Log`.

corresponds to the `--logtitle title` option of _robot_

## max-assign-length

Type: `int | None`

Maximum number of characters to show in log
when variables are assigned. Zero or negative values
can be used to avoid showing assigned values at all.
Default is 200.

corresponds to the `--maxassignlength characters` option of _robot_

## max-error-lines

Type: `int | None`

Maximum number of error message lines to show in
report when tests fail. Default is 40, minimum is 10
and `NONE` can be used to show the full message.

corresponds to the `--maxerrorlines lines` option of _robot_

## metadata

Type: `dict[str, str | StringExpression] | None`

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## name

Type: `str | StringExpression | None`

Set the name of the top level suite. By default the
name is created based on the executed file or
directory.

corresponds to the `-N --name name` option of _robot_

## no-status-rc

Type: `bool | Flag | None`

Sets the return code to zero regardless of failures
in test cases. Error codes are returned normally.

corresponds to the `--nostatusrc` option of _robot_

## output

Type: `str | StringExpression | None`

XML output file. Given path, similarly as paths given
to --log, --report, --xunit, and --debugfile, is
relative to --outputdir unless given as an absolute
path. Other output files are created based on XML
output files after the test execution and XML outputs
can also be further processed with Rebot tool. Can be
disabled by giving a special value `NONE`.

**Default:** output.xml

corresponds to the `-o --output file` option of _robot_

## output-dir

Type: `str | StringExpression | None`

Where to create output files. The default is the
directory where tests are run from and the given path
is considered relative to that unless it is absolute.

corresponds to the `-d --outputdir dir` option of _robot_

## parse-include

Type: `list[str | StringExpression] | None`

Parse only files matching `pattern`. It can be:
- a file name or pattern like `example.robot` or
`*.robot` to parse all files matching that name,
- a file path like `path/to/example.robot`, or
- a directory path like `path/to/example` to parse
all files in that directory, recursively.

corresponds to the `-I --parseinclude pattern *` option of _robot_

## parsers

Type: `dict[str, list[str | StringExpression]] | None`

Custom parser class or module. Parser classes accept
arguments the same way as with --listener.

corresponds to the `--parser parser *` option of _robot_

## paths

Type: `str | list[str] | None`

Specifies the paths where robot/robotcode should discover tests.
If no paths are given at the command line this value is used.

Examples:
```toml
paths = ["tests"]
```

Corresponds to the `paths` argument of __robot__.

## pre-rebot-modifiers

Type: `dict[str, list[str | StringExpression]] | None`

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## pre-run-modifiers

Type: `dict[str, list[str | StringExpression]] | None`

Class to programmatically modify the suite
structure before execution. Accepts arguments the
same way as with --listener.

corresponds to the `--prerunmodifier modifier *` option of _robot_

## profiles

Type: `dict[str, RobotProfile] | None`

Execution profiles.

## python-path

Type: `list[str | StringExpression] | None`

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

## quiet

Type: `bool | Flag | None`

Shortcut for `--console quiet`.

corresponds to the `--quiet` option of _robot_

## randomize

Type: `str | Literal['all', 'suites', 'tests', 'none'] | None`

Randomizes the test execution order.

**all:** randomizes both suites and tests

**suites:** randomizes suites

**tests:** randomizes tests

**none:** no randomization (default)
Use syntax `VALUE:SEED` to give a custom random seed.
The seed must be an integer.

Examples:

```
--randomize all
--randomize tests:1234
```

corresponds to the `--randomize all|suites|tests|none` option of _robot_

## re-run-failed

Type: `str | StringExpression | None`

Select failed tests from an earlier output file to be
re-executed. Equivalent to selecting same tests
individually using --test.

corresponds to the `-R --rerunfailed output` option of _robot_

## re-run-failed-suites

Type: `str | StringExpression | None`

Select failed suites from an earlier output
file to be re-executed.

corresponds to the `-S --rerunfailedsuites output` option of _robot_

## rebot

Type: `RebotProfile | None`

Options to be passed to _rebot_.

## rebot.console-colors

Type: `Literal['auto', 'on', 'ansi', 'off'] | None`

Use colors on console output or not.

**auto:** use colors when output not redirected (default)

**on:** always use colors

**ansi:** like `on` but use ANSI colors also on Windows

**off:** disable colors altogether

corresponds to the `-C --consolecolors auto|on|ansi|off` option of _robot_

## rebot.console-links

Type: `Literal['auto', 'off'] | None`

Control making paths to results files hyperlinks.

**auto:** use links when colors are enabled (default)

**off:** disable links unconditionally

corresponds to the `--consolelinks auto|off` option of _robot_

## rebot.doc

Type: `str | StringExpression | None`

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

## rebot.end-time

Type: `str | StringExpression | None`

Same as --starttime but for end time. If both options
are used, elapsed time of the suite is calculated
based on them. For combined suites, it is otherwise
calculated by adding elapsed times of the combined
suites together.

corresponds to the `--endtime timestamp` option of _rebot_

## rebot.excludes

Type: `list[str | StringExpression] | None`

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## rebot.expand-keywords

Type: `list[str | NamePattern | TagPattern] | None`

Matching keywords will be automatically expanded in
the log file. Matching against keyword name or tags
work using same rules as with --removekeywords.

Examples:

```
--expandkeywords name:BuiltIn.Log
--expandkeywords tag:expand
```

corresponds to the `--expandkeywords name:<pattern>|tag:<pattern> *` option of _robot_

## rebot.extend-excludes

Type: `list[str | StringExpression] | None`

Appends entries to the --exclude option.

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## rebot.extend-expand-keywords

Type: `list[str | NamePattern | TagPattern] | None`

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

## rebot.extend-flatten-keywords

Type: `list[str | Literal['for', 'while', 'iteration'] | NamePattern | TagPattern] | None`

Appends entries to the --flattenkeywords option.

Flattens matching keywords in the generated log file.
Matching keywords get all log messages from their
child keywords and children are discarded otherwise.

**for:** flatten FOR loops fully

**while:** flatten WHILE loops fully

**iteration:** flatten FOR/WHILE loop iterations

**foritem:** deprecated alias for `iteration`

**name:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords name:<pattern>`

**tag:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords tag:<pattern>`

corresponds to the `--flattenkeywords for|while|iteration|name:<pattern>|tag:<pattern> *` option of _robot_

## rebot.extend-includes

Type: `list[str | StringExpression] | None`

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

## rebot.extend-metadata

Type: `dict[str, str | StringExpression] | None`

Appends entries to the --metadata option.

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## rebot.extend-parse-include

Type: `list[str | StringExpression] | None`

Appends entries to the --parseinclude option.

Parse only files matching `pattern`. It can be:
- a file name or pattern like `example.robot` or
`*.robot` to parse all files matching that name,
- a file path like `path/to/example.robot`, or
- a directory path like `path/to/example` to parse
all files in that directory, recursively.

corresponds to the `-I --parseinclude pattern *` option of _robot_

## rebot.extend-pre-rebot-modifiers

Type: `dict[str, list[str | StringExpression]] | None`

Appends entries to the --prerebotmodifier option.

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## rebot.extend-python-path

Type: `list[str | StringExpression] | None`

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

## rebot.extend-remove-keywords

Type: `list[str | Literal['all', 'passed', 'for', 'wuks'] | NamePattern | TagPattern] | None`

Appends entries to the --removekeywords option.

Remove keyword data from the generated log file.
Keywords containing warnings are not removed except
in the `all` mode.

**all:** remove data from all keywords

**passed:** remove data only from keywords in passed
test cases and suites

**for:** remove passed iterations from for loops

**while:** remove passed iterations from while loops

**wuks:** remove all but the last failing keyword
inside `BuiltIn.Wait Until Keyword Succeeds`

**name:\<pattern>:** remove data from keywords that match
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



**tag:\<pattern>:** remove data from keywords that match
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

## rebot.extend-set-tag

Type: `list[str | StringExpression] | None`

Appends entries to the --settag option.

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## rebot.extend-suites

Type: `list[str | StringExpression] | None`

Appends entries to the --suite option.

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## rebot.extend-tag-doc

Type: `dict[str, str | StringExpression] | None`

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

## rebot.extend-tag-stat-combine

Type: `list[str | dict[str, str]] | None`

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

## rebot.extend-tag-stat-exclude

Type: `list[str | StringExpression] | None`

Appends entries to the --tagstatexclude option.

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## rebot.extend-tag-stat-include

Type: `list[str | StringExpression] | None`

Appends entries to the --tagstatinclude option.

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## rebot.extend-tag-stat-link

Type: `dict[str, str | StringExpression] | None`

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

## rebot.extend-tasks

Type: `list[str | StringExpression] | None`

Appends entries to the --task option.

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## rebot.extend-tests

Type: `list[str | StringExpression] | None`

Appends entries to the --test option.

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## rebot.flatten-keywords

Type: `list[str | Literal['for', 'while', 'iteration'] | NamePattern | TagPattern] | None`

Flattens matching keywords in the generated log file.
Matching keywords get all log messages from their
child keywords and children are discarded otherwise.

**for:** flatten FOR loops fully

**while:** flatten WHILE loops fully

**iteration:** flatten FOR/WHILE loop iterations

**foritem:** deprecated alias for `iteration`

**name:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords name:<pattern>`

**tag:\<pattern>:** flatten matched keywords using same
matching rules as with
`--removekeywords tag:<pattern>`

corresponds to the `--flattenkeywords for|while|iteration|name:<pattern>|tag:<pattern> *` option of _robot_

## rebot.includes

Type: `list[str | StringExpression] | None`

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

## rebot.legacy-output

Type: `bool | Flag | None`

Create XML output file in format compatible with
Robot Framework 6.x and earlier.

corresponds to the `--legacyoutput` option of _robot_

## rebot.log

Type: `str | StringExpression | None`

HTML log file. Can be disabled by giving a special
value `NONE`. Default: log.html

Examples:

```
`--log mylog.html`, `-l NONE`
```

corresponds to the `-l --log file` option of _robot_

## rebot.log-level

Type: `str | StringExpression | None`

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

## rebot.log-title

Type: `str | StringExpression | None`

Title for the generated log file. The default title
is `<SuiteName> Log`.

corresponds to the `--logtitle title` option of _robot_

## rebot.merge

Type: `bool | Flag | None`

When combining results, merge outputs together
instead of putting them under a new top level suite.

**Example:** rebot --merge orig.xml rerun.xml

corresponds to the `-R --merge` option of _rebot_

## rebot.metadata

Type: `dict[str, str | StringExpression] | None`

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## rebot.name

Type: `str | StringExpression | None`

Set the name of the top level suite. By default the
name is created based on the executed file or
directory.

corresponds to the `-N --name name` option of _robot_

## rebot.no-status-rc

Type: `bool | Flag | None`

Sets the return code to zero regardless of failures
in test cases. Error codes are returned normally.

corresponds to the `--nostatusrc` option of _robot_

## rebot.output

Type: `str | StringExpression | None`

XML output file. Not created unless this option is
specified. Given path, similarly as paths given to
--log, --report and --xunit, is relative to
--outputdir unless given as an absolute path.

corresponds to the `-o --output file` option of _rebot_

## rebot.output-dir

Type: `str | StringExpression | None`

Where to create output files. The default is the
directory where tests are run from and the given path
is considered relative to that unless it is absolute.

corresponds to the `-d --outputdir dir` option of _robot_

## rebot.parse-include

Type: `list[str | StringExpression] | None`

Parse only files matching `pattern`. It can be:
- a file name or pattern like `example.robot` or
`*.robot` to parse all files matching that name,
- a file path like `path/to/example.robot`, or
- a directory path like `path/to/example` to parse
all files in that directory, recursively.

corresponds to the `-I --parseinclude pattern *` option of _robot_

## rebot.pre-rebot-modifiers

Type: `dict[str, list[str | StringExpression]] | None`

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## rebot.process-empty-suite

Type: `bool | Flag | None`

Processes output also if the top level suite is
empty. Useful e.g. with --include/--exclude when it
is not an error that there are no matches.
Use --skiponfailure when starting execution instead.

corresponds to the `--processemptysuite` option of _rebot_

## rebot.python-path

Type: `list[str | StringExpression] | None`

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

## rebot.remove-keywords

Type: `list[str | Literal['all', 'passed', 'for', 'wuks'] | NamePattern | TagPattern] | None`

Remove keyword data from the generated log file.
Keywords containing warnings are not removed except
in the `all` mode.

**all:** remove data from all keywords

**passed:** remove data only from keywords in passed
test cases and suites

**for:** remove passed iterations from for loops

**while:** remove passed iterations from while loops

**wuks:** remove all but the last failing keyword
inside `BuiltIn.Wait Until Keyword Succeeds`

**name:\<pattern>:** remove data from keywords that match
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



**tag:\<pattern>:** remove data from keywords that match
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

## rebot.report

Type: `str | StringExpression | None`

HTML report file. Can be disabled with `NONE`
similarly as --log. Default: report.html

corresponds to the `-r --report file` option of _robot_

## rebot.report-background

Type: `str | StringExpression | None`

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

## rebot.report-title

Type: `str | StringExpression | None`

Title for the generated report file. The default
title is `<SuiteName> Report`.

corresponds to the `--reporttitle title` option of _robot_

## rebot.rpa

Type: `bool | Flag | None`

Turn on the generic automation mode. Mainly affects
terminology so that "test" is replaced with "task"
in logs and reports. By default the mode is got
from test/task header in data files.

corresponds to the `--rpa` option of _robot_

## rebot.set-tag

Type: `list[str | StringExpression] | None`

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## rebot.split-log

Type: `bool | Flag | None`

Split the log file into smaller pieces that open in
browsers transparently.

corresponds to the `--splitlog` option of _robot_

## rebot.start-time

Type: `str | StringExpression | None`

Set execution start time. Timestamp must be given in
format `2007-10-01 15:12:42.268` where all separators
are optional (e.g. `20071001151242268` is ok too) and
parts from milliseconds to hours can be omitted if
they are zero (e.g. `2007-10-01`). This can be used
to override start time of a single suite or to set
start time for a combined suite, which would
otherwise be `N/A`.

corresponds to the `--starttime timestamp` option of _rebot_

## rebot.suite-stat-level

Type: `int | None`

How many levels to show in `Statistics by Suite`
in log and report. By default all suite levels are
shown. Example:  --suitestatlevel 3

corresponds to the `--suitestatlevel level` option of _robot_

## rebot.suites

Type: `list[str | StringExpression] | None`

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## rebot.tag-doc

Type: `dict[str, str | StringExpression] | None`

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

## rebot.tag-stat-combine

Type: `list[str | dict[str, str]] | None`

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

## rebot.tag-stat-exclude

Type: `list[str | StringExpression] | None`

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## rebot.tag-stat-include

Type: `list[str | StringExpression] | None`

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## rebot.tag-stat-link

Type: `dict[str, str | StringExpression] | None`

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

## rebot.tasks

Type: `list[str | StringExpression] | None`

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## rebot.tests

Type: `list[str | StringExpression] | None`

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## rebot.timestamp-outputs

Type: `bool | Flag | None`

When this option is used, timestamp in a format
`YYYYMMDD-hhmmss` is added to all generated output
files between their basename and extension. For
example `-T -o output.xml -r report.html -l none`
creates files like `output-20070503-154410.xml` and
`report-20070503-154410.html`.

corresponds to the `-T --timestampoutputs` option of _robot_

## rebot.xunit

Type: `str | StringExpression | None`

xUnit compatible result file. Not created unless this
option is specified.

corresponds to the `-x --xunit file` option of _robot_

## remove-keywords

Type: `list[str | Literal['all', 'passed', 'for', 'wuks'] | NamePattern | TagPattern] | None`

Remove keyword data from the generated log file.
Keywords containing warnings are not removed except
in the `all` mode.

**all:** remove data from all keywords

**passed:** remove data only from keywords in passed
test cases and suites

**for:** remove passed iterations from for loops

**while:** remove passed iterations from while loops

**wuks:** remove all but the last failing keyword
inside `BuiltIn.Wait Until Keyword Succeeds`

**name:\<pattern>:** remove data from keywords that match
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



**tag:\<pattern>:** remove data from keywords that match
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

## report

Type: `str | StringExpression | None`

HTML report file. Can be disabled with `NONE`
similarly as --log. Default: report.html

corresponds to the `-r --report file` option of _robot_

## report-background

Type: `str | StringExpression | None`

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

## report-title

Type: `str | StringExpression | None`

Title for the generated report file. The default
title is `<SuiteName> Report`.

corresponds to the `--reporttitle title` option of _robot_

## rpa

Type: `bool | Flag | None`

Turn on the generic automation mode. Mainly affects
terminology so that "test" is replaced with "task"
in logs and reports. By default the mode is got
from test/task header in data files.

corresponds to the `--rpa` option of _robot_

## run-empty-suite

Type: `bool | Flag | None`

Executes suite even if it contains no tests. Useful
e.g. with --include/--exclude when it is not an error
that no test matches the condition.

corresponds to the `--runemptysuite` option of _robot_

## set-tag

Type: `list[str | StringExpression] | None`

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## skip

Type: `list[str | StringExpression] | None`

Tests having given tag will be skipped. Tag can be
a pattern.

corresponds to the `--skip tag *` option of _robot_

## skip-on-failure

Type: `list[str | StringExpression] | None`

Tests having given tag will be skipped if they fail.
Tag can be a pattern

corresponds to the `--skiponfailure tag *` option of _robot_

## skip-teardown-on-exit

Type: `bool | Flag | None`

Causes teardowns to be skipped if test execution is
stopped prematurely.

corresponds to the `--skipteardownonexit` option of _robot_

## split-log

Type: `bool | Flag | None`

Split the log file into smaller pieces that open in
browsers transparently.

corresponds to the `--splitlog` option of _robot_

## suite-stat-level

Type: `int | None`

How many levels to show in `Statistics by Suite`
in log and report. By default all suite levels are
shown. Example:  --suitestatlevel 3

corresponds to the `--suitestatlevel level` option of _robot_

## suites

Type: `list[str | StringExpression] | None`

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## tag-doc

Type: `dict[str, str | StringExpression] | None`

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

## tag-stat-combine

Type: `list[str | dict[str, str]] | None`

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

## tag-stat-exclude

Type: `list[str | StringExpression] | None`

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## tag-stat-include

Type: `list[str | StringExpression] | None`

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## tag-stat-link

Type: `dict[str, str | StringExpression] | None`

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

## tasks

Type: `list[str | StringExpression] | None`

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## testdoc

Type: `TestDocProfile | None`

Options to be passed to _testdoc_.

## testdoc.doc

Type: `str | StringExpression | None`

Override the documentation of the top level suite.

corresponds to the `-D --doc document` option of _testdoc_

## testdoc.excludes

Type: `list[str | StringExpression] | None`

Exclude tests by tags.

corresponds to the `-e --exclude tag *` option of _testdoc_

## testdoc.extend-excludes

Type: `list[str | StringExpression] | None`

Appends entries to the --exclude option.

Exclude tests by tags.

corresponds to the `-e --exclude tag *` option of _testdoc_

## testdoc.extend-includes

Type: `list[str | StringExpression] | None`

Appends entries to the --include option.

Include tests by tags.

corresponds to the `-i --include tag *` option of _testdoc_

## testdoc.extend-metadata

Type: `dict[str, str | StringExpression] | None`

Appends entries to the --metadata option.

Set/override metadata of the top level suite.

corresponds to the `-M --metadata name:value *` option of _testdoc_

## testdoc.extend-set-tag

Type: `list[str | StringExpression] | None`

Appends entries to the --settag option.

Set given tag(s) to all test cases.

corresponds to the `-G --settag tag *` option of _testdoc_

## testdoc.extend-suites

Type: `list[str | StringExpression] | None`

Appends entries to the --suite option.

Include suites by name.

corresponds to the `-s --suite name *` option of _testdoc_

## testdoc.extend-tests

Type: `list[str | StringExpression] | None`

Appends entries to the --test option.

Include tests by name.

corresponds to the `-t --test name *` option of _testdoc_

## testdoc.includes

Type: `list[str | StringExpression] | None`

Include tests by tags.

corresponds to the `-i --include tag *` option of _testdoc_

## testdoc.metadata

Type: `dict[str, str | StringExpression] | None`

Set/override metadata of the top level suite.

corresponds to the `-M --metadata name:value *` option of _testdoc_

## testdoc.name

Type: `str | StringExpression | None`

Override the name of the top level suite.

corresponds to the `-N --name name` option of _testdoc_

## testdoc.set-tag

Type: `list[str | StringExpression] | None`

Set given tag(s) to all test cases.

corresponds to the `-G --settag tag *` option of _testdoc_

## testdoc.suites

Type: `list[str | StringExpression] | None`

Include suites by name.

corresponds to the `-s --suite name *` option of _testdoc_

## testdoc.tests

Type: `list[str | StringExpression] | None`

Include tests by name.

corresponds to the `-t --test name *` option of _testdoc_

## testdoc.title

Type: `str | StringExpression | None`

Set the title of the generated documentation.
Underscores in the title are converted to spaces.
The default title is the name of the top level suite.

corresponds to the `-T --title title` option of _testdoc_

## tests

Type: `list[str | StringExpression] | None`

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## timestamp-outputs

Type: `bool | Flag | None`

When this option is used, timestamp in a format
`YYYYMMDD-hhmmss` is added to all generated output
files between their basename and extension. For
example `-T -o output.xml -r report.html -l none`
creates files like `output-20070503-154410.xml` and
`report-20070503-154410.html`.

corresponds to the `-T --timestampoutputs` option of _robot_

## tool

Type: `dict[str, Any] | None`

Tool configurations.

## tool.robotcode-analyze.cache

Type: `CacheConfig | None`

Defines the cache configuration.

## tool.robotcode-analyze.cache.cache-dir

Type: `str | None`

Path to the cache directory.

## tool.robotcode-analyze.cache.extend-ignore-arguments-for-library

Type: `list[str] | None`

Extend the ignore arguments for library settings.

## tool.robotcode-analyze.cache.extend-ignored-libraries

Type: `list[str] | None`

Extend the ignored libraries setting.

## tool.robotcode-analyze.cache.extend-ignored-variables

Type: `list[str] | None`

Extend the ignored variables setting.

## tool.robotcode-analyze.cache.ignore-arguments-for-library

Type: `list[str] | None`

Specifies a list of libraries for which arguments will be ignored during analysis.
This is usefull if you have library that gets variables from a python file as arguments that contains
complex data like big dictionaries or complex objects that **RobotCode** can't handle.
You can specify a glob pattern that matches the library name or the source file.

Examples:
- `**/mylibfolder/mylib.py`
- `MyLib`
- `mylib.subpackage.subpackage`

If you change this setting, you may need to run the command
`RobotCode: Clear Cache and Restart Language Servers`.

_Ensure your library functions correctly without arguments e.g. by defining default
values for all arguments._

## tool.robotcode-analyze.cache.ignored-libraries

Type: `list[str] | None`

Specifies the library names that should not be cached.
This is useful if you have a dynamic or hybrid library that has different keywords depending on
the arguments. You can specify a glob pattern that matches the library name or the source file.

Examples:
- `**/mylibfolder/mylib.py`
- `MyLib`
- `mylib.subpackage.subpackage`

For robot framework internal libraries, you have to specify the full module name like
`robot.libraries.Remote`.

## tool.robotcode-analyze.cache.ignored-variables

Type: `list[str] | None`

Specifies the variable files that should not be cached.
This is useful if you have a dynamic or hybrid variable files that has different variables
depending on the arguments. You can specify a glob pattern that matches the variable module
name or the source file.

Examples:
- `**/variables/myvars.py`
- `MyVariables`
- `myvars.subpackage.subpackage`

## tool.robotcode-analyze.exclude-patterns

Type: `list[str] | None`

Specifies glob patterns for excluding files and folders from analysing by the language server.

## tool.robotcode-analyze.extend-cache

Type: `CacheConfig | None`

Extend the cache configuration.

## tool.robotcode-analyze.extend-cache.cache-dir

Type: `str | None`

Path to the cache directory.

## tool.robotcode-analyze.extend-cache.extend-ignore-arguments-for-library

Type: `list[str] | None`

Extend the ignore arguments for library settings.

## tool.robotcode-analyze.extend-cache.extend-ignored-libraries

Type: `list[str] | None`

Extend the ignored libraries setting.

## tool.robotcode-analyze.extend-cache.extend-ignored-variables

Type: `list[str] | None`

Extend the ignored variables setting.

## tool.robotcode-analyze.extend-cache.ignore-arguments-for-library

Type: `list[str] | None`

Specifies a list of libraries for which arguments will be ignored during analysis.
This is usefull if you have library that gets variables from a python file as arguments that contains
complex data like big dictionaries or complex objects that **RobotCode** can't handle.
You can specify a glob pattern that matches the library name or the source file.

Examples:
- `**/mylibfolder/mylib.py`
- `MyLib`
- `mylib.subpackage.subpackage`

If you change this setting, you may need to run the command
`RobotCode: Clear Cache and Restart Language Servers`.

_Ensure your library functions correctly without arguments e.g. by defining default
values for all arguments._

## tool.robotcode-analyze.extend-cache.ignored-libraries

Type: `list[str] | None`

Specifies the library names that should not be cached.
This is useful if you have a dynamic or hybrid library that has different keywords depending on
the arguments. You can specify a glob pattern that matches the library name or the source file.

Examples:
- `**/mylibfolder/mylib.py`
- `MyLib`
- `mylib.subpackage.subpackage`

For robot framework internal libraries, you have to specify the full module name like
`robot.libraries.Remote`.

## tool.robotcode-analyze.extend-cache.ignored-variables

Type: `list[str] | None`

Specifies the variable files that should not be cached.
This is useful if you have a dynamic or hybrid variable files that has different variables
depending on the arguments. You can specify a glob pattern that matches the variable module
name or the source file.

Examples:
- `**/variables/myvars.py`
- `MyVariables`
- `myvars.subpackage.subpackage`

## tool.robotcode-analyze.extend-exclude-patterns

Type: `list[str] | None`

Extend the exclude patterns.

## tool.robotcode-analyze.extend-global-library-search-order

Type: `list[str] | None`

Extend the global library search order setting.

## tool.robotcode-analyze.extend-modifiers

Type: `ModifiersConfig | None`

Extends the modifiers for the analysis.

Examples:

```toml
[tool.robotcode-analyze.extend_modifiers]
ignore = ["VariableNotFound"]
extend-hint = ["KeywordNotFound"]
extend-information = ["MultipleKeywords"]
```

## tool.robotcode-analyze.extend-modifiers.error

Type: `list[str] | None`

Specifies the error codes to treat as errors.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
error = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.extend-error

Type: `list[str] | None`

Extend the error codes to treat as errors.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_error = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.extend-hint

Type: `list[str] | None`

Extend the error codes to treat as hint.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_hint = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.extend-ignore

Type: `list[str] | None`

Extend the error codes to ignore.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_ignore = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.extend-information

Type: `list[str] | None`

Extend the error codes to treat as information.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_information = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.extend-warning

Type: `list[str] | None`

Extend the error codes to treat as warnings.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_warning = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.hint

Type: `list[str] | None`

Specifies the error codes to treat as hint.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
hint = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.ignore

Type: `list[str] | None`

Specifies the error codes to ignore.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
ignore = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.information

Type: `list[str] | None`

Specifies the error codes to treat as information.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
information = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.extend-modifiers.warning

Type: `list[str] | None`

Specifies the error codes to treat as warning.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
warning = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.global-library-search-order

Type: `list[str] | None`

Specifies a global [search order](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#specifying-explicit-priority-between-libraries-and-resources)
for libraries and resources.
This is usefull when you have libraries containing keywords with the same name. **RobotCode** is unable to
analyze the library search order in a file specified with
[`Set Library Search Order`](https://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Library%20Search%20Order),
so you can define a global order here. Just make sure to call the `Set Library Search Order`
keyword somewhere in your robot file or internally in your library.

## tool.robotcode-analyze.modifiers

Type: `ModifiersConfig | None`

Defines the modifiers for the analysis.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
ignore = ["VariableNotFound"]
hint = ["KeywordNotFound"]
information = ["MultipleKeywords"]
```

## tool.robotcode-analyze.modifiers.error

Type: `list[str] | None`

Specifies the error codes to treat as errors.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
error = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.extend-error

Type: `list[str] | None`

Extend the error codes to treat as errors.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_error = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.extend-hint

Type: `list[str] | None`

Extend the error codes to treat as hint.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_hint = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.extend-ignore

Type: `list[str] | None`

Extend the error codes to ignore.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_ignore = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.extend-information

Type: `list[str] | None`

Extend the error codes to treat as information.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_information = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.extend-warning

Type: `list[str] | None`

Extend the error codes to treat as warnings.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
extend_warning = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.hint

Type: `list[str] | None`

Specifies the error codes to treat as hint.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
hint = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.ignore

Type: `list[str] | None`

Specifies the error codes to ignore.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
ignore = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.information

Type: `list[str] | None`

Specifies the error codes to treat as information.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
information = ["VariableNotFound", "multiple-keywords"]
```

## tool.robotcode-analyze.modifiers.warning

Type: `list[str] | None`

Specifies the error codes to treat as warning.

Examples:

```toml
[tool.robotcode-analyze.modifiers]
warning = ["VariableNotFound", "multiple-keywords"]
```

## variable-files

Type: `list[str | StringExpression] | None`

Python or YAML file file to read variables from.
Possible arguments to the variable file can be given
after the path using colon or semicolon as separator.

Examples:

```
--variablefile path/vars.yaml
--variablefile environment.py:testing
```

corresponds to the `-V --variablefile path *` option of _robot_

## variables

Type: `dict[str, str | StringExpression] | None`

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

## xunit

Type: `str | StringExpression | None`

xUnit compatible result file. Not created unless this
option is specified.

corresponds to the `-x --xunit file` option of _robot_


