# Changelog

All notable changes to this project will be documented in this file. See [conventional commits](https://www.conventionalcommits.org/) for commit guidelines.

## [2.8.0](https://github.com/robotcodedev/robotcode/compare/v2.7.0..v2.8.0) - 2026-10-25

### <!-- 0 -->Features

#### Analyze

- Add hidden dump-model command to inspect the semantic model ([23ad07c](https://github.com/robotcodedev/robotcode/commit/23ad07c8ffbddf3b6429d94f958537cdd39bf0c6))

  The new diagnostic command `robotcode analyze dump-model <file> [-o out.json]`
  serializes the complete semantic model of a Robot Framework file as
  deterministic JSON: the block tree, all statements with their full token
  trees including sub-tokens, resolved keyword and library references, and
  the variable scopes with per-definition visibility. This makes it possible
  to manually verify what the analyzer actually built and to diff models
  between versions.

  The command uses the same configuration as `robotcode analyze code`
  (robot.toml, profiles, -v/-V/-P) and builds the semantic model regardless
  of the experimental flag. It is hidden from help output; the JSON format
  is a developer surface without stability guarantees. OpenSpec change
  semantic-model-dump-tool synced and archived.


#### Config

- Let the rebot, libdoc and testdoc tables win over the settings outside of them ([a0e7a21](https://github.com/robotcodedev/robotcode/commit/a0e7a21f20e06f31a8f92325fc941608fe36a16c))

  A setting in `[rebot]`, `[libdoc]` or `[testdoc]` of robot.toml now wins over the same setting outside of the table, and `extend-` settings in these tables work. `robotcode rebot` takes from outside only what Robot Framework itself passes from robot to rebot after a run, and `robotcode libdoc` only `python-path`. The new `[extend-rebot]`, `[extend-libdoc]` and `[extend-testdoc]` change these tables from a later file, such as `.robot.toml`, or from a profile.


#### Debugger

- Name the failed keyword and the calls that led to it ([9cc3ef9](https://github.com/robotcodedev/robotcode/commit/9cc3ef95dc57b184b8ca01fcc8b2ec7af6c0d47b))

  When a debug run stops at a failure, VS Code's exception widget now names
  the failed keyword, test or suite, shows the message alone and lists the
  calls that led there with links to their lines, followed by the Python
  traceback when the error comes from a library's Python code.

- Match keyword breakpoints like Robot Framework ([491c19c](https://github.com/robotcodedev/robotcode/commit/491c19cdf68b6a2dd5a0ed3ec92e0267051f3a50))

  Keyword breakpoints of `robot-debug` and `.break` matched names exactly, so `get_price` or `should be equal` never stopped although Robot Framework runs those keywords, and a keyword with embedded arguments could only be targeted per call. They now match names like Robot Framework, accept its glob patterns such as `BuiltIn.*`, and stop at every call of a keyword with embedded arguments when given its definition name.


#### Language Server

- Show the errors of the configuration in the editor ([3bbd793](https://github.com/robotcodedev/robotcode/commit/3bbd79367cabf8b2a2104c7aa04b27c893839405))

  The language server now starts also when robot.toml cannot be loaded or a profile name selects nothing, and shows such errors of the configuration as error messages in the editor instead of only in its log. Names of the editor's own profile selection are left to the editor, which reports them with a way to fix them.

- Highlight uses of keyword arguments as parameters ([e4ae168](https://github.com/robotcodedev/robotcode/commit/e4ae168c607daa0398e78e4c69a443b06a38e830))

  Uses of an argument declared in [Arguments] now get the semantic token
  type parameter, like the declaration, also in settings such as [Timeout]
  and [Teardown] and wherever the [Arguments] line stands. Names in [Tags]
  and [Documentation], which Robot Framework resolves with the caller's
  variables, stay variables. Themes that style parameters show the uses
  like their declaration.

  Also plans making EXCEPT AS and item assignments references of the
  variable they set (except-and-item-assignment-references).

- Find references on the prefix of a keyword call ([cdd522d](https://github.com/robotcodedev/robotcode/commit/cdd522d166b61293e72921d1e1e909e1d6ee37d7))

  Find References on the library or resource name in front of a keyword, such
  as `BuiltIn` in `BuiltIn.Log` or `shop` in `shop.Open Shop As`, now lists the
  same places as on the import: where the library or resource file is imported
  and every call with its name in front. In PyCharm, LSP Reference(s) shows
  them there, and Show Usages and Find Usages on `BuiltIn` also list its calls.

- Keep the references in step with the files on disk ([6959f55](https://github.com/robotcodedev/robotcode/commit/6959f553bfa50ea553fe354708039c6cdebf3e47))

  Find References, Rename, the references code lens and the unused hints now see the latest analysis of every file the language server knows: references stay while an analysis is renewed, deleted files and analyses that end after a document was closed leave nothing behind, and files created outside the editor are analyzed. A periodic check of the workspace files finds the changes the editor does not report, every robotcode.analysis.fileCheckInterval minutes (5 by default, also on IntelliJ's Analysis page), and the analysis cache drops the entries of deleted files and keeps no analysis with a failed import.

- Sort deprecated keywords last in keyword completion ([f30205e](https://github.com/robotcodedev/robotcode/commit/f30205ed1ea737e90b9cf644e981ad18611fdff4))

  Deprecated keywords are now struck through in every keyword list, also after a library or resource name, and come after the other keywords. The new setting robotcode.completion.hideDeprecatedKeywords, off by default, leaves them out completely.

- Hide private keywords of other files in keyword completion ([f9d6b93](https://github.com/robotcodedev/robotcode/commit/f9d6b9349512286bf26cb6f65e1ca7ff61c63d56))

  Keyword completion no longer offers keywords tagged robot:private that are defined in another file, private library keywords included. The new setting robotcode.completion.hidePrivateKeywords brings them back, marked as private and sorted after the other keywords. Calls of private library keywords are now reported as PrivateKeyword too.

- Link documentation to the Documentation Viewer ([b60a48b](https://github.com/robotcodedev/robotcode/commit/b60a48bbec4adc585dffa9012974e897e268acdc))

  For clients that ask for it, as the VS Code extension does, the heading of a hover, of completion details and of Keywords view tooltips, the names of keywords, data types and sections, and the links within the documentation open the Documentation Viewer at that place instead of an error editor. Show in Documentation Viewer becomes the first and preferred source action and Open Documentation is marked as deprecated; signature help and the Keywords view compute the reference targets of a library once instead of per argument or keyword.

- Offer showing documentation in a viewer ([411da74](https://github.com/robotcodedev/robotcode/commit/411da74d7dcb41e125b84a6589fb592ee420f6b7))

  The source actions "Show in Documentation Viewer" and "Show in New Documentation Viewer" appear wherever "Open Documentation" does, for the import the analysis resolved the name to. "Open Documentation" and the Keywords view now also find a resource imported through a resource in another directory, use the arguments of the import a call went through, and open the documentation of the current file's own keywords at the keyword.

- Show the metadata of a test or task in its hover ([5f4a256](https://github.com/robotcodedev/robotcode/commit/5f4a256fe49c0fba503261e4061665740c5b4e25))

  The hover of a test or task name lists its `[Metadata]` (Robot Framework
  7.5) below the documentation and the tags.

- Keep EOL tokens in the semantic model ([f693e7f](https://github.com/robotcodedev/robotcode/commit/f693e7f99d1b20030185c9d807b83411fd8a38aa))

  The semantic model now retains every token that carries text — including
  line breaks. Concatenating all statement token values reproduces the
  original file byte-for-byte, which makes the model reconstruction-complete
  and lays the groundwork for a future visual editor. Only the virtual,
  empty EOS statement markers are still dropped.

  No feature behaves differently: EOL tokens are never rendered as semantic
  tokens, and signature help keeps its exact envelope at line ends —
  verified by the dual-path parity suites across all supported Robot
  Framework versions.

- Move sidecar LSP features off ModelHelper ([4edcda5](https://github.com/robotcodedev/robotcode/commit/4edcda53849e0c71f904de5d54699e46e8f687fe))

  With the experimental semantic-model flag enabled, selection range, inline
  values (debug), and evaluatable-expression lookup now work on the semantic
  model and behave identically to the classic path — verified by new
  equivalence suites that probe both paths position-by-position over the full
  LSP test corpus on all supported Robot Framework versions, with no
  exceptions.

  Also fixes real user-facing bugs found on the way: the debug
  evaluatable-expression request no longer crashes at positions without a
  token, variable names containing spaces now resolve correctly on the model
  path, environment variables resolve in inline values, and local variables
  resolve at their exact defining column like the classic path.

  Code lens, the keywords tree view, the docs HTTP server, hover, references,
  and rename no longer depend on the legacy ModelHelper at all. OpenSpec
  change semantic-model-sidecar-cleanup synced and archived.

- Complete semantic-model Tier 1 semantic-tokens parity ([bd63280](https://github.com/robotcodedev/robotcode/commit/bd632809b48d6b82e0b5e8f74783b8bc1f4bdfd2))

  With the experimental semantic-model flag enabled, semantic highlighting
  now matches the classic highlighting byte-for-byte on all supported Robot
  Framework versions (5.0-7.4): variables inside arguments, inner keyword
  calls of Run Keyword variants, embedded keyword names, imports, options,
  and all builtin/embedded modifiers render identically.

  The semantic model carries the final highlighting semantics itself: token
  kinds and modifiers are fully resolved during analysis, so the
  semantic-tokens provider is a plain static mapping without version- or
  context-dependent logic. Highlighting gaps found on the way are fixed in
  the model path: Run Keywords decomposition in suite setup/teardown,
  [Setup] NONE and empty [Teardown], and the Name suite setting.

  The parity suite is repaired and guarded: it fails loudly if the flag does
  not reach the server and covers the full LSP test corpus, with two
  documented exceptions where the new path is more correct than the classic
  one. OpenSpec change semantic-model-tier1-completion synced and archived.


#### PyCharm

- Report selected profiles that robot.toml does not define ([3489863](https://github.com/robotcodedev/robotcode/commit/3489863203ae585da40268ca094e6ade6ea814dc))

  When the selection names a profile that robot.toml does not define, a notification says so and offers Remove from Selection and Select Configuration Profiles..., also in place of the notification about a failed discovery. The profile list keeps patterns and hidden profiles in the selection, and messages of the language server show characters such as * and < as they are.

- Complete robot.toml and highlight robot code blocks in Markdown ([aa1af47](https://github.com/robotcodedev/robotcode/commit/aa1af472c9bd27aa10f8ee4475c206fdaf128f20))

  PyCharm now completes the settings of robot.toml and .robot.toml from
  RobotCode's JSON schema without a schema mapping by hand, as VS Code does.
  Markdown code blocks marked robot, like those marked robotframework, are
  highlighted as Robot Framework code in the editor and the preview.

- Use the interpreter of the Robot Framework module ([1c77903](https://github.com/robotcodedev/robotcode/commit/1c77903e1757b875d142e3c34baf0827e95d42f8))

  In a project with several modules, RobotCode now takes the interpreter
  and the roots of the module that holds the Robot Framework project, not
  the first module with an interpreter, and asks when several modules
  qualify; the General page can change the module. Run configurations now
  show in their editor when their interpreter lacks Robot Framework, a
  target path is missing or a selected test is gone, and a run checks the
  interpreter of its own configuration.

- Show each test failure with the calls that led to it ([f577367](https://github.com/robotcodedev/robotcode/commit/f577367253a4b501d84de1659e7419b0755628e9))

  A failed test's details in PyCharm now list each failure with its calls as Python lists them, from the call in the test inward, as `File "<file>", line <n>, in <keyword>` with links to the lines. Several failures follow an empty line and each begins with its message, failures the test caught are marked "Caught:", and a keyword such as Wait Until Keyword Succeeds that ends with an error of its own is one failure. A double-click on a failed test now opens the call in the test that led to its first failure, and VS Code's exception widget lists the calls in the same order, from the test down to the failed keyword.

- Announce a new RobotCode version with What's New ([67d6695](https://github.com/robotcodedev/robotcode/commit/67d66956340dee27ace1ad6a2468f3f84f1b4c84))

  After RobotCode was installed or updated, the first Robot Framework project that opens shows a notification whose action "What's New?" opens the news about the latest release in the browser, as in VS Code. Tools | RobotCode | Show What's New opens the same page at any time, dev builds aren't announced, and "Show whats new on update" on the General page switches the notification off for all projects.

- Put content and source roots on the Python path ([d661292](https://github.com/robotcodedev/robotcode/commit/d661292eb6663a61487840f175dcdd22c4230702))

  The analysis, test discovery and test runs now find libraries and resource files in the project's content roots and in folders marked as Sources or Test Sources, as PyCharm's Python run configurations do. Two switches on the Robot settings page, both on by default, turn this off for content roots or source roots, and marking a folder takes effect without restarting the IDE.

- Publish releases and prereleases to the JetBrains Marketplace ([7873e7a](https://github.com/robotcodedev/robotcode/commit/7873e7a051e551b6c061fc2c154a6e287dcbc424))

  New versions of the plugin are uploaded to the JetBrains Marketplace automatically when they are released, like the VS Code extension. Prereleases go to the Marketplace channel `dev`; to get them, add `https://plugins.jetbrains.com/plugins/dev/list` as a plugin repository in the IDE.

- Show a test's log messages and the process output in a Terminal tab ([cfafa48](https://github.com/robotcodedev/robotcode/commit/cfafa48f20ad798263b3a5174c25c32652a3d31c))

  Selecting a test in the results tree now shows the log messages that the debugger sent while it ran, also when Robot Framework's console is switched off, and the output of the Robot Framework process has a "Terminal" tab of its own that looks like a terminal run; it comes first and is shown when a run or debug session starts, and the tab of the results tree is named "Debug Console".

- Show where tests failed, link output files and rerun failed tests ([04338a7](https://github.com/robotcodedev/robotcode/commit/04338a7b8639188cf47d3642dfe680a67933d363))

  A failed test now lists the keywords it failed in, innermost first and with links to their calls, and navigating from it opens the call that failed; failures that the test caught before follow, marked as caught, as Robot Framework's log keeps them collapsed. The Output, Log and Report lines of the console open their files, the progress knows the number of tests from the start, and Rerun Failed Tests runs exactly the tests that failed, also from a debug session.

- Show report and log in a preview tab with a toolbar ([8f19b86](https://github.com/robotcodedev/robotcode/commit/8f19b865baf5179e93fcad6bb571b8b0fa9d4525))

  "Built-in preview" now opens the report and the log in a RobotCode preview tab that the next run reloads in place, in the editor split where the user put it, also for output outside the project, instead of the platform's preview, which went stale or moved between splits. The tab has a toolbar to go back and forward between report and log, reload, find in the page and open the shown page in the default browser.

- Add the run and debug options known from VS Code ([0e0b414](https://github.com/robotcodedev/robotcode/commit/0e0b414adbd67e5856babf3bd710c0dd411f7625))

  Robot Framework run configurations can now run tests through a launch wrapper such as xvfb-run, pass robotcode arguments, switch the debugger's messages, log and timestamps, stop on entry, wait longer for a slow debugger start and pass extra debugger arguments; the new Run and Debug settings pages hold the project defaults. After a run, the report or the log opens in the built-in preview or a browser when asked to, and the run and debug tabs offer Open Report and Open Log.

- Choose robot.toml profiles per run configuration and per run ([f57913e](https://github.com/robotcodedev/robotcode/commit/f57913e9c55fe67ded5e985ee9f6870840e64217))

  A Robot Framework run configuration can now follow the profiles selected for the project, use the default profiles of robot.toml or name its own, and Run with Profile... and Debug with Profile... in the gutter and context menus run a test, suite or folder once with a chosen profile, without changing any configuration.

- Add the Robot settings page known from VS Code ([45debd3](https://github.com/robotcodedev/robotcode/commit/45debd34489d327a97a616b4799ddeab05dc9735))

  PyCharm and IntelliJ IDEA now have a Robot page below the Robot Framework settings with the settings of VS Code's Robot category, such as the Python path, variables and environment variables. The language server, test discovery and every run use them together with robot.toml, and run configurations add their own values, so a library on an extra Python path resolves in the editor and in runs without an entry in robot.toml.

- Show the Robot Framework exception breakpoints as one group ([0a11c12](https://github.com/robotcodedev/robotcode/commit/0a11c12e0c4174233e6a74b533f0c98ec797faa9))

  The Breakpoints dialog lists Uncaught Failed Keywords in one Robot Framework Exception Breakpoints group, and its add button adds Failed Keywords, Failed Tests and Failed Suites with settings of their own, as with PyCharm's Python exception breakpoints.

- Add a debug console, hover values and breakpoint options ([eb1ea76](https://github.com/robotcodedev/robotcode/commit/eb1ea7660cb1fb6b3e84897a998161e6bbc3c7db))

  While a run is paused, the Evaluate dialog, watches, breakpoint fields and the new Robot Debug Console next to the run's console complete the keywords and variables of the paused run without logging errors, and hovering a variable shows its value. Line breakpoints get a condition, a log message and a hit count that the project keeps, and the IDE now applies a breakpoint's suspend policy, hit message, "Remove once hit" and the breakpoints that wait for it.

- Expand lists and change variables in the debugger ([2a11d7d](https://github.com/robotcodedev/robotcode/commit/2a11d7d82010f4b4a75b6b39366fcd0fa1f11cf7))

  While a run is paused, list variables expand into their items in pages of 100, also in Evaluate Expression and watches, and Set Value changes the variables of the paused keyword or test. Frames show their keyword, test or suite name, and groups and values the user expanded stay expanded after a step.

- Run Robot Framework tests from every context ([35a1e65](https://github.com/robotcodedev/robotcode/commit/35a1e65cbf2c5f37a263f9b1f3e3049881709b00))

  Ctrl+Shift+F10 and Run in the editor now run the test whose body holds the caret, elsewhere the suite of the file. Several selected files, folders or result nodes run together, suite nodes of the results tree can be rerun and opened, and suite files outside the paths of robot.toml run by their path. Folders with Robot Framework suites run as such by default while pytest stays in the menu, gutter runs take the values of the configuration template, and all of this keeps working while the IDE indexes.

- Set Robot Framework options in run configurations ([6a83900](https://github.com/robotcodedev/robotcode/commit/6a839000fdb4b6f9fa573dd43330d161624e353d))

  Run configurations get a Robot arguments field and, under Modify options, variables, variable files, Python path, languages, include and exclude tags, output directory, mode and dry run, passed after the options of robot.toml as in VS Code's launch configurations. Paths and robot arguments take IntelliJ's macros such as $ProjectFileDir$, and chosen files and folders are added relative to the working directory.

- Save and edit Robot Framework run configurations ([e9961d8](https://github.com/robotcodedev/robotcode/commit/e9961d86f213964185dbf06d4b4c58092fd37ca3))

  Run configurations keep their target across restarts and can be stored as project files: "Files and folders" with paths that replace those of robot.toml, or "Tests and suites" with the full names that discovery reports, in a field that expands to one entry per line. The editor is PyCharm's run configuration editor, so the interpreter, interpreter options, working directory, environment variables, .env files and Run with uv take effect, gutter runs reuse their configuration instead of creating "(1)" copies, Profile ends with a message, and a configuration with a remote interpreter is refused (#418).

- Parse only the selected files when running a single test or suite ([b133468](https://github.com/robotcodedev/robotcode/commit/b133468c549209b5440f21fd2b26918d0c71e17c))

  Running a test, a task or a suite from the gutter or the Project view now passes the same selection arguments as VS Code's Test Explorer, so Robot Framework 6.1 and newer parses only the involved files and errors in unrelated files no longer appear in or break the run (#631). In projects whose robot.toml lists several paths, such a run hits the Robot Framework bug from #656, as in VS Code; run-empty-suite = true in robot.toml avoids it.

- Restart the language server and rediscover tests only when their inputs change ([f98c931](https://github.com/robotcodedev/robotcode/commit/f98c931d90cd1ff2f7c4cdac5da9edcb5cf6f7ee))

  Settings changes restart the language server or run a discovery only when what they receive changes, the project's own robot.toml, .robotignore and .gitignore trigger both, Tools | RobotCode | Refresh Robot Framework Tests runs a discovery on demand, opening or closing a file no longer starts one, and a failed discovery keeps the run markers and shows one notification with robotcode's error instead of an IDE error, while problems that discovery reports for a file appear at its marker on line 1.

- Show run markers for the tasks of RPA suites ([c13e8c4](https://github.com/robotcodedev/robotcode/commit/c13e8c4a839fae4a5c92f4e022340e042bbf27ae))

  Tasks get run markers like tests, the marker on line 1 of a task file no longer disappears after the file is opened or edited, also in projects with rpa = true, and a file that loses its last test or task is picked up by a full discovery, as in VS Code.

- Switch RobotCode off per project and show its status in the status bar ([1e1fe80](https://github.com/robotcodedev/robotcode/commit/1e1fe80ade95b4914a48d62362a581c728ca5feb))

  "Disable extension" on the General settings page switches RobotCode off for the project, as in VS Code, and the banner for an unusable interpreter offers to configure the interpreter, retry, disable RobotCode or close it, with the pip command for a missing Robot Framework. The status bar shows the Robot Framework version and the selected profiles with a menu of the RobotCode actions, and quick fixes such as Create Keyword or Extract keyword now select or rename the new text instead of ending with an error notification.

- Select the robot.toml configuration profiles for the project ([2328b6f](https://github.com/robotcodedev/robotcode/commit/2328b6f2582735d3bc2039379c48e6ee7920412c))

  Profiles can be chosen with Tools | RobotCode | Select Configuration Profiles... or on the General settings page, behave as in VS Code's picker and reach the language server, test discovery and runs as -p; the choice is stored for the current user only. The shared RobotCode settings pages can be preset under Settings for New Projects, and the Robocop config file is stored as entered, as in VS Code, without a check by the plugin.

- Remove run markers while the project has no usable Python interpreter ([6e8c65a](https://github.com/robotcodedev/robotcode/commit/6e8c65abd13d775a755cc1aaed8ee376ee1c470a))

  When the environment check finds the project's interpreter not usable or the check fails, the run markers of the last discovery disappear instead of offering runs that cannot start; they stay while a check runs and come back with the discovery that follows a usable result.

- Check the Python environment in the background and start RobotCode only in Robot Framework projects ([36e5f3d](https://github.com/robotcodedev/robotcode/commit/36e5f3d78bd5a5d4e6c43187fe9994ab37ed8bfc))

  The environment check no longer blocks the editor, the status bar or the language server start, gives up after 30 seconds instead of switching RobotCode off, and names what is wrong, such as an old Python or Robot Framework version, a missing Robot Framework or a remote interpreter, which RobotCode does not support yet. RobotCode starts its language server and test discovery only in projects with Robot Framework files or a robot.toml, or once such a file is opened, restarts only when the project's interpreter really changes, picks up a Robot Framework installed later without a restart, and a run with an unusable interpreter fails with the IDE's usual run error.

- Add extra args for robotcode and the language server ([8eb083f](https://github.com/robotcodedev/robotcode/commit/8eb083f964e448f862c293ce12dd690e2b11703d))

  The new General and Language Server pages under Robot Framework take extra robotcode arguments, as VS Code's robotcode.extraArgs and robotcode.languageServer.extraArgs do: the first reach test discovery but not the language server or test runs, the second only the language server, whose output then appears in the Language Servers tool window. Both are stored for the current user in the workspace file. Extra arguments now come before the plugin's own options, so a --format among them no longer breaks test discovery.

- Add Analysis and Robocop settings pages and keep the analysis cache out of the project ([b858a7f](https://github.com/robotcodedev/robotcode/commit/b858a7fdbcff4431dfaff945dbadbc12014bac23))

  The analysis, diagnostics, workspace, experimental and Robocop settings of VS Code can now be changed in PyCharm and IntelliJ IDEA, under the names VS Code uses. The language server keeps its analysis cache in the IDE's system directory unless the save location is the project folder, so .robotcode_cache no longer appears in the project and gets indexed. Information diagnostics now show as weak warnings that the Problems view lists, while hints stay out of it, and applying several RobotCode pages restarts the language server once.

- Add an Editing settings page and send the language server VS Code's default settings ([5e49ce0](https://github.com/robotcodedev/robotcode/commit/5e49ce029a122aac86eaee8a68cebff54ba2361c))

  The Robot Framework settings node replaces the work-in-progress page and lists its sub-pages. The new Editing page makes the completion settings take effect, adds switches for private and deprecated keywords, and keeps the inlay hints off by default, because IntelliJ shows them all the time. The language server now gets every setting it reads with VS Code's defaults instead of its own, so it skips the folders VS Code excludes and starts its documentation server only when something needs it.

- Require PyCharm or IntelliJ IDEA 2026.1 and update LSP4IJ to 0.21.0 ([20109ae](https://github.com/robotcodedev/robotcode/commit/20109ae3fd63521a8b0e8777070ea2e508e2e796))

  The plugin is now built for the 2026.1 platform and needs PyCharm or IntelliJ IDEA 2026.1 or newer. It uses LSP4IJ 0.21.0.

- Read test metadata from the test discovery ([289cdb3](https://github.com/robotcodedev/robotcode/commit/289cdb3711a2f9cd5df42dff2bfb57690c5fb368))

  The test discovery understands the metadata that tests and tasks can
  have since Robot Framework 7.5.


#### REPL

- Name the file and line of each keyword in the JSON of robotcode doc ([7124234](https://github.com/robotcodedev/robotcode/commit/7124234d715b8922d2cd66fe66b65247ebc05c2c))

  The keyword entries in the JSON of `robotcode doc` now carry `source` and `lineno`, the file that defines the keyword and its line there, empty and `-1` when they are unknown. A tool that reads the JSON can open the definition of a keyword from them.

- Handle Ctrl-C like Python's REPL and pdb ([27124be](https://github.com/robotcodedev/robotcode/commit/27124be4aef8453a03df8891611dd545fa59baf0))

  Ctrl-C at the `>>>`, `(rdb)` and `(com)` prompts used to end the session, resume the run or store the typed commands; it now drops what was typed and shows the prompt again. While a run executes with the debugger attached, Ctrl-C pauses at the next keyword instead of failing the keyword that runs.

- Leave inputs that failed out of .save ([3b29a3c](https://github.com/robotcodedev/robotcode/commit/3b29a3c781d6de03447fb93359c032326aea1e8a))

  `.save` exported every input that parsed, so a session with a failed attempt wrote a file that failed at the same place. It now leaves out inputs whose run failed or was skipped and says how many it left out; `.save --keep-failed` keeps them, for example to reproduce a failing check.

- Show the subsections of the introduction in the sidebar of the documentation viewer ([1065834](https://github.com/robotcodedev/robotcode/commit/1065834fc356fab9ae5d642944f7aa2824d53637))

  The sidebar of `robotcode doc browse` and `.doc` lists the sections of a library's introduction with their subsections, indented by their depth, and the filter keeps an entry while one below it matches.

- Add a sidebar with the outline of a library page to the documentation viewer ([976afec](https://github.com/robotcodedev/robotcode/commit/976afec39ca9413d75f9b6ab4e51fee87cd66863))

  In `robotcode doc browse` and `.doc`, `s` shows the sections, keywords and data types of the page in a sidebar, as in Libdoc's HTML output. It filters while typing, jumps to the chosen heading, and stands beside the page in a wide terminal and over it in a narrow one.

- Add robotcode doc to show the documentation of libraries, resources and suites ([5ee0552](https://github.com/robotcodedev/robotcode/commit/5ee05529a964c43c438473c109a9df3164c204ec))

  `robotcode doc lib`, `keywords`, `keyword` and `browse` load their target anew with the project's configuration, profiles and variables, and write Markdown, a Markdown file or JSON, or open the page in the terminal viewer; a target that cannot be loaded aborts like Libdoc. The full page, which the REPL's `.doc` shows too, orders its keywords, leaves out private ones, starts the keywords with an index, documents the data types and links names, types and sections to their GitHub-style headings. Library hovers now escape `|` in table cells, keep `#` in link targets and show the scope as `GLOBAL`.

- Let unhandled failures fail the session test and the exit code ([47b3f6e](https://github.com/robotcodedev/robotcode/commit/47b3f6e1f1c3ae3861af8618b3616c502962bcdb))

  `robotcode repl` always marked its session test as passed and exited with 0, even when statements failed, so a piped check, a script in CI or an agent could not tell success from failure. A statement that fails without being handled now fails the session test in the output files, and a non-interactive session, with piped input or script files without `--inspect`, exits with 1. `--statusrc`/`--nostatusrc` and `no-status-rc` override that exit code, and `.exit CODE` ends the session with a code of its own.


#### Robot

- Warn about library imports that Robot Framework ignores because their name is taken ([1f3a676](https://github.com/robotcodedev/robotcode/commit/1f3a676dfcf8fe9ad222397ffd617cc02b91add0))

  Since Robot Framework 7.4, a library import is ignored with a warning when an earlier import already uses its name for another library or for the same library with other arguments, while RobotCode dropped such an import silently. It now reports it as LibraryImportIgnored, and an ignored import in a resource file at the suite's Resource import.

- Link argument and return types to their data types ([4846199](https://github.com/robotcodedev/robotcode/commit/4846199a7907885a77a807daf20175d242a94291))

  On the full documentation page that `robotcode doc lib`, the REPL's `.doc` and the Documentation Viewer show, each type in an argument table or a return type that has an entry under Data types now links to it, as in Libdoc's HTML. The renderer also gets what the language server needs to link documentation to the Documentation Viewer.

- Show argument descriptions in a column of the argument table ([f7a28ad](https://github.com/robotcodedev/robotcode/commit/f7a28ad6fb35004bfcbe83d352cd632ff2365b9e))

  Keyword documentation used to list the arguments when they had descriptions and show the table when they had none, so with Robot Framework 7.5 the same keyword looked different than with 7.4 and one page could mix both forms. The arguments now always appear in the table, with the descriptions in an additional column when there are any.

- Report a `Tags:` section without an empty row in keyword documentation ([4825d53](https://github.com/robotcodedev/robotcode/commit/4825d538b4cbdc15a25421227ad37ca0f91b129f))

  Robot Framework 7.5 warns at run time when the `Tags:` section of a
  keyword's documentation is not preceded by an empty row. RobotCode now shows
  the same warning while a resource or suite file is edited.

- Show the documentation of arguments, return values and exceptions ([ceb0053](https://github.com/robotcodedev/robotcode/commit/ceb00535203bec1fe0af5e77f0515696b9d40199))

  With Robot Framework 7.5, keywords that document their arguments in
  Google style (`Args:`, `Returns:`, `Raises:`), like the standard libraries
  do, list every argument with its type, default value and description in
  hover, signature help, named argument completion and the REPL. References
  such as `[Set Log Level]`, `%TOC%` and admonitions in Markdown
  documentation are resolved instead of being shown as raw text.

- Support Robot Framework 7.5 ([7c278d8](https://github.com/robotcodedev/robotcode/commit/7c278d83a1e8ddc894e84d719568f8ab1b1d5a96))

  Robot Framework 7.5 is now a supported and tested version. This includes
  the Markdown documentation of the standard libraries, `[Metadata]` in
  tests with the `${TEST_METADATA}` variable, Markdown resource imports,
  and custom console loggers and the libdoc `MARKDOWN` format in
  `robot.toml`.


#### RobotCode

- Support Python 3.15 ([7a70282](https://github.com/robotcodedev/robotcode/commit/7a702823197f5f5a901ae6699e83a0dd46134bdf))

  Python 3.15 is supported with Robot Framework 7.5, the first Robot Framework version that supports it. From now on every Robot Framework version is supported and tested only with the Python versions it officially supports itself, which also narrows the support on the older Python versions; other combinations may still work, but they are not tested anymore.


#### Runner

- Select tests and tasks by their metadata ([32e02c1](https://github.com/robotcodedev/robotcode/commit/32e02c1231299f24f8a3782f2731f878ae23aa6d))

  Robot Framework 7.5 lets tests and tasks carry [Metadata], but nothing could select by it. robot, robot-debug, discover and results now take --by-test-metadata and --exclude-by-test-metadata with tag-like patterns such as `Issue:4409 AND Author:Hans*`, the same selection works with plain robot through the robotcode.modifiers pre-run modifiers, and discover metadata lists the test and suite metadata in use.

- Configure the console of rebot in robot.toml ([f1b13fd](https://github.com/robotcodedev/robotcode/commit/f1b13fde534f142a775dac2709c96da053044ff7))

  Since Robot Framework 7.5 `rebot` has the `--console` and `--quiet`
  options. The `[rebot]` section of `robot.toml` accepts `console` and
  `quiet` now; the top-level `console` and `quiet` stay `robot` options and
  are not passed to `rebot`. The dry run of `robotcode rebot` says "rebot"
  instead of "libdoc".

- Show the metadata of tests and tasks in discover and results ([d661a27](https://github.com/robotcodedev/robotcode/commit/d661a27c81c0caa19288879e568c7cf5e28233d3))

  Since Robot Framework 7.5 tests and tasks can have a `[Metadata]` setting.
  `discover` and `results` include it in their JSON output, find it with
  `--search` and print it with `--show-metadata`; `discover all` and
  `results log` print it by default.

- Rename `--tags` of discover and results show to `--show-tags` ([177103c](https://github.com/robotcodedev/robotcode/commit/177103c859bceb70755491cf89d77ab07b052413))

  `robotcode discover all`, `tests` and `tasks` and `robotcode results show`
  now take `--show-tags / --no-show-tags` instead of `--tags / --no-tags`.


#### VS Code

- Show or open a Documentation Viewer from the Documentation Bookmarks view ([bc9855f](https://github.com/robotcodedev/robotcode/commit/bc9855f7569a0272444c7fa1b1e549eaec79a278))

  The title of the Documentation Bookmarks view has two buttons: Show Documentation Viewer brings the viewer that the actions use to the front with the focus, also from another window, or opens one when there is none, and New Documentation Viewer opens a new one. Show Documentation Viewer is a command of the palette too.

- Add a context menu to the outline of the Documentation Viewer ([8a1b212](https://github.com/robotcodedev/robotcode/commit/8a1b212773b1b29e9f7242729b4c910a9b4dda6d))

  A right-click on an entry of the outline, the context menu key or Shift+F10 opens a menu that shows the entry in the same or in a new viewer, bookmarks it without going there, and for a keyword opens the file that defines it at its line, also a library of the Python environment such as `Collections.py`.

- Report selected profiles that a folder does not define ([10ef5c8](https://github.com/robotcodedev/robotcode/commit/10ef5c813dcbc6624272a9fa49af724d3d8b54a7))

  When robotcode.profiles names a profile that a folder's configuration does not define, a notification says so and offers Remove from Selection and Select Configuration Profiles, the Testing view shows a hint instead of an error item, and the REPL shows the notification instead of a terminal that closes with the error. Select Configuration Profiles keeps patterns and hidden profiles in the selection and stores long profile names in full.

- Bookmark places in the Documentation Viewer ([9f56212](https://github.com/robotcodedev/robotcode/commit/9f56212038429dcffce77ebb9a2a8db898186367))

  A star after the target field bookmarks the place a viewer shows, in its
  workspace folder. The Explorer view Documentation Bookmarks lists, opens
  and removes the bookmarks and moves them to All Workspaces, which
  Settings Sync takes to other machines; the first start bookmarks the
  standard libraries. The target field shows the place after a #, as a
  browser's address bar does, and offers the bookmarks before its
  completions.

- Complete the target in the Documentation Viewer ([16e6fbb](https://github.com/robotcodedev/robotcode/commit/16e6fbba7d76c00982e09c291e4fecb2e53a4614))

  While you type in the target field of the Documentation Viewer, a list under
  it completes the names of libraries, resources and suite files, as the editor
  does for imports. Enter or Tab takes the selected suggestion.

- Copy the versions in use for a report ([1e0d8f8](https://github.com/robotcodedev/robotcode/commit/1e0d8f8b32589035e61f652c428cdcea9e40268e))
- Open a new Documentation Viewer from a viewer's toolbar ([e4c6fe7](https://github.com/robotcodedev/robotcode/commit/e4c6fe78d11d654676ee0857ad8d77ec0ed84569))

  A button at the end of a Documentation Viewer's toolbar opens a new viewer on
  BuiltIn in the viewer's workspace folder, with the target field ready for
  typing, where robotcode.documentationViewer.openLocation says. The commands are
  renamed to match: "RobotCode: New Documentation Viewer" and "RobotCode: Copy
  Documentation Viewer into New Window".

- Run tests in RobotCode's own terminal on Windows too ([fa71310](https://github.com/robotcodedev/robotcode/commit/fa713107f68e86cf425d1a5df9007e3898997033))

  Runs in the run terminal now show their output on Windows as well and take
  keys and Ctrl+C there, with the same line before each run, the same icon and
  the same closing on a key as on Linux and macOS.

- Run tests in RobotCode's own terminal ([552a354](https://github.com/robotcodedev/robotcode/commit/552a3549a1dca1ca9a65ed9764da2062eff8dc3e))

  Runs and debug sessions now start in a terminal of RobotCode, the new
  default of `robotcode.debug.defaultConsole` and `console`. The run is
  the terminal's process, without a shell, so the Python extensions type
  no activation into it and every run gets the same environment. Each
  run shows its command line as one types it, carries VS Code's command
  decoration with Copy Command and Copy Output, keeps its command line
  at the top while its output scrolls, and the terminal is reused for
  the next run or closes on a key. Runs from the Test Explorer now keep
  Robot Framework's exit code, so libraries such as Browser close their
  processes at the end. `integratedTerminal` keeps the previous behavior.

- Show each test failure with the calls that led to it ([04584c9](https://github.com/robotcodedev/robotcode/commit/04584c918481366afdbdf54afcd7712be7195e94))

  A failed test now gets one entry per failure in the Test Explorer instead
  of one per failed keyword. The entry sits at the step of the test that led
  to it, and its peek lists the calls from that step inward to the line that
  failed, with their code. A keyword such as Wait Until Keyword Succeeds that
  ends with an error of its own is one failure with that error, failures the
  test caught are marked "Caught:", and calls in between show the message
  inline.

- Follow the Python side's environment and recover on your own ([4fdc1ff](https://github.com/robotcodedev/robotcode/commit/4fdc1ffa2f456bf25de13a9080a676c4e1e68807))

  The extension resolves a folder's interpreter through the Python Environments
  extension when it offers its API and through the Python extension's API
  otherwise, decides existence and Python version from their data and checks
  Robot Framework with its script. It notices a new virtual environment, a
  changed selection and a later Robot Framework install by itself and starts the
  language server without a restart. The blocking quick pick is replaced by one
  message per folder that names the problem, offers Select Environment, Create
  Environment, Retry and Use .venv, closes itself when the environment is usable
  and asks after Cancel whether to switch RobotCode off for the folder.

- Explain an empty Test Explorer ([90ea9f7](https://github.com/robotcodedev/robotcode/commit/90ea9f71c8733c5750f99497bedff3cb0f38a515))

  When RobotCode finds no tests or tasks, the Testing view now says so below VS Code's own text, with Refresh Tests and a link to the troubleshooting page; when the integration is switched off for every folder, it names the setting with a button to it; and when the folder has no Python environment with Robot Framework, it says that and offers Select Python Environment. A context key set after each discovery picks the hint; a folder without Robot Framework files counts as discovered without tests, and the environment state is read from the cached check, so the hint does not wait for the environment dialog.

- Mark the language model tools setting as deprecated ([b3f0dc8](https://github.com/robotcodedev/robotcode/commit/b3f0dc838c484ea8abed8e8a3753038716545f9b))

  `robotcode.ai.enableLanguageModelTools` carried the deprecation only in its description text; VS Code now shows the setting as deprecated and the settings reference carries the notice. The tools keep working until they are removed; the RobotCode chat plugin, which uses the `robotcode` CLI, replaces them.

- Add a button that hides and shows the outline of the Documentation Viewer ([6412564](https://github.com/robotcodedev/robotcode/commit/6412564d2bbaba62484a6af7a597d1c29b725af5))

  The button at the start of the toolbar gives the page the full width of the viewer. Each viewer keeps whether its outline is shown, also after a reload of the window, and the setting `robotcode.documentationViewer.showOutline` decides how a new viewer starts.

- Show the subsections of the introduction in the outline of the Documentation Viewer ([59c1baf](https://github.com/robotcodedev/robotcode/commit/59c1baf8f44997faf8272c8dfb7c7723a26cc799))

  The outline lists the sections of a library's introduction with their subsections to any depth, as the table of contents in the page does since 3d743de7. Every entry with entries below it can be collapsed, the arrow keys move into and out of the tree at any depth, and the filter keeps an entry while one below it matches.

- Highlight Robot Framework code blocks in Markdown previews ([d8826dc](https://github.com/robotcodedev/robotcode/commit/d8826dcb0333afed094d2771016de5e98e4d3647))

  Code blocks marked `robotframework` or `robot` now get colors in the Markdown preview and in the Documentation Viewer, like the Python next to them, so the examples in library documentation are no longer plain text. In a workspace without Robot Framework files, the first Markdown preview activates RobotCode but starts no language server.

- Open the Documentation Viewer from links and the Keywords view ([f11e106](https://github.com/robotcodedev/robotcode/commit/f11e10642f68668ec434dfeefd0074e7d77d7758))

  The extension asks the language server for links to the viewer, which then shows the keyword, data type or section of a link, the book button of the Keywords view shows the viewer instead of the Libdoc page, and the viewer can open its page as a Markdown document. Command links in documentation run only when they open the viewer, so a command link in a library's documentation no longer runs a VS Code command.

- Add the Documentation Viewer ([5c569b7](https://github.com/robotcodedev/robotcode/commit/5c569b7ad1650dcdf4600fb8f7f6dcf4b13ce912))

  An editor tab that shows the documentation of a library, resource or suite file as `robotcode doc lib` generates it, with an outline and filter, history, find and a pin, opened by the new source actions, the Keywords view and the command palette. In a workspace with several folders each viewer uses the settings of its folder, which its toolbar shows and lets you change. On desktop, "Open Documentation", "Show Documentation" and log and report files set to open in the Simple Browser now open beside the editor in VS Code's integrated browser, in one reused tab.

- Require VS Code 1.127 and build for Node.js 24 ([381a1e9](https://github.com/robotcodedev/robotcode/commit/381a1e93efa59abb8240074e404b39d4c1c7f3d1))

  The VS Code extension now needs VS Code 1.127 or newer and is built for the Node.js 24 that the extension host of these versions runs. Older VS Code versions keep the newest RobotCode release they can install.


#### Website

- Expand the robot.toml guide into a group of pages ([9d0d64a](https://github.com/robotcodedev/robotcode/commit/9d0d64ad9d51e990003485d0555ad7df2a4966de))

  The guide now has pages on the files and the project root, the settings, profiles with default profiles, inheritance, order and hiding, how settings combine, the command line, recipes and troubleshooting, built on one example project. Its examples use TOML tables instead of inline tables, and the configuration page under Getting Started matches them.

- Add a guide to configuring projects with robot.toml ([6482969](https://github.com/robotcodedev/robotcode/commit/6482969f93427df9babcbb9336de214da1ccc1c8))

  The new guide explains all that robot.toml can do: how its settings map to Robot Framework options, paths, variables and environment variables, selecting and combining profiles, expressions, the files RobotCode reads, the project root and how to check the configuration. The configuration page under Getting Started is now a short start that links to it.

- Add a guide to working with RobotCode in PyCharm ([7eb2c4b](https://github.com/robotcodedev/robotcode/commit/7eb2c4bb34a5988394131c004f724bd70bcd17a2))

  A new PyCharm group under Guides shows how to write, navigate, run, debug and configure Robot Framework projects with RobotCode in PyCharm and IntelliJ IDEA, with screenshots that follow the site's light or dark theme. A comparison page names what PyCharm does not offer yet, such as the Test Explorer, and a new Get Started page sets RobotCode up in PyCharm.

- Add a guide to working with RobotCode in VS Code ([02bca23](https://github.com/robotcodedev/robotcode/commit/02bca2349f45345841da6485feb4f84cf6c86b4f))

  A new VS Code group under Guides shows how to write, navigate, run, debug and configure Robot Framework projects with RobotCode in VS Code, with screenshots and short recordings that follow the site's light or dark theme and with the menu way next to each shortcut. The VS Code settings get a generated reference page, and keys in running text no longer slip below the line.

- Show several examples for each feature of the home page tour ([b2f7c38](https://github.com/robotcodedev/robotcode/commit/b2f7c38dc12d36de094acafa107277757d66a671))

  Code intelligence, running and debugging, the configuration, the CLI and the REPL each show a series of recordings and terminal sessions, among them the Documentation Viewer, Go to Definition into a library, Robocop's findings, the Debug Console, a profile used in CI and the debugger at the REPL prompt. The VS Code recordings show the keyboard shortcuts they press, and a recording loads only when its example is shown.

- Rebuild robotcode.io on Astro and Starlight ([01910fa](https://github.com/robotcodedev/robotcode/commit/01910fa396efb1551f01948cc04de03039c2ef26))

  The documentation site is rebuilt on Astro and Starlight and reorganized into Getting Started, Guides and Reference by what the reader comes to do. A new home page shows RobotCode's features and an AI agent at work in short demos, and the news get tags and an RSS feed. All pages have new addresses; the old ones lead to the not-found page instead of redirecting. The What's New notification of the VS Code extension opens /news/latest/, which always leads to the newest release notes.



### <!-- 1 -->Bug Fixes

#### Analyze

- Find a changed resource open in the editor when checking the analysis cache on Windows ([39ebcf5](https://github.com/robotcodedev/robotcode/commit/39ebcf5af785cc30c50ddadf1cc8a922f8012b27))

  On Windows, a suite whose analysis was in the cache kept that analysis after a resource it imports was changed in the editor but not saved, so Find References, Rename and the unused hints went on showing the references from before the change. The check of the cache looked up the open resource with a URI that was not normalized: the analysis knows the file as `c:\...`, the documents of the editor as `C:\...`. So it compared the cached state with the unchanged file on disk. This also fixes the test for a resource changed in the editor, which failed in every Windows job of the CI.

- Read a cached Robot Framework file again after the language settings changed ([0a2e269](https://github.com/robotcodedev/robotcode/commit/0a2e269d0552278519bdeaf96502c2d8d81c21f5))

  After `languages` changed, files whose doc was in the analysis cache kept what they defined under the old settings. A resource with German section headers stayed empty after `languages = ["de"]` was added, and the suites that import it reported its keywords as not found, in `robotcode analyze code` and in the language server alike. Such a file is now read again with the current language settings.

- Keep the analysis cache in the cache-dir of robot.toml ([387c2d0](https://github.com/robotcodedev/robotcode/commit/387c2d05ea846ad5082ff4eb64c2e70258ce6abd))

  `robotcode analyze code` ignored `cache-dir` and wrote its cache into the project root, so `analyze cache` looked in another place; now both use it, relative to the project root, and the language server takes it ahead of the location the editor asks for.


#### Config

- Stop at a profile name that selects no profile ([dd3fb9c](https://github.com/robotcodedev/robotcode/commit/dd3fb9c45646da1760903c6226f7789d7fe8f706))

  A profile name or pattern from -p, ROBOTCODE_PROFILES, an editor's selection or inherits that selects no profile now stops robotcode before it runs anything, as an invalid robot.toml does: run exits with 252 and reports "No profile matches 'typo'.". Until now the command went on without the profile, so a mistyped profile on a CI server ran with another configuration. A name in default-profiles is only reported, an exact name also selects a profile with *, ? or [ in its name, and profiles that inherit each other stop with an error instead of a crash.

- Apply none of the profiles a disabled profile inherits from ([edaa183](https://github.com/robotcodedev/robotcode/commit/edaa183792ecbb1f9de72d6f68731e8fafc61545))

  Selecting a disabled profile still applied the profiles two or more levels up
  its chain: with ci disabled, inheriting from staging and staging from base,
  `-p ci` applied base. An inherited profile now applies only when a profile that
  inherits it applies, and an error in an `enabled` condition is reported once.

- Apply extend- settings next to the setting they extend ([45eaa5b](https://github.com/robotcodedev/robotcode/commit/45eaa5be64de81459a585c5150681ef994e12622))

  A profile or file with both `variables` and `extend-variables` ignored the extend- setting, and an extend- setting in `[extend-profiles.<name>]`, for example in `.robot.toml`, did not add to the setting of the profile it extends. Now the setting applies first and its extend- setting adds to it.


#### Debugger

- Show an error before the run in the Debug Console ([e7f9a61](https://github.com/robotcodedev/robotcode/commit/e7f9a61bb460c9cf1bd0ba959f11e29112ed01f0))

  With the internal console, a run that robotcode stops before Robot Framework runs, for example because of an error in robot.toml, now shows the error in the Debug Console. Until now the debug session ended first and the error was lost.

- Let a run's variable replace an inherited one of any case on Windows ([82ea39e](https://github.com/robotcodedev/robotcode/commit/82ea39e6265b79dd44252f8ddc46e8bd72fbd4f9))

  On Windows, a variable that a run's environment sets, such as `path` in
  `robotcode.robot.env` or `Path` in a launch configuration's `env`, now
  replaces the inherited one whatever its case. With Python 3.10, programs that
  a test started could still see the old value.

- Name the exception filters for tests and suites in the plural ([74823da](https://github.com/robotcodedev/robotcode/commit/74823da3e5d2332d7afad753992cb27f60797bf2))

  VS Code's Breakpoints view now shows "Failed Tests" and "Failed Suites", the
  names PyCharm uses too. Who had switched one of them on finds it off once
  after the update.

- Send grouped output with the console category ([d3765a2](https://github.com/robotcodedev/robotcode/commit/d3765a242a3da6ebeb9f7e66a22cf4c81d3cb0fe))

  The event that opens an output group sent the category as the text `OutputCategory.CONSOLE` instead of the console category, while the event that closes the group used the category; now both use it.

- Don't return from a finally block ([fca9eb5](https://github.com/robotcodedev/robotcode/commit/fca9eb59505e06c837e1f45e8e8f29e1e05d86d7))

  Python 3.14 and newer warn about the return in a finally block of the debugger when they compile it (PEP 765). The result is now returned after the block, and Ruff's rule B012 reports such statements from now on.

- Don't pause a run again after it was stopped ([5e0e3b7](https://github.com/robotcodedev/robotcode/commit/5e0e3b7afb5120e6359fb9869a3668a1db02a84a))

  Once a debug client has stopped a run, line breakpoints, steps and pause requests no longer pause it on its way to the end, so a breakpoint in a teardown no longer leaves the run paused after Stop in VS Code or in PyCharm and IntelliJ IDEA. Breakpoints with a log message keep writing it.

- Stop at the hit count of a breakpoint ([143cb60](https://github.com/robotcodedev/robotcode/commit/143cb60eec4c07ed39ea5cfe2a57c0bfcd9b5dca))

  A breakpoint with a hit count stopped at every hit except the given one, and a hit count with an operator such as `>= 3` never stopped. A hit count now stops at that hit, `>`, `>=`, `<` and `<=` compare with it, `% N` stops at every N-th hit, and a hit count of another form is reported in the Debug Console.

- Show a failing breakpoint condition also with .ignore and silent ([5136881](https://github.com/robotcodedev/robotcode/commit/51368814b1ff884763d6dea9c4d344237b191a2f))

  In `robot-debug` a breakpoint whose condition raised an error stayed hidden while `.ignore` skipped its hits, and with `silent` commands it never showed. Such a breakpoint now stops right away with the error in the stop line, also with `silent`, and a `.tbreak` stays in place so its condition can be fixed.

- Show why a breakpoint condition failed ([36022e1](https://github.com/robotcodedev/robotcode/commit/36022e16dc1bb3185dc2f914eabff4caf6217e6e))

  A breakpoint condition that raised an error went unnoticed: `robot-debug` stopped as if it were true, the VS Code debugger skipped the breakpoint as if it were false. Both now show the error, `robot-debug` in the stop line and VS Code in the Debug Console. The guide now also says that a keyword breakpoint's condition sees the caller's variables.

- Run keywords at the end of a failed test ([b3c004d](https://github.com/robotcodedev/robotcode/commit/b3c004de2822967fa1253d91d3a5da68430a70ec))

  A keyword typed at a failed-test stop of `robot-debug` failed with an IndexError on Robot Framework 7; it now runs. At a failed-suite stop `robot-debug` refuses keywords, because the suite is already closed in output.xml and the file would become unreadable. In VS Code the "Failed Test" exception breakpoint, which had no effect, stops again, and keywords evaluated at the end of a test or suite run there as well.


#### Language Server

- Offer the documentation actions in inline IF and Run Keyword ([b99fd04](https://github.com/robotcodedev/robotcode/commit/b99fd0409c549d9c2f0ed1f6a83536f63bdd255d))

  With the experimental semantic model, a keyword in the body of an inline
  IF or in the arguments of Run Keyword and its variants, nested ones too,
  now has the documentation actions and the link to the Documentation
  Viewer in the heading of its hover, as without the semantic model.

- List the declaration after the usages in Find References ([a486486](https://github.com/robotcodedev/robotcode/commit/a4864866eee781cb9eb33d54b15878f04e58fd4d))

  In PyCharm, LSP Reference(s) did nothing on a library keyword such as `Log`
  or `Append To List` and on a variable from a Python variables file: LSP4IJ
  searched from the first location, the definition in the Python file. Find
  References now lists the usages first and the definition last, so the popup
  shows them. VS Code sorts the locations itself and shows the same list.

- Analyze again every file that imports a changed file ([3758967](https://github.com/robotcodedev/robotcode/commit/3758967b11ef93f4b034d8cd0fe79a7744d1ce46))

  After a resource file changed, some of the closed files that import it could keep their old analysis, so Find References, Rename and the unused hints went on showing their old references until such a file changed or was opened; typing in a resource file that many suites import could leave dozens of them behind. Analyzing an unchanged closed file again now also reuses its own keywords, variables and imports, which saves memory and time in the language server.

- Keep lookups and the shutdown from stalling ([ce1d06e](https://github.com/robotcodedev/robotcode/commit/ce1d06e3322a1473a3496d5c04c44ba2b54a3053))

  Find References and the unused hints check whether the language server still knows a file without holding the lock of the reference index, so opening a document while its diagnostics are renewed no longer stalls them for up to five seconds. The periodic file check reads its interval before it takes its lock, so the shutdown does not wait for the client's answer. The guide on analyzing code adds that the analysis of a file with a failed import is not cached.

- Advertise the extract-variable code action kind ([10929f2](https://github.com/robotcodedev/robotcode/commit/10929f21bd07685894ff37d72ac617e24d41f43b))

  The refactoring that extracts a variable was returned with the kind `refactor.extract.variable`, but the server advertised only `refactor.extract.function` and `refactor.surround`; the kind is now in the list, so a client that asks for it by kind gets the action.

- Keep the saved text of closed files ([9a8bb97](https://github.com/robotcodedev/robotcode/commit/9a8bb97cc0aa47bd9870ec28dc5b03f0c5f7f711))

  After a file was edited, saved and closed, the language server went back to the text from before the edit and analyzed the file and the files that use it with that old content. Closed files now keep their saved text, and problems shown for an open file now also go away without editing it once their cause is gone, for example when a missing resource file is created.

- Offer only the code action kinds an editor asks for ([235f54d](https://github.com/robotcodedev/robotcode/commit/235f54df251ba7516a587d829159c58d89a7c600))

  Editors that ask for particular kinds of code actions, such as the quick fixes for an error or the entries of the Refactor menu, now get only those, and VS Code no longer logs a warning for each refactoring it drops. Language clients that leave out the trigger kind now get the quick fixes too.

- Don't freeze PyCharm and IntelliJ when Robot files are deleted, created or renamed ([4ac008d](https://github.com/robotcodedev/robotcode/commit/4ac008da37e9e0dd048c5cf274cca1702137b3a9))

  The server registered willCreateFiles, willRenameFiles, willDeleteFiles and willSaveWaitUntil without ever returning edits. Clients wait for these answers before the file operation or the save, and LSP4IJ can deadlock while it waits (redhat-developer/lsp4ij#1694), so the registrations and their handlers stay commented out until they return edits.

- List every import statement once in Find References on an import ([f66b01c](https://github.com/robotcodedev/robotcode/commit/f66b01c2a88d6c1fc9c51af24c06b85e47b3fd80))

  Find References on a Library, Resource or Variables import now also lists an import that repeats one the file already has, directly or through a resource file, and no longer lists the line of an import with an alias twice. A repeated Resource import gets hover, Go to Definition and Find References like a repeated Library import, and the calls with a resource file's name as prefix are found in every file that imports it, not only in the one the search starts from.

- Send semantic tokens only for the names of variables ([333ae31](https://github.com/robotcodedev/robotcode/commit/333ae319094fae0c3c1f5fc169ef35af74fd4c23))

  The braces, item access, assignment marks and the Python of `${{ }}` keep the look the grammar gives them, because the token covers only the name in both the legacy path and the semantic model. Type hints get a type token where Robot Framework parses them, arguments in `[Arguments]` are parameters, and options of EXCEPT and WHILE are one control-flow token like those of FOR and VAR. In PyCharm, Go to Declaration on a variable jumps to its definition again, since the token no longer starts at the `$`.


#### Plugin

- Print the file list of discover files as TOML ([445a03c](https://github.com/robotcodedev/robotcode/commit/445a03c3d54d5dd3705bc81570539a916568cd03))

  `robotcode --format toml discover files` failed with a TypeError; the paths are now printed under `data`, since TOML needs a table at the top level.

- No blank lines between lines when paging colored output through bat ([8406afc](https://github.com/robotcodedev/robotcode/commit/8406afc881e6d01badffe265d250f8dc0711c71d))

  Colored markdown output of commands like `discover` and `results` no longer pads every line with spaces to the terminal width, so pagers that reserve columns for line numbers or a frame, such as bat, stop showing an empty line after each line.


#### PyCharm

- Show the report and the log in the preview in PyCharm's theme ([c0f92e4](https://github.com/robotcodedev/robotcode/commit/c0f92e42351b9558c8bc7fc0fbda4a2766951eb1))

  With Robot Framework 7.0 or later, the built-in preview shows the report
  and the log in PyCharm's light or dark theme and follows a change of the
  theme, also in an open tab. A theme chosen with the switch of the report
  or the log stays until PyCharm's theme changes.

- Name the run configuration in the texts about its interpreter ([9e905c4](https://github.com/robotcodedev/robotcode/commit/9e905c4110bdc5b99e05d35be99f28705b0c639f))

  When a Robot Framework run configuration has an interpreter other than the
  project's, its errors and warnings in the editor and at the start of a run now
  speak of the Python interpreter of the run configuration, for example "Robot
  Framework is not installed in the Python interpreter of the run configuration."

- Leave PyCharm's profilers out of the run marker menu ([0fda1cd](https://github.com/robotcodedev/robotcode/commit/0fda1cd9b538efe1a543a8d3ebb2e61c2b6b8d06))

  The menu of a run marker no longer offers PyCharm Professional's Profile and
  Concurrency Diagram, which Robot Framework runs don't support. Concurrency
  Diagram, which More Run/Debug and the run widget still offer, now ends with a
  message as Profile does, instead of running the test under PyCharm's debugger.

- Remove the gap above tables in the documentation ([7eb4cd3](https://github.com/robotcodedev/robotcode/commit/7eb4cd3f666189ea763fdd60ab98b46a5346ff66))

  Quick Documentation, the hover and the Ctrl+hover hint left a large gap between
  a heading and the table below it: between "Arguments:" and the arguments of a
  keyword, and between the name of a library or resource file and its version and
  scope. The pictures of the documentation in the PyCharm guide and on the home
  page show it without the gap.

- Show the Ctrl+hover documentation without extra gaps ([83b3b44](https://github.com/robotcodedev/robotcode/commit/83b3b44a79183d6f570fe5dee6f9f24573d6b387))

  In PyCharm, the documentation that appears when Ctrl is held over a
  keyword or an import no longer shows a large empty area in front of
  tables and an extra empty line after each heading and paragraph. It is
  spaced as in Quick Documentation.

- Find the usages of a resource file from its import ([cc1915c](https://github.com/robotcodedev/robotcode/commit/cc1915c0dec58552835432a66e3c25552974c8c4))

  Find Usages and Show Usages on a resource import now list where the
  resource file is imported and where its keywords are called with its name
  in front; before, they found nothing. In a Robot Framework file, both now
  search for the name at the caret, as VS Code does.

- Find the usages of library keywords called with a prefix ([52a4e81](https://github.com/robotcodedev/robotcode/commit/52a4e814bcfd0ed40171434911c1be7dbf7470d6))

  Find Usages and Show Usages on the keyword of a call such as `BuiltIn.Log`
  or `Collections.Append To List` searched the library instead, and Show
  Usages jumped to it. They now find the usages of the keyword, as on a call
  without a prefix.

- Underline only the name under the mouse on Ctrl+hover ([f64d4c2](https://github.com/robotcodedev/robotcode/commit/f64d4c2b7d8167982ca7f29d6fb805b4605fa18c))

  Holding Ctrl over a keyword call with a library or resource prefix in a
  Robot Framework file, such as `BuiltIn.Log`, now underlines only the
  prefix or the keyword under the mouse, and the hint describes the target
  of that part. A variable with a type, such as `${arg2: str}`, is
  underlined without the type.

- Name the kind of a place in Show Usages for Robot files ([e1c53fc](https://github.com/robotcodedev/robotcode/commit/e1c53fca51a1ad9e535a230885c5ca21c3ba458a))

  Show Usages and Find Usages titled a keyword or variable in a Robot
  Framework file "LSP Usage Triggered Psi Element", and a local variable
  or keyword argument "LSP Symbol ${". They now name its kind and name,
  such as "Keyword Open Shop As", "Argument user" or "Variable greeting".
  The pictures of Show Usages in the PyCharm guide show the new title.

- Show only the preview in the preview tab of a report or log ([5b2abd3](https://github.com/robotcodedev/robotcode/commit/5b2abd332ff32a850cfaa077adbfc780988b9741))

  A plugin whose editor opens every binary file, such as a hex viewer, no
  longer adds a tab of its own next to the preview of a report or a log;
  the preview's file type also gets a display name of its own.

- Keep LSP4IJ's language server suggestion off the preview tab ([5f16aa6](https://github.com/robotcodedev/robotcode/commit/5f16aa613f8ac7b1f4694c87ffc8f37ebea1e8c1))

  The preview tab of a report or a log no longer shows LSP4IJ's bar
  "*.html files are supported by language servers (LSP4IJ)" with an offer
  to install the Harper language server: the IDE no longer takes the tab
  for a plain text file, and its title, icon and page stay as they were.

- Select the server log and polish small UI details ([397feb8](https://github.com/robotcodedev/robotcode/commit/397feb8b0c4838fd5e0eb06061afd72efde7cdb0))

  Show Language Server Log now selects the running RobotCode language server and its Logs tab in the Language Servers tool window instead of only opening the window. The Select Configuration Profiles dialog keeps a gap between a profile's name and its description, Find Action no longer lists the internal action that RobotCode's code actions use, and the help text of Open output after run names Open output target instead of an external browser.

- Ask for an IDE restart when installing or updating the plugin ([84c89ae](https://github.com/robotcodedev/robotcode/commit/84c89aec24142563f117aee8a68ef6d19420c924))

  Installing, updating and uninstalling RobotCode now take effect after a restart of the IDE, which asks for it. Before, the IDE tried to swap RobotCode while running, failed to unload it, and was left without RobotCode's file types and features until the next restart.

- Show no pip command in the interpreter banner ([69769c8](https://github.com/robotcodedev/robotcode/commit/69769c8a95facf0dad263a50bae7d8f53191ec87))

  The banner for a project interpreter without a usable Robot Framework showed a pip command that installs or upgrades it, although which tool and which version a project uses is the project's decision; it now names the problem and the requirement only, as the VS Code extension does.

- Don't freeze the IDE while running and debugging ([8741729](https://github.com/robotcodedev/robotcode/commit/8741729f7165c2b85820d59f58fda18acac70660))

  Run and Debug no longer freeze the IDE while the plugin connects to the RobotCode debugger, and stepping, changing breakpoints, Set Value, loading more list items and evaluating keywords no longer block it either. A debugger that does not accept the connection within 15 seconds ends the run with a message in its console instead of IDE errors. Watches now work as in VS Code: they are evaluated as expressions, run a keyword only when they start with `! `, and show `<undefined>` for unknown variables; evaluation errors show the debugger's message.

- End runs gracefully on Stop, also while paused ([0e187f6](https://github.com/robotcodedev/robotcode/commit/0e187f6911e35bc9f0f3b80be3e93fe82443afe2))

  Stop in PyCharm and IntelliJ IDEA now asks the RobotCode debugger to end the run, so a run paused at a breakpoint ends with a single Stop and still writes its output, log and report, and the output of its teardowns stays under the right test. Every run also gets its own debugger port, so runs started at the same time no longer share one.

- Make breakpoints take effect as the editor shows them ([b1231cc](https://github.com/robotcodedev/robotcode/commit/b1231cc51008f9f0142d06928c22f2f5db82c5d3))

  Disabling, muting, removing and moving a Robot Framework breakpoint now take effect at once in a running debug session, also for the last breakpoint of a file, Run to Cursor always continues to its target line, and breakpoints are in effect from the first keyword. The single "Any Exception" breakpoint, which never reached the debugger and could leave a run hanging, is replaced by Uncaught Failed Keywords, Failed Keywords, Failed Tests and Failed Suites, each with its own suspend policy.

- Color keyword calls like function calls ([24bad31](https://github.com/robotcodedev/robotcode/commit/24bad314bc05b698093a1dba1ba6fa310e82b3ee))

  Keyword calls in Robot Framework files now take the color scheme's Function call color instead of its Function declaration color, so they look like calls in the IDE's other languages, while test case and keyword names keep the declaration color. In schemes without a function call color, keyword calls are plain text unless the Keyword call setting on the Robot Framework color page gives them a color.

- Show suite teardown failures and keep the console in order ([4de10ee](https://github.com/robotcodedev/robotcode/commit/4de10eebb8d5d7f5a95bd23f63eea7045724c290))

  Tests whose suite teardown fails now show as failed, or as skipped when the teardown is skipped, in the results tree, the status line and the gutter. The run console shows the output in the order Robot Framework wrote it, with each test's output under its node and the lines between tests under their suite, and a run no longer leaves a thread behind.

- Keep language server output out of the IDE errors and end failed starts ([c297939](https://github.com/robotcodedev/robotcode/commit/c297939ed82f53994b794ff74404b55b9649d187))

  Lines the language server writes no longer raise IDE errors, and large output no longer stalls it; both appear in the Language Servers log. The plugin accepts the server only on 127.0.0.1, a server that exits before it connects fails the start with its exit code instead of hanging, and RobotCode does not start it again until it is restarted. Interpreters older than Python 3.10 are rejected with a message that names the requirement, Restart picks up an interpreter fixed outside the IDE, and Clear Cache and Restart works in the background and while the server is stopped.

- Show your own .resource file templates in the New Robot Framework File dialog ([aa06f60](https://github.com/robotcodedev/robotcode/commit/aa06f607ba74fa26b8e8a038d6bf32ca01e6bba6))

  The resource file type reported robot as its default extension, so the dialog matched templates with the resource extension against the wrong type and left them out. Templates for .resource files you created under File and Code Templates now appear next to the .robot ones.

- No error when the language server is stopped before it has connected ([3cb9fc0](https://github.com/robotcodedev/robotcode/commit/3cb9fc0e6ec8b34add94445adeb9b6859d223d3e))

  Closing a project or quitting the IDE while the language server was still starting reported a NullPointerException blamed on RobotCode. A restart during the start failed the same way without a message and left a thread waiting and a port open. Stopping now works at any point of the start.

- Use the platform's element type helper for semantic highlighting ([7b06004](https://github.com/robotcodedev/robotcode/commit/7b06004fbdb90c057a28a69fec21726b239a79c6))

  The check for which elements get semantic highlighting imported its element type helper from the TOML plugin, which the plugin does not declare as a dependency. It now uses the platform's own helper, so semantic highlighting no longer relies on classes of the TOML plugin.

- Keep jumping to the keyword in a call with a library or resource prefix ([ec80cc8](https://github.com/robotcodedev/robotcode/commit/ec80cc8a5067c57c2638849e9d61cae1aa396511))

  Go to Declaration after the dot of a call such as `common.Start Case` worked once and then led to the Resource import, because LSP4IJ covered the whole call with a token of its own after the first jump. The language server's tokens for the prefix and the keyword now stay, so every jump lands on the keyword.

- Offer Robot Framework breakpoints only in Robot Framework files ([b3487da](https://github.com/robotcodedev/robotcode/commit/b3487da13307ef8b52eb1abb66a6bca5ffda2ec1))

  A click in the gutter of another file, such as a C# file in Rider or a text or TOML file, creates that language's breakpoint again, or none, instead of a Robot Framework breakpoint that no debugger handles.

- Color type hints, named arguments, namespaces and operators as what they are ([59c3f69](https://github.com/robotcodedev/robotcode/commit/59c3f6957fd7af59a79d594f0968d6b168e79d19))

  These tokens correct what the grammar shows at their place, so their colours are drawn even where the scheme leaves them at plain text, instead of the colour of the grammar's category. Variables and parameters still keep the grammar look in that case. Parameters and type hints have colour settings of their own, and the settings page shows them in the colours the editor uses.

- Take highlighting colors from the active color scheme ([a47bc08](https://github.com/robotcodedev/robotcode/commit/a47bc08e61feb84d0c79b3fe99b913f004c43258))

  Variables and keyword calls now get the colors the active color scheme defines for fields and function declarations instead of plain text, operators and numbers in conditions get their own colors, and semantic highlighting only adds what the scheme defines instead of turning namespaces, named arguments and variable names into plain text. The plugin no longer ships its own colors for Darcula, Dark and Light; colors set on the Robot Framework color settings page are kept.

- Highlight test case and keyword names ([47f8f3b](https://github.com/robotcodedev/robotcode/commit/47f8f3b4fbedc2d8a6f1c547b58876e621642669))

  PyCharm and IntelliJ IDEA did not recognize test case and keyword names in the syntax highlighting, so the "Test case name" and "Keyword name" colors only showed once the language server's semantic highlighting arrived, clicking a name in the color settings preview did not select its entry, and escapes and embedded arguments in names were not highlighted. Highlighting in VS Code is unchanged.

- Stop using internal EditorBundle API for tab command name ([d9cbced](https://github.com/robotcodedev/robotcode/commit/d9cbcedbacb3122fd75236b23ebb8c2f22dced7a))

  The plugin verifier flagged usage of the internal com.intellij.openapi.editor.EditorBundle
  class and its message() method when setting the undo/redo command name for tab insertion.
  JetBrains rejects plugins that use internal platform APIs.

  Use the plugin's own RobotCodeBundle with a new command.typing.name key instead. The
  displayed command name ("Typing") is unchanged.


#### REPL

- End repl-server without a traceback on Python 3.11 ([cb2693d](https://github.com/robotcodedev/robotcode/commit/cb2693d310c3c1b0709d4bbd338b1aa3b4058b86))

  On Python 3.11, `robotcode repl-server` could print a Python traceback after its own error message when the session ended, for example with an invalid robot.toml. It now ends with the error message alone.

- End a robot-debug run without the debugger on Ctrl-C like a robot run ([4c1dcae](https://github.com/robotcodedev/robotcode/commit/4c1dcae74b8bac19daf407e7939f56e6162ff21c))

  With `--no-debugger-attached` or after `.detach`, Ctrl-C only failed the keyword that ran, and the run went on with the next tests; now the test fails with `Execution terminated by signal`, the remaining tests don't run, and a second Ctrl-C ends the process, as with `robotcode robot`.

- Let Ctrl-C resume a robot-debug stop with the plain backend ([3591db9](https://github.com/robotcodedev/robotcode/commit/3591db927264f5fdacf085f0b8a5a9d0d4cab086))

  With `--backend plain`, Ctrl-C at the `(rdb)` prompt did nothing; it now resumes the run as with the default backend, and at the `>>>` prompt it drops an unfinished block.

- End repl, repl-server and robot-debug on SIGTERM ([9e27f8e](https://github.com/robotcodedev/robotcode/commit/9e27f8e3366aaa287bcfd32b4812c90552495d73))

  SIGTERM, as sent by kill or a process manager, now ends a repl or repl-server session with exit code 253, also while it waits for input or for a client, and robot-debug ends its run like Robot Framework, also while it waits at a stop; a second SIGTERM ends them at once. repl-server also reports an invalid robot.toml with exit code 252 instead of showing a traceback and running on.

- Report settings typed at the REPL prompt ([3369603](https://github.com/robotcodedev/robotcode/commit/33696033b59b7e6aefbb63c1990dcf18274c493f))

  A setting such as `[Tags]` or `[Setup]` typed at the prompt was silently ignored, and `[Arguments]` was reported as not allowed with tests or tasks. The REPL now reports every setting as `Setting '<name>' is not allowed in the REPL.`, also at a `robot-debug` stop and in the VS Code REPL.

- Give every keyword its anchor in the JSON of robotcode doc lib ([bde6f41](https://github.com/robotcodedev/robotcode/commit/bde6f412a425bd20bb9597df37e1ca6e9c104ef0))

  A keyword with a variable in its name, such as `Open ${url} In Browser`, got an empty `anchor`, and so did every keyword sorted after it, because the page writes the variable as inline code and the heading no longer matched the name.

- Show links in the documentation viewer without a VT console ([c1cf903](https://github.com/robotcodedev/robotcode/commit/c1cf903518e55b72c94ca8b51b750877f7c70332))

  On Windows without a console that supports VT sequences, links in the viewer of `.doc`, `.kw` and `robotcode doc browse` could not be followed, because the rendering left them out for a legacy console the viewer never writes to.

- Report invalid input instead of silently dropping it ([bd51550](https://github.com/robotcodedev/robotcode/commit/bd51550c9c3738a239d80cf99d9fac9fe212c530))

  A script file with a parse error was skipped completely, input that ended inside an unfinished block was discarded at the end of the input, and a complete but invalid block made the REPL wait for more lines and swallow the valid ones after it, mostly without any message. Invalid input now runs like a `robot` test body: the statements before it run, it fails with Robot Framework's message when execution reaches it, and only an unfinished block waits for more lines. A line starting with `...` no longer runs as a statement of its own.

- Make `.vars --user` work at a debugger stop ([8db2266](https://github.com/robotcodedev/robotcode/commit/8db22667d8741830c2ec96b16d0ab88871abe8e3))

  `.vars --user` was ignored at a debugger stop, kept Robot Framework's constant variables such as `${True}` and `${/}` as well as the REPL's result variable `${_}`, and hid user variables that start like a built-in one, such as `${SUITE_VAR}`. It now hides exactly the variables Robot Framework sets itself and `${_}`, at the prompt and in every scope at a stop.

- Resolve a relative `--source` against the start directory ([19f6e07](https://github.com/robotcodedev/robotcode/commit/19f6e0795f60a48068a3ad7168ea66e278583909))

  `robotcode repl --source tests/spike.robot` resolved the relative path
  against the project root instead of the directory the REPL was started
  from, unlike the FILES arguments. `${CURDIR}` and, on Robot Framework 7.4,
  relative imports then pointed at the wrong directory, and `${SUITE SOURCE}`
  as well as the source in `output.xml` kept the unresolved relative path.

- Write output files on Robot Framework 5.0 and 6.0 again ([d712f32](https://github.com/robotcodedev/robotcode/commit/d712f32d326ff0088dbf83103a56c92192a9d0d2))

  Since 2.6.0, `robotcode repl -o output.xml` (and `robotcode repl-server`
  with an output file) crashed on Robot Framework 5.0 and 6.0 with a
  `TypeError` about a `PosixPath`/`WindowsPath` object before the prompt
  opened, leaving an `output.xml` without any results and no log, report or
  xunit file.

  On these versions `${SUITE SOURCE}` in the session also was a path object
  instead of a string, so string keywords like `Should Contain` failed on
  it, and listeners received path objects as `source` for the suite and for
  every keyword entered at the prompt. All of this works again; Robot
  Framework 6.1 and newer are unaffected.

- Ignore test selection, dry-run, set-tag and skip options from profiles ([ef18ed5](https://github.com/robotcodedev/robotcode/commit/ef18ed59d438f1a8f9f7bd3b44dc13e6372ef1eb))

  `robotcode repl` and the notebook kernel (`robotcode repl-server`) run the
  whole session as a single internal test. Settings from `robot.toml` meant
  for real suites could keep that test from running:

  - `includes`, `excludes`, `suites`, `tests`, `tasks`, `re-run-failed` and
    `re-run-failed-suites` deselected it, so the REPL stopped with an error
    such as "Suite ... contains no tests matching ..." or, with
    `run-empty-suite`, exited without starting
  - `set-tag` with `robot:skip`/`robot:exclude` or `skip` patterns skipped it
  - `dry-run` opened a prompt that executed nothing you typed

  The REPL now ignores these settings together with `skip-on-failure` and
  `skip-teardown-on-exit`, no matter whether they come from a profile, the
  top level of `robot.toml`, `default-profiles`, `args`, argument files or
  `ROBOT_OPTIONS`. Other profile settings, such as variables and
  `python-path`, still apply. Run `robotcode --verbose repl` to see which
  options were ignored.


#### Robot

- Analyze a cached file again when its imports or environment variables changed ([8b23db9](https://github.com/robotcodedev/robotcode/commit/8b23db973da12f3c0f38f0e74997461c8d5e9c58))

  The analysis of a file is no longer taken from the cache when one of its
  imports now finds another file or none, for example after a change of the
  Python path or of an environment variable in an import path, or when an
  environment variable the file uses has been set or unset since. Such files,
  also closed ones in the editor, kept their old diagnostics until they changed.

- Keep the keyword documentation of a cached semantic model ([27535f5](https://github.com/robotcodedev/robotcode/commit/27535f5385b754ba49aed4d4220854b6cc214414))

  With the experimental semantic model, a file that RobotCode restored from
  its analysis cache after a restart and that was then opened without changes
  had no documentation actions, no link in the hover's heading and no
  documentation links in the signature help for BuiltIn keywords until it was
  edited. The cached analysis now refers to the keywords of the restored file.

- Show no library scope for variable files ([36059ad](https://github.com/robotcodedev/robotcode/commit/36059adbd475eb0390dbeb271d922dd2f1533209))

  The hover of a variable file import no longer lists "Library Scope:
  GLOBAL", because Robot Framework knows no scope for variable files.
  Resource and suite files keep it, as Robot Framework's Libdoc shows it
  for them too.

- Count EXCEPT AS and item assignments as uses of their variable ([fe3eb81](https://github.com/robotcodedev/robotcode/commit/fe3eb8193fd213b9f4662e47e61c3783d3bcae8d))

  EXCEPT AS with the name of an argument or local variable and, on Robot
  Framework 6.1 and newer, item assignments such as ${items}[0]= now refer
  to the variable they set again, so Find References lists them and Rename
  renames them. Variables in the index of an item assignment count as uses,
  and an item assignment to an unknown variable or with an unknown variable
  in its index reports it as not found, as Robot Framework fails there.

- Convert reStructuredText documentation without the writer_name that Docutils deprecates ([d5520c9](https://github.com/robotcodedev/robotcode/commit/d5520c93c43e8dec0d2e2878d16227efd354888e))

  Docutils 0.22 and newer warn that the `writer_name` argument will be removed in Docutils 2.0. The documentation is now converted with an instance of the HTML5 writer, which every Docutils version takes and which renders the same HTML as before, checked with Docutils 0.16, 0.18, 0.21 and 0.23.

- Show no traceback for an import that times out or ends early ([f28308d](https://github.com/robotcodedev/robotcode/commit/f28308ddf3df9d1763bc2155179efa17ab3faaa6))

  When a library or variables file took longer than the load timeout or ended the process while it was imported, `robotcode analyze code` printed RobotCode's own tracebacks next to the diagnostics that already report this; now only the diagnostics are shown.

- Let a nearer robotcode: comment without a code list win ([2357745](https://github.com/robotcodedev/robotcode/commit/235774540ce91d388672ceec99e5e4bfdf8441ed))

  A `# robotcode: reset`, `ignore` or `error` without a code list lost against every comment that named the code, even one further up the file, so a later `# robotcode: reset` did not end an earlier `ignore[variable-not-found]`. Now the nearest comment wins, with or without codes, and within one comment the rightmost action, as the documentation describes.

- Apply an indented robotcode: comment that follows a nested block ([859fb51](https://github.com/robotcodedev/robotcode/commit/859fb51bed5ce32c53f9f024ec02cd694a86ce97))

  An indented `# robotcode:` comment that came after an IF, FOR or other nested block in the same test or keyword had no effect; it now applies from its line to the end of that test or keyword, like one placed before the nested block.

- Keep the code list of warning and information in robotcode: comments ([c0cd7f3](https://github.com/robotcodedev/robotcode/commit/c0cd7f387f7e40f92faa5d15650b01c150c000a5))

  A `# robotcode:` comment with `warning[...]` or `information[...]` changed every diagnostic of its line or scope instead of only the listed codes; the short forms `warn[...]` and `info[...]` were not affected.

- Accept environment variables with variables inside variable names ([9a0b840](https://github.com/robotcodedev/robotcode/commit/9a0b8407eb7adbcef4fe82267de2fb3e4d699cae))

  Robot Framework resolves the variables inside `%{...}` before it looks the environment variable up, so a name like `${X_%{ENV_${S}}}` passes there. RobotCode reported an error, defined a variable under the unresolved name or dropped such a reference without a diagnostic; it now reports these names and references as not statically resolvable.

- Stop reporting missing arguments for the keyword named in `Keyword Should Exist` ([8c7b2fe](https://github.com/robotcodedev/robotcode/commit/8c7b2fe3e8cf34aef03114af13b5fbab4dc212b6))

  With the semantic model on Robot Framework 7.4 and newer, a keyword name passed to `Keyword Should Exist` was analyzed like a call, so `Keyword Should Exist    Log` reported that `Log` got no arguments and a following `msg` argument was counted for the named keyword.

- Check each library and variable file of a cached namespace against its own file ([be00c31](https://github.com/robotcodedev/robotcode/commit/be00c317972bef66e141dc84409284f987206c39))

  A namespace in the namespace disk cache recorded its library and variable files by their import name, so of two files with the same name from different folders, such as vars.py and the sub/vars.py of a resource file, only one was checked: after a restart a change of the other one brought back the old analysis, and a namespace whose files had not changed could be analyzed again instead of restored. Each file is now a dependency of its own and is checked against its current state.

- Keep the references to imports of a namespace restored from the cache ([9a6c62f](https://github.com/robotcodedev/robotcode/commit/9a6c62f08923a10834c10b9be540dc3cbed3d147))

  A namespace restored from the namespace disk cache gave the references of an import that repeats an implicit or a resource file's import, such as an explicit Library BuiltIn or a library imported both by a resource file and directly, to that other import, or lost them when the arguments differed. Features that read the analysis of closed files now get the same references to imports as for a fresh analysis.

- List subsections in the table of contents of library documentation ([3d743de](https://github.com/robotcodedev/robotcode/commit/3d743de7e7c7f773cac12373382c8dfcdd70d679))

  A `%TOC%` in Robot Framework format listed only the top-level sections; it now nests their subsections, as Libdoc of Robot Framework 7.5 does. In both formats the table of contents takes the two highest heading levels the documentation uses, so a Markdown documentation whose sections start at `##` gets a well-formed nested list too.

- Keep every code of an action that repeats in a robotcode: comment ([d73a86f](https://github.com/robotcodedev/robotcode/commit/d73a86f8c91079618b84a978cfc8afa23cc1db87))

  With `# robotcode: ignore[a] warn[b] ignore[c]` the second ignore replaced the first, so `a` was reported again. Each code now belongs to the rightmost action that names it.

- Keep two libraries of one module apart ([65f13b6](https://github.com/robotcodedev/robotcode/commit/65f13b66b851694e604530d6ec459ac76ace9723))

  When two classes of one Python module were imported as libraries, such as `mylibs.LoginLib` and `mylibs.OrderLib`, the hover of the second import showed the first library, Go to Definition jumped to the first import, and highlights and references mixed both imports. Imports of the same library, also with other arguments, still belong together.

- Show code blocks in Markdown documentation as written ([1319117](https://github.com/robotcodedev/robotcode/commit/1319117bb3dfd3d4af41b243a7e9da62ff6ee2d7))

  In hovers, the Documentation Viewer and `robotcode doc`, a reference such as `[Setup]` or `list[int]` in a code block inside a block quote or admonition became a link, and on the documentation page a variable in such a block became inline code. Indented code blocks and HTML blocks got these links also outside of block quotes.

- Keep the URLs of keyword-local reference definitions on documentation pages ([1262ecf](https://github.com/robotcodedev/robotcode/commit/1262ecffdb061472e0dcd677d4e4a20014df436d))

  When two documentations on one page define the same reference label with different URLs, such as `[1]` in the BuiltIn documentation of Robot Framework 7.5, the later links went to the URL of the first definition. The page of `robotcode doc lib` and the REPL's `.doc` now gives such a label another name in the later documentation.

- Stop library loads at the timeout and check every set of import arguments ([ffe53e9](https://github.com/robotcodedev/robotcode/commit/ffe53e90e743b2de2ce6db7578487b4322e6bdf9))

  Loading a library or variable file now really ends when load-library-timeout expires, and the timeout is reported as LibraryTimeoutError or VariablesTimeoutError and kept until a file changes instead of blocking every analysis again. The disk cache stores one entry per set of import arguments, so changed or wrong arguments show their errors without clearing the cache. An import that ends early, for example through sys.exit(), is reported as LibraryExitError instead of ending the analysis, and an import whose keywords come from loading the library without its arguments gets the information LibraryLoadedWithoutArguments.

- Report variables nested in environment variables with the semantic model ([2da6565](https://github.com/robotcodedev/robotcode/commit/2da6565dec6423e9c28bad60fa3c85811e99988f))

  With the semantic model enabled, undefined variables inside the name or the default of `%{...}` were not reported and variables used only there were reported as unused, although Robot Framework resolves them before the lookup.

- Accept an empty default in environment variables ([cb2f96b](https://github.com/robotcodedev/robotcode/commit/cb2f96bd0697cbe115a6776a33da58500b6554b0))

  `%{NAME=}` was reported as EnvironmentVariableNotFound when NAME is not set, although Robot Framework resolves it to an empty string.

- Don't fail when the given paths are on different drives ([ea4bfae](https://github.com/robotcodedev/robotcode/commit/ea4bfaefb767344caf56621438ad46784b66b295))

  On Windows, a command like `robotcode libdoc MyLibrary D:\out\MyLibrary.html`
  failed with `max() iterable argument is empty` when the output folder was on
  another drive than the working directory. The current folder is used as the
  project root then.


#### RobotCode

- Use the singular for a count of one ([fce2108](https://github.com/robotcodedev/robotcode/commit/fce21084873cf5eae8088f2e6a22d2555cfa8d58))

  The references CodeLens now shows "1 reference" instead of "1 references". The REPL's .save summary and breakpoint list, the cache list and clear commands, the verbose file counts of analyze code and the timeout message for loading a library use the singular for one in the same way.

- Exit with 252 when robotcode itself reports an error ([6c22bf6](https://github.com/robotcodedev/robotcode/commit/6c22bf67e9e0550040f22ec0ae100067635464a1))

  Commands that run Robot Framework or wrap one of its tools exited with 1 or 2 when RobotCode itself reported an error, such as a wrapper that doesn't start, an invalid `robot.toml` or an unknown option, so a CI job couldn't tell a broken setup from failed tests. They now exit with Robot Framework's 252 for invalid data or command line options, and the CLI reference lists the exit codes of these commands.

- Honor --dry in debug and repl-server ([3af9aff](https://github.com/robotcodedev/robotcode/commit/3af9aff6620960f8848499bfcc2ed32fea674876))

  With `--dry`, `debug` still started the debug adapter and waited for a client, and `repl-server` printed the dry-run output but kept its server running, so both hung. Now they start nothing and print what robot would run, like the other commands.

- Don't run the wrapper on a dry run ([f8b6d5c](https://github.com/robotcodedev/robotcode/commit/f8b6d5c3716dd0d76653f8fbee8684814929071f))

  `--dry` still started the configured wrapper, so its setup and teardown brought real environments up and down; a dry run now only names the wrapper. Profile errors such as an unknown profile name are also no longer printed twice by the commands that run Robot Framework.


#### Runner

- Don't double the backslashes in results log links with spaces ([15cdb24](https://github.com/robotcodedev/robotcode/commit/15cdb248b2e2d4418748ce32bd04f6115b4428ec))

  On Windows, with html-to-markdown installed, `robotcode results log` showed
  links to files outside the output directory with doubled backslashes when the
  path contains a space.

- Take the wrapper from the configuration of the command ([aee1e50](https://github.com/robotcodedev/robotcode/commit/aee1e505428ef82a3a549e10914971a1fcf71d7a))

  Commands that run Robot Framework take the wrapper from the configuration
  they use, found from their paths, and load that configuration once. A run
  of a project's tests from the root of a monorepo now runs under that
  project's wrapper, and -v shows the loading once. A configuration that
  cannot be loaded starts no wrapper, also not one given with --wrapper.

- Resolve encoded and file: links and videos in results log ([85ddc4c](https://github.com/robotcodedev/robotcode/commit/85ddc4c6a8372c4daf5af4635aa9dea5ed460a50))

  robotcode results log now finds files whose names are URL-encoded, such as
  screenshots named after a test, follows the file: links OperatingSystem logs
  for files in the output directory, and extracts the videos Browser records.
  Linked screenshots no longer get an extra skipped entry, embedded files keep
  the name of their download attribute, and every message that links an
  extracted file points to the copy.

- Keep screenshot messages when an old html-to-markdown is installed ([1d719bc](https://github.com/robotcodedev/robotcode/commit/1d719bcf1c0745136f5147d5a9e0bc01277d8202))

  With html-to-markdown older than 3.18 installed, robotcode results log showed
  the screenshot messages of SeleniumLibrary and Browser as empty lines, and
  --extract left its directory empty. Such versions are now ignored in favour of
  the built-in converter, and the html extra requires html-to-markdown 3.18.

- Discover tests without a line number ([9f3077d](https://github.com/robotcodedev/robotcode/commit/9f3077d8adb868db8bbcb1dc34a08b6a0cfad275))

  `robotcode discover` no longer fails as a whole when a custom parser or
  a pre-run modifier creates a test without a line number, so VS Code and
  PyCharm show the tests of such a project. Runs report such a test, its
  result and its messages under the ID of its discovery, and PyCharm
  counts it in the test count of the run.

- Pass a positional path outside the project root as an absolute path ([0c6218f](https://github.com/robotcodedev/robotcode/commit/0c6218f71d215d5692730e73ce06e33700b765ff))

  Positional paths of `robot`, `robot-debug` and `discover` are relative to the working directory and are rewritten relative to the project root the run changes into. For a path outside that root, for example `robotcode --root /tmp/repro discover all .` run from `/tmp`, the rewrite failed with a traceback (`ValueError` from `relative_to`); such a path is now passed on as an absolute path, which stays valid after the change of directory.

- Reject an invalid --search-regex before reading the result file ([9b93a00](https://github.com/robotcodedev/robotcode/commit/9b93a00875b7954ce5aa24d88ff04408e4515b05))

  The `results` subcommands read the whole result file before they reported an invalid `--search-regex` pattern, and with a wrong path they reported the missing file instead; now the pattern is checked first.

- Let results --search find a test by its own message ([6c5c87f](https://github.com/robotcodedev/robotcode/commit/6c5c87f0e1836686a110be71243940f2510ecb60))

  `--search` and `--search-regex` looked at the messages a test's keywords logged, but not at the message of the test itself, so a test whose message came from a failing teardown ("Teardown failed: …") was not found; now that message counts too.

- List discover suites without their nested suites and tests ([3a5f927](https://github.com/robotcodedev/robotcode/commit/3a5f927024003d273ae93f16e35747c5312a67f2))

  In JSON and TOML, `robotcode discover suites` repeated every suite's whole subtree, tests included, inside each parent suite; now it is the flat list of suites the documentation describes.

- Resolve the paths of discover files from the working directory ([66e973b](https://github.com/robotcodedev/robotcode/commit/66e973bb131ae37495b83284ccf8f9107000b9d6))

  `robotcode discover files` started in a subfolder took relative paths from the project root, so it found nothing or listed a folder of the same name in the root; paths from the command line now count from the folder the command was started in, as with `discover tests`.

- Count each message of a run once in results ([8951e5e](https://github.com/robotcodedev/robotcode/commit/8951e5e922e431d176fa352a8fded54be31779b8))

  Robot Framework copies every warning and error logged in a test into the `<errors>` section of output.xml, so `messagesCount` counted them twice, and `executionMessagesCount` and `log --execution-messages` included them although they are meant for messages from outside the tests. The copies are now recognised the way Robot Framework links them, by message, level and timestamp.

- Say that summary --failed lists the failed tests below the counts ([203ee86](https://github.com/robotcodedev/robotcode/commit/203ee86202f4eaeedc4ec422e14fa07b6c680dbf))

  The help of `results summary` said the failed tests come above the counts, but the output lists them below. The CLI reference says the same now.

- List the files of discover files in the order of the given paths ([68af6ee](https://github.com/robotcodedev/robotcode/commit/68af6ee0a939ed4921ca30b9c14a1b243445df10))

  The paths were kept in a set, so with several paths the files came out in a different order on every run. They now keep the order of the paths, still without duplicates.

- Leave the source of a suite without its own file empty in discover ([f02c49a](https://github.com/robotcodedev/robotcode/commit/f02c49ae03988498498f01c9a09910d9e3b59c7d))

  A top suite built from several files, for example from a robot.toml that lists files in `paths`, has no source. discover reported the text "None" as its source in JSON and as its path in the text output; the field is now left out.

- Show the shared robot options in a fixed order ([d0d4892](https://github.com/robotcodedev/robotcode/commit/d0d48923d86589232deaafd40a2302354b158bbd))

  `--by-longname`, `--exclude-by-longname` and `--version` of `robot`, `robot-debug` and the `discover` commands appeared in `--help` and in the CLI reference in an order that could differ from one environment to the next.

- Leave the installed Robot Framework version out of result file errors ([1a3c50b](https://github.com/robotcodedev/robotcode/commit/1a3c50b9260e48f06d8046674319a2923132aa35))

  The error for a JSON result file on Robot Framework older than 7.0 printed the installed version as `6.1.1.None.None.None`. It and the hint for result files with test metadata now only name the Robot Framework version that is needed to read the file.


#### TextMate

- Highlight Robot Framework code in files, Markdown and the REPL as Robot Framework reads it ([8e99176](https://github.com/robotcodedev/robotcode/commit/8e99176df9cb1954cbe1db551282188aaadd1e3a))

  Environment variables no longer swallow the rest of their row, and comments right after a keyword or marker, RETURN, the FOR separators, item access such as ${LIST}[0], AS in EXCEPT and Library, and default values in [Arguments] are highlighted correctly in VS Code, IntelliJ, Markdown views and on the documentation site. REPL scripts and notebook cells now use the same grammar, so multiple assignments, nested variables, BREAK, CONTINUE and GROUP are highlighted there too.


#### VS Code

- Shorten the description of the Documentation Viewer's openLocation setting ([db4a080](https://github.com/robotcodedev/robotcode/commit/db4a080e7b975c468b2daa94f61a83225ae47c19))

  It now only says where a new viewer opens: beside the active editor or in the active editor group.

- Fill the Keywords view once the language server has started ([599ad73](https://github.com/robotcodedev/robotcode/commit/599ad73808c54bc7ddf77703acd7d831316004fc))

  When VS Code restores an open Robot Framework file at startup, the Keywords
  view shows its keywords as soon as the language server runs, without closing
  and reopening the file. Canceled requests of the view no longer show up as
  errors in RobotCode's output (#644).

- Show only the run's command line in a reused terminal's sticky scroll ([f3966fe](https://github.com/robotcodedev/robotcode/commit/f3966fea854ee103dd3004f79ad5389501d08301))

  When a run terminal is reused, VS Code's sticky scroll shows only the command
  line of the current run. Copy Output of a run ends with the line about the
  terminal's reuse.

- Keep the terminal in front at the first run of a window ([f15c1a5](https://github.com/robotcodedev/robotcode/commit/f15c1a53170271fef7745bf4fc7a7f1ac135e173))

  When a run writes its output to a terminal, VS Code no longer switches the
  panel to the Debug Console at the first run of a window. A value of
  debug.internalConsoleOptions in the settings or internalConsoleOptions in a
  launch configuration still decides when the Debug Console opens.

- Report environment problems at startup only if they remain ([b0cbfaa](https://github.com/robotcodedev/robotcode/commit/b0cbfaad340bc8cfed309df77a3515627f187eae))

  While VS Code starts or a folder is added, the Python extension may need
  some seconds to select the folder's environment. In these first 15 seconds
  RobotCode shows no environment message and no hint about a missing
  environment in the Testing view, the language status shows that it is
  still checking, and a problem that remains shows right after.

- Mark only the item with the problem in the language status ([e31651c](https://github.com/robotcodedev/robotcode/commit/e31651c8e8471718c6e1efd955f8288a5010156f))

  When the Python environment has no Robot Framework, only the Robot Framework
  item of the language status is shown as an error; the Python item turns red
  only when the interpreter has a problem. The Robot Framework item shows the
  version RobotCode's environment check found while the language server is
  still starting, and "unknown" instead of "not installed" when the interpreter
  cannot be used.

- Let the Documentation Viewer wait for the Python environment ([9f76cc5](https://github.com/robotcodedev/robotcode/commit/9f76cc595ab7502aad8058ad782c901a5f78b0bf))

  After a restart, a Documentation Viewer no longer fails with an error and a
  Retry button while the Python extension is still selecting the folder's
  environment. It shows the page it showed last, says that it waits, and loads
  the page by itself once the environment is usable; only a problem that lasts
  30 seconds shows as an error. A viewer also follows when another environment
  is selected for its folder.

- Keep the test tree in step with changed files ([b257df0](https://github.com/robotcodedev/robotcode/commit/b257df09e5699f4e83dd5505aeba945b3b68cfab))

  The Test Explorer now follows every change of a suite file: with several
  paths in robot.toml its tests keep their results and can be run, tasks
  stay after an edit, and files changed outside VS Code, restored under an
  open tab or changed together in one edit are read again. The top-level
  suite of several paths can be run again, and Run Tests and Debug Tests
  run every workspace folder. In PyCharm, an edit in a project with
  several paths no longer starts a full discovery.

- Start the terminal REPL in the folder's Python environment ([3852a99](https://github.com/robotcodedev/robotcode/commit/3852a99d5c53d0605b937fd00cf63b8f112ea783))
- Pass launcherExtraArgs to robotcode in every debug launcher mode ([1e2834d](https://github.com/robotcodedev/robotcode/commit/1e2834da05d9c898beaf571811722f09e96957b3))

  In the tcp and pipe-server launcher modes `launcherArgs` was passed twice, once in place of `launcherExtraArgs` as arguments of robotcode itself, and `launcherExtraArgs` was ignored; both modes now use the two attributes as the stdio mode does, and their descriptions say which command each one belongs to. Also documents the `stopOnEntry` launch attribute, which launcher and debugger already support, so launch.json no longer warns about it, disposes the "Configuration Profiles" language status item with the others, and gives the Robotidy and RobotCode icons their own descriptions.

- Recognize a chat plugins marketplace entry pinned to a tag ([b57e93b](https://github.com/robotcodedev/robotcode/commit/b57e93b968d3c5d980482f53e8fae0efd4455239))

  An entry such as `robotcodedev/robotframework-agent-plugins#robotcode--v2.7.0` counted as missing, so the Command Palette kept offering RobotCode: Add Chat Plugins Marketplace, which added a second entry, instead of Remove; now a pinned entry counts as the marketplace.

- Find debugpy launch configurations named in pythonConfiguration ([9e1c9f6](https://github.com/robotcodedev/robotcode/commit/9e1c9f692ddfef87c35b1da5d5ff9e45d034bbfc))

  A `pythonConfiguration` that names a launch configuration only found configurations of type `python`, so the bundled "RobotCode: Python" configuration of type `debugpy` and its options such as `justMyCode` were silently ignored when a Robot Framework debug session attached to Python; now `debugpy` and `python` configurations are found. Also gives the `off` value of `robotcode.analysis.progressMode` its own description, so the descriptions no longer belong to the wrong values, and removes the duplicated "RobotCode: Default" configuration snippet.

- Follow deleted, moved and new folders in the Test Explorer ([7434108](https://github.com/robotcodedev/robotcode/commit/7434108bfb5787053d0f14685bc591d7e7436850))

  Until now, folders of suites that were deleted, renamed or moved away, also by git or in a terminal, stayed in the tree until Refresh Tests, and folders that appeared at once did not show up. A failed discovery, for example because a test path no longer exists, no longer leaves the suites of the last discovery next to its error, which it did since 2.6.0.

- No longer leave the language server stopped after the Python environment dialog ([59a7c0d](https://github.com/robotcodedev/robotcode/commit/59a7c0d52ac0d0a9236b03d160f753bea9b4e95a))

  After Select Python Environment was closed without a new choice, or after Retry in the dialog about an invalid environment, the next restart, for example from a changed setting, left the language server stopped until the window was reloaded, and closing the interpreter picker ended the command with an error. Restart Language Servers and Clear Cache and Restart Language Servers now also check the environment again after the dialog about an invalid environment was dismissed, for example once Robot Framework is installed by hand.

- Correct typos and mixed-up texts in setting and color descriptions ([0f1f735](https://github.com/robotcodedev/robotcode/commit/0f1f73594f43881ce82ae9e7c5f8b69b15a82a9b))

  The descriptions of several settings, log colors and a language model tool had typos, and some log colors described a different color. Two robot.toml options had the same typo, which is now also fixed in the configuration reference and the schema.

- Name the workspace folder in Select Python Environment from the Command Palette ([f0eb94e](https://github.com/robotcodedev/robotcode/commit/f0eb94ee5f0d005f1c88b24563da0ab2ef0bda51))

  Run from the Command Palette, the command now works on the folder of the active file or the only workspace folder instead of showing 'undefined' in its title, and its Disable choice now switches RobotCode off for that folder.

- Require Python 3.10 before starting the language server ([1be14d6](https://github.com/robotcodedev/robotcode/commit/1be14d62ec89034fafc0b7f29408cb9c45d2f41f))

  The extension accepted Python 3.8 and 3.9, although every RobotCode package needs Python 3.10. It now rejects them up front, and the interpreter picker says that Python 3.10 or newer is required.

- Start the language server for folders with Robot Framework files ([1a3a644](https://github.com/robotcodedev/robotcode/commit/1a3a6447502e591c168b7065894c07b2a36ddccc))

  Since v0.36.0 the language server only started once a Robot Framework file was open, so workspace symbols and the diagnostics of `diagnosticMode: workspace` were missing until then. It now starts again when VS Code opens a folder with Robot Framework files, a `robot.toml`, or a `pyproject.toml` or `requirements.txt` that depends on Robot Framework or RobotCode; like Robot Framework, the search skips folders starting with `.` or `_`, and also folders such as `node_modules` and `target`. If Robot Framework is missing there, RobotCode asks for a Python environment right at startup.

- Stop activating RobotCode whenever Markdown is rendered ([2cb565f](https://github.com/robotcodedev/robotcode/commit/2cb565fd08b90f446b74ba50996fdbf468f81de7))

  The extension declared `markdown.markdownItPlugins` without providing a plugin, so VS Code's Markdown support activated RobotCode and its Python dependencies whenever it built its renderer, for example for a Markdown preview.

- Highlight Robot Framework code blocks that are indented in Markdown ([ff3c156](https://github.com/robotcodedev/robotcode/commit/ff3c1562ec12b27c81ad9631131de58b61fdf641))

  Code blocks inside lists or block quotes of a Markdown file were recognised
  but not colored, because the grammar expected every line to start at the
  beginning of the line and Markdown containers consume the prefix first.


#### Website

- Load the RoboCon video on click and name link targets ([2471867](https://github.com/robotcodedev/robotcode/commit/24718672e8ddf18fab911abffa03919b1369fe5c))

  The Get Started page for VS Code embedded the RoboCon video as a YouTube player that loaded with the page and set cookies; it now loads only when the reader starts it, as on the home page. Links that read "Learn more" and "here" now say where they lead.

- Correct global user config file location ([ac8fcf2](https://github.com/robotcodedev/robotcode/commit/ac8fcf28d2ff46a20b6e83a69b45dc74efe69cbd))

  The global user configuration is stored in the platform-specific user
  config directory as a robot.toml file, not at ~/.robot.toml in the home
  directory. Document the actual per-platform paths (Linux ~/.config,
  macOS ~/Library/Application Support, Windows %LOCALAPPDATA%) so the file
  is placed where RobotCode actually looks for it.


#### Bundled

- Run robotcode in VS Code terminals without bash and with spaces in the path ([465e682](https://github.com/robotcodedev/robotcode/commit/465e6829112644ac93b5170fc59911ad25232578))

  The robotcode command that VS Code terminals fall back to required /bin/bash, which Alpine-based containers, NixOS and FreeBSD don't have, and a space in the extension path, for example from a Windows user name like `John Doe`, split the path into two arguments in sh and cmd.



### <!-- 2 -->Documentation

- Add OpenSpec change proposals for REPL input errors and exit status ([e02ea84](https://github.com/robotcodedev/robotcode/commit/e02ea845e559d54895309f19860a2efba9e0822c))

  Two planned changes for `robotcode repl`, not yet implemented:

  - repl-report-input-errors: input that does not parse is no longer dropped
    silently. Script files and piped input run like a `robot` test body up to
    the invalid statement and fail there with Robot Framework's message,
    unfinished blocks at the end of input are reported, continuation lines are
    only requested while a block is really open, and orphaned `...` lines are
    rejected.
  - repl-exit-status: the session test in the output files is FAIL after an
    unhandled failure, non-interactive sessions (piped input, script files
    without `--inspect`) exit with code 1 on failure, `--statusrc` /
    `--nostatusrc` and `no-status-rc` override that, and `.exit CODE` /
    `.quit CODE` end the session with an explicit exit code.

- Add OpenSpec change proposals for the SemanticModel migration ([bf22ba9](https://github.com/robotcodedev/robotcode/commit/bf22ba9814bc1f7f3ed1127e5ba9b3180c4fe079))

  Introduce the openspec/ planning tree covering the remaining SemanticModel migration end to end: Tier 4 completion, the Phase 3 switchover (flag default flip, analyzer swap, KeywordTokenAnalyzer removal), and the Phase 4 cleanup that deletes NamespaceAnalyzer, ModelHelper, and ScopeTree.

  Adds Phase 5 feature proposals — call hierarchy, smart rename, quality diagnostics, and workspace refactorings — next to the existing sidecar-cleanup, tier1-completion, and hover changes.

  Sequencing is documented per change: only two hard gates (switchover, then cleanup); every other change is parallelizable once the model is available and proven correct.

  Relocate the SemanticModel design document from the git-ignored playground/ into a versioned dev-docs/ folder, trimmed to reference, rationale, and ideas (the planning and phase-tracking sections now live in the proposals). Point the proposals at the new location and record dev-docs/ in AGENTS.md as the home for planning and design notes.

#### Analyze

- Correct the analysis guides ([79c6d40](https://github.com/robotcodedev/robotcode/commit/79c6d400a772be9dd094bccd17af033cc05714c7))

  Corrects what `analyze code` resolves and counts when it gets paths, its exit codes on a failing command, the severity of the import diagnostics, how Robot Framework handles a repeated library import with other arguments, and the variable-not-found examples, which now show only what RobotCode reports.

- Describe import timeouts, early-ended imports and the cache per argument set ([513a183](https://github.com/robotcodedev/robotcode/commit/513a183a4e81903db74d6fc592547ae90b3b1024))

  The analysis reference names the new diagnostics and says when a timed-out library is loaded again and that library imports are cached per set of arguments.


#### CLI

- Correct the help of --color, --pager and --stop-on-entry ([a5e4efe](https://github.com/robotcodedev/robotcode/commit/a5e4efebfcfaea259ad2b29d2e46e6af5344be12))

  `--color` and `--pager` don't force anything into a pipe, `--stop-on-entry` stops at the first step, which can also be a control structure, and `analyze code` without paths analyzes the whole project, not the current directory.

- Leave hidden commands out of the CLI reference ([11ec641](https://github.com/robotcodedev/robotcode/commit/11ec641ea0e238dcfe188119e102a977ed7244b4))

  The reference documented the internal `debug-launch` command, although `--help` hides it, and would have picked up the hidden `analyze dump-model` the next time it was generated.


#### Config

- Describe profiles and their settings in the robot.toml reference ([a933a54](https://github.com/robotcodedev/robotcode/commit/a933a5493aee2012edfffc99002c163ca3018a66))

  The reference called profiles only "Execution profiles" and "Extra execution profiles"; it now says how profiles apply, that profiles in a later file such as .robot.toml replace those of robot.toml while extend-profiles adds to them, and what detached, inherits, enabled, hidden and default-profiles do.

- Correct examples, precedence and extend-* descriptions ([d2cfb47](https://github.com/robotcodedev/robotcode/commit/d2cfb47763bc49acbb10a120683108f388e05a90))

  The profile examples replaced `variables` instead of extending them and set a number where a string is required, the user configuration is per user and created when it is missing, profiles with the same precedence keep the order they are selected in, and the `extend-*` keys of the analyze settings only take effect in an `extend-<section>` table such as `[tool.robotcode-analyze.extend-modifiers]`.


#### Debugger

- Fix the links to exception breakpoints ([5a12cce](https://github.com/robotcodedev/robotcode/commit/5a12ccef5923da11b109fe3510d07e14e3af5c26))

  Both links pointed to an exception-breakpoints anchor that no heading of the robot-debug page has; they now point to the debug commands section, which describes the exception filters.


#### PyCharm

- Rewrite the plugin's Marketplace description ([106a101](https://github.com/robotcodedev/robotcode/commit/106a101165c5893629aacac12517f9725f314e7b))

  The description no longer calls the plugin not ready for production use. It
  says what RobotCode is for, lists its features in PyCharm, the requirements
  and the first steps, and links to the PyCharm guide on robotcode.io. On
  GitHub, the JetBrains logo shows again.


#### REPL

- Design the native REPL and notebooks ([6929f4c](https://github.com/robotcodedev/robotcode/commit/6929f4c81d454abdfc33cd3dd83c60052ea88920))

  dev-docs/repl-and-notebooks.md collects the decisions for a Robot Framework REPL in VS Code's Interactive Window and for notebooks, the execution layer they share with robotcode repl, the facts they rest on and the open questions. It gets cut into OpenSpec changes later.

- Correct the REPL and robot-debug guides ([e794706](https://github.com/robotcodedev/robotcode/commit/e794706e5b7c07155cfa33bcb83d8ed5c4f186a5))

  Corrects the dot-command prefixes, the flags only `robotcode repl` has, several prompt features of both backends, the example outputs, that `-l` needs `-o`, and where `--stop-on-entry` stops.

- Stop claiming that the command-line debugger shows logpoints ([d34fcdf](https://github.com/robotcodedev/robotcode/commit/d34fcdf275aadc8a7b4050c010301236bc22b324))

  The guide said `.breakpoints` shows a `logpoint` flag, but no command of `robot-debug` or the REPL sets a log message on a breakpoint, so the flag never appears.

- Correct the description of .set ([88d43e2](https://github.com/robotcodedev/robotcode/commit/88d43e279ebd15baacb53afedc31a65fb1d7d840))

  The help and the command-line debugging guide described `.set` like `Set Variable` and recommended `${{ … }}` for Python values. The command only changes existing variables and always stores a string, which neither of them said.

- Describe the sidebar of the documentation viewer ([12ef563](https://github.com/robotcodedev/robotcode/commit/12ef563e079e9fb0c3c42c7cfb2d32ecb515d0d3))

  The REPL guide lists the keys of the sidebar of `.doc`, and the guide to `robotcode doc` describes it for `browse` with its two layouts.

- Describe robotcode doc ([a1fba07](https://github.com/robotcodedev/robotcode/commit/a1fba07721ed66055c03005d1f2c232c914af1fb))

  A new guide covers the targets and their import arguments, the configuration, the Markdown and JSON output, keyword overviews and lookups, the terminal viewer and what happens when a target cannot be loaded. The command reference, the REPL's `.doc` and the AI-agent page point to it.

- Document the exit code and how invalid input is handled ([33ca61e](https://github.com/robotcodedev/robotcode/commit/33ca61e5c289f592e0ea7f3c42a0c8ae672e46bd))

  The REPL reference explains when the session test fails and when that reaches the exit code, the `--statusrc`/`--nostatusrc` options, `no-status-rc` and `.exit CODE`, and how invalid input, unfinished blocks and orphaned `...` lines are reported. The CI smoke-check recipes now use a check that can fail, and the claim that an empty line at the `>>>` prompt ends the session is corrected.

- Describe what `--source` and `.cwd` actually do ([7717763](https://github.com/robotcodedev/robotcode/commit/771776345d559a3d60de1b033e01eea3b2906a5f))

  The `--source` docs and help text claimed that the option sets the REPL's
  working directory and that relative imports and variable files resolve
  against it. The reference now explains the real behavior:

  - `${CURDIR}` is the directory of FILE, `${SUITE SOURCE}` and the suite
    source in `output.xml` are FILE
  - bare relative `Import Resource`, `Import Library` and `Import Variables`
    resolve against that directory only on Robot Framework 7.4 and newer
  - without `--source` the start directory is used, and a relative FILE is
    resolved against it
  - the REPL process itself keeps running in the project root, which is what
    `.cwd` prints and what relative paths in keywords like `File Should
    Exist` use


#### Runner

- Correct the discover, results, wrapper and ignore guides ([9e9745e](https://github.com/robotcodedev/robotcode/commit/9e9745e51cdfc6c69c01fd10f154a376c1b2aa19))

  Brings example outputs, JSON fields, patterns and option descriptions in line with the commands, among them that a suite pattern like `*.Login.*` selects nothing in a suite file, that `source` is absolute next to `relSource`, that `discover files` also lists `_` files, and that the PowerShell wrapper example passes `-p` and `-v` on.

- Document selecting tests by their metadata ([5c203f8](https://github.com/robotcodedev/robotcode/commit/5c203f8af341af12918eed39ec1ae2a3447a2bdb))

  Describes discover metadata, the pattern rules of --by-test-metadata and --exclude-by-test-metadata, how several values of one name are written, and the use with plain robot and robot.toml profiles, each marked as needing Robot Framework 7.5.


#### VS Code

- Show the Documentation Bookmarks view in the guide ([e6fc968](https://github.com/robotcodedev/robotcode/commit/e6fc968841a1587c83164baa2cb169dfd75cee8a))

  The page Documentation Viewer shows the view in the Explorer, with its groups and buttons, beside a viewer at the selected bookmark.

- List the new commands of the Documentation Viewer and retake its media ([fe31be3](https://github.com/robotcodedev/robotcode/commit/fe31be3bc6e65856d6476006d66fe704352f2f4e))

  The command table of the overview lists Show Documentation Viewer and Reset Documentation Bookmarks. The screenshot and the recording of the Documentation Viewer show the star of the bookmarks, the place in the target field and the new icon of New Documentation Viewer.

- Describe the button for a new Documentation Viewer ([35a20c0](https://github.com/robotcodedev/robotcode/commit/35a20c0ecf37c56934c63ae51d2eaac2d22eca84))

  The guide and the command table use the renamed commands, the guide describes
  the toolbar button and names VS Code's commands that cannot split or copy a
  viewer, and the screenshot of the viewer shows the new toolbar.

- Say when RobotCode reports environment problems at startup ([bdce7ae](https://github.com/robotcodedev/robotcode/commit/bdce7ae93221d704dcd25771b56fc4a22f96cc3e))

  The section on the Python environment says that RobotCode reports a
  problem it finds in the first 15 seconds after VS Code starts or a folder
  is added only if it remains, and that the language status shows meanwhile
  that RobotCode is still checking.

- Name the environment in the guide as the default setup does ([7561cc4](https://github.com/robotcodedev/robotcode/commit/7561cc4b24843e13643ab331b8bf3438f18ded22))

  The picture of RobotCode's environment message and its alt text name the
  virtual environment '.venv', as the message does with the Python
  Environments extension, instead of '.venv (venv)' from the Python
  extension's API.

- Describe how the Documentation Viewer waits for the Python environment ([f5c77bb](https://github.com/robotcodedev/robotcode/commit/f5c77bbed20eb82f771bc63d9946258c03bc1e17))

  The guide's paragraph on kept pages says that the viewer waits for a usable
  Python environment, shows its last page meanwhile, and shows a lasting problem
  as an error after 30 seconds.

- Correct when completion offers variables and tags ([244e150](https://github.com/robotcodedev/robotcode/commit/244e15007e9faf18ee1823a4107ae2fdac5d7801))

  Completion offers variables after `${`, `@{` and `&{` and environment variables after `%{`, and of the tags only the reserved ones such as `robot:skip`.

- Show the new Python environment message in the guide ([487a31f](https://github.com/robotcodedev/robotcode/commit/487a31f31bee5abb60f729b39ca88c0e859ef39f))

  The guide and the VS Code getting started page still showed the old environment dialog and pointed to `Python: Select Interpreter`; they now show the message RobotCode gives for an unusable environment, the hint of the Testing view without an environment, and what the language status shows for each problem.

- Base the highlighting guide on RobotCode's default styles ([278766c](https://github.com/robotcodedev/robotcode/commit/278766c882dfd1a5212a905bc7d5512877881103))

  The guide presented the font styles as a customization with a before/after comparison, but RobotCode sets them by default; it now shows the default rules as the starting point and says that a `textMateRules` list in the settings replaces them.

- Correct the VS Code guide ([9ddb119](https://github.com/robotcodedev/robotcode/commit/9ddb1190c98d183869fe5f8109d8e8019fd60fe9))

  Corrects what the Documentation Viewer commands do, how launch configurations combine with the settings, which settings the discovery and the analysis get and when the Test Explorer updates by itself, and retakes the REPL terminal screenshots, which showed different parts of the session.

- Mention the highlighted Robot Framework code blocks ([5f4d8e0](https://github.com/robotcodedev/robotcode/commit/5f4d8e01d7c86f83767067317bd362900d0d0f2f))
- Document the links to the Documentation Viewer ([356719d](https://github.com/robotcodedev/robotcode/commit/356719df7b684dce2b266de5c0805940b00abe7a))

  Also shows how to bind a key to the source actions, since RobotCode defines none, and marks the Libdoc actions as deprecated.

- Document the Documentation Viewer ([19e53e4](https://github.com/robotcodedev/robotcode/commit/19e53e4372a1ff2cd5db82cc4bc1060ccf7d1261))

  Adds a VS Code section to the page about browsing documentation, and the installation table now says that `robotcode doc` and the Documentation Viewer do not need Python-Markdown.


#### Website

- Show the documentation bookmarks in the v2.8.0 release notes ([018fb51](https://github.com/robotcodedev/robotcode/commit/018fb511faeb37854801d59d69f96ff28db7e7ff))

  The post now presents the Documentation Bookmarks view with a screenshot,
  gives PyCharm a longer entry higher up in the highlights and shortens the
  breaking change for profile names that select no profile.

- Let the spiders ask for a poke during the Halloween season ([a548ae1](https://github.com/robotcodedev/robotcode/commit/a548ae17fa6723861a9129f2de0f8711ff5658d2))

  During the Halloween season a spider of the home page or a news page now
  and then says "Trick or treat? Poke me!" in a speech bubble, so that
  visitors find the RobotCode tips that clicked creatures leave as treats.
  The spiders take turns and stop asking once the visitor has got a treat.

- Add the v2.8.0 release notes ([2717523](https://github.com/robotcodedev/robotcode/commit/27175235ef39fd707beb39606dad42e609f9b4e8))

  Announce the Robot Framework 7.5 support, the Documentation Viewer, the
  Python environments in VS Code, the biggest update of the PyCharm plugin
  and the new website, with screenshots of the new features.

- Link the contribution guide and the dev builds on Support & Contribute ([5cb2af5](https://github.com/robotcodedev/robotcode/commit/5cb2af59e975c94601f4c8199d778ec20338d5e3))

  The page now points contributors to CONTRIBUTING.md and testers to the page about the dev builds.

- Add nine posters to the Halloween gallery of the home page ([6cd6d52](https://github.com/robotcodedev/robotcode/commit/6cd6d52d8a73efacfa3b32dfe795e08bc485e4a2))

  During the Halloween season the gallery of the home page shows nine new posters, from The Suite to A Nightmare on CI Street; the poster after Nosferatu (2024) is gone.

- Describe what happens when a profile name selects no profile ([aaa65fb](https://github.com/robotcodedev/robotcode/commit/aaa65fb61fa08d43cfcec6fecc93b9b74690a10e))

  The robot.toml troubleshooting page and the VS Code and PyCharm guides say when such a name stops a command, what the language server shows, and how the editors report a name of their selection.

- Describe how results log --extract resolves links and names files ([39eafe7](https://github.com/robotcodedev/robotcode/commit/39eafe7f5698b54965a0313893d84ab4cb3b2bd8))

  The --extract section now says how encoded names, file: links, folders,
  videos and repeated references are handled, and that an embedded file keeps
  the name from its download attribute.

- Say that the PyCharm preview shows report and log in the IDE's theme ([10b6537](https://github.com/robotcodedev/robotcode/commit/10b6537875cbc61cb3e88b585d36f7560122b756))

  The page on running tests says that the preview shows the report and the
  log in PyCharm's theme, follows a change of it, and keeps the theme chosen
  with the page's own switch until PyCharm's theme changes.

- Say that PyCharm completes robot.toml and highlights robot code blocks ([5b11695](https://github.com/robotcodedev/robotcode/commit/5b116950b7994d1e8ab54778606499fec9e8689d))

  The configuration pages say that PyCharm completes robot.toml and
  .robot.toml without further setup, and the comparison with VS Code gets
  rows for the completion in robot.toml and for Robot Framework code blocks
  in Markdown.

- Say which module's interpreter RobotCode uses in PyCharm ([978fd75](https://github.com/robotcodedev/robotcode/commit/978fd75e5bec2bb9967d1694565e2b314843cdd1))

  The PyCharm guide now says that RobotCode takes the interpreter of the module
  with the Robot Framework project, asks when several modules qualify, and that
  Module for RobotCode on the General page changes the choice.

- Add a page on how to try the dev builds ([a4eb6b7](https://github.com/robotcodedev/robotcode/commit/a4eb6b7eec85dc3a46a994374d5f1a3419719f09))

  The new Getting Started page explains how to switch to the dev builds of the VS Code extension, the PyCharm plugin and the Python packages, with pip or uv, how to recognize them and how to go back to a release. The README links it under Get Involved.

- Let the Halloween fog and the Spooky switch move in steps ([75e2040](https://github.com/robotcodedev/robotcode/commit/75e2040147d59eae546619eaedb21b00914b1743))

  The fog drifts and billows in small steps and the floating Spooky
  switch moves a pixel at a time, so that on a fast screen the browser no
  longer draws the decorations again at every refresh; on a 145 Hz screen
  the home page with the hero out of view goes from about half a
  processor core to about a quarter.

- Let the progress bars of the home page demos move in steps ([1a53cd7](https://github.com/robotcodedev/robotcode/commit/1a53cd788887af6597171e706e38f644ba9ffa7b))

  The bar under the active tab of the feature tour and of the agent demo
  now grows in steps of about two pixels instead of continuously, so the
  browser no longer draws a new picture at every refresh of the screen
  while a demo plays; on a 145 Hz screen the agent demo goes from about
  18 to about 4 % of a processor core.

- Stop the home page from painting the tour's progress bar and the news badge in every frame ([58f4188](https://github.com/robotcodedev/robotcode/commit/58f418897e8d8534142bc6c0467f71d6035b6b30))

  The progress bar of the feature tour now grows by a transform instead of its width, and the badge of a fresh news post pulses five times after the page loads instead of for as long as it is open, so the home page no longer keeps the processor busy while it is shown.

- Let blood run down the title of the home page at Halloween ([1d8ee74](https://github.com/robotcodedev/robotcode/commit/1d8ee74a206498bda0a38a86afc699450df20ecf))

  During the Halloween season, while Spooky mode is on, the title of the home page is full of blood: drops gather at the bottom of its letters and fall, and the traces they leave dry darker. With Spooky mode off the title looks as usual.

- Let the gallery on the home page move on by itself ([448f75a](https://github.com/robotcodedev/robotcode/commit/448f75a3e30bc1740b5771c09f4af77ab8293585))

  The picture next to the title of the home page now changes by itself every eight seconds with a short fade, so visitors see more of the RobotCode artwork. It stays while you point at it, focus it or look at the enlarged view, and it doesn't move on with reduced motion.

- Add a Halloween season to the website ([f6c614c](https://github.com/robotcodedev/robotcode/commit/f6c614ce4ee99d91e2f91f2fc442c3e257d8c0c3))

  From October 20 to November 2, robotcode.io dresses up for Halloween: it starts in the dark theme unless you picked one, the home page shows RobotCode on horror-film posters, and the home page and the news pages get spiders with an egg sac, bats, a peeking ghost, a floating pumpkin, fog, the moon with lightning and thunder, and a music box. Switches next to the pumpkin turn the decorations, the sound and the music off, and `?season=halloween` shows the season at any time.

- Don't promise the same features in every IDE ([39bb9c7](https://github.com/robotcodedev/robotcode/commit/39bb9c75e7c4917e57f1355e71867102d9a082fd))

  The About page and the feature tour on the home page said that VS Code and IntelliJ have the same features because they share a codebase; they share the language server, while tools such as the Documentation Viewer and notebooks exist only in VS Code.

- Show the newest news post at the top of the home page ([19ffded](https://github.com/robotcodedev/robotcode/commit/19ffdedc115de09e1ab7650b977174630a11c889))

  The home page shows its newest news post with its date as a badge above the title, so it is seen without scrolling, and the badge pulses gently while the post is less than 30 days old.

- Keep the CI's Python and Robot Framework matrix off the Getting Started page ([aea2d30](https://github.com/robotcodedev/robotcode/commit/aea2d308c3d5fd915cffddb518a69306e0fdf5c4))

  The table read as if each Robot Framework version ran only with the Python versions the CI tests, such as Robot Framework 5.0 only with Python 3.10. The requirements now say that the Python version has to suit the Robot Framework version, and the matrix stays with the contributors in CONTRIBUTING.md and the README.

- Show the glow of the home page's hero behind its picture ([d3a68a7](https://github.com/robotcodedev/robotcode/commit/d3a68a7935b87a53e40084ac21543c60d2c72f87))

  The glow sat beside the picture, the further off the wider the window, because its position was set in the backdrop that reaches past the content column. It now sits centred behind the picture in every layout, and the soft glow lies under the text instead of at the window's edge.

- Set the header, the sidebar and the home page sections apart in the light theme ([73928e7](https://github.com/robotcodedev/robotcode/commit/73928e7c7c5c5b70d2525ea2295fa88906e0fe80))

  In the light theme, the header and the sidebar now have a gray of their own as in the dark theme, and the tinted bands of the home page are stronger, so the parts of a page no longer blend into one white surface.

- Show how to pin the chat plugin to a version ([e91edf8](https://github.com/robotcodedev/robotcode/commit/e91edf8c0019fc52bf6f9f87e042937731af2cd8))

  Projects on an older RobotCode can install the marketplace plugin from
  the matching release tag instead of the newest one.

- Correct settings, commands, claims and examples after a review ([cbc92b6](https://github.com/robotcodedev/robotcode/commit/cbc92b60dd99ada883d332ebb9717f89ceb6cda7))

  A review checked the pages against the code and against real runs. It corrects wrong setting and option names, commands that fail, statements the code contradicts and output examples in an old format, now taken from real runs, and quotes the pip extras so they work in zsh. The home page buttons now say VS Code Extension and JetBrains Plugin, and the RoboCon tutorial is described as its video description lists it.

- Name the period key by its scan code in the source-action binding ([b97b086](https://github.com/robotcodedev/robotcode/commit/b97b08638d030c578f2afcf5c0d9e8740b852dd1))

  The keybindings.json example for the Source Action menu in Browsing Library Documentation writes the key as ctrl+shift+[Period].

- Replace the GIF recordings with the example project's videos ([a811832](https://github.com/robotcodedev/robotcode/commit/a811832dfed9d335d25937d0ace506518c0c02fc))

  The About page and the home page of the current site showed GIF recordings with a user and host name in the terminal. They now show the recordings of the example project that the preview's home page uses, and the preview's conversion imports a page's videos like its images.

- Record the home page videos anew, with a debug session ([1346c4e](https://github.com/robotcodedev/robotcode/commit/1346c4ed1f1042f0600e1dc1dca141d50fcdd142))

  The screen recordings of the feature tour showed a user and host name in the terminal. They are recorded anew in the example project, and Run, debug & test explorer adds a debug session with a breakpoint, Step Into, Step Over and the variables as a second video, chosen with a dot like the editor screenshots. A feature chosen before the tour comes into view now stays chosen.

- Show RobotCode in VS Code and PyCharm in the editor series ([7c04ab8](https://github.com/robotcodedev/robotcode/commit/7c04ab8cf407bc698dd19bff654b6ac3dda78891))

  The Multi-IDE feature of the preview's home page now shows diagnostics, completion, inlay hints, references and the keyword documentation in VS Code and PyCharm next to Neovim, mixed by feature. The screenshots change every three seconds with a fade, and a dot per screenshot under the window replaces the labelled buttons.

- Keep the editor screenshots inside their feature ([5c95c82](https://github.com/robotcodedev/robotcode/commit/5c95c824bba369fcc129b5c4299d8d5ee8edecca))

  The current screenshot of the editor series stayed visible on top of the recordings and terminal sessions of the other features, because it was made visible even while its panel was hidden.

- Show conversations with an AI agent on the home page ([9c03781](https://github.com/robotcodedev/robotcode/commit/9c0378103d4ea6584cb8d407e7e325a967b3fdd2))

  The agent window of the preview now plays seven conversations with follow-up questions about an example web shop, from writing a test for a requirement with the Browser library to finding the tests that cover a requirement and fixing a failing test, and the section describes what an agent can do with the RobotCode skill rather than which commands it runs. The configuration demo shows a profile that extends the variables instead of replacing them, with a browser name the Browser library knows.

- Show RobotCode in Neovim as a series of screenshots ([15f0e47](https://github.com/robotcodedev/robotcode/commit/15f0e47cebd7070f025cef4866e8830e3e7a8be4))

  The Multi-IDE feature of the home page now plays a series of screenshots of the example project in Neovim — diagnostics, completion, inlay hints and references — instead of the picture of import errors from the Neovim guide; the series can take screenshots of other editors as well. The output in the demos was taken again after the example project was cleaned up.

- Take the home page demos from a fuller example project ([840e58b](https://github.com/robotcodedev/robotcode/commit/840e58bd374aec3671414560b67f0f43639b5efd))

  The terminal sessions of the home page now come from an example web shop with several suites, a keyword library and suite and test metadata, run with the released robotcode 2.7.0. Sublime Text is no longer named among the editors, as it has not been tried with RobotCode.

- Rework the home page of the preview ([152596f](https://github.com/robotcodedev/robotcode/commit/152596f15df9aa1af81dae6983002c8281abbf47))

  The home page now leads with a feature tour whose window plays screen recordings and real robotcode terminal sessions, followed by a section on the AI agent skill with a demo of an agent working through robotcode, the RoboCon tutorial, the latest news as a short list and a section on RobotCode being open source, sponsoring and supporters. The two screen recordings are MP4 versions of the GIFs, at a third of their size.

- Drop the MDX override of the preview ([f772016](https://github.com/robotcodedev/robotcode/commit/f7720164fbe56b9ab6555915d0c575bc77ffe4c3))

  The override was based on a lockfile that npm 10 rejected, not on a real conflict: with a freshly generated lockfile, starlight-blog's own @astrojs/mdx 7 installs next to Starlight's version 8 and npm ci and the build work without it. This corrects the reason given in 53e246c0.

- Check the links of the preview's not-found page ([ccb8c58](https://github.com/robotcodedev/robotcode/commit/ccb8c589f00cf9d913639cb61d1c5a7bfb2714de))

  The build's link check reads only the docs collection, so the conversion script now checks the links in src/pages/ and fails on one that points to no page.

- Give starlight-blog the MDX integration Starlight uses ([53e246c](https://github.com/robotcodedev/robotcode/commit/53e246c052a26dceb273c54a896e21a1201916ab))

  starlight-blog 0.30 still declares @astrojs/mdx 7, whose Sätteri 0.3 peer npm 10 and npm 12 resolve differently. Overriding it with Starlight's @astrojs/mdx range instead of pinning Sätteri leaves one MDX integration in the tree and no unmet peer.

- Use the newest dependencies in the preview ([d49c86e](https://github.com/robotcodedev/robotcode/commit/d49c86eabc74d4393cdb5a37decd0e56e287301a))

  Moves js-yaml to 5 and drops sharp, which Astro already brings. Starlight's own js-yaml 4 import is bundled into the prerender build so it no longer resolves to version 5, and Sharp may now process the two large animated GIFs of the home page, so they ship as WebP like all other images and the build stays free of warnings without the image cache.

- Add a Starlight preview of the site ([e88ea95](https://github.com/robotcodedev/robotcode/commit/e88ea95e4d813347f34a26b4780fd3d545b29e1b))

  Adds docs-next/, an Astro + Starlight site that scripts/convert.mjs generates from docs/ before every dev and build, with the new Getting Started, Guides and Reference structure, the news as a blog and a link check. It is not deployed: a build-only workflow checks it on changes to docs/, and the extension build, the VSIX and linting leave it out.


#### Contributing

- Describe the tests of the VS Code extension and the PyCharm plugin ([44d2551](https://github.com/robotcodedev/robotcode/commit/44d25517a6809af730d483d8fcc2e95f66085e60))

  The contribution guide and the pull request template now ask for the tests of every changed part, explain how to run, try and verify the PyCharm plugin, list what the CI runs and ask for tests that pass on Linux, Windows and macOS. The commit types and scopes match the ones in use.

- Describe how to regenerate the CLI reference ([5ff48c8](https://github.com/robotcodedev/robotcode/commit/5ff48c8ad8c269b553c175ed23d4d04b0bbbed41))


### <!-- 3 -->Performance

#### Core

- Free events and document caches without the garbage collector ([20d3084](https://github.com/robotcodedev/robotcode/commit/20d3084f6bdd18023c457716560150894bf76c99))

  Each rebuilt namespace left an event behind that only the garbage collector could free. Events and the cache entries of documents are now freed as soon as they are no longer used, and a listener that dies right after it was removed no longer causes an ignored KeyError while another thread calls its event.


#### Language Server

- Parse the document once per selection range request ([32369fe](https://github.com/robotcodedev/robotcode/commit/32369feee66303aac072d755d184aa048eeb500b))

  Selection ranges built the model again for every requested position when the document had no version, so a request with many positions parsed the whole file once per position. The model is now taken once per request, which roughly halves the time of the selection range parity tests.


#### Website

- Load only the shown picture on the home page ([98d8b0e](https://github.com/robotcodedev/robotcode/commit/98d8b0ea8fd62a186f8d2a55a2b0a851cbe41813))

  The home page chose its random picture only after it had loaded and fetched the first picture and both lightbox images as well. It now picks the picture while the page is parsed, requests only that one, early, and loads the enlarged picture when the lightbox opens.



### <!-- 4 -->Refactor

#### PyCharm

- Remove the empty listener, the broken icon and the placeholder test classes ([ceb4acc](https://github.com/robotcodedev/robotcode/commit/ceb4acc5a0f203995ab80a7ae5df0132caf0f2ac))

  The application activation listener did nothing, the Robot icon pointed to a file that does not exist and was never used, and the test status listener and test action provider were placeholders whose registrations were already commented out. The outdated TODO about exception breakpoints goes too, since they are registered.

- Replace the remaining deprecated platform calls ([9010b48](https://github.com/robotcodedev/robotcode/commit/9010b488e60b65c8a42b7a9acd7972c3d7cfbf1e))

  Highlighting restarts after a test refresh now pass a reason to the platform, and the message bundle delegates to a DynamicBundle instance instead of subclassing it. This removes all deprecation and compiler warnings that 2026.1 allows us to fix; behavior is unchanged.

- Start debug sessions with the session builder ([b556b0e](https://github.com/robotcodedev/robotcode/commit/b556b0ea0f98668cbc1444ebfc78b403f16bebb3))

  The debug runner now starts its session through the session builder and returns the descriptor of the started result, instead of the startSession and getRunContentDescriptor calls that 2026.1 deprecates. This removes the debugger deprecation warnings; debugging behaves as before.

- Build the TextMate lexer with the API 2026.1 recommends ([829affb](https://github.com/robotcodedev/robotcode/commit/829affb1f3cd430a954b2f33d7171ea90a5fde84))

  The lexer now uses the regex provider, weigher and syntax matcher the platform's own TextMate highlighting uses, shared by all lexer instances instead of new caches per lexer, and takes the language descriptor from the syntax table. This removes all TextMate deprecation warnings; the tokens stay the same.


#### Robot

- Track the keyword and test case context of the analyzers with flags ([25f9444](https://github.com/robotcodedev/robotcode/commit/25f9444befda4f33c4def06b6723b9b2f179fbb4))

  Both analyzers set a flag while they visit a keyword or a test case instead
  of searching the node stack, and the semantic analyzer tells metadata from
  documentation by type instead of by class name.

- Index test metadata separately from suite metadata ([9d93cb2](https://github.com/robotcodedev/robotcode/commit/9d93cb2feffe57742b38502b24e89a35a458dbd9))

  The analyzer keeps the references to the names of test `[Metadata]`
  settings apart from the ones of suite `Metadata` settings, and compares
  the names like Robot Framework does, ignoring case, spaces and underscores.


#### TextMate

- Use a separate grammar for Robot Framework code blocks in Markdown ([ff1ddc4](https://github.com/robotcodedev/robotcode/commit/ff1ddc4e233debb7419a476b4c54810f184bfd92))

  Highlighting code blocks indented in Markdown lists and block quotes needs a variable-length look-behind and while rules that IntelliJ's TextMate implementation cannot handle, which left Robot Framework files without highlighting in the IntelliJ plugin. Robot Framework files get a grammar with plain line anchors again, the Markdown code block injection of VS Code uses a second grammar generated from the same template, and the template is back in sync with the committed grammar so the generator can be run again.


#### VS Code

- Remove the unused inline values request from the client ([d4fc2f5](https://github.com/robotcodedev/robotcode/commit/d4fc2f59d4a048bb3f4fa18a7faea6da2875a2c8))

  `getInlineValues` sent `robot/debugging/getInlineValues`, a request the language server never had, and nothing called the method; inline values come from the standard `textDocument/inlineValue` request. The method and the inline value types that only it used are removed.


#### Website

- Look up the screenshots of the VS Code guide by name ([bf8b51a](https://github.com/robotcodedev/robotcode/commit/bf8b51a5fa0e4d66bb6f4122b7981169cd9a8154))

  A page now names a light and dark pair once instead of importing both files, so adding a screenshot or recording takes a single tag; the rendered pages stay the same.



## [2.7.0](https://github.com/robotcodedev/robotcode/compare/v2.6.2..v2.7.0) - 2026-07-14

### <!-- 0 -->Features

#### Robot

- Make the analysis cache trustworthy under rapid file changes ([c998399](https://github.com/robotcodedev/robotcode/commit/c998399906355535cd3c2d60aaa3c071a37a410e))

  Fast consecutive changes to several files could poison the analysis
  cache: the editor and the CLI then reported errors that did not exist,
  like missing keywords or unresolvable variables, until the affected
  files were touched again. Cached results are now bound to exactly the
  file state they were computed from, and unsaved editor content is
  analyzed but never cached, so stale results can no longer stick.


#### RobotCode

- Run tests through a wrapper ([7aa84f6](https://github.com/robotcodedev/robotcode/commit/7aa84f6c08d17e95d981e67692763408d66c497c))

  Run the test execution through a command of your choosing, so you can
  prepare the environment a run needs - start the services, servers,
  mocks or session the tests depend on, run the tests inside it, and tear
  it down again afterwards. For anything that is only environment
  variables, keep using robot.toml's [env].

  Configure it per profile in robot.toml:

      [profiles.integration]
      wrapper = ["./with-test-services.sh"]

  set it ad hoc with --wrapper (or the ROBOTCODE_WRAPPER env var), and
  turn a configured wrapper off for one run with --no-wrapper. It applies
  to every command that executes Robot Framework - run, debug, the REPL
  and the notebook kernel - never to discovery, the language server or
  libdoc.

  Editors pick it up automatically because they run robotcode; the
  VS Code setting robotcode.debug.launchWrapper can override it for the
  IDE alone.



### <!-- 1 -->Bug Fixes

#### Plugin

- Use compact JSON separators for json output format ([e882368](https://github.com/robotcodedev/robotcode/commit/e882368e52326233100dfe6ddbee3e77c84fbc38))

  The compact flag was compared against OutputFormat.TEXT instead of
  OutputFormat.JSON, so compact JSON output was never actually applied.


#### RobotCode

- Make the wrapper work on Windows ([7baa0ac](https://github.com/robotcodedev/robotcode/commit/7baa0ac9499c406bb47bbb8a16aaa9152bb1ef6f))

  The wrapper re-run used os.execvp to replace the process, which only has
  POSIX semantics; on Windows os.exec* spawns a new process and exits the
  caller, so the exit code and stdout/stderr don't propagate. Keep execvp
  on POSIX (clean, no extra process) and on Windows spawn the command,
  wait, and forward its exit code. The subprocess tests, and their wrapper
  scripts, use spawn-and-wait too, so they no longer skip on Windows.

  Also document how running through a wrapper differs on Linux/macOS vs.
  Windows, and why.

- Make the wrapper work in VS Code ([1180d9c](https://github.com/robotcodedev/robotcode/commit/1180d9cdc13e7dc313bc26c03c84ba663c8d34c7))

  Running or debugging tests through a wrapper did not work from the
  editor, where robotcode runs from a bundled path instead of being
  installed in the interpreter. Two things are fixed:

  - The debug launcher no longer applies the wrapper itself; it forwards a
    launch.json wrapper to robotcode as --wrapper and lets robotcode apply
    it (so a launch.json wrapper still overrides the profile's).

  - When robotcode re-executes itself under the wrapper it re-runs through
    the same entry it was started from (--launcher-script) instead of
    python -m robotcode.cli, which the bundled interpreter cannot import.
    ROBOTCODE_BUNDLED_ROBOTCODE_MAIN is deliberately not used for this: VS
    Code sets it in every terminal, so it would divert a directly started
    robotcode to the bundled copy.


#### VS Code

- Adapt to vscode-languageclient 10 type changes ([95f305a](https://github.com/robotcodedev/robotcode/commit/95f305ae6f402287f2cb0d2ac5028acc4695a69c))

  Bumping vscode-languageclient to 10.1.0 broke the typecheck:
  LanguageClient now requires a LogOutputChannel instead of a plain
  OutputChannel, and Diagnostic.message can now be a MarkupContent
  instead of just a string.

- Restore -I and -N options when running tests ([c76b113](https://github.com/robotcodedev/robotcode/commit/c76b113936599446b9fdae20c6f9441f9a77be43))

  Running a single test, a file, or any subset from the Test Explorer
  again passes Robot Framework's parse-include (-I) and top-level suite
  name (-N) options. Since 2.6.0 both were missing, so on Robot Framework
  6.1+ the run parsed the whole workspace and surfaced parse errors from
  unrelated files.

  Robot Framework's --parseinclude support is now reported as a
  per-project fact on the discovery result envelope. In the
  `robotcode discover -f json` output this is the new
  `supportsParseInclude` key on the result (replacing the previous
  `needsParseInclude` key on each item).



### <!-- 2 -->Documentation

#### News

- Add v2.7.0 release notes ([033e12d](https://github.com/robotcodedev/robotcode/commit/033e12d90d8250513c5805113266996bae512680))

  Announce the test-run wrapper, the trustworthy analysis cache, and the
  restored -I/-N options for Test Explorer subset runs.



## [2.6.2](https://github.com/robotcodedev/robotcode/compare/v2.6.1..v2.6.2) - 2026-06-15

### <!-- 1 -->Bug Fixes

#### VS Code

- Refresh the Test Explorer after a language server restart ([0098190](https://github.com/robotcodedev/robotcode/commit/00981905c0d192eba07c7227d2dc80ef7cd00c16))

  - test items and run buttons no longer vanish until a window reload after a restart
  - a folder's tests are re-discovered when its language server restarts
  - run profiles are rebuilt once per restart instead of on every state change
  - a test run no longer hangs when a debug session fails to start
  - cancelling a run stops only that run, and works while it is still starting
  - a fixed error clears its decoration; stale diagnostics are cleared on an invalid environment
  - per-folder refresh, so one folder no longer interferes with another



### <!-- 2 -->Documentation

#### News

- Cover v2.6.2 alongside v2.6.1 in the release notes ([5beabad](https://github.com/robotcodedev/robotcode/commit/5beabad67d847e5929f3d1fdccb6c74329d488cb))
- Add v2.6.1 release notes ([3e1be81](https://github.com/robotcodedev/robotcode/commit/3e1be81d9b43d77a623acb3be5763c1a517e8381))


## [2.6.1](https://github.com/robotcodedev/robotcode/compare/v2.6.0..v2.6.1) - 2026-06-14

### <!-- 1 -->Bug Fixes

- Don't pull html-to-markdown into the 'all' extra ([6bf2a6d](https://github.com/robotcodedev/robotcode/commit/6bf2a6d1b41976683f50a36e21fac3ddf26ec12a))

  Since version 2.0 html-to-markdown ships as a Rust extension with prebuilt wheels only for a limited set of platforms (manylinux x86_64/aarch64, macOS, win_amd64). On other targets such as 32-bit Raspberry Pi OS (armv7l) or Alpine/musllinux, pip falls back to a source build that needs a Rust toolchain and fails, which broke 'pip install robotcode[all]'.

  html-to-markdown only improves HTML log conversion in the 'results' command and has a built-in stdlib fallback, so it is now opt-in via 'pip install robotcode-runner[html]'.

#### Language Server

- Prevent inconsistent Robocop formatting ([e31ed32](https://github.com/robotcodedev/robotcode/commit/e31ed32fcf6c51b10aa76c56b1bea64d5f1f2ea0))

  Formatting a file with Robocop repeatedly no longer oscillates between states (for example a blank line being added and removed before a section header on every other format). The formatter mutated the shared, cached document model in place; it now works on a fresh, uncached model so repeated formatting stays idempotent.


#### Robot

- Recover automatically from a corrupt cache database ([2ec7a9c](https://github.com/robotcodedev/robotcode/commit/2ec7a9c149eb1771ecf02832bafe409c252cbce3))

  The workspace cache database could become corrupt ("database disk image
  is malformed"). Once that happened nothing recovered: restarting the
  language server kept failing while opening the cache, and "Clear Cache
  and Restart Language Servers" failed too because it cleared entries
  through the already-damaged database.

  RobotCode now detects a corrupt cache database, discards it (including
  its -wal/-shm sidecars) and rebuilds it from scratch, so the keyword
  view, test discovery and the clear-cache command keep working without
  any manual cleanup. If the file cannot be removed or reopened (for
  example while another editor window holds it open), it falls back to a
  temporary in-memory cache for the session instead of failing to start.

  Access to the cache is now serialized so it stays consistent under the
  language server's concurrent requests, and memory-mapped reads are
  disabled on macOS, where they could leave a corrupt page behind.


#### VS Code

- Drop selected profiles that no longer exist in the config ([e3bad18](https://github.com/robotcodedev/robotcode/commit/e3bad18f24aaba6b4a71a696a390361ba1c5ce0e))

  When a profile was selected and then removed from robot.toml — for
  example after switching git branches — the selection stayed active.
  This produced a "profile not found" error on every test run, and the
  profile could not be deselected because the selection menu refused to
  open when no profiles were left to choose from.

  Now opening "Select Configuration Profiles" removes any selected
  profile that is no longer defined in the configuration and shows a
  message listing which profiles were removed. If the available profiles
  cannot be determined (e.g. an invalid environment), the current
  selection is left untouched.



### <!-- 2 -->Documentation

- Add reference page for excluding files with .robotignore ([d8990ec](https://github.com/robotcodedev/robotcode/commit/d8990ec5a4c8d1e8ec97b41548eeb9114b396007))

  Documents the .robotignore file: gitignore-style syntax, how it relates to .gitignore (it replaces it rather than merging), nested files, what RobotCode skips by default, where it applies (discovery, analysis, and the language server), how to verify the result with `robotcode discover files`, and how to use it to speed up analysis on large projects.

  Also links the new page from the discover `files` reference.

#### Ai-agents

- Foreground the debugger over the REPL ([0c40394](https://github.com/robotcodedev/robotcode/commit/0c40394d97b503ba05f7bb72d1a988c837ccb61f))

  Make robot-debug the primary tool for working with a real test and
  the REPL the narrower fallback for exploring when no test exists yet.
  Add debugger examples, a debugger-first core-habit entry, a
  troubleshooting item for chasing a failing test instead of debugging
  it, and note that agent output capture and the plain backend apply to
  robot-debug too.



## [2.6.0](https://github.com/robotcodedev/robotcode/compare/v2.5.1..v2.6.0) - 2026-06-09

### <!-- 0 -->Features

- Add inline documentation and examples to robot.toml.json ([825f891](https://github.com/robotcodedev/robotcode/commit/825f891391ac30e44aad17b686e3424db13587e1))

  Users now get rich documentation directly in their editor when editing
  robot.toml configurations through JSON schema integration. The schema works
  seamlessly with the Even Better TOML VS Code extension
  (https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml),
  which is powered by Taplo.

  Enhancements to robot.toml.json:
  - Comprehensive inline documentation (markdownDescription) for every field
  - TOML code examples extracted from configuration docs
  - Direct links to RobotCode documentation via Taplo integration
  - Full compatibility with Even Better TOML and other Taplo-based editors

  Improvements to schema generator:
  - Complete type hints for all inner functions
  - Detailed docstrings for better code clarity
  - More robust TOML code block extraction regex

#### Analyze

- Add --code filter to code subcommand ([4bfc339](https://github.com/robotcodedev/robotcode/commit/4bfc339e1d84cd07fc17dfb949d0fc5c41802431))

  `--code` restricts the result to the given diagnostic codes (e.g.
  `KeywordNotFound`), repeatable and comma-separated, matched
  case-insensitively like the modifiers. Unlike `-mi "*"` + re-include, it
  filters without changing the severity of what remains. It affects the
  output, summary and exit code, and combines with --severity using AND.

- Add --severity filter to code subcommand ([f565c16](https://github.com/robotcodedev/robotcode/commit/f565c1672561f5e96a31dcf8216f671fb4c6ac1a))

  `--severity` restricts the analysis result to the listed severities
  (repeatable and comma-separated; error/warn/info/hint). Filtered-out
  severities are dropped from the output, the summary counts and the exit
  code alike, so all three stay consistent. It's orthogonal to
  --exit-code-mask (which only masks the exit code) and complements the
  diagnostic modifiers (which remap rather than filter).

- Add SARIF, GitHub and GitLab output formats ([7103836](https://github.com/robotcodedev/robotcode/commit/7103836cef38a0d0fab37e7bf791958ebb20f57c))

  `robotcode analyze code` gains a local `--output-format` flag (overrides
  the global `--format` for this command) with these values:

  - `concise` (default): the human-readable text output
  - `json` / `json-indent`: structured result (diagnostics + summary)
  - `sarif`: SARIF 2.1.0 log for GitHub code scanning and other consumers
  - `github`: GitHub Actions workflow annotations (`::error file=...`)
  - `gitlab`: GitLab Code Quality report (JSON array)

  `--output-file FILE` writes the report to a file instead of stdout (for
  the json/json-indent/sarif/github/gitlab formats), which is handy for CI
  artifact upload. A missing target directory raises a clear UsageError and
  other I/O errors surface as a ClickException instead of a traceback.

  Mapping details shared across the machine formats:
  - LSP 0-based ranges become the 1-based positions SARIF/GitHub expect
  - severities collapse onto each format's levels (e.g. SARIF error/warning/
    note, GitHub error/warning/notice, GitLab major/minor/info)
  - artifact paths are POSIX and relative to the project root (what the CI
    integrations expect); `--full-paths` switches to absolute paths
  - SARIF and GitLab results carry a stable fingerprint (independent of line
    number) so alerts survive unrelated edits
  - GitHub property/message values are escaped per the @actions/toolkit rules

- Add JSON output and --full-paths to code subcommand ([fc76cf3](https://github.com/robotcodedev/robotcode/commit/fc76cf37251049697ebbfc7fe8670c5d45912409))

  `robotcode --format json analyze code` (and `--format json_indent`) now
  emit a structured result instead of falling back to plain text:

  - `diagnostics`: a map of source path to LSP diagnostics, using the same
    shape as the `discover`/`results` commands so editor and CI integrations
    can reuse their parsers. Workspace-level diagnostics key on ".".
  - `summary`: file count and per-severity totals.

  The JSON always carries the full diagnostic message (tracebacks included);
  `--show-tracebacks` only affects the text output.

  New `--full-paths/--no-full-paths` flag (mirroring `discover`) switches
  between root-relative and absolute paths in both text and JSON output.
  JSON keys are always rendered POSIX-style for cross-platform stability.

- Polish code subcommand output ([1049b79](https://github.com/robotcodedev/robotcode/commit/1049b79a1323aec66a350674bc823372bc76fbca))

  - Output is now sorted by (file, line, column) so warnings and errors
    appear in source order instead of mixed by analyzer pass.
  - Severity is rendered as a full word, e.g. `[ERROR]` instead of `[E]`,
    matching the convention from Robocop, ruff, mypy and friends.
  - Robot Framework's appended Python tracebacks and PYTHONPATH dumps are
    no longer printed by default; the new `--show-tracebacks` flag opts
    back into the full message.
  - Multi-line diagnostic messages (e.g. `MultipleKeywords` listing the
    alternative names) are re-indented with a consistent prefix.
  - Related-information entries are prefixed with `-> ` to set them apart
    visually, and they fall back to `(see related location)` when Robot
    Framework provides no secondary message.


#### CLI

- Detect GitHub Copilot agent sessions ([dbc5603](https://github.com/robotcodedev/robotcode/commit/dbc560384cc224c0c132f86aa135e9159a334b0c))

  Adds two markers to the AI-agent auto-detection so terminal commands
  invoked from Copilot get the same clean-output defaults (no color,
  no pager, REPL plain backend) as sessions from Claude Code, Cursor,
  Codex, and friends:

  - COPILOT_AGENT — set by VS Code Copilot Chat / agent mode in
    terminals launched via run_in_terminal
    (microsoft/vscode#311734).
  - COPILOT_AGENT_SESSION_ID — set on every shell command and MCP
    server the standalone GitHub Copilot CLI spawns (>= 0.0.429).

- Adapt automatically to AI agent sessions ([8b34a33](https://github.com/robotcodedev/robotcode/commit/8b34a33454319e585769711540c4516db52ce3f9))

  When `robotcode` is invoked from inside an AI agent (Claude Code,
  Cursor, Copilot CLI, OpenCode, Codex, Gemini, …) it now drops
  coloured output, the pager, and the REPL's interactive prompt
  features — so the agent sees clean line-by-line text instead of
  ANSI escapes and popup ghosts.

  Explicit flags and the usual environment variables (`NO_COLOR`,
  `FORCE_COLOR`, `ROBOTCODE_REPL_PLAIN`, `ROBOTCODE_REPL_BACKEND`)
  still override the detection. `ROBOTCODE_NO_AI_AGENT=1` opts out
  when you want the full experience anyway; `ROBOTCODE_FORCE_AI_AGENT=1`
  turns the agent-mode on for local repros.

- Auto-detect when to emit colors, honor NO_COLOR and FORCE_COLOR ([4bbf944](https://github.com/robotcodedev/robotcode/commit/4bbf9448889f4b7563aeb887f9a0d828ce3d4ad6))

  ANSI escape codes no longer leak into piped output, files, log captures or
  CI artefacts — colors are auto-disabled when stdout/stderr isn't a TTY.
  The NO_COLOR and FORCE_COLOR environment variables are now respected.
  stdout and stderr are decided independently, so warnings keep their colour
  when stdout is piped but stderr is still on the terminal. Explicit `--color`
  / `--no-color` still override everything.


#### Language Server

- Use the SemanticModel for the "Create Keyword" and "Assign Result to Variable" code actions ([6a3d5a3](https://github.com/robotcodedev/robotcode/commit/6a3d5a397af47ac70bed6701df1bc71f0789346c))

  When the experimental SemanticAnalyzer is enabled, the "Create Keyword"
  quick fix (offered for unknown keywords) and the "Assign keyword result
  to variable" refactor read the keyword call's namespace, library entry
  and assignment state from the SemanticModel instead of walking the AST
  and re-resolving via ModelHelper. Output unchanged — covered by
  dedicated equivalence test files for both code actions.

- Use the SemanticModel for the "Open Documentation" code action ([0768c84](https://github.com/robotcodedev/robotcode/commit/0768c84b0448e012173dfd7fd5ebcbdc7eafda86))

  When the experimental SemanticAnalyzer is enabled, the "Open Documentation"
  code action reads the pre-resolved keyword data and SemanticTokens from
  the model instead of looking the keyword up again on every request.
  Output is unchanged — verified by the existing E2E suite under both paths
  and a new equivalence test file.

- Use the SemanticModel for signature help ([9415e86](https://github.com/robotcodedev/robotcode/commit/9415e8613c909618fa398ab81640e37f6744b8f2))

  When the experimental SemanticAnalyzer is enabled, signature help reads
  the pre-resolved keyword data from the SemanticModel instead of looking
  the keyword up again on every request. Output is unchanged — verified by
  running the existing regression suite under both paths and a dedicated
  equivalence test file.


#### REPL

- Suggest the setting-import aliases in tab-completion ([6507af5](https://github.com/robotcodedev/robotcode/commit/6507af58119417f7c691f567364b05abae340830))

  Typing at the prompt now suggests `Library`, `Resource`, and `Variables` next to the keywords, and completing their argument offers the same libraries, resources, and variable files as `Import Library` / `Import Resource` / `Import Variables` — so the Settings-style aliases are as discoverable as the keywords they stand for. Offered only at the interactive prompt, where they apply.

- Make the interactive shell and debugger more consistent ([1a11c80](https://github.com/robotcodedev/robotcode/commit/1a11c803234c243f44340e7c240ed567f8b433f9))

  Several rough edges in the interactive shell and its command-line debugger are smoothed out, so it behaves consistently — both with the rest of Robot Framework and within itself:

  - **Failures behave like a shell, not a debugger.** A failing keyword prints its error and leaves you at the prompt; the debugger only steps in when asked for, and switching it off keeps your breakpoints so switching it back on picks up where you were. (`robotcode robot-debug` is unchanged for debugging a real run.)
  - **Imports work like they do in a suite.** Write `Library`, `Resource`, or `Variables` at the prompt just as under `*** Settings ***`; saved sessions keep that familiar layout.
  - **The debugger speaks one language.** Its commands and messages now follow one short, uniform style instead of a mix of phrasings and cryptic notes.

- Add an interactive command-line debugger ([8e62733](https://github.com/robotcodedev/robotcode/commit/8e6273397ae80f0718351425320c31d6209a1bc0))

  Debug Robot Framework runs straight from the terminal — pause a run, see
  where you are, inspect and change state, run keywords in the live context,
  and step through execution, no editor required. It's the scriptable,
  terminal-native counterpart to the VS Code extension's graphical debugger.

  - **Two ways in.** `robotcode robot-debug <paths>` (alias `run-debug`) runs a
    real suite through the normal runner with the debugger attached — same
    output, options and arguments as `robotcode robot`, and the run keeps
    streaming as you step, continue or detach. `robotcode repl` (alias `shell`)
    now has the debugger built in too, so breakpoints fire while you try
    keywords at the prompt.
  - **Pause where you want.** Line and keyword breakpoints (`--break
    login.robot:42`, `--break "Open Browser"`), an embedded `Breakpoint` step in
    a `.robot` file, `--stop-on-entry`, and breaking on failures (uncaught
    failures by default, plus `--break-on-all-exceptions`, `--break-on-failed-test`
    and `--break-on-failed-suite`). Every stop shows why, which keyword, and where.
  - **Step through it.** `.step`/`.next`/`.return`/`.continue`/`.until`, plus
    `.detach` (stop debugging but let the run finish) and `.abort` (end it now).
  - **Inspect and change state.** Walk the call stack (`.where`/`.up`/`.down`/
    `.frame`), list variables by scope (`.vars`), evaluate in the selected frame
    (`.print`/`.pprint`/`.whatis`), auto-show expressions at every stop
    (`.display`), set variables (`.set`), and run any keyword right at the prompt
    in the paused context.
  - **Manage breakpoints live.** List them and add conditional, one-shot,
    logpoint or command-list breakpoints; set conditions, ignore N hits, delete,
    and disable/enable by number (`.breakpoints`/`.condition`/`.ignore`/`.delete`/
    `.disable`/`.enable`/`.commands`/`.tbreak`). Arm exception breakpoints on the
    fly with `.catch`.
  - **Read source and docs in place.** `.list` shows the source at the stop,
    `.source <kw>` a named keyword's definition; the full shell command set
    (`.kw`, `.doc`, `.imports`, `.save`, …) works at the debug prompt too. On the
    rich prompt these open in a scrollable full-screen viewer with search and
    links; on the plain prompt they print inline.
  - **Built for humans and agents alike.** Context-aware completion, syntax
    highlighting, persistent history and multi-line editing on the rich prompt;
    `--plain` (or `--backend` / `ROBOTCODE_REPL_*`) gives a bare prompt that reads
    commands from stdin, and the rich prompt falls back to plain automatically on
    piped input — so the debugger drives cleanly from scripts, CI or AI agents.
  - Long commands accept any unambiguous prefix; one-letter aliases mirror pdb.

- Browse and search keywords from .kw ([a884736](https://github.com/robotcodedev/robotcode/commit/a8847363ae6286cbb66d7cdf5f73d440a557a23c))

  `.kw` does more than show a single keyword now. With no argument it
  lists every keyword you have imported, grouped by the library or
  resource it comes from. With text that isn't an exact keyword name it
  lists the keywords whose name contains that text, so you can find a
  keyword without remembering its full name or leaving the REPL. Giving an
  exact keyword name still shows that keyword's full documentation as
  before.

  In the interactive documentation viewer the listed keyword names are
  links: Tab to one and press Enter to open its documentation, and press
  `[` to go back to the list — the same navigation the cross-reference
  links inside a library page already use. On the plain backend the list
  comes back as text.

- Document imported resources and aliased/argument libraries in .doc and .kw ([3d1665d](https://github.com/robotcodedev/robotcode/commit/3d1665d0eb6e28bf7db146b8ec5e4460397a942c))

  The `.doc` and `.kw` commands show documentation for the libraries,
  resources, and keywords you are working with in the REPL. They now cover
  everything the current session has imported and match how it was imported.

  `.doc` documents imported resource files, not just libraries — the
  resource introduction plus every keyword with its arguments and
  description. It also works for libraries that were imported with
  arguments, which previously could not be shown. Libraries and resources
  are addressed by the name they were imported under, so a library imported
  with an alias (`AS`, or the older `WITH NAME`) is found by that alias.

  `.kw` accepts the explicit `Owner.Keyword` form, e.g. `.kw BuiltIn.Log`,
  to pick a specific keyword when the same name is provided by more than one
  import; names resolve the same way they do in a suite. It now also shows
  full documentation for resource keywords, including the argument table.

  Running `.doc` or `.kw` on something you haven't imported tells you it
  isn't loaded instead of showing an empty page. The built-in help for both
  commands has been rewritten to read as user help rather than internal notes.

- Show a startup banner ([73eb26a](https://github.com/robotcodedev/robotcode/commit/73eb26a47b743856712c51cabb60e5b0bd30995a))

  When the REPL starts in an interactive terminal it now prints a
  Python-style banner with the RobotCode, Robot Framework, and Python
  versions, plus a hint about `.help` and `.exit`. The banner is skipped
  when stdin is piped/redirected or when running `--files` without
  `--inspect`.

- Documentation viewer and themed prompt out of the box ([dda4258](https://github.com/robotcodedev/robotcode/commit/dda42580c59e0d04f073afba8df78b25ac8a3b92))

  `.help`, `.kw`, and `.doc` (or F1 for help) open a built-in
  documentation viewer — a tiny terminal browser for Robot Framework
  docs without leaving your REPL session.

  - Search with `/`, jump between matches with `n`/`N`.
  - Click a link, or use Tab/Shift-Tab to step between them. Anchor
    links jump to the right section, web links open in your browser.
  - Walk back and forward through your reading history with `[` and `]`.
  - Scroll with the mouse wheel, or with j/k, PgUp/PgDn, g/G.
  - Pages use the same renderer the editor shows on hover: signature,
    argument table with types and defaults, tags, docstring, headings,
    lists, tables, code blocks.

  A single color theme covers the prompt, syntax highlighting, log
  lines (`INFO`, `WARN`, `ERROR`, …), and the documentation viewer.

  `prompt_toolkit` and `rich` are bundled with `robotcode-repl`, so the
  rich prompt experience is available out of the box. `--plain` (or
  `--backend=plain`) is available for AI-agent sessions and pipe
  workflows that need clean stdin/stdout.

- Same prompt experience on Linux, macOS, and Windows ([f8b8b15](https://github.com/robotcodedev/robotcode/commit/f8b8b15af4f668895d7fd82e7291f4dc2ef672fc))

  The interactive REPL ships with a single editor that behaves the
  same way on every platform. Install the `[prompt-toolkit]` extra
  to enable it:

      pip install 'robotcode-repl[prompt-toolkit]'

  You get a completion popup, syntax highlighting, signature toolbar,
  persistent history and Ctrl-R search. Without the extra the prompt
  degrades to a plain `input()` line read.

  The previously implemented readline-based path has been removed —
  its behaviour differed too much across platforms and had platform-
  specific bugs that weren't worth maintaining.

- --backend flag to force a specific input backend ([372afca](https://github.com/robotcodedev/robotcode/commit/372afcad1adb783cc30eef2d40ced521fe722ca5))

  Lets you exercise the readline (or plain) code path without
  uninstalling the prompt_toolkit extra:

      robotcode repl --backend=readline

- Dot-commands, ${_} last-result, signature hints, session export ([75cbdfd](https://github.com/robotcodedev/robotcode/commit/75cbdfd4dbc89b9ac9393d4bd94b23ffe60426d5))

  A grab-bag of power-user features for the interactive REPL:

  - Dot-commands intercepted before Robot's parser sees them — `.help`
    (with per-command drill-down via `.help <cmd>`), `.imports`, `.vars`,
    `.kw <name>`, `.doc <library>`, `.history`/`.history clear`/`.history
    del <N>`, `.cwd`, `.clear`, `.save [-a] [-t name] <file>`, `.exit`.
    Help text on each command documents its flags and shows examples.
  - `${_}` mirrors the last keyword's non-None return value, like Python's
    interactive `_`. Works in the next argument with no `${tmp}=` step.
  - F1 invokes `.help` from the prompt; Ctrl-R reverse-search now
    documented (was already wired via prompt_toolkit defaults).
  - Bottom row shows the active keyword's signature with the current
    argument highlighted when the cursor sits in an argument cell.
    Named-arg syntax (`html=True`) follows the spec position, not the
    positional cell index. Outside an argument cell the row is hidden so
    the prompt stays uncluttered.
  - Embedded-argument completion: `Literal[...]`-typed parameters on
    RF 7+ expose their allowed values as completion candidates after
    `name=`. Silently no-ops on RF 5/6.
  - `.save` writes the session to a runnable `.robot` file with imports
    hoisted into a `*** Settings ***` section.

  All features are prompt_toolkit-aware where it matters but degrade
  cleanly on the readline and plain backends.

- Session-context toolbar + completion/popup polish ([7e0c881](https://github.com/robotcodedev/robotcode/commit/7e0c8819201ae6c2db44dd4ad9f77927ddb1a3c6))

  Adds the bottom-toolbar feature from the original plan plus the
  last round of UX polish on the prompt_toolkit candidate popup
  that we shaved down through testing:

  - **Bottom toolbar** shows the running RF version and the cwd at
    all times — orientation info that's useful when juggling several
    venvs / project directories.
  - **Esc** closes the candidate popup and reverts any preview text
    that arrow-navigation had pinned, restoring the user's literal
    pre-popup buffer. Bound only when the popup is open
    (`has_completions` filter) so Esc keeps its Alt-chord prefix
    role everywhere else.
  - **Enter** on a highlighted candidate accepts it (popup closes,
    preview becomes permanent). For keyword completions Enter also
    cleans up the cell — deletes any leftover text after the cursor
    in the same cell (so a mid-cell completion replaces the whole
    keyword) and appends a cell separator if no argument follows.
  - **Tab** is smart: cycles through the popup when one is open,
    inserts a cell separator in argument context, opens the popup
    otherwise.
  - **Multi-line history** survives a session restart as one entry
    (newlines are escaped to `\\n` on disk so the file stays
    readline-compatible).
  - **Mid-keyword preview** renders cleanly — `${Lo}` cursor before
    `o`, picking `Log To Console` now shows `Log To Console`, not
    `Log To Consoleog` (we trim the forward-cell tail from the
    state's `original_document` before prompt_toolkit applies the
    preview).
  - **TEXT_FRAGMENT** in compound variable lookups (`${PREFIX_${X}}`)
    renders with the variable-name colour, not the argument colour,
    so the eye reads the whole concatenated name as one identifier.
  - **EOL / EOS** tokens from Robot's tokenizer are dropped from the
    rendered fragments — `\\n` inside a fragment would otherwise show
    as `^J` at the end of every multi-line buffer line.
  - **Trailing whitespace** is padded out to the document's actual
    length so the cursor stays in sync with the buffer (was sticking
    at column 0 when the user kept typing spaces).
  - **`_completion.py`** is consolidated — `candidates_for()` is now
    a thin projection over `candidates_for_rich()`, ~200 lines of
    duplicated helpers removed (was an artefact of how the rich
    variant was added in the previous commit).
  - **`CELL_SEPARATOR`** + **`find_cell_end()`** added to
    `_completion.py` as named constants and a shared helper, used by
    the smart-Tab / Enter-cleanup paths.

- Doc hints next to completion popup candidates ([c891215](https://github.com/robotcodedev/robotcode/commit/c891215077faba3da8f1d552cc45728c22730170))

  The `prompt-toolkit` candidate popup now shows a short context line
  next to each candidate (prompt_toolkit's `display_meta`), so you
  know *what* a candidate is before picking it:

  - **Keywords**: first line of the keyword's docstring next to the
    name (`Log a message with the given level` next to `Log`, etc.)
  - **Library / resource / variables imports**: the discovery kind —
    `MODULE_INTERNAL` for built-ins, `MODULE` for third-party,
    `RESOURCE` for `.resource` files, `FILE` for filesystem hits
  - **Variables (`${…}`/`@{…}`/`&{…}`)**: `repr(value)[:40]` of the
    current value in the live suite scope
  - **Environment variables (`%{…}`)**: `repr(os.environ[name])[:40]`

  Backed by a new `candidates_for_rich()` API parallel to the
  existing `candidates_for()` — keeps the readline backend's path
  zero-cost (it can't render two-column popups anyway). Works on
  RF 5/6/7+ with the same attribute-name version-switch
  (`short_doc` ↔ `shortdoc`) the rest of the package already uses.

- Robot-aware syntax highlighting at the prompt ([a35b252](https://github.com/robotcodedev/robotcode/commit/a35b252576ad9b6a2ca2d382d0e6f470da29368f))

  When the `prompt-toolkit` extra is installed, the prompt now paints
  Robot Framework syntax in colour. Keywords, arguments, assigns,
  comments, block constructs (`FOR`, `IF`, `END`, …), BDD prefixes
  (`Given`, `When`, `Then`, … plus localised variants from RF 6+) and
  variables all render distinctly.

  Variables decompose to the part level: sigil and braces, base name,
  type hints (`${age: int}`), default values (`%{HOME=default}`),
  subscripts (`${dict}[key]`), nested forms (`${${inner}}`), and
  inline-Python expressions (`${{expr}}`) all get their own colour.

  The highlighter uses Robot's own production tokenizer
  (`robot.api.get_tokens`) plus the `robotcode` semantic analyzer's
  variable decomposer — the same code path the RobotCode VS Code
  extension uses for semantic-token rendering. Colour assignments
  mirror the LSP semantic-token mapping, so the REPL prompt and the
  VS Code editor use a consistent palette.

  No additional dependency: Robot is already required by
  `robotcode-repl`, and the variable decomposer ships with
  `robotcode-robot`. Works on RF 5, 6, and 7+ (BDD-prefix
  localisation requires RF 6+; English defaults apply on RF 5).

- Multi-line buffer with block-aware auto-indent ([8cfcc4c](https://github.com/robotcodedev/robotcode/commit/8cfcc4c97adaa8137af435b341fbd20e44267413))

  When you open a Robot block (`FOR`, `WHILE`, `IF`, `TRY`, `GROUP`),
  the next line of input is auto-indented to the matching depth.
  `END` pops one level. Nested blocks stack — `IF` inside `FOR` lands
  at depth 2.

  Behaviour differs slightly between backends:

  - **readline** (always available): each continuation line is its own
    `input()` call. The `... ` prompt seeds the buffer with the right
    number of spaces via `set_pre_input_hook`. You type from there.
  - **prompt-toolkit** (with the optional extra): one multi-line
    buffer per top-level statement. Plain **Enter** is smart — submits
    when the block is balanced, otherwise inserts a newline +
    auto-indent so you keep typing inside. **Alt-Enter** (`Esc`
    `Enter`) and **Ctrl-J** always insert a newline + auto-indent,
    even when balanced. Cursor-Up/Down navigates inside the buffer.

  Shift-Enter is intentionally not bound — most terminals can't
  deliver it distinctly from plain Enter. Alt-Enter and Ctrl-J cover
  the use case portably.

- `--plain` flag to skip all prompt enhancements ([bf9fc5b](https://github.com/robotcodedev/robotcode/commit/bf9fc5b22b671316d74caccd530b9ddcc948e666))

  `robotcode repl --plain` (or `ROBOTCODE_REPL_PLAIN=1`) bypasses the
  prompt-toolkit / readline cascade and falls back to a bare `input()`
  call — no history, no Tab-completion, no candidate popup, no
  auto-suggest, no syntax highlighting.

  Recommended for:

  - AI-agent invocations where ANSI escapes from the candidate popup
    would corrupt the stdout capture the agent reads back
  - Automation pipelines and CI that pipe input via heredoc
  - Wrapper scripts that need a deterministic, side-effect-free prompt

  `--plain` and `--no-history` are orthogonal — plain mode has no
  history file anyway, but combining the two is safe and does not
  raise.

- Live as-you-type completion with prompt_toolkit ([b449e1b](https://github.com/robotcodedev/robotcode/commit/b449e1b07cfd9e583a63f297b9e6168f69f5ebd6))

  `pip install 'robotcode-repl[prompt-toolkit]'` swaps the readline
  frontend for one driven by `PromptSession`:

  - **Live candidate popup** under the cursor as you type — no Tab
    needed (though Tab still works). Arrow-keys pick, Enter accepts.
    The verbose `Import Library  Foo` / `Import Library  Bar` row
    layout is replaced by just the labels.
  - **Fish-style auto-suggest** — last matching line you typed shows
    greyed-out behind the cursor, right-arrow accepts it.
  - **Ctrl-R** reverse search with a dedicated UI, bracket auto-match,
    multi-line cursor movement inside open blocks.

  The completer runs in a background thread (`complete_in_thread=True`)
  so the popup never blocks the UI, and Robot's expensive
  `complete_*_import(None, …)` filesystem / `sys.path` discovery is
  cached for the session — even with hundreds of importable modules,
  only the first keystroke pays the walk cost.

  Candidate sourcing reuses the same Robot-aware logic the readline
  backend uses, and the history file is shared on disk between the
  two backends — swapping extras (or having neither) doesn't lose
  arrow-up recall.

- Tab completion for keywords, variables, imports ([72cdbc2](https://github.com/robotcodedev/robotcode/commit/72cdbc29594ad972945bad9c216e9436f6d2438a))

  Tab now completes Robot-aware:

  - keyword names at the start of a cell, sourced from every loaded
    library and imported resource (case + whitespace + underscore
    insensitive — matches Robot's own resolution rules)
  - `${...}` / `@{...}` / `&{...}` variables from the live suite scope,
    and `%{...}` environment variables from the process environment
  - `Import Library` arguments — plain identifiers (`Coll<Tab>` →
    `Collections`), dotted module paths (`robot.libraries.Coll<Tab>` →
    `robot.libraries.Collections`), and filesystem paths (`./libs/My<Tab>`
    → `./libs/MyLib.py`)
  - `Import Resource` arguments — `.robot` / `.resource` files only
  - `Import Variables` arguments — `.py` / `.yaml` / `.yml` / `.json`
    variable files plus discoverable variables modules

  Works across Robot Framework 5, 6, and 7+.

  On Pythons whose stdlib `readline` is backed by libedit (macOS system
  Python, some uv / python-build-standalone builds), install the
  `gnureadline` extra for full GNU readline behaviour:
  `pip install robotcode-repl[gnureadline]`.

- `--no-history` flag for ephemeral sessions ([1c28b57](https://github.com/robotcodedev/robotcode/commit/1c28b57c8d9a1f78a08c72926992f7ff8d8b675b))

  `robotcode repl --no-history` skips loading and saving the persistent
  history file. Arrow-up still recalls lines from the current session;
  nothing leaks across sessions. Useful for AI-agent invocations, quick
  spike sessions, or working with secrets you don't want sitting in
  `.robotcode_cache/repl_history`. Also picked up from the
  `ROBOTCODE_REPL_NO_HISTORY` env var, which is handier when the REPL
  is launched by a wrapper script.

- Fish-style history dedup and configurable size ([1c93402](https://github.com/robotcodedev/robotcode/commit/1c9340283f4720cfdede25682f3a7734b6d0fd27))

  Re-running a command that's already in the history no longer leaves
  the older copy behind — only the most recent invocation survives, so
  arrow-up cycles through *unique* commands (the same behaviour fish
  shell ships). Legacy history files with duplicates are cleaned up on
  first load.

  The buffer size is now configurable via the `ROBOTCODE_REPL_HISTORY_SIZE`
  environment variable; default stays at 1000 entries.

- Persistent line history across sessions ([9c99f43](https://github.com/robotcodedev/robotcode/commit/9c99f43b282680d1b7db9edd0afe263c25a57684))

  `robotcode repl` now remembers the lines you typed and recalls them
  with Pfeil-hoch / Ctrl-R, just like Python's own shell or bash. The
  history file lands in your project's `.robotcode_cache/` when one is
  detected, otherwise in the per-user cache directory. `ROBOTCODE_CACHE_DIR`
  overrides both.


#### Robot

- Enable bottom-up navigation in the SemanticModel ([a87fc79](https://github.com/robotcodedev/robotcode/commit/a87fc7930cf62114dae23cca9cea0a1a5c97b8d3))

  Every SemanticNode now carries a `parent` back-pointer, so LSP features
  that start from a token or statement can walk up to the enclosing block,
  section, or definition without re-querying the model by line. Comes with
  helpers `enclosing_definition_block`, `enclosing_block_of_kind`,
  `enclosing_section`, and `path_from_root` on `SemanticModel`.

  Parent is typed as `SemanticNode` (not `SemanticBlock`) so it can also
  point at a Statement — `RunKeywordCallStatement.inner_calls` are
  parented to their outer Run-Keyword statement.

- Pre-resolve more semantic data so LSP features can read it once ([be36e61](https://github.com/robotcodedev/robotcode/commit/be36e617ba8be7a564ccccd87acfa5f71ddbae59))

  Inlay Hints now read from the SemanticModel instead of doing a second
  analysis pass. The model gains a real block hierarchy (FOR/WHILE/IF/TRY/
  GROUP), pre-resolved init keyword docs on Library/Variables imports,
  and consolidated header-token construction so future LSP feature
  migrations stop re-walking the AST.

  The old AST-walk path stays as fallback while
  `robotcode.experimental.semanticModel` is off; both paths must produce
  identical hints (covered by parametrized equivalence tests across all
  supported RF versions).

- Implement cross-platform file locking for data cache ([8ae4aec](https://github.com/robotcodedev/robotcode/commit/8ae4aec35048b8c4b65874a90fbc15bb162ef3dd))

  Replace the Unix-only flock-based locking with a platform-dispatched
  implementation using LockFileEx/UnlockFileEx (Windows) and fcntl.flock
  (Unix/macOS). The Windows path previously had no-op early returns,
  meaning the exclusive lock used by `cache prune` provided no actual
  protection on Windows.

- Introduce SemanticModel for richer Robot Framework analysis (Part 1) ([23a538c](https://github.com/robotcodedev/robotcode/commit/23a538cbb3105ac52696dedf85e861e6cca9b6c5))

  Introduce the first part of an opt-in SemanticModel that provides deeper
  static analysis of Robot Framework files, available behind a feature flag.

  Enable via robot.toml:

      [tool.robotcode-analyze]
      semantic-model = true

  or in VS Code settings:

      "robotcode.experimental.semanticModel": true

  - Nested variable resolution: variables like ${DICT_${key}} are now
    statically resolved where possible, with diagnostics when resolution
    fails
  - Richer semantic highlighting: token classification driven by the
    semantic model instead of syntactic heuristics
  - RF 7.4 type hint support: KeywordName/KeywordArgument annotations are
    recognized for run-keyword detection
  - Log output to verify which analyzer is active
  - Robust deserialization of cached library data when new fields are added

  The SemanticModel is disabled by default. Further parts will add
  additional LSP feature migrations and extended analysis capabilities.


#### Runner

- Extend `results` & `discover` search and add `log --keyword-info` / `--suite-info` ([9559316](https://github.com/robotcodedev/robotcode/commit/95593168aa3b8883e94edcd602ee09c5afc212bf))

  `--search` / `--search-regex` reach more places now. On top of the
  existing test name / body / tags targets, they also hit:

  - every executed keyword's `[Documentation]`, `[Tags]` and `[Timeout]`
    — answer questions like "which tests touched a keyword tagged `slow`"
    or "which tests called a keyword whose docstring mentions
    rate-limiting".
  - any ancestor suite's `Documentation` or `Metadata` — a hit on a
    suite-level field keeps every test underneath, so
    `--search "API tests"` picks up every test in a suite whose
    docstring reads "API tests" without enumerating names.

  Both rules apply to `results` and `discover` alike.

  `results log` gains two opt-in views (default off — the plain log
  stays compact):

  - `--keyword-info` prints each executed keyword's `[Documentation]`,
    `[Tags]` and `[Timeout]` under its header, so the log shows what
    each keyword *is*, not just what it was called with.
  - `--suite-info` groups tests under a `Suite:` header that carries
    the suite's name, source, status, `Documentation` and `Metadata`
    — useful when scanning a multi-suite run to see at a glance which
    suite a test belongs to and what it's about.

  They compose: `log --suite-info --keyword-info` gives a structured
  view that mirrors the layout of the original `.robot` files.

- Add `--search` / `--search-regex` to `discover` commands ([ce8c783](https://github.com/robotcodedev/robotcode/commit/ce8c783cddde8f51734e7f4c40a6775026c76a1f))

  `discover all` / `tests` / `tasks` / `suites` / `tags` / `files` now
  support the same search flags as the `results` family. Filtering runs
  through a `SearchModifier` SuiteVisitor wired into the existing
  `prerunmodifier` slot, so the `Collector` only ever sees the surviving
  tree — statistics, ancestor suites and the tag aggregate fall out of
  that automatically.

  Search targets per test: name, full name, source path, documentation,
  template, timeout, tags (normalisation-aware), and the full body —
  keyword names, arguments, assigned variables, FOR/WHILE/IF conditions,
  VAR/RETURN values, EXCEPT patterns, GROUP names, plus setup/teardown.
  TEXT output highlights matches in name/source/tags/path; JSON output
  echoes the pattern in `filtersApplied`.

  To avoid duplication, the search infrastructure moves into a shared
  `runner/cli/_search.py` module: `SearchMatcher` (with a model-agnostic
  `matches_body` method that walks both `robot.running` and `robot.result`
  body trees via duck-typing), `make_search_matcher`, `make_highlighter`
  and the new `SearchModifier`. `results.py` and `_render.py` switch to
  the shared module and drop their local copies.

- Add the standard result filters to `results diff` ([a10f6ce](https://github.com/robotcodedev/robotcode/commit/a10f6ce78944a36bcbe86571ff99f7a3277d0b0e))

  `results diff` now accepts the same filter options as the other `results`
  subcommands: `--status`, `-i/--include`, `-e/--exclude`, `-s/--suite`,
  `-t/--test`, `-bl/--by-longname`, `-ebl/--exclude-by-longname`, plus
  `--search` / `--search-regex`. Each filter is applied identically to
  both baseline and current before the diff, so the comparison can be
  scoped to a single suite, tag pattern, name, or message snippet:

  ```
  robotcode results diff baseline.xml -s "MyProject.Login"
  robotcode results diff baseline.xml -i smoke
  robotcode results diff baseline.xml --search TimeoutError
  robotcode results diff baseline.xml -bl "MyProject.Login.Bad Password"
  ```

  `DiffResult` gains a `filtersApplied` field (additive, optional) so the
  JSON output records the filters in the same shape used by the other
  result models.

- Add `-bl/--by-longname` and `-ebl/--exclude-by-longname` to results filters ([33697cb](https://github.com/robotcodedev/robotcode/commit/33697cba2d2e354289b3612c3c96a80f8e202767))

  `robotcode results` now accepts long-name filters alongside the existing
  `--status`, `-i/--include`, `-e/--exclude`, `-s/--suite`, `-t/--test`
  options. Pick a specific test or suite by its full long name (exact
  match), or exclude a branch of the tree the same way:

  ```
  robotcode results show -bl "MyProject.Login.Bad Password"
  robotcode results summary -ebl "MyProject.Slow Suite"
  robotcode results stats --by tag -bl "MyProject.Smoke"
  robotcode results log -bl "MyProject.Login" -bl "MyProject.Logout"
  ```

  Both options compose with the existing filters and `--search` /
  `--search-regex`, and surface in JSON `filtersApplied` as `by-longname`
  / `exclude-by-longname` for CI consumption. Available on `summary`,
  `show`, `log`, and `stats`.

  Along the way, trimmed redundant "repeat for OR" notes from option help
  texts — Click already shows the `*` marker on repeatable options.

- Split `--search` and `--search-regex`, add to `summary` and `stats` ([89c2952](https://github.com/robotcodedev/robotcode/commit/89c2952dc33d44b11630831a78b3c9aaa1799dac))

  `--search-regex` is now a standalone option that accepts a pattern instead
  of a boolean flag — you no longer have to spell out both `--search TEXT
  --search-regex`. The two options are mutually exclusive:

  - `--search TEXT` — case-insensitive substring match (`open browser`,
    `TimeoutError`, …)
  - `--search-regex PATTERN` — Python regex, honoured as written. Use
    `(?i)pattern` for case-insensitive matching, just like in any regex
    engine.

  Both options now work on `summary`, `show`, `log`, and `stats`, so the
  same search vocabulary applies across the whole `results` family:

  ```
  robotcode results summary --search TimeoutError
  robotcode results stats --by tag --search Browser
  robotcode results show --search-regex "AssertionError.*"
  robotcode results log --search "Open Browser"
  ```

  Search traverses the raw output tree (test attributes plus keyword names,
  arguments, and log messages), so a single search reaches into the
  execution body without first materialising the full per-test log.

- Add `results diff` for comparing two runs ([bbdcf33](https://github.com/robotcodedev/robotcode/commit/bbdcf337b010c9110e68ee0c7c896c3538c3764b))

  `results diff BASELINE [CURRENT]` compares two `output.xml` / `output.json`
  files and reports tests whose status changed, plus tests that appeared or
  disappeared between the runs. Categories:

  - **New failures** — passed in baseline, fails in current
  - **New passes** — failed or skipped in baseline, passes in current
  - **Status changes** — any other status flip
  - **Added** — only in current
  - **Removed** — only in baseline

  If `CURRENT` is omitted, it falls back to the active profile's auto-
  discovered output file, so the common pattern is `robotcode results diff
  /path/to/baseline.xml` after the latest run. Use `--only new-failures`
  (repeatable) to narrow the view; combined with `--format json` this gives
  CI pipelines a clean signal for PR feedback without parsing `output.xml`
  themselves.

  Exit code is always 0 — the command is for inspection, not gating.

- Add `--search` / `--search-regex` to `results show` and `log` ([1e90209](https://github.com/robotcodedev/robotcode/commit/1e90209f8b33a401f83e9988b2ea59737f100233))

  `results log` and `results show` now accept `--search TEXT` to narrow the
  output to tests that mention the given text — searched across test name,
  failure message, keyword names, keyword arguments, and log messages.
  Case-insensitive substring match by default; pass `--search-regex` to use
  a Python regular expression instead.

  In `log`'s TEXT output, every match is highlighted with a yellow background
  so the relevant lines stand out at a glance — handy for tracking down
  which test triggered a particular `TimeoutError` without reopening
  `log.html`. JSON output records the search pattern in `filtersApplied` for
  auditability but stays free of markup.

  `--search` composes with the existing filters (`--status`, `-i/-e/-s/-t`),
  so combinations like "failures that mention `AssertionError`" or "smoke
  tests where `Open Browser` was called" come naturally.

- Add `results stats` subcommand ([d1fa30f](https://github.com/robotcodedev/robotcode/commit/d1fa30f6f31b00721309ca18d4f775b466f7aa5f))

  `results stats` aggregates a finished run by `--by tag`, `--by suite`, or
  `--by status` — the same dimensions `report.html` exposes in its
  "Statistics by Tag" / "Statistics by Suite" panels. Repeat `--by` to render
  multiple sections in one call.

  Each section is a table with pass/fail/skip counts and total elapsed time
  per group, sorted by failures (descending) by default. Switch to `--sort
  elapsed`, `--sort total`, or `--sort name`, and limit rows with `--top N`.
  The standard `--status`, `-i/--include`, `-e/--exclude`, `-s/--suite`,
  `-t/--test` filters narrow the test set before aggregation, so combinations
  like "tag stats for the smoke suite, top 10 by failures" come out of the
  box.

  JSON output exposes a stable `StatsResult` / `StatsSection` / `StatsGroup`
  schema for CI consumption.

- Add `--sort` and `--reverse` to `results show` ([e4d693c](https://github.com/robotcodedev/robotcode/commit/e4d693cd2c78d8aa2cd7a807f7773e0cf4e3f1b3))

  `results show` can now sort tests by `name`, `suite`, `status`, `elapsed`,
  or `start` before display. Pair with `--top N` for triage views like "the
  slowest 10 tests" or "failures first". `--reverse` flips the order; without
  `--sort`, execution order is preserved (the existing behaviour).

  `status` orders FAIL → SKIP → PASS → NOT RUN (matching `report.html`'s
  custom sort), and `elapsed` defaults to longest-first so the most expensive
  tests bubble to the top. A dim footer line `Sorted by FIELD (desc)` is
  emitted in TEXT mode when a sort is active; JSON output reflects the order
  in the `tests` array.

- Unify `results log` filters and add `--max-depth` ([02bb47b](https://github.com/robotcodedev/robotcode/commit/02bb47b8707539d1a01432739c3b8fa35c5d600a))

  `results log` now uses the same filter options as `results show` and `results
  summary` — pick tests by `--status`, `-i/--include`, `-e/--exclude`,
  `-s/--suite`, or `-t/--test`. The old `TEST_PATTERN` positional and
  `--failures-only` flag are gone; use `-t "*Login*"` and `--status fail`
  instead.

  A new `--max-depth N` collapses deeply nested keyword calls. The keyword
  header still prints, and a dim `… N hidden (--max-depth N)` marker takes the
  place of the body so nothing disappears silently. Default `0` keeps the
  behaviour unchanged (full tree). The previous `--keywords/--no-keywords`
  toggle is dropped — without keyword grouping the output overlapped with
  `results show`.

  See [docs/03_reference/cli.md](docs/03_reference/cli.md) for the refreshed
  option reference.

- Add `results` command to inspect Robot Framework runs ([cf67abf](https://github.com/robotcodedev/robotcode/commit/cf67abf8e30d953d26fa17578518382703ab8a1b))

  After running tests, `robotcode results` lets you explore the output
  without opening `report.html` or re-running the suite — handy for CI
  logs, agent-driven workflows, and quick failure inspection from the
  terminal.

  Three subcommands:

  - `robotcode results summary` — overall status, pass/fail/skip counts,
    run duration, and the total number of error and warning messages.
    `--failures` adds the list of failed tests above the counts.
  - `robotcode results show` — one line per test with its status, source
    link, and failure message. Filter by status, tags, suite or test
    name pattern.
  - `robotcode results log` — the full execution tree: every keyword
    call, control structure, and log message, just like Robot's
    `report.html` but in your terminal. `--failures-only`, `--level
    WARN`, `--extract DIR` (pulls out screenshots and embedded
    artefacts), and more.

  The output file is auto-discovered from your active `robot.toml`
  profile; override with `-o/--output PATH`. Test names carry a
  `(path:line)` suffix that VS Code's integrated terminal turns into a
  clickable goto-source link. Pass `--format json` (or `toml`) for a
  structured, agent-friendly payload.

  See `docs/03_reference/cli.md` and `robotcode results --help` for the
  full reference.


#### VS Code

- Add commands to register the chat plugins marketplace ([0e2b02f](https://github.com/robotcodedev/robotcode/commit/0e2b02f41c314c0298eb215cadac48a3362380bc))

  Two new Command Palette commands let you pull the RobotCode chat
  plugins marketplace into VS Code without editing settings by hand:

  - "RobotCode: Add Chat Plugins Marketplace"
  - "RobotCode: Remove Chat Plugins Marketplace"

  They add or remove robotcodedev/robotframework-agent-plugins in the
  user-level `chat.plugins.marketplaces` setting, so GitHub Copilot Chat
  can discover and install RobotCode plugins (and future ones from that
  marketplace). This is the marketplace route — separate from the plugin
  the extension already bundles via `contributes.chatPlugins`.

  If you install the robotcode plugin from the marketplace, disable the
  bundled one by turning off `robotcode.ai.enableChatPlugins` to avoid
  running two copies of the same plugin.

  Only the applicable command is shown: Add when the marketplace is not
  registered, Remove when it is. Removing also clears the entry when it
  was added as a GitHub URL rather than the owner/repo shorthand.

- Bundle AI chat plugins ([4018a4f](https://github.com/robotcodedev/robotcode/commit/4018a4fdc6980a68193c34d7ea6cf4d8e88c44a7))

  The extension now bundles chat plugins for GitHub Copilot Chat in VS Code.
  When enabled, the agent uses the project's `robotcode` CLI to answer Robot
  Framework questions and run tasks, honoring the project's `robot.toml`,
  profiles, and Python environment.

  For example:

  - *"run the smoke tests with the ci profile"* runs them through the
    selected profile and reports pass/fail counts
  - *"why did Login Works fail?"* inspects the existing run results instead
    of loading `output.xml` into the chat
  - *"what tests and tags exist?"* uses `robotcode discover`, which resolves
    the real set (paths, profiles, variables, pre-run modifiers) rather than
    grepping `.robot` files
  - *"what arguments does this keyword take?"* looks it up with `libdoc`
    against the installed libraries and local resources
  - *"try this keyword"* runs it in the REPL

  Enabled by default; toggle with `robotcode.ai.enableChatPlugins`.

  For other AI agents (Claude Code, Codex, and other Open-Plugin-compatible
  tools), the same plugins are published as a marketplace:
  https://github.com/robotcodedev/robotframework-agent-plugins

- Disable chat language model tools by default ([3c47b48](https://github.com/robotcodedev/robotcode/commit/3c47b48e53bbd9f5a8d8649205747d88b6ea6d8d))

  RobotCode now includes a `robotcode` CLI-based chat plugin  for chat assistance. They use the same CLI workflows RobotCode users already know for setup, configuration, profiles, discovery, analysis, test runs, result inspection, and REPL usage.

  The existing VS Code Chat language model tools are now turned off by default. They provide chat access to RobotCode information such as keyword documentation, library documentation, document imports, and environment details.

  Users who still need these tools can enable `robotcode.ai.enableLanguageModelTools`.

  The setting remains visible in VS Code for now and notes that the language model tools are planned for deprecation and later removal.

- Add global setting to disable What's New notification ([fa03c08](https://github.com/robotcodedev/robotcode/commit/fa03c0849464857b71c5b730d7ca77e60f5052ea))

  Allow users to turn off the update notification that appears after
  RobotCode has been updated. The new `robotcode.showWhatsNewOnUpdate`
  setting can be found in the global VS Code settings under
  RobotCode > General.


#### Website

- Add interactive hero image carousel with responsive lightbox ([edd6d22](https://github.com/robotcodedev/robotcode/commit/edd6d22253825b6cda458a62da75fde420344593))

#### Discover

- Show a diagnostics summary, full list only on demand ([4b96656](https://github.com/robotcodedev/robotcode/commit/4b966564acb1f1d3147ca6cf2a616e59e71fc334))

  `robotcode discover` no longer prints Robot's parsing errors and warnings
  by default. When a suite has parse issues, a compact `Diagnostics` section
  with the error/warning counts now appears after the statistics, separate
  from the discovery statistics.

  Pass `--diagnostics` to list the full messages; they are printed before
  the discovered results, with file paths shown the same project-relative
  way as the rest of the output. The machine-readable JSON output keeps
  including the full diagnostics regardless, so editors are unaffected.

- `robotcode discover` TEXT output is now markdown ([a7ef8bc](https://github.com/robotcodedev/robotcode/commit/a7ef8bce46e944afddf19c6ba7e405854ba7eb30))

  `robotcode discover` subcommands now emit markdown for human
  output. On a coloured TTY rich renders it to themed ANSI and
  pages if needed; in a pipe (or with --no-color) the raw markdown
  is emitted verbatim. JSON output is unchanged.

  - info renders as a field/value table.
  - files, suites, tests, tasks emit as bullet lists; tags shows
    one bullet per tag with nested tests/tasks when --tests / --tasks
    is on.
  - all keeps the workspace → suites → tests tree as a nested
    markdown list, each level indented two spaces.
  - Statistics blocks are markdown tables.

  The generic markdown helpers used by results — md_table,
  bold_status, path_paren, display_width, the search highlighter
  — move from `results/_render.py` to a shared
  `cli/_markdown.py` so both commands import them from one place.

  Same commit aligns the existing results renderer on the new
  label convention: **bold** is reserved for entities (test/suite
  /tag names, status); _italic_ marks labels (Tags, Total,
  Extracted, Summary, metadata keys); `(path:line)` references
  are wrapped in inline-code spans so they read as code tokens.


#### Results

- `robotcode results` TEXT output is now markdown ([4b94d66](https://github.com/robotcodedev/robotcode/commit/4b94d6659400522f881d21e28805108bcccb8e64))

  `robotcode results` subcommands now emit markdown for human
  output. On a coloured TTY rich renders it to themed ANSI and
  pages if needed; in a pipe (or with --no-color) the raw
  markdown is emitted verbatim — ideal for pasting into PRs,
  Slack, or feeding to an LLM. JSON output is unchanged.

  - summary, show, log, stats and diff open with a markdown
    heading and lay out content as tables, bullet lists,
    blockquotes for failure messages, and inline code for log
    output.
  - Each status shows both an icon and the bold word
    (✅ PASS, ❌ FAIL, ⏭ SKIP, ⏸ NOT RUN, ⚪ NOT SET). summary
    and stats tables are column-padded so the raw markdown stays
    aligned under `cat`/`less`.
  - log renders each test body as a nested list: keywords,
    control flow (FOR, WHILE, IF, TRY, VAR, GROUP), setups and
    teardowns. Argument values appear as inline-code spans;
    failure messages as blockquotes between a keyword and its
    children. Log output renders as `` - `[INFO] text` ``;
    multi-line messages get a fenced code block.
  - Artefacts attached to log messages render as markdown:
    images as `![name](url)` so GitHub, Slack and VS Code show
    them inline; other files as `[path](url)` so OSC 8-aware
    terminals (rich, wezterm, iTerm2) make them clickable. Link
    targets prefer paths relative to cwd and fall back to
    `file://` URLs when the artefact lives outside cwd;
    `--full-paths` forces `file://` URLs everywhere.

- Unify failure vocabulary across results subcommands ([e3a0bd3](https://github.com/robotcodedev/robotcode/commit/e3a0bd34b095b0e162dcc09c50dea84656817b42))

  `summary` uses `--failed/--no-failed` for the failures listing (with
  `failed` as the matching JSON field), lining the wording up with
  `--status fail` everywhere else.

  `show`, `log`, and `stats` gain `--failed`, `--passed`, and
  `--skipped` as additive shortcuts for `--status fail|pass|skip`.
  They stack with each other and with `--status`, so
  `results show --failed --skipped` is `--status fail --status skip`
  without the typing.



### <!-- 1 -->Bug Fixes

#### Analyze

- Run unused diagnostics through the diagnostic modifier ([f13b678](https://github.com/robotcodedev/robotcode/commit/f13b678341b4d886dc46bf099e631e68fba06898))

  `collect_unused_keywords` / `collect_unused_variables` returned their
  diagnostics directly, bypassing the diagnostic modifier. As a result the
  `KeywordNotUsed` / `VariableNotUsed` diagnostics could not be ignored or
  restyled via `-mi`/`-mX` or `# robotcode:` comments, unlike every other
  diagnostic. Pass their result through `modify_diagnostics`, the same way
  `collect_diagnostics` does.

- Tighten path filtering and refine code output ([b0b8820](https://github.com/robotcodedev/robotcode/commit/b0b8820185612c337f1d348a8ee368bff64c8b29))

  - Path arguments to `robotcode analyze code` are now matched segment-wise:
    passing `tests/api` no longer pulls in siblings like `tests/api_v2`.
  - Workspace-level diagnostics (e.g. variable/library import errors) are
    now prefixed with `.:` instead of being printed without any source
    marker; their related-information lines keep their line/column.
  - The summary line picks its color from the highest severity present
    (red/yellow/blue/cyan) instead of only highlighting errors.
  - Unused-keyword/variable collectors are only registered when
    `--collect-unused` is set, and empty document reports from the
    analysis pass are no longer emitted.

- Ignore intentionally unused variables in CLI diagnostics ([9cba5b0](https://github.com/robotcodedev/robotcode/commit/9cba5b091691a61ec415468ffaf98c0a271555e0))

  Treat variable names starting with "_" as intentionally unused in CLI unused-variable diagnostics, matching the language server behavior.


#### Config

- Allow "NONE" string for max-error-lines in robot.toml ([6f2e5e1](https://github.com/robotcodedev/robotcode/commit/6f2e5e154c60de7f6296d6eaad4ad804377be148))

  You can now set max-error-lines = "NONE" to show the full error
  message, matching Robot Framework's --maxerrorlines NONE. Integers
  keep working as before; any other string is rejected with a clear
  error.


#### Language Server

- Honor semantic model setting changes ([782d83d](https://github.com/robotcodedev/robotcode/commit/782d83d480be765259f6b9da898ed71208cbfaee))

#### Plugin

- Suppress mypy type-arg warning on click.ParamType subclass ([ecf88e7](https://github.com/robotcodedev/robotcode/commit/ecf88e7eda14eb2a12afb9b86b956c1ae0d9bdf9))

  A recent mypy / click version bump started flagging
  `AddressPortParamType(click.ParamType)` as 'Missing type arguments
  for generic type ParamType'. Suppress with `# type: ignore[type-arg]`
  inline — the class deliberately omits the type parameter because the
  value shape is heterogenous (parsed by `convert`).

- Make click help-text generation deterministic ([b45757c](https://github.com/robotcodedev/robotcode/commit/b45757c78cd328ba549182de75375576fe7bcd2c))

  The `MutuallyExclusiveOption` help text joined a `Set[str]` and
  `EnumChoice` returned `set(choices).difference(excluded)` — both
  produced non-deterministic ordering, so regenerating `cli.md` always
  re-shuffled the option lists. Sort the mutex set; preserve enum
  definition order via a list comprehension. Regenerate `cli.md` so the
  typo fix from eeb8979a actually lands in the docs and the option
  ordering is stable across future runs.


#### REPL

- Handle all return-value assignment forms in completion and argument hints ([bad6e14](https://github.com/robotcodedev/robotcode/commit/bad6e148b189c762e02f093e332280134a96d1d2))

  Keyword completion and the status-bar argument hint now work after any return-value assignment Robot Framework allows — including item assignment (`${x}[0]`, `${d}[key]`) and type hints (`${x: int}`), not just a plain `${x} =`. The keyword is resolved with Robot Framework's own variable parser, so the REPL matches real assignment syntax exactly. The status-bar hint, which previously showed nothing once an assignment was present, is fixed too.

- Keep keyword completion working after a return-value assignment ([dc5d0be](https://github.com/robotcodedev/robotcode/commit/dc5d0be5a3b661d5b50009dceeb713d8c6c4c3e9))

  Starting a line with a return-value assignment — `${result}=    Some Keyword`, or several targets like `${a}    ${b}=    …` — no longer turns off keyword completion in the keyword cell. Completion and Tab now skip the assignment targets and complete the keyword (and then its arguments) just as they would without an assignment.

- Prevent multiple concurrent REPL executions ([1edfe13](https://github.com/robotcodedev/robotcode/commit/1edfe1363262caabc5ac721c21151fa2477d90b7))
- ${_} now mirrors every keyword result, including None ([45ec8fa](https://github.com/robotcodedev/robotcode/commit/45ec8fa61a7ad81b2c1c51da7e8ede58a2a41a89))

  In the REPL, `${_}` holds the result of the last keyword. Previously
  keywords that return None (such as `Log`) left `${_}` untouched, so the
  most natural first step — `Log  hello` then `Log  ${_}` — failed with
  "Variable '${_}' not found".

  `${_}` now always reflects the most recent keyword and is set to None
  when a keyword returns nothing. It's also seeded to None at startup, so
  `${_}` resolves even before the first keyword runs.

- Resolve relative import paths against the working directory ([8a34747](https://github.com/robotcodedev/robotcode/commit/8a3474737855be3c0d017f6ea166760f66bbf794))

  Imports such as `Import Resource    foo/my.resource` typed at the REPL
  prompt now resolve relative to the REPL's working directory, just like
  the same import does in a `.robot` file. Previously such imports only
  worked when the path was absolute, prefixed with `${CURDIR}/`, or
  reachable via the module search path.

  This matches Robot Framework's own resolution since RF 7.4. The REPL
  docs also note that on RF < 7.4 bare relative paths still fail (RF
  itself doesn't resolve them that way on those versions); use
  `${CURDIR}/...` or put the directory on the module search path
  instead.

- Keep REPL startup working on pyreadline3 (Windows) ([7ba1a01](https://github.com/robotcodedev/robotcode/commit/7ba1a0157d4dce2697fefebe518d218ea5d809cd))

  `robotcode repl` crashed on startup on Windows when launched against
  `pyreadline3` and a history file that still had legacy duplicates —
  pyreadline3 doesn't expose `remove_history_item`, so the dedup pass
  tripped on AttributeError before the prompt ever appeared.

  History dedup and `.history del <N>` now feature-detect
  `remove_history_item` and fall back to a `clear_history` + re-`add_history`
  rebuild when the running readline shim doesn't expose it. CPython's
  GNU readline path is unchanged.

- Preserve backslashes in dot-command argument paths ([ed2b91a](https://github.com/robotcodedev/robotcode/commit/ed2b91acc158190119aa64a532beb3d4660baaa0))

  `.save C:\Users\…\scratch.robot` mangled the path on Windows because
  `shlex.split` consumes backslashes as escape characters. Switch to a
  custom shlex with `escape=""` so paths arrive intact while shell-style
  quoting (for spaces in paths) still works.

- `-d`/`--outputdir` was silently ignored ([06bc85d](https://github.com/robotcodedev/robotcode/commit/06bc85de514f93c296a285b58bcc886f6d845e4c))

  `robotcode repl -d ./results -o output.xml` used to write the file
  into the working directory instead of `./results`. The directory now
  honours `-d`, the `output-dir` setting in `robot.toml`, and `robot`'s
  default precedence in that order. Both `repl` and `repl-server` are
  fixed.


#### Robot

- Fix Run Keyword If nested run keyword handling in all branches ([1d283aa](https://github.com/robotcodedev/robotcode/commit/1d283aaaebed13cfb59436dcdcd68a88da5e0edc))

  All three Run Keyword If branches (IF, ELSE, ELSE IF) now use
  skip_args() + _analyze_keyword_call(analyze_run_keywords=True)
  so nested run keywords receive only branch-local tokens instead
  of consuming ELSE/ELSE IF markers.

- Correct type-hint handling in semantic analyzer ([ecfde21](https://github.com/robotcodedev/robotcode/commit/ecfde21d4e882daae753af4b6fecc5873bca678b))

  strip variable type hints only in declaration contexts
  preserve typed names in usage lookups
  resolve nested typed variable declarations correctly
  stop splitting type hints on additional colons in tokenizer
  add regression tests for variables, VAR, assignments and arguments


#### Runner

- Keep `relSource` in `results` JSON regardless of `--full-paths` ([e4ff456](https://github.com/robotcodedev/robotcode/commit/e4ff4569857b294af2b921002c42007350635af3))

  Aligns `results` with `discover`, which always carries both `source`
  (absolute) and `relSource` in its JSON output. Two changes:

  - `_make_test_item` / `_make_diff_change` / `LogTest` stop conditionally
    setting `rel_source=None` when `--full-paths` is on. The flag is now
    purely a TEXT-rendering hint.
  - `_rel_to_cwd` falls back to the original path (instead of `None`)
    when the source isn't anchored under cwd, mirroring
    `discover.get_rel_source`. Consumers like the VS Code extension can
    now rely on `relSource` being present whenever `source` is.

  `_make_diff_change` and `_make_test_item` no longer take `full_paths`,
  since the parameter became unused after the change. Call sites updated.

  Plus acceptance tests covering the harmonised behaviour on `summary`,
  `show`, `log` and `diff`, and a TEXT-only `--full-paths` test on
  `discover tags` (the last subcommand without coverage).

- Chdir into root_folder in `discover files` ([b92acdc](https://github.com/robotcodedev/robotcode/commit/b92acdc55a0cad637d5b9577ce1179b339edd5a6))

  The other `discover` subcommands wrap their work in
  `with app.chdir(root_folder)` via `handle_options`, so `get_rel_source`
  produces paths relative to the project root. `discover files` skipped
  that step, which made its default (non-`--full-paths`) output depend on
  the caller's process cwd: if cwd was outside the project, paths fell
  back to absolute, breaking the documented semantics.

  Wrap the body in the same chdir context so the output is consistent
  with the rest of `discover`. Also flips a fragile `test_files_default_
  relative` from ordering-dependent (it would fail in the full suite
  when an earlier test left cwd in a tmp dir) to robust.

- Honour subcommand semantics in `discover` JSON output ([0f26a3f](https://github.com/robotcodedev/robotcode/commit/0f26a3fa6bec4ed582deca329cfdf504a4fc1b47))

  Two `discover` subcommands silently differed between their TEXT and
  JSON renderers because the type filter only ran in the TEXT path:

  - `discover tests -f json` returned every item in
    `collector.test_and_tasks` — i.e. tasks slipped in too, even though
    the TEXT render correctly filtered to `type == "test"`. Same shape
    bug on `discover tasks`. Filter the list before handing it to
    `ResultItem` so JSON and TEXT agree.
  - `discover tags --not-normalized -f json` ignored the flag and always
    returned the normalised tag dict; only the TEXT path consulted
    `--normalized`. Pick the right collector dict (`tags` vs
    `normalized_tags`) for both renderers.

  Both surfaced while wiring up the new discover acceptance tests.

- Page `discover` output through a single pager invocation ([069c34e](https://github.com/robotcodedev/robotcode/commit/069c34e2dcbe4588438e8c0820df36f392cee3c3))

  Each `discover` subcommand opened the system pager multiple times in
  sequence — once for the main listing, then once for the statistics block
  (and once per key for `discover info`). The fix routes everything through
  a single `echo_via_pager` call so the user only sees one pager instance.

- Normalise tags in `results` commands ([8f93500](https://github.com/robotcodedev/robotcode/commit/8f93500cc77a77b23170c86d0a01d79e18c87569))

  Robot Framework treats tags as equal when they differ only in case,
  whitespace, or underscores (`Bug 1` ≡ `bug_1` ≡ `Bug1`). The new
  `results` commands didn't honour that:

  * `stats --by tag` showed each spelling variant as its own bucket,
    even though they referred to the same semantic tag.
  * `tests[].tags` in `show` / `summary --failures` echoed the raw form
    from the result file, so the same tag could appear with different
    spellings on different tests.
  * `--search` / `--search-regex` against tags compared the raw strings,
    so `--search "bug 1"` missed tests literally tagged `bug_1`.
  * `filtersApplied.include/exclude` echoed the user input verbatim, which
    didn't reflect how Robot actually interpreted the pattern.

  Every tag-handling spot now uses Robot's `normalize(..., ignore="_")`:

  * Stats buckets group by the normalised form and display the normalised
    label too.
  * `_make_test_item` emits already-normalised tags in JSON / TEXT.
  * `_SearchMatcher` carries a separate tag-aware predicate that
    normalises both haystack and needle (substring) or just the haystack
    (regex).
  * `_canonical_tag_pattern` normalises plain single-tag patterns in
    `filtersApplied`; patterns containing an uppercase `AND` / `OR` /
    `NOT` operator are echoed verbatim because each operand would need
    individual normalisation.

  Tests added: stats merges equivalent tags into one bucket; `show`
  emits normalised `tags`; `--search` is normalisation-aware against
  tags; `filtersApplied` echoes the canonical pattern form. The
  `tagged.robot` fixture grew three new tests (`norm tag`, `norm_tag`,
  `NormTag`) so the regression case is exercised end-to-end.

- Make `results` commands work against older Robot Framework outputs ([20bb597](https://github.com/robotcodedev/robotcode/commit/20bb597b4128935d2661dacf76bf00522b7593a9))

  `robotcode results` failed on `output.xml` files generated by Robot
  Framework 5 and 6 — the older models use different attribute names than
  RF 7 (`elapsedtime` vs `elapsed_time`, `starttime`/`endtime` as the
  `YYYYMMDD HH:MM:SS.fff` string, no `variables` on `WhileIteration`, …).

  Each accessor now falls back to the legacy spelling and the iteration
  helper limits loop-variable lookups to `ForIteration` via `isinstance`,
  so `summary`, `show`, `log`, `stats`, and `diff` produce identical
  output regardless of which Robot version wrote the file. Timestamps in
  the legacy string format are normalised to ISO 8601 in the JSON
  contract.

  Smoke-tested across RF 5.0, 6.0, 7.0, 7.3, and 7.4.

- Escape `<errors>` in `results log` help to prevent VitePress build error ([7dc79ef](https://github.com/robotcodedev/robotcode/commit/7dc79ef72081e25e00085d6be0f87cdcdd00e70e))

  The `--execution-messages` help text contained a raw `<errors>` tag that
  VitePress' Vue parser interpreted as an unclosed HTML element, breaking
  the generated `cli.md` docs page. Wrap it in backticks so it renders as
  inline code and is ignored by the template compiler.


#### VS Code

- Let Tab accept Copilot inline edit suggestions ([f724aa2](https://github.com/robotcodedev/robotcode/commit/f724aa25eef27b65294ee010f86c1d46afa245df))

  When "4 Spaces Tab" was enabled, pressing Tab inserted four spaces
  instead of accepting or jumping to Copilot's inline edit (Next Edit)
  suggestions. Tab now yields to those suggestions and only inserts
  spaces when none is pending.

- Update stale RF version UI strings from 4.1 to 5.0 (#605) ([f846483](https://github.com/robotcodedev/robotcode/commit/f846483f9c759ab037af50430561275148623d39))

  The quick-pick dialog shown when environment validation fails still
  referenced 'robotframework version 4.1 or higher' in both the
  'Select Python Interpreter' detail and the 'Retry' detail text.
  The actual enforced minimum has been 5.0 since commit 02cf495f
  (refactor: introduce RF_VERSION constant and remove RF < 5.0 dead code).


#### Website

- Fix sidebar links treated as external URLs ([9b393ec](https://github.com/robotcodedev/robotcode/commit/9b393ec8141f25bb7e680c067f2c3563818e2979))

  vitepress-sidebar generates base:"/" with links starting with "/",
  causing VitePress to produce protocol-relative URLs ("//path") that
  browsers interpret as external links. Remove the redundant base:"/"
  from the root sidebar group so absolute links resolve correctly.


#### Analysis

- Respect diagnosticMode for workspace files ([d2f8114](https://github.com/robotcodedev/robotcode/commit/d2f81147335d56b3aa851f0aefd37c3b118bfbce))

  Diagnostics for closed workspace files could appear (or be suppressed)
  inconsistently in openFilesOnly mode, depending on which file the
  workspace diagnostics loop happened to iterate last.

  Also clarify the diagnosticMode description so it no longer implies
  that background analysis is restricted -- the setting only controls
  which files diagnostics are reported for.


#### Bundled

- Quote arguments in robotcode script to handle spaces correctly ([4311747](https://github.com/robotcodedev/robotcode/commit/43117478ed5a7110703fab4b6d2a1df19d0b2b6b))

#### Discover

- Render arbitrarily deep suite trees in markdown output ([3825939](https://github.com/robotcodedev/robotcode/commit/38259393db317a7621344edffd1a9a0af75fafab))

  `robotcode discover all` (and any other markdown output) now renders
  the full workspace tree no matter how deeply suites are nested.
  Previously, projects nested past ~8 levels had everything below the
  limit silently dropped — including the trailing `## Statistics`
  block — because rich's markdown parser caps nesting at 20 and every
  list level consumes two of that budget.

  Markdown is now rendered through a parser configured for deep
  nesting, so the whole tree and its statistics always appear. Headings
  are left-aligned and tables render without the extra blank lines rich
  inserts by default.

  rich is now a direct dependency of the plugin package (the lowest
  package that renders markdown); the repl package picks it up
  transitively instead of declaring it separately.


#### Packages

- Pin internal robotcode dependencies to exact version ([7e4e9f2](https://github.com/robotcodedev/robotcode/commit/7e4e9f212e62978397caf0bf32564d028974df00))

  Updating a single robotcode package now pulls the matching versions of
  its robotcode dependencies along with it. Previously the inter-package
  dependencies were unconstrained, so upgrading one package could leave
  its siblings on an older release and break the installation.

  The pins are kept in sync automatically on each release.


#### Repl, repl-server

- `-v` / `--variable` and `-V` / `--variablefile` now work ([7ecdd82](https://github.com/robotcodedev/robotcode/commit/7ecdd82d2f932d8bf1508bf0fe8aff3a28682e76))

  Both flags on `robotcode repl` and `robotcode repl-server` were broken
  — `-v BASE_URL:staging` did not register the variable, and `-V vars.yaml`
  did not load the file. They now behave the same as the matching `robot`
  flags: `-v` sets inline name/value pairs, `-V` reads variables from
  `.yaml` / `.py` / `.json` files. Repeat either flag to set multiple at
  once.


#### Schema

- Revert robot.toml json-schema, because older versions of robotcode need this ([fafb168](https://github.com/robotcodedev/robotcode/commit/fafb16813bb9f8e124aa6aeb7b5f5c17cd934596))


### <!-- 2 -->Documentation

- Split REPL reference into shell and command-line debugger pages ([7f0577f](https://github.com/robotcodedev/robotcode/commit/7f0577f23b6a14a96df1712f247044be05f5c37d))

  The REPL reference mixed the interactive shell with the command-line
  debugger. It is now two pages:

  - "Interactive Robot Framework with robotcode repl" — the shell.
  - "Command-line debugging with robotcode robot-debug" — a dedicated page
    for the debugger: ways to pause a run (line, keyword, embedded
    Breakpoint keyword, exceptions, stop-on-entry), the debug command set
    (stepping, call stack, inspecting and setting variables, breakpoint
    management, exception filters, log-and-continue), a worked example with
    the embedded Breakpoint keyword, and how it relates to the VS Code
    debugger.

  Other improvements:

  - Each command reference page now states which optional package to
    install to run it: robotcode[repl], [runner], or [analyze].
  - The CLI reference now documents robotcode robot-debug (alias run-debug)
    and lists it under the repl package.
  - Fixed the .doc command description: it shows documentation for
    libraries and resources the session has imported, not on demand.

- Add "Working with AI Agents" reference page ([e7c8d68](https://github.com/robotcodedev/robotcode/commit/e7c8d682b1f8aef66df68726eaa1e4cd807bac58))

  Describe how RobotCode lets AI coding agents work through the project's
  own robotcode CLI instead of guessing:

  - the chat plugin (a skill) and what it teaches the agent — discover,
    libdoc, REPL, results, analyze on the resolved project
  - the bundled VS Code plugin and its enableChatPlugins toggle, plus the
    extension shipping the robotcode CLI on the integrated terminal PATH
  - installing the plugin in other agents via the Open Plugins marketplace
  - recommended project-context setup (AGENTS.md / CLAUDE.md): environment,
    library init steps, the system under test, conventions
  - the CLI's AI-agent detection and its override env vars/flags
  - troubleshooting

- Refine contribution guide and AI policy ([b93cbf6](https://github.com/robotcodedev/robotcode/commit/b93cbf6227539eda15bd433663a76db276521409))

  - AI_POLICY: welcoming, principle-led intro; clarify that what
    matters is human ownership, not whether an autonomous agent was
    involved; frame the purpose around protecting maintainer time,
    which is what ultimately keeps RobotCode sustainable
  - CONTRIBUTING: add a "find your path" orientation block and a
    warmer Project-Wide Rules intro; lead commit-signing setup with
    the low-effort SSH path; document that documentation-only changes
    need neither the test matrix nor linting (there is no Markdown
    linter); remove decorative emoji
  - PULL_REQUEST_TEMPLATE: mark the tests and linting checks N/A for
    documentation-only / non-code changes

- Add `results` analysis guide ([ebb2d12](https://github.com/robotcodedev/robotcode/commit/ebb2d1285316b544bc4647ee059f5c44f7020d57))

  A task-oriented user guide for the `robotcode results` family of
  commands, split into two parts:

  * **Using the commands** — what each subcommand does in the terminal,
    its useful flags, sort/filter semantics, and the pager / colour
    handling. Recipes for the common day-to-day questions: "what
    failed", "which test took longest", "drill into one test",
    "regression vs main".
  * **JSON reference** — schema rules (omitted vs `null` vs `[]`),
    per-subcommand JSON shape, the body-item-type vocabulary used by
    `log`, the `filtersApplied` echo, and CI/jq recipes for pass-fail
    gates, slow-test reports, notification payloads and artefact
    gathering. Includes a note specifically for AI-driven workflows on
    why streaming the focused JSON beats parsing raw `output.xml`.

  Also linked from the reference index page.

- Update json schema for robot.toml validations ([6d4fd6d](https://github.com/robotcodedev/robotcode/commit/6d4fd6d88a29af46e6057565019cdf77912428d4))
#### Analyze

- Document the `-mi "*"` allow-list pattern ([b5b2444](https://github.com/robotcodedev/robotcode/commit/b5b2444aad5b584a03586542b3ab898035aabe3c))

  Show that `*` matches every code, so `-mi "*"` plus re-introducing
  specific codes builds an allow-list — and point out it remaps severity,
  unlike the --code filter.

- Document the --code filter ([e72ac55](https://github.com/robotcodedev/robotcode/commit/e72ac55a20cc24a19f8cdcdffbb825e64f5f32ec))

  Fold --code into the "reporting only some diagnostics" section next to
  --severity, noting that both filter (rather than remap) and combine with
  AND.

- Document --severity filter and unused diagnostic control ([2da8116](https://github.com/robotcodedev/robotcode/commit/2da81165f24a7b180f3dbf270b9072edb6f3acce))

  - describe the new --severity output filter alongside the modifiers
  - note that KeywordNotUsed/VariableNotUsed can now be remapped or
    ignored like any other diagnostic

- Streamline and correct analyze-code guide ([0272ab9](https://github.com/robotcodedev/robotcode/commit/0272ab9dcd6899dc59b38cc6e06b2cb1de43222b))

  - drop the flag table; defer to the CLI reference
  - move the JSON reference to the end
  - trim implementation internals from the SARIF section and give every
    output format a consistent invocation + example
  - note that the CI examples assume project setup via its package manager
  - fix a dead anchor link

  Corrections after review:
  - no paths analyzes/reports the whole project, not the profile's default
    paths; paths/--filter narrow the reported per-file diagnostics while
    import/library resolution always covers the whole project
  - explain why --collect-unused is opt-in (needs whole-project reference
    data, extra pass, slower with many keywords/variables)
  - note that a real run or discovery can surface errors static analysis
    misses (suite-wide checks like duplicate test names, PreRunModifier)
  - show how to read the bitwise exit code from the shell

- Document CI workflows, drop scratch workflow ([fcb0caa](https://github.com/robotcodedev/robotcode/commit/fcb0caa84d4bd9203d483f0cd5d1a62482375fb3))

  Replace the fragmentary CI snippets in the analyze-code guide with full,
  copy-pasteable workflows for GitHub code scanning (SARIF upload), GitHub
  inline annotations, and GitLab Code Quality — including the
  `security-events: write` permission and current action versions
  (checkout@v5, upload-sarif@v4) that the manual trial surfaced.

  Remove the throwaway .github/workflows/analyze-code.yml now that the
  examples live in the documentation.

- Add reference guide for analyze code ([095b52a](https://github.com/robotcodedev/robotcode/commit/095b52a4092e74277d623c8065ef9c3cc9337646))

  Add a task-oriented guide for `robotcode analyze code` under
  docs/03_reference, in the style of the discover/results guides: what it
  checks, severities and diagnostic modifiers, exit codes and masks, all
  output formats (concise, json, sarif, github, gitlab), a flag reference,
  JSON/SARIF/GitHub/GitLab output references, CI recipes, and the cache
  subcommands. Link it from the reference index.


#### CLI

- Enhance command options documentation for severity and code filters ([422d466](https://github.com/robotcodedev/robotcode/commit/422d466d4c73b70075519bc5af0d6cf0d990e31a))
- Document core, results and testdoc commands ([b48a58d](https://github.com/robotcodedev/robotcode/commit/b48a58d8aea23d0332337db5390306a5063f04e5))

  Add the missing commands to the package overview: the core
  `robotcode` package now lists `config` and `profiles`, and the runner
  package lists `results` and `testdoc`. Close the reference with help
  hints and links to the related configuration, discovery, results and
  REPL pages.


#### Config

- Show TOML examples in robot.toml reference ([c53da77](https://github.com/robotcodedev/robotcode/commit/c53da77a648056bde46b1a0db9da1dc13eda816d))

  The "Examples:" blocks were carried over verbatim from Robot
  Framework's CLI help, so they showed --flags instead of TOML.
  Add a curated TOML_EXAMPLES map in generate_rf_options.py (with
  extend- prefix rewriting for extend-* variants) and regenerate
  model.py and config.md.


#### REPL

- Clarify REPL scripts are body-only .robotrepl files, not full suites ([a169d86](https://github.com/robotcodedev/robotcode/commit/a169d8671be63c1ee15270734e1371568900dacc))

  Reword the file-execution section so it no longer implies a full `.robot`
  suite can be run. These inputs are REPL scripts — a test-case body only,
  with no `*** Settings ***` / `*** Test Cases ***` sections — and use the
  `.robotrepl` / `.robotscript` extension instead of `.robot`. A file with
  section headers fails with "No keyword with name '*** Settings ***'
  found"; import libraries and resources from inside the body with
  `Import Library` / `Import Resource`.

  Also note that `.save` only guarantees the export parses cleanly —
  REPL-only variables like ${_} still need an edit to run standalone — and
  tidy up wording, hyphenation, and a duplicated shortcuts list.

- Document the prompt-toolkit extra ([2660b7b](https://github.com/robotcodedev/robotcode/commit/2660b7be5a560f20f6ad4a43a93f795eca58ffa5))

  New section in the REPL reference covers:

  - the `prompt-toolkit` extra (`pip install 'robotcode-repl[prompt-toolkit]'`)
    and the upgrades it lights up — live as-you-type candidate popup,
    fish-style auto-suggest, Ctrl-R reverse search UI, bracket
    auto-match, multi-line cursor movement
  - the threaded completer + session cache that keep the popup
    responsive even with hundreds of importable modules on `sys.path`
  - the fact that history is shared on disk between backends, so
    swapping extras doesn't lose arrow-up recall
  - the `[prompt-toolkit,gnureadline]` combined extras as a sensible
    setup for libedit-backed Pythons

- Document history persistence and tab completion ([1374da7](https://github.com/robotcodedev/robotcode/commit/1374da74e44d606a9a6d8923feb3265560436709))

  New "Prompt features" section in the REPL reference covers:

  - where the history file lives (project `.robotcode_cache/` vs. the
    per-user cache directory, `ROBOTCODE_CACHE_DIR` override), how the
    fish-style dedup behaves, and the `--no-history` /
    `ROBOTCODE_REPL_NO_HISTORY` / `ROBOTCODE_REPL_HISTORY_SIZE`
    escape hatches
  - what Tab completes — keywords from loaded libraries and imported
    resources, suite-scope variables (`${...}` / `@{...}` / `&{...}`),
    `%{...}` environment variables, and the three `Import` arguments
    with plain / dotted / filesystem prefixes
  - the `gnureadline` extra for macOS' system Python and
    `python-build-standalone` interpreters (`uv` / `rye` / …) where the
    stdlib `readline` is libedit-backed and Tab would otherwise be
    degraded

  Also adds the REPL reference to the index page.


#### Runner

- Task-oriented guide for `robotcode discover` ([f69fd9a](https://github.com/robotcodedev/robotcode/commit/f69fd9ab0a792e5549f0f61e7f20b8ab2ad1e538))

  A new `discovering-tests.md` page covers the `discover` family the same
  way `analyzing-results.md` covers `results`. It walks every subcommand
  from the terminal perspective — `all`, `tests`, `tasks`, `suites`,
  `tags`, `files`, `info` — with examples and flag tables, then the
  shared Robot-native filters and `--search` / `--search-regex`
  behaviour, and finally the full JSON schema reference for scripts,
  CI pipelines, and editor integrations (`TestItem`, `ResultItem`,
  `TagsResult`, `Info`, `diagnostics`, `filtersApplied`) plus a set of
  jq-based CI recipes for sharding, tag reports, and parse-error gates.

- Cover extended search and `results log --keyword-info` / `--suite-info` ([a7395f6](https://github.com/robotcodedev/robotcode/commit/a7395f617609ae5437b10a0217c9748354fe8a91))

  - `analyzing-results.md`: search-target list mentions test
    doc/template/timeout, keyword [Documentation]/[Tags]/[Timeout]
    (result-tree-only), and ancestor-suite Documentation/Metadata. New
    `--keyword-info and --suite-info` subsection explains what each flag
    adds to TEXT and JSON, with a combined example. `log` JSON schema
    shows the new `suites` array and per-test `suite` cross-reference plus
    a table for the keyword doc/tags/timeout fields.

  - `cli.md`: regenerated from `hatch run create-cmd-line-docs` to pick
    up the new `--keyword-info` / `--suite-info` flags on `results log`
    and the updated `--search` help text across `results` and `discover`.

- Fix "releative" typo in `discover --help` ([eeb8979](https://github.com/robotcodedev/robotcode/commit/eeb8979a0a89e44c6b33d62703e55b83964db29f))

#### Website

- Use bundler module resolution ([dd6f358](https://github.com/robotcodedev/robotcode/commit/dd6f3581c568866b9636b1901991ae5e3800485a))
- Improve hero image navigation ([09a8975](https://github.com/robotcodedev/robotcode/commit/09a89753283c437880e9d96f90253520830a1efd))

#### Contributing

- Add agent workflow guide and update contribution guide ([9a024a2](https://github.com/robotcodedev/robotcode/commit/9a024a2b98de2f8065ce74d62df755731d330ec1))
- Clarify DCO vs GPG signing and unify branding ([a1f116d](https://github.com/robotcodedev/robotcode/commit/a1f116d5ea3f656eca1710f94bd6ec2df19150e9))

  Reference the DCO in the CONTRIBUTING Legal Notice and recommend
  `git commit -s`. Clarify in both places that the DCO sign-off is
  separate from the GPG/SSH commit signature (`git commit -S`) required
  for merges.

  In AI_POLICY.md, drop the duplicated DCO statement and link to the
  Legal Notice instead. Align the PR template's tests/lint/signed-commits
  bullets with the CONTRIBUTING checklist, and unify the project name
  spelling to "RobotCode" across the three files (URLs and CLI names
  unchanged).

- Add AI policy and refine contribution guide ([688e6ae](https://github.com/robotcodedev/robotcode/commit/688e6ae0cc09062b5cc8f389e86f4ed8a9743da7))

  Add a project-wide AI and Automated Contribution Policy (AI_POLICY.md)
  covering human responsibility, disclosure, low-context submissions, and
  enforcement.

  Restructure CONTRIBUTING.md:
  - new "Project-Wide Rules" section linking the AI policy and the
    payment/bounty rule
  - add a pre-commit hooks section (uvx / uv tool install / pipx)
  - mention uv / uvx alongside pipx for installing hatch
  - rewrite the Running Tests section: \`hatch run test:test\` as the
    recommended default, correct RF versions (5.0–7.4) and matrix size
    (5×8=40), clarify that bare \`hatch run test\` only runs in the
    default env
  - consolidate PR guidelines into a PR checklist + description +
    review process, referencing the new PR template
  - fix TOC duplicates and the empty Payment link

  Add a GitHub pull request template with checklist and AI/tooling
  disclosure block, and add the same disclosure block to the bug,
  enhancement, and question issue templates.


#### Home

- Refresh landing page ([8dc70e0](https://github.com/robotcodedev/robotcode/commit/8dc70e08b0c221d4f1275bf7d57153b09ed099a8))

  Mirrors the reworked README pitch: tightened hero, consolidated feature
  cards, and a "Sponsor RobotCode" section with Individual/Corporate split.

  Adds a RandomTagline component, analogous to RandomHeroImage, so the
  hero tagline rotates randomly on each page load.


#### News

- Add v2.6.0 release notes ([7d6a701](https://github.com/robotcodedev/robotcode/commit/7d6a701df553d8a99e388bc19cf916c6fdca2540))

#### Readme

- Restructure and refresh ([69c881b](https://github.com/robotcodedev/robotcode/commit/69c881bf3316752ebfd370c7ec0f7ac18f42583d))

  - Sharpen What-is intro with Foundation / Core-Team partnership note
  - Restructure Key Features into Editor/IDE, Configuration, Command line
    groups with marketing-oriented bullets
  - Tighten Requirements (correct VS Code 1.108 / IntelliJ 2025.3,
    prominent LSP-editor note)
  - Add Command Line installation block for CI / non-IDE users
  - Fix broken doc links (troubleshooting page never existed,
    /support/ → /05_contributing/)
  - Split Sponsor RobotCode and Get Involved into separate sections


#### Repl, repl-server

- Correct misleading `--source` help text ([87402e3](https://github.com/robotcodedev/robotcode/commit/87402e333c9091fc1458280c805f6ee1cfa10169))

  The flag only uses the parent directory of `FILE` as the REPL's
  working directory — it does not read or write the file, and does not
  set a suite name.



### <!-- 3 -->Performance

#### VS Code

- Smoother test explorer refreshes and live test updates ([bc488d0](https://github.com/robotcodedev/robotcode/commit/bc488d0d81f795618cd6b08e32f4e156b66a4219))

  The Test Explorer used to flicker on every keystroke when the tree was
  expanded, slow to a crawl during multi-file edits (e.g. when an AI agent
  applies many edits at once), and sometimes show "AbortError" as a
  workspace entry at startup. Newly added or removed tests didn't appear
  in the tree until the refresh button was pressed.

  What's different now:

  - The tree only re-renders when the discovered tests actually change;
    identical re-discoveries leave the UI untouched.
  - One refresh runs at a time — newer edits cancel the in-flight
    subprocess instead of queuing up behind it.
  - Many edits in a short window collapse into a single workspace refresh.
  - External file changes no longer collapse expanded tree nodes.
  - Tests added or removed in a saved file appear/disappear immediately.
  - A workspace refresh no longer runs a redundant per-document discover
    for every open file.

  Also fixes a non-deterministic tag order from the discover command so
  the TS side can reliably detect real tag changes.



### <!-- 4 -->Refactor

- Drop three orphaned private symbols ([38a7995](https://github.com/robotcodedev/robotcode/commit/38a799518d8830c38e03d0fd0a61b6fe2fca204b))

  Dead code surfaced by an unused-symbol sweep across `packages/`:

  - `_BRANCHES` (repl/_indent.py): a frozenset that was only there
    to document which Robot keywords (`ELSE`, `ELSE IF`, `EXCEPT`,
    `FINALLY`) the indent counter ignores. Replaced with a short
    inline comment — same self-documenting effect, no orphan symbol.
  - `_split_comma` (analyze/code/cli.py): a click callback added
    alongside the `--xm` / `--xe` exit-code-mask options, then
    superseded by `_parse_exit_code_mask` and never wired up.
  - `_cancel_all_running_tasks` (core/concurrent.py): originally
    the public `cancel_running_callables`; the FutureEx → Task
    rename privatised it but no caller followed.

#### Language Server

- Pure SemanticModel for signature help and code action ([2a4e728](https://github.com/robotcodedev/robotcode/commit/2a4e7288c48ca60cbb3f878928652163d81fe02a))

  Both LSP feature paths now read everything off the SemanticModel — no
  RF AST walks, no ModelHelper position helpers. SemanticToken carries a
  precomputed LSP Range so consumers can use native operators
  (`pos in tok.range`, `range in tok.range`, `tok.range.extend(...)`)
  instead of per-coordinate arithmetic. Output unchanged.


#### REPL

- Unify the setting-alias flag and tidy completion internals ([c3d50fe](https://github.com/robotcodedev/robotcode/commit/c3d50fef9645ef538a8117b7b9d381d0ac83bc6f))

  Review follow-up, no behaviour change:

  - Use one name, `setting_import_aliases`, for the flag everywhere (it was
    `include_setting_aliases` on `candidates_for_rich`).
  - Make `_RobotCompleter`'s flag public so the `_smart_tab` key binding reads it
    off the active completer without reaching into a private attribute.
  - Move the assignment-target helpers above their first caller so there is no
    forward reference.
  - Add completer-level tests: the `>>>` completer forwards the flag into the
    candidate service, and Tab after a setting alias opens completion instead of
    inserting a cell separator.


#### Runner

- Extract `discover` data models and align `info` JSON casing ([95c119b](https://github.com/robotcodedev/robotcode/commit/95c119ba09f2d61c66597cbdc51c64059e5a8aac))

  The `TestItem` / `ResultItem` / `Statistics` / `TagsResult` / `Info`
  classes move out of `discover.py` into a dedicated `_models.py`,
  matching the layout the `results` family already uses. `discover.py`
  imports them from there, keeping the command file focused on click
  wiring and traversal.

  `Info` was the only `discover` model without `CamelSnakeMixin`, so
  `discover info` was emitting `robot_version_string` / `python_version_string`
  / `system_version` / `robot_env` while every other `discover` and
  `results` JSON key was already camelCase. It now uses the mixin too,
  so `-f json discover info` (and the TEXT key:value rendering) speaks
  the same `robotVersionString` / `pythonVersionString` / `systemVersion`
  / `robotEnv` shape as the rest. Tests and the reference docs follow.

- Adopt SuiteVisitor for body traversal in `_search` ([000f2e9](https://github.com/robotcodedev/robotcode/commit/000f2e90ce46ced2d33de880c2f4b9cbf4f9b62b))

  Replace `_body_matches`' manual recursion + string-based `item.type`
  dispatch with a `SuiteVisitor` subclass that overrides one `start_X` per
  body-item type. Robot's own visitor handles the recursion; returning
  `False` from each hook short-circuits the rest of the traversal once a
  match is found.

  This drops every `getattr` in the file: the fully-qualified keyword name
  comes from the inherited `Keyword.name` property (which already composes
  `libname.kwname` on RF <7 result trees), result-tree-only `.message` is
  guarded with `isinstance(item, StatusMixin)`, `template` (running-model
  only) is guarded with `isinstance(test, RunningTestCase)`, and the
  `For.assign` vs `For.variables` rename is handled by one top-level
  `RF_VERSION` gate. RF 7+ `Var`/`Group`/`Error` types come in via a
  `TYPE_CHECKING` import with `# type: ignore[attr-defined,unused-ignore]`.

  As a side-effect `Error.values` is now part of the searched fields —
  the old type-string dispatch silently skipped Error items.

- Adopt ResultVisitor for body traversal in `results` ([5e5c88f](https://github.com/robotcodedev/robotcode/commit/5e5c88f97e2b16be8b254b40be5dac89082623e8))

  Replace manual body recursion (`_collect_test_body`'s build-pattern and
  `_count_all_messages`' inline `walk`) with `ResultVisitor` subclasses that
  override the per-type `end_X` methods Robot's dispatch already provides.
  This removes the string-based `item.type` checks, eliminates the
  remaining `getattr` calls on stable Robot attributes, and lets every body
  item flow through one well-typed code path.

  Side cleanups in the same pass: hoist RF-version-conditional access
  (`kwname`/`libname` vs `name`/`owner`, `For.assign` vs `For.variables`,
  `Result.elapsed_time` vs `elapsedtime`, `StatusMixin` time fields) into
  top-level helpers gated on `RF_VERSION`, switch the `Var`/`Group`/`Error`
  imports to a `TYPE_CHECKING`-only `# type: ignore[attr-defined,unused-ignore]`
  form, and drop `_eval_str` — the profile is already evaluated before it
  reaches this code, and `StringExpression.__str__` covers the rest.

- Drop more `Any` from `results.py` (15 → 6) ([8b4f059](https://github.com/robotcodedev/robotcode/commit/8b4f05907daadf6fb0f1081c1593acea031e3f7b))

  Three more rounds of tightening on top of the previous pass:

  - `_eval_str` / `_iso` accept `object` (we use generic `isinstance` /
    `getattr` / `str()` on them, no type-specific access).
  - `_make_message_entry` takes `Message` — it's only called for
    MESSAGE-typed body items, so the static type is precise.
  - `_start_time` / `_end_time` now return `Optional[object]` (forwarded
    unchanged to `_iso`, which accepts `object`).
  - The four RF-version-gated helpers (`_iter_all_tests`,
    `_get_full_name`, `_keyword_name_and_owner`, `_loop_variables`) get
    proper `TestSuite` / `TestCase` parameters where the polymorphism
    isn't on the input type. Internally they use `getattr` for the
    attributes whose existence depends on the runtime RF version, so
    mypy stays happy across the whole RF matrix without `# type:
    ignore`. Same behaviour, just less guesswork at call sites.

  `Any` remains on the six positions where it's the only honest answer:
  the heterogeneous body-item helpers (`_keyword_name_and_owner`,
  `_loop_variables`, `_elapsed_seconds`, `_start_time`, `_end_time`,
  inner `build`). Each item type carries different attributes; we
  dispatch by `type` string and `getattr`. Typing them as a Union of 9+
  result-tree classes would be heavier than the type safety it provides.

- Replace `Any` with proper Robot types in `results.py` ([e70314f](https://github.com/robotcodedev/robotcode/commit/e70314f80d3de55da97653e325a66b9c24e536ad))

  Twenty-one stable-API positions get real type hints. `Any` survives only
  where it's genuinely the right answer:

  - The four RF-version-gated helpers (`_iter_all_tests`,
    `_get_full_name`, `_keyword_name_and_owner`, `_loop_variables`) —
    each branch accesses attributes that exist only on the matching RF
    version, and mypy sees only the installed one.
  - Body-item helpers and the inner `build(item)` in `_collect_test_body`
    — body items are a `Keyword | For | If | Try | While | Var | Return
    | Group | Message` union and we dispatch by `getattr(item, "type")`.
  - `_elapsed_seconds` / `_start_time` / `_end_time` — called on suites,
    tests *and* keywords; truly polymorphic.
  - `_iso`, `_eval_str`, `msg` — string-or-something accepting helpers.

  For everything else, the actual Robot class lands in the signature:
  `TestSuite` and `TestCase` from `robot.result`, `Result` for the loaded
  execution result, `ExecutionErrors` for the errors collection,
  `RobotBaseProfile` for the resolved profile, and `SuiteVisitor` for the
  modifier list. No behaviour change; mypy is happy on every RF version
  in the matrix.

- Collapse `results` filter pipeline into a single pass ([93c3cf6](https://github.com/robotcodedev/robotcode/commit/93c3cf623f0faa42ae2e9e5a2a13056eb79d1f3e))

  Every `results` subcommand used to filter twice: first delegating
  include/exclude/suite/test to `TestSuite.filter()` via
  `_apply_tree_filters`, then re-walking the (still-full) tree inline to
  apply `--status` and `--search`. The matcher and the status-set lived
  in each command body; helpers like `_collect_counts` /
  `_collect_failures` took the matcher and status filters as parameters.

  Collapse that into one pre-pass and one pre-pass only:

  - Add a `ByStatus` `SuiteVisitor` in `_search.py` (Robot has no native
    status filter, so this stays ours, but in the same shape as
    `ByLongName` / `SearchModifier`).
  - Extend `_apply_tree_filters` to also accept `status_filters` and the
    search matcher, bundling every project-specific filter into a single
    `ModelModifier` pass that visits the tree once.
  - After the pre-pass, every surviving test has cleared every filter, so
    `_collect_counts` and `_collect_failures` shrink to a plain tally /
    `[t for t in suite ... if t.status == "FAIL"]`. The
    `_normalise_statuses` / `_raw_test_search_matches` helpers and the
    `_STATUS_KEY_MAP` constant lose their last callers and go away too.
  - One subtle behaviour shift: search now matches `test.name` and
    `test.longname` separately (via `SearchModifier`), where the old
    `_raw_test_search_matches` only saw the full name. That's a strict
    superset — an anchored regex like `^Pass.*` now matches a test
    literally named `Passing Test Three`. Updated
    `test_search_regex_anchors_and_alternation` to pick a pattern that
    matches no field instead of relying on the old narrower contract.

- Polish `results stats` UX and docstrings ([36e3996](https://github.com/robotcodedev/robotcode/commit/36e39961409ed37d4fdb39cead8d789886556655))

  - `--by` now displays the actual choices (`[tag|suite|status]`) in `--help`
    instead of the placeholder `DIMENSION` metavar, so the allowed values
    are discoverable without reading the docs.
  - `stats --by suite` groups by the suite's full name (e.g.
    `MyProject.Login`) rather than the bare leaf name. Suites that share an
    end name in different parts of the tree are now distinguished.
  - Drop internal `report.html` / "Mirrors X" justifications from
    user-facing docstrings — that's plan-rationale, not help text.


#### Diagnostics

- Unify number-literal detection helpers ([4dcb22f](https://github.com/robotcodedev/robotcode/commit/4dcb22f0df161d7f01669d9d7f0fead97613f8c8))

  Replace the direct `robot.variables.finders.NumberFinder` dependency and
  the two duplicated `_try_resolve_number_literal` static methods with
  shared `try_resolve_number_literal` / `is_number_literal` helpers in
  `robot.utils.variables`, consumed from `model_helper`, `namespace_analyzer`
  and the semantic `analyzer`.


#### Tests

- Standardize on pytest-mock and shared analyzer fixtures ([441618c](https://github.com/robotcodedev/robotcode/commit/441618c9d053b2189dde5035a5f0e27489ddd826))

  Replaces direct unittest.mock usage with the project's existing
  pytest-mock convention so tests are stricter (autospec) and new tests
  need less boilerplate.



## [2.5.1](https://github.com/robotcodedev/robotcode/compare/v2.5.0..v2.5.1) - 2026-04-01

### <!-- 1 -->Bug Fixes

#### Robot

- Match longest BDD prefix first for multi-word prefixes ([dad536e](https://github.com/robotcodedev/robotcode/commit/dad536ecc44e4cdad9f222b3387f276dc7e6ee0a))

  French BDD prefixes like "Étant donné que", "Et que",
  "Mais que" were not fully recognized because shorter prefixes (e.g.
  "Et") matched before longer ones (e.g. "Et que").

  Replaced manual iteration and set lookups with a regex-based approach
  matching Robot Framework's own strategy: prefixes sorted by length
  (longest first), compiled into a cached regex pattern. This applies to
  keyword_finder, model_helper (split/strip/is_bdd), and semantic tokens.

- Fix ${CURDIR} replacement in variable values and unify handling ([13bf36b](https://github.com/robotcodedev/robotcode/commit/13bf36b8639887ff21d807a0045f8432b81fce8c))

  Extract replace_curdir_in_variable_values() helper into utils/variables.py
  to deduplicate the ${CURDIR} substitution logic from _MyResourceBuilder and
  NamespaceAnalyzer. Fixes incorrect double-backslash escaping in
  _MyResourceBuilder that caused ${CURDIR} resolution to fail on Windows.


#### Analyzer

- Do not report embedded arguments as VariableNotFound in template keywords ([c34455f](https://github.com/robotcodedev/robotcode/commit/c34455fe3a2a485bf361b65a6b52b55650d674b7))

  When a test case uses [Template] or Test Template with a keyword that has
  embedded arguments (e.g. "The result of ${calculation} should be ${expected}"),
  the embedded argument placeholders were incorrectly analyzed as unresolved
  variables, producing false VariableNotFound diagnostics.

  Skip variable analysis for embedded argument tokens when the keyword call
  originates from a template declaration.



### <!-- 2 -->Documentation

#### News

- Add v2.5.1 release notes ([b0d9fb9](https://github.com/robotcodedev/robotcode/commit/b0d9fb94fc6dc36ae4ff9fba0f8a5c3ba3888dd0))


### <!-- 4 -->Refactor

#### Diagnostics

- Add debug logging for namespace cache misses ([99e322d](https://github.com/robotcodedev/robotcode/commit/99e322d8d9be298fbb22bb46d2283fa2db26e223))

  Log specific reasons when namespace cache entries are invalidated,
  including source mtime changes, config fingerprint mismatches, and
  dependency changes (libraries, resources, variables). Uses debug
  level with context_name="cache" for targeted activation.



## [2.5.0](https://github.com/robotcodedev/robotcode/compare/v2.4.0..v2.5.0) - 2026-03-31

### <!-- 0 -->Features

#### Analyze

- Add cache management CLI commands ([1421107](https://github.com/robotcodedev/robotcode/commit/1421107e20473b441861958feca96262832946bb))

  Add `robotcode analyze cache` subcommand group with five commands:
  - `path`: print resolved cache directory
  - `info`: show cache statistics with per-section breakdown
  - `list`: list cached entries with glob pattern filtering (-p)
  - `clear`: remove cached entries by section
  - `prune`: delete entire .robotcode_cache directory

  Output adapts to the global --format flag (text/json/toml) and
  --no-color mode. Text output uses rich-rendered markdown tables
  when color is enabled, plain aligned tables otherwise.

- Enable namespace caching by default ([d896213](https://github.com/robotcodedev/robotcode/commit/d8962139775144697c2d3e41fe37f6595bc272d6))

  Namespace caching speeds up startup for large projects by skipping
  re-analysis of unchanged files. It is now mature enough to be enabled
  by default.

- Add --cache-namespaces/--no-cache-namespaces CLI option ([b050c32](https://github.com/robotcodedev/robotcode/commit/b050c32e94989f638ec0cfcafe5122bfdf3a4945))

  Add option to enable/disable caching of fully analyzed namespace data
  to disk. Disabled by default until the cache is fully optimized and
  validated. When enabled, skips re-analysis of unchanged files on
  startup, which can significantly speed up large projects.

  Available as CLI flag (--cache-namespaces/--no-cache-namespaces),
  robot.toml setting (tool.robotcode-analyze.cache.cache_namespaces),
  and VS Code setting (robotcode.analysis.cache.cacheNamespaces).

- Add collection of unused keywords and variables on the CLI ([5734690](https://github.com/robotcodedev/robotcode/commit/5734690b4a9a627306751c704b6fc0934739a1fc))

  Add support for collecting unused keyword and variable diagnostics when
  running `robotcode analyze code` from the command line.

  The feature can be enabled in `robot.toml`:

  ```toml
  [tool.robotcode-analyze.code]
  collect-unused = true
  ```

  or controlled directly per invocation:

  ```bash
  robotcode analyze code --collect-unused
  robotcode analyze code --no-collect-unused
  ```


#### Language Server

- Add code completion for `Literal` type hint values ([42ab3a0](https://github.com/robotcodedev/robotcode/commit/42ab3a073e562c21474d39667ef653948128abe6))

  Keywords with `Literal["fast", "slow", "auto"]` type hints now show
  their allowed values in the completion list, making it easier to
  discover and select valid argument values without checking the
  keyword documentation.

  Also supports `Union` types containing `Literal`, e.g.
  `Union[Literal["x", "y"], int]`.

- Add json to watched file extensions ([74e92b0](https://github.com/robotcodedev/robotcode/commit/74e92b00ef947291e7e6bd0fe09f37b919292b85))

#### Plugin

- Add `has_rich` property to detect `rich` availability ([4581cc6](https://github.com/robotcodedev/robotcode/commit/4581cc6e7594798a28c0795a0f56b7e5fca62a9b))

  Fall back to plain-text output in cache CLI commands when the `rich`
  package is not installed, instead of dumping raw unformatted markdown.


#### Robot

- Add `ROBOTCODE_CACHE_DIR` env var for cache path override ([a778cd5](https://github.com/robotcodedev/robotcode/commit/a778cd58542b841966047278ad6fa91049f38c25))

  Enable redirecting the analysis cache to a custom directory via the
  `ROBOTCODE_CACHE_DIR` environment variable. This allows all RobotCode
  tools — CLI commands, analyze runs, and the language server — to
  share the same cache regardless of where it is stored.

  The VS Code extension automatically sets this variable in the
  integrated terminal, so CLI commands find the correct cache
  without any manual setup.

  Cache clearing now operates on the database directly instead of
  removing the directory, preventing errors when multiple processes
  access the cache concurrently.

- Add advisory file locking to SQLite cache ([b9351fc](https://github.com/robotcodedev/robotcode/commit/b9351fc3f4c9515e56ebfbd13a9b744ac88bee52))

  Add shared/exclusive advisory file locking (fcntl.flock) to prevent
  `prune` from deleting a cache database while another process (language
  server, analyze run) is using it.

- Add SQLite cache backend for library and namespace data ([edaea47](https://github.com/robotcodedev/robotcode/commit/edaea473b9d51f52b1a91c705facf2a31ad571c3))

  Replace file-based pickle caching with a single SQLite database per
  workspace, consolidating all cache entries into one file instead of
  many individual .pkl files scattered across directories.

- Add namespace disk cache for cold-start acceleration ([abf3387](https://github.com/robotcodedev/robotcode/commit/abf33871b16b1b344c85c2ae77a344a2a5dcd6b1))

  Speed up first-time file analysis by caching fully resolved
  namespace results to disk. On subsequent IDE starts, cached
  namespaces are reused instead of re-analyzing every file from
  scratch, significantly reducing the time until diagnostics,
  code completion, and navigation become available.

  The cache is automatically invalidated when source files,
  library dependencies, environment variables, command-line
  variables, language configuration, or the RobotCode version
  change.

- Add ProjectIndex for O(1) workspace-wide reference lookups ([6ef90f1](https://github.com/robotcodedev/robotcode/commit/6ef90f111f367af51924f1f991ba02ae6e807298))

  Add an incrementally maintained inverse reference index (ProjectIndex)
  scoped per WorkspaceFolder. On each file build, references are updated
  in-place instead of scanning all files. All six reference types are
  supported: keywords, variables, namespace entries, keyword tags,
  testcase tags, and metadata.

- Track tag and metadata references in namespace analysis ([6a372fe](https://github.com/robotcodedev/robotcode/commit/6a372febb092055b4fec4528b5f5870233c854da))

  Add structured reference tracking for tags and metadata during analysis.
  Tags are split into keyword_tag_references and testcase_tag_references
  to reflect their different semantics in Robot Framework (keyword visibility
  vs test selection/reporting). Metadata references track settings-level
  metadata entries by key. All reference keys are normalized for consistent
  lookups. Remove unused TagDefinition class.


#### VS Code

- Show "What's New" notification after extension update ([7fb2071](https://github.com/robotcodedev/robotcode/commit/7fb2071104be976d0099f54c65aa58476e01a806))

  Display an info notification when the extension version changes,
  linking to the news page on robotcode.io via the built-in Simple Browser.
  Also adds a public "RobotCode: Show What's New" command to the palette.


#### Settings

- Remove deprecated robocop configuration options ([fa2217e](https://github.com/robotcodedev/robotcode/commit/fa2217eaeae800023c6961970ee93ec715f28d53))


### <!-- 1 -->Bug Fixes

#### Robot

- Strip trailing `=` from variable names in resource builder ([e11ca60](https://github.com/robotcodedev/robotcode/commit/e11ca6061ecf7b1659e74a72ddecb6baadc545a3))
- Do not override the source on a model if there is already a source field ([7e74c2d](https://github.com/robotcodedev/robotcode/commit/7e74c2dfbe57367edacc81fd0f6460d23337eccc))

  Newer Robot Framework versions already set the source field on File AST blocks, so overriding it here is unnecessary.

- Resolve relative library paths in namespace cache validation ([45d8f9f](https://github.com/robotcodedev/robotcode/commit/45d8f9f92a01987955df48325ea16f4a10fbcf75))

  Namespace cache validation failed for files importing libraries via
  relative paths (e.g. ../../resources/libraries/common.py), causing
  unnecessary full rebuilds on every warm start.

  Two issues fixed:
  - validate_namespace_meta now passes the source file's directory as
    base_dir when falling back to get_library_meta/get_variables_meta,
    so relative paths resolve correctly
  - get_library_meta and get_variables_meta initialize import_name
    before the try block to avoid UnboundLocalError when find_library
    or find_variables fails

- Correct check for __init__.py file in _is_valid_file function ([ffad219](https://github.com/robotcodedev/robotcode/commit/ffad219d9bc4311a2f1a70d272feb942467b1bfb))
- Add lock for _workspace_languages to prevent race condition ([9bf0ee6](https://github.com/robotcodedev/robotcode/commit/9bf0ee619d20d1f676b35797867260aab924a2af))

  WeakKeyDictionary is not thread-safe for concurrent read/write.
  Protect all access to _workspace_languages with a dedicated RLock.



### <!-- 2 -->Documentation

- Update release notes for v2.5.0 with ([9978a88](https://github.com/robotcodedev/robotcode/commit/9978a8869359ca7dbfbbde7ac3ddc96dd1eb1996))
- Add news section to documentation site ([7f14925](https://github.com/robotcodedev/robotcode/commit/7f1492508bef6f487e31bbd8f532449d7c05d392))

  Add a dedicated news section for release announcements with
  auto-generated sidebar (sorted newest-first), content loader,
  and redirect from /news/ to the latest article.

#### News

- Add supplementary release note for v2.5.0 ([a8c39a3](https://github.com/robotcodedev/robotcode/commit/a8c39a377a74db9fe2a93e165415d0e805470d2d))


### <!-- 3 -->Performance

#### Robot

- Patch RF's variable_not_found to skip slow RecommendationFinder ([78a26c3](https://github.com/robotcodedev/robotcode/commit/78a26c3004717f06edadda114d8d196fd9729e7e))

  Robot Framework's variable_not_found() calls RecommendationFinder for
  fuzzy "Did you mean...?" suggestions on every unresolved variable. This
  is O(n*m) over all variable candidates and extremely slow for large
  projects (see #587: 30+ min for 375 files).

  RobotCode never uses the recommendation text — all VariableError catch
  sites either ignore the error or use it for unrelated diagnostics.

  The monkey-patch replaces variable_not_found in all 5 RF modules that
  import it (notfound, finders, evaluation, store, __init__) with a fast
  version that raises VariableError with just the base message.

- Speed up namespace cache loading with source hints and top-level-only imports ([1d4ba6b](https://github.com/robotcodedev/robotcode/commit/1d4ba6b73f0e1b57341b5f116084c0ab0902dcc7))

  Add resolved_resource_sources to NamespaceData that maps import hint
  keys to resolved file paths. During from_data() re-resolution, these
  hints skip expensive find_resource() filesystem searches when the
  cached path still exists on disk.

  Also limit cached imports to top-level only (recursive imports are
  re-discovered during resolution), replace Path-based normalization
  with string-only os.path calls in imports_manager, and add a hint_key
  property to Import for consistent key computation.

- Fix ArgumentSpec.resolve() caching bug for RobotArgumentSpec ([05142c8](https://github.com/robotcodedev/robotcode/commit/05142c821a64136453a1388c2d30dccb08093bd7))

  The RobotArgumentSpec was recreated on every call (100K times) because:
  - hasattr() always returned False with @dataclass(slots=True)
  - Assignment went to a local variable instead of self

  RobotArgumentSpec.__init__ calls: 100K → 1.3K (-98.7%)
  resolve cumtime: 3.93s → 3.29s (-0.64s)
  Warm no-NS total: 30.78s → 29.81s (-0.97s, -3.2%)

- Replace pathlib with os.path in file resolution ([f3118bd](https://github.com/robotcodedev/robotcode/commit/f3118bd2d5213f0e6404e476025a40799205c383))

  Replace pathlib.Path operations with os.path string functions
  in robot_path.py for significantly faster file resolution:

  - Use os.path.join/abspath/isfile/isdir instead of Path objects
  - Cache validated sys.path entries lazily (_get_valid_sys_path)
  - Separate basedir check from sys.path iteration
  - Introduce _PathLike type alias for cleaner signatures
  - Fix is_fifo() bug: use os.path.isfile() for __init__.py check

  Warm namespace-cache scenario: 19.30s -> 13.84s (-28.3%).
  Pathlib calls reduced by 78-100%, posix.stat calls by 35%.

- Cache KeywordMatcher and add dict-index to KeywordStore ([5d21baf](https://github.com/robotcodedev/robotcode/commit/5d21bafb711091112d473f3d5c9c47865a22796d))

  - Cache KeywordMatcher on KeywordDoc via lazy-init _matcher slot,
    eliminating 7.5M redundant instantiations per analysis run
  - Add dict-index (_index + _embedded) to KeywordStore for O(1)
    keyword lookup by normalized name; linear scan only for embedded
    keywords
  - Add __getstate__/__setstate__ to KeywordDoc and KeywordStore to
    exclude transient fields (_matcher, _index, _embedded, parent,
    _hash_value, _stable_id) from pickle serialization
  - Restore parent references in LibraryDoc.__setstate__ via
    _update_keywords after deserialization
  - Remove unused nosave metadata from argument_definitions, parent,
    and keyword_doc fields
  - Fix Application.keyboard_interrupt to use self.exit() for
    consistent shutdown behavior

  Measured improvement (cProfile, 1065 Robot files):
  - Warm no-NS: 37.46s -> 29.25s (-22%)
  - Cold no-NS: 42.94s -> 33.39s (-22%)
  - Keyword matching: ~9.0s -> ~0.5s (-94%)
  - Function calls: 118M -> 81M (-31%)

- Optimize dataclass identity for ProjectIndex caching ([deedd7b](https://github.com/robotcodedev/robotcode/commit/deedd7be944b426f4f9d65ff90fbfae464f33086))

  Prepare VariableDefinition, KeywordDoc, and LibraryDoc for efficient
  use as dictionary keys in the upcoming ProjectIndex disk cache and
  cross-process worker communication.


#### Cache

- Defer data blob loading in CacheEntry until first access ([795c420](https://github.com/robotcodedev/robotcode/commit/795c42073b49071eabc9a8afd4c4e7eb1659dceb))

#### Diagnostics

- Remove redundant exists() check in get_resource_meta ([5696868](https://github.com/robotcodedev/robotcode/commit/569686849ffc2f286e3af93095cfef8e5b5767ce))
- Consolidate to single AST model and remove data_only parameter ([e2e4cbd](https://github.com/robotcodedev/robotcode/commit/e2e4cbd04d58d2d775742c0fddaee63f948c335d))

  This eliminates the second cached AST model per document, saving ~500KB/doc
  in CLI and ~200KB/doc in the Language Server. Releasing the model reference
  after analysis frees an additional ~100-500KB/doc in CLI mode.


#### Imports

- Cache get_module_spec results in ImportsManager ([fa83b30](https://github.com/robotcodedev/robotcode/commit/fa83b3045dc4f87f91952bb1ab0ec64e492be28a))


### <!-- 4 -->Refactor

- Introduce RF_VERSION constant and remove RF < 5.0 dead code ([02cf495](https://github.com/robotcodedev/robotcode/commit/02cf495faa1683a3ff6f62552cf1fb5d7f86454d))

  - Add module-level RF_VERSION constant to robotcode.robot.utils,
    resolved once at import time instead of repeated lru_cache lookups
  - Remove dead code paths for Robot Framework < 5.0 (no longer supported),
    including the internal tidy-based formatter and obsolete version branches
  - Replace all ~134 get_robot_version() call sites across 27 files with
    the RF_VERSION constant

#### Robot

- Remove unnecessary type casting in CacheEntry ([c4eb160](https://github.com/robotcodedev/robotcode/commit/c4eb160b6d02ce95e51f3c0084cdf9ccf209bd75))
- Optimize RF_VERSION checks with module-level dispatch ([eec1627](https://github.com/robotcodedev/robotcode/commit/eec1627f7777d17b8928ea6678b7905b9f933d5e))

  - Remove redundant _ROBOT_VERSION alias in semantic_tokens.py
  - Remove always-true RF >= 5.0 guards (minimum supported version)
  - Use conditional class-level property/method definitions for
    is_private and is_reserved in library_doc.py
  - Add _RF7_PLUS module-level bool for BDD keyword search hot path
  - Move ExceptHeader/WhileHeader imports to top-level (always available)

- Replace Namespace getter methods with read-only properties ([127ad65](https://github.com/robotcodedev/robotcode/commit/127ad6550e691011b8916620b28765c5b3c039ed))
- Extract Namespace into DTO with event-driven invalidation ([4f37419](https://github.com/robotcodedev/robotcode/commit/4f3741906798e9ff5a5263c7f1a8413b4e55ff66))

  Split the monolithic Namespace class into focused modules to reduce
  complexity and improve maintainability. The Namespace is now a pure data
  container built by NamespaceBuilder, with dedicated modules for import
  resolution, AST analysis, variable scoping, and scope trees.


#### Cache

- Optimize SqliteDataCache with lazy deserialization and per-section tables ([eeec613](https://github.com/robotcodedev/robotcode/commit/eeec61379aa9bca255389d8f60246a140b0bc0db))

  Replace single cache_entries table with per-section tables (libdoc,
  variables, resource, namespace) for better query performance.

  Introduce CacheEntry with lazy meta/data deserialization — data blobs
  are only unpickled on cache hit, avoiding expensive deserialization on
  meta mismatch.

  Move version checking from per-entry meta_version field to DB-level
  app_version parameter. On version mismatch all tables are dropped and
  recreated automatically.

  Simplify cache API from 3 methods (cache_data_exists, read_cache_data,
  save_cache_data) to 2 (read_entry, save_entry), reducing DB
  round-trips from 3 to 1 for reads and 2 to 1 for writes.

  Remove filepath_base property (adler32 hash-based keys) from all
  metadata classes — cache keys now use source paths or library names
  directly.


#### Diagnostics

- Extract _run_in_subprocess and _save_import_cache helpers ([0c347fd](https://github.com/robotcodedev/robotcode/commit/0c347fd9a55f4e9cca8a86628addd297df52e468))

  - Unify duplicated ProcessPoolExecutor lifecycle from
    _get_library_libdoc and _get_variables_libdoc into _run_in_subprocess
  - Unify duplicated cache save logic into _save_import_cache

- Deduplicate and optimize metadata classes in imports_manager ([a0cb4c6](https://github.com/robotcodedev/robotcode/commit/a0cb4c6820f895e2e56bbeb20a406ba2270f2a46))

  - Extract _collect_library_mtimes() to unify duplicated mtime collection
    from get_library_meta and get_variables_meta, using os.walk instead of
    Path.rglob for better performance
  - Extract _matches_any_pattern() to unify triplicated pattern matching
  - Add slots=True to LibraryMetaData, RobotFileMeta, and NamespaceMetaData
  - Move mtime collection into dataclass constructors to avoid post-init mutation
  - Remove unused itertools import


#### Jsonrpc2

- Harden resource lifecycle without __del__ ([5cb7bb7](https://github.com/robotcodedev/robotcode/commit/5cb7bb71fac305a8dc7039187c4b076ab7d90bbd))

  - remove __del__-based resource cleanup from server, debugger client, and protocol
  - move shutdown to explicit close/close_async paths
  - make JsonRPCServer.close wait for server shutdown when safe
  - add best-effort weakref finalizers for forgotten cleanup without noisy warnings
  - unify runtime and finalizer bookkeeping into shared state objects



## [2.4.0](https://github.com/robotcodedev/robotcode/compare/v2.3.1..v2.4.0) - 2026-03-17

### <!-- 0 -->Features

#### Plugin

- Add fast exit option to Application.exit method ([acfa7e9](https://github.com/robotcodedev/robotcode/commit/acfa7e9a2d6b138f487183e19b8700d2e88db313))


### <!-- 1 -->Bug Fixes

#### VS Code

- Fix invalid glob pattern in selectConfigurationProfiles ([58b5a8f](https://github.com/robotcodedev/robotcode/commit/58b5a8f1d1b8a2363a08b7872e20519316a44025))

  Remove extra closing brace in the file extension glob pattern that
  caused workspace folder detection to fail when selecting configuration
  profiles.


#### Dependencies

- Update click version to 8.2.0 in requirements files ([6e1220e](https://github.com/robotcodedev/robotcode/commit/6e1220e0542dc12a37dcb6c489d1653238ffbe8e))


### <!-- 3 -->Performance

#### Robot

- Cache LibraryDoc for robot and resource files on disk ([9b89623](https://github.com/robotcodedev/robotcode/commit/9b896236c2590571fd5cb4cd95fbb156d0929cb1))

  Resource and robot files are now cached on disk between sessions.
  On subsequent opens, imports, keywords, and variables from these
  files are loaded from cache instead of being re-parsed, resulting
  in faster startup and quicker response times when navigating
  projects with many resource files.

  The cache is automatically invalidated when a file is modified
  on disk. Files that are currently open in the editor always use
  the live content and bypass the disk cache.

- Remove unnecessary token list caching from document cache ([5f8591d](https://github.com/robotcodedev/robotcode/commit/5f8591d9a079261769d4a2c718c53124c22d510b))

  Token lists were cached separately in document._cache, but only used
  as intermediate input for AST model building. No external caller ever
  accessed the cached token lists directly.

  Move token generation into model builder methods so tokens are only
  produced on cache miss. On cache hit, neither tokenization nor model
  building occurs.

  - Eliminates up to 6 cached token lists per document in Language Server
  - No behavior change for CLI (tokens were already uncached for version=None)
  - Remove ~80 lines of redundant caching infrastructure

- Use file_id tuples instead of os.path.samefile for path comparison ([3f3bd84](https://github.com/robotcodedev/robotcode/commit/3f3bd8430a5c745bae6d0274ab4001acbe73044e))

  Replace repeated os.path.samefile() calls (2x stat per call) in namespace
  import loops with pre-computed (st_dev, st_ino) tuple comparisons.

  - Add FileId type, file_id() and same_file_id() to core utils
  - Add lazy source_id property to LibraryDoc (excluded from pickle)
  - Pre-compute source_id on Namespace init
  - Compute file_id once per find_resource result instead of per-iteration


#### Diagnostics

- Skip full AST model parsing when no robotcode: markers present ([7b3999e](https://github.com/robotcodedev/robotcode/commit/7b3999e203209c67613f27fecacc943ac981d824))


### <!-- 4 -->Refactor

#### Robot

- Remove unnecessary finalizers and dispose chain ([eaa7e14](https://github.com/robotcodedev/robotcode/commit/eaa7e14e2672cbf8da49a2eb58205384bd34c9cf))

  Remove redundant _release_watchers_finalizer from _ImportEntry — file
  watcher cleanup is already handled explicitly by _remove_file_watcher()
  during invalidation and by server_shutdown() at LS shutdown.

  Remove the _dispose_finalizer/dispose() chain through ImportsManager,
  DocumentsCacheHelper, RobotFrameworkLanguageProvider, CodeAnalyzer, and
  CLI. With the per-entry finalizers gone, these only cleared dicts that
  Python already cleans up at process exit.

  Fix broken finalizer in Workspace.add_file_watchers() where the closure
  captured the entry object, preventing it from ever being garbage
  collected.

  Set atexit=False on sentinel finalizers so they only fire during normal
  GC (needed for LS live cleanup), not at interpreter shutdown.

- Replace __del__ with weakref.finalize in imports_manager ([e0e8d81](https://github.com/robotcodedev/robotcode/commit/e0e8d81219d1da8682839ab804cbc94408cf7d3f))

  Replace fragile `__del__` methods with `weakref.finalize` in both
  `_ImportEntry` and `ImportsManager` for reliable cleanup:

  - _ImportEntry: register finalizer in __init__ with file_watchers list
    and file_watcher_manager as strong refs (no self access needed);
    change _remove_file_watcher to use .clear() instead of = []
  - ImportsManager: register finalizer lazily in executor property when
    ProcessPoolExecutor is created; add static _shutdown_executor callback

  weakref.finalize is guaranteed to run even with circular references
  and does not prevent garbage collection of reference cycles.


#### Imports_manager

- Cleanup and fix correctness issues ([25ef49c](https://github.com/robotcodedev/robotcode/commit/25ef49c3ea0fec68f4f36a702e8f20a3c32c5537))


## [2.3.1](https://github.com/robotcodedev/robotcode/compare/v2.3.0..v2.3.1) - 2026-03-12

### <!-- 1 -->Bug Fixes

#### Language Server

- Update version check for Robocop in formatting and diagnostics parts ([45655f4](https://github.com/robotcodedev/robotcode/commit/45655f4c62a634b76f4e57bf284b366b2e79ce35))


## [2.3.0](https://github.com/robotcodedev/robotcode/compare/v2.2.0..v2.3.0) - 2026-03-12

### <!-- 0 -->Features

#### Robocop

- Robocop 8.0 support ([f723d98](https://github.com/robotcodedev/robotcode/commit/f723d98bd3ec9ac4234ab5661681f09220c942ac))


### <!-- 2 -->Documentation

#### Tips-and-tricks

- Make LSP config OS independent ([e1abda2](https://github.com/robotcodedev/robotcode/commit/e1abda26de71f447dee3fbdc94e400a2ed1ac504))

  More robust implementation of get_python_path helper function.

- LSP setup guide for Neovim ([c63c125](https://github.com/robotcodedev/robotcode/commit/c63c125b39e904ceaa85bc48c78accfbd63d53e1))


## [2.2.0](https://github.com/robotcodedev/robotcode/compare/v2.1.0..v2.2.0) - 2026-01-02

### <!-- 0 -->Features

- Add support for Robot Framework 7.4 ([3e140c9](https://github.com/robotcodedev/robotcode/commit/3e140c9a18fbe563f0f4c7a7fdee306fdcf97225))
- Enhance diagnostics and analysis features with progress indicators in verbose mode and performance improvements ([1ac9247](https://github.com/robotcodedev/robotcode/commit/1ac9247fa820605e66d6dc61f24732edab662f12))

### <!-- 1 -->Bug Fixes

#### Language Server

- Default to folding ranges to character-based ([6cbefe2](https://github.com/robotcodedev/robotcode/commit/6cbefe2901890930a89ce7e53bcd1a26b51ba4e1))

  Use character-based folding ranges by default when client capabilities are unknown.


#### PyCharm

- Add missing language method in RobotCodeCodeStyleSettingsProvider ([90673bf](https://github.com/robotcodedev/robotcode/commit/90673bf16393ff317079059c870c97340229f0e7))

#### Robot

- Use explicit class reference for super() in VariablesDoc to allow slots ([8af05a9](https://github.com/robotcodedev/robotcode/commit/8af05a9756bd957c7cba03c0ca9ac91a691ab598))

#### Robocop

- Update robocop documentation urls ([c15bdfa](https://github.com/robotcodedev/robotcode/commit/c15bdfa27713ed68959a8ccbf5a2d61469a8fa06))


### <!-- 2 -->Documentation

- Add some funny random hero images ([f62e1bd](https://github.com/robotcodedev/robotcode/commit/f62e1bd8cfe621414c1a45f318f687407731a401))
- Back to normal hero image ([57633b5](https://github.com/robotcodedev/robotcode/commit/57633b5a1271c5383a548234108ece0aa86be88d))

### <!-- 3 -->Performance

#### Lsp

- Use dataclass slots for protocol types ([82012e8](https://github.com/robotcodedev/robotcode/commit/82012e8c478b75e1781b3eb3ac9f9c3a4ce0c29a))

  use @dataclass(slots=True) for LSP model classes to reduce per-instance memory overhead and speed up attribute access in LSP hot paths



### <!-- 4 -->Refactor

- Reduce lru_cache maxsize for performance optimization across multiple modules ([f715d32](https://github.com/robotcodedev/robotcode/commit/f715d3239ba19b6eaa9f8a346ab61bf524aa5dc8))
#### Core

- Simplify casing caches and add support for PEP 604 unions ([428226a](https://github.com/robotcodedev/robotcode/commit/428226a8d393e7f650e5b7caa43feb090587490c))


## [2.1.0](https://github.com/robotcodedev/robotcode/compare/v2.0.4..v2.1.0) - 2025-12-02

### <!-- 0 -->Features

#### VS Code

- Add option to control extension activation per scope ([7af4583](https://github.com/robotcodedev/robotcode/commit/7af4583367c1746bb089eedb085fcb6d5f9fe966))

  Add new `robotcode.disableExtension` configuration setting that allows
  users to disable or enable the RobotCode extension at any scope level.

  With resource scope, users can:
  - Disable the extension globally (user settings) and enable it for
    specific workspaces or folders
  - Disable the extension for a workspace and enable it for specific
    folders within
  - Disable the extension only for specific folders in multi-root
    workspaces

  This is useful in:
  - Large workspaces where RobotCode is not needed everywhere
  - Multi-root workspaces with mixed project types
  - Environments where users want opt-in rather than opt-out behavior



### <!-- 2 -->Documentation

- Correct some stylings ([5edb90c](https://github.com/robotcodedev/robotcode/commit/5edb90c90700bb0fea5773f102171e14da8f6abd))
- Make the hero image a bit more christmassy ([4fd8412](https://github.com/robotcodedev/robotcode/commit/4fd841257ed6f9297799a7b9ab1ce829c6837266))

### <!-- 3 -->Performance

#### VS Code

- Cache getRobotCodeProfiles results ([8aa6db5](https://github.com/robotcodedev/robotcode/commit/8aa6db5f39252106d138d49a40f8050dbe00da81))

  Add caching for robot.toml profiles to avoid spawning a new process
  on every call. Cache is invalidated on language client state changes.



## [2.0.4](https://github.com/robotcodedev/robotcode/compare/v2.0.3..v2.0.4) - 2025-11-25

### <!-- 2 -->Documentation

- Add diagnostics modifiers section to reference documentation ([52b1deb](https://github.com/robotcodedev/robotcode/commit/52b1debd4dc337221e195d86a56677b4c300f27c))
- Correct command syntax for running tests with overridden variables ([bfc6801](https://github.com/robotcodedev/robotcode/commit/bfc6801da41c8068b248c918955d581b55a628d2))

## [2.0.3](https://github.com/robotcodedev/robotcode/compare/v2.0.2..v2.0.3) - 2025-11-20

### <!-- 1 -->Bug Fixes

#### VS Code

- Correct configurations in settings view ([8bd0329](https://github.com/robotcodedev/robotcode/commit/8bd0329f768bb2440f4409869b442edc807da0a7))


## [2.0.2](https://github.com/robotcodedev/robotcode/compare/v2.0.1..v2.0.2) - 2025-11-19

### <!-- 1 -->Bug Fixes

#### VS Code

- Improve workspace folder resolution logic for chat tools ([de73d7d](https://github.com/robotcodedev/robotcode/commit/de73d7d2fc347d6cfc37f9319e20ee81efe006ef))


### <!-- 2 -->Documentation

- Add Robot Framework Foundation and imbus as sponsors ([804758c](https://github.com/robotcodedev/robotcode/commit/804758c7ed75c1f7145a1370f0e2e33393c582e9))

## [2.0.1](https://github.com/robotcodedev/robotcode/compare/v2.0.0..v2.0.1) - 2025-10-10

### <!-- 1 -->Bug Fixes

- Corrected packaging of python wheels/vscode packages ([242f822](https://github.com/robotcodedev/robotcode/commit/242f822c5ffa2b6c0611620f0701a0286d405d87))

## [2.0.0](https://github.com/robotcodedev/robotcode/compare/v1.9.0..v2.0.0) - 2025-10-10

### <!-- 0 -->Features

- Drop Python 3.8 and 3.9 support, require Python 3.10+ ([7c825de](https://github.com/robotcodedev/robotcode/commit/7c825de2fa1a956e375dc01f542c66b8975d687c))
  - **BREAKING**: Python 3.8 and 3.9 are no longer supported. Minimum required version is now Python 3.10.
#### Language Server

- Add support for folding documentation settings ([2b627d7](https://github.com/robotcodedev/robotcode/commit/2b627d7e107a6290da8c6ac7f77e246b53553071))
- Remove Robotidy support ([c49bf40](https://github.com/robotcodedev/robotcode/commit/c49bf405900ca9226463f87719f6cc678d8ff8ae))
  - **BREAKING**: remove Robotidy support

  Use robotframework-robocop>=6.0 for formatting.



### <!-- 1 -->Bug Fixes

- Remove Python 3.8 support and update classifiers for Python 3.14 ([e642d5b](https://github.com/robotcodedev/robotcode/commit/e642d5bf4ea9cf9169ea9aadcc4945251a3063db))
#### Debugger

- Handle breakpoints in `__init__.robot` files correctly ([34da5e7](https://github.com/robotcodedev/robotcode/commit/34da5e7db1955f7dde5a3a1c60f46cdc9fc6ea82))

#### Language Server

- Support for Python 3.14 ([d7fe624](https://github.com/robotcodedev/robotcode/commit/d7fe624a79a09ecfbc4fa0ff61acb86a0d54b873))
- Update sort_text to use e.label for better clarity in import completion items ([39e1272](https://github.com/robotcodedev/robotcode/commit/39e12726f73004ef9083dd767ef8d1dbd6c9bd06))

#### Robot

- Change logger level from critical to trace for LoadLibrary timeout ([52fc3b0](https://github.com/robotcodedev/robotcode/commit/52fc3b0c642447bd9cb424d16693307bab1c285f))
- Change logger level from critical to trace for load_library_timeout ([c0e6898](https://github.com/robotcodedev/robotcode/commit/c0e68986287c79ae411a95286d1e31d41c8a0b36))


### <!-- 2 -->Documentation

- Update Python version references to 3.12.6 and adjust testing matrix to 3.10-3.14 ([0d41933](https://github.com/robotcodedev/robotcode/commit/0d41933d15b516c7884557cbba157230ac96a70b))
- Disable math rendering in VitePress config and remove related dependencies ([5390600](https://github.com/robotcodedev/robotcode/commit/5390600fd211cbe8761a51f0864439c837605d50))

## [1.9.0](https://github.com/robotcodedev/robotcode/compare/v1.8.0..v1.9.0) - 2025-09-12

### <!-- 0 -->Features

#### Robot

- Define more detailed error message for library load timeout ([d5848ab](https://github.com/robotcodedev/robotcode/commit/d5848ab6d9b1285a6dc2465869b2bc274693603e))
- Environment variable for load library timeout ([20c98c3](https://github.com/robotcodedev/robotcode/commit/20c98c3db7beaa9e67b8214f41976a70048305e6))

#### Analyze,robot

- Add configurable load_library_timeout with CLI flag and robot.toml support ([461212d](https://github.com/robotcodedev/robotcode/commit/461212d8c5ce8f24ce795b33ed0b6106bbba9497))

  Add configurable library/variable load timeout. Sources (precedence):

  analyze code: --load-library-timeout / --no-load-library-timeout
  VS Code setting: robotcode.analysis.robot.loadLibraryTimeout
  robot.toml / pyproject: [tool.robotcode-analyze] load-library-timeout
  Env: ROBOTCODE_LOAD_LIBRARY_TIMEOUT
  Default: 10
  Replaces previous hard-coded timeout, adds validation (>0), clearer docs, and examples.



### <!-- 1 -->Bug Fixes

#### Robot

- Update class inheritance from BaseOptions to RobotBaseOptions for consistency ([1f18c52](https://github.com/robotcodedev/robotcode/commit/1f18c52600e9e467c835f9ebc0586b093e201def))
- Improve timeout error messages for library and variable loading ([d698900](https://github.com/robotcodedev/robotcode/commit/d698900bad4e0df6df26c925905777b245414164))
- Use --no* for disabled RF flags (e.g. --noexitonfailure) instead of short enable flags ([a6ffcf5](https://github.com/robotcodedev/robotcode/commit/a6ffcf56fdaa76efcb2f7ec7b6cfbad6d6ea2ddb))

#### Tests

- Use raw string notation for regex in exception matchers ([d6ba124](https://github.com/robotcodedev/robotcode/commit/d6ba12461f9f29e680c094b1f9279206300fb322))


### <!-- 2 -->Documentation

- Enhance README.md's and remove redundant license files across packages ([f21f4ea](https://github.com/robotcodedev/robotcode/commit/f21f4eafc43cf6bbea60e87f15025a6c4dcfed7c))
- Add comprehensive security policy and reporting guidelines ([a49027a](https://github.com/robotcodedev/robotcode/commit/a49027a2ba6c6eaa4d96a4cbb78f91cc8ded4d91))
- Update links and improve wording in documentation ([409c393](https://github.com/robotcodedev/robotcode/commit/409c393b716904a66b76885400f3953083eb8a7d))
- Reorganize support section in README.md for clarity ([22e56b7](https://github.com/robotcodedev/robotcode/commit/22e56b7a4e4e8ec47d62649ef83445b32aeb3742))
#### Config

- Add load-library-timeout option for library and variable loading to json schema ([d93a397](https://github.com/robotcodedev/robotcode/commit/d93a397fcb2018b46cca2b41c186e559709d09bd))


### <!-- 4 -->Refactor

#### Tests

- Remove performance tests for argument processing ([d019a60](https://github.com/robotcodedev/robotcode/commit/d019a60fccb23e3d4a7d1269aae3379b97ce803b))


## [1.8.0](https://github.com/robotcodedev/robotcode/compare/v1.7.0..v1.8.0) - 2025-08-15

### <!-- 0 -->Features

#### Website

- Integrate lite-youtube-embed and update search provider to Algolia ([aa02835](https://github.com/robotcodedev/robotcode/commit/aa02835d007b2041b4e8572fb1340608520524d5))


### <!-- 1 -->Bug Fixes

#### VS Code

- Improve handling of active environment path changes in PythonManager ([79e410e](https://github.com/robotcodedev/robotcode/commit/79e410ee275c1ce701ca438cef99d4c11be312a3))


### <!-- 2 -->Documentation

- Redesign landing page a bit ([b9dcf16](https://github.com/robotcodedev/robotcode/commit/b9dcf1641d485f9ce51a1d535393c7c926be4995))
- Add commit message standard to guidelines ([2db7f61](https://github.com/robotcodedev/robotcode/commit/2db7f61e12c280663fe9fc5d4f1adf6b286e0ff6))
- Add CLAUDE.md for project guidance and development instructions ([53bcc04](https://github.com/robotcodedev/robotcode/commit/53bcc04bfb636b53a21b8e9e9a57753d1fbe8e81))
- Add project language requirement to ensure consistency in code and documentation ([a6baec4](https://github.com/robotcodedev/robotcode/commit/a6baec46e0a9405296b869dac7368f1cada6211a))
- Enhance guidance on modular resource file structure and performance considerations ([7800f67](https://github.com/robotcodedev/robotcode/commit/7800f673333a8bad7d405201f8be0bb0a4925b93))
- Update requirements for Python, Robot Framework, and VSCode versions ([e91918d](https://github.com/robotcodedev/robotcode/commit/e91918d049e2a7660168d7e6c80d4e802c72a930))
- Add support section to README.md with sponsorship details ([675cc9c](https://github.com/robotcodedev/robotcode/commit/675cc9c927670adec584e23da9aa5e10b1120197))
#### Contributing

- Remove emojis and improve formatting for clarity ([b5bf94d](https://github.com/robotcodedev/robotcode/commit/b5bf94deb145c869aca55ac11c250156293413ff))

#### Copilot-instructions

- Update formatting and punctuation for clarity and consistency ([d39a5fc](https://github.com/robotcodedev/robotcode/commit/d39a5fc3adfffda4d8093e49ff5687cd7cfb1669))

#### Css

- Update brand colors and button styles for Robot Framework theme ([3b84bb4](https://github.com/robotcodedev/robotcode/commit/3b84bb48ad07e637cb49238c7c87fb7e4f9126d9))

#### Tips

- Correct link to "Why is my variable shown as 'not found'" article ([0f45265](https://github.com/robotcodedev/robotcode/commit/0f45265752c1f409f6bbca4a64d3a9c23fc9be39))
- Reorganize tip and tricks files with numbered prefixes and finish why_variable_not_found article ([4a9156c](https://github.com/robotcodedev/robotcode/commit/4a9156cc6bdb9cd4a4ccd2400435e70b1d24c0ef))


## [1.7.0](https://github.com/robotcodedev/robotcode/compare/v1.6.0..v1.7.0) - 2025-07-31

### <!-- 0 -->Features

#### Website

- Add generated llms.txt and llms-full.txt to website ([1f23559](https://github.com/robotcodedev/robotcode/commit/1f23559ff9f26cb2dd9977c001b883493f1f32b4))


### <!-- 1 -->Bug Fixes

#### Diagnostics

- Correct overriding of imported variables in suite variables ([afed6db](https://github.com/robotcodedev/robotcode/commit/afed6db7cf9d5293b62a01eaaeba621517894ebd))


### <!-- 4 -->Refactor

#### Jsonrpc

- Fix some spellings and split up some methods ([3c71ce6](https://github.com/robotcodedev/robotcode/commit/3c71ce64f8a797a4f0db925c2379800a3e48a987))


## [1.6.0](https://github.com/robotcodedev/robotcode/compare/v1.5.0..v1.6.0) - 2025-07-30

### <!-- 0 -->Features

#### Debugger

- Better synchronization between test view and execution in vscode, part 1 ([63c895f](https://github.com/robotcodedev/robotcode/commit/63c895f8d78ba0db64c32c4100ab09bf42941232))

#### RobotCode

- Remove robotframework-tidy from optional-dependencies ([205cfd1](https://github.com/robotcodedev/robotcode/commit/205cfd1a93aae3bfc4e062d1d16b0dd3ad2e4f98))

#### Debug

- Better synchronization between test view and execution in intellij-client, part 2 ([4ce87a2](https://github.com/robotcodedev/robotcode/commit/4ce87a2a86c72c944fab5de1288d08ecc33928e7))


### <!-- 1 -->Bug Fixes

#### Core

- Remove unnecessary socket option for address reuse in find_free_port ([1ee754a](https://github.com/robotcodedev/robotcode/commit/1ee754abc7b27a8d2d70e15f39dad8ec0febc4da))

#### Debugger

- Enhance error handling in DAPClient and simplify port allocation for new testrun sessions ([43f242d](https://github.com/robotcodedev/robotcode/commit/43f242d61dc0e249e1912ac0d7be8df63478d802))

  - every new test run gets it's own tcp port

- Only sync when not in CallKeyword state ([709798a](https://github.com/robotcodedev/robotcode/commit/709798ac5cfbdf84ede7282d396bcae03a7e33f7))


### <!-- 2 -->Documentation

- Remove robotframework-tidy from docs ([c259a0f](https://github.com/robotcodedev/robotcode/commit/c259a0f42819e25603ff333afdf6fc9c00b6b279))

### <!-- 4 -->Refactor

#### Debugger

- Split get_variables method and splitup version specific behavior for exception handling ([c828202](https://github.com/robotcodedev/robotcode/commit/c828202021d8b0eb0e4862fec0e96713977cfe62))
- Break down complex evaluate() method ([4c6b9af](https://github.com/robotcodedev/robotcode/commit/4c6b9afc988a0b4838e16bd9f57b4d57db278721))
- Optimize cache management and improve regex matching performance ([2edfeea](https://github.com/robotcodedev/robotcode/commit/2edfeea3d884b486b19d3c6ab4b6e76e03572b57))
- Enhance type safety by introducing protocols and type definitions for log messages and attributes ([a65b9b9](https://github.com/robotcodedev/robotcode/commit/a65b9b95cf66d3b513da2c50d1409a56887c9963))
- Replace magic numbers with named constants for better readability ([65b0912](https://github.com/robotcodedev/robotcode/commit/65b091218e2ed5552e6d2a84ab61600ecbdc75a3))
- Replace instance method calls with property access for consistency ([8ea82e4](https://github.com/robotcodedev/robotcode/commit/8ea82e45f4d343431aa42dfd525ed5ccb09d4df7))

#### Language Server

- Improve performance and memory consumption for semantic tokens ([e8297ff](https://github.com/robotcodedev/robotcode/commit/e8297ffc2f093cbab7eeff0bbecc7fba3dd5f330))
- Remove unused semantic token types and update regression tests ([6b262b5](https://github.com/robotcodedev/robotcode/commit/6b262b54d3aa53e55f4661b289f7959baf1f260a))
- Remove unused methods to simplify code ([96ba516](https://github.com/robotcodedev/robotcode/commit/96ba5162238fe04ca9b2473dcc512b94efc8cf7f))
- Optimize memory consumption and perfomance in semantic token highlighter ([7e5e8e3](https://github.com/robotcodedev/robotcode/commit/7e5e8e3b9ebc0a3a1ce0a0dccee4cdf160d7bdb5))
- Remove some unneeded casts ([c82a604](https://github.com/robotcodedev/robotcode/commit/c82a6040ea9b6d786e0af9cf5078780e2aaf7437))

#### Instructions

- Clarify implementation guidelines and communication flow ([b37be1c](https://github.com/robotcodedev/robotcode/commit/b37be1c683467ba4f3557127cb6337d5baad19c3))


## [1.5.0](https://github.com/robotcodedev/robotcode/compare/v1.4.0..v1.5.0) - 2025-07-07

### <!-- 0 -->Features

#### CLI

- Add new command line switch `--log-config` to specify a python json log configuration ([31a11f2](https://github.com/robotcodedev/robotcode/commit/31a11f27b96fba6c879218c9b13cdea5f8bb89c3))

#### Jsonrpcl

- Simplify error message formatting in JsonRPCProtocol for better readability in clients ([75614b0](https://github.com/robotcodedev/robotcode/commit/75614b05820f57c98c416949abced03970e0b429))


### <!-- 4 -->Refactor

#### Language Server

- Remove some unused code ([fa429a5](https://github.com/robotcodedev/robotcode/commit/fa429a502e1901cfc0d4126c4047994a5fd5ee39))
- Simplify keyword renaming ([3836362](https://github.com/robotcodedev/robotcode/commit/3836362073599bcc32d9cb38425645d34d681f91))
- Simplify variable renaming ([779fd70](https://github.com/robotcodedev/robotcode/commit/779fd703339ce81124f03f08b73e2639d0729212))


## [1.4.0](https://github.com/robotcodedev/robotcode/compare/v1.3.0..v1.4.0) - 2025-06-30

### <!-- 0 -->Features

#### Language Server

- Improve and unify Robocop 6 configuration loading ([b3c5dd3](https://github.com/robotcodedev/robotcode/commit/b3c5dd3c50308116fc1e1de7adc156a6086cd8fd))

  - Enhance configuration loading process
  - Add notifications for faulty configurations



### <!-- 1 -->Bug Fixes

#### Language Server

- Remove timing messages from diagnostics in log ([c908485](https://github.com/robotcodedev/robotcode/commit/c90848514f713805fa330ccfc4344cc8775d0118))

  - if you want to see it again, then you have to enable the log output for the language server



### <!-- 2 -->Documentation

- Update Python and Robot Framework version requirements and deprecation notice ([6396b7e](https://github.com/robotcodedev/robotcode/commit/6396b7ef76fd8d41c3d79afc0bab871342eb8622))

### <!-- 4 -->Refactor

- Simpify some logging code ([5ea1ca1](https://github.com/robotcodedev/robotcode/commit/5ea1ca1c77269df8ebcc70e9a86e77a89d9249a6))
- Switch lint environment to python 3.10 and corrected all linting errors and warnings ([19a2632](https://github.com/robotcodedev/robotcode/commit/19a26325454ba1b5e53b8548a16c0a3fbe8d5422))

## [1.3.0](https://github.com/robotcodedev/robotcode/compare/v1.2.0..v1.3.0) - 2025-06-16

### <!-- 0 -->Features

- Basic support for Robot Framework 7.3 ([e6ffef7](https://github.com/robotcodedev/robotcode/commit/e6ffef7ded23ccab2bf3359891e5698f65a99ec4))
- Show editor hint for Python/Robot Framework issues instead of throwing error ([4c2a43b](https://github.com/robotcodedev/robotcode/commit/4c2a43b8fd2ece7f905fc10695f2d5b9487dc52a))

  When opening a Robot Framework file, issues related to the Python environment or Robot Framework version are now shown as an editor hint at the top of the file tab, instead of raising an exception.

#### Debugger

- Update delayed logging handling for Robot Framework 7.3 compatibility ([0b51afc](https://github.com/robotcodedev/robotcode/commit/0b51afce6acace2de358120dae365f190719cd05))

#### Language Server

- Show variable type in hover for RF 7.3 ([10d981f](https://github.com/robotcodedev/robotcode/commit/10d981f657ba34db1449984fe4a28623632c5b64))
- Implemented robocop 6.0 formatting and deprecate old robotidy ([310bc54](https://github.com/robotcodedev/robotcode/commit/310bc544be8306fb85a329698763b562cd9d85aa))
- Better support for indexed assignments ([6fad9b1](https://github.com/robotcodedev/robotcode/commit/6fad9b161b85b2412b6a9d5169e69b4ce37c43c3))

#### PyCharm

- Reimplement and simplified parsing and syntax highlightning ([2dcdf7c](https://github.com/robotcodedev/robotcode/commit/2dcdf7ce846e8483fb427cdc7945a084fe4c3232))

#### Robot

- Unify variable handling and prepare for RF 7.3 type parsing ([73cda66](https://github.com/robotcodedev/robotcode/commit/73cda6698959fd3cbdce0901b87a40701cbe4966))

  - Added support for parse_type parameter in Robot Framework 7.3+
  - Unified variable processing across different RF versions


#### VS Code

- Deprecate some robocop settings ([1b23965](https://github.com/robotcodedev/robotcode/commit/1b23965aec6dc00618bfe5c4927c9889f44cc4d1))
- Add language model tool to get the library and resource imports from a robot file ([e5631f0](https://github.com/robotcodedev/robotcode/commit/e5631f042e42810b35d8694649cb76819b7b5866))
- Add language model tools for retrieving library documentation and environment details ([a311e99](https://github.com/robotcodedev/robotcode/commit/a311e996cf95b2afaacc4b4402a4e2749b8d46bc))
- Add deprecation messages for robotframework-tidy in configuration ([37c5371](https://github.com/robotcodedev/robotcode/commit/37c5371919d10a7ea1f46c91f1f7707b63fa96ce))

#### Analyzer

- Support for converting resolvable variables with types ([17123a0](https://github.com/robotcodedev/robotcode/commit/17123a046015e57fc64aa73f1227309b78bed4a2))
- Support for types in embedded arguments ([35526a0](https://github.com/robotcodedev/robotcode/commit/35526a05fbfdccc2a250f86a8fe3d51bf510607c))
- Improve 'keyword not found' messages for old `FOR:` syntax ([94cdc54](https://github.com/robotcodedev/robotcode/commit/94cdc54dd017e6e3892ead8a4cd9d8068b6b88ca))


### <!-- 1 -->Bug Fixes

- Corrected detection of robocop ([f06bcbc](https://github.com/robotcodedev/robotcode/commit/f06bcbc1c2514326567399f8e5179da6ff5f9ed7))
#### CLI

- Set case_sensitive default to False in EnumChoice ([3fd27d4](https://github.com/robotcodedev/robotcode/commit/3fd27d47cec9f515bc618b330b2dccf1acc6255d))
- Corrected monkey patching for click>=8.2.0 ([425e64d](https://github.com/robotcodedev/robotcode/commit/425e64ddf8c6a9a54ec6fe3d801253c2e3a2156a))

#### Debugger

- Improve termination handling ([a890264](https://github.com/robotcodedev/robotcode/commit/a890264547341c190eaef5e0240f0cc81deb3c70))

#### Language Server

- Implemented support for robocop >= 6 checks ([8dc2f3c](https://github.com/robotcodedev/robotcode/commit/8dc2f3ce94bf6c6a771b6ffcc6a969ae617397e6))
- Disable on-demand startup for the documentation server to ensure it launches on initialization ([81d63fa](https://github.com/robotcodedev/robotcode/commit/81d63faa5f0cfbcf95e293c53daeb80840117438))

#### TextMate

- Corrected highlightning of comments in variable section ([5204afb](https://github.com/robotcodedev/robotcode/commit/5204afbfdd7f745c3e00ebc8d59fa3ad992ec0a8))
- Enhance variable assignment handling ([7333eb9](https://github.com/robotcodedev/robotcode/commit/7333eb9b2f46e2af25583af2d5346b4b92dd1137))

#### Formatting

- Improve message clarity for robocop formatting ([f71d15d](https://github.com/robotcodedev/robotcode/commit/f71d15df40f8bfd1f9f325d35e1ba73bcf16c9aa))

#### Imports

- Corrected caching of already loaded resources ([4606c4f](https://github.com/robotcodedev/robotcode/commit/4606c4ff12906b54edfeb1e29927f61b2130332c))

#### Listener

- Add 'robocop.toml' to monitored project files to allow detection of changes in robocop configuration ([987ea42](https://github.com/robotcodedev/robotcode/commit/987ea421f22b133851a462b921b7c3e1e5802a4a))

#### Net

- Move SO_REUSEADDR socket option setting to the correct location to speeding up port discovery and preventing bind failures. ([b54cc93](https://github.com/robotcodedev/robotcode/commit/b54cc9300abb4c7060bfa94cb2e1bfa272936eda))


### <!-- 2 -->Documentation

#### Contributing

- Enhance development setup and workflow instructions ([b23331b](https://github.com/robotcodedev/robotcode/commit/b23331b8622ddd97c2030de96212323f5e7d4171))

  Updated the contributing guide to include detailed development environment setup options, IDE configuration, and a comprehensive development workflow. Improved clarity and added troubleshooting tips for common issues.



### <!-- 4 -->Refactor

#### PyCharm

- Some code cleanup ([479a9c3](https://github.com/robotcodedev/robotcode/commit/479a9c3e6b1bc117e5c1222953b755a198cbc8c2))

#### VS Code

- Some refactorings and code cleanup ([d8eac38](https://github.com/robotcodedev/robotcode/commit/d8eac3808e23320fcb7efa92e85c574988d1a7ef))

#### Analyzer

- Some renamings ([5f1f5c3](https://github.com/robotcodedev/robotcode/commit/5f1f5c37f62ae6cb32bf7a1db5c6ddbb592d8337))


## [1.2.0](https://github.com/robotcodedev/robotcode/compare/v1.1.0..v1.2.0) - 2025-05-07

### <!-- 0 -->Features

#### Language Server

- Refactor and optimize Robot Framework textmate syntax highlighting rules ([5b7c4b1](https://github.com/robotcodedev/robotcode/commit/5b7c4b13469072e3c39c8c112118149ac4b5b1cd))

  this also fixes the loading of robotframework core test files in PyCharm


#### PyCharm

- Refactored textmate highlightning to use the new intellij textmate infrastructure ([74644f0](https://github.com/robotcodedev/robotcode/commit/74644f055e6c1dea38e37446ef430387c667b80c))


### <!-- 1 -->Bug Fixes

- Update IntelliJ platform version and plugin dependencies ([e94c96b](https://github.com/robotcodedev/robotcode/commit/e94c96b99646e602820663f1210d0df962251bf1))

  because of some new features regarding syntax highlightning and text mate the minimal supported version is PyCharm 2025.1

#### PyCharm

- Reenable semantic highlightning, because something has changed in the new LSP4IJ API ([5cdf3c3](https://github.com/robotcodedev/robotcode/commit/5cdf3c3ab87857db294e63bcdc0798f1cfd5eacd))
- Corrected handling of short by-longname argument ([b5fa232](https://github.com/robotcodedev/robotcode/commit/b5fa232f4c0fd3032b863363c141d8ffeff6c8c7))


## [1.1.0](https://github.com/robotcodedev/robotcode/compare/v1.0.3..v1.1.0) - 2025-04-29

### <!-- 0 -->Features

#### Analyze

- Exit code mask configuration for code analysis ([4b677ad](https://github.com/robotcodedev/robotcode/commit/4b677add254f88519d950e54ac5ef1f4e499d0e6))

  Configure which message types should **not** influence the exit code of `robotcode analyze code`, allowing granular control over CI/CD pipeline behavior or pre-commit hooks.

  **Configuration File (`robot.toml`)**

  ```toml
  [tool.robotcode-analyze.code]
  exit-code-mask = ["error", "warn"]
  ```

  **Command Line Options**

  ```
  robotcode analyze code --exit-code-mask error,warn    # or -xm
  robotcode analyze code --extend-exit-code-mask info   # or -xe
  ```

  - `-xm` (or `--exit-code-mask`) overwrites the configuration in `robot.toml`
  - `-xe` (or `--extend-exit-code-mask`) extends the configuration in `robot.toml`
  - Both options can be specified multiple times or with comma-separated values:

      ```
      robotcode analyze code -xm error -xm warn  # multiple options
      robotcode analyze code -xm error,warn      # comma-separated
      ```

  **Behavior**

  - Message types in the mask are ignored when determining exit code
  - Available types: `error`, `warn`/`warning`, `info`/`information`, `hint`
  - Special value `all` ignores all message types (always exit code 0)
  - Without configuration, all message types affect the exit code

  **Example**

  ```toml
  # In robot.toml - Ignore warnings but let errors affect exit code
  [tool.robotcode-analyze.code]
  exit-code-mask = ["warn"]
  ```

  ```bash
  # Using short options
  robotcode analyze code -xm error,hint  # Overwrites robot.toml config
  robotcode analyze code -xe info -xe hint  # Extends robot.toml config with multiple types
  robotcode analyze code -xm all          # Always exit with code 0
  ```


#### VS Code

- Use short CLI argument versions when calling robotcode ([0987f55](https://github.com/robotcodedev/robotcode/commit/0987f551803f23e2c8342638d2b3bb1e23cc99da))
- Add configuration for output file display options ([738d7a6](https://github.com/robotcodedev/robotcode/commit/738d7a6129f8e459c0af1961ebedfe320d2a4b9d))

  Add "robotcode.run.openOutputTarget" setting to control how Robot Framework output files are displayed:
  - simpleBrowser: in VSCode's built-in browser
  - externalHttp: in default browser via HTTP protocol
  - externalFile: in default browser via file system

  The externalFile options may not run in remote development environments.



### <!-- 1 -->Bug Fixes

#### Analyze

- Allow `all` also in `robot.toml` configuration for `exit-code-mask` ([a496714](https://github.com/robotcodedev/robotcode/commit/a496714b88d397b46f4b4192c82336711fccac5a))

#### Language Server

- Corrected highlightning of embedded arguments if there is a namespace given before the keyword ([0ce5446](https://github.com/robotcodedev/robotcode/commit/0ce5446154b34655bd5db4c6cba91a9a82266440))


### <!-- 2 -->Documentation

- Added pycharm link on the robotcode.io homepage ([7686a21](https://github.com/robotcodedev/robotcode/commit/7686a21c76681d2a7321a67c1c872b6c77687000))
- Draft article about variables ([161006e](https://github.com/robotcodedev/robotcode/commit/161006e6a730f52501bdff7dcd1cba9e85300fcd))

### <!-- 4 -->Refactor

#### Analyze

- Move code analysing to it's own module ([0123a50](https://github.com/robotcodedev/robotcode/commit/0123a507a3b23265676aa8d0c68af322e01f513c))


## [1.0.3](https://github.com/robotcodedev/robotcode/compare/v1.0.2..v1.0.3) - 2025-03-14

### <!-- 1 -->Bug Fixes

#### Debugger

- Ensure proper evaluation of variable expressions ([6b90851](https://github.com/robotcodedev/robotcode/commit/6b90851271beeb0cfa1a3f6feb6ce2a82a3b0361))

#### VS Code

- Correct handling of comments in keyword calls with return ([c3c32bf](https://github.com/robotcodedev/robotcode/commit/c3c32bf36d3a75aabf22e01de9a35130931bbee9))

#### Analyzer

- Corrected handling of VAR statement for variable with equal sign ([227d173](https://github.com/robotcodedev/robotcode/commit/227d1738b05cbd07cc5ee88cd234fc477b082e18))


### <!-- 4 -->Refactor

#### Debugger

- Some code simplifications ([b14877c](https://github.com/robotcodedev/robotcode/commit/b14877c41091ba777fdf8a4410ff4fc9630c383d))


## [1.0.2](https://github.com/robotcodedev/robotcode/compare/v1.0.1..v1.0.2) - 2025-03-07

### <!-- 1 -->Bug Fixes

#### Debugger

- Remove unnecessary environment variables for debugpy sessions ([08cba92](https://github.com/robotcodedev/robotcode/commit/08cba92302bf79be1a71c370aaf573f23be90b33))


## [1.0.1](https://github.com/robotcodedev/robotcode/compare/v1.0.0..v1.0.1) - 2025-03-06

### <!-- 1 -->Bug Fixes

#### Language Server

- Improve range calculation for document symbols and add handling for negative ranges ([1db6978](https://github.com/robotcodedev/robotcode/commit/1db69786b3a926abd03a669b84058c41105ce1fb))


### <!-- 2 -->Documentation

- Add a separate document about support and contribution ([4da4a51](https://github.com/robotcodedev/robotcode/commit/4da4a51189f7869644932ac4afdb7ce7ec3e430f))
- Fixes some typos ([d149ae8](https://github.com/robotcodedev/robotcode/commit/d149ae830cea98a2556b11575bb30a52b006dcf1))

## [1.0.0](https://github.com/robotcodedev/robotcode/compare/v0.109.6..v1.0.0) - 2025-03-05

### <!-- 0 -->Features

#### PyCharm

- Support for more semantic highlight tokens ([e48943b](https://github.com/robotcodedev/robotcode/commit/e48943b5fff6b296a4ddb510be5eb1cf144c2a4e))


### <!-- 1 -->Bug Fixes

#### Tmlang

- Recognize 2 or spaces between arguments to better work in intellj platform ([6198707](https://github.com/robotcodedev/robotcode/commit/6198707c7f22a9744dcad7a4e0d9bc6f64f46e4c))


### <!-- 2 -->Documentation

- Update get started/configuration ([f8060e5](https://github.com/robotcodedev/robotcode/commit/f8060e53ba95007fea2a62c137dfc4c271086cab))

## [0.109.6](https://github.com/robotcodedev/robotcode/compare/v0.109.5..v0.109.6) - 2025-02-28

### <!-- 1 -->Bug Fixes

#### VS Code

- Downgrade to typescript 5.7.3 because eslint dont support newer ones ([f1ea63e](https://github.com/robotcodedev/robotcode/commit/f1ea63eb08039c45d663e957953dd43b512ccc27))


## [0.109.5](https://github.com/robotcodedev/robotcode/compare/v0.109.4..v0.109.5) - 2025-02-28

### <!-- 1 -->Bug Fixes

#### Language Server

- Corrected document_symbols when matching keyword or test case declaration when no name is given ([1525db2](https://github.com/robotcodedev/robotcode/commit/1525db2985dfe7ecd488c2e838fd39f0355fbd5a))


## [0.109.4](https://github.com/robotcodedev/robotcode/compare/v0.109.3..v0.109.4) - 2025-02-28

### <!-- 1 -->Bug Fixes

#### Debugger

- Don't connect to non config debugpy sessions, use our own ([1a1d515](https://github.com/robotcodedev/robotcode/commit/1a1d5150011b540477f76dc8d21b6dddeb905d84))


## [0.109.3](https://github.com/robotcodedev/robotcode/compare/v0.109.2..v0.109.3) - 2025-02-26

### <!-- 2 -->Documentation

- Rewrite index of tips&tricks ([579e728](https://github.com/robotcodedev/robotcode/commit/579e728af6a0601c186b0a896ad884c7d2ff0a7f))
- Update article about avoiding global resource files ([87bd175](https://github.com/robotcodedev/robotcode/commit/87bd1759532b748462745057c7cc1109571a4dd3))
- Add examples of good project structure and a small migration guide to avoiding global resources document ([dfd495c](https://github.com/robotcodedev/robotcode/commit/dfd495caa595da7aa1fc33c5b3255bd4e222d35d))
- Update the articel about avoiding global resource files ([bd396fb](https://github.com/robotcodedev/robotcode/commit/bd396fb550897dc0933b31544ecac847358b9739))
- Update the articel about avoiding global resource files ([57f9209](https://github.com/robotcodedev/robotcode/commit/57f9209452ea03cc0f4dc2378ca3696086497ef4))
- Correct links ([22af24d](https://github.com/robotcodedev/robotcode/commit/22af24d116ce0165bff67e1a7a51ba6527cbdefa))
- Added an article about avoiding a global resource file ([18327b6](https://github.com/robotcodedev/robotcode/commit/18327b6b320201bf8e5de4a8b4939a085ed47ae0))

## [0.109.2](https://github.com/robotcodedev/robotcode/compare/v0.109.1..v0.109.2) - 2025-02-23

### <!-- 1 -->Bug Fixes

#### PyCharm

- Remove trailing slash from URIs ([62fde84](https://github.com/robotcodedev/robotcode/commit/62fde847aff911f0e6e7b521c1e564f8a0fa2455))


### <!-- 4 -->Refactor

#### RobotCode

- Remove `clean` and `new` command because we implement it later ([6da369a](https://github.com/robotcodedev/robotcode/commit/6da369ae69c1f3f6b1f97c9952d3035dc713076f))

  create enhancement request #393


#### Runner

- Remove underlining from statistics output ([6fdd81d](https://github.com/robotcodedev/robotcode/commit/6fdd81d03d0d9ba826f331f32c739662d947609f))


## [0.109.1](https://github.com/robotcodedev/robotcode/compare/v0.109.0..v0.109.1) - 2025-02-10

### <!-- 1 -->Bug Fixes

#### VS Code

- Correct appending profile options to robotcode commands ([8746faa](https://github.com/robotcodedev/robotcode/commit/8746faae84ab2bc2a0e0a972fcd7f84e844f1bba))


## [0.109.0](https://github.com/robotcodedev/robotcode/compare/v0.108.1..v0.109.0) - 2025-02-10

### <!-- 0 -->Features

#### RobotCode

- Automatically create `.gitignore` in `.robotcode_cache` ([79d14e4](https://github.com/robotcodedev/robotcode/commit/79d14e4e0173527eabbd4cd119f36feacc7c18d5))

  You no longer need to manually add `.robotcode_cache` to your `.gitignore` file, as it is now automatically ignored.
  If you already have an existing `.robotcode_cache` folder, simply run the command `RobotCode: Clear Cache and Restart Language Servers`.
  For IntelliJ-based platforms, you can find this command in the **RobotCode** menu under the **Tools** main menu.


#### VS Code

- Use shell integration instead of full python command line to start repl if shell integration is enabled ([50426a2](https://github.com/robotcodedev/robotcode/commit/50426a26c700702d1eeeb85ca8e642f33a2b413c))
- Add shell integration to run RobotCode in a VSCode terminal without requiring Python package installation ([febf5d8](https://github.com/robotcodedev/robotcode/commit/febf5d898c744df29f388173a06f1197e333efab))


### <!-- 1 -->Bug Fixes

#### Debugger

- If there is already a debugpy adapter endpoint defined we don't need explicitly attach the python debugger ([7f3010a](https://github.com/robotcodedev/robotcode/commit/7f3010a92b8737f0f9608bedbeb166a95c96b46b))
- Use 32-bit thread IDs for improved compatibility with some LSP clients ([5055763](https://github.com/robotcodedev/robotcode/commit/50557638c258b7496cbb4097b358ed1fe0075523))

#### PyCharm

- Stabilize test discovery at project startup ([7aeb379](https://github.com/robotcodedev/robotcode/commit/7aeb37974da360630d20416475ba407d39163cc5))

#### Vscode,intellij

- Escape glob patterns in --suite and --parse-include arguments for discover and executing tests ([4007481](https://github.com/robotcodedev/robotcode/commit/40074816b4a87cb1fb1c4f937d215457fb2e905f))


## [0.108.1](https://github.com/robotcodedev/robotcode/compare/v0.108.0..v0.108.1) - 2025-02-03

### <!-- 1 -->Bug Fixes

#### Language Server

- Only send complete documentation when resolving completion items for typed dicts and enums ([498af3c](https://github.com/robotcodedev/robotcode/commit/498af3c9845c181c0541bd21ae7b19bf6f137db4))
- Cache to_markdown methods ([39e509e](https://github.com/robotcodedev/robotcode/commit/39e509eb03ba01ae2b1fbce021640c2b76f8f1e6))

#### PyCharm

- Make comparing testitem uri's platform independend ([f597624](https://github.com/robotcodedev/robotcode/commit/f597624c6063410ba7f5afcc09a77c770636fd57))


## [0.108.0](https://github.com/robotcodedev/robotcode/compare/v0.107.0..v0.108.0) - 2025-01-22

### <!-- 0 -->Features

#### PyCharm

- Add clear cache and restart actions for language server ([2f04e9a](https://github.com/robotcodedev/robotcode/commit/2f04e9aa3116c5bdb7ac3826c6433b04c8c5077b))


### <!-- 1 -->Bug Fixes

#### Debugger

- Corrected evaluating/executing keywords for RF 7.2 ([df92ad4](https://github.com/robotcodedev/robotcode/commit/df92ad4e6910de9556e6c20148489ab42ed06a93))


### <!-- 2 -->Documentation

- Change svgs in README to pngs ([434307c](https://github.com/robotcodedev/robotcode/commit/434307c2e042bed06a159983e5052e0961d05f86))
- Redesign the README and some docs and added `powered by IntelliJ` to README and docs ([db5ec53](https://github.com/robotcodedev/robotcode/commit/db5ec5378dbeee82c24a62bf4a22c32e8bc89e36))

## [0.107.0](https://github.com/robotcodedev/robotcode/compare/v0.106.1..v0.107.0) - 2025-01-21

### <!-- 0 -->Features

#### Language Server

- Support for workspace symbols ([66cb701](https://github.com/robotcodedev/robotcode/commit/66cb701620322bd248db053dcb3d0f598c76a93b))
- Support for workspace symbols ([a90ce60](https://github.com/robotcodedev/robotcode/commit/a90ce60250b9dc82c8a78bc910878171617c6a45))

#### PyCharm

- Support for highlight for python expressions ([a2c2760](https://github.com/robotcodedev/robotcode/commit/a2c276043f26303b4856dc13aed88cd2eea5432f))
- Implemented support for 4 spaces tab ([de83635](https://github.com/robotcodedev/robotcode/commit/de836356cd991cf09d315aaacad2ed1e94c433b9))

  - this is enabled by default for robot files

- Dynamic update of test run buttons on file and configuration changes ([da9687c](https://github.com/robotcodedev/robotcode/commit/da9687c0cd75270d6f7f397f776f230b3469a684))


### <!-- 1 -->Bug Fixes

#### PyCharm

- Stabilized getting the correct python sdk for a project ([f8622ef](https://github.com/robotcodedev/robotcode/commit/f8622ef6eacfb6dc484044b465f281cba02ee0c3))


### <!-- 4 -->Refactor

#### Robot

- Remove unused digest fields from KeywordDoc and LibraryDoc ([e550fb0](https://github.com/robotcodedev/robotcode/commit/e550fb0be816fed4a1d66d17ae3f02b059095713))


## [0.106.1](https://github.com/robotcodedev/robotcode/compare/v0.106.0..v0.106.1) - 2025-01-16

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct highlightning of embedded keywords arguments ([6db88f2](https://github.com/robotcodedev/robotcode/commit/6db88f2b2cc8ae812701757a62537344051a38a5))

#### VS Code

- Suppress UI error notifications if configuration has changed ([2f1265a](https://github.com/robotcodedev/robotcode/commit/2f1265a41af079f0ce11ce161703a35ed0d6d37c))


## [0.106.0](https://github.com/robotcodedev/robotcode/compare/v0.105.0..v0.106.0) - 2025-01-15

### <!-- 0 -->Features

- Ready for RF 7.2 ([45a0131](https://github.com/robotcodedev/robotcode/commit/45a01312af5abfff33fa15023dce5364ecf5ee7c))
#### Debugger

- Display a virtual variable in the local scope with details about the current exception when an exception breakpoint is triggered ([4690071](https://github.com/robotcodedev/robotcode/commit/46900713196cb9d52afab2b5692cf9594e374c79))

#### PyCharm

- Support for pause and exception break points in debugger ([446a246](https://github.com/robotcodedev/robotcode/commit/446a2460b240b3b0636c9fbb4ebeb60fbf9320ca))
- Execute tests from project tree view on files and folders ([b155bd1](https://github.com/robotcodedev/robotcode/commit/b155bd1d6e4fd5a963625585cf1b0c101600cb00))
- Implemented show test status on gutter icon ([678e5e8](https://github.com/robotcodedev/robotcode/commit/678e5e8d8d2e81dd00a4cbddc0a42ca9fa4de269))
- Implemented robot framework debugger ([121b26e](https://github.com/robotcodedev/robotcode/commit/121b26eee9ef580816bdaed09bec17c304fe8c38))


### <!-- 1 -->Bug Fixes

#### VS Code

- Suppress UI error notifications for language client errors; log them in the output channel instead ([420a8a7](https://github.com/robotcodedev/robotcode/commit/420a8a7c234c70414a9027a9597dbc80309327f1))


## [0.105.0](https://github.com/robotcodedev/robotcode/compare/v0.104.0..v0.105.0) - 2025-01-06

### <!-- 0 -->Features

#### Language Server

- Enhanced hover representation of variables ([039682d](https://github.com/robotcodedev/robotcode/commit/039682dbdd19a6e1dc972f642dbfd5f1787b4dcd))
- Correct highlightning to better highlight python expresseions, escape sequences, environment variable default value and embedded argument regexes ([5dba571](https://github.com/robotcodedev/robotcode/commit/5dba5713f746cb9fb1b36433be982493bb3905d2))

#### PyCharm

- Implemented support for highlightning embedded arguments, escape sequences, python expressions and so on ([c5d6cf3](https://github.com/robotcodedev/robotcode/commit/c5d6cf3722c22929799b154204711c697928da7e))
- Finalize syntax coloring and sematic highlightning part 2 ([97081a5](https://github.com/robotcodedev/robotcode/commit/97081a5f13a7f58d6825853330c8806506ad6fde))
- Finalize syntax coloring and sematic highlightning ([faa905d](https://github.com/robotcodedev/robotcode/commit/faa905d048d4af076695b619d91ee97371cfd0fd))
- Implemented brace matcher for variables ([9ee1f22](https://github.com/robotcodedev/robotcode/commit/9ee1f22c2f077a1c92ac9f5f6dc37542fb24e79c))
- Added initial Robot Framework file templates and better syntax highlighting support based on a customized TextMate lexer/parser ([ef67d2c](https://github.com/robotcodedev/robotcode/commit/ef67d2c661c6ae8c8c734561b54f63d82f9b4e3c))


### <!-- 2 -->Documentation

- Update readme's ([f4f576f](https://github.com/robotcodedev/robotcode/commit/f4f576f3222ac3cf08904a336615edf45c57f922))

## [0.104.0](https://github.com/robotcodedev/robotcode/compare/v0.103.0..v0.104.0) - 2024-12-30

### <!-- 0 -->Features

#### PyCharm

- Implemented correct coloring of most elements and started implementing some settings dialogs for colors, codestyle and project settings ([dcb20f7](https://github.com/robotcodedev/robotcode/commit/dcb20f73d5cdbb2130634e1ca753044ba354230d))
- Added a first version of pycharm/intellij plugin ([e32117e](https://github.com/robotcodedev/robotcode/commit/e32117eaf8d835ab5efa78e9db2021e3dde23f24))


### <!-- 1 -->Bug Fixes

#### Language Server

- Don't break initialization if `initializationOptions` are in wrong format ([7f27b66](https://github.com/robotcodedev/robotcode/commit/7f27b66a489a6cd3017ad0f633f94f319d051fa7))

#### VS Code

- Prevent the creation of multiple output channels for language servers ([56a0174](https://github.com/robotcodedev/robotcode/commit/56a01743c0962e185f08ae45fc28634df3996482))


## [0.103.0](https://github.com/robotcodedev/robotcode/compare/v0.102.0..v0.103.0) - 2024-12-19

### <!-- 0 -->Features

#### Language Server

- Added support for GROUP block in RF 7.2 ([6495d59](https://github.com/robotcodedev/robotcode/commit/6495d59fc89152adec8282bf99cef6f476ee0367))
- Implemented `window/logMessage` to log output directly to the language server protocol client ([98c96f9](https://github.com/robotcodedev/robotcode/commit/98c96f9001a532a6139b0d5758e9886a32ad65a9))

#### Notebook

- Implemented interupt execution and restart kernel ([2f2f629](https://github.com/robotcodedev/robotcode/commit/2f2f629fbccf37b4ed1f4f110953a7b04bf76dc1))


### <!-- 1 -->Bug Fixes

#### Core

- Handle json from_dict correctly for optinal types ([6820cc8](https://github.com/robotcodedev/robotcode/commit/6820cc8c83cd50111a1bcfc3f0241ff503153516))

#### Language Server

- Increase spaces in FOR snippet ([8adad45](https://github.com/robotcodedev/robotcode/commit/8adad455bb95fc4b5a6bd25fdf7e2e7b38c47492))


## [0.102.0](https://github.com/robotcodedev/robotcode/compare/v0.101.0..v0.102.0) - 2024-12-15

### <!-- 0 -->Features

#### Debugger

- Increase the portion of the variable’s value displayed in the debug view ([0b0b80e](https://github.com/robotcodedev/robotcode/commit/0b0b80e3f506ac1a8d560464c08c7c2f3359f1a0))


### <!-- 1 -->Bug Fixes

#### Debugger

- Corrected order of sequences and values in variables view ([b0bf5c7](https://github.com/robotcodedev/robotcode/commit/b0bf5c76560714ceff3f484874efa5b74c3bb651))


## [0.101.0](https://github.com/robotcodedev/robotcode/compare/v0.100.2..v0.101.0) - 2024-12-11

### <!-- 0 -->Features

#### Language Server

- Support for folding WHILE and TRY/EXCEPT/FINALLY statements ([b3c1ce2](https://github.com/robotcodedev/robotcode/commit/b3c1ce2ad8d2f696b33c240672edc3822524403f))

#### VS Code

- Added "File > New File" menu support and context menu option for creating Robot files in the file explorer ([330fc4c](https://github.com/robotcodedev/robotcode/commit/330fc4cf596b9cf60c37aeee102f0fda92873f38))

#### Icons

- Change the color of the file icons back to the official colors ([d6b2ff4](https://github.com/robotcodedev/robotcode/commit/d6b2ff4f19f9eee33c56daad3f2a59b2d2e89d29))

#### Notebook

- Optimize robot notebook file format, remove old html output ([7bc22fb](https://github.com/robotcodedev/robotcode/commit/7bc22fbc8793f375e5f6a532c07f910d90df092a))


### <!-- 1 -->Bug Fixes

#### VS Code

- Fixed highlightning of bold/italic in documentation ([d0e3b2e](https://github.com/robotcodedev/robotcode/commit/d0e3b2edcb7ef05ae99e9053a5acd47a2ce74901))


## [0.100.2](https://github.com/robotcodedev/robotcode/compare/v0.100.1..v0.100.2) - 2024-12-06

### <!-- 1 -->Bug Fixes

#### Plugin

- Corrected context based change current directory ([359589d](https://github.com/robotcodedev/robotcode/commit/359589d5c7a2f1b48bd0677db4e3fde6172aa6b8))


## [0.100.1](https://github.com/robotcodedev/robotcode/compare/v0.100.0..v0.100.1) - 2024-12-06

### <!-- 1 -->Bug Fixes

#### VS Code

- Update title for creating new Robot Framework Notebook ([86c48f8](https://github.com/robotcodedev/robotcode/commit/86c48f8490aabecace6d3cd24faf619d02c1a45e))

#### Jsonrpc2

- Corrected starting server in pipe mode ([e69f686](https://github.com/robotcodedev/robotcode/commit/e69f68664687be3d6af16c4f8a71972a34808c0a))


## [0.100.0](https://github.com/robotcodedev/robotcode/compare/v0.99.0..v0.100.0) - 2024-12-05

### <!-- 0 -->Features

#### VS Code

- Preview of Robot Framework Notebook support for VSCode ([9185ccd](https://github.com/robotcodedev/robotcode/commit/9185ccd84dbb9f2f5cd2aba4212598abd93ef0f1))
- Added some better file icons ([39fad12](https://github.com/robotcodedev/robotcode/commit/39fad12e6cc8d1246dc45c8e843fa1c3b046a491))

#### Analyzer

- Add error codes `VariableNotReplaced` and `EnvironmentVariableNotReplaced` for variables not found/replaced in documentation, tags, and metadata ([c5f766f](https://github.com/robotcodedev/robotcode/commit/c5f766f036e49153f318e91ddefb68c975668669))


### <!-- 1 -->Bug Fixes

#### Analyze

- Corrected statistics about analyzed  files ([18b6cb8](https://github.com/robotcodedev/robotcode/commit/18b6cb878e893b32ce26b16c3de0c6e628367fde))

#### Config

- Corrected handling of relative items in python path and other variables if current folder is different then root folder of the project ([66a94bc](https://github.com/robotcodedev/robotcode/commit/66a94bc993a27d8fe5cec13813e524b1099509c6))

#### VS Code

- Corrected highlightning of bold/italic in documentation tags ([170287d](https://github.com/robotcodedev/robotcode/commit/170287db04ec811e39b7ec5e7bd853ae9d98ec7c))

#### Analyzer

- Correct handling of variables in embedded args in keyword calls ([2c8ed56](https://github.com/robotcodedev/robotcode/commit/2c8ed5662be1e8621d7d9c742275ccaf1809d06c))


### <!-- 2 -->Documentation

- Update some docs ([639314b](https://github.com/robotcodedev/robotcode/commit/639314b9e526e7e3d5820631db0c7c777ac9d648))

## [0.99.0](https://github.com/robotcodedev/robotcode/compare/v0.98.0..v0.99.0) - 2024-11-20

### <!-- 0 -->Features

#### Analyze

- `analyze code` now return a flag that indicates if errors/warnings/etc. occurs ([5125f7d](https://github.com/robotcodedev/robotcode/commit/5125f7dca21daf18f21708ab0676d8707fbb2827))

  - `0`: **SUCCESS** - No issues detected.
          - `1`: **ERRORS** - Critical issues found.
          - `2`: **WARNINGS** - Non-critical issues detected.
          - `4`: **INFORMATIONS** - General information messages.
          - `8`: **HINTS** - Suggestions or improvements.

  A return code 1 means error and 3 means there are errors and warning and so on.


#### CLI

- Add an astric (*) for options that can be used multiple times ([5bf5493](https://github.com/robotcodedev/robotcode/commit/5bf54936c2bfa12d92171d2fd9f9b55c86f9115f))


### <!-- 1 -->Bug Fixes

#### Analyzer

- Better recognition of circular imports ([a36dd41](https://github.com/robotcodedev/robotcode/commit/a36dd414c88f418e486979ae9fe988cafb97143c))


## [0.98.0](https://github.com/robotcodedev/robotcode/compare/v0.97.0..v0.98.0) - 2024-11-19

### <!-- 0 -->Features

#### REPL

- Rework repl a little bit and add some new command line options ([610b1f3](https://github.com/robotcodedev/robotcode/commit/610b1f3482ed37b87e2df8058ea4ab1a05f96cd1))

  see documentation


#### Analyzer

- Added command line options for diagnostics modifiers to `code` command ([0a29800](https://github.com/robotcodedev/robotcode/commit/0a29800b53ca53fb49999053be3cb58b8a1df629))


### <!-- 1 -->Bug Fixes

#### Analyze

- Corrected importing resources with identical relative names but different base paths ([5792ac7](https://github.com/robotcodedev/robotcode/commit/5792ac764a164279db2048c6667e135a73d65444))
- Corrected checking if a resource is already imported ([b5a76b3](https://github.com/robotcodedev/robotcode/commit/b5a76b37937f57c30209f7fb03f298bcd0588c70))


## [0.97.0](https://github.com/robotcodedev/robotcode/compare/v0.96.0..v0.97.0) - 2024-11-13

### <!-- 0 -->Features

#### Analyze

- Add CLI options for `pythonpath`, `variable`, and `variablefile` to `analyze code` command; collect errors for unimportable command line variable files ([b4e6be4](https://github.com/robotcodedev/robotcode/commit/b4e6be4ea740808b07647d2eaf28e85fb486a0e0))
- `analyze code` command now also uses the settings in the `robot.toml` file. ([bd17a5d](https://github.com/robotcodedev/robotcode/commit/bd17a5d18372e0d1baa7b8e627e81c8d7639bab2))

#### Robot

- Display filename on TOML parsing error ([8c25db8](https://github.com/robotcodedev/robotcode/commit/8c25db81fb74ca9b0c647c434cb9ba9f344a54cd))


### <!-- 1 -->Bug Fixes

#### Language Server

- Support glob pattern in `robot.toml`s `python-path` setting ([f6e380c](https://github.com/robotcodedev/robotcode/commit/f6e380c624f3126cb960c576ca4e083c8fe9a0fc))

#### VS Code

- Correct handling of comments in tmlanguage ([ce794bf](https://github.com/robotcodedev/robotcode/commit/ce794bfcb16481e14c3b003a8587060999f78d66))


### <!-- 2 -->Documentation

- Expand documentation on `robotcode` packages, installation, and usage ([907fa8c](https://github.com/robotcodedev/robotcode/commit/907fa8c0b3c4d17b14fd1477f8acb4e7cd1aa401))

## [0.96.0](https://github.com/robotcodedev/robotcode/compare/v0.95.2..v0.96.0) - 2024-11-04

### <!-- 0 -->Features

#### Analyze

- Add command line support for static analysis of Robot Framework projects ([01a4c6d](https://github.com/robotcodedev/robotcode/commit/01a4c6dddc2c7ce7f2d4e63e31a5e3a01cec69f4))

#### VS Code

- Connect vscode testrun to the debug session to link the lifecycle to of the session to the ui actions of the test run ([0d3bd27](https://github.com/robotcodedev/robotcode/commit/0d3bd272df53905942723069acc2dc6511674d3c))


### <!-- 1 -->Bug Fixes

- Corrected hash calculation for keyword matchers for keywords with embedded arguments for RF < 7 ([c58f622](https://github.com/robotcodedev/robotcode/commit/c58f622f1493d49d5b87e476b99965e3d2c935e6))
#### VS Code

- Corrected tmlanguage to color variables in variables section ([0e32e41](https://github.com/robotcodedev/robotcode/commit/0e32e4123a0b5ae73055c1ebcf1a9e2d8bb5d8ab))


## [0.95.2](https://github.com/robotcodedev/robotcode/compare/v0.95.1..v0.95.2) - 2024-10-28

### <!-- 3 -->Performance

#### Analyzer

- Simplify generating of internal libdocs for resource files ([c232cea](https://github.com/robotcodedev/robotcode/commit/c232cea29672fc30eaf7a7e6ce08ee0ed8283968))


### <!-- 4 -->Refactor

#### All

- Some cache adjustments and removal of unnecessary code ([9b0999c](https://github.com/robotcodedev/robotcode/commit/9b0999cc4425d84fb20c6c81b0e63b1939abebe7))


## [0.95.1](https://github.com/robotcodedev/robotcode/compare/v0.95.0..v0.95.1) - 2024-10-26

### <!-- 1 -->Bug Fixes

#### Robot

- Corrected some type hint for python 3.8 ([47510ac](https://github.com/robotcodedev/robotcode/commit/47510ac37b26dd3f6ffd1e0e454e6ae581076017))

#### VS Code

- Restart the language server if a change is detected in a `.gitignore` or `.robotignore` file ([7613bb2](https://github.com/robotcodedev/robotcode/commit/7613bb25bbe1623016997dbfbeba85789f480e8b))


### <!-- 2 -->Documentation

- Update documentation for command line tools ([9e0d0dc](https://github.com/robotcodedev/robotcode/commit/9e0d0dc427c841c9a414a7baf00fc3cf9735c76a))

### <!-- 3 -->Performance

#### Language Server

- Corrected handling of matching multiple keywords if keywords have embedded keywords ([c662685](https://github.com/robotcodedev/robotcode/commit/c6626857053d103264c848685e06a33390991d11))

#### Analyzer

- Speed up finding keywords and variables a little bit more ([aaa6439](https://github.com/robotcodedev/robotcode/commit/aaa6439870378bf9dccaca8e8c310da742e8b3dd))
- Speed up the creation of libdocs from resource files ([2dfc91b](https://github.com/robotcodedev/robotcode/commit/2dfc91bb475781c6b0f557028046a69777eb155d))


## [0.95.0](https://github.com/robotcodedev/robotcode/compare/v0.94.0..v0.95.0) - 2024-10-25

### <!-- 0 -->Features

#### Analyzer

- Implemented better handling of imports of dynamic libraries ([f6b5b87](https://github.com/robotcodedev/robotcode/commit/f6b5b875daf7cd8d59d0cc46ea24a4d07b02c777))

  - show also errors on in dynamic library API like in `get_keyword_documentation` and `get_keyword_arguments`


#### Discover

- Rework discover commands ([87e1dd9](https://github.com/robotcodedev/robotcode/commit/87e1dd96c525c9639b2727681bac22cc4c3ca8cc))

  - show statistics on all commands
  - better differention of tests and tasks
  - new command `tasks` to show only the tasks
  - command tests show only the tests
  - new arguments for `tags` command `--tests` and `--tags`
  - show the type of test or task in test explorer description



### <!-- 1 -->Bug Fixes

#### Language Server

- Only update direct references to a file, not imports if something changes ([ea24b06](https://github.com/robotcodedev/robotcode/commit/ea24b061c77de38e1f755a74979d2632970ff032))
- Corrected inlay hints for bdd style keyword calls ([77ce8f1](https://github.com/robotcodedev/robotcode/commit/77ce8f1147a4355ea71986408971fca4f441bee5))

#### Analyzer

- Fixed find variables as modules for RF > 5 ([ce787b2](https://github.com/robotcodedev/robotcode/commit/ce787b26d6fab981e432166972429aa2d0d84240))
- Corrected exception in parsing ForHeaders with invalid variable ([0851d4f](https://github.com/robotcodedev/robotcode/commit/0851d4f6eb7bd90958996cc9c25506712885dca9))
- Corrected analyzing of `[Return]`, `[Setup]`, `[Teardown]` statement ([4e17c8f](https://github.com/robotcodedev/robotcode/commit/4e17c8fc10814f62799548467efac25c07fbe429))
- Handle bdd prefixes correctly if keyword is cached ([41ff53f](https://github.com/robotcodedev/robotcode/commit/41ff53f9b3c8cc34f06f34ebeaa7c63691544cb2))
- Fix some spellings ([b622c42](https://github.com/robotcodedev/robotcode/commit/b622c42d33bc0a41fab8ffa00cdc74cbb7fe98c8))


### <!-- 3 -->Performance

#### Analyzer

- Implemented DataCache, cache files are now saved in pickle format by default instead of json ([f3ecc22](https://github.com/robotcodedev/robotcode/commit/f3ecc221d0018f9264c958074a7458a6e119b1f6))
- Introduced some caching for parsing variables ([e39afe9](https://github.com/robotcodedev/robotcode/commit/e39afe92ef9dfd44d33537b4dec9bbec3738d116))
- Cache embedded arguments and some more little perf tweaks ([3603ff6](https://github.com/robotcodedev/robotcode/commit/3603ff6395d16473fdeb1fca8de910ea3aab8de2))
- Optimized analysing keyword calls ([b1f0f28](https://github.com/robotcodedev/robotcode/commit/b1f0f28dfd0c7f38904ae9ecd0c247f5efec2ab1))
- Restructured code for handling bdd prefixes ([96fbe90](https://github.com/robotcodedev/robotcode/commit/96fbe9064fafe0a64f82b0d95b017726d18381fb))


## [0.94.0](https://github.com/robotcodedev/robotcode/compare/v0.93.1..v0.94.0) - 2024-10-20

### <!-- 0 -->Features

- Python 3.13 support ([3874a9c](https://github.com/robotcodedev/robotcode/commit/3874a9cee3116794f510f79c1aa28586ce7b7d06))

### <!-- 1 -->Bug Fixes

- Correct analyzing of variables in WhileHeader options ([3a4ee79](https://github.com/robotcodedev/robotcode/commit/3a4ee79651c0d8ba650113e953abee52866f4338))
#### REPL

- Corrected start of repl command if there is no  `robot.toml` with a `path`  setting ([42f96b4](https://github.com/robotcodedev/robotcode/commit/42f96b4fe42e75c52f58734c1767cd7d39307e06))

#### Website

- Corrected some things about the inheritance of profiles ([aa50cc7](https://github.com/robotcodedev/robotcode/commit/aa50cc74173671b629ebd2c8c7adbddc5f5ce77d))

#### Analyzer

- Decrease load load library timeout and better error messages if time out occurs ([a3fb4a3](https://github.com/robotcodedev/robotcode/commit/a3fb4a3f6011b6d74cc5d9970b5faa1d7a090b1a))
- Better exception message for invalid command variable files ([f8cb770](https://github.com/robotcodedev/robotcode/commit/f8cb770e68815719d6c70404325c8e7e75956fd6))


### <!-- 3 -->Performance

#### Analyze

- Optimize find unused refences (1.5x-2x faster) ([fda1f02](https://github.com/robotcodedev/robotcode/commit/fda1f029a1c9e18b9334ade8ea338e47a953cd30))
- Improved performance of code analysis (more then 2x faster) ([2951759](https://github.com/robotcodedev/robotcode/commit/29517592ee6a09d6e36cb89dae81aa6b5669709e))

#### Analyzer

- Move model and token analyzing to the normal analysing stage ([7b3eb0c](https://github.com/robotcodedev/robotcode/commit/7b3eb0cafc5e3843827f3ef5e89b2c75bd986ab4))


### <!-- 4 -->Refactor

#### Analyze

- Remove unused/unneeded call to find variable in namespace ([b561607](https://github.com/robotcodedev/robotcode/commit/b5616072372bfe08bd6bcc9c08188ae867aa4a35))


## [0.93.1](https://github.com/robotcodedev/robotcode/compare/v0.93.0..v0.93.1) - 2024-10-09

### <!-- 1 -->Bug Fixes

#### Language Server

- Stabilized resolving of variables in test case and keyword documentation ([1bad58f](https://github.com/robotcodedev/robotcode/commit/1bad58fa16e10f0fe5b5f947b7fbea93b5497d8d))


## [0.93.0](https://github.com/robotcodedev/robotcode/compare/v0.92.0..v0.93.0) - 2024-10-08

### <!-- 0 -->Features

- Add `--no-vcs` command-line option to ignore VCS directories (e.g., .git) when detecting the project root ([d7e28f2](https://github.com/robotcodedev/robotcode/commit/d7e28f2c7c7ffd42ce3d989d1ae8f4e8207d7b81))

  #closes 201

- `--root` command line argument to specify a project root and disable autodetection of project root ([add4102](https://github.com/robotcodedev/robotcode/commit/add4102594ee73c3a93760eb4a5846358ddf2b1a))
- Improved logging with time information ([27d21b5](https://github.com/robotcodedev/robotcode/commit/27d21b599d7d5005e2920a11b47583e32f9a049c))

  - Operations that take a little longer now have an indication of how long they took
  - 2 new command line switches `--log-format` and `--log-style`, see also the Python logging documentation

#### CLI

- New command line interface tool - Robot Framework REPL interpreter ([be386d2](https://github.com/robotcodedev/robotcode/commit/be386d244be0b9b85ca4fbe49597985652f066db))

  The new CLI command `repl` introduces an interactive Robot Framework interpreter. You can install it by running `pip install robotcode[repl]` and start it via the command line using `robotcode repl`.

  With this interactive interpreter, you can execute Robot Framework keywords without the need to run a full test suite. By default, all BuiltIn keywords are immediately accessible. To load a library, you can use the `import library` keyword, and for resources or variable files, you can use the corresponding built-in commands `import resource` and `import variables`. The outcome of any keyword execution, along with relevant log details, is displayed directly in the console.

  You can exit the interpreter using the `exit` keyword or by pressing `CTRL`+`D` on Unix-like systems and `CTRL+Z` followed by `ENTER` on Windows.

  At this stage, the implementation is fairly basic, but additional features for the REPL command are planned. This also serves as the first step toward an exciting new feature (spoiler alert!): Robot Framework Notebooks.


#### Debugger

- Increase timeouts for debugger to fit better to python debugger timeouts and introduce environment variables to override these timeouts ([63f3e4a](https://github.com/robotcodedev/robotcode/commit/63f3e4ac4d061eed95c95d615c501b2d4430e378))

#### Language Server

- Resolve variable in hover for documentation settings in testcases and keywords ([ffa9bdb](https://github.com/robotcodedev/robotcode/commit/ffa9bdb2cdca47b20f56b14deaece59fc49b9a13))

#### VS Code

- Introduce RobotCode: Start Terminal REPL command for launching the interactive Robot Framework interpreter directly from VSCode ([f4025fb](https://github.com/robotcodedev/robotcode/commit/f4025fb77c54ea49531c1ec67f1072c0a43c87f9))


### <!-- 1 -->Bug Fixes

- Corrected highlightning invalid sections for RF7 ([d139ff1](https://github.com/robotcodedev/robotcode/commit/d139ff1f9c309060cc12d1d7499cab1ada4a0b01))
- Enable supportsANSIStyling in DAP to reeanble colored output in debug console ([0d5616c](https://github.com/robotcodedev/robotcode/commit/0d5616c33215ed993052d4f50e7ad41a13b21058))
- Logging of measure_time if log is disabled ([725c739](https://github.com/robotcodedev/robotcode/commit/725c739c0ed01b1249a611605c96e035467f03fa))

### <!-- 3 -->Performance

#### Language Server

- Speedup semantic highlightning a lot ([567ac72](https://github.com/robotcodedev/robotcode/commit/567ac72b393d6e42baadd575195744c5503da297))


### <!-- 4 -->Refactor

- Some performance tweaks ([d3b39be](https://github.com/robotcodedev/robotcode/commit/d3b39be576dd80d757554708fff2cd0bc40354ff))

## [0.92.0](https://github.com/robotcodedev/robotcode/compare/v0.91.0..v0.92.0) - 2024-10-01

### <!-- 0 -->Features

- Introduce `Select Python Environment` command and deprecate `robotcode.python` ([be0573d](https://github.com/robotcodedev/robotcode/commit/be0573ddcfaf1100de8058bc6383a013eaf4ee88))

  See [here](https://github.com/microsoft/vscode-python/wiki/Setting-descriptions#pythondefaultinterpreterpath) for an explanation.

#### Analyze

- Allow shortforms of `warning` and `information`, `warn` and `info` in diagnostic modifiers ([f226091](https://github.com/robotcodedev/robotcode/commit/f226091e59b0fff2858de7311d542b903c5bf2d3))

#### Config

- Added posibility to allow different tool configs to robot.toml.json schema ([ee256ce](https://github.com/robotcodedev/robotcode/commit/ee256ce38b39ae67ae107bb5fffa5dba8d8d7db4))

#### VS Code

- Introduce setting for modifing the diagnostics severity ([5cca59f](https://github.com/robotcodedev/robotcode/commit/5cca59fd364cb1c6a8a8c6f0e63a956bca88e366))

  With these settings, you can override the default configuration for all diagnostic messages. By combining file, block, and line diagnostic modifiers, you can precisely control how specific errors are displayed.

  - **`robotcode.analysis.diagnosticModifiers.ignore`**: Suppresses specific diagnostics from being displayed. You can specify one or more error codes, like `MultipleKeywords` or `[multiple-keywords, VariableNotFound]`. Use `*` to ignore all errors and then maybe add specific error codes to other modifiers, such as `information`, to selectively show them.
  - **`robotcode.analysis.diagnosticModifiers.error`**: Treats selected diagnostics as errors.
  - **`robotcode.analysis.diagnosticModifiers.warning`**: Displays chosen diagnostics as warnings.
  - **`robotcode.analysis.diagnosticModifiers.information`**: Shows specified diagnostics as information
  - **`robotcode.analysis.diagnosticModifiers.hint`**: Marks selected diagnostics as hints

  These settings allow you to tailor the diagnostic outputs to meet the specific needs of your project.


#### Robot.toml

- Introduce new settings for analysis in robot.toml ([fa37dba](https://github.com/robotcodedev/robotcode/commit/fa37dba7ccfebf9d221b6985a12e460e27209f64))


## [0.91.0](https://github.com/robotcodedev/robotcode/compare/v0.90.0..v0.91.0) - 2024-09-27

### <!-- 0 -->Features

- New command `RobotCode: Report Issue` ([94d1efa](https://github.com/robotcodedev/robotcode/commit/94d1efac4edeed7e6117a50448678254e8320c0c))

  with this command you can report an issue directly from vscode to RobotCode's issue tracker

#### Analyze

- Show messages for InvalidHeader and DeprecatedHeader for RF7 ([518aa12](https://github.com/robotcodedev/robotcode/commit/518aa127d57bfeaf3a0bd1cbfc034394f56f63cb))


### <!-- 1 -->Bug Fixes

#### VS Code

- Correct handling when opening library in keywords view if keyword is loaded twice with a different alias ([ac23751](https://github.com/robotcodedev/robotcode/commit/ac23751087fc9051ace8345ebe58cda88d4eb891))
- Tool menu stabilized ([de774fa](https://github.com/robotcodedev/robotcode/commit/de774fafa34269eb448b35fbf403ceb2cda04ed6))


## [0.90.0](https://github.com/robotcodedev/robotcode/compare/v0.89.1..v0.90.0) - 2024-09-16

### <!-- 0 -->Features

- Provide a language status icon and robot tools menu ([7ef83f3](https://github.com/robotcodedev/robotcode/commit/7ef83f3a5d70818ae8947d621ed765d0d3a65ce3))

  Language Status Item:
  ![image](https://github.com/user-attachments/assets/ff0d80d2-0cb5-4942-b828-ccab975cfc00)

  RobotCode Tool Menu
  ![image](https://github.com/user-attachments/assets/a9b15d1f-90c7-41f1-b29b-c9d6a59211e3)

  A short Video:
  https://github.com/user-attachments/assets/b6980485-d7ec-4f6c-88a0-7d1a4e65dc40


## [0.89.1](https://github.com/robotcodedev/robotcode/compare/v0.89.0..v0.89.1) - 2024-09-11

### <!-- 1 -->Bug Fixes

- Dont show completion right after `...` ([f24f6a8](https://github.com/robotcodedev/robotcode/commit/f24f6a8691451e34e65a3b6fba1f9d000278c066))
- Corrected completion of arguments after `...` continuation line ([377aa9d](https://github.com/robotcodedev/robotcode/commit/377aa9d39a185961b2e6c16cb68c7169f490b15f))
- Corrected parsing of OPTION tokens and variable resolving ([5a8abf2](https://github.com/robotcodedev/robotcode/commit/5a8abf2ea5ae0be9833ecd0ff90658d6e3dbac59))

## [0.89.0](https://github.com/robotcodedev/robotcode/compare/v0.88.0..v0.89.0) - 2024-09-10

### <!-- 0 -->Features

- Variables start with a `_` are no longer beeing reported as unused ([afea114](https://github.com/robotcodedev/robotcode/commit/afea11413ceb96d21397416c37f538102fd259cb))
- Enable Robot Framework 7.1 support ([6921c9a](https://github.com/robotcodedev/robotcode/commit/6921c9ac4457a3a8ad5b830584533c1c2ec69a99))

### <!-- 1 -->Bug Fixes

- Document highlight should only highlight real references not text references ([a0c184a](https://github.com/robotcodedev/robotcode/commit/a0c184a809fc8128d256c723d11fa49c160bbe32))

### <!-- 4 -->Refactor

- Fix some unused ignores for mypy ([575bbff](https://github.com/robotcodedev/robotcode/commit/575bbff0692fdcffcbc80aa4031450cff8148bd4))
- Use lambda instead of functools.partial ([1518f71](https://github.com/robotcodedev/robotcode/commit/1518f71acb48dd9e7ccd822da58d3203eebb7774))

  functools.partial with method is deprecated in Python 3.13


## [0.88.0](https://github.com/robotcodedev/robotcode/compare/v0.87.0..v0.88.0) - 2024-09-07

### <!-- 0 -->Features

#### CLI

- Disable console links for RF7.1 if running in VSCode terminal ([5e83537](https://github.com/robotcodedev/robotcode/commit/5e83537c999030780f9b254ca3c5ef7cbee99af3))

#### Config

- Add console_links to robot.toml ([3902937](https://github.com/robotcodedev/robotcode/commit/390293755d5f658e5e66a0be25ce1a1560f0483f))

#### Language Server

- Corrected and generalized semantic tokenizing if OPTION tokens in except and while statements ([d5a9339](https://github.com/robotcodedev/robotcode/commit/d5a9339e705e50ec3fb1af7e7559a5dd8b2012b5))


### <!-- 2 -->Documentation

- Add a Tip&Tricks page ([dd27480](https://github.com/robotcodedev/robotcode/commit/dd274806324388a7798de2c5e7fd3dcf2794a230))
- Update readme ([1e601e3](https://github.com/robotcodedev/robotcode/commit/1e601e3c1542d8358e1d207c5083cbbdfd3c20f2))
- Update some documentation about config and cli ([84553c3](https://github.com/robotcodedev/robotcode/commit/84553c358f6793855a4c7641659c0f7b75a1aba5))
- Introduce a script that generate the doc for cli tools ([ecb5ec9](https://github.com/robotcodedev/robotcode/commit/ecb5ec9db8740f9b794555b7a408a80670afe926))

## [0.87.0](https://github.com/robotcodedev/robotcode/compare/v0.86.2..v0.87.0) - 2024-08-29

### <!-- 0 -->Features

#### CLI

- New command `discover files` ([505f473](https://github.com/robotcodedev/robotcode/commit/505f4736c6d050304719866a3fdc210af5d8596a))

  find all relevant robot framework files in a project.


#### Discover

- Add more colors and infos to discover commands ([9e2d6f7](https://github.com/robotcodedev/robotcode/commit/9e2d6f7e8ecc36c2b4916f62153392664dc43ba2))


### <!-- 1 -->Bug Fixes

- Correct installing colorama package ([da28477](https://github.com/robotcodedev/robotcode/commit/da28477ad126b40f796d8a9b85c64d0077133dd8))

  this is somehow lost in the lates version of click..


## [0.86.2](https://github.com/robotcodedev/robotcode/compare/v0.86.1..v0.86.2) - 2024-08-29

### <!-- 1 -->Bug Fixes

- Correction of some type hints that prevent robot code from running with older Python versions ([37e20e3](https://github.com/robotcodedev/robotcode/commit/37e20e395c345c63b6e772e59cebdf6e3844550d))

## [0.86.1](https://github.com/robotcodedev/robotcode/compare/v0.86.0..v0.86.1) - 2024-08-29

### <!-- 2 -->Documentation

- Update about and remove playground ([fd140d0](https://github.com/robotcodedev/robotcode/commit/fd140d046e686f542277699fd5bdd76a54137883))

## [0.86.0](https://github.com/robotcodedev/robotcode/compare/v0.85.0..v0.86.0) - 2024-08-29

### <!-- 0 -->Features

#### RobotCode

- Introduce support for `.gitignore` and `.robotignore` during test suite discovery ([022517f](https://github.com/robotcodedev/robotcode/commit/022517fef7a428a952cf6df7bdd4b7690c9875d5))

  Implemented support for `.gitignore` and `.robotignore` files in the discovery process of Robot Framework test suites and test cases.

- Introduce support for `.gitignore` and `.robotignore` during test suite discovery ([74fa480](https://github.com/robotcodedev/robotcode/commit/74fa480cdbe6d03f9d146ea322db4e4e22e242e8))

  Implemented support for `.gitignore` and `.robotignore` files in the discovery process of Robot Framework test suites and test cases.



### <!-- 1 -->Bug Fixes

- Correct vscodeignore file ([461bfb1](https://github.com/robotcodedev/robotcode/commit/461bfb1048308959e7ba8de1c9be92a8e9257c29))

  I have over optimized the .vscodeignore file 🥶

- Change detection of win32 ([0dfbd94](https://github.com/robotcodedev/robotcode/commit/0dfbd947baa4eb7dae984fda29e3f5d502a01ea7))
- Change detection of win32 ([13a9265](https://github.com/robotcodedev/robotcode/commit/13a92652fa9a42d0eec989bd14cbe5cd3c115596))

## [0.85.0](https://github.com/robotcodedev/robotcode/compare/v0.84.0..v0.85.0) - 2024-08-18

### <!-- 0 -->Features

#### Language Server

- Send full completion info if language client does not support `completionItem/resolve` ([4cf0127](https://github.com/robotcodedev/robotcode/commit/4cf01274e70070b3c9eb9e630afe08be57035e37))


### <!-- 1 -->Bug Fixes

#### Language Server

- Corrected coloring of test case/keyword names if names contains line continuations `...` ([a848a93](https://github.com/robotcodedev/robotcode/commit/a848a935567a41804fa20879a5da6016b5a68f0d))


### <!-- 2 -->Documentation

- "Get Started" improved ([c9954ad](https://github.com/robotcodedev/robotcode/commit/c9954ad394069f71eeac23c4b3453588227834ae))
- Correct RF versions in README ([da0af7b](https://github.com/robotcodedev/robotcode/commit/da0af7b82064304c7ed7c1290bb081eb4b38dde6))
- Some more restrucuting ([5b2752f](https://github.com/robotcodedev/robotcode/commit/5b2752f66f2791da51e5d2cc7b063ec8b50fd247))
- Some reorganizations ([a49829b](https://github.com/robotcodedev/robotcode/commit/a49829b80b2e0f35eb4c70772bcff0af720fffeb))

## [0.84.0](https://github.com/robotcodedev/robotcode/compare/v0.83.3..v0.84.0) - 2024-08-08

### <!-- 0 -->Features

- Diagnostics modifiers ([223ec13](https://github.com/robotcodedev/robotcode/commit/223ec134a9a947db50aebba0d10ad290ab3bffb5))

  Implement functionality to configure diagnostic error messages during source code analysis. Lines in the code with the `# robotcode:` marker are now interpreted as modifiers. The full structure of a modifier is `# robotcode: <action>[code(,code)*]*`.

  **Allowed actions:**

  - `ignore`: Ignore specified diagnostic codes.
  - `hint`: Treat specified diagnostic codes as hints.
  - `warn`: Treat specified diagnostic codes as warnings.
  - `error`: Treat specified diagnostic codes as errors.
  - `reset`: Reset the diagnostic codes to their default state.

  **This implementation allows for the following:**

  - Custom actions to be performed on specified diagnostic codes.
  - Enhanced control over which diagnostic messages are shown, ignored, or modified.
  - Flexibility in managing diagnostic outputs for better code quality and debugging experience.

  **Usage details:**

  - A diagnostic modifier can be placed at the end of a line. It modifies only the errors occurring in that line.
  - A modifier can be placed at the very beginning of a line. It applies from that line to the end of the file.
  - If a modifier is within a block (e.g., Testcase, Keyword, IF, FOR) and is indented, it applies only to the current block.

  **Example usage:**

  - `# robotcode: ignore[variable-not-found, keyword-not-found]` - Ignores the errors for variable not found and keyword not found.
  - `# robotcode: hint[MultipleKeywords]` - Treats the MultipleKeywords error as a hint.
  - `# robotcode: warn[variable-not-found]` - Treats the variable-not-found error as a warning.
  - `# robotcode: error[keyword-not-found]` - Treats the keyword-not-found error as an error.
  - `# robotcode: reset[MultipleKeywords]` - Resets the MultipleKeywords error to its default state.
  - `# robotcode: ignore` - Ignores all diagnostic messages .
  - `# robotcode: reset` - Resets all diagnostic messages to their default.

  **Example scenarios:**

  *Modifier at the end of a line:*

  ```robot
  *** Keywords ***
  Keyword Name
      Log    ${arg1}    # robotcode: ignore[variable-not-found]
  ```
  This modifier will ignore the `variable-not-found` error for the `Log` keyword in this line only.

  *Modifier at the beginning of a line:*

  ```robot
  # robotcode: ignore[keyword-not-found]
  *** Test Cases ***
  Example Test
      Log    Hello
      Some Undefined Keyword
  ```
  This modifier will ignore `keyword-not-found` errors from the point it is declared to the end of the file.

  *Modifier within a block:*

  ```robot
  *** Keywords ***
  Example Keyword
      # robotcode: warn[variable-not-found]
      Log    ${arg1}
      Another Keyword
  ```
  This modifier will treat `variable-not-found` errors as warnings within the `Example Keyword` block.

  *Modifier using reset:*

  ```robot
  # robotcode: error[variable-not-found]
  *** Test Cases ***
  Example Test
      Log    ${undefined_variable}
      # robotcode: reset[variable-not-found]
      Log    ${undefined_variable}
  ```
  In this example, the `variable-not-found` error is treated as an error until it is reset in the `Another Test` block, where it will return to its default state.

  *Modifier to ignore all diagnostic messages:*

  ```robot
  # robotcode: ignore
  *** Test Cases ***
  Example Test
      Log    ${undefined_variable}
      Some Undefined Keyword
  ```
  This modifier will ignore all diagnostic messages from the point it is declared to the end of the file.

  *Modifier to reset all diagnostic messages:*

  ```robot
  # robotcode: ignore
  *** Test Cases ***
  Example Test
      Log    ${undefined_variable}
      # robotcode: reset
      Another Test
          Some Undefined Keyword
  ```
  In this example, all diagnostic messages are ignored until the `reset` modifier, which returns all messages to their default state from that point onward.

- Diagnostics modifiers ([d1e5f3f](https://github.com/robotcodedev/robotcode/commit/d1e5f3f5781ba50416fdd3e39c8416978dffc5c7))

  Implement functionality to configure diagnostic error messages during source code analysis. Lines in the code with the `# robotcode:` marker are now interpreted as modifiers. The full structure of a modifier is `# robotcode: <action>[code(,code)*]*`.

  **Allowed actions:**

  - `ignore`: Ignore specified diagnostic codes.
  - `hint`: Treat specified diagnostic codes as hints.
  - `warn`: Treat specified diagnostic codes as warnings.
  - `error`: Treat specified diagnostic codes as errors.
  - `reset`: Reset the diagnostic codes to their default state.

  **This implementation allows for the following:**

  - Custom actions to be performed on specified diagnostic codes.
  - Enhanced control over which diagnostic messages are shown, ignored, or modified.
  - Flexibility in managing diagnostic outputs for better code quality and debugging experience.

  **Usage details:**

  - A diagnostic modifier can be placed at the end of a line. It modifies only the errors occurring in that line.
  - A modifier can be placed at the very beginning of a line. It applies from that line to the end of the file.
  - If a modifier is within a block (e.g., Testcase, Keyword, IF, FOR) and is indented, it applies only to the current block.

  **Example usage:**

  - `# robotcode: ignore[variable-not-found, keyword-not-found]` - Ignores the errors for variable not found and keyword not found.
  - `# robotcode: hint[MultipleKeywords]` - Treats the MultipleKeywords error as a hint.
  - `# robotcode: warn[variable-not-found]` - Treats the variable-not-found error as a warning.
  - `# robotcode: error[keyword-not-found]` - Treats the keyword-not-found error as an error.
  - `# robotcode: reset[MultipleKeywords]` - Resets the MultipleKeywords error to its default state.
  - `# robotcode: ignore` - Ignores all diagnostic messages .
  - `# robotcode: reset` - Resets all diagnostic messages to their default.

  **Example scenarios:**

  *Modifier at the end of a line:*

  ```robot
  *** Keywords ***
  Keyword Name
      Log    ${arg1}    # robotcode: ignore[variable-not-found]
  ```
  This modifier will ignore the `variable-not-found` error for the `Log` keyword in this line only.

  *Modifier at the beginning of a line:*

  ```robot
  # robotcode: ignore[keyword-not-found]
  *** Test Cases ***
  Example Test
      Log    Hello
      Some Undefined Keyword
  ```
  This modifier will ignore `keyword-not-found` errors from the point it is declared to the end of the file.

  *Modifier within a block:*

  ```robot
  *** Keywords ***
  Example Keyword
      # robotcode: warn[variable-not-found]
      Log    ${arg1}
      Another Keyword
  ```
  This modifier will treat `variable-not-found` errors as warnings within the `Example Keyword` block.

  *Modifier using reset:*

  ```robot
  # robotcode: error[variable-not-found]
  *** Test Cases ***
  Example Test
      Log    ${undefined_variable}
      # robotcode: reset[variable-not-found]
      Log    ${undefined_variable}
  ```
  In this example, the `variable-not-found` error is treated as an error until it is reset in the `Another Test` block, where it will return to its default state.

  *Modifier to ignore all diagnostic messages:*

  ```robot
  # robotcode: ignore
  *** Test Cases ***
  Example Test
      Log    ${undefined_variable}
      Some Undefined Keyword
  ```
  This modifier will ignore all diagnostic messages from the point it is declared to the end of the file.

  *Modifier to reset all diagnostic messages:*

  ```robot
  # robotcode: ignore
  *** Test Cases ***
  Example Test
      Log    ${undefined_variable}
      # robotcode: reset
      Another Test
          Some Undefined Keyword
  ```
  In this example, all diagnostic messages are ignored until the `reset` modifier, which returns all messages to their default state from that point onward.

#### Debugger

- Added support for disabling the hiding of debugger threads/tasks. ([049c905](https://github.com/robotcodedev/robotcode/commit/049c90517d36035e3bc86d0271e219e744c5dc7c))

  By setting the ROBOTCODE_DISABLE_HIDDEN_TASKS environment variable to a value not equal to 0, the Robot Code debugger will not be hidden from the Debugpy debugger, allowing you to debug the Robot Code debugger itself.



### <!-- 1 -->Bug Fixes

#### Debugger

- Corrected start debuggin in internalConsole ([f3fbf20](https://github.com/robotcodedev/robotcode/commit/f3fbf20d01d75264d86c0af4575e98b0cfa7ec5b))
- Corrected start debuggin in internalConsole ([b5124c8](https://github.com/robotcodedev/robotcode/commit/b5124c87265aac26f30ec535ec72770bf258cfbd))
- Corrected handling of local variables in variables inspector ([12ecdd4](https://github.com/robotcodedev/robotcode/commit/12ecdd43376484a40b6cdeb2bca752bc09178fad))

#### Robot

- Use casefold for normalizing and remove some local imports in VariableMatcher ([04e12a7](https://github.com/robotcodedev/robotcode/commit/04e12a7ee262177f5bede595baa14e283c3ef4e7))

#### VS Code

- Only test cases are reported as queued, started and completed ([f68b8e3](https://github.com/robotcodedev/robotcode/commit/f68b8e34161b4ec977fcae04d891399a53f951fc))

  this corrects the number of successful/executed test cases in the upper area of the test explorer

- Remove `attachPython` from default `launch.json` config ([8052f8d](https://github.com/robotcodedev/robotcode/commit/8052f8dfc4e83a8d7e26ef8049c3631881e0dd34))
- Only test cases are reported as queued, started and completed ([1d01f43](https://github.com/robotcodedev/robotcode/commit/1d01f43687a1b2f8428982cadcee7e72e1764738))

  this corrects the number of successful/executed test cases in the upper area of the test explorer

- Remove `attachPython` from default `launch.json` config ([217653b](https://github.com/robotcodedev/robotcode/commit/217653b6a6c3e78dbbead659880c12c1d5fb4a54))


### <!-- 2 -->Documentation

- Fix some formatting and spelling things ([99d18fe](https://github.com/robotcodedev/robotcode/commit/99d18fe2ffa3f754b125b7ae5f501ae90144c561))
- Updated config page ([b230689](https://github.com/robotcodedev/robotcode/commit/b23068989da3aaff5ed8dce3b3c6653dceb88eb5))
#### Quickstart

- Improve quickstart documentation ([a5dd60a](https://github.com/robotcodedev/robotcode/commit/a5dd60a0d1da7fd85cb781eaaaf530e5d8f30e8a))
- Add quickstart documentation page ([1fdb966](https://github.com/robotcodedev/robotcode/commit/1fdb966038595b79b7081ee94a735a8d76f3098e))


## [0.83.3](https://github.com/robotcodedev/robotcode/compare/v0.83.2..v0.83.3) - 2024-06-20

### <!-- 1 -->Bug Fixes

#### Config

- Correct handling of string expression at building the command line in config model ([0a85e3d](https://github.com/robotcodedev/robotcode/commit/0a85e3df465805e6c6ec098d51ee6af43a72ae39))


## [0.83.2](https://github.com/robotcodedev/robotcode/compare/v0.83.1..v0.83.2) - 2024-06-20

### <!-- 1 -->Bug Fixes

#### VS Code

- Some small corrections for in (semantic) highlightning ([43321f6](https://github.com/robotcodedev/robotcode/commit/43321f652930f91a4a2ab3f8ebd96056076dcdb5))
- Optimize tmLanguage definition ([166cd25](https://github.com/robotcodedev/robotcode/commit/166cd2536d545c003fd8d7cdd5da31cfb74f94d4))


### <!-- 2 -->Documentation

- Fix some typos ([8a1e91e](https://github.com/robotcodedev/robotcode/commit/8a1e91ed7cec0749e5b62ab99db27fede249ddda))

## [0.83.1](https://github.com/robotcodedev/robotcode/compare/v0.83.0..v0.83.1) - 2024-06-10

### <!-- 1 -->Bug Fixes

#### Config

- Correct some markdown syntax error in documentation for config model ([b5fed35](https://github.com/robotcodedev/robotcode/commit/b5fed353f75c679a49e9000a085ebdeca2b9d30d))

#### VS Code

- Correct highlightning of line continuations if it contains empty lines or comments lines ([c274c51](https://github.com/robotcodedev/robotcode/commit/c274c5113c55c75ba9496a3337279a11bb7dded0))


### <!-- 2 -->Documentation

- Add a logo with text ([1ded4d0](https://github.com/robotcodedev/robotcode/commit/1ded4d0b10cfd137271e867ebfc0bd1c4d7fd12c))
- Setup vitepress project correctly ([882d27c](https://github.com/robotcodedev/robotcode/commit/882d27c8c26af1d69c62c697b76e6c33874fb646))
- Initial move to vitepress for documentation ([f37d8e7](https://github.com/robotcodedev/robotcode/commit/f37d8e7b3e89eedb04c92fa032b257a7efede43c))
- Add a header to config docs ([17ae419](https://github.com/robotcodedev/robotcode/commit/17ae419c237c5e76d4cb2294c676896780dfade1))

## [0.83.0](https://github.com/robotcodedev/robotcode/compare/v0.82.3..v0.83.0) - 2024-05-16

### <!-- 0 -->Features

#### VS Code

- Support for highlighning robot code in markdown code blocks ([b9de061](https://github.com/robotcodedev/robotcode/commit/b9de061f4511dec43c8a6f1b04437a1ccb1bc20d))

  use the at defining the language in a codeblock you can use `robot` or `robotframework` as specifier



### <!-- 1 -->Bug Fixes

#### Debugger

- Fix type annotations for python 3.8 ([d2cc421](https://github.com/robotcodedev/robotcode/commit/d2cc42129725566c08bb0fe49f81fb41b2600695))


## [0.82.3](https://github.com/robotcodedev/robotcode/compare/v0.82.2..v0.82.3) - 2024-05-12

### <!-- 1 -->Bug Fixes

#### Analyse

- Allow local variables in [Teardown] ([5bab97c](https://github.com/robotcodedev/robotcode/commit/5bab97c16f13a9041401c27e07782dbde9ce90a0))


## [0.82.2](https://github.com/robotcodedev/robotcode/compare/v0.82.1..v0.82.2) - 2024-05-10

### <!-- 1 -->Bug Fixes

#### Analyse

- Correct handling of keyword arguments in all other keyword settings, regardless of the order of the settings. ([62f9544](https://github.com/robotcodedev/robotcode/commit/62f95443b2f70d92afd16b15c65d9943f4e5f34e))


## [0.82.1](https://github.com/robotcodedev/robotcode/compare/v0.82.0..v0.82.1) - 2024-05-09

### <!-- 1 -->Bug Fixes

#### Runner

- `--by-longname` and `--exclude-by-longname` now take into account whether a name for the run was set via `--name` command line argument or in the `name` setting robot.toml ([6f5c719](https://github.com/robotcodedev/robotcode/commit/6f5c719832885e524b72a69d47b2ccaf0608f6f9))


### <!-- 4 -->Refactor

#### Debugger

- Some code simplifications ([bc97744](https://github.com/robotcodedev/robotcode/commit/bc977445a5419cdc6ea5ad968298395a538a12bc))


## [0.82.0](https://github.com/robotcodedev/robotcode/compare/v0.81.0..v0.82.0) - 2024-05-05

### <!-- 0 -->Features

#### VS Code

- Detection of invalid robot environment now shows a quickpick instead an error message ([95a7630](https://github.com/robotcodedev/robotcode/commit/95a7630e4c8820d8521935847a65eb71bf215097))

  In the case RobotCode will initalize the LanguageServer and detect that environment is not valid, means wrong python version, no robotframework installed, instead an error message pops up a quickpick pops up, where you can do different things, like select a differnt interpreter, create a new venv, ignore this for the moment.
  The advantage of this way is, that this also works with extensions like Pyhton Manger and so on



## [0.81.0](https://github.com/robotcodedev/robotcode/compare/v0.80.0..v0.81.0) - 2024-05-03

### <!-- 0 -->Features

#### VS Code

- Get debugpy debuggerpackagepath from ms-python.debugpy extension ([9a00d0c](https://github.com/robotcodedev/robotcode/commit/9a00d0c4588bcfe55d5838070dc76410fa060c19))


### <!-- 1 -->Bug Fixes

#### Debugger

- Rework async code in debugger and some other little quitrks in debugger, like hiding the debugger thread when debuggin python code ([d7fe611](https://github.com/robotcodedev/robotcode/commit/d7fe611b1a88a8cac3ea31de4cf7de6a33339ea3))


## [0.80.0](https://github.com/robotcodedev/robotcode/compare/v0.79.0..v0.80.0) - 2024-05-01

### <!-- 0 -->Features

- We have a new icon ([fe78ec8](https://github.com/robotcodedev/robotcode/commit/fe78ec8ce6f7e269f22e9b9dd03b226d2eb96c54))

## [0.79.0](https://github.com/robotcodedev/robotcode/compare/v0.78.4..v0.79.0) - 2024-04-21

### <!-- 0 -->Features

#### Language Server

- Highlight some formatting tags in documentation like bold and italics for englisch language ([4d2cdae](https://github.com/robotcodedev/robotcode/commit/4d2cdae250d797d816366a723eeb56d4e93519a4))

#### VS Code

- Add option to disable the vscodes test explorer/execution integration ([9332099](https://github.com/robotcodedev/robotcode/commit/93320995e4cb206e42339247d55c78f9fd327916))


### <!-- 1 -->Bug Fixes

#### Debugger

- Don't show a message on unsupported rpc commands ([504e091](https://github.com/robotcodedev/robotcode/commit/504e091954b053288701d8b729a9ae2609ed73cc))

#### Language Server

- Normalize path handling should not fully resolve symlinks ([0c0198a](https://github.com/robotcodedev/robotcode/commit/0c0198a99374cea5d6801b8590292bef06e87073))


## [0.78.4](https://github.com/robotcodedev/robotcode/compare/v0.78.3..v0.78.4) - 2024-03-20

### <!-- 1 -->Bug Fixes

#### RobotCode

- Add missing `robotcode-robot` dependency ([d9cea02](https://github.com/robotcodedev/robotcode/commit/d9cea026d5f28773f1951b4717e014c0e17e15d0))


## [0.78.3](https://github.com/robotcodedev/robotcode/compare/v0.78.2..v0.78.3) - 2024-03-20

### <!-- 1 -->Bug Fixes

#### Language Server

- Add missing `robotcode-robot` dependency ([2d1c99d](https://github.com/robotcodedev/robotcode/commit/2d1c99d3cdeef9681f3bbeb4fc4f5df0f5d6de93))


## [0.78.2](https://github.com/robotcodedev/robotcode/compare/v0.78.1..v0.78.2) - 2024-03-19

### <!-- 1 -->Bug Fixes

#### Tidy

- Make robotframework-tidy 4.11 running ([569dbe8](https://github.com/robotcodedev/robotcode/commit/569dbe8e1ed264bed2f99c29fdb2d2c949acee30))


## [0.78.1](https://github.com/robotcodedev/robotcode/compare/v0.78.0..v0.78.1) - 2024-03-15

### <!-- 1 -->Bug Fixes

#### Analyze

- If a imported resource has import errors it is shown as releated information ([caf8541](https://github.com/robotcodedev/robotcode/commit/caf8541c76e98bbd3ece931be31e00b388634d3a))

#### Language Server

- Hovering over `EMPTY` builtin variable respects the type and shows correct empty values ([c8b66c8](https://github.com/robotcodedev/robotcode/commit/c8b66c8fcd05d18ee1d27b79f20bc8d2ff51dc44))

#### Profiles

- Profiles inherited by `[profile].inherit` are now merged before the parent profile, unless the `precedence` is set and are only enabled if the parent profile is enabled ([318d780](https://github.com/robotcodedev/robotcode/commit/318d780d9e04b7cfae42a1616af76af56317b320))


## [0.78.0](https://github.com/robotcodedev/robotcode/compare/v0.77.1..v0.78.0) - 2024-03-07

### <!-- 0 -->Features

#### VS Code

- Python syntax highlightning in IF and WHILE statements ([c56def3](https://github.com/robotcodedev/robotcode/commit/c56def3577d1e3024f747695119e5ed6e508d200))

  implements a part of #230



### <!-- 1 -->Bug Fixes

#### VS Code

- Some corrections in environment variable highlightning ([8936bfb](https://github.com/robotcodedev/robotcode/commit/8936bfbabfef3b35811db32a757e577010c78e6f))


## [0.77.1](https://github.com/robotcodedev/robotcode/compare/v0.77.0..v0.77.1) - 2024-03-06

### <!-- 1 -->Bug Fixes

#### VS Code

- Correct some things in bracket highlightning and coloring ([6c584dc](https://github.com/robotcodedev/robotcode/commit/6c584dc5923398f43f6df1e09f1e6e07a12d4b44))


## [0.77.0](https://github.com/robotcodedev/robotcode/compare/v0.76.2..v0.77.0) - 2024-03-05

### <!-- 0 -->Features

#### VS Code

- Python syntax highlightning in `${{}}` expressions ([adf3627](https://github.com/robotcodedev/robotcode/commit/adf36270ab7d39028ee1684e438cc42694af5e67))

  this implements a part of #230

- Enable bracket coloring and matching in keyword arguments ([45243e5](https://github.com/robotcodedev/robotcode/commit/45243e589ce44274aae58186071dbf271392d408))


### <!-- 1 -->Bug Fixes

#### Diagnostics

- Resolving variables does not work for builtin vars at library import ([6b97730](https://github.com/robotcodedev/robotcode/commit/6b97730f1791482a9ca9e5dee847cf6a240c98e2))


## [0.76.2](https://github.com/robotcodedev/robotcode/compare/v0.76.1..v0.76.2) - 2024-03-01

### <!-- 1 -->Bug Fixes

#### CLI

- Add missing plugin package ([66982bd](https://github.com/robotcodedev/robotcode/commit/66982bd2dab0a15081e82ccd1bdcbfd466fcafd7))


## [0.76.1](https://github.com/robotcodedev/robotcode/compare/v0.76.0..v0.76.1) - 2024-02-29

### <!-- 1 -->Bug Fixes

#### Core

- Send cache_invalidate events before and after locking to avoid deadlocks ([5f06377](https://github.com/robotcodedev/robotcode/commit/5f06377bfdd436dd0d1867ab6817cec7521454dc))
- Avoid iterator changes during Event.notify when adding or removing new event handlers ([ccc5faf](https://github.com/robotcodedev/robotcode/commit/ccc5fafe40b1e9cbec828f3e976189ba35b0100d))

#### Language Server

- Change keywords treeview rpc methods to non async ([f85621a](https://github.com/robotcodedev/robotcode/commit/f85621ac7f9ccdf22b54e8528a788eea2fd6fbf5))
- Sometimes an exception in evaluating variables in expressions occurs ([bd9bcfd](https://github.com/robotcodedev/robotcode/commit/bd9bcfde91e61261e4580552e1a3d2c92200d3c5))


### <!-- 3 -->Performance

#### Language Server

- Optimize analysing and collecting diagnostics ([065db06](https://github.com/robotcodedev/robotcode/commit/065db067b2d80259edd2267e08f40690a5f22a41))


## [0.76.0](https://github.com/robotcodedev/robotcode/compare/v0.75.0..v0.76.0) - 2024-02-19

### <!-- 0 -->Features

#### Language Server

- Introduce new setting `robotcode.analysis.cache.ignoreArgumentsForLibrary` ([bb55ff4](https://github.com/robotcodedev/robotcode/commit/bb55ff4e73c2221a2e811c2644538501982906cb))

  This is usefull if you have library that get's variables from a python file that contains complex data like big dictionaries or complex objects that robotcode can't handle.


#### VS Code

- Use the official python extension api to get informations about python environments ([c032814](https://github.com/robotcodedev/robotcode/commit/c032814bbf1a51a9a9ece79fef51cbcac4a0aa53))

  closes [ENHANCEMENT] Integrate new Python Extension API #215


#### Marketplace

- Create a Q&A discussion category on github ([605377d](https://github.com/robotcodedev/robotcode/commit/605377dce9facf12c0d7db296e620a42d7a3e87b))

  as a second way to ask questions and collect answers about robotcode I created a discussion group on the RobotCode github repository



### <!-- 1 -->Bug Fixes

#### Language Server

- Correct variable handling from resource imports ([619eee4](https://github.com/robotcodedev/robotcode/commit/619eee4c879fcc586b8b8be396cb141c0488cdf4))
- Add duplicated imports to references ([e603628](https://github.com/robotcodedev/robotcode/commit/e603628f599c361e13b2f09acf236c30d3822496))

#### VS Code

- Correct resolving resource documentation in keywords treeview ([2935bb8](https://github.com/robotcodedev/robotcode/commit/2935bb8b139f88d48217d902fd69bd0233e17dcb))


### <!-- 3 -->Performance

#### Language Server

- Try to use the last initialized namespace for completions to be a bit more responsive ([2c6fe37](https://github.com/robotcodedev/robotcode/commit/2c6fe37c2e8be9d13aca9eca0d07ff4ee1b85456))

#### Analyzer

- Optimization of the analysis of imports, accelerated by a factor of 3 ([321b88d](https://github.com/robotcodedev/robotcode/commit/321b88d33e083bfcef650a491afb518edc811ffe))


## [0.75.0](https://github.com/robotcodedev/robotcode/compare/v0.74.0..v0.75.0) - 2024-02-13

### <!-- 0 -->Features

#### VS Code

- Debugger now uses the new `Python Debugger` extension as default debugger for python ([aab6b6d](https://github.com/robotcodedev/robotcode/commit/aab6b6dc3d6f07ce35ddd292605c24df525475be))

  Microsoft rewrites the debugger extension for python and this will be the new standard extension for debugging python code. see [here](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy)



### <!-- 1 -->Bug Fixes

#### Debugger

- Fix some small glitches when robot is terminated but the Vscode is not fast enough to notice it ;-) ([5fdb0d7](https://github.com/robotcodedev/robotcode/commit/5fdb0d7f7ab92a131172d38e252810e82e39bad6))
- Correct wrong lineno informations from robot in listener start_(test/suite/keyword) lineno is `None` ([b4f9c5c](https://github.com/robotcodedev/robotcode/commit/b4f9c5c67f41d7be1170c9da022cd5421a0d20ef))

  If RobotFramework executes a test case, keyword or so, where the line number is not set internally, i.e. `None`, it generates an empty string for the line number in the listener instead of also passing `None`. This rarely happens, but it does occur.



## [0.74.0](https://github.com/robotcodedev/robotcode/compare/v0.73.3..v0.74.0) - 2024-02-12

### <!-- 0 -->Features

#### VS Code

- Organize vscode settings in groups ([9bbe68b](https://github.com/robotcodedev/robotcode/commit/9bbe68bcd9ba718d8293c27ee3e64a6d9cd792a4))


### <!-- 1 -->Bug Fixes

#### Debugger

- Add `BuiltIn.Run Keyword And Return Status` to the list of keywords that caught exceptions on inner keywords ([add8297](https://github.com/robotcodedev/robotcode/commit/add8297e851f1226dd980fa543bb4c9f124ad441))
- Filling zeros are now added to the name of an element so that elements are sorted correctly in the variable view at debugging time ([456ab2c](https://github.com/robotcodedev/robotcode/commit/456ab2c0a30a490e3324d0376cd7fe651a1c2c4a))

#### Language Server

- Correct importing variables with the same filename ([e1ac0cb](https://github.com/robotcodedev/robotcode/commit/e1ac0cb5ed439fce3e8c9c2dad19ded4c1726eb4))

  closes [BUG] Variables from variable files are often displayed as not found #214


#### Robot

- Handle OSErrors if creating/reading user robot.toml ([470b438](https://github.com/robotcodedev/robotcode/commit/470b438778f2c82c31de08e39b75d7663a5fe504))

  should fix: #187



## [0.73.3](https://github.com/robotcodedev/robotcode/compare/v0.73.2..v0.73.3) - 2024-02-07

### <!-- 1 -->Bug Fixes

#### Discover

- Update run buttons doesn't work on typing ([5f8a890](https://github.com/robotcodedev/robotcode/commit/5f8a8903660f97a2fcc10219ce5962045800febb))


## [0.73.2](https://github.com/robotcodedev/robotcode/compare/v0.73.1..v0.73.2) - 2024-02-07

### <!-- 1 -->Bug Fixes

#### Discover

- Discover files when robot arguments with relative files are now read correctly ([d12c67c](https://github.com/robotcodedev/robotcode/commit/d12c67c5ff9a0ebc4a80d507d15666079406d869))


### <!-- 2 -->Documentation

- Update versions in README ([d6c6f09](https://github.com/robotcodedev/robotcode/commit/d6c6f097bad4ffa17e77ba251b6b01e124557ee6))

## [0.73.1](https://github.com/robotcodedev/robotcode/compare/v0.73.0..v0.73.1) - 2024-02-05

### <!-- 1 -->Bug Fixes

#### Language Server

- Don't show deprecation message for tags starting with an hyphen in RF7 ([d510a65](https://github.com/robotcodedev/robotcode/commit/d510a653078bbcc6ee1527041c0ce8240c2fbb72))

  fixes [BUG] #212



## [0.73.0](https://github.com/robotcodedev/robotcode/compare/v0.72.0..v0.73.0) - 2024-02-05

### <!-- 0 -->Features

#### VS Code

- Introduce robotcode contribution point for vscode extensions plugins ([6519687](https://github.com/robotcodedev/robotcode/commit/6519687823cc7d955b4ea30439b4c436f5828b4c))


### <!-- 1 -->Bug Fixes

#### VS Code

- Stabilized recreation of test explorer items if folders are deleted ([370ff84](https://github.com/robotcodedev/robotcode/commit/370ff847e644ff99d7563a5fbc04b81864dcb5f6))
- Trim and shorten long names and descriptions in `Select Configuration Profiles` command ([8abcb67](https://github.com/robotcodedev/robotcode/commit/8abcb67cc697e0fcf3986b551727338887daeeff))

#### Discover

- Don't show an error if no tests or suite are found ([f57b065](https://github.com/robotcodedev/robotcode/commit/f57b065dd6ecda58176f2af5cb945daed7d1a3ea))


## [0.72.0](https://github.com/robotcodedev/robotcode/compare/v0.71.1..v0.72.0) - 2024-02-01

### <!-- 0 -->Features

#### VS Code

- Show profiles from robot.toml in test explorer as test profile ([fcb32a7](https://github.com/robotcodedev/robotcode/commit/fcb32a7a0e7ea40e87e0b459db2cdfd582837b0e))

#### Profiles

- A profile can now be hidden and inherit from other profiles ([9cd2ffb](https://github.com/robotcodedev/robotcode/commit/9cd2ffb16ecf139c5c8f2c3cdda2a82cc529b7b5))
- Profiles prefixed with an underscore (`_`) are now automatically hidden in `profiles list` command ([97bf390](https://github.com/robotcodedev/robotcode/commit/97bf3901652892cca71f5a92d98adb151cdfb772))
- Enhanced handling of environment variables in profile settings ([37fdbb3](https://github.com/robotcodedev/robotcode/commit/37fdbb3108360e20eb44235d0a3130df32d69ff5))

  This update allows the setting, overriding, and utilization of system environment variables in expressions and conditions within the robot.toml configuration files. This enhancement increases the flexibility and adaptability of profile configurations.



### <!-- 1 -->Bug Fixes

#### Profiles

- Enhanced error handling if invalid profile is given ([c3d8b07](https://github.com/robotcodedev/robotcode/commit/c3d8b0732cf689953abee2ca007e16f9f7759930))


## [0.71.1](https://github.com/robotcodedev/robotcode/compare/v0.71.0..v0.71.1) - 2024-01-30

### <!-- 1 -->Bug Fixes

#### VS Code

- Remove unneeded "test" badge on the explorer icon ([4f012b4](https://github.com/robotcodedev/robotcode/commit/4f012b44dc4bd0c54de75a510e7512b649f9b8a8))

#### Diagnostics

- Library doc are now correctly unloaded when they are no longer needed ([df6762a](https://github.com/robotcodedev/robotcode/commit/df6762af293b18def1c565ac0856f8b0f3f1295b))


### <!-- 3 -->Performance

#### Language Server

- Remove unneeded double caching of library imports ([3de0882](https://github.com/robotcodedev/robotcode/commit/3de08823a559cc141b7b530384cb5924c8ce7b54))


### <!-- 4 -->Refactor

#### Core

- Add locks with default_timouts in documents actions ([5eab74e](https://github.com/robotcodedev/robotcode/commit/5eab74e799ef70a47f9e45a15035424b19bfd3bb))


## [0.71.0](https://github.com/robotcodedev/robotcode/compare/v0.70.0..v0.71.0) - 2024-01-27

### <!-- 0 -->Features

#### Analyzer

- Introduce `robotcode.analysis.robot.globalLibrarySearchOrder` setting to specify a global search for libs and resources ([9d34ed4](https://github.com/robotcodedev/robotcode/commit/9d34ed4c9e826465e52f54ebcfee483fb6a740b3))

  Implemented this, because analyse `Set Library Search Order` is to hard.



## [0.70.0](https://github.com/robotcodedev/robotcode/compare/v0.69.0..v0.70.0) - 2024-01-26

### <!-- 0 -->Features

#### VS Code

- Simple drag'n drop keywords from keywords view to text editor ([6093387](https://github.com/robotcodedev/robotcode/commit/60933878cb5c9b7ed2e46caab67ee32e073dc366))


### <!-- 1 -->Bug Fixes

#### Debugger

- Fix some things in debugger to better support Robot Framework version 7.0 ([a81695c](https://github.com/robotcodedev/robotcode/commit/a81695c617c41d6e257c5fafee92fd746431a698))

#### Language Server

- Correct minimum robot version in version check ([f33c80a](https://github.com/robotcodedev/robotcode/commit/f33c80a730b49667ef5f463733bd32880f44e145))

#### Analyzer

- Correct resolving variables declared with the new VAR statement and a scope ([a259ec6](https://github.com/robotcodedev/robotcode/commit/a259ec6bbc1c8ae4ae2d5169e4f7df184292cc82))


## [0.69.0](https://github.com/robotcodedev/robotcode/compare/v0.68.5..v0.69.0) - 2024-01-24

### <!-- 0 -->Features

#### Language Server

- Start the internal HTTP server only on demand ([2254156](https://github.com/robotcodedev/robotcode/commit/2254156c2109cd4fb80a12d615e2b79d78bcda5f))

  You can disable this behaviour with the new option `robotcode.documentationServer.startOnDemand`.


#### VS Code

- New keywords tree view in the explorer sidebar ([c0495e6](https://github.com/robotcodedev/robotcode/commit/c0495e680e0d046a9e4937451e9a6b04ac28b268))


### <!-- 1 -->Bug Fixes

#### Language Server

- Display the return type in hover only when it is explicitly defined ([3fa09a7](https://github.com/robotcodedev/robotcode/commit/3fa09a7cccee5170b400626876ca6f1bdcb984d8))

#### Runner

- Environment vars are evaluated to late ([f74ea4a](https://github.com/robotcodedev/robotcode/commit/f74ea4ac4f98aa04a1c342434b8b0e19559f4ea6))


## [0.68.5](https://github.com/robotcodedev/robotcode/compare/v0.68.4..v0.68.5) - 2024-01-21

### <!-- 1 -->Bug Fixes

#### Language Server

- Filewatcher does not work ([5b72148](https://github.com/robotcodedev/robotcode/commit/5b7214824eb51bab6d1adaec97f177f152fde0bf))


## [0.68.4](https://github.com/robotcodedev/robotcode/compare/v0.68.3..v0.68.4) - 2024-01-20

### <!-- 1 -->Bug Fixes

#### Language Server

- Start langserver should not raise a TypeError if startet with no config ([5eca367](https://github.com/robotcodedev/robotcode/commit/5eca367f87d27fd0bfe99023f21db7e137af2c37))


### <!-- 2 -->Documentation

- Create CONTRIBUTING.md and review CODE_OF_CONDUCT.md ([a107b95](https://github.com/robotcodedev/robotcode/commit/a107b95b3fc40b76abfe74972b5f0e254cbfabe4))
- Change description of package ([f6a4f79](https://github.com/robotcodedev/robotcode/commit/f6a4f79df13b72b36cb5958f467ac3c2d75eae66))

### <!-- 4 -->Refactor

- Move diagnostics helper code to robotcode.robot package ([c94edb3](https://github.com/robotcodedev/robotcode/commit/c94edb306132daddccd6fd9e64343914aafa868a))
#### Language Server

- Move TextDocument from langserver to core package, some other simple refactorings ([d60977b](https://github.com/robotcodedev/robotcode/commit/d60977bb9ccab4b09a6e69b2ba71dd7a2ae5d2f1))
- Remove unused maxProjectFileCount setting ([4f4ad31](https://github.com/robotcodedev/robotcode/commit/4f4ad318d67fe784db13fece70fbd79e3ccedb00))


## [0.68.3](https://github.com/robotcodedev/robotcode/compare/v0.68.2..v0.68.3) - 2024-01-11

### <!-- 1 -->Bug Fixes

#### Language Server

- Generate libdoc spec generation for RFW 7 ([e259c86](https://github.com/robotcodedev/robotcode/commit/e259c869fecbd09379863e214bec778dd902724c))
- Completion in templated test cases should not show keywords and such things ([621c70a](https://github.com/robotcodedev/robotcode/commit/621c70ab36cee35a468b7741e82778eb02355a4a))

#### VS Code

- Open a result file or view documention does not work in CodeSpaces ([0020ddf](https://github.com/robotcodedev/robotcode/commit/0020ddf00c82a3ee325cb4d9a588dcdccaf32c19))


## [0.68.2](https://github.com/robotcodedev/robotcode/compare/v0.68.1..v0.68.2) - 2024-01-10

### <!-- 1 -->Bug Fixes

#### Language Server

- Stabilize workspace diagnostics ([185b551](https://github.com/robotcodedev/robotcode/commit/185b551a88e3b823290da9916d1052dec04dda96))
- Speedup diagnostics, unused references and codelenses updates ([e13641e](https://github.com/robotcodedev/robotcode/commit/e13641e80cd296fd1463152d70e90e234223d9da))
- Langserver that sometimes hangs, 'loop is not running'  or 'lock take to long' messages ([37d8119](https://github.com/robotcodedev/robotcode/commit/37d8119408bd31bb8e0e7381b2509a3cd47cdcbc))

  Rewrote and refactor diagnostics and refreshing part to use normal threads and not async. This should also bring a better performance for bigger projects, but maybe this needs some more optimizations.

- Preventing extensive calls to 'workspace/configuration' through caching ([77db502](https://github.com/robotcodedev/robotcode/commit/77db5024fb7a5fa56fb895e5a3d9a371910c7bf5))
- Goto and implementation sometimes return to many wrong results on import statements ([3798c5e](https://github.com/robotcodedev/robotcode/commit/3798c5ef06ef8b02994b6dbc2ba71ea37fe1b542))
- Correct highlight ranges for hover ([d0e4091](https://github.com/robotcodedev/robotcode/commit/d0e40919ace8ae3d08a3256695212f2723950ffd))


### <!-- 4 -->Refactor

- Move some diagnostics code from langserver package to robot package ([4b3e65c](https://github.com/robotcodedev/robotcode/commit/4b3e65cad56b7029860a35a4e16f496930a4b504))
- Move language_server.robotframework.utils to robotcode.robot package ([6fe4dc0](https://github.com/robotcodedev/robotcode/commit/6fe4dc03408a2fb9c6c21c8db8954f6cb04c825f))
- Move most of langserver...ast_utils to robotcode.robot.utils.ast ([bc96805](https://github.com/robotcodedev/robotcode/commit/bc96805dc8fb813ac4b2fe4e65da79897bf275c4))
- Remove some unneeded code ([65e1775](https://github.com/robotcodedev/robotcode/commit/65e1775fd380b7e6b67a88c327f8961929e9cafb))
#### Language Server

- Rename core.concurrent.FutureEx to Task ([d75eb9a](https://github.com/robotcodedev/robotcode/commit/d75eb9aa7005514c01b3ced5924191ed7cd780ab))
- Remove threaded decorator from rpc methods and introduce a threaded property for the rpc_method decorator ([b478ae3](https://github.com/robotcodedev/robotcode/commit/b478ae3da563fd9af7409c234b55efabb412f8a7))
- Correct refresh handling and remove some unneeded code ([3f3944f](https://github.com/robotcodedev/robotcode/commit/3f3944f630ac6117cdb8a16d7078f9e8ab47e6cc))
- Remove async code from semantic tokens ([3adddd1](https://github.com/robotcodedev/robotcode/commit/3adddd12f75664dc98988402c2597965be7a4bf3))
- Remove async code from rename ([15e409d](https://github.com/robotcodedev/robotcode/commit/15e409dcb67e2fbe0fc6a3479ad1a0f090b3830d))
- Remove async code from diagnostics, selection range, workspace, signature help ([0c38843](https://github.com/robotcodedev/robotcode/commit/0c38843b28cfa5175d65b3eafec3c455afcc3d2f))
- Remove async code from inline value ([4e1b23c](https://github.com/robotcodedev/robotcode/commit/4e1b23cf3fe43d7a602f0c8983879d4e25444ed0))
- Remove async code from inlay hints ([7535bfa](https://github.com/robotcodedev/robotcode/commit/7535bfa68c493e566ee39ef51370e04eda809b5f))
- Remove async code from formatting and some import corrections ([2f25c78](https://github.com/robotcodedev/robotcode/commit/2f25c7805fe1e81589aedf7ee3f420db36ed88c4))
- Remove async code from commands ([58f185b](https://github.com/robotcodedev/robotcode/commit/58f185bd0636a3c1f640372771a66e8b2a33cc06))
- Remove async code from code lens ([204624c](https://github.com/robotcodedev/robotcode/commit/204624cc3fa1662babc929b5067497e820d660d1))
- Move core.utils.threading to core.concurrent and rename some function ([faee359](https://github.com/robotcodedev/robotcode/commit/faee359d0c7e45b7c1d0b44b1b6c1d247fb1d6fe))
- Some parameter renaming ([a2bddf9](https://github.com/robotcodedev/robotcode/commit/a2bddf94eb69bd2e3238d13484ff3c46df0cc1e2))
- Remove async code from completions ([5009202](https://github.com/robotcodedev/robotcode/commit/5009202eeef47bb67ebac0d21d58244c24f3ae35))
- Remove async code from code actions ([87cb416](https://github.com/robotcodedev/robotcode/commit/87cb416ae2daf390ef49ca0e8016c691faa3ecfe))
- Move local import to global imports in document_symbols ([135b0d4](https://github.com/robotcodedev/robotcode/commit/135b0d4dc1979471a389b3efbf75278325e10139))
- Remove async code from document_highlight and document_symbols, add regression tests for document_symbols ([755daf7](https://github.com/robotcodedev/robotcode/commit/755daf72d1e9ff2a98dbf73e91de28e0a4ade3ac))
- Remove HasExtendCapabilities protocol and implement the method directly, extend threaded decorator ([b76eb0f](https://github.com/robotcodedev/robotcode/commit/b76eb0f4fcdd649232bfddcf7060423c385af92d))
- Implement cancelable threads and remove async code from definition, implementations, hover, folding ([2fae8e3](https://github.com/robotcodedev/robotcode/commit/2fae8e35a54ef0173a7f13cd7016a724587d9958))
- Remove AsyncVisitor code ([c9aaa60](https://github.com/robotcodedev/robotcode/commit/c9aaa6088a86c67b8dec5cb9794efe6c339cc6a5))
- Remove async from robotcode langserver analytics ([1ff1e44](https://github.com/robotcodedev/robotcode/commit/1ff1e44d91f64671e108b35f8fe9f7005a72be5d))

#### RobotCode

- Move threaded decorator to the new core.utils.threading module ([96b897b](https://github.com/robotcodedev/robotcode/commit/96b897b63bdc13aaa0e383a12e74399e0f8caa86))


## [0.68.1](https://github.com/robotcodedev/robotcode/compare/v0.68.0..v0.68.1) - 2023-12-21

### <!-- 1 -->Bug Fixes

#### RobotCode

- Catch OSError's if we can't create the default robot.toml config file ([6dd5f9e](https://github.com/robotcodedev/robotcode/commit/6dd5f9ef69f4d9914e34feccb8566fbfca79b260))
- Add missing robotcode-plugin dependency ([570232d](https://github.com/robotcodedev/robotcode/commit/570232d6c7fa5c9bb2492515c4006d830481e151))


## [0.68.0](https://github.com/robotcodedev/robotcode/compare/v0.67.0..v0.68.0) - 2023-12-20

### <!-- 0 -->Features

- Support for new keyword model changes in RFW 7 ([cb306cb](https://github.com/robotcodedev/robotcode/commit/cb306cb48e4c0d6849324241b944de4d408fbc9e))

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct duplicate items in completions ([023bfd7](https://github.com/robotcodedev/robotcode/commit/023bfd7d9b8784f2c5d4095c408207cffdebba73))


### <!-- 4 -->Refactor

#### Core

- Move some files from core to utils ([92c1911](https://github.com/robotcodedev/robotcode/commit/92c1911b9da41d1368d25e694b84c04bcb56e4b0))

#### Debugger

- Move import in cli handler in to cli function ([c96a321](https://github.com/robotcodedev/robotcode/commit/c96a3210459a018679f1beac2176182c4d493284))


## [0.67.0](https://github.com/robotcodedev/robotcode/compare/v0.66.1..v0.67.0) - 2023-12-13

### <!-- 0 -->Features

#### CLI

- Introduce a command line switch to log to a file ([7a6b8af](https://github.com/robotcodedev/robotcode/commit/7a6b8af39989b5c49e3350fea65f46ed496d0db8))

#### Debugger

- Lighter color for timestamps and respect the `--no-color' command line switch to disable colored output ([6f12eed](https://github.com/robotcodedev/robotcode/commit/6f12eed78b03f5efc19a87c69c46254a8f1b1cc8))


### <!-- 1 -->Bug Fixes

#### Language Server

- Unbound local variable in imports manager ([6d7b3d2](https://github.com/robotcodedev/robotcode/commit/6d7b3d2e53b9e8766891332318b5085a797f40ca))
- Correted folding of IF blocks with multiple ELSE/ELSE IF's ([536db5e](https://github.com/robotcodedev/robotcode/commit/536db5e7038ada87f37a6dce8fbf6d4c0d9fb0a0))

#### VS Code

- Don't show diagnostics when discover tests from a single file ([25024ac](https://github.com/robotcodedev/robotcode/commit/25024ac4151571448b3ca465f90823d1761c336e))


### <!-- 4 -->Refactor

#### Language Server

- Make documents handling synchronous and more threadsafe ([d1c72c2](https://github.com/robotcodedev/robotcode/commit/d1c72c21b8fd7851c9743c23e3b98cd67d0e53dd))

#### Langserver,jsonrpc

- Use concurrent.futures.Future to send request, make register_capabilities syncronous ([41f495b](https://github.com/robotcodedev/robotcode/commit/41f495b6d01300400365009d50123f2cf83914e3))


## [0.66.1](https://github.com/robotcodedev/robotcode/compare/v0.66.0..v0.66.1) - 2023-11-24

### <!-- 1 -->Bug Fixes

#### Language Server

- Show a hint instead an error if there are variables used in a test case name ([6589b71](https://github.com/robotcodedev/robotcode/commit/6589b712c12efc570ab5d395752b3e0acce8fac8))


## [0.66.0](https://github.com/robotcodedev/robotcode/compare/v0.65.1..v0.66.0) - 2023-11-23

### <!-- 0 -->Features

#### Language Server

- Implemented deprecation warning for old [RETURN] setting for RF 7 ([40a5e42](https://github.com/robotcodedev/robotcode/commit/40a5e429f9b73dc834f9693a034bace3ff51d7e9))


### <!-- 1 -->Bug Fixes

#### Language Server

- Handle unwanted warning messages at libdoc generation for robot files ([ce20bf5](https://github.com/robotcodedev/robotcode/commit/ce20bf5124705a4a84de694430ea37a8df64b86f))


## [0.65.1](https://github.com/robotcodedev/robotcode/compare/v0.65.0..v0.65.1) - 2023-11-23

### <!-- 4 -->Refactor

#### Debugger

- Use concurrent.futures for sending request instead of asyncio.Futures ([dc06c2c](https://github.com/robotcodedev/robotcode/commit/dc06c2c5ac079248a6116f1d01cf6da4b8860481))


## [0.65.0](https://github.com/robotcodedev/robotcode/compare/v0.64.1..v0.65.0) - 2023-11-22

### <!-- 0 -->Features

#### Language Server

- Added new return type information of keyword from libdoc to documentation hover ([b91f2ff](https://github.com/robotcodedev/robotcode/commit/b91f2ff5b5a369ac65f36f0222954e29c56ca2f7))
- Support for new VAR statement in RF7 ([2678884](https://github.com/robotcodedev/robotcode/commit/2678884fedce733a3c6a52589c4b5f55fb2beda4))


### <!-- 4 -->Refactor

- Move markdown formatter to robotcode.robot.utils ([5a22bef](https://github.com/robotcodedev/robotcode/commit/5a22bef05d015576742506423b13cd773a4d9c70))
- Some code cleanup and simplifications ([f799fb4](https://github.com/robotcodedev/robotcode/commit/f799fb44090ded0fb0d12b0d4dbef8dbfdc28706))
#### Jsonrpc

- Use concurrent.Futures instead of asyncio.Futures for request ([50384dc](https://github.com/robotcodedev/robotcode/commit/50384dcc94b676c4c8b3a6a7f1e4881104d99999))


## [0.64.1](https://github.com/robotcodedev/robotcode/compare/v0.64.0..v0.64.1) - 2023-11-20

### <!-- 1 -->Bug Fixes

- Correct creating run profiles if you use a single workspace folder ([e5430ec](https://github.com/robotcodedev/robotcode/commit/e5430ec4311b03165bf984eac02ee7f636d6ef9a))

## [0.64.0](https://github.com/robotcodedev/robotcode/compare/v0.63.0..v0.64.0) - 2023-11-19

### <!-- 0 -->Features

#### Language Server

- Add completions and new snippets for the new VAR statement for RF7 ([5631a1b](https://github.com/robotcodedev/robotcode/commit/5631a1bf11f7f3bc368732c06708dda10b80933d))
- Colorize new VAR token for RF7 ([3cd27b2](https://github.com/robotcodedev/robotcode/commit/3cd27b2307f4d5d8aba140bdc0127b7048ca8c68))

#### VS Code

- Support for creating test profiles in vscodes test explorer ([8c0e889](https://github.com/robotcodedev/robotcode/commit/8c0e8893e1dfde90e8f624d7aa256b796dc0c7e3))

  In `launch.json` you can create a new entry with purpose `test-profile` this entry is show in the "run tests" and "debug tests" drop down and can be selected by right click on a test end then "Execute Using Profile..." entry. This profile is then used instead of the default test launch config with the purpose `test`

  Example
  ```jsonc
  {
      "name": "Test Environment",
      "type": "robotcode",
      "purpose": "test-profile",
      "request": "launch",
      "presentation": {
          "hidden": true
      },
      "variables": {
          "TEST_PROFILE_VAR": "TEST_PROFILE_VALUE"
      }
  }
  ```



### <!-- 1 -->Bug Fixes

- Some small glitches in semantic highlightning ([39b658f](https://github.com/robotcodedev/robotcode/commit/39b658fd6acb9378d253e56e32bfea8046482b8b))
- Correct completion of argument types for RF7 ([dbca774](https://github.com/robotcodedev/robotcode/commit/dbca774e4b38aac389d7ac2b1a12fe6cd730157f))
#### CLI

- Add missing dependency ([9c6ed1f](https://github.com/robotcodedev/robotcode/commit/9c6ed1faed00a577dea34e1c1c5fd9146f687a2a))

#### Language Server

- Correct detection of valid nodes in quickfixes for TRY/EXCEPT statements in RF5 ([1bcef86](https://github.com/robotcodedev/robotcode/commit/1bcef867260c607c1fb8719a36d4408b84e138e6))
- Support for clients that do not implement pull diagnostics, e.g. neovim ([ced5372](https://github.com/robotcodedev/robotcode/commit/ced5372267a0cf632f556391b2fcc215dc46016d))
- Signature help and markdown documentation for arguments without type for RF7 ([d67b2a0](https://github.com/robotcodedev/robotcode/commit/d67b2a025416a1e2ea90c20ec0db888794f874a8))


### <!-- 2 -->Documentation

- Correct some docs for CLI interface ([7bc7099](https://github.com/robotcodedev/robotcode/commit/7bc70992d2cdff14c1a6b20b387633a7df40d591))
- Correct some command line descriptions ([c0e2536](https://github.com/robotcodedev/robotcode/commit/c0e2536cb07b087e9929597146fde29b2f4f1a87))

### <!-- 4 -->Refactor

- Some code simplifications ([fbec326](https://github.com/robotcodedev/robotcode/commit/fbec3263054453ba37f8311e0d0f580b695f2565))
- Remove inner imports from analyzer ([470bcff](https://github.com/robotcodedev/robotcode/commit/470bcff25f1121460e146171a48104d9a8e35e7b))
#### CLI

- Move --(no)-diagnostic switch to the discover command ([9ed33c9](https://github.com/robotcodedev/robotcode/commit/9ed33c9944c0064de26e533ee328cf2207f3f30e))


## [0.63.0](https://github.com/robotcodedev/robotcode/compare/v0.62.3..v0.63.0) - 2023-11-12

### <!-- 0 -->Features

- First support for RF 7 ([bd704c2](https://github.com/robotcodedev/robotcode/commit/bd704c2b1f45b906568188cd54b255bb0e15a4f1))

  start implementing #177


### <!-- 1 -->Bug Fixes

#### Language Server

- Simplify code for variables and library completions ([256d7aa](https://github.com/robotcodedev/robotcode/commit/256d7aacee531e4a8f27044f9342d6149a0d4a85))


### <!-- 2 -->Documentation

- Add some new logo ideas ([e468a0f](https://github.com/robotcodedev/robotcode/commit/e468a0f35d01a85378fcdc8da44961189d087985))

### <!-- 4 -->Refactor

- Remove unused code and update dependencies ([4c2d1f7](https://github.com/robotcodedev/robotcode/commit/4c2d1f76cbcf5da56955c143404cf4cf386652d7))
#### VS Code

- Detection and running of python from vscode ([6000edb](https://github.com/robotcodedev/robotcode/commit/6000edb33f9bf9845cadf1a6d2e96e59ccb9e010))


## [0.62.3](https://github.com/robotcodedev/robotcode/compare/v0.62.2..v0.62.3) - 2023-10-31

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct handling of imports containing backslashes, in RobotFramework you have to escape them ([097c28b](https://github.com/robotcodedev/robotcode/commit/097c28bb2ac2e9621bce01a3746cb16edec1a107))
- Correction of escaped characters and variables highlighting in import names ([22ef5f3](https://github.com/robotcodedev/robotcode/commit/22ef5f3e1be3509e2343a3e83f81c07d4ec97a91))


## [0.62.2](https://github.com/robotcodedev/robotcode/compare/v0.62.1..v0.62.2) - 2023-10-28

### <!-- 1 -->Bug Fixes

#### Language Server

- Resolving of ${EXECDIR} and ${CURDIR} corrected ([32a1492](https://github.com/robotcodedev/robotcode/commit/32a1492bb8743a10293a148573424c6efa6153c3))


## [0.62.1](https://github.com/robotcodedev/robotcode/compare/v0.62.0..v0.62.1) - 2023-10-28

### <!-- 1 -->Bug Fixes

#### Language Server

- Single resource file with different relative paths is not seen as same file ([0c2a08f](https://github.com/robotcodedev/robotcode/commit/0c2a08fd18a4073352849316e48e68fa48add490))


## [0.62.0](https://github.com/robotcodedev/robotcode/compare/v0.61.7..v0.62.0) - 2023-10-27

### <!-- 0 -->Features

- Do not use pathlib.Path.resolve because it is slow and we don't need to resolve links ([85c3dc1](https://github.com/robotcodedev/robotcode/commit/85c3dc16245d151c37aac9c9cb87e9fa1a7bb2e2))
#### Language Server

- Support for importing libraries of multiple classes from a module ([35c9775](https://github.com/robotcodedev/robotcode/commit/35c97759718c1a9515000bed7365eec04c4bf16d))


## [0.61.7](https://github.com/robotcodedev/robotcode/compare/v0.61.6..v0.61.7) - 2023-10-25

### <!-- 3 -->Performance

#### Language Server

- Increase performance of visitor a little bit more ([a257b90](https://github.com/robotcodedev/robotcode/commit/a257b9075d87b3e5bceeb74c32cc39d1f848f807))


## [0.61.6](https://github.com/robotcodedev/robotcode/compare/v0.61.5..v0.61.6) - 2023-10-20

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct handling of imports with the same namespace name ([c65e98d](https://github.com/robotcodedev/robotcode/commit/c65e98d3a7c6d09cc86a536fd6cfdc88d35e282e))

  hover, semantic hightlightning, references are aware of the current keyword call namespace if given



### <!-- 4 -->Refactor

#### Language Server

- Make package import relativ ([91513c5](https://github.com/robotcodedev/robotcode/commit/91513c51b4b9923b1d33fbc0198e9331f2f314aa))


## [0.61.5](https://github.com/robotcodedev/robotcode/compare/v0.61.4..v0.61.5) - 2023-10-19

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct highlight, completion, analyze, etc. keyword calls with `.` that are also valid namespaces ([42fe633](https://github.com/robotcodedev/robotcode/commit/42fe633be64409766f02132eb353b1dd5525d75e))


## [0.61.4](https://github.com/robotcodedev/robotcode/compare/v0.61.3..v0.61.4) - 2023-10-15

### <!-- 1 -->Bug Fixes

#### Language Server

- Complete keywords containing `.` if there is no namespace with the name before the dot ([5fc3104](https://github.com/robotcodedev/robotcode/commit/5fc31043336ec12e12d065c6a7732d462db6115b))

#### Discover

- Normalize tags in tests command and sort tags ([cf1159c](https://github.com/robotcodedev/robotcode/commit/cf1159cf51f2eb95365cc5f489a06de15074aa24))


### <!-- 2 -->Documentation

- Optimize some config descriptions ([88ee386](https://github.com/robotcodedev/robotcode/commit/88ee3863236653c2766ed4d392c4ff4040a70506))

### <!-- 3 -->Performance

#### Language Server

- Speedup Visitor and AsyncVisitor a little bit ([3d8a22d](https://github.com/robotcodedev/robotcode/commit/3d8a22dbfeb801a76a259f351ddd62593b235e76))


## [0.61.3](https://github.com/robotcodedev/robotcode/compare/v0.61.2..v0.61.3) - 2023-10-10

### <!-- 3 -->Performance

#### Core

- Increase performance of dataclasses.from_dict ([a41cfb3](https://github.com/robotcodedev/robotcode/commit/a41cfb3835cc76a1616ad8de71dcdc374b240222))
- Improve perfomance of converting dataclasses to json ([dfb576e](https://github.com/robotcodedev/robotcode/commit/dfb576e2578d8306516400132d6b6d8df4a71e18))


## [0.61.2](https://github.com/robotcodedev/robotcode/compare/v0.61.1..v0.61.2) - 2023-10-07

### <!-- 1 -->Bug Fixes

- Some regression tests ([d36deb4](https://github.com/robotcodedev/robotcode/commit/d36deb460e5226decd64dd4ccc3ea7c793542e82))

## [0.61.1](https://github.com/robotcodedev/robotcode/compare/v0.61.0..v0.61.1) - 2023-10-07

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct handling of `robotcode.robocop.configurations` setting ([9dc690e](https://github.com/robotcodedev/robotcode/commit/9dc690e9376902c08158a632e3fa09fd938d4ae7))


### <!-- 3 -->Performance

- Some more performance corrections for as_dict ([3212c71](https://github.com/robotcodedev/robotcode/commit/3212c7122c19b5b231076c386eb6079499aa1697))

## [0.61.0](https://github.com/robotcodedev/robotcode/compare/v0.60.0..v0.61.0) - 2023-10-07

### <!-- 0 -->Features

#### RobotCode

- Better formatting and include active, selected, enabled state of a profile in `profile list` command ([850c751](https://github.com/robotcodedev/robotcode/commit/850c751a34a96bcc8965b8d08c82dbae5e1e558a))
- Rename `extra-` prefix to `extend-` in robot.toml files ([d4747e2](https://github.com/robotcodedev/robotcode/commit/d4747e256122cfde7556ef28de6e310867ccf3f6))

#### Discovery

- Add more options for discovering tags and tests ([508b517](https://github.com/robotcodedev/robotcode/commit/508b5178c7503525bda7708e191f76b1cddacc7c))


### <!-- 2 -->Documentation

- Update json schema and doc for `robot.toml` file ([f7c0693](https://github.com/robotcodedev/robotcode/commit/f7c0693d0fd6c78cf01b0429a6ad75b5796d7253))

### <!-- 3 -->Performance

- Optimize performance of as_dict for dataclasses ([2b4ce26](https://github.com/robotcodedev/robotcode/commit/2b4ce26abcb91974092019a03e6ddf3edba2b254))

## [0.60.0](https://github.com/robotcodedev/robotcode/compare/v0.59.0..v0.60.0) - 2023-10-04

### <!-- 0 -->Features

#### RobotCode

- Add `Path` to allowed GLOBALS in config expressions ([66aea74](https://github.com/robotcodedev/robotcode/commit/66aea748df4b2861951c8dc2d2a8a22b78c1fefc))
- Introduce plugin spec for configuration classes ([582e360](https://github.com/robotcodedev/robotcode/commit/582e3608f452a4168124a11b23a872c45f8096be))


## [0.59.0](https://github.com/robotcodedev/robotcode/compare/v0.58.0..v0.59.0) - 2023-09-28

### <!-- 0 -->Features

#### Language Server

- All refactorings and quickfixes are now previewable ([40e9d92](https://github.com/robotcodedev/robotcode/commit/40e9d92596e5ae99a7f84e86d7eebd4edb4214c3))

  when you select a quickfix or refactoring with <kbd>CONTROL</kbd>+<kbd>RETURN</kbd> a refactor preview window is shown.



## [0.58.0](https://github.com/robotcodedev/robotcode/compare/v0.57.4..v0.58.0) - 2023-09-26

### <!-- 0 -->Features

#### Language Server

- Code action - extract keyword ([9f92775](https://github.com/robotcodedev/robotcode/commit/9f927752b721d26b8dc7c24434efbe1a5ac9f56a))

#### VS Code

- Update to vscode-languageclient to 9.0, now we need at least a vscode version >=1.82 ([d8591b1](https://github.com/robotcodedev/robotcode/commit/d8591b1a0199be4c884cfe60e89966ee7a675537))


## [0.57.4](https://github.com/robotcodedev/robotcode/compare/v0.57.3..v0.57.4) - 2023-09-24

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct "Create keyword" quick fix to ignore empty lines when inserting text ([12af94d](https://github.com/robotcodedev/robotcode/commit/12af94d0f551bb3265a13c22e434a12cd817bb49))


## [0.57.3](https://github.com/robotcodedev/robotcode/compare/v0.57.2..v0.57.3) - 2023-09-23

### <!-- 1 -->Bug Fixes

#### Language Server

- Only show valid headers in resource and init.robot file at completion ([674040a](https://github.com/robotcodedev/robotcode/commit/674040a4ec0de9d8cf6031796798d7b1a03acfee))
- Some correction at line and file endings for signature help ([782bfe6](https://github.com/robotcodedev/robotcode/commit/782bfe69b7f0828e4d6f952fe6bbe665de10a1c4))


## [0.57.2](https://github.com/robotcodedev/robotcode/compare/v0.57.1..v0.57.2) - 2023-09-20

### <!-- 1 -->Bug Fixes

#### Language Server

- Don't show surround code action if we have selected template arguments ([59a0114](https://github.com/robotcodedev/robotcode/commit/59a01140f8800d5be0caba48e0654dee8de83325))
- Don't show argument completion if the cursor is in a keyword assignment ([3c5a797](https://github.com/robotcodedev/robotcode/commit/3c5a797c37d4c6a3c06f4d87cdb0d01fe2c98146))


## [0.57.1](https://github.com/robotcodedev/robotcode/compare/v0.57.0..v0.57.1) - 2023-09-19

### <!-- 1 -->Bug Fixes

#### Language Server

- Correct some in refactor surrounding quirks at file ends ([082132c](https://github.com/robotcodedev/robotcode/commit/082132cc69df4ab0a96fe834426107cc003dfad8))
- Correct some completion quirks at line or file ends ([080ab83](https://github.com/robotcodedev/robotcode/commit/080ab83a02ba34cfbae55785813b0ffdf40ceb77))


## [0.57.0](https://github.com/robotcodedev/robotcode/compare/v0.56.0..v0.57.0) - 2023-09-17

### <!-- 0 -->Features

- New code action refactor rewrite: surroundings for TRY/EXCEPT/FINALLY ([fdba5b9](https://github.com/robotcodedev/robotcode/commit/fdba5b93cd3b9484eceb73b9eeacbef2769876d2))
#### Language Server

- Improved quickfix `create keyword` can now add keywords to resource files if valid namespace is given ([9499d43](https://github.com/robotcodedev/robotcode/commit/9499d431fd1fb842237948956a42e6f803128a60))
- Quick fixes for code actions are generated for all diagnostics specified in the request, and quick fixes are generated with the name of the variable or keyword in the label. ([c2b8f5a](https://github.com/robotcodedev/robotcode/commit/c2b8f5aa3ac11905b3f8bfe45e89691219f85df9))


### <!-- 4 -->Refactor

#### Language Server

- Move code action `assign result to variable` to refactorings ([b8efd1d](https://github.com/robotcodedev/robotcode/commit/b8efd1d392035e71e303e8d937476d699a421d08))


## [0.56.0](https://github.com/robotcodedev/robotcode/compare/v0.55.1..v0.56.0) - 2023-09-11

### <!-- 0 -->Features

#### Language Server

- New code action quick fix - Add argument ([a21c05b](https://github.com/robotcodedev/robotcode/commit/a21c05be3f767def97d38c9960df8efdade1749c))
- New code action quick fix - create suite variable ([4c03a80](https://github.com/robotcodedev/robotcode/commit/4c03a80f118fdb5547777f62a99546a874d2cfdb))
- New code action quick fixes - assign kw result to variable, create local variable, disable robot code diagnostics for line ([bba00aa](https://github.com/robotcodedev/robotcode/commit/bba00aa3edc9e51a24104221d019798aba211d5d))


### <!-- 2 -->Documentation

- Fix some comments in changelog and add some more todos ([dc71f0e](https://github.com/robotcodedev/robotcode/commit/dc71f0e61618d211a518a3af160c5d30004084b2))

### <!-- 4 -->Refactor

#### Language Server

- Move all error messages to one place ([125c091](https://github.com/robotcodedev/robotcode/commit/125c09116aec4475a9331301fdb636e34f45c11d))


## [0.55.1](https://github.com/robotcodedev/robotcode/compare/v0.55.0..v0.55.1) - 2023-09-06

### <!-- 1 -->Bug Fixes

#### Debugger

- Correct update of test run results when suite teardown fails or is skipped during suite teardown for RF 4.1 ([65d67ca](https://github.com/robotcodedev/robotcode/commit/65d67ca1b4293db3ba2da943c3e77c46233f2181))

  this is a follow up to 80b742e



## [0.55.0](https://github.com/robotcodedev/robotcode/compare/v0.54.3..v0.55.0) - 2023-09-05

### <!-- 0 -->Features

- Support for robocop 4.1.1 code descriptions ([a5a0d4c](https://github.com/robotcodedev/robotcode/commit/a5a0d4c49d8212812cb8d81e2fb55809352a36aa))
#### Language Server

- Better completion for variable imports ([1602b71](https://github.com/robotcodedev/robotcode/commit/1602b71e57f44757fe09de39ab6af48c11bbaf56))


### <!-- 1 -->Bug Fixes

- Correct handling of @ variable and & dictionary arguments in signature help and completion ([4415387](https://github.com/robotcodedev/robotcode/commit/44153873fff9981eda05a07ba2922a625328e756))
- Don't complete arguments for run keywords ([38698ed](https://github.com/robotcodedev/robotcode/commit/38698ed05a5f809f287c9e003d3837e605bab2be))
- Update of RobotCode icon in status bar when Python environment is changed ([161806c](https://github.com/robotcodedev/robotcode/commit/161806c32df5f76d6ca86a441e060024f0eeba17))

### <!-- 4 -->Refactor

- Move code_actions and support unions with enums and string in dataclasses ([b9a3f10](https://github.com/robotcodedev/robotcode/commit/b9a3f10a6ba8a2c9c1f5fc6c1d06d57d9d7c9760))

## [0.54.3](https://github.com/robotcodedev/robotcode/compare/v0.54.2..v0.54.3) - 2023-09-02

### <!-- 1 -->Bug Fixes

#### Language Server

- Dont show values in completions if the token before is an named argument token ([26c6eda](https://github.com/robotcodedev/robotcode/commit/26c6edab9488f9b345cb328c792153a1a2cfb887))
- Change scope name of argument tokens to allow better automatic opening of completions ([4f144c4](https://github.com/robotcodedev/robotcode/commit/4f144c4114d6ed1921143451d47ecfe738a77f1b))
- Correct some styles for semantic highlightning ([89eeeb4](https://github.com/robotcodedev/robotcode/commit/89eeeb4506d8e1730cf8c44dc69f423ad95d0d24))


## [0.54.2](https://github.com/robotcodedev/robotcode/compare/v0.54.1..v0.54.2) - 2023-09-02

### <!-- 1 -->Bug Fixes

- Sorting of completion items on library imports ([5d2c20d](https://github.com/robotcodedev/robotcode/commit/5d2c20d063e1b807a91e086910ebf082834cf800))
#### Language Server

- Escape pipe symbols in keyword argument descriptions in hover ([b3111fe](https://github.com/robotcodedev/robotcode/commit/b3111fe31e4f29fcffdde8d20bbc293e3b951391))

#### VS Code

- Correct highligtning of keyword arguments ([162a0b0](https://github.com/robotcodedev/robotcode/commit/162a0b0fd04c3db41dba1e6f20d3b321a9d306b9))


## [0.54.1](https://github.com/robotcodedev/robotcode/compare/v0.54.0..v0.54.1) - 2023-09-01

### <!-- 1 -->Bug Fixes

- Disable html report for pytest ([8fcb4ed](https://github.com/robotcodedev/robotcode/commit/8fcb4ed0b6f88e876ee6dfeb5bf08f7b8826114a))

## [0.54.0](https://github.com/robotcodedev/robotcode/compare/v0.53.0..v0.54.0) - 2023-09-01

### <!-- 0 -->Features

#### Language Server

- Better signature help and completion of keyword arguments and library import arguments, including completions for type converters like Enums, bools, TypedDict, ... ([dee570b](https://github.com/robotcodedev/robotcode/commit/dee570b98352c4d6aafe1ce5496806fd02fc9254))
- Better argument signatures for completion and signature help ([ed7b186](https://github.com/robotcodedev/robotcode/commit/ed7b18623b7f49180f98672bd7fb2a0781e15b9e))

  don't break between prefix and name of signature



### <!-- 1 -->Bug Fixes

#### Language Server

- Correct end positon of completion range in arguments ([063d105](https://github.com/robotcodedev/robotcode/commit/063d105d6fa2feb94253a9b46a448c2977a168a2))
- Disable directory browsing in documentation server ([18ad3ff](https://github.com/robotcodedev/robotcode/commit/18ad3ff50f7a223bdeed6f58d1cd54386a12664b))


## [0.53.0](https://github.com/robotcodedev/robotcode/compare/v0.52.0..v0.53.0) - 2023-08-27

### <!-- 0 -->Features

#### Language Server

- First version of completion of enums and typed dicts for RF >= 6.1 ([bd39e30](https://github.com/robotcodedev/robotcode/commit/bd39e306a6bdd03610ed5b1b74d8977655042796))

#### Robocop

- With code descriptions in `robocop` diagnostics you can jump directly to the website where the rule is explained ([46125a5](https://github.com/robotcodedev/robotcode/commit/46125a58ad9bbccb8fd2a2763b1e63a6407ef7f3))

  closes  #152



## [0.52.0](https://github.com/robotcodedev/robotcode/compare/v0.51.1..v0.52.0) - 2023-08-25

### <!-- 0 -->Features

#### Debugger

- Add some more informations in verbose mode ([ff87819](https://github.com/robotcodedev/robotcode/commit/ff87819c10f1ceb656ce28d678e9c74f4d0b5810))

#### Language Server

- Inlay hint and signature help now shows the correct parameters and active parameter index, make both work for library and variable imports and show type informations if type hints are defined ([99bc996](https://github.com/robotcodedev/robotcode/commit/99bc996a970e91ec54bdec5a2f371baafd965706))
- Goto, highlight, rename, hover, find references for named arguments ([054d210](https://github.com/robotcodedev/robotcode/commit/054d2101536a205d87b2d7409609cfe5ac1ba6ff))

  rename and goto only works for resource keywords


#### RobotCode

- Internal cli args are now hidden ([934e299](https://github.com/robotcodedev/robotcode/commit/934e299ecbfce3d7ef5a3ca403201499836a32fd))

  If you want to show these args set the environment variable `ROBOTCODE_SHOW_HIDDEN_ARGS` to `true` or `1`.



### <!-- 1 -->Bug Fixes

- Use import nodes to add references for libraries/resources and variables ([f0eb9c9](https://github.com/robotcodedev/robotcode/commit/f0eb9c9b695c02ec42cf3cfa2fb9445b225dc2ea))

## [0.51.0](https://github.com/robotcodedev/robotcode/compare/v0.50.0..v0.51.0) - 2023-08-13

### <!-- 0 -->Features

#### Language Server

- Rework "Analysing", "Hover", "Document Highlight", "Goto" and other things to make them faster, simpler, and easier to extend ([47c1feb](https://github.com/robotcodedev/robotcode/commit/47c1febac2536f653ff662154dcea40c48f860c2))
- Highlight namespace references ([b9cd85a](https://github.com/robotcodedev/robotcode/commit/b9cd85a9e6af908ab3c541eb37b89e1d3c08fc82))

#### Discovery

- Option to show/hide parsing errors/warnings at suite/test discovery ([633b6b5](https://github.com/robotcodedev/robotcode/commit/633b6b54f3026a93821faedd0d48a860ebac6f63))


### <!-- 1 -->Bug Fixes

- Correct hovering, goto, etc. for if/else if/inline if statements ([7250709](https://github.com/robotcodedev/robotcode/commit/7250709ce5b593f8fb14212130a8f876e0d73f67))
#### Language Server

- Correct highlighting of keyword arguments with default value ([c12e1ef](https://github.com/robotcodedev/robotcode/commit/c12e1efac14f6173b2a3058ab0494a5643db3d54))


### <!-- 2 -->Documentation

- Extend some help texts ([f14ec2d](https://github.com/robotcodedev/robotcode/commit/f14ec2d21ddab8d99c96d6494b5bbf79fcae9eee))

### <!-- 4 -->Refactor

#### Language Server

- Speed up hovering for keywords, variables and namespace by using references from code analysis ([4ba77ab](https://github.com/robotcodedev/robotcode/commit/4ba77ab018637fbc7b613281e8dac93054acf19a))


## [0.50.0](https://github.com/robotcodedev/robotcode/compare/v0.49.0..v0.50.0) - 2023-08-08

### <!-- 0 -->Features

#### RobotCode

- Use default configuration if no project root or project configuration is found ([ac1daa1](https://github.com/robotcodedev/robotcode/commit/ac1daa18094472d1d28796c891645607647a2073))

#### Discover

- Tags are now discovered normalized by default ([7f52283](https://github.com/robotcodedev/robotcode/commit/7f52283804a645433ec8f5ae9737eae70f53f8cb))

  you can add --not-normalized cli argument to get the tags not normalized



### <!-- 1 -->Bug Fixes

- Made RobotCode work with Python 3.12 ([aee8378](https://github.com/robotcodedev/robotcode/commit/aee8378b3e8dadb6378a8aff88269d56679b1512))

  Because of some changes in `runtime_protocols', see python doc


### <!-- 2 -->Documentation

- Reorganize docs ([5fb0d61](https://github.com/robotcodedev/robotcode/commit/5fb0d61a835126cec9e6ac68f1ba78b94c46bbd7))

## [0.49.0](https://github.com/robotcodedev/robotcode/compare/v0.48.0..v0.49.0) - 2023-08-03

### <!-- 0 -->Features

- "create keyword" quick fix detects bdd prefixes in the keyword being created and creates keywords without the prefix ([e9b6431](https://github.com/robotcodedev/robotcode/commit/e9b64313a35db2931dc02a5c6f0f95f4a1f9be98))
- Reporting suites and tests with the same name when tests are discovered ([e5d895b](https://github.com/robotcodedev/robotcode/commit/e5d895bff914326fcc99d5c86ea98624a86136b4))
- User default `robot.toml` config file ([55f559d](https://github.com/robotcodedev/robotcode/commit/55f559d36c16fb0e9f371c31d1a2a45d427eb636))

  Instead of defining default settings like output-dir or python-path in VSCode a default config file is created in user directory. The default settings in VSCode are removed, but you can define them here again, but the prefered way is to use the `robot.toml` file in user directory.


### <!-- 1 -->Bug Fixes

- Completion of bdd prefixes optimized ([840778e](https://github.com/robotcodedev/robotcode/commit/840778e801ea360756f76490ffd13091b4a3d908))

  - If you press CTRL+SPACE after a bdd prefix the completion list is shown without typing any other key.
  - if the cursor is at the bdd prefix, other bdd prefix are on the top of the completion list and if you select a bdd prefix only the old prefix is overwritten


### <!-- 2 -->Documentation

- Correct doc strings in model ([e0f8e6b](https://github.com/robotcodedev/robotcode/commit/e0f8e6b166d5d255cbf8498272869d8c2f2b30c4))
- Better help texts for profiles and config commands ([3195451](https://github.com/robotcodedev/robotcode/commit/3195451c449dbf4e15c854c04e8bc9b5f5e45767))

## [0.48.0](https://github.com/robotcodedev/robotcode/compare/v0.47.5..v0.48.0) - 2023-07-30

### <!-- 0 -->Features

- Removed old `robotcode.debugger` script in favor of using `robotcode debug` cli command ([e69b10a](https://github.com/robotcodedev/robotcode/commit/e69b10afce725c796a53b40abc866e2a7b44d655))
#### VS Code

- Added a statusbar item that shows some information about the current robot environment, like version, python version, etc. ([1ff174a](https://github.com/robotcodedev/robotcode/commit/1ff174a42083f902e2ea8fb7a6b93e72fe5edacb))


### <!-- 1 -->Bug Fixes

- Better output for discover info command ([ac6b4a6](https://github.com/robotcodedev/robotcode/commit/ac6b4a67be5e891d14e7cc05b42fe73f210478e8))
- Discover tests for RF 6.1.1 ([b27cbcf](https://github.com/robotcodedev/robotcode/commit/b27cbcfe7ed373b05caf5b5d3b4df93345b6c34d))
- In a test run, errors that occur are first selected in the test case and not in the keyword definition ([a6f0488](https://github.com/robotcodedev/robotcode/commit/a6f0488fd155d3aa01da4568d5154e22b5c57ab5))
- Correct completion of settings with ctrl+space in some situation ([47c1165](https://github.com/robotcodedev/robotcode/commit/47c1165468b5ea9e6705c4f95d1f763afae0fda2))
- Correct update of test run results when suite teardown fails or is skipped during suite teardown ([80b742e](https://github.com/robotcodedev/robotcode/commit/80b742eb1cde1777393475727f15738f58b497a9))

  Unfortunately, if a test has already failed but it is subsequently skipped in the teardown, the error status of VSCode is not set because the skipped status has a lower priority than the failed status. This is a VSCode problem and I can't change it at the moment.

#### RobotCode

- Add missing profile settings to config documentation ([48cb64c](https://github.com/robotcodedev/robotcode/commit/48cb64cd6e04d97dd473598b3b91a0698772de48))


## [0.47.5](https://github.com/robotcodedev/robotcode/compare/v0.47.4..v0.47.5) - 2023-07-20

### <!-- 1 -->Bug Fixes

- Add missing log-level in testcontroller ([a26193f](https://github.com/robotcodedev/robotcode/commit/a26193fe2012b32690146ee364a48d0b95756077))

## [0.47.4](https://github.com/robotcodedev/robotcode/compare/v0.47.3..v0.47.4) - 2023-07-20

### <!-- 1 -->Bug Fixes

- Don't update tests if editing `__init__.robot` files ([d6d1785](https://github.com/robotcodedev/robotcode/commit/d6d178536b807bda04e790bd0a8d62f36e710042))

## [0.47.3](https://github.com/robotcodedev/robotcode/compare/v0.47.2..v0.47.3) - 2023-07-18

### <!-- 1 -->Bug Fixes

- Move to commitizen to create new releases, this is only a dummy release.. ([07b6e4c](https://github.com/robotcodedev/robotcode/commit/07b6e4c96b63b821368c47094c55192b03f33279))
- Reset changlog ([e39b6ce](https://github.com/robotcodedev/robotcode/commit/e39b6ce25183f4353830db8abc8b04ee19ffbbeb))

## [0.47.2](https://github.com/robotcodedev/robotcode/compare/v0.47.1..v0.47.2) - 2023-07-17

### <!-- 1 -->Bug Fixes

- Duplicated header completions if languages contains same words ([d725c6e](https://github.com/robotcodedev/robotcode/commit/d725c6e0dc3f28bfdc6a6407a0d4e38426552e7f))

## [0.47.1](https://github.com/robotcodedev/robotcode/compare/v0.47.0..v0.47.1) - 2023-07-10

### <!-- 1 -->Bug Fixes

- Dont update tests in an opened file twice if file is saved ([390e6d4](https://github.com/robotcodedev/robotcode/commit/390e6d4ae6ad6f3ac46805d03a4034a86030c0c9))
#### Debugger

- Print the result of an keyword in debugger also if it has a variable assignment ([43440d8](https://github.com/robotcodedev/robotcode/commit/43440d82e667aa4cdcbebdad848621f93075f282))


## [0.47.0](https://github.com/robotcodedev/robotcode/compare/v0.46.0..v0.47.0) - 2023-07-10

### <!-- 0 -->Features

- Show deprecation information if using `Force Tags` and `Default Tags` ([f23e5d0](https://github.com/robotcodedev/robotcode/commit/f23e5d0ec2420561589ca24240e449defe7fd373))
- Complete reserved tags in Tags settings ([483b9ac](https://github.com/robotcodedev/robotcode/commit/483b9ac539daca8129945aec31735fd51bf00c6b))

  Closes [ENHANCEMENT] Support Reserved Tags #103

- Show more informations in hint over a variables import ([735a209](https://github.com/robotcodedev/robotcode/commit/735a209801ab3014ec417a583279929a9d88c1b2))
#### Debugger

- Expanding dict and list variables in the variable view of the debugger, this also works in hints over variables, in the watch view and also by evaluating expressions/keywords in the command line of the debugger ([2969379](https://github.com/robotcodedev/robotcode/commit/296937934db8997891df61c600953fc166a2dec2))
- Simple keyword completion in debugger ([6b1ffb6](https://github.com/robotcodedev/robotcode/commit/6b1ffb6ae5738cd9fcf674729baecbb3964d0729))
- Switching between "keyword" and "expression" mode by typing `# exprmode` into debug console (default: keyword mode) ([1cc6680](https://github.com/robotcodedev/robotcode/commit/1cc668006b4d04911cae419d3dd53916c7dd68fe))

  In the expression mode you can enter python expression and ask for variables and so on.
  In keyword mode you can enter robot framework statements, i.e. simple keyword call, IF/FOR/TRY statements, this also allows multi line input

- Debugger does not stop on errors caught in TRY/EXCEPT blocks ([043842c](https://github.com/robotcodedev/robotcode/commit/043842c0709867fdc18d9b4417c7db00cead04fb))

  To stop on these errors you have to switch on the exception breakpoint "Failed Keywords".



### <!-- 1 -->Bug Fixes

- Correct message output in test results view ([b18856f](https://github.com/robotcodedev/robotcode/commit/b18856f1232650e91de3abf1ee8071c750fb689c))
- Stabilize debugger with new vscode version > 1.79 ([d5ad4ba](https://github.com/robotcodedev/robotcode/commit/d5ad4bad6ffe8f210cb6b0f10ca33ccdb269a457))
- Update diagnostic for Robocop 4.0 release after disablers module was rewritten ([6636bfd](https://github.com/robotcodedev/robotcode/commit/6636bfd352927c5721f9c34edfc99b2635b99937))
#### Debugger

- Hide uncaught exceptions now also works correctly for RF >=5 and < 6.1 ([f784613](https://github.com/robotcodedev/robotcode/commit/f7846138d2f668625d1afc2ec46f246338cc084e))
- (re)disable attachPython by default ([26ee516](https://github.com/robotcodedev/robotcode/commit/26ee516b9dda5912fff18d2b9e4f3126b08fcc0a))


## [0.46.0](https://github.com/robotcodedev/robotcode/compare/v0.45.0..v0.46.0) - 2023-07-05

### <!-- 0 -->Features

- Allow multiline RF statements in debug console ([f057131](https://github.com/robotcodedev/robotcode/commit/f057131e956c2b5d3ee1255fd4fe7958ddd8722c))

  This supports also IF/ELSE, FOR, TRY/EXCEPT/FINALLY  statements. Just copy your piece of code to the debug console.
  This also enables the python debugger by default if you run a RF debugging session


### <!-- 1 -->Bug Fixes

- Insted of starting the debugger, start robotcode.cli in debug launcher ([013bdfd](https://github.com/robotcodedev/robotcode/commit/013bdfd485e021a511759a6d98fbc55693b0fafc))
#### Debugger

- Evaluation expressions in RFW >= 6.1 not work correctly ([f7c38d6](https://github.com/robotcodedev/robotcode/commit/f7c38d6dcfc6b96b64d9db7fb1e53393426bf3bf))


## [0.45.0](https://github.com/robotcodedev/robotcode/compare/v0.44.1..v0.45.0) - 2023-06-23

### <!-- 0 -->Features

- Library doc now generates a more RFW-like signature for arguments and argument defaults like ${SPACE}, ${EMPTY}, ${True}, etc. for the respective values ([28a1f8a](https://github.com/robotcodedev/robotcode/commit/28a1f8a7451fb77e91348569065dff8573080330))

### <!-- 1 -->Bug Fixes

- Document_symbols throws exception if section name is empty ([ffce34d](https://github.com/robotcodedev/robotcode/commit/ffce34d7edd3f31f94da76edc090853f98cadb29))
- Change code property for diagnostics for analyse imports to ImportRequiresValue ([222e89c](https://github.com/robotcodedev/robotcode/commit/222e89cdc0391323d89c54ccbc4a54d13eb99b28))

## [0.44.1](https://github.com/robotcodedev/robotcode/compare/v0.44.0..v0.44.1) - 2023-06-21

### <!-- 1 -->Bug Fixes

- Completion and diagnostics for import statements for RF >= 6.1 ([b4e9f03](https://github.com/robotcodedev/robotcode/commit/b4e9f0333633f3d83990137e0a78d61faa029b8c))

## [0.44.0](https://github.com/robotcodedev/robotcode/compare/v0.43.2..v0.44.0) - 2023-06-21

### <!-- 0 -->Features

- Add option to start a debugpy session for debugging purpose ([3f626cc](https://github.com/robotcodedev/robotcode/commit/3f626cc4dd0fdf70191c84e9a63388eb947fa1db))

### <!-- 1 -->Bug Fixes

- Correct handling error in server->client JSON RPC requests ([6e16659](https://github.com/robotcodedev/robotcode/commit/6e166590f7b0096741c085d13ea7437f4674c4a8))
- Detect languageId of not given at "textDocument/didOpen" ([54e329e](https://github.com/robotcodedev/robotcode/commit/54e329e48d456c61063b697b91d4796a8ca34b3e))
- Extension not terminating sometimes on vscode exit ([753c89c](https://github.com/robotcodedev/robotcode/commit/753c89c91373bb5a27881bee23c1fc1e37b41356))

### <!-- 4 -->Refactor

- Make mypy and ruff happy ([0c26cc0](https://github.com/robotcodedev/robotcode/commit/0c26cc076abe2ec678c0e2f40bdcc1accdd8f894))

## [0.43.2](https://github.com/robotcodedev/robotcode/compare/v0.43.1..v0.43.2) - 2023-06-20

### <!-- 1 -->Bug Fixes

- Update testitems does not work correctly if a __init__.robot is changed ([a426e84](https://github.com/robotcodedev/robotcode/commit/a426e840c35a17aba95f0c927b34d338d4a31889))
- Only update test explorer items if file is a valid robot suite ([9461acf](https://github.com/robotcodedev/robotcode/commit/9461acf5e1b1263dd5f61c1b864de83729fd87ec))

## [0.43.1](https://github.com/robotcodedev/robotcode/compare/v0.43.0..v0.43.1) - 2023-06-15

### <!-- 1 -->Bug Fixes

- Intellisense doesn't work when importing yml file with variables #143 ([b19eea1](https://github.com/robotcodedev/robotcode/commit/b19eea19541e5bcfd22b7e4a79f14fb9eb43061a))

## [0.43.0](https://github.com/robotcodedev/robotcode/compare/v0.42.0..v0.43.0) - 2023-06-14

### <!-- 0 -->Features

- Support for importing `.json` files in RF 6.1 ([0f84c4e](https://github.com/robotcodedev/robotcode/commit/0f84c4ec1d9a897aa25ab37fff702f8feea50cf4))
- Enable importing and completion of `.rest`, `.rsrc` and `.json` resource extensions (not parsing) ([3df22dd](https://github.com/robotcodedev/robotcode/commit/3df22ddcb703983b56d0756fef29d06cb2960009))
- Support for new RF 6.1 `--parse-include` option for discovering and executing tests ([607cf8d](https://github.com/robotcodedev/robotcode/commit/607cf8db2777b5d11db89e830131261d60581b0f))
- Support for new `--parseinclude` option in robot config ([dfd88d8](https://github.com/robotcodedev/robotcode/commit/dfd88d87ed08d1065a26eb6f29c1eec6a03272f6))

### <!-- 1 -->Bug Fixes

- Correct highlightning `*** Tasks ***` and `*** Settings ***` ([c4cfdb9](https://github.com/robotcodedev/robotcode/commit/c4cfdb97b1e0b60561573dd94ddac5631093a7c6))
- Hover over a tasks shows "task" in hint and not "test case" ([457f3ae](https://github.com/robotcodedev/robotcode/commit/457f3ae1409d58c5c6c5844c714559ce161fa5dd))
- Checks for robot version 6.1 ([e16f09c](https://github.com/robotcodedev/robotcode/commit/e16f09caa359995c052606a46c9843fba0591731))

## [0.42.0](https://github.com/robotcodedev/robotcode/compare/v0.41.0..v0.42.0) - 2023-06-05

### <!-- 0 -->Features

- Support for new `--parseinclude` option in robot config ([6b84986](https://github.com/robotcodedev/robotcode/commit/6b84986e7109c36b5df81c0ff56f84665a855c6a))

### <!-- 1 -->Bug Fixes

- Compatibility with Python 3.12 ([3ec4d23](https://github.com/robotcodedev/robotcode/commit/3ec4d23cd4e4f2b04d5a1b792131b90ef523b8e8))
- Resolving variable values in hover for RF 6.1 ([0acdd21](https://github.com/robotcodedev/robotcode/commit/0acdd21f24266700d87b046deead43aa33aae90b))

### <!-- 4 -->Refactor

- Fix some mypy warnings ([8622099](https://github.com/robotcodedev/robotcode/commit/862209929bfcfe56dbd6995851858f56bd43c02d))

## [0.41.0](https://github.com/robotcodedev/robotcode/compare/v0.40.0..v0.41.0) - 2023-05-23

### <!-- 0 -->Features

- New `robotcode.robotidy.ignoreGitDir` and `robotcode.robotidy.config` setting to set the config file for _robotidy_ and to ignore git files if searching for config files for _robotidy_ ([a9e9c02](https://github.com/robotcodedev/robotcode/commit/a9e9c023ed62b1fc6ab7d231c9a1c47cfb42330b))

  see also: https://robotidy.readthedocs.io/

- Optimize/speedup searching of files, setting `robotcode.workspace.excludePatterns` now supports gitignore like patterns ([d48b629](https://github.com/robotcodedev/robotcode/commit/d48b629a2ad77c9ee1bb67fc2ff00461b593ace3))

### <!-- 1 -->Bug Fixes

- Patched FileReader for discovery should respect accept_text ([c654af5](https://github.com/robotcodedev/robotcode/commit/c654af57329068e6f5dbd3350aa6f4b7ef2edc46))

### <!-- 4 -->Refactor

- Some optimization in searching files ([5de8a17](https://github.com/robotcodedev/robotcode/commit/5de8a17ecc4d8c0a57e5b3716a88c86427963618))

## [0.40.0](https://github.com/robotcodedev/robotcode/compare/v0.39.0..v0.40.0) - 2023-05-17

### <!-- 0 -->Features

- Show argument infos for dynamic variables imports ([94b21fb](https://github.com/robotcodedev/robotcode/commit/94b21fb08ebd3177668a7a1f20aa27d160060515))

### <!-- 1 -->Bug Fixes

- Wrong values for command line vars ([3720109](https://github.com/robotcodedev/robotcode/commit/37201094d0a1bf10fe8ba6a66a0f08c210b9ca8a))

## [0.39.0](https://github.com/robotcodedev/robotcode/compare/v0.38.0..v0.39.0) - 2023-05-16

### <!-- 0 -->Features

- New command `RobotCode: Select Execution Profiles` ([78f5548](https://github.com/robotcodedev/robotcode/commit/78f554899a0c50c82deeac07fc921128beef778c))
- Language server now is a robotcode cli plugin and can use config files and execution profiles ([12308bb](https://github.com/robotcodedev/robotcode/commit/12308bbed1585b62885a8d699d8969a1310b7db3))

### <!-- 2 -->Documentation

- Update config documentation ([b188b27](https://github.com/robotcodedev/robotcode/commit/b188b276f4fd1c7b65c01585127f04e5a214aee6))

## [0.38.0](https://github.com/robotcodedev/robotcode/compare/v0.37.1..v0.38.0) - 2023-05-15

### <!-- 0 -->Features

- New command `discover tags` ([a8fbb22](https://github.com/robotcodedev/robotcode/commit/a8fbb22baaa1a667c786fb8c71c50cd76b6d6bc4))

### <!-- 1 -->Bug Fixes

- Bring output console into view if robotcode discovery fails ([8bcc147](https://github.com/robotcodedev/robotcode/commit/8bcc1477b1315a7bd385d159346dd6ca95c0e57f))
- Use dispose instead of stop to exit language server instances ([5aba99b](https://github.com/robotcodedev/robotcode/commit/5aba99b1ad551132e8f86c138cca28694dfec545))

### <!-- 4 -->Refactor

- Fix some ruff warnings ([1161451](https://github.com/robotcodedev/robotcode/commit/11614517b922652d7475b21ac33d2d2989a62ce0))

## [0.37.1](https://github.com/robotcodedev/robotcode/compare/v0.37.0..v0.37.1) - 2023-05-11

### <!-- 1 -->Bug Fixes

#### Discover

- Wrong filename in diagnostics message on update single document ([dee91c4](https://github.com/robotcodedev/robotcode/commit/dee91c42a01f012efbf5e24a233fb80895ce0910))


## [0.37.0](https://github.com/robotcodedev/robotcode/compare/v0.36.0..v0.37.0) - 2023-05-10

### <!-- 0 -->Features

- Reintroduce of updating the tests when typing ([94053fc](https://github.com/robotcodedev/robotcode/commit/94053fca5ad40300c8e57bebbecc2523b7d26d94))
- Test discovery now runs in a separate process with the `robotcode discover` command, this supports also prerunmodifiers and RF 6.1 custom parsers ([ee5f0fb](https://github.com/robotcodedev/robotcode/commit/ee5f0fb8dd70232cc50b78e73b180adb906c57d2))

### <!-- 1 -->Bug Fixes

- Some correction in completions for robotframework >= 6.1 ([058e187](https://github.com/robotcodedev/robotcode/commit/058e187e587403f39657e5e23276b432996a4b07))
#### Language Server

- Resolving variables as variable import arguments does not work correctly ([a7ba998](https://github.com/robotcodedev/robotcode/commit/a7ba9980279c95eea3bbb6891fa29eb5af26222e))


### <!-- 4 -->Refactor

- Correct some help texts and printing of output ([b225a73](https://github.com/robotcodedev/robotcode/commit/b225a73a4c4e17ddb0e5265c04a052cf6050988b))

## [0.36.0](https://github.com/robotcodedev/robotcode/compare/v0.35.0..v0.36.0) - 2023-05-01

### <!-- 0 -->Features

- Simple `discover all` command ([a1d8b84](https://github.com/robotcodedev/robotcode/commit/a1d8b84349193be58432ec883e1c5dbf0887f64e))

  shows which tests are executed without running them.

- Select run profiles in test explorer ([a7f8408](https://github.com/robotcodedev/robotcode/commit/a7f840801656b96fc5dca68b69a112c17f7a08bc))

## [0.35.0](https://github.com/robotcodedev/robotcode/compare/v0.34.1..v0.35.0) - 2023-04-25

### <!-- 0 -->Features

#### Runner

- Add `run` alias for `robot` command in cli ([9b782cc](https://github.com/robotcodedev/robotcode/commit/9b782ccfa0f8cd74bc5166a0c816e63dc1840796))


### <!-- 1 -->Bug Fixes

#### Debug-launcher

- Switch back to `stdio` communication, because this does not work on Windows with python <3.8 ([6b0e96e](https://github.com/robotcodedev/robotcode/commit/6b0e96efebeec42d014f81d70573fc075a19bd5f))


## [0.34.1](https://github.com/robotcodedev/robotcode/compare/v0.34.0..v0.34.1) - 2023-04-21

### <!-- 1 -->Bug Fixes

- Some code scanning alerts ([61771f8](https://github.com/robotcodedev/robotcode/commit/61771f82ba42100f798a7cf9ae494959ea9af77e))

## [0.34.0](https://github.com/robotcodedev/robotcode/compare/v0.33.0..v0.34.0) - 2023-04-20

### <!-- 0 -->Features

#### Debugger

- Refactored robotcode debugger to support debugging/running tests with robotcode's configurations and profiles, also command line tool changes. ([69131e6](https://github.com/robotcodedev/robotcode/commit/69131e6a65fd82de7db1f445bfd0b6991bfac951))

  The command line `robotcode.debugger` is deprectated and do not support configs and profiles, to use the full feature set use `robotcode debug` to start the debug server.

  By default `robotcode debug` starts a debug session and waits for incoming connections.


#### Runner

- Implement command line options to select tests/tasks/suites by longname ([d2cb7dc](https://github.com/robotcodedev/robotcode/commit/d2cb7dc1daff8932003b013dc1c069356194050c))


### <!-- 1 -->Bug Fixes

- Correct toml json schema urls ([bf4def7](https://github.com/robotcodedev/robotcode/commit/bf4def70e487437c3629085485688c540f792d54))

### <!-- 4 -->Refactor

- Fix some ruff errors ([38aa2d2](https://github.com/robotcodedev/robotcode/commit/38aa2d230ae785719eae86785ed0fd4b66036ee8))
- Create robotcode bundled interface ([1126605](https://github.com/robotcodedev/robotcode/commit/1126605c52fb17993c875358e8e1ddca2a8ea224))

## [0.33.0](https://github.com/robotcodedev/robotcode/compare/v0.32.3..v0.33.0) - 2023-04-09

### <!-- 0 -->Features

- Improved Handling of UTF-16 encoded multibyte characters, e.g. emojis are now handled correctly ([d17e79c](https://github.com/robotcodedev/robotcode/commit/d17e79c258837cc24c9f69f30358c4a7c1adfed9))

### <!-- 1 -->Bug Fixes

- End positions on formatting ([a87ba80](https://github.com/robotcodedev/robotcode/commit/a87ba805ad800f91067c912fa6984605ec1bebe4))

## [0.32.3](https://github.com/robotcodedev/robotcode/compare/v0.32.2..v0.32.3) - 2023-04-07

### <!-- 0 -->Features

#### RobotCode

- Add new command to show informations about configuration setttings ([47216e9](https://github.com/robotcodedev/robotcode/commit/47216e9179a6a1744fee95b3b25d98734281c674))


### <!-- 1 -->Bug Fixes

- Correct formatting with robotframework-tidy, also support tidy 4.0 reruns now, closes #124 ([3b4c0e8](https://github.com/robotcodedev/robotcode/commit/3b4c0e87dec4a1cb62800ccd70c3d7b01b9e7ce9))

### <!-- 2 -->Documentation

- Use markdown style examples in commandline doc ([7575a77](https://github.com/robotcodedev/robotcode/commit/7575a77a73bceeb99ee3a2ffba7e06f8d7072e19))

## [0.32.2](https://github.com/robotcodedev/robotcode/compare/v0.32.1..v0.32.2) - 2023-04-05

### <!-- 1 -->Bug Fixes

- Update git versions script ([fb16818](https://github.com/robotcodedev/robotcode/commit/fb16818b61068659b8607eee585a705d8e2caf26))

## [0.32.1](https://github.com/robotcodedev/robotcode/compare/v0.32.0..v0.32.1) - 2023-04-05

### <!-- 1 -->Bug Fixes

- Dataclasses from dict respects Literals also for Python 3.8 and 3.9 ([73b7b1c](https://github.com/robotcodedev/robotcode/commit/73b7b1c64e6842249d8278d71ccea76f8118b810))

## [0.32.0](https://github.com/robotcodedev/robotcode/compare/v0.31.0..v0.32.0) - 2023-04-05

### <!-- 0 -->Features

- Allow expression for str options, better handling of tag:<pattern>, name:<pattern> options ([d037ddb](https://github.com/robotcodedev/robotcode/commit/d037ddbd9d44ccbb501af3854cf8a7d7df607ddd))
- Add command for robots _testdoc_ ([dd6d758](https://github.com/robotcodedev/robotcode/commit/dd6d7583f5075b35823b83b8a7aa828507904013))

### <!-- 4 -->Refactor

- Switch to src layout ([40d6262](https://github.com/robotcodedev/robotcode/commit/40d626280721068aed09d84181b3d4c5b31cc9f8))

## [0.31.0](https://github.com/robotcodedev/robotcode/compare/v0.30.0..v0.31.0) - 2023-03-30

### <!-- 0 -->Features

- Profiles can now be enabled or disabled, also with a condition. Profiles can now also be selected with a wildcard pattern. ([4282f02](https://github.com/robotcodedev/robotcode/commit/4282f02bab4b483d74d486e983ec9a1f606fd3d7))
- New commands robot, rebot, libdoc for robotcode.runner ([25027fa](https://github.com/robotcodedev/robotcode/commit/25027faf3e3b7bb14596d90dd0ec1f43af922522))
#### RobotCode

- Add commands to get informations about configurations and profiles ([edc4ee5](https://github.com/robotcodedev/robotcode/commit/edc4ee5e5b41f397918b9476ec7e6e09f0bfe53c))


### <!-- 2 -->Documentation

- Introduce mike for versioned documentation ([4c6e9ac](https://github.com/robotcodedev/robotcode/commit/4c6e9ac0830830c80a543bb197b39f19f32a1203))

### <!-- 4 -->Refactor

- Move the config command to robotcode package ([90c6c25](https://github.com/robotcodedev/robotcode/commit/90c6c2545dc6f2077d6aa2f2670a3570d134a673))
- Add more configuration options, update schema, new command config ([5816669](https://github.com/robotcodedev/robotcode/commit/5816669096fc90cfd58f947e361b2e36d725902e))

## [0.30.0](https://github.com/robotcodedev/robotcode/compare/v0.29.0..v0.30.0) - 2023-03-22

### <!-- 0 -->Features

#### Robotcode-runner

- Robotcode-runner now supports all features, but not all robot options are supported ([1b7affb](https://github.com/robotcodedev/robotcode/commit/1b7affbf954dbec8eaf924557272105e59eb5c84))


### <!-- 4 -->Refactor

- Implement robot.toml config file and runner ([cff5c81](https://github.com/robotcodedev/robotcode/commit/cff5c81392c671509a76f4e19bbf0a49775b3e4c))

## [0.29.0](https://github.com/robotcodedev/robotcode/compare/v0.28.4..v0.29.0) - 2023-03-20

### <!-- 0 -->Features

- Support for Refresh Tests button in test explorer ([0b27713](https://github.com/robotcodedev/robotcode/commit/0b277134101f65cd57e6980105137ca7c0faa69f))

## [0.28.4](https://github.com/robotcodedev/robotcode/compare/v0.28.3..v0.28.4) - 2023-03-19

### <!-- 1 -->Bug Fixes

- Update regression tests ([59b782d](https://github.com/robotcodedev/robotcode/commit/59b782d434764a564521832f375ce062ed155842))

## [0.28.3](https://github.com/robotcodedev/robotcode/compare/v0.28.2..v0.28.3) - 2023-03-19

### <!-- 1 -->Bug Fixes

- Correct analysing keywords with embedded arguments for RF >= 6.1 ([ef0b51f](https://github.com/robotcodedev/robotcode/commit/ef0b51f0bae83194a20a45d7cb07a4a6ac2b4f1c))
- Correct discovering for RobotFramework 6.1a1 ([99aa82d](https://github.com/robotcodedev/robotcode/commit/99aa82de7d8b67d6acae1d2131351ff9354c4a4f))

### <!-- 2 -->Documentation

- Start documentation with mkdocs ([381dcfe](https://github.com/robotcodedev/robotcode/commit/381dcfea90d5a2edd1bc3cf4c78d3d6d0c660784))

## [0.28.2](https://github.com/robotcodedev/robotcode/compare/v0.28.1..v0.28.2) - 2023-03-10

### <!-- 1 -->Bug Fixes

- Correct version of robotcode runner ([1ba8590](https://github.com/robotcodedev/robotcode/commit/1ba85902bfe8ab2c737658757e8fc76bf7cd19ca))

## [0.28.1](https://github.com/robotcodedev/robotcode/compare/v0.28.0..v0.28.1) - 2023-03-10

### <!-- 1 -->Bug Fixes

- Source actions are missing in the context menu for versions #129 ([dd6202a](https://github.com/robotcodedev/robotcode/commit/dd6202af03e9ff09a0140d1d0d5da40db20410a8))

## [0.28.0](https://github.com/robotcodedev/robotcode/compare/v0.27.2..v0.28.0) - 2023-03-09

### <!-- 0 -->Features

- Debugger is now started from bundled/tool/debugger if available ([4b04c7a](https://github.com/robotcodedev/robotcode/commit/4b04c7a0524ba7804a7c4c01e1d2107e5ee188ae))

### <!-- 1 -->Bug Fixes

- #125 Robot Code crashes with a variables file containing a Dict[str, Callable] ([7e0b55c](https://github.com/robotcodedev/robotcode/commit/7e0b55c65609ba37c928a636d0b764ddbb2ae57d))
- Return codes for command line tools now uses sys.exit with return codes ([b6ad7dd](https://github.com/robotcodedev/robotcode/commit/b6ad7dd75276e65ffab9c8acb2c24e0750a93791))

### <!-- 2 -->Documentation

- Correct readme's ([f09880b](https://github.com/robotcodedev/robotcode/commit/f09880ba32547e00374a5af2d5e27d19ec83add9))

## [0.27.2](https://github.com/robotcodedev/robotcode/compare/v0.27.1..v0.27.2) - 2023-03-06

### <!-- 1 -->Bug Fixes

- Unknown workspace edit change received at renaming ([48aef63](https://github.com/robotcodedev/robotcode/commit/48aef63b9085cb90fdbdc42d18ae5843c7774d69))
- The debugger no longer requires a dependency on the language server ([c5199ee](https://github.com/robotcodedev/robotcode/commit/c5199ee7111d17f44334464d6a6d24965adb2eea))

### <!-- 4 -->Refactor

- Some big refactoring, introdude robotcode.runner project ([d0f71fe](https://github.com/robotcodedev/robotcode/commit/d0f71feb4ce529e2025ac99079d6fff45803084a))

## [0.27.1](https://github.com/robotcodedev/robotcode/compare/v0.27.0..v0.27.1) - 2023-03-01

### <!-- 2 -->Documentation

- Update badges in README's ([78bbf7a](https://github.com/robotcodedev/robotcode/commit/78bbf7a6cf3e2b79ca6500a576f25e48f2fae7e8))

## [0.27.0](https://github.com/robotcodedev/robotcode/compare/v0.26.2..v0.27.0) - 2023-03-01

### <!-- 0 -->Features

- Split python code into several packages, now for instance robotcode.debugger can be installed standalone ([01ac842](https://github.com/robotcodedev/robotcode/commit/01ac84237fccc40be658e0f35d4f7b00942f8461))

### <!-- 4 -->Refactor

- Introduce bundled/libs/tool folders and move python source to src folder ([478c93a](https://github.com/robotcodedev/robotcode/commit/478c93a4c644856d5b136ccbdcab234ff4f4bac7))

  this is to prepare the splitting of one big python package to several smaller packages, i.e. to install the robotcode.debugger standalone without other dependencies


## [0.26.2](https://github.com/robotcodedev/robotcode/compare/v0.26.1..v0.26.2) - 2023-02-25

### <!-- 1 -->Bug Fixes

- Publish script ([0d3dd8f](https://github.com/robotcodedev/robotcode/commit/0d3dd8fb7bac3d26cccb5fa60be3d4284bc8d9b7))

## [0.26.1](https://github.com/robotcodedev/robotcode/compare/v0.26.0..v0.26.1) - 2023-02-25

### <!-- 1 -->Bug Fixes

- Github workflow ([a235b86](https://github.com/robotcodedev/robotcode/commit/a235b864139c911cf593b58843c4d2726f770cf5))

## [0.26.0](https://github.com/robotcodedev/robotcode/compare/v0.25.1..v0.26.0) - 2023-02-25

### <!-- 0 -->Features

- Switch to [hatch](https://hatch.pypa.io) build tool and bigger internal refactorings ([bc1c99b](https://github.com/robotcodedev/robotcode/commit/bc1c99bd8d70ec0b6a70257575d9dd4c44793f96))

### <!-- 1 -->Bug Fixes

- Correct error message if variable import not found ([a4b8fbb](https://github.com/robotcodedev/robotcode/commit/a4b8fbb6d830dfb92c59b17b7ac14fafe88558ed))

### <!-- 2 -->Documentation

- Add python badges to README ([c0ec329](https://github.com/robotcodedev/robotcode/commit/c0ec3290b80714ff73528082a3fd2825f1c01f59))
- Add some badges to readme and reorder the chapters ([22120f1](https://github.com/robotcodedev/robotcode/commit/22120f16e973f61b02f04a47c29fbe6d1b5e2283))

### <!-- 4 -->Refactor

- Generate lsp types from json model ([8b7af4f](https://github.com/robotcodedev/robotcode/commit/8b7af4f1081ea4fe9eca6516c762d9dfb2b7ed9e))
- Fix some mypy errors ([9356b32](https://github.com/robotcodedev/robotcode/commit/9356b32420a7049ba50ac76dab8bb288fcf6051a))
- Fix some PIE810 errors ([59848e2](https://github.com/robotcodedev/robotcode/commit/59848e22178a7691732be22932e3562b44fdab02))
- Simplify some code ([9403f72](https://github.com/robotcodedev/robotcode/commit/9403f723526e9a1ffa7067023427f95a59ab736e))
- Fix some flake8-return warnings ([bea720d](https://github.com/robotcodedev/robotcode/commit/bea720dbd17eaaf937168835684b9010dbe57921))
- Fix some pytest ruff warning ([b2bff02](https://github.com/robotcodedev/robotcode/commit/b2bff02083cc16682de237390d9880a4010db051))
- Use `list` over useless lambda in default_factories ([930fa46](https://github.com/robotcodedev/robotcode/commit/930fa466c46d6822b670459b1d1574d92bc56878))
- Change logger calls with an f-string to use lambdas ([cc555e1](https://github.com/robotcodedev/robotcode/commit/cc555e1953a88a8857d69f259c07ed9b8e66434e))
- Replace *Generator with *Iterator ([cd96b1d](https://github.com/robotcodedev/robotcode/commit/cd96b1dd35fe5b57fd5442c107d3ee43aa87b370))
- Fix some ruff errors and warnings, disable isort in precommit ([c144250](https://github.com/robotcodedev/robotcode/commit/c1442503d3d899c7108bfbceef17943e823e92ba))
#### Robotlangserver

- Workspace rpc methods are now running threaded ([8f8f2b9](https://github.com/robotcodedev/robotcode/commit/8f8f2b946e6fa97b6b934e8a6db30128a5351e7c))
- Optimize test discovering ([4949ba6](https://github.com/robotcodedev/robotcode/commit/4949ba6b3e6dce7f00624586fcb5db2f0a630ad1))


## [0.25.1](https://github.com/robotcodedev/robotcode/compare/v0.25.0..v0.25.1) - 2023-01-24

### <!-- 1 -->Bug Fixes

#### VS Code

- In long test runs suites with failed tests are still marked as running even though they are already finished ([942addf](https://github.com/robotcodedev/robotcode/commit/942addf005878bab9983603cd85429283eee4c6e))


### <!-- 4 -->Refactor

- Add `type` parameter to end_output_group ([299658f](https://github.com/robotcodedev/robotcode/commit/299658f153738e7c7b004a61af19eb8154e53df2))

## [0.25.0](https://github.com/robotcodedev/robotcode/compare/v0.24.4..v0.25.0) - 2023-01-24

### <!-- 0 -->Features

#### Debugger

- New setting for `outputTimestamps` in launch and workspace configuration to enable/disable timestamps in debug console ([e3ed581](https://github.com/robotcodedev/robotcode/commit/e3ed581f99d92f2e00c1cae443b98d9d255b638b))


## [0.24.4](https://github.com/robotcodedev/robotcode/compare/v0.24.3..v0.24.4) - 2023-01-23

### <!-- 1 -->Bug Fixes

#### Debugger

- Show error/warning messages of python logger in debug console ([665a3ff](https://github.com/robotcodedev/robotcode/commit/665a3ffd22f28ef73bb48aa63ceaeb831b6f4ffe))


## [0.24.3](https://github.com/robotcodedev/robotcode/compare/v0.24.2..v0.24.3) - 2023-01-23

### <!-- 1 -->Bug Fixes

- Set env and pythonpath erlier in lifecycle to prevent that sometime analyses fails because of python path is not correct ([4183391](https://github.com/robotcodedev/robotcode/commit/41833917d2311b33effa1dc2e8f654b0982c439c))

## [0.24.2](https://github.com/robotcodedev/robotcode/compare/v0.24.1..v0.24.2) - 2023-01-20

### <!-- 1 -->Bug Fixes

#### Robotlangserver

- Retun correct robot framework version test ([e786b76](https://github.com/robotcodedev/robotcode/commit/e786b76144718b2773ae7d0516a88969e8a6b647))


## [0.24.1](https://github.com/robotcodedev/robotcode/compare/v0.24.0..v0.24.1) - 2023-01-20

### <!-- 1 -->Bug Fixes

- Start diagnostics only when the language server is fully initialized ([d2bd3db](https://github.com/robotcodedev/robotcode/commit/d2bd3db3f6e4ce978fb32231d68764367426e7eb))
#### Robotlangserver

- Robot version string is incorrectly parsed if version has no patch ([d1afe4d](https://github.com/robotcodedev/robotcode/commit/d1afe4d6f1c10740f6ac850526b1f357653c95d2))

  correct can't get namespace diagnostics ''>=' not supported between instances of 'NoneType' and 'int'' sometimes happens



## [0.24.0](https://github.com/robotcodedev/robotcode/compare/v0.23.0..v0.24.0) - 2023-01-16

### <!-- 0 -->Features

#### Robotlangserver

- Create undefined keywords in the same file ([c607c3f](https://github.com/robotcodedev/robotcode/commit/c607c3f10b5d9382285e1bfeffdd81992336bab2))


### <!-- 4 -->Refactor

- Prepare create keywords quickfix ([b34c8bf](https://github.com/robotcodedev/robotcode/commit/b34c8bfa80be6ebe08e25e239983b18a53c81bea))
- Introduce asyncio.RLock ([ab918db](https://github.com/robotcodedev/robotcode/commit/ab918db596d0502a4666816589b1674d99cbef18))

## [0.23.0](https://github.com/robotcodedev/robotcode/compare/v0.22.1..v0.23.0) - 2023-01-13

### <!-- 0 -->Features

#### Robotlangserver

- Highlight named args in library imports ([63b93af](https://github.com/robotcodedev/robotcode/commit/63b93af853c0b54628e6bf59a6cc54fa77d97c8d))


### <!-- 1 -->Bug Fixes

#### Robotlangserver

- Remove possible deadlock in completion ([3d17699](https://github.com/robotcodedev/robotcode/commit/3d17699587096ca49711ef98bf1273d710cd8335))


## [0.22.1](https://github.com/robotcodedev/robotcode/compare/v0.22.0..v0.22.1) - 2023-01-13

### <!-- 1 -->Bug Fixes

#### Robotlangserver

- Resolving imports with arguments in diffent files and folders but with same string representation ie. ${curdir}/blah.py now works correctly ([8c0517d](https://github.com/robotcodedev/robotcode/commit/8c0517d2c30ad395b121fde841869c994741151d))
- Generating documentation view with parameters that contains .py at the at does not work ([8210bd9](https://github.com/robotcodedev/robotcode/commit/8210bd9c8bed94e61b475a2c25dc032c7bdb3d68))


## [0.22.0](https://github.com/robotcodedev/robotcode/compare/v0.21.4..v0.22.0) - 2023-01-12

### <!-- 0 -->Features

- Add onEnter rule to split a long line closes #78 ([3efe416](https://github.com/robotcodedev/robotcode/commit/3efe4166829bd65a53dc5b5e3d33173c88258b28))

## [0.21.4](https://github.com/robotcodedev/robotcode/compare/v0.21.3..v0.21.4) - 2023-01-11

### <!-- 1 -->Bug Fixes

#### Robotlangserver

- Remove possible deadlock in Namespace initialization ([27d781c](https://github.com/robotcodedev/robotcode/commit/27d781c6305643b81904e4bf30b8f64a45ffa9ee))


## [0.21.3](https://github.com/robotcodedev/robotcode/compare/v0.21.2..v0.21.3) - 2023-01-10

### <!-- 1 -->Bug Fixes

#### Robotlangserver

- If a lock takes to long, try to cancel the lock ([75e9d66](https://github.com/robotcodedev/robotcode/commit/75e9d66572cdcb5cb144e55541b60e44fa102f7f))


## [0.21.2](https://github.com/robotcodedev/robotcode/compare/v0.21.1..v0.21.2) - 2023-01-10

### <!-- 1 -->Bug Fixes

- Use markdownDescription in settings and launch configurations where needed ([229a4a6](https://github.com/robotcodedev/robotcode/commit/229a4a6c316da5606c16629617e211ecf1a9a6d4))

### <!-- 3 -->Performance

- Massive overall speed improvements ([aee36d7](https://github.com/robotcodedev/robotcode/commit/aee36d7f8a4924b6c35f7055d5d6fa170db6f5de))

  Mainly from changing locks from async.Lock to threading.Lock.
  Extra: more timing statistics in log output


### <!-- 4 -->Refactor

- Remove unneeded code ([a92db4d](https://github.com/robotcodedev/robotcode/commit/a92db4dd75f24cf68ed877322d65d01ab3982c37))

## [0.21.1](https://github.com/robotcodedev/robotcode/compare/v0.21.0..v0.21.1) - 2023-01-07

### <!-- 3 -->Performance

- Caching of variable imports ([9d70610](https://github.com/robotcodedev/robotcode/commit/9d70610b27d3e65177d1389197d2da53bee8e73e))

## [0.21.0](https://github.com/robotcodedev/robotcode/compare/v0.20.0..v0.21.0) - 2023-01-07

### <!-- 0 -->Features

- New setting `robotcode.analysis.cache.ignoredLibraries` to define which libraries should never be cached ([5087c91](https://github.com/robotcodedev/robotcode/commit/5087c912fe2844396c0c2c30222ff215af105731))

### <!-- 1 -->Bug Fixes

- Try to handle unknow documents as .robot files to support resources as .txt or .tsv files ([4fed028](https://github.com/robotcodedev/robotcode/commit/4fed028a42b3705568639469de24615d23152de3))
- Generating keyword specs for keywords with empty lineno ([60d76aa](https://github.com/robotcodedev/robotcode/commit/60d76aa25c9437d1c3029322d3c576738c0406cb))
#### Robotlangserver

- Speedup analyser ([228ae4e](https://github.com/robotcodedev/robotcode/commit/228ae4e9a50b6cb0ad5ecb824f6b45bcb1476258))
- Loading documents hardened ([eab71f8](https://github.com/robotcodedev/robotcode/commit/eab71f87b3e16eeb34e62a811235e5126b2734cf))

  Invalid document don't break loading, initializing and analysing documents and discovering tests



## [0.20.0](https://github.com/robotcodedev/robotcode/compare/v0.19.1..v0.20.0) - 2023-01-06

### <!-- 0 -->Features

#### Debugger

- Add `include` and `exclude` properties to launch configurations ([f4681eb](https://github.com/robotcodedev/robotcode/commit/f4681ebedffa8f43eda31fadc80e3adc16b9572e))

  see --include and --exclude arguments from robot


#### Robotlangserver

- Implement embedded keyword precedence for RF 6.0, this also speedups keyword analysing ([f975be8](https://github.com/robotcodedev/robotcode/commit/f975be8d53ac2ef6a0cbcc8d69dbf815e04312e8))
- Support for robot:private keywords for RF>6.0.0 ([e24603f](https://github.com/robotcodedev/robotcode/commit/e24603f07319e2730fb59d62e1f8f4bc8c245368))

  Show warnings if you use a private keyword and prioritize not private keywords over private keywords

- Show keyword tags in keyword documentation ([c82b60b](https://github.com/robotcodedev/robotcode/commit/c82b60b281c70eb6aa3cb4227a494d1b1f026f12))


### <!-- 1 -->Bug Fixes

- Speedup loading and analysing tests ([9989edf](https://github.com/robotcodedev/robotcode/commit/9989edf8868ddd3360939b93bbaf395aa939bb85))

  Instead of waiting for diagnostics load and analyse documents one by one, load first the documents and then start analysing and discovering in different tasks/threads

#### Robotlangserver

- Ignore parsing errors in test discovery ([470723b](https://github.com/robotcodedev/robotcode/commit/470723b3f064ba496fb59dba600fc099901c0433))

  If a file is not valid, i.e. not in UTF-8 format, test discovery does not stop, but an error is written in the output


#### Vscode-testexplorer

- Correctly combine args and paths in debug configurations ([4b7e7d5](https://github.com/robotcodedev/robotcode/commit/4b7e7d527eb209746ffe1d8ae903d44e79a4d4d3))


### <!-- 4 -->Refactor

#### Debugger

- Move debugger.modifiers one level higher to shorten the commandline ([eea384d](https://github.com/robotcodedev/robotcode/commit/eea384dfc211dad2c629fe824deccd8e82b5120c))

#### Robotlangserver

- Better error messages if converting from json to dataclasses ([29959ea](https://github.com/robotcodedev/robotcode/commit/29959ead0d6a7fb185eec5cebc2c0023ed9f3ac6))


## [0.19.1](https://github.com/robotcodedev/robotcode/compare/v0.19.0..v0.19.1) - 2023-01-05

### <!-- 1 -->Bug Fixes

#### Debugger

- Use default target if there is no target specified in launch config with purpose test ([f633cc5](https://github.com/robotcodedev/robotcode/commit/f633cc5d27e1ad7ab9cc304d3977540365848211))


## [0.19.0](https://github.com/robotcodedev/robotcode/compare/v0.18.0..v0.19.0) - 2023-01-04

### <!-- 0 -->Features

- New command `Clear Cache and Restart Language Servers` ([a2ffdc6](https://github.com/robotcodedev/robotcode/commit/a2ffdc6c63150387a0bd7077cb0d31ce80e36076))

  Clears all cached data i.e library docs and restarts the language servers.

#### Debugger

- Possibility to disable the target `.` in a robotcode launch configurations with `null`, to append your own targets in `args` ([42e528d](https://github.com/robotcodedev/robotcode/commit/42e528d995c63efbdfa6aa3336749f4c92bbc442))

#### Robotlangserver

- New setting `.analysis.cache.saveLocation` where you can specify the location where robotcode saves cached data ([22526e5](https://github.com/robotcodedev/robotcode/commit/22526e532d4294d84e894c4017a6be55deddd5e7))


### <!-- 1 -->Bug Fixes

#### Robotlangserver

- Don't report load workspace progress if progressmode is off ([6dca5e0](https://github.com/robotcodedev/robotcode/commit/6dca5e0f9e8380dc43f5389f7656c3b054da7ede))


## [0.18.0](https://github.com/robotcodedev/robotcode/compare/v0.17.3..v0.18.0) - 2022-12-15

### <!-- 0 -->Features

#### Robotlangserver

- Speedup loading of class and module libraries ([975661c](https://github.com/robotcodedev/robotcode/commit/975661c7d33d2736355be66d7e1b26979ef9b0aa))

  implement a caching mechanism to load and analyse libraries only once or update the cache if the library is changed



### <!-- 1 -->Bug Fixes

#### Robotlangserver

- Update libraries when editing not work ([9adc6c8](https://github.com/robotcodedev/robotcode/commit/9adc6c866d8164a97224bef6a6b21b867355c4ec))


## [0.17.3](https://github.com/robotcodedev/robotcode/compare/v0.17.2..v0.17.3) - 2022-12-11

### <!-- 1 -->Bug Fixes

#### VS Code

- Highlightning comments in text mate mode ([1c1cb9a](https://github.com/robotcodedev/robotcode/commit/1c1cb9a22a02c89dd604418d883b570a68d199b1))
- Some tweaks for better highlightning ([40b7512](https://github.com/robotcodedev/robotcode/commit/40b751223ea77b0c978f9252b3e946c02f9437d6))


### <!-- 3 -->Performance

#### Robotlangserver

- Speedup keyword completion ([6bcaa22](https://github.com/robotcodedev/robotcode/commit/6bcaa22ab492bad7882f5585ae852be87384f497))

  Recalcution of useable keywords is only called if imports changed, this should speedup showing the completion window for keywords

- Refactor some unnecessary async/await methods ([0f8c134](https://github.com/robotcodedev/robotcode/commit/0f8c1349f9bcdeb817f28247afc11c076c9747d0))


## [0.17.2](https://github.com/robotcodedev/robotcode/compare/v0.17.1..v0.17.2) - 2022-12-09

### <!-- 1 -->Bug Fixes

#### VS Code

- Enhance tmLanguage to support thing  like variables, assignments,... better ([ec3fce0](https://github.com/robotcodedev/robotcode/commit/ec3fce062019ba8fa9fcdea2480d6e5be69fccf5))


## [0.17.0](https://github.com/robotcodedev/robotcode/compare/v0.16.0..v0.17.0) - 2022-12-08

### <!-- 0 -->Features

#### VS Code

- Add configuration defaults for `editor.tokenColorCustomizations` and `editor.semanticTokenColorCustomizations` ([ce927d9](https://github.com/robotcodedev/robotcode/commit/ce927d98565be3d481927cea64b8db630cde43d3))

  This leads to better syntax highlighting in Robotframework files.



## [0.16.0](https://github.com/robotcodedev/robotcode/compare/v0.15.1..v0.16.0) - 2022-12-08

### <!-- 0 -->Features

#### VS Code

- Provide better coloring in the debug console. ([c5de757](https://github.com/robotcodedev/robotcode/commit/c5de757ad132fb06a07be80d39c512568a18aa08))
- Add new command `Restart Language Server` ([2b4c9c6](https://github.com/robotcodedev/robotcode/commit/2b4c9c6b90520234e4277364563c37e979c2f409))

  If the extension hangs, you can try to restart only the language server of robot code instead of restart or reload vscode


#### Robotlangserver

- Highlight dictionary keys and values with different colors ([9596540](https://github.com/robotcodedev/robotcode/commit/9596540bfdf2e027c1a1963a2c8b3ae81d42485a))
- Optimization of the analysis of keywords with embedded arguments ([0995a2e](https://github.com/robotcodedev/robotcode/commit/0995a2ee73561162b823d43c5e8077a8daa28053))
- Highlight embedded arguments ([d8b23e4](https://github.com/robotcodedev/robotcode/commit/d8b23e45951e660baea327b3534026da9ee27286))


### <!-- 1 -->Bug Fixes

#### VS Code

- Capitalize commands categories ([b048ca4](https://github.com/robotcodedev/robotcode/commit/b048ca4a5fc3379ff4107ccfeebcbceac2785dd9))

#### Robotlangserver

- Try to hover, goto, ... for keyword with variables in names ([ec2c444](https://github.com/robotcodedev/robotcode/commit/ec2c44457d936431e62fcdb9cb5ef7ca941e3e8b))


## [0.15.0](https://github.com/robotcodedev/robotcode/compare/v0.14.5..v0.15.0) - 2022-12-07

### <!-- 0 -->Features

- Simplifying implementation of discovering of tests ([c8abfae](https://github.com/robotcodedev/robotcode/commit/c8abfae067b3ae98b7330bdacb8027d184df4297))

### <!-- 1 -->Bug Fixes

- Debugger now also supports dictionary expressions ([f80cbd9](https://github.com/robotcodedev/robotcode/commit/f80cbd9ea9c91ebbe2b4f0cba20cfd6fb2d830a1))

  given this example:

  ```robot
  *** Variables ***
  &{DICTIONARY_EXAMPLE1}      output_dir=${OUTPUT DIR}
  ...                         AA=${DUT_IP_ADDRESS_1}
  ...                         ZZ=${{{1:2, 3:4}}}
  ```

  now you can also evaluate expressions like

  ```
  ${DICTIONARY_EXAMPLE1}[output_dir]
  ```

  in the debugger.


## [0.2.0](https://github.com/robotcodedev/robotcode/compare/v0.19.1..v0.2.0) - 2021-09-16

<!-- generated by git-cliff -->
