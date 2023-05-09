## args

Type: typing.Optional[typing.List[str]]

Arguments to be passed to _robot_.

Examples:
```toml
args = ["-t", "abc"]
```

## console

Type: typing.Optional[typing.Literal['verbose', 'dotted', 'skipped', 'quiet', 'none']]

How to report execution on the console.
verbose:  report every suite and test (default)
dotted:   only show `.` for passed test, `s` for
skipped tests, and `F` for failed tests
quiet:    no output except for errors and warnings
none:     no output whatsoever

corresponds to the `--console type` option of _robot_

## console-colors

Type: typing.Optional[typing.Literal['auto', 'on', 'ansi', 'off']]

Use colors on console output or not.
auto: use colors when output not redirected (default)
on:   always use colors
ansi: like `on` but use ANSI colors also on Windows
off:  disable colors altogether

corresponds to the `-C --consolecolors auto|on|ansi|off` option of _robot_

## console-markers

Type: typing.Optional[typing.Literal['auto', 'on', 'off']]

Show markers on the console when top level
keywords in a test case end. Values have same
semantics as with --consolecolors.

corresponds to the `-K --consolemarkers auto|on|off` option of _robot_

## console-width

Type: typing.Optional[int]

Width of the console output. Default is 78.

corresponds to the `-W --consolewidth chars` option of _robot_

## debug-file

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Debug file written during execution. Not created
unless this option is specified.

corresponds to the `-b --debugfile file` option of _robot_

## default-profiles

Type: typing.Union[str, typing.List[str], NoneType]

Selects the Default profile if no profile is given at command line.

Examples:
```toml
default_profiles = "default"
```

```toml
default_profiles = ["default", "Firefox"]
```

## doc

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Shortcut for `--console dotted`.

corresponds to the `-. --dotted` option of _robot_

## dry-run

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Verifies test data and runs tests so that library
keywords are not executed.

corresponds to the `--dryrun` option of _robot_

## env

Type: typing.Optional[typing.Dict[str, str]]

Define environment variables to be set before running tests.

Examples:
```toml
[env]
TEST_VAR = "test"
SECRET = "password"
```

## excludes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## exit-on-error

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Stops test execution if any error occurs when parsing
test data, importing libraries, and so on.

corresponds to the `--exitonerror` option of _robot_

## exit-on-failure

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Stops test execution if any test fails.

corresponds to the `-X --exitonfailure` option of _robot_

## expand-keywords

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

Matching keywords will be automatically expanded in
the log file. Matching against keyword name or tags
work using same rules as with --removekeywords.

Examples:

```
--expandkeywords name:BuiltIn.Log
--expandkeywords tag:expand
```

corresponds to the `--expandkeywords name:<pattern>|tag:<pattern> *` option of _robot_

## extensions

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

## extra-args

Type: typing.Optional[typing.List[str]]

Append extra arguments to be passed to _robot_.

## extra-env

Type: typing.Optional[typing.Dict[str, str]]

Append extra environment variables to be set before tests.

## extra-excludes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --exclude option.

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## extra-expand-keywords

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## extra-flatten-keywords

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['for', 'while', 'iteration'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## extra-includes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## extra-languages

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --language option.

Activate localization. `lang` can be a name or a code
of a built-in language, or a path or a module name of
a custom language file.

corresponds to the `--language lang *` option of _rebot_

## extra-listeners

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

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

## extra-metadata

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --metadata option.

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## extra-parsers

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --parser option.

Custom parser class or module. Parser classes accept
arguments the same way as with --listener.

corresponds to the `--parser parser *` option of _rebot_

## extra-paths

Type: typing.Union[str, typing.List[str], NoneType]

Append extra entries to the paths argument.

Examples:
```toml
paths = ["tests"]
```

## extra-pre-rebot-modifiers

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

Appends entries to the --prerebotmodifier option.

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## extra-pre-run-modifiers

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

Appends entries to the --prerunmodifier option.

Class to programmatically modify the suite
structure before execution. Accepts arguments the
same way as with --listener.

corresponds to the `--prerunmodifier modifier *` option of _rebot_

## extra-profiles

Type: typing.Optional[typing.Dict[str, robotcode.robot.config.model.RobotProfile]]

Extra execution profiles.

## extra-python-path

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## extra-remove-keywords

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['all', 'passed', 'for', 'wuks'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## extra-set-tag

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --settag option.

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## extra-skip

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --skip option.

Tests having given tag will be skipped. Tag can be
a pattern.

corresponds to the `--skip tag *` option of _rebot_

## extra-skip-on-failure

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --skiponfailure option.

Tests having given tag will be skipped if they fail.
Tag can be a pattern

corresponds to the `--skiponfailure tag *` option of _rebot_

## extra-suites

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --suite option.

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## extra-tag-doc

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## extra-tag-stat-combine

Type: typing.Optional[typing.List[typing.Union[str, typing.Dict[str, str]]]]

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

## extra-tag-stat-exclude

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --tagstatexclude option.

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## extra-tag-stat-include

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --tagstatinclude option.

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## extra-tag-stat-link

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## extra-tasks

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --task option.

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## extra-tests

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --test option.

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## extra-variable-files

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## extra-variables

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --variable option.

Set variables in the test data. Only scalar
variables with string value are supported and name is
given without `${}`. See --variablefile for a more
powerful variable setting mechanism.

Examples:

```
--variable str:Hello       =>  ${str} = `Hello`
-v hi:Hi_World -E space:_  =>  ${hi} = `Hi World`
-v x: -v y:42              =>  ${x} = ``, ${y} = `42`
```

corresponds to the `-v --variable name:value *` option of _rebot_

## flatten-keywords

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['for', 'while', 'iteration'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## includes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Activate localization. `lang` can be a name or a code
of a built-in language, or a path or a module name of
a custom language file.

corresponds to the `--language lang *` option of _robot_

## libdoc

Type: typing.Optional[robotcode.robot.config.model.LibDocProfile]

Options to be passed to _libdoc_.

## libdoc.doc-format

Type: typing.Optional[typing.Literal['ROBOT', 'HTML', 'TEXT', 'REST']]

Specifies the source documentation format. Possible
values are Robot Framework's documentation format,
HTML, plain text, and reStructuredText. The default
value can be specified in library source code and
the initial default value is ROBOT.

corresponds to the `-F --docformat ROBOT|HTML|TEXT|REST` option of _libdoc_

## libdoc.extra-python-path

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --pythonpath option.

Additional locations where to search for libraries
and resources.

corresponds to the `-P --pythonpath path *` option of _libdoc_

## libdoc.format

Type: typing.Optional[typing.Literal['HTML', 'XML', 'JSON', 'LIBSPEC']]

Specifies whether to generate an HTML output for
humans or a machine readable spec file in XML or JSON
format. The LIBSPEC format means XML spec with
documentations converted to HTML. The default format
is got from the output file extension.

corresponds to the `-f --format HTML|XML|JSON|LIBSPEC` option of _libdoc_

## libdoc.name

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Sets the name of the documented library or resource.

corresponds to the `-n --name name` option of _libdoc_

## libdoc.python-path

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Additional locations where to search for libraries
and resources.

corresponds to the `-P --pythonpath path *` option of _libdoc_

## libdoc.quiet

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Do not print the path of the generated output file
to the console. New in RF 4.0.

corresponds to the `--quiet` option of _libdoc_

## libdoc.spec-doc-format

Type: typing.Optional[typing.Literal['RAW', 'HTML']]

Specifies the documentation format used with XML and
JSON spec files. RAW means preserving the original
documentation format and HTML means converting
documentation to HTML. The default is RAW with XML
spec files and HTML with JSON specs and when using
the special LIBSPEC format. New in RF 4.0.

corresponds to the `-s --specdocformat RAW|HTML` option of _libdoc_

## libdoc.theme

Type: typing.Optional[typing.Literal['DARK', 'LIGHT', 'NONE']]

Use dark or light HTML theme. If this option is not
used, or the value is NONE, the theme is selected
based on the browser color scheme. New in RF 6.0.

corresponds to the `--theme DARK|LIGHT|NONE` option of _libdoc_

## listeners

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

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

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

HTML log file. Can be disabled by giving a special
value `NONE`. Default: log.html

Examples:

```
`--log mylog.html`, `-l NONE`
```

corresponds to the `-l --log file` option of _robot_

## log-level

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Title for the generated log file. The default title
is `<SuiteName> Log`.

corresponds to the `--logtitle title` option of _robot_

## max-assign-length

Type: typing.Optional[int]

Maximum number of characters to show in log
when variables are assigned. Zero or negative values
can be used to avoid showing assigned values at all.
Default is 200.

corresponds to the `--maxassignlength characters` option of _robot_

## max-error-lines

Type: typing.Optional[int]

Maximum number of error message lines to show in
report when tests fail. Default is 40, minimum is 10
and `NONE` can be used to show the full message.

corresponds to the `--maxerrorlines lines` option of _robot_

## metadata

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## name

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Set the name of the top level suite. By default the
name is created based on the executed file or
directory.

corresponds to the `-N --name name` option of _robot_

## no-status-rc

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Sets the return code to zero regardless of failures
in test cases. Error codes are returned normally.

corresponds to the `--nostatusrc` option of _robot_

## output

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

XML output file. Given path, similarly as paths given
to --log, --report, --xunit, and --debugfile, is
relative to --outputdir unless given as an absolute
path. Other output files are created based on XML
output files after the test execution and XML outputs
can also be further processed with Rebot tool. Can be
disabled by giving a special value `NONE`.
Default: output.xml

corresponds to the `-o --output file` option of _robot_

## output-dir

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Where to create output files. The default is the
directory where tests are run from and the given path
is considered relative to that unless it is absolute.

corresponds to the `-d --outputdir dir` option of _robot_

## parsers

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Custom parser class or module. Parser classes accept
arguments the same way as with --listener.

corresponds to the `--parser parser *` option of _robot_

## paths

Type: typing.Union[str, typing.List[str], NoneType]

Specifies the paths where robot/robotcode should discover tests.
If no paths are given at the command line this value is used.

Examples:
```toml
paths = ["tests"]
```

Corresponds to the `paths` argument of __robot__.

## pre-rebot-modifiers

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## pre-run-modifiers

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

Class to programmatically modify the suite
structure before execution. Accepts arguments the
same way as with --listener.

corresponds to the `--prerunmodifier modifier *` option of _robot_

## profiles

Type: typing.Optional[typing.Dict[str, robotcode.robot.config.model.RobotProfile]]

Execution profiles.

## python-path

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Shortcut for `--console quiet`.

corresponds to the `--quiet` option of _robot_

## randomize

Type: typing.Union[str, typing.Literal['all', 'suites', 'tests', 'none'], NoneType]

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

## re-run-failed

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Select failed tests from an earlier output file to be
re-executed. Equivalent to selecting same tests
individually using --test.

corresponds to the `-R --rerunfailed output` option of _robot_

## re-run-failed-suites

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Select failed suites from an earlier output
file to be re-executed.

corresponds to the `-S --rerunfailedsuites output` option of _robot_

## rebot

Type: typing.Optional[robotcode.robot.config.model.RebotProfile]

Options to be passed to _rebot_.

## rebot.console-colors

Type: typing.Optional[typing.Literal['auto', 'on', 'ansi', 'off']]

Use colors on console output or not.
auto: use colors when output not redirected (default)
on:   always use colors
ansi: like `on` but use ANSI colors also on Windows
off:  disable colors altogether

corresponds to the `-C --consolecolors auto|on|ansi|off` option of _robot_

## rebot.doc

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Same as --starttime but for end time. If both options
are used, elapsed time of the suite is calculated
based on them. For combined suites, it is otherwise
calculated by adding elapsed times of the combined
suites together.

corresponds to the `--endtime timestamp` option of _rebot_

## rebot.excludes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## rebot.expand-keywords

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

Matching keywords will be automatically expanded in
the log file. Matching against keyword name or tags
work using same rules as with --removekeywords.

Examples:

```
--expandkeywords name:BuiltIn.Log
--expandkeywords tag:expand
```

corresponds to the `--expandkeywords name:<pattern>|tag:<pattern> *` option of _robot_

## rebot.extra-excludes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --exclude option.

Select test cases not to run by tag. These tests are
not run even if included with --include. Tags are
matched using same rules as with --include.

corresponds to the `-e --exclude tag *` option of _robot_

## rebot.extra-expand-keywords

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## rebot.extra-flatten-keywords

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['for', 'while', 'iteration'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## rebot.extra-includes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## rebot.extra-metadata

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --metadata option.

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## rebot.extra-pre-rebot-modifiers

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

Appends entries to the --prerebotmodifier option.

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## rebot.extra-python-path

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## rebot.extra-remove-keywords

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['all', 'passed', 'for', 'wuks'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## rebot.extra-set-tag

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --settag option.

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## rebot.extra-suites

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --suite option.

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## rebot.extra-tag-doc

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## rebot.extra-tag-stat-combine

Type: typing.Optional[typing.List[typing.Union[str, typing.Dict[str, str]]]]

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

## rebot.extra-tag-stat-exclude

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --tagstatexclude option.

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## rebot.extra-tag-stat-include

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --tagstatinclude option.

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## rebot.extra-tag-stat-link

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## rebot.extra-tasks

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --task option.

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## rebot.extra-tests

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --test option.

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## rebot.flatten-keywords

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['for', 'while', 'iteration'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## rebot.includes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

## rebot.log

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

HTML log file. Can be disabled by giving a special
value `NONE`. Default: log.html

Examples:

```
`--log mylog.html`, `-l NONE`
```

corresponds to the `-l --log file` option of _robot_

## rebot.log-level

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Title for the generated log file. The default title
is `<SuiteName> Log`.

corresponds to the `--logtitle title` option of _robot_

## rebot.merge

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

When combining results, merge outputs together
instead of putting them under a new top level suite.
Example: rebot --merge orig.xml rerun.xml

corresponds to the `-R --merge` option of _rebot_

## rebot.metadata

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Set metadata of the top level suite. Value can
contain formatting and be read from a file similarly
as --doc. Example: --metadata Version:1.2

corresponds to the `-M --metadata name:value *` option of _robot_

## rebot.name

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Set the name of the top level suite. By default the
name is created based on the executed file or
directory.

corresponds to the `-N --name name` option of _robot_

## rebot.no-status-rc

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Sets the return code to zero regardless of failures
in test cases. Error codes are returned normally.

corresponds to the `--nostatusrc` option of _robot_

## rebot.output

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

XML output file. Not created unless this option is
specified. Given path, similarly as paths given to
--log, --report and --xunit, is relative to
--outputdir unless given as an absolute path.

corresponds to the `-o --output file` option of _rebot_

## rebot.output-dir

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Where to create output files. The default is the
directory where tests are run from and the given path
is considered relative to that unless it is absolute.

corresponds to the `-d --outputdir dir` option of _robot_

## rebot.pre-rebot-modifiers

Type: typing.Optional[typing.Dict[str, typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]]

Class to programmatically modify the result
model before creating reports and logs. Accepts
arguments the same way as with --listener.

corresponds to the `--prerebotmodifier modifier *` option of _robot_

## rebot.process-empty-suite

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Processes output also if the top level suite is
empty. Useful e.g. with --include/--exclude when it
is not an error that there are no matches.
Use --skiponfailure when starting execution instead.

corresponds to the `--processemptysuite` option of _rebot_

## rebot.python-path

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['all', 'passed', 'for', 'wuks'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## rebot.report

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

HTML report file. Can be disabled with `NONE`
similarly as --log. Default: report.html

corresponds to the `-r --report file` option of _robot_

## rebot.report-background

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Title for the generated report file. The default
title is `<SuiteName> Report`.

corresponds to the `--reporttitle title` option of _robot_

## rebot.rpa

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Turn on the generic automation mode. Mainly affects
terminology so that "test" is replaced with "task"
in logs and reports. By default the mode is got
from test/task header in data files.

corresponds to the `--rpa` option of _robot_

## rebot.set-tag

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## rebot.split-log

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Split the log file into smaller pieces that open in
browsers transparently.

corresponds to the `--splitlog` option of _robot_

## rebot.start-time

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

Type: typing.Optional[int]

How many levels to show in `Statistics by Suite`
in log and report. By default all suite levels are
shown. Example:  --suitestatlevel 3

corresponds to the `--suitestatlevel level` option of _robot_

## rebot.suites

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## rebot.tag-doc

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Optional[typing.List[typing.Union[str, typing.Dict[str, str]]]]

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

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## rebot.tag-stat-include

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## rebot.tag-stat-link

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## rebot.tests

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## rebot.timestamp-outputs

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

When this option is used, timestamp in a format
`YYYYMMDD-hhmmss` is added to all generated output
files between their basename and extension. For
example `-T -o output.xml -r report.html -l none`
creates files like `output-20070503-154410.xml` and
`report-20070503-154410.html`.

corresponds to the `-T --timestampoutputs` option of _robot_

## rebot.xunit

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

xUnit compatible result file. Not created unless this
option is specified.

corresponds to the `-x --xunit file` option of _robot_

## remove-keywords

Type: typing.Optional[typing.List[typing.Union[str, typing.Literal['all', 'passed', 'for', 'wuks'], robotcode.robot.config.model.NamePattern, robotcode.robot.config.model.TagPattern]]]

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

## report

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

HTML report file. Can be disabled with `NONE`
similarly as --log. Default: report.html

corresponds to the `-r --report file` option of _robot_

## report-background

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

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

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Title for the generated report file. The default
title is `<SuiteName> Report`.

corresponds to the `--reporttitle title` option of _robot_

## rpa

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Turn on the generic automation mode. Mainly affects
terminology so that "test" is replaced with "task"
in logs and reports. By default the mode is got
from test/task header in data files.

corresponds to the `--rpa` option of _robot_

## run-empty-suite

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Executes suite even if it contains no tests. Useful
e.g. with --include/--exclude when it is not an error
that no test matches the condition.

corresponds to the `--runemptysuite` option of _robot_

## set-tag

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Sets given tag(s) to all executed tests.

corresponds to the `-G --settag tag *` option of _robot_

## skip

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Tests having given tag will be skipped. Tag can be
a pattern.

corresponds to the `--skip tag *` option of _robot_

## skip-on-failure

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Tests having given tag will be skipped if they fail.
Tag can be a pattern

corresponds to the `--skiponfailure tag *` option of _robot_

## skip-teardown-on-exit

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Causes teardowns to be skipped if test execution is
stopped prematurely.

corresponds to the `--skipteardownonexit` option of _robot_

## split-log

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

Split the log file into smaller pieces that open in
browsers transparently.

corresponds to the `--splitlog` option of _robot_

## suite-stat-level

Type: typing.Optional[int]

How many levels to show in `Statistics by Suite`
in log and report. By default all suite levels are
shown. Example:  --suitestatlevel 3

corresponds to the `--suitestatlevel level` option of _robot_

## suites

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Select suites by name. When this option is used with
--test, --include or --exclude, only tests in
matching suites and also matching other filtering
criteria are selected. Name can be a simple pattern
similarly as with --test and it can contain parent
name separated with a dot. For example, `-s X.Y`
selects suite `Y` only if its parent is `X`.

corresponds to the `-s --suite name *` option of _robot_

## tag-doc

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Optional[typing.List[typing.Union[str, typing.Dict[str, str]]]]

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

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Exclude matching tags from `Statistics by Tag`.
This option can be used with --tagstatinclude
similarly as --exclude is used with --include.

corresponds to the `--tagstatexclude tag *` option of _robot_

## tag-stat-include

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Include only matching tags in `Statistics by Tag`
in log and report. By default all tags are shown.
Given tag can be a pattern like with --include.

corresponds to the `--tagstatinclude tag *` option of _robot_

## tag-stat-link

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Alias to --test. Especially applicable with --rpa.

corresponds to the `--task name *` option of _robot_

## testdoc

Type: typing.Optional[robotcode.robot.config.model.TestDocProfile]

Options to be passed to _testdoc_.

## testdoc.doc

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Override the documentation of the top level suite.

corresponds to the `-D --doc document` option of _testdoc_

## testdoc.excludes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Exclude tests by tags.

corresponds to the `-e --exclude tag *` option of _testdoc_

## testdoc.extra-excludes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --exclude option.

Exclude tests by tags.

corresponds to the `-e --exclude tag *` option of _testdoc_

## testdoc.extra-includes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --include option.

Include tests by tags.

corresponds to the `-i --include tag *` option of _testdoc_

## testdoc.extra-metadata

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --metadata option.

Set/override metadata of the top level suite.

corresponds to the `-M --metadata name:value *` option of _testdoc_

## testdoc.extra-set-tag

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --settag option.

Set given tag(s) to all test cases.

corresponds to the `-G --settag tag *` option of _testdoc_

## testdoc.extra-suites

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --suite option.

Include suites by name.

corresponds to the `-s --suite name *` option of _testdoc_

## testdoc.extra-tests

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Appends entries to the --test option.

Include tests by name.

corresponds to the `-t --test name *` option of _testdoc_

## testdoc.includes

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Include tests by tags.

corresponds to the `-i --include tag *` option of _testdoc_

## testdoc.metadata

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Set/override metadata of the top level suite.

corresponds to the `-M --metadata name:value *` option of _testdoc_

## testdoc.name

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Override the name of the top level suite.

corresponds to the `-N --name name` option of _testdoc_

## testdoc.set-tag

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Set given tag(s) to all test cases.

corresponds to the `-G --settag tag *` option of _testdoc_

## testdoc.suites

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Include suites by name.

corresponds to the `-s --suite name *` option of _testdoc_

## testdoc.tests

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Include tests by name.

corresponds to the `-t --test name *` option of _testdoc_

## testdoc.title

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

Set the title of the generated documentation.
Underscores in the title are converted to spaces.
The default title is the name of the top level suite.

corresponds to the `-T --title title` option of _testdoc_

## tests

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Select tests by name or by long name containing also
parent suite name like `Parent.Test`. Name is case
and space insensitive and it can also be a simple
pattern where `*` matches anything, `?` matches any
single character, and `[chars]` matches one character
in brackets.

corresponds to the `-t --test name *` option of _robot_

## timestamp-outputs

Type: typing.Union[bool, robotcode.robot.config.model.Flag, NoneType]

When this option is used, timestamp in a format
`YYYYMMDD-hhmmss` is added to all generated output
files between their basename and extension. For
example `-T -o output.xml -r report.html -l none`
creates files like `output-20070503-154410.xml` and
`report-20070503-154410.html`.

corresponds to the `-T --timestampoutputs` option of _robot_

## tool

Type: typing.Any

Tool configuration.

## variable-files

Type: typing.Optional[typing.List[typing.Union[str, robotcode.robot.config.model.StringExpression]]]

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

Type: typing.Optional[typing.Dict[str, typing.Union[str, robotcode.robot.config.model.StringExpression]]]

Set variables in the test data. Only scalar
variables with string value are supported and name is
given without `${}`. See --variablefile for a more
powerful variable setting mechanism.

Examples:

```
--variable str:Hello       =>  ${str} = `Hello`
-v hi:Hi_World -E space:_  =>  ${hi} = `Hi World`
-v x: -v y:42              =>  ${x} = ``, ${y} = `42`
```

corresponds to the `-v --variable name:value *` option of _robot_

## xunit

Type: typing.Union[str, robotcode.robot.config.model.StringExpression, NoneType]

xUnit compatible result file. Not created unless this
option is specified.

corresponds to the `-x --xunit file` option of _robot_


