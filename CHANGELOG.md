# Changelog

All notable changes to this project will be documented in this file. See [conventional commits](https://www.conventionalcommits.org/) for commit guidelines.

## [0.95.0](https://github.com/robotcodedev/robotcode/compare/v0.94.0..v0.95.0) - 2024-10-25

### Bug Fixes

- **analyzer:** Fix some spellings ([b622c42](https://github.com/robotcodedev/robotcode/commit/b622c42d33bc0a41fab8ffa00cdc74cbb7fe98c8))
- **analyzer:** Handle bdd prefixes correctly if keyword is cached ([41ff53f](https://github.com/robotcodedev/robotcode/commit/41ff53f9b3c8cc34f06f34ebeaa7c63691544cb2))
- **analyzer:** Corrected analyzing of `[Return]`, `[Setup]`, `[Teardown]` statement ([4e17c8f](https://github.com/robotcodedev/robotcode/commit/4e17c8fc10814f62799548467efac25c07fbe429))
- **analyzer:** Corrected exception in parsing ForHeaders with invalid variable ([0851d4f](https://github.com/robotcodedev/robotcode/commit/0851d4f6eb7bd90958996cc9c25506712885dca9))
- **analyzer:** Fixed find variables as modules for RF > 5 ([ce787b2](https://github.com/robotcodedev/robotcode/commit/ce787b26d6fab981e432166972429aa2d0d84240))
- **langserver:** Corrected inlay hints for bdd style keyword calls ([77ce8f1](https://github.com/robotcodedev/robotcode/commit/77ce8f1147a4355ea71986408971fca4f441bee5))
- **langserver:** Only update direct references to a file, not imports if something changes ([ea24b06](https://github.com/robotcodedev/robotcode/commit/ea24b061c77de38e1f755a74979d2632970ff032))


### Features

- **analyzer:** Implemented better handling of imports of dynamic libraries ([f6b5b87](https://github.com/robotcodedev/robotcode/commit/f6b5b875daf7cd8d59d0cc46ea24a4d07b02c777))

  - show also errors on in dynamic library API like in `get_keyword_documentation` and `get_keyword_arguments`

- **discover:** Rework discover commands ([87e1dd9](https://github.com/robotcodedev/robotcode/commit/87e1dd96c525c9639b2727681bac22cc4c3ca8cc))

  - show statistics on all commands
  - better differention of tests and tasks
  - new command `tasks` to show only the tasks
  - command tests show only the tests
  - new arguments for `tags` command `--tests` and `--tags`
  - show the type of test or task in test explorer description



### Performance

- **analyzer:** Restructured code for handling bdd prefixes ([96fbe90](https://github.com/robotcodedev/robotcode/commit/96fbe9064fafe0a64f82b0d95b017726d18381fb))
- **analyzer:** Optimized analysing keyword calls ([b1f0f28](https://github.com/robotcodedev/robotcode/commit/b1f0f28dfd0c7f38904ae9ecd0c247f5efec2ab1))
- **analyzer:** Cache embedded arguments and some more little perf tweaks ([3603ff6](https://github.com/robotcodedev/robotcode/commit/3603ff6395d16473fdeb1fca8de910ea3aab8de2))
- **analyzer:** Introduced some caching for parsing variables ([e39afe9](https://github.com/robotcodedev/robotcode/commit/e39afe92ef9dfd44d33537b4dec9bbec3738d116))
- **analyzer:** Implemented DataCache, cache files are now saved in pickle format by default instead of json ([f3ecc22](https://github.com/robotcodedev/robotcode/commit/f3ecc221d0018f9264c958074a7458a6e119b1f6))


## [0.94.0](https://github.com/robotcodedev/robotcode/compare/v0.93.1..v0.94.0) - 2024-10-20

### Bug Fixes

- **analyzer:** Better exception message for invalid command variable files ([f8cb770](https://github.com/robotcodedev/robotcode/commit/f8cb770e68815719d6c70404325c8e7e75956fd6))
- **analyzer:** Decrease load load library timeout and better error messages if time out occurs ([a3fb4a3](https://github.com/robotcodedev/robotcode/commit/a3fb4a3f6011b6d74cc5d9970b5faa1d7a090b1a))
- **docs:** Corrected some things about the inheritance of profiles ([aa50cc7](https://github.com/robotcodedev/robotcode/commit/aa50cc74173671b629ebd2c8c7adbddc5f5ce77d))
- **repl:** Corrected start of repl command if there is no  `robot.toml` with a `path`  setting ([42f96b4](https://github.com/robotcodedev/robotcode/commit/42f96b4fe42e75c52f58734c1767cd7d39307e06))
- Correct analyzing of variables in WhileHeader options ([3a4ee79](https://github.com/robotcodedev/robotcode/commit/3a4ee79651c0d8ba650113e953abee52866f4338))


### Features

- Python 3.13 support ([3874a9c](https://github.com/robotcodedev/robotcode/commit/3874a9cee3116794f510f79c1aa28586ce7b7d06))


### Performance

- **analyze:** Improved performance of code analysis (more then 2x faster) ([2951759](https://github.com/robotcodedev/robotcode/commit/29517592ee6a09d6e36cb89dae81aa6b5669709e))
- **analyze:** Optimize find unused refences (1.5x-2x faster) ([fda1f02](https://github.com/robotcodedev/robotcode/commit/fda1f029a1c9e18b9334ade8ea338e47a953cd30))
- **analyzer:** Move model and token analyzing to the normal analysing stage ([7b3eb0c](https://github.com/robotcodedev/robotcode/commit/7b3eb0cafc5e3843827f3ef5e89b2c75bd986ab4))


### Refactor

- **analyze:** Remove unused/unneeded call to find variable in namespace ([b561607](https://github.com/robotcodedev/robotcode/commit/b5616072372bfe08bd6bcc9c08188ae867aa4a35))


### Testing

- Update tests for RF 7.1.1 ([702c5c9](https://github.com/robotcodedev/robotcode/commit/702c5c9a666f7ab2ae560f6e2c0c0393ece60dc3))


## [0.93.1](https://github.com/robotcodedev/robotcode/compare/v0.93.0..v0.93.1) - 2024-10-09

### Bug Fixes

- **langserver:** Stabilized resolving of variables in test case and keyword documentation ([1bad58f](https://github.com/robotcodedev/robotcode/commit/1bad58fa16e10f0fe5b5f947b7fbea93b5497d8d))


## [0.93.0](https://github.com/robotcodedev/robotcode/compare/v0.92.0..v0.93.0) - 2024-10-08

### Bug Fixes

- Logging of measure_time if log is disabled ([725c739](https://github.com/robotcodedev/robotcode/commit/725c739c0ed01b1249a611605c96e035467f03fa))
- Enable supportsANSIStyling in DAP to reeanble colored output in debug console ([0d5616c](https://github.com/robotcodedev/robotcode/commit/0d5616c33215ed993052d4f50e7ad41a13b21058))
- Corrected highlightning invalid sections for RF7 ([d139ff1](https://github.com/robotcodedev/robotcode/commit/d139ff1f9c309060cc12d1d7499cab1ada4a0b01))


### Features

- **cli:** New command line interface tool - Robot Framework REPL interpreter ([be386d2](https://github.com/robotcodedev/robotcode/commit/be386d244be0b9b85ca4fbe49597985652f066db))

  The new CLI command `repl` introduces an interactive Robot Framework interpreter. You can install it by running `pip install robotcode[repl]` and start it via the command line using `robotcode repl`.

  With this interactive interpreter, you can execute Robot Framework keywords without the need to run a full test suite. By default, all BuiltIn keywords are immediately accessible. To load a library, you can use the `import library` keyword, and for resources or variable files, you can use the corresponding built-in commands `import resource` and `import variables`. The outcome of any keyword execution, along with relevant log details, is displayed directly in the console.

  You can exit the interpreter using the `exit` keyword or by pressing `CTRL`+`D` on Unix-like systems and `CTRL+Z` followed by `ENTER` on Windows.

  At this stage, the implementation is fairly basic, but additional features for the REPL command are planned. This also serves as the first step toward an exciting new feature (spoiler alert!): Robot Framework Notebooks.

- **debugger:** Increase timeouts for debugger to fit better to python debugger timeouts and introduce environment variables to override these timeouts ([63f3e4a](https://github.com/robotcodedev/robotcode/commit/63f3e4ac4d061eed95c95d615c501b2d4430e378))
- **langserver:** Resolve variable in hover for documentation settings in testcases and keywords ([ffa9bdb](https://github.com/robotcodedev/robotcode/commit/ffa9bdb2cdca47b20f56b14deaece59fc49b9a13))
- **vscode:** Introduce RobotCode: Start Terminal REPL command for launching the interactive Robot Framework interpreter directly from VSCode ([f4025fb](https://github.com/robotcodedev/robotcode/commit/f4025fb77c54ea49531c1ec67f1072c0a43c87f9))
- Improved logging with time information ([27d21b5](https://github.com/robotcodedev/robotcode/commit/27d21b599d7d5005e2920a11b47583e32f9a049c))


  - Operations that take a little longer now have an indication of how long they took
  - 2 new command line switches `--log-format` and `--log-style`, see also the Python logging documentation
- `--root` command line argument to specify a project root and disable autodetection of project root ([add4102](https://github.com/robotcodedev/robotcode/commit/add4102594ee73c3a93760eb4a5846358ddf2b1a))
- Add `--no-vcs` command-line option to ignore VCS directories (e.g., .git) when detecting the project root ([d7e28f2](https://github.com/robotcodedev/robotcode/commit/d7e28f2c7c7ffd42ce3d989d1ae8f4e8207d7b81))


  #closes 201


### Performance

- **langserver:** Speedup semantic highlightning a lot ([567ac72](https://github.com/robotcodedev/robotcode/commit/567ac72b393d6e42baadd575195744c5503da297))


### Refactor

- Some performance tweaks ([d3b39be](https://github.com/robotcodedev/robotcode/commit/d3b39be576dd80d757554708fff2cd0bc40354ff))


## [0.92.0](https://github.com/robotcodedev/robotcode/compare/v0.91.0..v0.92.0) - 2024-10-01

### Features

- **analyze:** Allow shortforms of `warning` and `information`, `warn` and `info` in diagnostic modifiers ([f226091](https://github.com/robotcodedev/robotcode/commit/f226091e59b0fff2858de7311d542b903c5bf2d3))
- **config:** Added posibility to allow different tool configs to robot.toml.json schema ([ee256ce](https://github.com/robotcodedev/robotcode/commit/ee256ce38b39ae67ae107bb5fffa5dba8d8d7db4))
- **robot.toml:** Introduce new settings for analysis in robot.toml ([fa37dba](https://github.com/robotcodedev/robotcode/commit/fa37dba7ccfebf9d221b6985a12e460e27209f64))
- **vscode:** Introduce setting for modifing the diagnostics severity ([5cca59f](https://github.com/robotcodedev/robotcode/commit/5cca59fd364cb1c6a8a8c6f0e63a956bca88e366))

  With these settings, you can override the default configuration for all diagnostic messages. By combining file, block, and line diagnostic modifiers, you can precisely control how specific errors are displayed.

  - **`robotcode.analysis.diagnosticModifiers.ignore`**: Suppresses specific diagnostics from being displayed. You can specify one or more error codes, like `MultipleKeywords` or `[multiple-keywords, VariableNotFound]`. Use `*` to ignore all errors and then maybe add specific error codes to other modifiers, such as `information`, to selectively show them.
  - **`robotcode.analysis.diagnosticModifiers.error`**: Treats selected diagnostics as errors.
  - **`robotcode.analysis.diagnosticModifiers.warning`**: Displays chosen diagnostics as warnings.
  - **`robotcode.analysis.diagnosticModifiers.information`**: Shows specified diagnostics as information
  - **`robotcode.analysis.diagnosticModifiers.hint`**: Marks selected diagnostics as hints

  These settings allow you to tailor the diagnostic outputs to meet the specific needs of your project.

- Introduce `Select Python Environment` command and deprecate `robotcode.python` ([be0573d](https://github.com/robotcodedev/robotcode/commit/be0573ddcfaf1100de8058bc6383a013eaf4ee88))


  See [here](https://github.com/microsoft/vscode-python/wiki/Setting-descriptions#pythondefaultinterpreterpath) for an explanation.


## [0.91.0](https://github.com/robotcodedev/robotcode/compare/v0.90.0..v0.91.0) - 2024-09-27

### Bug Fixes

- **vscode:** Tool menu stabilized ([de774fa](https://github.com/robotcodedev/robotcode/commit/de774fafa34269eb448b35fbf403ceb2cda04ed6))
- **vscode:** Correct handling when opening library in keywords view if keyword is loaded twice with a different alias ([ac23751](https://github.com/robotcodedev/robotcode/commit/ac23751087fc9051ace8345ebe58cda88d4eb891))


### Features

- **analyze:** Show messages for InvalidHeader and DeprecatedHeader for RF7 ([518aa12](https://github.com/robotcodedev/robotcode/commit/518aa127d57bfeaf3a0bd1cbfc034394f56f63cb))
- New command `RobotCode: Report Issue` ([94d1efa](https://github.com/robotcodedev/robotcode/commit/94d1efac4edeed7e6117a50448678254e8320c0c))


  with this command you can report an issue directly from vscode to RobotCode's issue tracker


## [0.90.0](https://github.com/robotcodedev/robotcode/compare/v0.89.1..v0.90.0) - 2024-09-16

### Features

- Provide a language status icon and robot tools menu ([7ef83f3](https://github.com/robotcodedev/robotcode/commit/7ef83f3a5d70818ae8947d621ed765d0d3a65ce3))


  Language Status Item:
  ![image](https://github.com/user-attachments/assets/ff0d80d2-0cb5-4942-b828-ccab975cfc00)

  RobotCode Tool Menu
  ![image](https://github.com/user-attachments/assets/a9b15d1f-90c7-41f1-b29b-c9d6a59211e3)

  A short Video:
  https://github.com/user-attachments/assets/b6980485-d7ec-4f6c-88a0-7d1a4e65dc40


## [0.89.1](https://github.com/robotcodedev/robotcode/compare/v0.89.0..v0.89.1) - 2024-09-11

### Bug Fixes

- Corrected parsing of OPTION tokens and variable resolving ([5a8abf2](https://github.com/robotcodedev/robotcode/commit/5a8abf2ea5ae0be9833ecd0ff90658d6e3dbac59))
- Corrected completion of arguments after `...` continuation line ([377aa9d](https://github.com/robotcodedev/robotcode/commit/377aa9d39a185961b2e6c16cb68c7169f490b15f))
- Dont show completion right after `...` ([f24f6a8](https://github.com/robotcodedev/robotcode/commit/f24f6a8691451e34e65a3b6fba1f9d000278c066))


### Testing

- Add some more regression tests ([e2b3c4e](https://github.com/robotcodedev/robotcode/commit/e2b3c4e627df35b214d1d79b103400506d450911))


## [0.89.0](https://github.com/robotcodedev/robotcode/compare/v0.88.0..v0.89.0) - 2024-09-10

### Bug Fixes

- Document highlight should only highlight real references not text references ([a0c184a](https://github.com/robotcodedev/robotcode/commit/a0c184a809fc8128d256c723d11fa49c160bbe32))


### Features

- Enable Robot Framework 7.1 support ([6921c9a](https://github.com/robotcodedev/robotcode/commit/6921c9ac4457a3a8ad5b830584533c1c2ec69a99))
- Variables start with a `_` are no longer beeing reported as unused ([afea114](https://github.com/robotcodedev/robotcode/commit/afea11413ceb96d21397416c37f538102fd259cb))


### Refactor

- Use lambda instead of functools.partial ([1518f71](https://github.com/robotcodedev/robotcode/commit/1518f71acb48dd9e7ccd822da58d3203eebb7774))


  functools.partial with method is deprecated in Python 3.13
- Fix some unused ignores for mypy ([575bbff](https://github.com/robotcodedev/robotcode/commit/575bbff0692fdcffcbc80aa4031450cff8148bd4))


## [0.88.0](https://github.com/robotcodedev/robotcode/compare/v0.87.0..v0.88.0) - 2024-09-07

### Documentation

- Introduce a script that generate the doc for cli tools ([ecb5ec9](https://github.com/robotcodedev/robotcode/commit/ecb5ec9db8740f9b794555b7a408a80670afe926))
- Update some documentation about config and cli ([84553c3](https://github.com/robotcodedev/robotcode/commit/84553c358f6793855a4c7641659c0f7b75a1aba5))
- Update readme ([1e601e3](https://github.com/robotcodedev/robotcode/commit/1e601e3c1542d8358e1d207c5083cbbdfd3c20f2))
- Add a Tip&Tricks page ([dd27480](https://github.com/robotcodedev/robotcode/commit/dd274806324388a7798de2c5e7fd3dcf2794a230))


### Features

- **cli:** Disable console links for RF7.1 if running in VSCode terminal ([5e83537](https://github.com/robotcodedev/robotcode/commit/5e83537c999030780f9b254ca3c5ef7cbee99af3))
- **config:** Add console_links to robot.toml ([3902937](https://github.com/robotcodedev/robotcode/commit/390293755d5f658e5e66a0be25ce1a1560f0483f))
- **langserver:** Corrected and generalized semantic tokenizing if OPTION tokens in except and while statements ([d5a9339](https://github.com/robotcodedev/robotcode/commit/d5a9339e705e50ec3fb1af7e7559a5dd8b2012b5))


### Testing

- Corrected some regression tests ([f4a5d41](https://github.com/robotcodedev/robotcode/commit/f4a5d413995d08c021569c80f035ce5f819f0061))
- Add tests for RF 7.1 ([cbe9fb2](https://github.com/robotcodedev/robotcode/commit/cbe9fb28cbf47fa0ac4eeb5150dfde77f5bccbdc))


## [0.87.0](https://github.com/robotcodedev/robotcode/compare/v0.86.2..v0.87.0) - 2024-08-29

### Bug Fixes

- Correct installing colorama package ([da28477](https://github.com/robotcodedev/robotcode/commit/da28477ad126b40f796d8a9b85c64d0077133dd8))


  this is somehow lost in the lates version of click..


### Features

- **cli:** New command `discover files` ([505f473](https://github.com/robotcodedev/robotcode/commit/505f4736c6d050304719866a3fdc210af5d8596a))

  find all relevant robot framework files in a project.

- **discover:** Add more colors and infos to discover commands ([9e2d6f7](https://github.com/robotcodedev/robotcode/commit/9e2d6f7e8ecc36c2b4916f62153392664dc43ba2))


## [0.86.2](https://github.com/robotcodedev/robotcode/compare/v0.86.1..v0.86.2) - 2024-08-29

### Bug Fixes

- Correction of some type hints that prevent robot code from running with older Python versions ([37e20e3](https://github.com/robotcodedev/robotcode/commit/37e20e395c345c63b6e772e59cebdf6e3844550d))


## [0.86.1](https://github.com/robotcodedev/robotcode/compare/v0.86.0..v0.86.1) - 2024-08-29

### Documentation

- Update about and remove playground ([fd140d0](https://github.com/robotcodedev/robotcode/commit/fd140d046e686f542277699fd5bdd76a54137883))


## [0.86.0](https://github.com/robotcodedev/robotcode/compare/v0.85.0..v0.86.0) - 2024-08-29

### Bug Fixes

- Change detection of win32 ([13a9265](https://github.com/robotcodedev/robotcode/commit/13a92652fa9a42d0eec989bd14cbe5cd3c115596))
- Change detection of win32 ([0dfbd94](https://github.com/robotcodedev/robotcode/commit/0dfbd947baa4eb7dae984fda29e3f5d502a01ea7))
- Correct vscodeignore file ([461bfb1](https://github.com/robotcodedev/robotcode/commit/461bfb1048308959e7ba8de1c9be92a8e9257c29))


  I have over optimized the .vscodeignore file 🥶


### Features

- **robotcode:** Introduce support for `.gitignore` and `.robotignore` during test suite discovery ([74fa480](https://github.com/robotcodedev/robotcode/commit/74fa480cdbe6d03f9d146ea322db4e4e22e242e8))

  Implemented support for `.gitignore` and `.robotignore` files in the discovery process of Robot Framework test suites and test cases.

- **robotcode:** Introduce support for `.gitignore` and `.robotignore` during test suite discovery ([022517f](https://github.com/robotcodedev/robotcode/commit/022517fef7a428a952cf6df7bdd4b7690c9875d5))

  Implemented support for `.gitignore` and `.robotignore` files in the discovery process of Robot Framework test suites and test cases.



## [0.85.0](https://github.com/robotcodedev/robotcode/compare/v0.84.0..v0.85.0) - 2024-08-18

### Bug Fixes

- **langserver:** Corrected coloring of test case/keyword names if names contains line continuations `...` ([a848a93](https://github.com/robotcodedev/robotcode/commit/a848a935567a41804fa20879a5da6016b5a68f0d))


### Documentation

- Some reorganizations ([a49829b](https://github.com/robotcodedev/robotcode/commit/a49829b80b2e0f35eb4c70772bcff0af720fffeb))
- Some more restrucuting ([5b2752f](https://github.com/robotcodedev/robotcode/commit/5b2752f66f2791da51e5d2cc7b063ec8b50fd247))
- Correct RF versions in README ([da0af7b](https://github.com/robotcodedev/robotcode/commit/da0af7b82064304c7ed7c1290bb081eb4b38dde6))
- "Get Started" improved ([c9954ad](https://github.com/robotcodedev/robotcode/commit/c9954ad394069f71eeac23c4b3453588227834ae))


### Features

- **langserver:** Send full completion info if language client does not support `completionItem/resolve` ([4cf0127](https://github.com/robotcodedev/robotcode/commit/4cf01274e70070b3c9eb9e630afe08be57035e37))


## [0.84.0](https://github.com/robotcodedev/robotcode/compare/v0.83.3..v0.84.0) - 2024-08-08

### Bug Fixes

- **debugger:** Corrected handling of local variables in variables inspector ([12ecdd4](https://github.com/robotcodedev/robotcode/commit/12ecdd43376484a40b6cdeb2bca752bc09178fad))
- **debugger:** Corrected start debuggin in internalConsole ([b5124c8](https://github.com/robotcodedev/robotcode/commit/b5124c87265aac26f30ec535ec72770bf258cfbd))
- **debugger:** Corrected start debuggin in internalConsole ([f3fbf20](https://github.com/robotcodedev/robotcode/commit/f3fbf20d01d75264d86c0af4575e98b0cfa7ec5b))
- **robot:** Use casefold for normalizing and remove some local imports in VariableMatcher ([04e12a7](https://github.com/robotcodedev/robotcode/commit/04e12a7ee262177f5bede595baa14e283c3ef4e7))
- **vscode:** Remove `attachPython` from default `launch.json` config ([217653b](https://github.com/robotcodedev/robotcode/commit/217653b6a6c3e78dbbead659880c12c1d5fb4a54))
- **vscode:** Only test cases are reported as queued, started and completed ([1d01f43](https://github.com/robotcodedev/robotcode/commit/1d01f43687a1b2f8428982cadcee7e72e1764738))

  this corrects the number of successful/executed test cases in the upper area of the test explorer

- **vscode:** Remove `attachPython` from default `launch.json` config ([8052f8d](https://github.com/robotcodedev/robotcode/commit/8052f8dfc4e83a8d7e26ef8049c3631881e0dd34))
- **vscode:** Only test cases are reported as queued, started and completed ([f68b8e3](https://github.com/robotcodedev/robotcode/commit/f68b8e34161b4ec977fcae04d891399a53f951fc))

  this corrects the number of successful/executed test cases in the upper area of the test explorer



### Documentation

- **quickstart:** Add quickstart documentation page ([1fdb966](https://github.com/robotcodedev/robotcode/commit/1fdb966038595b79b7081ee94a735a8d76f3098e))
- **quickstart:** Improve quickstart documentation ([a5dd60a](https://github.com/robotcodedev/robotcode/commit/a5dd60a0d1da7fd85cb781eaaaf530e5d8f30e8a))
- Updated config page ([b230689](https://github.com/robotcodedev/robotcode/commit/b23068989da3aaff5ed8dce3b3c6653dceb88eb5))
- Fix some formatting and spelling things ([99d18fe](https://github.com/robotcodedev/robotcode/commit/99d18fe2ffa3f754b125b7ae5f501ae90144c561))


### Features

- **debugger:** Added support for disabling the hiding of debugger threads/tasks. ([049c905](https://github.com/robotcodedev/robotcode/commit/049c90517d36035e3bc86d0271e219e744c5dc7c))

  By setting the ROBOTCODE_DISABLE_HIDDEN_TASKS environment variable to a value not equal to 0, the Robot Code debugger will not be hidden from the Debugpy debugger, allowing you to debug the Robot Code debugger itself.

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


## [0.83.3](https://github.com/robotcodedev/robotcode/compare/v0.83.2..v0.83.3) - 2024-06-20

### Bug Fixes

- **config:** Correct handling of string expression at building the command line in config model ([0a85e3d](https://github.com/robotcodedev/robotcode/commit/0a85e3df465805e6c6ec098d51ee6af43a72ae39))


## [0.83.2](https://github.com/robotcodedev/robotcode/compare/v0.83.1..v0.83.2) - 2024-06-20

### Bug Fixes

- **vscode:** Optimize tmLanguage definition ([166cd25](https://github.com/robotcodedev/robotcode/commit/166cd2536d545c003fd8d7cdd5da31cfb74f94d4))
- **vscode:** Some small corrections for in (semantic) highlightning ([43321f6](https://github.com/robotcodedev/robotcode/commit/43321f652930f91a4a2ab3f8ebd96056076dcdb5))


### Documentation

- Fix some typos ([8a1e91e](https://github.com/robotcodedev/robotcode/commit/8a1e91ed7cec0749e5b62ab99db27fede249ddda))


## [0.83.1](https://github.com/robotcodedev/robotcode/compare/v0.83.0..v0.83.1) - 2024-06-10

### Bug Fixes

- **config:** Correct some markdown syntax error in documentation for config model ([b5fed35](https://github.com/robotcodedev/robotcode/commit/b5fed353f75c679a49e9000a085ebdeca2b9d30d))
- **vscode:** Correct highlightning of line continuations if it contains empty lines or comments lines ([c274c51](https://github.com/robotcodedev/robotcode/commit/c274c5113c55c75ba9496a3337279a11bb7dded0))


### Documentation

- Add a header to config docs ([17ae419](https://github.com/robotcodedev/robotcode/commit/17ae419c237c5e76d4cb2294c676896780dfade1))
- Initial move to vitepress for documentation ([f37d8e7](https://github.com/robotcodedev/robotcode/commit/f37d8e7b3e89eedb04c92fa032b257a7efede43c))
- Setup vitepress project correctly ([882d27c](https://github.com/robotcodedev/robotcode/commit/882d27c8c26af1d69c62c697b76e6c33874fb646))
- Add a logo with text ([1ded4d0](https://github.com/robotcodedev/robotcode/commit/1ded4d0b10cfd137271e867ebfc0bd1c4d7fd12c))


### Testing

- Enable pytest-rerunfailures for unittests ([3b6e0ce](https://github.com/robotcodedev/robotcode/commit/3b6e0cedb30dffd7eb8ff538f09cf93b8a5c9be6))
- Fix tests for Robot Framework version 7.0.1 ([420fee4](https://github.com/robotcodedev/robotcode/commit/420fee4236f7520102862efe0063896ba2761cda))


## [0.83.0](https://github.com/robotcodedev/robotcode/compare/v0.82.3..v0.83.0) - 2024-05-16

### Bug Fixes

- **debugger:** Fix type annotations for python 3.8 ([d2cc421](https://github.com/robotcodedev/robotcode/commit/d2cc42129725566c08bb0fe49f81fb41b2600695))


### Features

- **vscode:** Support for highlighning robot code in markdown code blocks ([b9de061](https://github.com/robotcodedev/robotcode/commit/b9de061f4511dec43c8a6f1b04437a1ccb1bc20d))

  use the at defining the language in a codeblock you can use `robot` or `robotframework` as specifier



## [0.82.3](https://github.com/robotcodedev/robotcode/compare/v0.82.2..v0.82.3) - 2024-05-12

### Bug Fixes

- **analyse:** Allow local variables in [Teardown] ([5bab97c](https://github.com/robotcodedev/robotcode/commit/5bab97c16f13a9041401c27e07782dbde9ce90a0))


### Testing

- Update some tests ([4981eb3](https://github.com/robotcodedev/robotcode/commit/4981eb30300f15ec1db48f9450a91c40546d42b6))


## [0.82.2](https://github.com/robotcodedev/robotcode/compare/v0.82.1..v0.82.2) - 2024-05-10

### Bug Fixes

- **analyse:** Correct handling of keyword arguments in all other keyword settings, regardless of the order of the settings. ([62f9544](https://github.com/robotcodedev/robotcode/commit/62f95443b2f70d92afd16b15c65d9943f4e5f34e))


## [0.82.1](https://github.com/robotcodedev/robotcode/compare/v0.82.0..v0.82.1) - 2024-05-09

### Bug Fixes

- **runner:** `--by-longname` and `--exclude-by-longname` now take into account whether a name for the run was set via `--name` command line argument or in the `name` setting robot.toml ([6f5c719](https://github.com/robotcodedev/robotcode/commit/6f5c719832885e524b72a69d47b2ccaf0608f6f9))


### Refactor

- **debugger:** Some code simplifications ([bc97744](https://github.com/robotcodedev/robotcode/commit/bc977445a5419cdc6ea5ad968298395a538a12bc))


## [0.82.0](https://github.com/robotcodedev/robotcode/compare/v0.81.0..v0.82.0) - 2024-05-05

### Features

- **vscode:** Detection of invalid robot environment now shows a quickpick instead an error message ([95a7630](https://github.com/robotcodedev/robotcode/commit/95a7630e4c8820d8521935847a65eb71bf215097))

  In the case RobotCode will initalize the LanguageServer and detect that environment is not valid, means wrong python version, no robotframework installed, instead an error message pops up a quickpick pops up, where you can do different things, like select a differnt interpreter, create a new venv, ignore this for the moment.
  The advantage of this way is, that this also works with extensions like Pyhton Manger and so on



## [0.81.0](https://github.com/robotcodedev/robotcode/compare/v0.80.0..v0.81.0) - 2024-05-03

### Bug Fixes

- **debugger:** Rework async code in debugger and some other little quitrks in debugger, like hiding the debugger thread when debuggin python code ([d7fe611](https://github.com/robotcodedev/robotcode/commit/d7fe611b1a88a8cac3ea31de4cf7de6a33339ea3))


### Features

- **vscode:** Get debugpy debuggerpackagepath from ms-python.debugpy extension ([9a00d0c](https://github.com/robotcodedev/robotcode/commit/9a00d0c4588bcfe55d5838070dc76410fa060c19))


## [0.80.0](https://github.com/robotcodedev/robotcode/compare/v0.79.0..v0.80.0) - 2024-05-01

### Features

- We have a new icon ([fe78ec8](https://github.com/robotcodedev/robotcode/commit/fe78ec8ce6f7e269f22e9b9dd03b226d2eb96c54))


## [0.79.0](https://github.com/robotcodedev/robotcode/compare/v0.78.4..v0.79.0) - 2024-04-21

### Bug Fixes

- **debugger:** Don't show a message on unsupported rpc commands ([504e091](https://github.com/robotcodedev/robotcode/commit/504e091954b053288701d8b729a9ae2609ed73cc))
- **langserver:** Normalize path handling should not fully resolve symlinks ([0c0198a](https://github.com/robotcodedev/robotcode/commit/0c0198a99374cea5d6801b8590292bef06e87073))


### Features

- **langserver:** Highlight some formatting tags in documentation like bold and italics for englisch language ([4d2cdae](https://github.com/robotcodedev/robotcode/commit/4d2cdae250d797d816366a723eeb56d4e93519a4))
- **vscode:** Add option to disable the vscodes test explorer/execution integration ([9332099](https://github.com/robotcodedev/robotcode/commit/93320995e4cb206e42339247d55c78f9fd327916))


### Testing

- **langserver:** Update regression tests ([4fab1d1](https://github.com/robotcodedev/robotcode/commit/4fab1d1abad6d637ea054ee71d6e4dac836fd85e))


## [0.78.4](https://github.com/robotcodedev/robotcode/compare/v0.78.3..v0.78.4) - 2024-03-20

### Bug Fixes

- **robotcode:** Add missing `robotcode-robot` dependency ([d9cea02](https://github.com/robotcodedev/robotcode/commit/d9cea026d5f28773f1951b4717e014c0e17e15d0))


## [0.78.3](https://github.com/robotcodedev/robotcode/compare/v0.78.2..v0.78.3) - 2024-03-20

### Bug Fixes

- **langserver:** Add missing `robotcode-robot` dependency ([2d1c99d](https://github.com/robotcodedev/robotcode/commit/2d1c99d3cdeef9681f3bbeb4fc4f5df0f5d6de93))


## [0.78.2](https://github.com/robotcodedev/robotcode/compare/v0.78.1..v0.78.2) - 2024-03-19

### Bug Fixes

- **tidy:** Make robotframework-tidy 4.11 running ([569dbe8](https://github.com/robotcodedev/robotcode/commit/569dbe8e1ed264bed2f99c29fdb2d2c949acee30))


## [0.78.1](https://github.com/robotcodedev/robotcode/compare/v0.78.0..v0.78.1) - 2024-03-15

### Bug Fixes

- **analyze:** If a imported resource has import errors it is shown as releated information ([caf8541](https://github.com/robotcodedev/robotcode/commit/caf8541c76e98bbd3ece931be31e00b388634d3a))
- **langserver:** Hovering over `EMPTY` builtin variable respects the type and shows correct empty values ([c8b66c8](https://github.com/robotcodedev/robotcode/commit/c8b66c8fcd05d18ee1d27b79f20bc8d2ff51dc44))
- **profiles:** Profiles inherited by `[profile].inherit` are now merged before the parent profile, unless the `precedence` is set and are only enabled if the parent profile is enabled ([318d780](https://github.com/robotcodedev/robotcode/commit/318d780d9e04b7cfae42a1616af76af56317b320))


## [0.78.0](https://github.com/robotcodedev/robotcode/compare/v0.77.1..v0.78.0) - 2024-03-07

### Bug Fixes

- **vscode:** Some corrections in environment variable highlightning ([8936bfb](https://github.com/robotcodedev/robotcode/commit/8936bfbabfef3b35811db32a757e577010c78e6f))


### Features

- **vscode:** Python syntax highlightning in IF and WHILE statements ([c56def3](https://github.com/robotcodedev/robotcode/commit/c56def3577d1e3024f747695119e5ed6e508d200))

  implements a part of #230



### Testing

- Fix some regression tests ([6001e30](https://github.com/robotcodedev/robotcode/commit/6001e30a1a2e5c3dfb20aeab54ebe6f3dc95f203))


## [0.77.1](https://github.com/robotcodedev/robotcode/compare/v0.77.0..v0.77.1) - 2024-03-06

### Bug Fixes

- **vscode:** Correct some things in bracket highlightning and coloring ([6c584dc](https://github.com/robotcodedev/robotcode/commit/6c584dc5923398f43f6df1e09f1e6e07a12d4b44))


## [0.77.0](https://github.com/robotcodedev/robotcode/compare/v0.76.2..v0.77.0) - 2024-03-05

### Bug Fixes

- **diagnostics:** Resolving variables does not work for builtin vars at library import ([6b97730](https://github.com/robotcodedev/robotcode/commit/6b97730f1791482a9ca9e5dee847cf6a240c98e2))


### Features

- **vscode:** Enable bracket coloring and matching in keyword arguments ([45243e5](https://github.com/robotcodedev/robotcode/commit/45243e589ce44274aae58186071dbf271392d408))
- **vscode:** Python syntax highlightning in `${{}}` expressions ([adf3627](https://github.com/robotcodedev/robotcode/commit/adf36270ab7d39028ee1684e438cc42694af5e67))

  this implements a part of #230



### Testing

- Update regression some tests ([f01d37e](https://github.com/robotcodedev/robotcode/commit/f01d37e42bd9ceab040ff0a3bb4e635902073a51))
- Fix some regression tests ([cb420ad](https://github.com/robotcodedev/robotcode/commit/cb420adb5f7384ebaf9e5f562b4356c5600721f0))


## [0.76.2](https://github.com/robotcodedev/robotcode/compare/v0.76.1..v0.76.2) - 2024-03-01

### Bug Fixes

- **cli:** Add missing plugin package ([66982bd](https://github.com/robotcodedev/robotcode/commit/66982bd2dab0a15081e82ccd1bdcbfd466fcafd7))


## [0.76.1](https://github.com/robotcodedev/robotcode/compare/v0.76.0..v0.76.1) - 2024-02-29

### Bug Fixes

- **core:** Avoid iterator changes during Event.notify when adding or removing new event handlers ([ccc5faf](https://github.com/robotcodedev/robotcode/commit/ccc5fafe40b1e9cbec828f3e976189ba35b0100d))
- **core:** Send cache_invalidate events before and after locking to avoid deadlocks ([5f06377](https://github.com/robotcodedev/robotcode/commit/5f06377bfdd436dd0d1867ab6817cec7521454dc))
- **langserver:** Sometimes an exception in evaluating variables in expressions occurs ([bd9bcfd](https://github.com/robotcodedev/robotcode/commit/bd9bcfde91e61261e4580552e1a3d2c92200d3c5))
- **langserver:** Change keywords treeview rpc methods to non async ([f85621a](https://github.com/robotcodedev/robotcode/commit/f85621ac7f9ccdf22b54e8528a788eea2fd6fbf5))


### Performance

- **langserver:** Optimize analysing and collecting diagnostics ([065db06](https://github.com/robotcodedev/robotcode/commit/065db067b2d80259edd2267e08f40690a5f22a41))


## [0.76.0](https://github.com/robotcodedev/robotcode/compare/v0.75.0..v0.76.0) - 2024-02-19

### Bug Fixes

- **langserver:** Add duplicated imports to references ([e603628](https://github.com/robotcodedev/robotcode/commit/e603628f599c361e13b2f09acf236c30d3822496))
- **langserver:** Correct variable handling from resource imports ([619eee4](https://github.com/robotcodedev/robotcode/commit/619eee4c879fcc586b8b8be396cb141c0488cdf4))
- **vscode:** Correct resolving resource documentation in keywords treeview ([2935bb8](https://github.com/robotcodedev/robotcode/commit/2935bb8b139f88d48217d902fd69bd0233e17dcb))


### Features

- **langserver:** Introduce new setting `robotcode.analysis.cache.ignoreArgumentsForLibrary` ([bb55ff4](https://github.com/robotcodedev/robotcode/commit/bb55ff4e73c2221a2e811c2644538501982906cb))

  This is usefull if you have library that get's variables from a python file that contains complex data like big dictionaries or complex objects that robotcode can't handle.

- **marketplace:** Create a Q&A discussion category on github ([605377d](https://github.com/robotcodedev/robotcode/commit/605377dce9facf12c0d7db296e620a42d7a3e87b))

  as a second way to ask questions and collect answers about robotcode I created a discussion group on the RobotCode github repository

- **vscode:** Use the official python extension api to get informations about python environments ([c032814](https://github.com/robotcodedev/robotcode/commit/c032814bbf1a51a9a9ece79fef51cbcac4a0aa53))

  closes [ENHANCEMENT] Integrate new Python Extension API #215



### Performance

- **analyzer:** Optimization of the analysis of imports, accelerated by a factor of 3 ([321b88d](https://github.com/robotcodedev/robotcode/commit/321b88d33e083bfcef650a491afb518edc811ffe))
- **langserver:** Try to use the last initialized namespace for completions to be a bit more responsive ([2c6fe37](https://github.com/robotcodedev/robotcode/commit/2c6fe37c2e8be9d13aca9eca0d07ff4ee1b85456))


## [0.75.0](https://github.com/robotcodedev/robotcode/compare/v0.74.0..v0.75.0) - 2024-02-13

### Bug Fixes

- **debugger:** Correct wrong lineno informations from robot in listener start_(test/suite/keyword) lineno is `None` ([b4f9c5c](https://github.com/robotcodedev/robotcode/commit/b4f9c5c67f41d7be1170c9da022cd5421a0d20ef))

  If RobotFramework executes a test case, keyword or so, where the line number is not set internally, i.e. `None`, it generates an empty string for the line number in the listener instead of also passing `None`. This rarely happens, but it does occur.

- **debugger:** Fix some small glitches when robot is terminated but the Vscode is not fast enough to notice it ;-) ([5fdb0d7](https://github.com/robotcodedev/robotcode/commit/5fdb0d7f7ab92a131172d38e252810e82e39bad6))


### Features

- **vscode:** Debugger now uses the new `Python Debugger` extension as default debugger for python ([aab6b6d](https://github.com/robotcodedev/robotcode/commit/aab6b6dc3d6f07ce35ddd292605c24df525475be))

  Microsoft rewrites the debugger extension for python and this will be the new standard extension for debugging python code. see [here](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy)



## [0.74.0](https://github.com/robotcodedev/robotcode/compare/v0.73.3..v0.74.0) - 2024-02-12

### Bug Fixes

- **debugger:** Filling zeros are now added to the name of an element so that elements are sorted correctly in the variable view at debugging time ([456ab2c](https://github.com/robotcodedev/robotcode/commit/456ab2c0a30a490e3324d0376cd7fe651a1c2c4a))
- **debugger:** Add `BuiltIn.Run Keyword And Return Status` to the list of keywords that caught exceptions on inner keywords ([add8297](https://github.com/robotcodedev/robotcode/commit/add8297e851f1226dd980fa543bb4c9f124ad441))
- **langserver:** Correct importing variables with the same filename ([e1ac0cb](https://github.com/robotcodedev/robotcode/commit/e1ac0cb5ed439fce3e8c9c2dad19ded4c1726eb4))

  closes [BUG] Variables from variable files are often displayed as not found #214

- **robot:** Handle OSErrors if creating/reading user robot.toml ([470b438](https://github.com/robotcodedev/robotcode/commit/470b438778f2c82c31de08e39b75d7663a5fe504))

  should fix: #187



### Features

- **vscode:** Organize vscode settings in groups ([9bbe68b](https://github.com/robotcodedev/robotcode/commit/9bbe68bcd9ba718d8293c27ee3e64a6d9cd792a4))


## [0.73.3](https://github.com/robotcodedev/robotcode/compare/v0.73.2..v0.73.3) - 2024-02-07

### Bug Fixes

- **discover:** Update run buttons doesn't work on typing ([5f8a890](https://github.com/robotcodedev/robotcode/commit/5f8a8903660f97a2fcc10219ce5962045800febb))


## [0.73.2](https://github.com/robotcodedev/robotcode/compare/v0.73.1..v0.73.2) - 2024-02-07

### Bug Fixes

- **discover:** Discover files when robot arguments with relative files are now read correctly ([d12c67c](https://github.com/robotcodedev/robotcode/commit/d12c67c5ff9a0ebc4a80d507d15666079406d869))


### Documentation

- Update versions in README ([d6c6f09](https://github.com/robotcodedev/robotcode/commit/d6c6f097bad4ffa17e77ba251b6b01e124557ee6))


## [0.73.1](https://github.com/robotcodedev/robotcode/compare/v0.73.0..v0.73.1) - 2024-02-05

### Bug Fixes

- **langserver:** Don't show deprecation message for tags starting with an hyphen in RF7 ([d510a65](https://github.com/robotcodedev/robotcode/commit/d510a653078bbcc6ee1527041c0ce8240c2fbb72))

  fixes [BUG] #212



## [0.73.0](https://github.com/robotcodedev/robotcode/compare/v0.72.0..v0.73.0) - 2024-02-05

### Bug Fixes

- **discover:** Don't show an error if no tests or suite are found ([f57b065](https://github.com/robotcodedev/robotcode/commit/f57b065dd6ecda58176f2af5cb945daed7d1a3ea))
- **vscode:** Trim and shorten long names and descriptions in `Select Configuration Profiles` command ([8abcb67](https://github.com/robotcodedev/robotcode/commit/8abcb67cc697e0fcf3986b551727338887daeeff))
- **vscode:** Stabilized recreation of test explorer items if folders are deleted ([370ff84](https://github.com/robotcodedev/robotcode/commit/370ff847e644ff99d7563a5fbc04b81864dcb5f6))


### Features

- **vscode:** Introduce robotcode contribution point for vscode extensions plugins ([6519687](https://github.com/robotcodedev/robotcode/commit/6519687823cc7d955b4ea30439b4c436f5828b4c))


## [0.72.0](https://github.com/robotcodedev/robotcode/compare/v0.71.1..v0.72.0) - 2024-02-01

### Bug Fixes

- **profiles:** Enhanced error handling if invalid profile is given ([c3d8b07](https://github.com/robotcodedev/robotcode/commit/c3d8b0732cf689953abee2ca007e16f9f7759930))


### Features

- **profiles:** Enhanced handling of environment variables in profile settings ([37fdbb3](https://github.com/robotcodedev/robotcode/commit/37fdbb3108360e20eb44235d0a3130df32d69ff5))

  This update allows the setting, overriding, and utilization of system environment variables in expressions and conditions within the robot.toml configuration files. This enhancement increases the flexibility and adaptability of profile configurations.

- **profiles:** Profiles prefixed with an underscore (`_`) are now automatically hidden in `profiles list` command ([97bf390](https://github.com/robotcodedev/robotcode/commit/97bf3901652892cca71f5a92d98adb151cdfb772))
- **profiles:** A profile can now be hidden and inherit from other profiles ([9cd2ffb](https://github.com/robotcodedev/robotcode/commit/9cd2ffb16ecf139c5c8f2c3cdda2a82cc529b7b5))
- **vscode:** Show profiles from robot.toml in test explorer as test profile ([fcb32a7](https://github.com/robotcodedev/robotcode/commit/fcb32a7a0e7ea40e87e0b459db2cdfd582837b0e))


## [0.71.1](https://github.com/robotcodedev/robotcode/compare/v0.71.0..v0.71.1) - 2024-01-30

### Bug Fixes

- **diagnostics:** Library doc are now correctly unloaded when they are no longer needed ([df6762a](https://github.com/robotcodedev/robotcode/commit/df6762af293b18def1c565ac0856f8b0f3f1295b))
- **vscode:** Remove unneeded "test" badge on the explorer icon ([4f012b4](https://github.com/robotcodedev/robotcode/commit/4f012b44dc4bd0c54de75a510e7512b649f9b8a8))


### Performance

- **langserver:** Remove unneeded double caching of library imports ([3de0882](https://github.com/robotcodedev/robotcode/commit/3de08823a559cc141b7b530384cb5924c8ce7b54))


### Refactor

- **core:** Add locks with default_timouts in documents actions ([5eab74e](https://github.com/robotcodedev/robotcode/commit/5eab74e799ef70a47f9e45a15035424b19bfd3bb))


## [0.71.0](https://github.com/robotcodedev/robotcode/compare/v0.70.0..v0.71.0) - 2024-01-27

### Features

- **analyzer:** Introduce `robotcode.analysis.robot.globalLibrarySearchOrder` setting to specify a global search for libs and resources ([9d34ed4](https://github.com/robotcodedev/robotcode/commit/9d34ed4c9e826465e52f54ebcfee483fb6a740b3))

  Implemented this, because analyse `Set Library Search Order` is to hard.



## [0.70.0](https://github.com/robotcodedev/robotcode/compare/v0.69.0..v0.70.0) - 2024-01-26

### Bug Fixes

- **analyzer:** Correct resolving variables declared with the new VAR statement and a scope ([a259ec6](https://github.com/robotcodedev/robotcode/commit/a259ec6bbc1c8ae4ae2d5169e4f7df184292cc82))
- **debugger:** Fix some things in debugger to better support Robot Framework version 7.0 ([a81695c](https://github.com/robotcodedev/robotcode/commit/a81695c617c41d6e257c5fafee92fd746431a698))
- **langserver:** Correct minimum robot version in version check ([f33c80a](https://github.com/robotcodedev/robotcode/commit/f33c80a730b49667ef5f463733bd32880f44e145))


### Features

- **vscode:** Simple drag'n drop keywords from keywords view to text editor ([6093387](https://github.com/robotcodedev/robotcode/commit/60933878cb5c9b7ed2e46caab67ee32e073dc366))


## [0.69.0](https://github.com/robotcodedev/robotcode/compare/v0.68.5..v0.69.0) - 2024-01-24

### Bug Fixes

- **langserver:** Display the return type in hover only when it is explicitly defined ([3fa09a7](https://github.com/robotcodedev/robotcode/commit/3fa09a7cccee5170b400626876ca6f1bdcb984d8))
- **runner:** Environment vars are evaluated to late ([f74ea4a](https://github.com/robotcodedev/robotcode/commit/f74ea4ac4f98aa04a1c342434b8b0e19559f4ea6))


### Features

- **langserver:** Start the internal HTTP server only on demand ([2254156](https://github.com/robotcodedev/robotcode/commit/2254156c2109cd4fb80a12d615e2b79d78bcda5f))

  You can disable this behaviour with the new option `robotcode.documentationServer.startOnDemand`.

- **vscode:** New keywords tree view in the explorer sidebar ([c0495e6](https://github.com/robotcodedev/robotcode/commit/c0495e680e0d046a9e4937451e9a6b04ac28b268))


## [0.68.5](https://github.com/robotcodedev/robotcode/compare/v0.68.4..v0.68.5) - 2024-01-21

### Bug Fixes

- **langserver:** Filewatcher does not work ([5b72148](https://github.com/robotcodedev/robotcode/commit/5b7214824eb51bab6d1adaec97f177f152fde0bf))


## [0.68.4](https://github.com/robotcodedev/robotcode/compare/v0.68.3..v0.68.4) - 2024-01-20

### Bug Fixes

- **langserver:** Start langserver should not raise a TypeError if startet with no config ([5eca367](https://github.com/robotcodedev/robotcode/commit/5eca367f87d27fd0bfe99023f21db7e137af2c37))


### Documentation

- Change description of package ([f6a4f79](https://github.com/robotcodedev/robotcode/commit/f6a4f79df13b72b36cb5958f467ac3c2d75eae66))
- Create CONTRIBUTING.md and review CODE_OF_CONDUCT.md ([a107b95](https://github.com/robotcodedev/robotcode/commit/a107b95b3fc40b76abfe74972b5f0e254cbfabe4))


### Refactor

- **langserver:** Remove unused maxProjectFileCount setting ([4f4ad31](https://github.com/robotcodedev/robotcode/commit/4f4ad318d67fe784db13fece70fbd79e3ccedb00))
- **langserver:** Move TextDocument from langserver to core package, some other simple refactorings ([d60977b](https://github.com/robotcodedev/robotcode/commit/d60977bb9ccab4b09a6e69b2ba71dd7a2ae5d2f1))
- Move diagnostics helper code to robotcode.robot package ([c94edb3](https://github.com/robotcodedev/robotcode/commit/c94edb306132daddccd6fd9e64343914aafa868a))


## [0.68.3](https://github.com/robotcodedev/robotcode/compare/v0.68.2..v0.68.3) - 2024-01-11

### Bug Fixes

- **langserver:** Completion in templated test cases should not show keywords and such things ([621c70a](https://github.com/robotcodedev/robotcode/commit/621c70ab36cee35a468b7741e82778eb02355a4a))
- **langserver:** Generate libdoc spec generation for RFW 7 ([e259c86](https://github.com/robotcodedev/robotcode/commit/e259c869fecbd09379863e214bec778dd902724c))
- **vscode:** Open a result file or view documention does not work in CodeSpaces ([0020ddf](https://github.com/robotcodedev/robotcode/commit/0020ddf00c82a3ee325cb4d9a588dcdccaf32c19))


## [0.68.2](https://github.com/robotcodedev/robotcode/compare/v0.68.1..v0.68.2) - 2024-01-10

### Bug Fixes

- **langserver:** Correct highlight ranges for hover ([d0e4091](https://github.com/robotcodedev/robotcode/commit/d0e40919ace8ae3d08a3256695212f2723950ffd))
- **langserver:** Goto and implementation sometimes return to many wrong results on import statements ([3798c5e](https://github.com/robotcodedev/robotcode/commit/3798c5ef06ef8b02994b6dbc2ba71ea37fe1b542))
- **langserver:** Preventing extensive calls to 'workspace/configuration' through caching ([77db502](https://github.com/robotcodedev/robotcode/commit/77db5024fb7a5fa56fb895e5a3d9a371910c7bf5))
- **langserver:** Langserver that sometimes hangs, 'loop is not running'  or 'lock take to long' messages ([37d8119](https://github.com/robotcodedev/robotcode/commit/37d8119408bd31bb8e0e7381b2509a3cd47cdcbc))

  Rewrote and refactor diagnostics and refreshing part to use normal threads and not async. This should also bring a better performance for bigger projects, but maybe this needs some more optimizations.

- **langserver:** Speedup diagnostics, unused references and codelenses updates ([e13641e](https://github.com/robotcodedev/robotcode/commit/e13641e80cd296fd1463152d70e90e234223d9da))
- **langserver:** Stabilize workspace diagnostics ([185b551](https://github.com/robotcodedev/robotcode/commit/185b551a88e3b823290da9916d1052dec04dda96))


### Refactor

- **langserver:** Remove async from robotcode langserver analytics ([1ff1e44](https://github.com/robotcodedev/robotcode/commit/1ff1e44d91f64671e108b35f8fe9f7005a72be5d))
- **langserver:** Remove AsyncVisitor code ([c9aaa60](https://github.com/robotcodedev/robotcode/commit/c9aaa6088a86c67b8dec5cb9794efe6c339cc6a5))
- **langserver:** Implement cancelable threads and remove async code from definition, implementations, hover, folding ([2fae8e3](https://github.com/robotcodedev/robotcode/commit/2fae8e35a54ef0173a7f13cd7016a724587d9958))
- **langserver:** Remove HasExtendCapabilities protocol and implement the method directly, extend threaded decorator ([b76eb0f](https://github.com/robotcodedev/robotcode/commit/b76eb0f4fcdd649232bfddcf7060423c385af92d))
- **langserver:** Remove async code from document_highlight and document_symbols, add regression tests for document_symbols ([755daf7](https://github.com/robotcodedev/robotcode/commit/755daf72d1e9ff2a98dbf73e91de28e0a4ade3ac))
- **langserver:** Move local import to global imports in document_symbols ([135b0d4](https://github.com/robotcodedev/robotcode/commit/135b0d4dc1979471a389b3efbf75278325e10139))
- **langserver:** Remove async code from code actions ([87cb416](https://github.com/robotcodedev/robotcode/commit/87cb416ae2daf390ef49ca0e8016c691faa3ecfe))
- **langserver:** Remove async code from completions ([5009202](https://github.com/robotcodedev/robotcode/commit/5009202eeef47bb67ebac0d21d58244c24f3ae35))
- **langserver:** Some parameter renaming ([a2bddf9](https://github.com/robotcodedev/robotcode/commit/a2bddf94eb69bd2e3238d13484ff3c46df0cc1e2))
- **langserver:** Move core.utils.threading to core.concurrent and rename some function ([faee359](https://github.com/robotcodedev/robotcode/commit/faee359d0c7e45b7c1d0b44b1b6c1d247fb1d6fe))
- **langserver:** Remove async code from code lens ([204624c](https://github.com/robotcodedev/robotcode/commit/204624cc3fa1662babc929b5067497e820d660d1))
- **langserver:** Remove async code from commands ([58f185b](https://github.com/robotcodedev/robotcode/commit/58f185bd0636a3c1f640372771a66e8b2a33cc06))
- **langserver:** Remove async code from formatting and some import corrections ([2f25c78](https://github.com/robotcodedev/robotcode/commit/2f25c7805fe1e81589aedf7ee3f420db36ed88c4))
- **langserver:** Remove async code from inlay hints ([7535bfa](https://github.com/robotcodedev/robotcode/commit/7535bfa68c493e566ee39ef51370e04eda809b5f))
- **langserver:** Remove async code from inline value ([4e1b23c](https://github.com/robotcodedev/robotcode/commit/4e1b23cf3fe43d7a602f0c8983879d4e25444ed0))
- **langserver:** Remove async code from diagnostics, selection range, workspace, signature help ([0c38843](https://github.com/robotcodedev/robotcode/commit/0c38843b28cfa5175d65b3eafec3c455afcc3d2f))
- **langserver:** Remove async code from rename ([15e409d](https://github.com/robotcodedev/robotcode/commit/15e409dcb67e2fbe0fc6a3479ad1a0f090b3830d))
- **langserver:** Remove async code from semantic tokens ([3adddd1](https://github.com/robotcodedev/robotcode/commit/3adddd12f75664dc98988402c2597965be7a4bf3))
- **langserver:** Correct refresh handling and remove some unneeded code ([3f3944f](https://github.com/robotcodedev/robotcode/commit/3f3944f630ac6117cdb8a16d7078f9e8ab47e6cc))
- **langserver:** Remove threaded decorator from rpc methods and introduce a threaded property for the rpc_method decorator ([b478ae3](https://github.com/robotcodedev/robotcode/commit/b478ae3da563fd9af7409c234b55efabb412f8a7))
- **langserver:** Rename core.concurrent.FutureEx to Task ([d75eb9a](https://github.com/robotcodedev/robotcode/commit/d75eb9aa7005514c01b3ced5924191ed7cd780ab))
- **robotcode:** Move threaded decorator to the new core.utils.threading module ([96b897b](https://github.com/robotcodedev/robotcode/commit/96b897b63bdc13aaa0e383a12e74399e0f8caa86))
- Remove some unneeded code ([65e1775](https://github.com/robotcodedev/robotcode/commit/65e1775fd380b7e6b67a88c327f8961929e9cafb))
- Move most of langserver...ast_utils to robotcode.robot.utils.ast ([bc96805](https://github.com/robotcodedev/robotcode/commit/bc96805dc8fb813ac4b2fe4e65da79897bf275c4))
- Move language_server.robotframework.utils to robotcode.robot package ([6fe4dc0](https://github.com/robotcodedev/robotcode/commit/6fe4dc03408a2fb9c6c21c8db8954f6cb04c825f))
- Move some diagnostics code from langserver package to robot package ([4b3e65c](https://github.com/robotcodedev/robotcode/commit/4b3e65cad56b7029860a35a4e16f496930a4b504))


### Testing

- Add RFW 7.0 to devel and test matrix ([cd35020](https://github.com/robotcodedev/robotcode/commit/cd3502086b1505b53a89047d27ca097d3dfce07b))
- Try to stablize regression tests ([19419b3](https://github.com/robotcodedev/robotcode/commit/19419b3c10f0a7e079d6b6b7466516f4ec756f88))
- Enable RFW 7.0 tests in github workflow ([6a39f66](https://github.com/robotcodedev/robotcode/commit/6a39f66f6113ef8e1437a3bf2ae10d3de6fe0203))
- Another try to stabilize regression tests ([91d4d48](https://github.com/robotcodedev/robotcode/commit/91d4d482fdcecc65270f98f715760576ea9f7544))


## [0.68.1](https://github.com/robotcodedev/robotcode/compare/v0.68.0..v0.68.1) - 2023-12-21

### Bug Fixes

- **robotcode:** Add missing robotcode-plugin dependency ([570232d](https://github.com/robotcodedev/robotcode/commit/570232d6c7fa5c9bb2492515c4006d830481e151))
- **robotcode:** Catch OSError's if we can't create the default robot.toml config file ([6dd5f9e](https://github.com/robotcodedev/robotcode/commit/6dd5f9ef69f4d9914e34feccb8566fbfca79b260))


## [0.68.0](https://github.com/robotcodedev/robotcode/compare/v0.67.0..v0.68.0) - 2023-12-20

### Bug Fixes

- **langserver:** Correct duplicate items in completions ([023bfd7](https://github.com/robotcodedev/robotcode/commit/023bfd7d9b8784f2c5d4095c408207cffdebba73))


### Features

- Support for new keyword model changes in RFW 7 ([cb306cb](https://github.com/robotcodedev/robotcode/commit/cb306cb48e4c0d6849324241b944de4d408fbc9e))


### Refactor

- **core:** Move some files from core to utils ([92c1911](https://github.com/robotcodedev/robotcode/commit/92c1911b9da41d1368d25e694b84c04bcb56e4b0))
- **debugger:** Move import in cli handler in to cli function ([c96a321](https://github.com/robotcodedev/robotcode/commit/c96a3210459a018679f1beac2176182c4d493284))


## [0.67.0](https://github.com/robotcodedev/robotcode/compare/v0.66.1..v0.67.0) - 2023-12-13

### Bug Fixes

- **langserver:** Correted folding of IF blocks with multiple ELSE/ELSE IF's ([536db5e](https://github.com/robotcodedev/robotcode/commit/536db5e7038ada87f37a6dce8fbf6d4c0d9fb0a0))
- **langserver:** Unbound local variable in imports manager ([6d7b3d2](https://github.com/robotcodedev/robotcode/commit/6d7b3d2e53b9e8766891332318b5085a797f40ca))
- **vscode:** Don't show diagnostics when discover tests from a single file ([25024ac](https://github.com/robotcodedev/robotcode/commit/25024ac4151571448b3ca465f90823d1761c336e))


### Features

- **cli:** Introduce a command line switch to log to a file ([7a6b8af](https://github.com/robotcodedev/robotcode/commit/7a6b8af39989b5c49e3350fea65f46ed496d0db8))
- **debugger:** Lighter color for timestamps and respect the `--no-color' command line switch to disable colored output ([6f12eed](https://github.com/robotcodedev/robotcode/commit/6f12eed78b03f5efc19a87c69c46254a8f1b1cc8))


### Refactor

- **langserver:** Make documents handling synchronous and more threadsafe ([d1c72c2](https://github.com/robotcodedev/robotcode/commit/d1c72c21b8fd7851c9743c23e3b98cd67d0e53dd))
- **langserver,jsonrpc:** Use concurrent.futures.Future to send request, make register_capabilities syncronous ([41f495b](https://github.com/robotcodedev/robotcode/commit/41f495b6d01300400365009d50123f2cf83914e3))


### Testing

- **langserver:** Fix some regression tests ([0016ef6](https://github.com/robotcodedev/robotcode/commit/0016ef6318b6587fb8e9f193d80e8a5da370538c))
- **langserver:** Fix some regression tests ([fec9542](https://github.com/robotcodedev/robotcode/commit/fec954287c534d2e98f8a798d7058426231a86ed))
- **langserver:** Fix some more regression tests ([a399bd6](https://github.com/robotcodedev/robotcode/commit/a399bd6e1bd9fae2f15a198ec1c75b49b814947b))


## [0.66.1](https://github.com/robotcodedev/robotcode/compare/v0.66.0..v0.66.1) - 2023-11-24

### Bug Fixes

- **langserver:** Show a hint instead an error if there are variables used in a test case name ([6589b71](https://github.com/robotcodedev/robotcode/commit/6589b712c12efc570ab5d395752b3e0acce8fac8))


## [0.66.0](https://github.com/robotcodedev/robotcode/compare/v0.65.1..v0.66.0) - 2023-11-23

### Bug Fixes

- **langserver:** Handle unwanted warning messages at libdoc generation for robot files ([ce20bf5](https://github.com/robotcodedev/robotcode/commit/ce20bf5124705a4a84de694430ea37a8df64b86f))


### Features

- **langserver:** Implemented deprecation warning for old [RETURN] setting for RF 7 ([40a5e42](https://github.com/robotcodedev/robotcode/commit/40a5e429f9b73dc834f9693a034bace3ff51d7e9))


## [0.65.1](https://github.com/robotcodedev/robotcode/compare/v0.65.0..v0.65.1) - 2023-11-23

### Refactor

- **debugger:** Use concurrent.futures for sending request instead of asyncio.Futures ([dc06c2c](https://github.com/robotcodedev/robotcode/commit/dc06c2c5ac079248a6116f1d01cf6da4b8860481))


## [0.65.0](https://github.com/robotcodedev/robotcode/compare/v0.64.1..v0.65.0) - 2023-11-22

### Features

- **langserver:** Support for new VAR statement in RF7 ([2678884](https://github.com/robotcodedev/robotcode/commit/2678884fedce733a3c6a52589c4b5f55fb2beda4))
- **langserver:** Added new return type information of keyword from libdoc to documentation hover ([b91f2ff](https://github.com/robotcodedev/robotcode/commit/b91f2ff5b5a369ac65f36f0222954e29c56ca2f7))


### Refactor

- **jsonrpc:** Use concurrent.Futures instead of asyncio.Futures for request ([50384dc](https://github.com/robotcodedev/robotcode/commit/50384dcc94b676c4c8b3a6a7f1e4881104d99999))
- Some code cleanup and simplifications ([f799fb4](https://github.com/robotcodedev/robotcode/commit/f799fb44090ded0fb0d12b0d4dbef8dbfdc28706))
- Move markdown formatter to robotcode.robot.utils ([5a22bef](https://github.com/robotcodedev/robotcode/commit/5a22bef05d015576742506423b13cd773a4d9c70))


## [0.64.1](https://github.com/robotcodedev/robotcode/compare/v0.64.0..v0.64.1) - 2023-11-20

### Bug Fixes

- Correct creating run profiles if you use a single workspace folder ([e5430ec](https://github.com/robotcodedev/robotcode/commit/e5430ec4311b03165bf984eac02ee7f636d6ef9a))


## [0.64.0](https://github.com/robotcodedev/robotcode/compare/v0.63.0..v0.64.0) - 2023-11-19

### Bug Fixes

- **cli:** Add missing dependency ([9c6ed1f](https://github.com/robotcodedev/robotcode/commit/9c6ed1faed00a577dea34e1c1c5fd9146f687a2a))
- **langserver:** Signature help and markdown documentation for arguments without type for RF7 ([d67b2a0](https://github.com/robotcodedev/robotcode/commit/d67b2a025416a1e2ea90c20ec0db888794f874a8))
- **langserver:** Support for clients that do not implement pull diagnostics, e.g. neovim ([ced5372](https://github.com/robotcodedev/robotcode/commit/ced5372267a0cf632f556391b2fcc215dc46016d))
- **langserver:** Correct detection of valid nodes in quickfixes for TRY/EXCEPT statements in RF5 ([1bcef86](https://github.com/robotcodedev/robotcode/commit/1bcef867260c607c1fb8719a36d4408b84e138e6))
- Correct completion of argument types for RF7 ([dbca774](https://github.com/robotcodedev/robotcode/commit/dbca774e4b38aac389d7ac2b1a12fe6cd730157f))
- Some small glitches in semantic highlightning ([39b658f](https://github.com/robotcodedev/robotcode/commit/39b658fd6acb9378d253e56e32bfea8046482b8b))


### Documentation

- Correct some command line descriptions ([c0e2536](https://github.com/robotcodedev/robotcode/commit/c0e2536cb07b087e9929597146fde29b2f4f1a87))
- Correct some docs for CLI interface ([7bc7099](https://github.com/robotcodedev/robotcode/commit/7bc70992d2cdff14c1a6b20b387633a7df40d591))


### Features

- **langserver:** Colorize new VAR token for RF7 ([3cd27b2](https://github.com/robotcodedev/robotcode/commit/3cd27b2307f4d5d8aba140bdc0127b7048ca8c68))
- **langserver:** Add completions and new snippets for the new VAR statement for RF7 ([5631a1b](https://github.com/robotcodedev/robotcode/commit/5631a1bf11f7f3bc368732c06708dda10b80933d))
- **vscode:** Support for creating test profiles in vscodes test explorer ([8c0e889](https://github.com/robotcodedev/robotcode/commit/8c0e8893e1dfde90e8f624d7aa256b796dc0c7e3))

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



### Refactor

- **cli:** Move --(no)-diagnostic switch to the discover command ([9ed33c9](https://github.com/robotcodedev/robotcode/commit/9ed33c9944c0064de26e533ee328cf2207f3f30e))
- Remove inner imports from analyzer ([470bcff](https://github.com/robotcodedev/robotcode/commit/470bcff25f1121460e146171a48104d9a8e35e7b))
- Some code simplifications ([fbec326](https://github.com/robotcodedev/robotcode/commit/fbec3263054453ba37f8311e0d0f580b695f2565))


## [0.63.0](https://github.com/robotcodedev/robotcode/compare/v0.62.3..v0.63.0) - 2023-11-12

### Bug Fixes

- **langserver:** Simplify code for variables and library completions ([256d7aa](https://github.com/robotcodedev/robotcode/commit/256d7aacee531e4a8f27044f9342d6149a0d4a85))


### Documentation

- Add some new logo ideas ([e468a0f](https://github.com/robotcodedev/robotcode/commit/e468a0f35d01a85378fcdc8da44961189d087985))


### Features

- First support for RF 7 ([bd704c2](https://github.com/robotcodedev/robotcode/commit/bd704c2b1f45b906568188cd54b255bb0e15a4f1))


  start implementing #177


### Refactor

- **vscode:** Detection and running of python from vscode ([6000edb](https://github.com/robotcodedev/robotcode/commit/6000edb33f9bf9845cadf1a6d2e96e59ccb9e010))
- Remove unused code and update dependencies ([4c2d1f7](https://github.com/robotcodedev/robotcode/commit/4c2d1f76cbcf5da56955c143404cf4cf386652d7))


## [0.62.3](https://github.com/robotcodedev/robotcode/compare/v0.62.2..v0.62.3) - 2023-10-31

### Bug Fixes

- **langserver:** Correction of escaped characters and variables highlighting in import names ([22ef5f3](https://github.com/robotcodedev/robotcode/commit/22ef5f3e1be3509e2343a3e83f81c07d4ec97a91))
- **langserver:** Correct handling of imports containing backslashes, in RobotFramework you have to escape them ([097c28b](https://github.com/robotcodedev/robotcode/commit/097c28bb2ac2e9621bce01a3746cb16edec1a107))


## [0.62.2](https://github.com/robotcodedev/robotcode/compare/v0.62.1..v0.62.2) - 2023-10-28

### Bug Fixes

- **langserver:** Resolving of ${EXECDIR} and ${CURDIR} corrected ([32a1492](https://github.com/robotcodedev/robotcode/commit/32a1492bb8743a10293a148573424c6efa6153c3))


## [0.62.1](https://github.com/robotcodedev/robotcode/compare/v0.62.0..v0.62.1) - 2023-10-28

### Bug Fixes

- **langserver:** Single resource file with different relative paths is not seen as same file ([0c2a08f](https://github.com/robotcodedev/robotcode/commit/0c2a08fd18a4073352849316e48e68fa48add490))


## [0.62.0](https://github.com/robotcodedev/robotcode/compare/v0.61.7..v0.62.0) - 2023-10-27

### Features

- **langserver:** Support for importing libraries of multiple classes from a module ([35c9775](https://github.com/robotcodedev/robotcode/commit/35c97759718c1a9515000bed7365eec04c4bf16d))
- Do not use pathlib.Path.resolve because it is slow and we don't need to resolve links ([85c3dc1](https://github.com/robotcodedev/robotcode/commit/85c3dc16245d151c37aac9c9cb87e9fa1a7bb2e2))


### Testing

- Correct some regression tests ([6031f48](https://github.com/robotcodedev/robotcode/commit/6031f48eb7e846f763eff8efb4c8b9757e9b5662))


## [0.61.7](https://github.com/robotcodedev/robotcode/compare/v0.61.6..v0.61.7) - 2023-10-25

### Performance

- **langserver:** Increase performance of visitor a little bit more ([a257b90](https://github.com/robotcodedev/robotcode/commit/a257b9075d87b3e5bceeb74c32cc39d1f848f807))


## [0.61.6](https://github.com/robotcodedev/robotcode/compare/v0.61.5..v0.61.6) - 2023-10-20

### Bug Fixes

- **langserver:** Correct handling of imports with the same namespace name ([c65e98d](https://github.com/robotcodedev/robotcode/commit/c65e98d3a7c6d09cc86a536fd6cfdc88d35e282e))

  hover, semantic hightlightning, references are aware of the current keyword call namespace if given



### Refactor

- **langserver:** Make package import relativ ([91513c5](https://github.com/robotcodedev/robotcode/commit/91513c51b4b9923b1d33fbc0198e9331f2f314aa))


## [0.61.5](https://github.com/robotcodedev/robotcode/compare/v0.61.4..v0.61.5) - 2023-10-19

### Bug Fixes

- **langserver:** Correct highlight, completion, analyze, etc. keyword calls with `.` that are also valid namespaces ([42fe633](https://github.com/robotcodedev/robotcode/commit/42fe633be64409766f02132eb353b1dd5525d75e))


## [0.61.4](https://github.com/robotcodedev/robotcode/compare/v0.61.3..v0.61.4) - 2023-10-15

### Bug Fixes

- **discover:** Normalize tags in tests command and sort tags ([cf1159c](https://github.com/robotcodedev/robotcode/commit/cf1159cf51f2eb95365cc5f489a06de15074aa24))
- **langserver:** Complete keywords containing `.` if there is no namespace with the name before the dot ([5fc3104](https://github.com/robotcodedev/robotcode/commit/5fc31043336ec12e12d065c6a7732d462db6115b))


### Documentation

- Optimize some config descriptions ([88ee386](https://github.com/robotcodedev/robotcode/commit/88ee3863236653c2766ed4d392c4ff4040a70506))


### Performance

- **langserver:** Speedup Visitor and AsyncVisitor a little bit ([3d8a22d](https://github.com/robotcodedev/robotcode/commit/3d8a22dbfeb801a76a259f351ddd62593b235e76))


## [0.61.3](https://github.com/robotcodedev/robotcode/compare/v0.61.2..v0.61.3) - 2023-10-10

### Performance

- **core:** Improve perfomance of converting dataclasses to json ([dfb576e](https://github.com/robotcodedev/robotcode/commit/dfb576e2578d8306516400132d6b6d8df4a71e18))
- **core:** Increase performance of dataclasses.from_dict ([a41cfb3](https://github.com/robotcodedev/robotcode/commit/a41cfb3835cc76a1616ad8de71dcdc374b240222))


## [0.61.2](https://github.com/robotcodedev/robotcode/compare/v0.61.1..v0.61.2) - 2023-10-07

### Bug Fixes

- Some regression tests ([d36deb4](https://github.com/robotcodedev/robotcode/commit/d36deb460e5226decd64dd4ccc3ea7c793542e82))


## [0.61.1](https://github.com/robotcodedev/robotcode/compare/v0.61.0..v0.61.1) - 2023-10-07

### Bug Fixes

- **langserver:** Correct handling of `robotcode.robocop.configurations` setting ([9dc690e](https://github.com/robotcodedev/robotcode/commit/9dc690e9376902c08158a632e3fa09fd938d4ae7))


### Performance

- Some more performance corrections for as_dict ([3212c71](https://github.com/robotcodedev/robotcode/commit/3212c7122c19b5b231076c386eb6079499aa1697))


## [0.61.0](https://github.com/robotcodedev/robotcode/compare/v0.60.0..v0.61.0) - 2023-10-07

### Documentation

- Update json schema and doc for `robot.toml` file ([f7c0693](https://github.com/robotcodedev/robotcode/commit/f7c0693d0fd6c78cf01b0429a6ad75b5796d7253))


### Features

- **discovery:** Add more options for discovering tags and tests ([508b517](https://github.com/robotcodedev/robotcode/commit/508b5178c7503525bda7708e191f76b1cddacc7c))
- **robotcode:** Rename `extra-` prefix to `extend-` in robot.toml files ([d4747e2](https://github.com/robotcodedev/robotcode/commit/d4747e256122cfde7556ef28de6e310867ccf3f6))
- **robotcode:** Better formatting and include active, selected, enabled state of a profile in `profile list` command ([850c751](https://github.com/robotcodedev/robotcode/commit/850c751a34a96bcc8965b8d08c82dbae5e1e558a))


### Performance

- Optimize performance of as_dict for dataclasses ([2b4ce26](https://github.com/robotcodedev/robotcode/commit/2b4ce26abcb91974092019a03e6ddf3edba2b254))


## [0.60.0](https://github.com/robotcodedev/robotcode/compare/v0.59.0..v0.60.0) - 2023-10-04

### Features

- **robotcode:** Introduce plugin spec for configuration classes ([582e360](https://github.com/robotcodedev/robotcode/commit/582e3608f452a4168124a11b23a872c45f8096be))
- **robotcode:** Add `Path` to allowed GLOBALS in config expressions ([66aea74](https://github.com/robotcodedev/robotcode/commit/66aea748df4b2861951c8dc2d2a8a22b78c1fefc))


## [0.59.0](https://github.com/robotcodedev/robotcode/compare/v0.58.0..v0.59.0) - 2023-09-28

### Features

- **langserver:** All refactorings and quickfixes are now previewable ([40e9d92](https://github.com/robotcodedev/robotcode/commit/40e9d92596e5ae99a7f84e86d7eebd4edb4214c3))

  when you select a quickfix or refactoring with <kbd>CONTROL</kbd>+<kbd>RETURN</kbd> a refactor preview window is shown.



## [0.58.0](https://github.com/robotcodedev/robotcode/compare/v0.57.4..v0.58.0) - 2023-09-26

### Features

- **langserver:** Code action - extract keyword ([9f92775](https://github.com/robotcodedev/robotcode/commit/9f927752b721d26b8dc7c24434efbe1a5ac9f56a))
- **vscode:** Update to vscode-languageclient to 9.0, now we need at least a vscode version >=1.82 ([d8591b1](https://github.com/robotcodedev/robotcode/commit/d8591b1a0199be4c884cfe60e89966ee7a675537))


## [0.57.4](https://github.com/robotcodedev/robotcode/compare/v0.57.3..v0.57.4) - 2023-09-24

### Bug Fixes

- **langserver:** Correct "Create keyword" quick fix to ignore empty lines when inserting text ([12af94d](https://github.com/robotcodedev/robotcode/commit/12af94d0f551bb3265a13c22e434a12cd817bb49))


## [0.57.3](https://github.com/robotcodedev/robotcode/compare/v0.57.2..v0.57.3) - 2023-09-23

### Bug Fixes

- **langserver:** Some correction at line and file endings for signature help ([782bfe6](https://github.com/robotcodedev/robotcode/commit/782bfe69b7f0828e4d6f952fe6bbe665de10a1c4))
- **langserver:** Only show valid headers in resource and init.robot file at completion ([674040a](https://github.com/robotcodedev/robotcode/commit/674040a4ec0de9d8cf6031796798d7b1a03acfee))


## [0.57.2](https://github.com/robotcodedev/robotcode/compare/v0.57.1..v0.57.2) - 2023-09-20

### Bug Fixes

- **langserver:** Don't show argument completion if the cursor is in a keyword assignment ([3c5a797](https://github.com/robotcodedev/robotcode/commit/3c5a797c37d4c6a3c06f4d87cdb0d01fe2c98146))
- **langserver:** Don't show surround code action if we have selected template arguments ([59a0114](https://github.com/robotcodedev/robotcode/commit/59a01140f8800d5be0caba48e0654dee8de83325))


## [0.57.1](https://github.com/robotcodedev/robotcode/compare/v0.57.0..v0.57.1) - 2023-09-19

### Bug Fixes

- **langserver:** Correct some completion quirks at line or file ends ([080ab83](https://github.com/robotcodedev/robotcode/commit/080ab83a02ba34cfbae55785813b0ffdf40ceb77))
- **langserver:** Correct some in refactor surrounding quirks at file ends ([082132c](https://github.com/robotcodedev/robotcode/commit/082132cc69df4ab0a96fe834426107cc003dfad8))


## [0.57.0](https://github.com/robotcodedev/robotcode/compare/v0.56.0..v0.57.0) - 2023-09-17

### Features

- **langserver:** Quick fixes for code actions are generated for all diagnostics specified in the request, and quick fixes are generated with the name of the variable or keyword in the label. ([c2b8f5a](https://github.com/robotcodedev/robotcode/commit/c2b8f5aa3ac11905b3f8bfe45e89691219f85df9))
- **langserver:** Improved quickfix `create keyword` can now add keywords to resource files if valid namespace is given ([9499d43](https://github.com/robotcodedev/robotcode/commit/9499d431fd1fb842237948956a42e6f803128a60))
- New code action refactor rewrite: surroundings for TRY/EXCEPT/FINALLY ([fdba5b9](https://github.com/robotcodedev/robotcode/commit/fdba5b93cd3b9484eceb73b9eeacbef2769876d2))


### Refactor

- **langserver:** Move code action `assign result to variable` to refactorings ([b8efd1d](https://github.com/robotcodedev/robotcode/commit/b8efd1d392035e71e303e8d937476d699a421d08))


## [0.56.0](https://github.com/robotcodedev/robotcode/compare/v0.55.1..v0.56.0) - 2023-09-11

### Documentation

- Fix some comments in changelog and add some more todos ([dc71f0e](https://github.com/robotcodedev/robotcode/commit/dc71f0e61618d211a518a3af160c5d30004084b2))


### Features

- **langserver:** New code action quick fixes - assign kw result to variable, create local variable, disable robot code diagnostics for line ([bba00aa](https://github.com/robotcodedev/robotcode/commit/bba00aa3edc9e51a24104221d019798aba211d5d))
- **langserver:** New code action quick fix - create suite variable ([4c03a80](https://github.com/robotcodedev/robotcode/commit/4c03a80f118fdb5547777f62a99546a874d2cfdb))
- **langserver:** New code action quick fix - Add argument ([a21c05b](https://github.com/robotcodedev/robotcode/commit/a21c05be3f767def97d38c9960df8efdade1749c))


### Refactor

- **langserver:** Move all error messages to one place ([125c091](https://github.com/robotcodedev/robotcode/commit/125c09116aec4475a9331301fdb636e34f45c11d))


### Testing

- Update code action show documentation test cases ([1c333d3](https://github.com/robotcodedev/robotcode/commit/1c333d3d531a78ed79e157ad3d81d9c50cfb9cf2))


## [0.55.1](https://github.com/robotcodedev/robotcode/compare/v0.55.0..v0.55.1) - 2023-09-06

### Bug Fixes

- **debugger:** Correct update of test run results when suite teardown fails or is skipped during suite teardown for RF 4.1 ([65d67ca](https://github.com/robotcodedev/robotcode/commit/65d67ca1b4293db3ba2da943c3e77c46233f2181))

  this is a follow up to 80b742e



## [0.55.0](https://github.com/robotcodedev/robotcode/compare/v0.54.3..v0.55.0) - 2023-09-05

### Bug Fixes

- Update of RobotCode icon in status bar when Python environment is changed ([161806c](https://github.com/robotcodedev/robotcode/commit/161806c32df5f76d6ca86a441e060024f0eeba17))
- Don't complete arguments for run keywords ([38698ed](https://github.com/robotcodedev/robotcode/commit/38698ed05a5f809f287c9e003d3837e605bab2be))
- Correct handling of @ variable and & dictionary arguments in signature help and completion ([4415387](https://github.com/robotcodedev/robotcode/commit/44153873fff9981eda05a07ba2922a625328e756))


### Features

- **langserver:** Better completion for variable imports ([1602b71](https://github.com/robotcodedev/robotcode/commit/1602b71e57f44757fe09de39ab6af48c11bbaf56))
- Support for robocop 4.1.1 code descriptions ([a5a0d4c](https://github.com/robotcodedev/robotcode/commit/a5a0d4c49d8212812cb8d81e2fb55809352a36aa))


### Refactor

- Move code_actions and support unions with enums and string in dataclasses ([b9a3f10](https://github.com/robotcodedev/robotcode/commit/b9a3f10a6ba8a2c9c1f5fc6c1d06d57d9d7c9760))


## [0.54.3](https://github.com/robotcodedev/robotcode/compare/v0.54.2..v0.54.3) - 2023-09-02

### Bug Fixes

- **langserver:** Correct some styles for semantic highlightning ([89eeeb4](https://github.com/robotcodedev/robotcode/commit/89eeeb4506d8e1730cf8c44dc69f423ad95d0d24))
- **langserver:** Change scope name of argument tokens to allow better automatic opening of completions ([4f144c4](https://github.com/robotcodedev/robotcode/commit/4f144c4114d6ed1921143451d47ecfe738a77f1b))
- **langserver:** Dont show values in completions if the token before is an named argument token ([26c6eda](https://github.com/robotcodedev/robotcode/commit/26c6edab9488f9b345cb328c792153a1a2cfb887))


## [0.54.2](https://github.com/robotcodedev/robotcode/compare/v0.54.1..v0.54.2) - 2023-09-02

### Bug Fixes

- **langserver:** Escape pipe symbols in keyword argument descriptions in hover ([b3111fe](https://github.com/robotcodedev/robotcode/commit/b3111fe31e4f29fcffdde8d20bbc293e3b951391))
- **vscode:** Correct highligtning of keyword arguments ([162a0b0](https://github.com/robotcodedev/robotcode/commit/162a0b0fd04c3db41dba1e6f20d3b321a9d306b9))
- Sorting of completion items on library imports ([5d2c20d](https://github.com/robotcodedev/robotcode/commit/5d2c20d063e1b807a91e086910ebf082834cf800))


## [0.54.1](https://github.com/robotcodedev/robotcode/compare/v0.54.0..v0.54.1) - 2023-09-01

### Bug Fixes

- Disable html report for pytest ([8fcb4ed](https://github.com/robotcodedev/robotcode/commit/8fcb4ed0b6f88e876ee6dfeb5bf08f7b8826114a))


## [0.54.0](https://github.com/robotcodedev/robotcode/compare/v0.53.0..v0.54.0) - 2023-09-01

### Bug Fixes

- **langserver:** Disable directory browsing in documentation server ([18ad3ff](https://github.com/robotcodedev/robotcode/commit/18ad3ff50f7a223bdeed6f58d1cd54386a12664b))
- **langserver:** Correct end positon of completion range in arguments ([063d105](https://github.com/robotcodedev/robotcode/commit/063d105d6fa2feb94253a9b46a448c2977a168a2))


### Features

- **langserver:** Better argument signatures for completion and signature help ([ed7b186](https://github.com/robotcodedev/robotcode/commit/ed7b18623b7f49180f98672bd7fb2a0781e15b9e))

  don't break between prefix and name of signature

- **langserver:** Better signature help and completion of keyword arguments and library import arguments, including completions for type converters like Enums, bools, TypedDict, ... ([dee570b](https://github.com/robotcodedev/robotcode/commit/dee570b98352c4d6aafe1ce5496806fd02fc9254))


## [0.53.0](https://github.com/robotcodedev/robotcode/compare/v0.52.0..v0.53.0) - 2023-08-27

### Features

- **langserver:** First version of completion of enums and typed dicts for RF >= 6.1 ([bd39e30](https://github.com/robotcodedev/robotcode/commit/bd39e306a6bdd03610ed5b1b74d8977655042796))
- **robocop:** With code descriptions in `robocop` diagnostics you can jump directly to the website where the rule is explained ([46125a5](https://github.com/robotcodedev/robotcode/commit/46125a58ad9bbccb8fd2a2763b1e63a6407ef7f3))

  closes  #152



## [0.52.0](https://github.com/robotcodedev/robotcode/compare/v0.51.1..v0.52.0) - 2023-08-25

### Bug Fixes

- Use import nodes to add references for libraries/resources and variables ([f0eb9c9](https://github.com/robotcodedev/robotcode/commit/f0eb9c9b695c02ec42cf3cfa2fb9445b225dc2ea))


### Features

- **debugger:** Add some more informations in verbose mode ([ff87819](https://github.com/robotcodedev/robotcode/commit/ff87819c10f1ceb656ce28d678e9c74f4d0b5810))
- **langserver:** Goto, highlight, rename, hover, find references for named arguments ([054d210](https://github.com/robotcodedev/robotcode/commit/054d2101536a205d87b2d7409609cfe5ac1ba6ff))

  rename and goto only works for resource keywords

- **langserver:** Inlay hint and signature help now shows the correct parameters and active parameter index, make both work for library and variable imports and show type informations if type hints are defined ([99bc996](https://github.com/robotcodedev/robotcode/commit/99bc996a970e91ec54bdec5a2f371baafd965706))
- **robotcode:** Internal cli args are now hidden ([934e299](https://github.com/robotcodedev/robotcode/commit/934e299ecbfce3d7ef5a3ca403201499836a32fd))

  If you want to show these args set the environment variable `ROBOTCODE_SHOW_HIDDEN_ARGS` to `true` or `1`.



## [0.51.1](https://github.com/robotcodedev/robotcode/compare/v0.51.0..v0.51.1) - 2023-08-13

### Testing

- Update some tests ([b459cf7](https://github.com/robotcodedev/robotcode/commit/b459cf766d06a66327591a67570d1118810cb381))


## [0.51.0](https://github.com/robotcodedev/robotcode/compare/v0.50.0..v0.51.0) - 2023-08-13

### Bug Fixes

- **langserver:** Correct highlighting of keyword arguments with default value ([c12e1ef](https://github.com/robotcodedev/robotcode/commit/c12e1efac14f6173b2a3058ab0494a5643db3d54))
- Correct hovering, goto, etc. for if/else if/inline if statements ([7250709](https://github.com/robotcodedev/robotcode/commit/7250709ce5b593f8fb14212130a8f876e0d73f67))


### Documentation

- Extend some help texts ([f14ec2d](https://github.com/robotcodedev/robotcode/commit/f14ec2d21ddab8d99c96d6494b5bbf79fcae9eee))


### Features

- **discovery:** Option to show/hide parsing errors/warnings at suite/test discovery ([633b6b5](https://github.com/robotcodedev/robotcode/commit/633b6b54f3026a93821faedd0d48a860ebac6f63))
- **langserver:** Highlight namespace references ([b9cd85a](https://github.com/robotcodedev/robotcode/commit/b9cd85a9e6af908ab3c541eb37b89e1d3c08fc82))
- **langserver:** Rework "Analysing", "Hover", "Document Highlight", "Goto" and other things to make them faster, simpler, and easier to extend ([47c1feb](https://github.com/robotcodedev/robotcode/commit/47c1febac2536f653ff662154dcea40c48f860c2))


### Refactor

- **langserver:** Speed up hovering for keywords, variables and namespace by using references from code analysis ([4ba77ab](https://github.com/robotcodedev/robotcode/commit/4ba77ab018637fbc7b613281e8dac93054acf19a))


## [0.50.0](https://github.com/robotcodedev/robotcode/compare/v0.49.0..v0.50.0) - 2023-08-08

### Bug Fixes

- Made RobotCode work with Python 3.12 ([aee8378](https://github.com/robotcodedev/robotcode/commit/aee8378b3e8dadb6378a8aff88269d56679b1512))


  Because of some changes in `runtime_protocols', see python doc


### Documentation

- Reorganize docs ([5fb0d61](https://github.com/robotcodedev/robotcode/commit/5fb0d61a835126cec9e6ac68f1ba78b94c46bbd7))


### Features

- **discover:** Tags are now discovered normalized by default ([7f52283](https://github.com/robotcodedev/robotcode/commit/7f52283804a645433ec8f5ae9737eae70f53f8cb))

  you can add --not-normalized cli argument to get the tags not normalized

- **robotcode:** Use default configuration if no project root or project configuration is found ([ac1daa1](https://github.com/robotcodedev/robotcode/commit/ac1daa18094472d1d28796c891645607647a2073))


## [0.49.0](https://github.com/robotcodedev/robotcode/compare/v0.48.0..v0.49.0) - 2023-08-03

### Bug Fixes

- Completion of bdd prefixes optimized ([840778e](https://github.com/robotcodedev/robotcode/commit/840778e801ea360756f76490ffd13091b4a3d908))


  - If you press CTRL+SPACE after a bdd prefix the completion list is shown without typing any other key.
  - if the cursor is at the bdd prefix, other bdd prefix are on the top of the completion list and if you select a bdd prefix only the old prefix is overwritten


### Documentation

- Better help texts for profiles and config commands ([3195451](https://github.com/robotcodedev/robotcode/commit/3195451c449dbf4e15c854c04e8bc9b5f5e45767))
- Correct doc strings in model ([e0f8e6b](https://github.com/robotcodedev/robotcode/commit/e0f8e6b166d5d255cbf8498272869d8c2f2b30c4))


### Features

- User default `robot.toml` config file ([55f559d](https://github.com/robotcodedev/robotcode/commit/55f559d36c16fb0e9f371c31d1a2a45d427eb636))


  Instead of defining default settings like output-dir or python-path in VSCode a default config file is created in user directory. The default settings in VSCode are removed, but you can define them here again, but the prefered way is to use the `robot.toml` file in user directory.
- Reporting suites and tests with the same name when tests are discovered ([e5d895b](https://github.com/robotcodedev/robotcode/commit/e5d895bff914326fcc99d5c86ea98624a86136b4))
- "create keyword" quick fix detects bdd prefixes in the keyword being created and creates keywords without the prefix ([e9b6431](https://github.com/robotcodedev/robotcode/commit/e9b64313a35db2931dc02a5c6f0f95f4a1f9be98))


## [0.48.0](https://github.com/robotcodedev/robotcode/compare/v0.47.5..v0.48.0) - 2023-07-30

### Bug Fixes

- **robotcode:** Add missing profile settings to config documentation ([48cb64c](https://github.com/robotcodedev/robotcode/commit/48cb64cd6e04d97dd473598b3b91a0698772de48))
- Correct update of test run results when suite teardown fails or is skipped during suite teardown ([80b742e](https://github.com/robotcodedev/robotcode/commit/80b742eb1cde1777393475727f15738f58b497a9))


  Unfortunately, if a test has already failed but it is subsequently skipped in the teardown, the error status of VSCode is not set because the skipped status has a lower priority than the failed status. This is a VSCode problem and I can't change it at the moment.
- Correct completion of settings with ctrl+space in some situation ([47c1165](https://github.com/robotcodedev/robotcode/commit/47c1165468b5ea9e6705c4f95d1f763afae0fda2))
- In a test run, errors that occur are first selected in the test case and not in the keyword definition ([a6f0488](https://github.com/robotcodedev/robotcode/commit/a6f0488fd155d3aa01da4568d5154e22b5c57ab5))
- Discover tests for RF 6.1.1 ([b27cbcf](https://github.com/robotcodedev/robotcode/commit/b27cbcfe7ed373b05caf5b5d3b4df93345b6c34d))
- Better output for discover info command ([ac6b4a6](https://github.com/robotcodedev/robotcode/commit/ac6b4a67be5e891d14e7cc05b42fe73f210478e8))


### Features

- **vscode:** Added a statusbar item that shows some information about the current robot environment, like version, python version, etc. ([1ff174a](https://github.com/robotcodedev/robotcode/commit/1ff174a42083f902e2ea8fb7a6b93e72fe5edacb))
- Removed old `robotcode.debugger` script in favor of using `robotcode debug` cli command ([e69b10a](https://github.com/robotcodedev/robotcode/commit/e69b10afce725c796a53b40abc866e2a7b44d655))


## [0.47.5](https://github.com/robotcodedev/robotcode/compare/v0.47.4..v0.47.5) - 2023-07-20

### Bug Fixes

- Add missing log-level in testcontroller ([a26193f](https://github.com/robotcodedev/robotcode/commit/a26193fe2012b32690146ee364a48d0b95756077))


## [0.47.4](https://github.com/robotcodedev/robotcode/compare/v0.47.3..v0.47.4) - 2023-07-20

### Bug Fixes

- Don't update tests if editing `__init__.robot` files ([d6d1785](https://github.com/robotcodedev/robotcode/commit/d6d178536b807bda04e790bd0a8d62f36e710042))


## [0.47.3](https://github.com/robotcodedev/robotcode/compare/v0.47.2..v0.47.3) - 2023-07-18

### Bug Fixes

- Reset changlog ([e39b6ce](https://github.com/robotcodedev/robotcode/commit/e39b6ce25183f4353830db8abc8b04ee19ffbbeb))
- Move to commitizen to create new releases, this is only a dummy release.. ([07b6e4c](https://github.com/robotcodedev/robotcode/commit/07b6e4c96b63b821368c47094c55192b03f33279))


## [0.47.2](https://github.com/robotcodedev/robotcode/compare/v0.47.1..v0.47.2) - 2023-07-17

### Bug Fixes

- Duplicated header completions if languages contains same words ([d725c6e](https://github.com/robotcodedev/robotcode/commit/d725c6e0dc3f28bfdc6a6407a0d4e38426552e7f))


## [0.47.1](https://github.com/robotcodedev/robotcode/compare/v0.47.0..v0.47.1) - 2023-07-10

### Bug Fixes

- **debugger:** Print the result of an keyword in debugger also if it has a variable assignment ([43440d8](https://github.com/robotcodedev/robotcode/commit/43440d82e667aa4cdcbebdad848621f93075f282))
- Dont update tests in an opened file twice if file is saved ([390e6d4](https://github.com/robotcodedev/robotcode/commit/390e6d4ae6ad6f3ac46805d03a4034a86030c0c9))


## [0.47.0](https://github.com/robotcodedev/robotcode/compare/v0.46.0..v0.47.0) - 2023-07-10

### Bug Fixes

- **debugger:** (re)disable attachPython by default ([26ee516](https://github.com/robotcodedev/robotcode/commit/26ee516b9dda5912fff18d2b9e4f3126b08fcc0a))
- **debugger:** Hide uncaught exceptions now also works correctly for RF >=5 and < 6.1 ([f784613](https://github.com/robotcodedev/robotcode/commit/f7846138d2f668625d1afc2ec46f246338cc084e))
- Update diagnostic for Robocop 4.0 release after disablers module was rewritten ([6636bfd](https://github.com/robotcodedev/robotcode/commit/6636bfd352927c5721f9c34edfc99b2635b99937))
- Stabilize debugger with new vscode version > 1.79 ([d5ad4ba](https://github.com/robotcodedev/robotcode/commit/d5ad4bad6ffe8f210cb6b0f10ca33ccdb269a457))
- Correct message output in test results view ([b18856f](https://github.com/robotcodedev/robotcode/commit/b18856f1232650e91de3abf1ee8071c750fb689c))


### Features

- **debugger:** Debugger does not stop on errors caught in TRY/EXCEPT blocks ([043842c](https://github.com/robotcodedev/robotcode/commit/043842c0709867fdc18d9b4417c7db00cead04fb))

  To stop on these errors you have to switch on the exception breakpoint "Failed Keywords".

- **debugger:** Switching between "keyword" and "expression" mode by typing `# exprmode` into debug console (default: keyword mode) ([1cc6680](https://github.com/robotcodedev/robotcode/commit/1cc668006b4d04911cae419d3dd53916c7dd68fe))

  In the expression mode you can enter python expression and ask for variables and so on.
  In keyword mode you can enter robot framework statements, i.e. simple keyword call, IF/FOR/TRY statements, this also allows multi line input

- **debugger:** Simple keyword completion in debugger ([6b1ffb6](https://github.com/robotcodedev/robotcode/commit/6b1ffb6ae5738cd9fcf674729baecbb3964d0729))
- **debugger:** Expanding dict and list variables in the variable view of the debugger, this also works in hints over variables, in the watch view and also by evaluating expressions/keywords in the command line of the debugger ([2969379](https://github.com/robotcodedev/robotcode/commit/296937934db8997891df61c600953fc166a2dec2))
- Show more informations in hint over a variables import ([735a209](https://github.com/robotcodedev/robotcode/commit/735a209801ab3014ec417a583279929a9d88c1b2))
- Complete reserved tags in Tags settings ([483b9ac](https://github.com/robotcodedev/robotcode/commit/483b9ac539daca8129945aec31735fd51bf00c6b))


  Closes [ENHANCEMENT] Support Reserved Tags #103
- Show deprecation information if using `Force Tags` and `Default Tags` ([f23e5d0](https://github.com/robotcodedev/robotcode/commit/f23e5d0ec2420561589ca24240e449defe7fd373))


## [0.46.0](https://github.com/robotcodedev/robotcode/compare/v0.45.0..v0.46.0) - 2023-07-05

### Bug Fixes

- **debugger:** Evaluation expressions in RFW >= 6.1 not work correctly ([f7c38d6](https://github.com/robotcodedev/robotcode/commit/f7c38d6dcfc6b96b64d9db7fb1e53393426bf3bf))
- Insted of starting the debugger, start robotcode.cli in debug launcher ([013bdfd](https://github.com/robotcodedev/robotcode/commit/013bdfd485e021a511759a6d98fbc55693b0fafc))


### Features

- Allow multiline RF statements in debug console ([f057131](https://github.com/robotcodedev/robotcode/commit/f057131e956c2b5d3ee1255fd4fe7958ddd8722c))


  This supports also IF/ELSE, FOR, TRY/EXCEPT/FINALLY  statements. Just copy your piece of code to the debug console.
  This also enables the python debugger by default if you run a RF debugging session


## [0.45.0](https://github.com/robotcodedev/robotcode/compare/v0.44.1..v0.45.0) - 2023-06-23

### Bug Fixes

- Change code property for diagnostics for analyse imports to ImportRequiresValue ([222e89c](https://github.com/robotcodedev/robotcode/commit/222e89cdc0391323d89c54ccbc4a54d13eb99b28))
- Document_symbols throws exception if section name is empty ([ffce34d](https://github.com/robotcodedev/robotcode/commit/ffce34d7edd3f31f94da76edc090853f98cadb29))


### Features

- Library doc now generates a more RFW-like signature for arguments and argument defaults like ${SPACE}, ${EMPTY}, ${True}, etc. for the respective values ([28a1f8a](https://github.com/robotcodedev/robotcode/commit/28a1f8a7451fb77e91348569065dff8573080330))


## [0.44.1](https://github.com/robotcodedev/robotcode/compare/v0.44.0..v0.44.1) - 2023-06-21

### Bug Fixes

- Completion and diagnostics for import statements for RF >= 6.1 ([b4e9f03](https://github.com/robotcodedev/robotcode/commit/b4e9f0333633f3d83990137e0a78d61faa029b8c))


## [0.44.0](https://github.com/robotcodedev/robotcode/compare/v0.43.2..v0.44.0) - 2023-06-21

### Bug Fixes

- Extension not terminating sometimes on vscode exit ([753c89c](https://github.com/robotcodedev/robotcode/commit/753c89c91373bb5a27881bee23c1fc1e37b41356))
- Detect languageId of not given at "textDocument/didOpen" ([54e329e](https://github.com/robotcodedev/robotcode/commit/54e329e48d456c61063b697b91d4796a8ca34b3e))
- Correct handling error in server->client JSON RPC requests ([6e16659](https://github.com/robotcodedev/robotcode/commit/6e166590f7b0096741c085d13ea7437f4674c4a8))


### Features

- Add option to start a debugpy session for debugging purpose ([3f626cc](https://github.com/robotcodedev/robotcode/commit/3f626cc4dd0fdf70191c84e9a63388eb947fa1db))


### Refactor

- Make mypy and ruff happy ([0c26cc0](https://github.com/robotcodedev/robotcode/commit/0c26cc076abe2ec678c0e2f40bdcc1accdd8f894))


## [0.43.2](https://github.com/robotcodedev/robotcode/compare/v0.43.1..v0.43.2) - 2023-06-20

### Bug Fixes

- Only update test explorer items if file is a valid robot suite ([9461acf](https://github.com/robotcodedev/robotcode/commit/9461acf5e1b1263dd5f61c1b864de83729fd87ec))
- Update testitems does not work correctly if a __init__.robot is changed ([a426e84](https://github.com/robotcodedev/robotcode/commit/a426e840c35a17aba95f0c927b34d338d4a31889))


## [0.43.1](https://github.com/robotcodedev/robotcode/compare/v0.43.0..v0.43.1) - 2023-06-15

### Bug Fixes

- Intellisense doesn't work when importing yml file with variables #143 ([b19eea1](https://github.com/robotcodedev/robotcode/commit/b19eea19541e5bcfd22b7e4a79f14fb9eb43061a))


## [0.43.0](https://github.com/robotcodedev/robotcode/compare/v0.42.0..v0.43.0) - 2023-06-14

### Bug Fixes

- Checks for robot version 6.1 ([e16f09c](https://github.com/robotcodedev/robotcode/commit/e16f09caa359995c052606a46c9843fba0591731))
- Hover over a tasks shows "task" in hint and not "test case" ([457f3ae](https://github.com/robotcodedev/robotcode/commit/457f3ae1409d58c5c6c5844c714559ce161fa5dd))
- Correct highlightning `*** Tasks ***` and `*** Settings ***` ([c4cfdb9](https://github.com/robotcodedev/robotcode/commit/c4cfdb97b1e0b60561573dd94ddac5631093a7c6))


### Features

- Support for new `--parseinclude` option in robot config ([dfd88d8](https://github.com/robotcodedev/robotcode/commit/dfd88d87ed08d1065a26eb6f29c1eec6a03272f6))
- Support for new RF 6.1 `--parse-include` option for discovering and executing tests ([607cf8d](https://github.com/robotcodedev/robotcode/commit/607cf8db2777b5d11db89e830131261d60581b0f))
- Enable importing and completion of `.rest`, `.rsrc` and `.json` resource extensions (not parsing) ([3df22dd](https://github.com/robotcodedev/robotcode/commit/3df22ddcb703983b56d0756fef29d06cb2960009))
- Support for importing `.json` files in RF 6.1 ([0f84c4e](https://github.com/robotcodedev/robotcode/commit/0f84c4ec1d9a897aa25ab37fff702f8feea50cf4))


### Testing

- Update tests für RF 6.1rc1 ([3d8a702](https://github.com/robotcodedev/robotcode/commit/3d8a702b3a4e838c5e7e23de4b37b4945dd9f377))
- Update regression tests ([b37bf58](https://github.com/robotcodedev/robotcode/commit/b37bf587e19d4c4bf1846a341572abdf3c1bcf63))


## [0.42.0](https://github.com/robotcodedev/robotcode/compare/v0.41.0..v0.42.0) - 2023-06-05

### Bug Fixes

- Resolving variable values in hover for RF 6.1 ([0acdd21](https://github.com/robotcodedev/robotcode/commit/0acdd21f24266700d87b046deead43aa33aae90b))
- Compatibility with Python 3.12 ([3ec4d23](https://github.com/robotcodedev/robotcode/commit/3ec4d23cd4e4f2b04d5a1b792131b90ef523b8e8))


### Features

- Support for new `--parseinclude` option in robot config ([6b84986](https://github.com/robotcodedev/robotcode/commit/6b84986e7109c36b5df81c0ff56f84665a855c6a))


### Refactor

- Fix some mypy warnings ([8622099](https://github.com/robotcodedev/robotcode/commit/862209929bfcfe56dbd6995851858f56bd43c02d))


### Testing

- Fix some tests ([39dcfd9](https://github.com/robotcodedev/robotcode/commit/39dcfd95cb4ad10b89b5028a68ce142a8b58816a))


## [0.41.0](https://github.com/robotcodedev/robotcode/compare/v0.40.0..v0.41.0) - 2023-05-23

### Bug Fixes

- Patched FileReader for discovery should respect accept_text ([c654af5](https://github.com/robotcodedev/robotcode/commit/c654af57329068e6f5dbd3350aa6f4b7ef2edc46))


### Features

- Optimize/speedup searching of files, setting `robotcode.workspace.excludePatterns` now supports gitignore like patterns ([d48b629](https://github.com/robotcodedev/robotcode/commit/d48b629a2ad77c9ee1bb67fc2ff00461b593ace3))
- New `robotcode.robotidy.ignoreGitDir` and `robotcode.robotidy.config` setting to set the config file for _robotidy_ and to ignore git files if searching for config files for _robotidy_ ([a9e9c02](https://github.com/robotcodedev/robotcode/commit/a9e9c023ed62b1fc6ab7d231c9a1c47cfb42330b))


  see also: https://robotidy.readthedocs.io/


### Refactor

- Some optimization in searching files ([5de8a17](https://github.com/robotcodedev/robotcode/commit/5de8a17ecc4d8c0a57e5b3716a88c86427963618))


## [0.40.0](https://github.com/robotcodedev/robotcode/compare/v0.39.0..v0.40.0) - 2023-05-17

### Bug Fixes

- Wrong values for command line vars ([3720109](https://github.com/robotcodedev/robotcode/commit/37201094d0a1bf10fe8ba6a66a0f08c210b9ca8a))


### Features

- Show argument infos for dynamic variables imports ([94b21fb](https://github.com/robotcodedev/robotcode/commit/94b21fb08ebd3177668a7a1f20aa27d160060515))


## [0.39.0](https://github.com/robotcodedev/robotcode/compare/v0.38.0..v0.39.0) - 2023-05-16

### Documentation

- Update config documentation ([b188b27](https://github.com/robotcodedev/robotcode/commit/b188b276f4fd1c7b65c01585127f04e5a214aee6))


### Features

- Language server now is a robotcode cli plugin and can use config files and execution profiles ([12308bb](https://github.com/robotcodedev/robotcode/commit/12308bbed1585b62885a8d699d8969a1310b7db3))
- New command `RobotCode: Select Execution Profiles` ([78f5548](https://github.com/robotcodedev/robotcode/commit/78f554899a0c50c82deeac07fc921128beef778c))


## [0.38.0](https://github.com/robotcodedev/robotcode/compare/v0.37.1..v0.38.0) - 2023-05-15

### Bug Fixes

- Use dispose instead of stop to exit language server instances ([5aba99b](https://github.com/robotcodedev/robotcode/commit/5aba99b1ad551132e8f86c138cca28694dfec545))
- Bring output console into view if robotcode discovery fails ([8bcc147](https://github.com/robotcodedev/robotcode/commit/8bcc1477b1315a7bd385d159346dd6ca95c0e57f))


### Features

- New command `discover tags` ([a8fbb22](https://github.com/robotcodedev/robotcode/commit/a8fbb22baaa1a667c786fb8c71c50cd76b6d6bc4))


### Refactor

- Fix some ruff warnings ([1161451](https://github.com/robotcodedev/robotcode/commit/11614517b922652d7475b21ac33d2d2989a62ce0))


## [0.37.1](https://github.com/robotcodedev/robotcode/compare/v0.37.0..v0.37.1) - 2023-05-11

### Bug Fixes

- **discover:** Wrong filename in diagnostics message on update single document ([dee91c4](https://github.com/robotcodedev/robotcode/commit/dee91c42a01f012efbf5e24a233fb80895ce0910))


## [0.37.0](https://github.com/robotcodedev/robotcode/compare/v0.36.0..v0.37.0) - 2023-05-10

### Bug Fixes

- **langserver:** Resolving variables as variable import arguments does not work correctly ([a7ba998](https://github.com/robotcodedev/robotcode/commit/a7ba9980279c95eea3bbb6891fa29eb5af26222e))
- Some correction in completions for robotframework >= 6.1 ([058e187](https://github.com/robotcodedev/robotcode/commit/058e187e587403f39657e5e23276b432996a4b07))


### Features

- Test discovery now runs in a separate process with the `robotcode discover` command, this supports also prerunmodifiers and RF 6.1 custom parsers ([ee5f0fb](https://github.com/robotcodedev/robotcode/commit/ee5f0fb8dd70232cc50b78e73b180adb906c57d2))
- Reintroduce of updating the tests when typing ([94053fc](https://github.com/robotcodedev/robotcode/commit/94053fca5ad40300c8e57bebbecc2523b7d26d94))


### Refactor

- Correct some help texts and printing of output ([b225a73](https://github.com/robotcodedev/robotcode/commit/b225a73a4c4e17ddb0e5265c04a052cf6050988b))


## [0.36.0](https://github.com/robotcodedev/robotcode/compare/v0.35.0..v0.36.0) - 2023-05-01

### Features

- Select run profiles in test explorer ([a7f8408](https://github.com/robotcodedev/robotcode/commit/a7f840801656b96fc5dca68b69a112c17f7a08bc))
- Simple `discover all` command ([a1d8b84](https://github.com/robotcodedev/robotcode/commit/a1d8b84349193be58432ec883e1c5dbf0887f64e))


  shows which tests are executed without running them.


## [0.35.0](https://github.com/robotcodedev/robotcode/compare/v0.34.1..v0.35.0) - 2023-04-25

### Bug Fixes

- **debug-launcher:** Switch back to `stdio` communication, because this does not work on Windows with python <3.8 ([6b0e96e](https://github.com/robotcodedev/robotcode/commit/6b0e96efebeec42d014f81d70573fc075a19bd5f))


### Features

- **runner:** Add `run` alias for `robot` command in cli ([9b782cc](https://github.com/robotcodedev/robotcode/commit/9b782ccfa0f8cd74bc5166a0c816e63dc1840796))


## [0.34.1](https://github.com/robotcodedev/robotcode/compare/v0.34.0..v0.34.1) - 2023-04-21

### Bug Fixes

- Some code scanning alerts ([61771f8](https://github.com/robotcodedev/robotcode/commit/61771f82ba42100f798a7cf9ae494959ea9af77e))


## [0.34.0](https://github.com/robotcodedev/robotcode/compare/v0.33.0..v0.34.0) - 2023-04-20

### Bug Fixes

- Correct toml json schema urls ([bf4def7](https://github.com/robotcodedev/robotcode/commit/bf4def70e487437c3629085485688c540f792d54))


### Features

- **debugger:** Refactored robotcode debugger to support debugging/running tests with robotcode's configurations and profiles, also command line tool changes. ([69131e6](https://github.com/robotcodedev/robotcode/commit/69131e6a65fd82de7db1f445bfd0b6991bfac951))

  The command line `robotcode.debugger` is deprectated and do not support configs and profiles, to use the full feature set use `robotcode debug` to start the debug server.

  By default `robotcode debug` starts a debug session and waits for incoming connections.

- **runner:** Implement command line options to select tests/tasks/suites by longname ([d2cb7dc](https://github.com/robotcodedev/robotcode/commit/d2cb7dc1daff8932003b013dc1c069356194050c))


### Refactor

- Create robotcode bundled interface ([1126605](https://github.com/robotcodedev/robotcode/commit/1126605c52fb17993c875358e8e1ddca2a8ea224))
- Fix some ruff errors ([38aa2d2](https://github.com/robotcodedev/robotcode/commit/38aa2d230ae785719eae86785ed0fd4b66036ee8))


## [0.33.0](https://github.com/robotcodedev/robotcode/compare/v0.32.3..v0.33.0) - 2023-04-09

### Bug Fixes

- End positions on formatting ([a87ba80](https://github.com/robotcodedev/robotcode/commit/a87ba805ad800f91067c912fa6984605ec1bebe4))


### Features

- Improved Handling of UTF-16 encoded multibyte characters, e.g. emojis are now handled correctly ([d17e79c](https://github.com/robotcodedev/robotcode/commit/d17e79c258837cc24c9f69f30358c4a7c1adfed9))


## [0.32.3](https://github.com/robotcodedev/robotcode/compare/v0.32.2..v0.32.3) - 2023-04-07

### Bug Fixes

- Correct formatting with robotframework-tidy, also support tidy 4.0 reruns now, closes #124 ([3b4c0e8](https://github.com/robotcodedev/robotcode/commit/3b4c0e87dec4a1cb62800ccd70c3d7b01b9e7ce9))


### Documentation

- Use markdown style examples in commandline doc ([7575a77](https://github.com/robotcodedev/robotcode/commit/7575a77a73bceeb99ee3a2ffba7e06f8d7072e19))


### Features

- **robotcode:** Add new command to show informations about configuration setttings ([47216e9](https://github.com/robotcodedev/robotcode/commit/47216e9179a6a1744fee95b3b25d98734281c674))


### Testing

- Fix DeprecationWarning for some tests ([6e70fc3](https://github.com/robotcodedev/robotcode/commit/6e70fc3f860fa21912117b21a4317a99699faefb))


## [0.32.2](https://github.com/robotcodedev/robotcode/compare/v0.32.1..v0.32.2) - 2023-04-05

### Bug Fixes

- Update git versions script ([fb16818](https://github.com/robotcodedev/robotcode/commit/fb16818b61068659b8607eee585a705d8e2caf26))


## [0.32.1](https://github.com/robotcodedev/robotcode/compare/v0.32.0..v0.32.1) - 2023-04-05

### Bug Fixes

- Dataclasses from dict respects Literals also for Python 3.8 and 3.9 ([73b7b1c](https://github.com/robotcodedev/robotcode/commit/73b7b1c64e6842249d8278d71ccea76f8118b810))


## [0.32.0](https://github.com/robotcodedev/robotcode/compare/v0.31.0..v0.32.0) - 2023-04-05

### Features

- Add command for robots _testdoc_ ([dd6d758](https://github.com/robotcodedev/robotcode/commit/dd6d7583f5075b35823b83b8a7aa828507904013))
- Allow expression for str options, better handling of tag:<pattern>, name:<pattern> options ([d037ddb](https://github.com/robotcodedev/robotcode/commit/d037ddbd9d44ccbb501af3854cf8a7d7df607ddd))


### Refactor

- Switch to src layout ([40d6262](https://github.com/robotcodedev/robotcode/commit/40d626280721068aed09d84181b3d4c5b31cc9f8))


## [0.31.0](https://github.com/robotcodedev/robotcode/compare/v0.30.0..v0.31.0) - 2023-03-30

### Documentation

- Introduce mike for versioned documentation ([4c6e9ac](https://github.com/robotcodedev/robotcode/commit/4c6e9ac0830830c80a543bb197b39f19f32a1203))


### Features

- **robotcode:** Add commands to get informations about configurations and profiles ([edc4ee5](https://github.com/robotcodedev/robotcode/commit/edc4ee5e5b41f397918b9476ec7e6e09f0bfe53c))
- New commands robot, rebot, libdoc for robotcode.runner ([25027fa](https://github.com/robotcodedev/robotcode/commit/25027faf3e3b7bb14596d90dd0ec1f43af922522))
- Profiles can now be enabled or disabled, also with a condition. Profiles can now also be selected with a wildcard pattern. ([4282f02](https://github.com/robotcodedev/robotcode/commit/4282f02bab4b483d74d486e983ec9a1f606fd3d7))


### Refactor

- Add more configuration options, update schema, new command config ([5816669](https://github.com/robotcodedev/robotcode/commit/5816669096fc90cfd58f947e361b2e36d725902e))
- Move the config command to robotcode package ([90c6c25](https://github.com/robotcodedev/robotcode/commit/90c6c2545dc6f2077d6aa2f2670a3570d134a673))


### Testing

- Correct mypy error in tests ([37dca4d](https://github.com/robotcodedev/robotcode/commit/37dca4d57871d882b40bbc31cb6c7fa0055eafe3))
- Add bundled to be ignored in pytest discovery ([c008005](https://github.com/robotcodedev/robotcode/commit/c0080059b9c9133e531b337492b71cbd07437962))


## [0.30.0](https://github.com/robotcodedev/robotcode/compare/v0.29.0..v0.30.0) - 2023-03-22

### Features

- **robotcode-runner:** Robotcode-runner now supports all features, but not all robot options are supported ([1b7affb](https://github.com/robotcodedev/robotcode/commit/1b7affbf954dbec8eaf924557272105e59eb5c84))


### Refactor

- Implement robot.toml config file and runner ([cff5c81](https://github.com/robotcodedev/robotcode/commit/cff5c81392c671509a76f4e19bbf0a49775b3e4c))


## [0.29.0](https://github.com/robotcodedev/robotcode/compare/v0.28.4..v0.29.0) - 2023-03-20

### Features

- Support for Refresh Tests button in test explorer ([0b27713](https://github.com/robotcodedev/robotcode/commit/0b277134101f65cd57e6980105137ca7c0faa69f))


## [0.28.4](https://github.com/robotcodedev/robotcode/compare/v0.28.3..v0.28.4) - 2023-03-19

### Bug Fixes

- Update regression tests ([59b782d](https://github.com/robotcodedev/robotcode/commit/59b782d434764a564521832f375ce062ed155842))


## [0.28.3](https://github.com/robotcodedev/robotcode/compare/v0.28.2..v0.28.3) - 2023-03-19

### Bug Fixes

- Correct discovering for RobotFramework 6.1a1 ([99aa82d](https://github.com/robotcodedev/robotcode/commit/99aa82de7d8b67d6acae1d2131351ff9354c4a4f))
- Correct analysing keywords with embedded arguments for RF >= 6.1 ([ef0b51f](https://github.com/robotcodedev/robotcode/commit/ef0b51f0bae83194a20a45d7cb07a4a6ac2b4f1c))


### Documentation

- Start documentation with mkdocs ([381dcfe](https://github.com/robotcodedev/robotcode/commit/381dcfea90d5a2edd1bc3cf4c78d3d6d0c660784))


## [0.28.2](https://github.com/robotcodedev/robotcode/compare/v0.28.1..v0.28.2) - 2023-03-10

### Bug Fixes

- Correct version of robotcode runner ([1ba8590](https://github.com/robotcodedev/robotcode/commit/1ba85902bfe8ab2c737658757e8fc76bf7cd19ca))


### Testing

- Add tests for code action show documentation ([e692680](https://github.com/robotcodedev/robotcode/commit/e6926808a725cd7794ad9f8717bf36ecd17a5265))


## [0.28.1](https://github.com/robotcodedev/robotcode/compare/v0.28.0..v0.28.1) - 2023-03-10

### Bug Fixes

- Source actions are missing in the context menu for versions #129 ([dd6202a](https://github.com/robotcodedev/robotcode/commit/dd6202af03e9ff09a0140d1d0d5da40db20410a8))


## [0.28.0](https://github.com/robotcodedev/robotcode/compare/v0.27.2..v0.28.0) - 2023-03-09

### Bug Fixes

- Return codes for command line tools now uses sys.exit with return codes ([b6ad7dd](https://github.com/robotcodedev/robotcode/commit/b6ad7dd75276e65ffab9c8acb2c24e0750a93791))
- #125 Robot Code crashes with a variables file containing a Dict[str, Callable] ([7e0b55c](https://github.com/robotcodedev/robotcode/commit/7e0b55c65609ba37c928a636d0b764ddbb2ae57d))


### Documentation

- Correct readme's ([f09880b](https://github.com/robotcodedev/robotcode/commit/f09880ba32547e00374a5af2d5e27d19ec83add9))


### Features

- Debugger is now started from bundled/tool/debugger if available ([4b04c7a](https://github.com/robotcodedev/robotcode/commit/4b04c7a0524ba7804a7c4c01e1d2107e5ee188ae))


## [0.27.2](https://github.com/robotcodedev/robotcode/compare/v0.27.1..v0.27.2) - 2023-03-06

### Bug Fixes

- The debugger no longer requires a dependency on the language server ([c5199ee](https://github.com/robotcodedev/robotcode/commit/c5199ee7111d17f44334464d6a6d24965adb2eea))
- Unknown workspace edit change received at renaming ([48aef63](https://github.com/robotcodedev/robotcode/commit/48aef63b9085cb90fdbdc42d18ae5843c7774d69))


### Refactor

- Some big refactoring, introdude robotcode.runner project ([d0f71fe](https://github.com/robotcodedev/robotcode/commit/d0f71feb4ce529e2025ac99079d6fff45803084a))


## [0.27.1](https://github.com/robotcodedev/robotcode/compare/v0.27.0..v0.27.1) - 2023-03-01

### Documentation

- Update badges in README's ([78bbf7a](https://github.com/robotcodedev/robotcode/commit/78bbf7a6cf3e2b79ca6500a576f25e48f2fae7e8))


## [0.27.0](https://github.com/robotcodedev/robotcode/compare/v0.26.2..v0.27.0) - 2023-03-01

### Features

- Split python code into several packages, now for instance robotcode.debugger can be installed standalone ([01ac842](https://github.com/robotcodedev/robotcode/commit/01ac84237fccc40be658e0f35d4f7b00942f8461))


### Refactor

- Introduce bundled/libs/tool folders and move python source to src folder ([478c93a](https://github.com/robotcodedev/robotcode/commit/478c93a4c644856d5b136ccbdcab234ff4f4bac7))


  this is to prepare the splitting of one big python package to several smaller packages, i.e. to install the robotcode.debugger standalone without other dependencies


### Testing

- Don't run the LS tests in another thread ([c464edc](https://github.com/robotcodedev/robotcode/commit/c464edc4b697f4663478154985d4acba569c6a52))


## [0.26.2](https://github.com/robotcodedev/robotcode/compare/v0.26.1..v0.26.2) - 2023-02-25

### Bug Fixes

- Publish script ([0d3dd8f](https://github.com/robotcodedev/robotcode/commit/0d3dd8fb7bac3d26cccb5fa60be3d4284bc8d9b7))


## [0.26.1](https://github.com/robotcodedev/robotcode/compare/v0.26.0..v0.26.1) - 2023-02-25

### Bug Fixes

- Github workflow ([a235b86](https://github.com/robotcodedev/robotcode/commit/a235b864139c911cf593b58843c4d2726f770cf5))


## [0.26.0](https://github.com/robotcodedev/robotcode/compare/v0.25.2-beta.1..v0.26.0) - 2023-02-25

### Bug Fixes

- Correct error message if variable import not found ([a4b8fbb](https://github.com/robotcodedev/robotcode/commit/a4b8fbb6d830dfb92c59b17b7ac14fafe88558ed))


### Features

- Switch to [hatch](https://hatch.pypa.io) build tool and bigger internal refactorings ([bc1c99b](https://github.com/robotcodedev/robotcode/commit/bc1c99bd8d70ec0b6a70257575d9dd4c44793f96))


### Refactor

- Generate lsp types from json model ([8b7af4f](https://github.com/robotcodedev/robotcode/commit/8b7af4f1081ea4fe9eca6516c762d9dfb2b7ed9e))


### Testing

- Introduce timeout/wait_for for langserver tests ([b9f4d5e](https://github.com/robotcodedev/robotcode/commit/b9f4d5e219d2f6c5a335d12c131ee0c8ced9d475))
- Decrease timeout for language server tests ([9790823](https://github.com/robotcodedev/robotcode/commit/979082354e4fdaadd01d2eefe5071edafaf3d4ee))
- Increate test timeouts and enable pytest logging ([1d6a980](https://github.com/robotcodedev/robotcode/commit/1d6a980f7f629abd0b7951566621868b4b55ad29))
- Disable run_workspace_diagnostics in unit tests ([2348b0e](https://github.com/robotcodedev/robotcode/commit/2348b0e641cbcfe8ef06ef31766e6a3954070e52))
- Increase timeout for langserver tests ([1224dae](https://github.com/robotcodedev/robotcode/commit/1224dae0a020d6d48a8a3a8e4d538bfc51c1726e))
- Use Lock instead of RLock for AsyncLRUCache ([c36683e](https://github.com/robotcodedev/robotcode/commit/c36683e3d113f1c31fc9e47196797746b4cd7fc8))
- Remove cache dir before running tests ([5a9323b](https://github.com/robotcodedev/robotcode/commit/5a9323b6c3f402c8abcd3129ccb92553fee40716))
- Ignore errors if remove cache dir ([c670989](https://github.com/robotcodedev/robotcode/commit/c67098916b5b7d9f0050127102936c3a9ffcc18b))


## [0.25.2-beta.1](https://github.com/robotcodedev/robotcode/compare/v0.25.1..v0.25.2-beta.1) - 2023-02-07

### Documentation

- Add some badges to readme and reorder the chapters ([22120f1](https://github.com/robotcodedev/robotcode/commit/22120f16e973f61b02f04a47c29fbe6d1b5e2283))
- Add python badges to README ([c0ec329](https://github.com/robotcodedev/robotcode/commit/c0ec3290b80714ff73528082a3fd2825f1c01f59))


### Refactor

- **robotlangserver:** Optimize test discovering ([4949ba6](https://github.com/robotcodedev/robotcode/commit/4949ba6b3e6dce7f00624586fcb5db2f0a630ad1))
- **robotlangserver:** Workspace rpc methods are now running threaded ([8f8f2b9](https://github.com/robotcodedev/robotcode/commit/8f8f2b946e6fa97b6b934e8a6db30128a5351e7c))
- Fix some ruff errors and warnings, disable isort in precommit ([c144250](https://github.com/robotcodedev/robotcode/commit/c1442503d3d899c7108bfbceef17943e823e92ba))
- Replace *Generator with *Iterator ([cd96b1d](https://github.com/robotcodedev/robotcode/commit/cd96b1dd35fe5b57fd5442c107d3ee43aa87b370))
- Change logger calls with an f-string to use lambdas ([cc555e1](https://github.com/robotcodedev/robotcode/commit/cc555e1953a88a8857d69f259c07ed9b8e66434e))
- Use `list` over useless lambda in default_factories ([930fa46](https://github.com/robotcodedev/robotcode/commit/930fa466c46d6822b670459b1d1574d92bc56878))
- Fix some pytest ruff warning ([b2bff02](https://github.com/robotcodedev/robotcode/commit/b2bff02083cc16682de237390d9880a4010db051))
- Fix some flake8-return warnings ([bea720d](https://github.com/robotcodedev/robotcode/commit/bea720dbd17eaaf937168835684b9010dbe57921))
- Simplify some code ([9403f72](https://github.com/robotcodedev/robotcode/commit/9403f723526e9a1ffa7067023427f95a59ab736e))
- Fix some PIE810 errors ([59848e2](https://github.com/robotcodedev/robotcode/commit/59848e22178a7691732be22932e3562b44fdab02))
- Fix some mypy errors ([9356b32](https://github.com/robotcodedev/robotcode/commit/9356b32420a7049ba50ac76dab8bb288fcf6051a))


### Testing

- Add a copy of remote example library ([d0b2ca5](https://github.com/robotcodedev/robotcode/commit/d0b2ca5a4ed7a6b8bd7eef09764f7a072f1df47d))
- Enable pytest logging ([bf07425](https://github.com/robotcodedev/robotcode/commit/bf07425dd15ebfe0bdcd0e20f1a584705a0d2a8e))
- Remove Remote library references ([2ba0edd](https://github.com/robotcodedev/robotcode/commit/2ba0eddc6da08fb11d4ec38713c81fd0ad0b8287))
- Run discovery tests in thread ([5fe0f97](https://github.com/robotcodedev/robotcode/commit/5fe0f97673f5d249de33734315c5ef0563cffe5a))
- Run coroutines in ThreadPoolExecutor ([e4325f1](https://github.com/robotcodedev/robotcode/commit/e4325f1fcffb32c06f1bcf5c95cf1ebcab81943a))
- Disable logging ([b6e59b5](https://github.com/robotcodedev/robotcode/commit/b6e59b5473c086433ca065814bd88d2e0a3fb89c))
- Let collect data in languages server test run in his own thread ([327b122](https://github.com/robotcodedev/robotcode/commit/327b122aef03e223dd12aed5bc0bbb6324ee4a10))
- Make regtests for rf tests version dependend ([fe69626](https://github.com/robotcodedev/robotcode/commit/fe6962629edf5b90eeb4e9f4ba6a7b025498feca))


## [0.25.1](https://github.com/robotcodedev/robotcode/compare/v0.25.0..v0.25.1) - 2023-01-24

### Bug Fixes

- **vscode:** In long test runs suites with failed tests are still marked as running even though they are already finished ([942addf](https://github.com/robotcodedev/robotcode/commit/942addf005878bab9983603cd85429283eee4c6e))


### Refactor

- Add `type` parameter to end_output_group ([299658f](https://github.com/robotcodedev/robotcode/commit/299658f153738e7c7b004a61af19eb8154e53df2))


## [0.25.0](https://github.com/robotcodedev/robotcode/compare/v0.24.4..v0.25.0) - 2023-01-24

### Features

- **debugger:** New setting for `outputTimestamps` in launch and workspace configuration to enable/disable timestamps in debug console ([e3ed581](https://github.com/robotcodedev/robotcode/commit/e3ed581f99d92f2e00c1cae443b98d9d255b638b))


## [0.24.4](https://github.com/robotcodedev/robotcode/compare/v0.24.3..v0.24.4) - 2023-01-23

### Bug Fixes

- **debugger:** Show error/warning messages of python logger in debug console ([665a3ff](https://github.com/robotcodedev/robotcode/commit/665a3ffd22f28ef73bb48aa63ceaeb831b6f4ffe))


## [0.24.3](https://github.com/robotcodedev/robotcode/compare/v0.24.2..v0.24.3) - 2023-01-23

### Bug Fixes

- Set env and pythonpath erlier in lifecycle to prevent that sometime analyses fails because of python path is not correct ([4183391](https://github.com/robotcodedev/robotcode/commit/41833917d2311b33effa1dc2e8f654b0982c439c))


## [0.24.2](https://github.com/robotcodedev/robotcode/compare/v0.24.1..v0.24.2) - 2023-01-20

### Bug Fixes

- **robotlangserver:** Retun correct robot framework version test ([e786b76](https://github.com/robotcodedev/robotcode/commit/e786b76144718b2773ae7d0516a88969e8a6b647))


## [0.24.1](https://github.com/robotcodedev/robotcode/compare/v0.24.0..v0.24.1) - 2023-01-20

### Bug Fixes

- **robotlangserver:** Robot version string is incorrectly parsed if version has no patch ([d1afe4d](https://github.com/robotcodedev/robotcode/commit/d1afe4d6f1c10740f6ac850526b1f357653c95d2))

  correct can't get namespace diagnostics ''>=' not supported between instances of 'NoneType' and 'int'' sometimes happens

- Start diagnostics only when the language server is fully initialized ([d2bd3db](https://github.com/robotcodedev/robotcode/commit/d2bd3db3f6e4ce978fb32231d68764367426e7eb))


## [0.24.0](https://github.com/robotcodedev/robotcode/compare/v0.23.0..v0.24.0) - 2023-01-16

### Features

- **robotlangserver:** Create undefined keywords in the same file ([c607c3f](https://github.com/robotcodedev/robotcode/commit/c607c3f10b5d9382285e1bfeffdd81992336bab2))


### Refactor

- Introduce asyncio.RLock ([ab918db](https://github.com/robotcodedev/robotcode/commit/ab918db596d0502a4666816589b1674d99cbef18))
- Prepare create keywords quickfix ([b34c8bf](https://github.com/robotcodedev/robotcode/commit/b34c8bfa80be6ebe08e25e239983b18a53c81bea))


## [0.23.0](https://github.com/robotcodedev/robotcode/compare/v0.22.1..v0.23.0) - 2023-01-13

### Bug Fixes

- **robotlangserver:** Remove possible deadlock in completion ([3d17699](https://github.com/robotcodedev/robotcode/commit/3d17699587096ca49711ef98bf1273d710cd8335))


### Features

- **robotlangserver:** Highlight named args in library imports ([63b93af](https://github.com/robotcodedev/robotcode/commit/63b93af853c0b54628e6bf59a6cc54fa77d97c8d))


## [0.22.1](https://github.com/robotcodedev/robotcode/compare/v0.22.0..v0.22.1) - 2023-01-13

### Bug Fixes

- **robotlangserver:** Generating documentation view with parameters that contains .py at the at does not work ([8210bd9](https://github.com/robotcodedev/robotcode/commit/8210bd9c8bed94e61b475a2c25dc032c7bdb3d68))
- **robotlangserver:** Resolving imports with arguments in diffent files and folders but with same string representation ie. ${curdir}/blah.py now works correctly ([8c0517d](https://github.com/robotcodedev/robotcode/commit/8c0517d2c30ad395b121fde841869c994741151d))


## [0.22.0](https://github.com/robotcodedev/robotcode/compare/v0.21.4..v0.22.0) - 2023-01-12

### Features

- Add onEnter rule to split a long line closes #78 ([3efe416](https://github.com/robotcodedev/robotcode/commit/3efe4166829bd65a53dc5b5e3d33173c88258b28))


## [0.21.4](https://github.com/robotcodedev/robotcode/compare/v0.21.3..v0.21.4) - 2023-01-11

### Bug Fixes

- **robotlangserver:** Remove possible deadlock in Namespace initialization ([27d781c](https://github.com/robotcodedev/robotcode/commit/27d781c6305643b81904e4bf30b8f64a45ffa9ee))


## [0.21.3](https://github.com/robotcodedev/robotcode/compare/v0.21.2..v0.21.3) - 2023-01-10

### Bug Fixes

- **robotlangserver:** If a lock takes to long, try to cancel the lock ([75e9d66](https://github.com/robotcodedev/robotcode/commit/75e9d66572cdcb5cb144e55541b60e44fa102f7f))


## [0.21.2](https://github.com/robotcodedev/robotcode/compare/v0.21.1..v0.21.2) - 2023-01-10

### Bug Fixes

- Use markdownDescription in settings and launch configurations where needed ([229a4a6](https://github.com/robotcodedev/robotcode/commit/229a4a6c316da5606c16629617e211ecf1a9a6d4))


### Performance

- Massive overall speed improvements ([aee36d7](https://github.com/robotcodedev/robotcode/commit/aee36d7f8a4924b6c35f7055d5d6fa170db6f5de))


  Mainly from changing locks from async.Lock to threading.Lock.
  Extra: more timing statistics in log output


### Refactor

- Remove unneeded code ([a92db4d](https://github.com/robotcodedev/robotcode/commit/a92db4dd75f24cf68ed877322d65d01ab3982c37))


## [0.21.1](https://github.com/robotcodedev/robotcode/compare/v0.21.0..v0.21.1) - 2023-01-07

### Performance

- Caching of variable imports ([9d70610](https://github.com/robotcodedev/robotcode/commit/9d70610b27d3e65177d1389197d2da53bee8e73e))


## [0.21.0](https://github.com/robotcodedev/robotcode/compare/v0.20.0..v0.21.0) - 2023-01-07

### Bug Fixes

- **robotlangserver:** Loading documents hardened ([eab71f8](https://github.com/robotcodedev/robotcode/commit/eab71f87b3e16eeb34e62a811235e5126b2734cf))

  Invalid document don't break loading, initializing and analysing documents and discovering tests

- **robotlangserver:** Speedup analyser ([228ae4e](https://github.com/robotcodedev/robotcode/commit/228ae4e9a50b6cb0ad5ecb824f6b45bcb1476258))
- Generating keyword specs for keywords with empty lineno ([60d76aa](https://github.com/robotcodedev/robotcode/commit/60d76aa25c9437d1c3029322d3c576738c0406cb))
- Try to handle unknow documents as .robot files to support resources as .txt or .tsv files ([4fed028](https://github.com/robotcodedev/robotcode/commit/4fed028a42b3705568639469de24615d23152de3))


### Features

- New setting `robotcode.analysis.cache.ignoredLibraries` to define which libraries should never be cached ([5087c91](https://github.com/robotcodedev/robotcode/commit/5087c912fe2844396c0c2c30222ff215af105731))


## [0.20.0](https://github.com/robotcodedev/robotcode/compare/v0.19.1..v0.20.0) - 2023-01-06

### Bug Fixes

- **robotlangserver:** Ignore parsing errors in test discovery ([470723b](https://github.com/robotcodedev/robotcode/commit/470723b3f064ba496fb59dba600fc099901c0433))

  If a file is not valid, i.e. not in UTF-8 format, test discovery does not stop, but an error is written in the output

- **vscode-testexplorer:** Correctly combine args and paths in debug configurations ([4b7e7d5](https://github.com/robotcodedev/robotcode/commit/4b7e7d527eb209746ffe1d8ae903d44e79a4d4d3))
- Speedup loading and analysing tests ([9989edf](https://github.com/robotcodedev/robotcode/commit/9989edf8868ddd3360939b93bbaf395aa939bb85))


  Instead of waiting for diagnostics load and analyse documents one by one, load first the documents and then start analysing and discovering in different tasks/threads


### Features

- **debugger:** Add `include` and `exclude` properties to launch configurations ([f4681eb](https://github.com/robotcodedev/robotcode/commit/f4681ebedffa8f43eda31fadc80e3adc16b9572e))

  see --include and --exclude arguments from robot

- **robotlangserver:** Show keyword tags in keyword documentation ([c82b60b](https://github.com/robotcodedev/robotcode/commit/c82b60b281c70eb6aa3cb4227a494d1b1f026f12))
- **robotlangserver:** Support for robot:private keywords for RF>6.0.0 ([e24603f](https://github.com/robotcodedev/robotcode/commit/e24603f07319e2730fb59d62e1f8f4bc8c245368))

  Show warnings if you use a private keyword and prioritize not private keywords over private keywords

- **robotlangserver:** Implement embedded keyword precedence for RF 6.0, this also speedups keyword analysing ([f975be8](https://github.com/robotcodedev/robotcode/commit/f975be8d53ac2ef6a0cbcc8d69dbf815e04312e8))


### Refactor

- **debugger:** Move debugger.modifiers one level higher to shorten the commandline ([eea384d](https://github.com/robotcodedev/robotcode/commit/eea384dfc211dad2c629fe824deccd8e82b5120c))
- **robotlangserver:** Better error messages if converting from json to dataclasses ([29959ea](https://github.com/robotcodedev/robotcode/commit/29959ead0d6a7fb185eec5cebc2c0023ed9f3ac6))


## [0.19.1](https://github.com/robotcodedev/robotcode/compare/v0.19.0..v0.19.1) - 2023-01-05

### Bug Fixes

- **debugger:** Use default target if there is no target specified in launch config with purpose test ([f633cc5](https://github.com/robotcodedev/robotcode/commit/f633cc5d27e1ad7ab9cc304d3977540365848211))


## [0.19.0](https://github.com/robotcodedev/robotcode/compare/v0.18.0..v0.19.0) - 2023-01-04

### Bug Fixes

- **robotlangserver:** Don't report load workspace progress if progressmode is off ([6dca5e0](https://github.com/robotcodedev/robotcode/commit/6dca5e0f9e8380dc43f5389f7656c3b054da7ede))


### Features

- **debugger:** Possibility to disable the target `.` in a robotcode launch configurations with `null`, to append your own targets in `args` ([42e528d](https://github.com/robotcodedev/robotcode/commit/42e528d995c63efbdfa6aa3336749f4c92bbc442))
- **robotlangserver:** New setting `.analysis.cache.saveLocation` where you can specify the location where robotcode saves cached data ([22526e5](https://github.com/robotcodedev/robotcode/commit/22526e532d4294d84e894c4017a6be55deddd5e7))
- New command `Clear Cache and Restart Language Servers` ([a2ffdc6](https://github.com/robotcodedev/robotcode/commit/a2ffdc6c63150387a0bd7077cb0d31ce80e36076))


  Clears all cached data i.e library docs and restarts the language servers.


## [0.18.0](https://github.com/robotcodedev/robotcode/compare/v0.17.3..v0.18.0) - 2022-12-15

### Bug Fixes

- **robotlangserver:** Update libraries when editing not work ([9adc6c8](https://github.com/robotcodedev/robotcode/commit/9adc6c866d8164a97224bef6a6b21b867355c4ec))


### Features

- **robotlangserver:** Speedup loading of class and module libraries ([975661c](https://github.com/robotcodedev/robotcode/commit/975661c7d33d2736355be66d7e1b26979ef9b0aa))

  implement a caching mechanism to load and analyse libraries only once or update the cache if the library is changed



## [0.17.3](https://github.com/robotcodedev/robotcode/compare/v0.17.2..v0.17.3) - 2022-12-11

### Bug Fixes

- **vscode:** Some tweaks for better highlightning ([40b7512](https://github.com/robotcodedev/robotcode/commit/40b751223ea77b0c978f9252b3e946c02f9437d6))
- **vscode:** Highlightning comments in text mate mode ([1c1cb9a](https://github.com/robotcodedev/robotcode/commit/1c1cb9a22a02c89dd604418d883b570a68d199b1))


### Performance

- **robotlangserver:** Refactor some unnecessary async/await methods ([0f8c134](https://github.com/robotcodedev/robotcode/commit/0f8c1349f9bcdeb817f28247afc11c076c9747d0))
- **robotlangserver:** Speedup keyword completion ([6bcaa22](https://github.com/robotcodedev/robotcode/commit/6bcaa22ab492bad7882f5585ae852be87384f497))

  Recalcution of useable keywords is only called if imports changed, this should speedup showing the completion window for keywords



### Testing

- **all:** Switching to pytest-regtest ([c2d8384](https://github.com/robotcodedev/robotcode/commit/c2d838474591f07d217da1b7a9ef0303b66e794f))

  Switching to pytest-regtest brings massive speed to regression test

- **all:** Fix tests for python 3.11 ([07d5101](https://github.com/robotcodedev/robotcode/commit/07d510163edc9034cfd063324eadb84418d212c7))


## [0.17.2](https://github.com/robotcodedev/robotcode/compare/v0.17.1..v0.17.2) - 2022-12-09

### Bug Fixes

- **vscode:** Enhance tmLanguage to support thing  like variables, assignments,... better ([ec3fce0](https://github.com/robotcodedev/robotcode/commit/ec3fce062019ba8fa9fcdea2480d6e5be69fccf5))


## [0.17.0](https://github.com/robotcodedev/robotcode/compare/v0.16.0..v0.17.0) - 2022-12-08

### Features

- **vscode:** Add configuration defaults for `editor.tokenColorCustomizations` and `editor.semanticTokenColorCustomizations` ([ce927d9](https://github.com/robotcodedev/robotcode/commit/ce927d98565be3d481927cea64b8db630cde43d3))

  This leads to better syntax highlighting in Robotframework files.



## [0.16.0](https://github.com/robotcodedev/robotcode/compare/v0.15.1..v0.16.0) - 2022-12-08

### Bug Fixes

- **robotlangserver:** Try to hover, goto, ... for keyword with variables in names ([ec2c444](https://github.com/robotcodedev/robotcode/commit/ec2c44457d936431e62fcdb9cb5ef7ca941e3e8b))
- **vscode:** Capitalize commands categories ([b048ca4](https://github.com/robotcodedev/robotcode/commit/b048ca4a5fc3379ff4107ccfeebcbceac2785dd9))


### Features

- **robotlangserver:** Highlight embedded arguments ([d8b23e4](https://github.com/robotcodedev/robotcode/commit/d8b23e45951e660baea327b3534026da9ee27286))
- **robotlangserver:** Optimization of the analysis of keywords with embedded arguments ([0995a2e](https://github.com/robotcodedev/robotcode/commit/0995a2ee73561162b823d43c5e8077a8daa28053))
- **robotlangserver:** Highlight dictionary keys and values with different colors ([9596540](https://github.com/robotcodedev/robotcode/commit/9596540bfdf2e027c1a1963a2c8b3ae81d42485a))
- **vscode:** Add new command `Restart Language Server` ([2b4c9c6](https://github.com/robotcodedev/robotcode/commit/2b4c9c6b90520234e4277364563c37e979c2f409))

  If the extension hangs, you can try to restart only the language server of robot code instead of restart or reload vscode

- **vscode:** Provide better coloring in the debug console. ([c5de757](https://github.com/robotcodedev/robotcode/commit/c5de757ad132fb06a07be80d39c512568a18aa08))


## [0.15.0](https://github.com/robotcodedev/robotcode/compare/v0.14.5..v0.15.0) - 2022-12-07

### Bug Fixes

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


### Features

- Simplifying implementation of discovering of tests ([c8abfae](https://github.com/robotcodedev/robotcode/commit/c8abfae067b3ae98b7330bdacb8027d184df4297))


### Testing

- Add tests for workspace discovery ([61f82ce](https://github.com/robotcodedev/robotcode/commit/61f82ced19f227c311fea3b64c9b53394d92feeb))


<!-- generated by git-cliff -->
