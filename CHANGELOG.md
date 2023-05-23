# Change Log

All notable changes to the "robotcode" extension will be documented in this file.

<!--next-version-placeholder-->

## v0.41.0 (2023-05-24)
### Feature
* New `robotcode.robotidy.ignoreGitDir` and `robotcode.robotidy.config` setting to set the config file for _robotidy_ and to ignore git files if searching for config files for _robotidy_ ([`a9e9c02`](https://github.com/d-biehl/robotcode/commit/a9e9c023ed62b1fc6ab7d231c9a1c47cfb42330b))
* Optimize/speedup searching of files, setting `robotcode.workspace.excludePatterns` now supports gitignore like patterns ([`d48b629`](https://github.com/d-biehl/robotcode/commit/d48b629a2ad77c9ee1bb67fc2ff00461b593ace3))

### Fix
* Patched FileReader for discovery should respect accept_text ([`c654af5`](https://github.com/d-biehl/robotcode/commit/c654af57329068e6f5dbd3350aa6f4b7ef2edc46))

## v0.40.0 (2023-05-17)
### Feature
* Show argument infos for dynamic variables imports ([`94b21fb`](https://github.com/d-biehl/robotcode/commit/94b21fb08ebd3177668a7a1f20aa27d160060515))

### Fix
* Wrong values for command line vars ([`3720109`](https://github.com/d-biehl/robotcode/commit/37201094d0a1bf10fe8ba6a66a0f08c210b9ca8a))

## v0.39.0 (2023-05-16)
### Feature
* New command `RobotCode: Select Execution Profiles` ([`78f5548`](https://github.com/d-biehl/robotcode/commit/78f554899a0c50c82deeac07fc921128beef778c))
* Language server now is a robotcode cli plugin and can use config files and execution profiles ([`12308bb`](https://github.com/d-biehl/robotcode/commit/12308bbed1585b62885a8d699d8969a1310b7db3))

## v0.38.0 (2023-05-15)
### Feature
* New command `discover tags` ([`a8fbb22`](https://github.com/d-biehl/robotcode/commit/a8fbb22baaa1a667c786fb8c71c50cd76b6d6bc4))

### Fix
* Bring output console into view if robotcode discovery fails ([`8bcc147`](https://github.com/d-biehl/robotcode/commit/8bcc1477b1315a7bd385d159346dd6ca95c0e57f))
* Use dispose instead of stop to exit language server instances ([`5aba99b`](https://github.com/d-biehl/robotcode/commit/5aba99b1ad551132e8f86c138cca28694dfec545))

## v0.37.1 (2023-05-11)
### Fix
* **discover:** Wrong filename in diagnostics message on update single document ([`dee91c4`](https://github.com/d-biehl/robotcode/commit/dee91c42a01f012efbf5e24a233fb80895ce0910))

## v0.37.0 (2023-05-10)
### Feature
* Reintroduce of updating the tests when typing ([`94053fc`](https://github.com/d-biehl/robotcode/commit/94053fca5ad40300c8e57bebbecc2523b7d26d94))
* Test discovery now runs in a separate process with the `robotcode discover` command, this supports also prerunmodifiers and RF 6.1 custom parsers ([`ee5f0fb`](https://github.com/d-biehl/robotcode/commit/ee5f0fb8dd70232cc50b78e73b180adb906c57d2))

### Fix
* Some correction in completions for robotframework >= 6.1 ([`058e187`](https://github.com/d-biehl/robotcode/commit/058e187e587403f39657e5e23276b432996a4b07))
* **langserver:** Resolving variables as variable import arguments does not work correctly ([`a7ba998`](https://github.com/d-biehl/robotcode/commit/a7ba9980279c95eea3bbb6891fa29eb5af26222e))

## v0.36.0 (2023-05-01)
### Feature
* Simple `discover all` command ([`a1d8b84`](https://github.com/d-biehl/robotcode/commit/a1d8b84349193be58432ec883e1c5dbf0887f64e))
* Select run profiles in test explorer ([`a7f8408`](https://github.com/d-biehl/robotcode/commit/a7f840801656b96fc5dca68b69a112c17f7a08bc))

## v0.35.0 (2023-04-25)
### Feature
* **runner:** Add `run` alias for `robot` command in cli ([`9b782cc`](https://github.com/d-biehl/robotcode/commit/9b782ccfa0f8cd74bc5166a0c816e63dc1840796))

### Fix
* **debug-launcher:** Switch back to `stdio` communication, because this does not work on Windows with python <3.8 ([`6b0e96e`](https://github.com/d-biehl/robotcode/commit/6b0e96efebeec42d014f81d70573fc075a19bd5f))

## v0.34.1 (2023-04-21)
### Fix
* Some code scanning alerts ([`61771f8`](https://github.com/d-biehl/robotcode/commit/61771f82ba42100f798a7cf9ae494959ea9af77e))

## v0.34.0 (2023-04-20)
### Feature
* **debugger:** Refactored robotcode debugger to support debugging/running tests with robotcode's configurations and profiles, also command line tool changes. ([`69131e6`](https://github.com/d-biehl/robotcode/commit/69131e6a65fd82de7db1f445bfd0b6991bfac951))

### Fix
* Correct toml json schema urls ([`bf4def7`](https://github.com/d-biehl/robotcode/commit/bf4def70e487437c3629085485688c540f792d54))

## v0.33.0 (2023-04-09)
### Feature
* Improved Handling of UTF-16 encoded multibyte characters, e.g. emojis are now handled correctly ([`d17e79c`](https://github.com/d-biehl/robotcode/commit/d17e79c258837cc24c9f69f30358c4a7c1adfed9))

### Fix
* End positions on formatting ([`a87ba80`](https://github.com/d-biehl/robotcode/commit/a87ba805ad800f91067c912fa6984605ec1bebe4))

## v0.32.3 (2023-04-07)
### Fix
* Correct formatting with robotframework-tidy, also support tidy 4.0 reruns now, closes #124 ([`3b4c0e8`](https://github.com/d-biehl/robotcode/commit/3b4c0e87dec4a1cb62800ccd70c3d7b01b9e7ce9))

## v0.32.2 (2023-04-05)
### Fix
* Update git versions script ([`fb16818`](https://github.com/d-biehl/robotcode/commit/fb16818b61068659b8607eee585a705d8e2caf26))

## v0.32.1 (2023-04-05)
### Fix
* Dataclasses from dict respects Literals also for Python 3.8 and 3.9 ([`73b7b1c`](https://github.com/d-biehl/robotcode/commit/73b7b1c64e6842249d8278d71ccea76f8118b810))

## v0.32.0 (2023-04-05)
### Feature
* Allow expression for str options, better handling of tag:<pattern>, name:<pattern> options ([`d037ddb`](https://github.com/d-biehl/robotcode/commit/d037ddbd9d44ccbb501af3854cf8a7d7df607ddd))
* Add command for robots _testdoc_ ([`dd6d758`](https://github.com/d-biehl/robotcode/commit/dd6d7583f5075b35823b83b8a7aa828507904013))

## v0.31.0 (2023-03-30)
### Feature
* Profiles can now be enabled or disabled, also with a condition. Profiles can now also be selected with a wildcard pattern. ([`4282f02`](https://github.com/d-biehl/robotcode/commit/4282f02bab4b483d74d486e983ec9a1f606fd3d7))
* New commands robot, rebot, libdoc for robotcode.runner ([`25027fa`](https://github.com/d-biehl/robotcode/commit/25027faf3e3b7bb14596d90dd0ec1f43af922522))
* **robotcode:** Add commands to get informations about configurations and profiles ([`edc4ee5`](https://github.com/d-biehl/robotcode/commit/edc4ee5e5b41f397918b9476ec7e6e09f0bfe53c))

### Documentation
* Introduce mike for versioned documentation ([`4c6e9ac`](https://github.com/d-biehl/robotcode/commit/4c6e9ac0830830c80a543bb197b39f19f32a1203))

## v0.30.0 (2023-03-22)
### Feature
* **robotcode-runner:** Robotcode-runner now supports all features, but not all robot options are supported ([`1b7affb`](https://github.com/d-biehl/robotcode/commit/1b7affbf954dbec8eaf924557272105e59eb5c84))

## v0.29.0 (2023-03-21)
### Feature
* Support for Refresh Tests button in test explorer ([`0b27713`](https://github.com/d-biehl/robotcode/commit/0b277134101f65cd57e6980105137ca7c0faa69f))

## v0.28.4 (2023-03-19)
### Fix
* Update regression tests ([`59b782d`](https://github.com/d-biehl/robotcode/commit/59b782d434764a564521832f375ce062ed155842))

## v0.28.3 (2023-03-19)
### Fix
* Correct analysing keywords with embedded arguments for RF >= 6.1 ([`ef0b51f`](https://github.com/d-biehl/robotcode/commit/ef0b51f0bae83194a20a45d7cb07a4a6ac2b4f1c))
* Correct discovering for RobotFramework 6.1a1 ([`99aa82d`](https://github.com/d-biehl/robotcode/commit/99aa82de7d8b67d6acae1d2131351ff9354c4a4f))

## v0.28.2 (2023-03-10)
### Fix
* Correct version of robotcode runner ([`1ba8590`](https://github.com/d-biehl/robotcode/commit/1ba85902bfe8ab2c737658757e8fc76bf7cd19ca))

## v0.28.1 (2023-03-10)
### Fix
* Source actions are missing in the context menu for versions #129 ([`dd6202a`](https://github.com/d-biehl/robotcode/commit/dd6202af03e9ff09a0140d1d0d5da40db20410a8))

## v0.28.0 (2023-03-09)
### Feature
* Debugger is now started from bundled/tool/debugger if available ([`4b04c7a`](https://github.com/d-biehl/robotcode/commit/4b04c7a0524ba7804a7c4c01e1d2107e5ee188ae))

### Fix
* #125 Robot Code crashes with a variables file containing a Dict[str, Callable] ([`7e0b55c`](https://github.com/d-biehl/robotcode/commit/7e0b55c65609ba37c928a636d0b764ddbb2ae57d))
* Return codes for command line tools now uses sys.exit with return codes ([`b6ad7dd`](https://github.com/d-biehl/robotcode/commit/b6ad7dd75276e65ffab9c8acb2c24e0750a93791))

## v0.27.2 (2023-03-06)
### Fix
* Unknown workspace edit change received at renaming ([`48aef63`](https://github.com/d-biehl/robotcode/commit/48aef63b9085cb90fdbdc42d18ae5843c7774d69))
* The debugger no longer requires a dependency on the language server ([`c5199ee`](https://github.com/d-biehl/robotcode/commit/c5199ee7111d17f44334464d6a6d24965adb2eea))

## v0.27.1 (2023-03-01)


## v0.27.0 (2023-03-01)
### Feature
* Split python code into several packages, now for instance robotcode.debugger can be installed standalone ([`01ac842`](https://github.com/d-biehl/robotcode/commit/01ac84237fccc40be658e0f35d4f7b00942f8461))

## v0.26.2 (2023-02-25)
### Fix
* Publish script ([`0d3dd8f`](https://github.com/d-biehl/robotcode/commit/0d3dd8fb7bac3d26cccb5fa60be3d4284bc8d9b7))

## v0.26.1 (2023-02-25)
### Fix
* Github workflow ([`a235b86`](https://github.com/d-biehl/robotcode/commit/a235b864139c911cf593b58843c4d2726f770cf5))

## v0.26.0 (2023-02-25)
### Feature
* Switch to [hatch](https://hatch.pypa.io) build tool and bigger internal refactorings ([`bc1c99b`](https://github.com/d-biehl/robotcode/commit/bc1c99bd8d70ec0b6a70257575d9dd4c44793f96))

### Fix
* Correct error message if variable import not found ([`a4b8fbb`](https://github.com/d-biehl/robotcode/commit/a4b8fbb6d830dfb92c59b17b7ac14fafe88558ed))

## v0.25.3-beta.2 (2023-02-25)
### Hint
* this is just a dummy release

## v0.25.2-beta.1 (2023-02-07)
### Documentation
* Add python badges to README ([`c0ec329`](https://github.com/d-biehl/robotcode/commit/c0ec3290b80714ff73528082a3fd2825f1c01f59))
* Add some badges to readme and reorder the chapters ([`22120f1`](https://github.com/d-biehl/robotcode/commit/22120f16e973f61b02f04a47c29fbe6d1b5e2283))

## v0.25.1 (2023-01-24)
### Fix
* **vscode:** In long test runs suites with failed tests are still marked as running even though they are already finished ([`942addf`](https://github.com/d-biehl/robotcode/commit/942addf005878bab9983603cd85429283eee4c6e))

## v0.25.0 (2023-01-24)
### Feature
* **debugger:** New setting for `outputTimestamps` in launch and workspace configuration to enable/disable timestamps in debug console ([`e3ed581`](https://github.com/d-biehl/robotcode/commit/e3ed581f99d92f2e00c1cae443b98d9d255b638b))

## v0.24.4 (2023-01-24)
### Fix
* **debugger:** Show error/warning messages of python logger in debug console ([`665a3ff`](https://github.com/d-biehl/robotcode/commit/665a3ffd22f28ef73bb48aa63ceaeb831b6f4ffe))

## v0.24.3 (2023-01-23)
### Fix
* Set env and pythonpath erlier in lifecycle to prevent that sometime analyses fails because of python path is not correct ([`4183391`](https://github.com/d-biehl/robotcode/commit/41833917d2311b33effa1dc2e8f654b0982c439c))

## v0.24.2 (2023-01-20)
### Fix
* **robotlangserver:** Retun correct robot framework version test ([`e786b76`](https://github.com/d-biehl/robotcode/commit/e786b76144718b2773ae7d0516a88969e8a6b647))

## v0.24.1 (2023-01-20)
### Fix
* **robotlangserver:** Robot version string is incorrectly parsed if version has no patch ([`d1afe4d`](https://github.com/d-biehl/robotcode/commit/d1afe4d6f1c10740f6ac850526b1f357653c95d2))
* Start diagnostics only when the language server is fully initialized ([`d2bd3db`](https://github.com/d-biehl/robotcode/commit/d2bd3db3f6e4ce978fb32231d68764367426e7eb))

## v0.24.0 (2023-01-16)
### Feature
* **robotlangserver:** Create undefined keywords in the same file ([`c607c3f`](https://github.com/d-biehl/robotcode/commit/c607c3f10b5d9382285e1bfeffdd81992336bab2))

## v0.23.0 (2023-01-13)
### Feature
* **robotlangserver:** Highlight named args in library imports ([`63b93af`](https://github.com/d-biehl/robotcode/commit/63b93af853c0b54628e6bf59a6cc54fa77d97c8d))

### Fix
* **robotlangserver:** Remove possible deadlock in completion ([`3d17699`](https://github.com/d-biehl/robotcode/commit/3d17699587096ca49711ef98bf1273d710cd8335))

## v0.22.1 (2023-01-13)
### Fix
* **robotlangserver:** Resolving imports with arguments in diffent files and folders but with same string representation ie. ${curdir}/blah.py now works correctly ([`8c0517d`](https://github.com/d-biehl/robotcode/commit/8c0517d2c30ad395b121fde841869c994741151d))
* **robotlangserver:** Generating documentation view with parameters that contains .py at the at does not work ([`8210bd9`](https://github.com/d-biehl/robotcode/commit/8210bd9c8bed94e61b475a2c25dc032c7bdb3d68))

## v0.22.0 (2023-01-12)
### Feature
* Add onEnter rule to split a long line closes #78 ([`3efe416`](https://github.com/d-biehl/robotcode/commit/3efe4166829bd65a53dc5b5e3d33173c88258b28))

## v0.21.4 (2023-01-11)
### Fix
* **robotlangserver:** Remove possible deadlock in Namespace initialization ([`27d781c`](https://github.com/d-biehl/robotcode/commit/27d781c6305643b81904e4bf30b8f64a45ffa9ee))

## v0.21.3 (2023-01-10)
### Fix
* **robotlangserver:** If a lock takes to long, try to cancel the lock ([`75e9d66`](https://github.com/d-biehl/robotcode/commit/75e9d66572cdcb5cb144e55541b60e44fa102f7f))

## v0.21.2 (2023-01-10)
### Fix
* Use markdownDescription in settings and launch configurations where needed ([`229a4a6`](https://github.com/d-biehl/robotcode/commit/229a4a6c316da5606c16629617e211ecf1a9a6d4))

### Performance
* Massive overall speed improvements ([`aee36d7`](https://github.com/d-biehl/robotcode/commit/aee36d7f8a4924b6c35f7055d5d6fa170db6f5de))

## v0.21.1 (2023-01-07)
### Performance
* Caching of variable imports ([`9d70610`](https://github.com/d-biehl/robotcode/commit/9d70610b27d3e65177d1389197d2da53bee8e73e))

## v0.21.0 (2023-01-07)
### Feature
* New setting `robotcode.analysis.cache.ignoredLibraries` to define which libraries should never be cached ([`5087c91`](https://github.com/d-biehl/robotcode/commit/5087c912fe2844396c0c2c30222ff215af105731))

### Fix
* **robotlangserver:** Speedup analyser ([`228ae4e`](https://github.com/d-biehl/robotcode/commit/228ae4e9a50b6cb0ad5ecb824f6b45bcb1476258))
* Try to handle unknow documents as .robot files to support resources as .txt or .tsv files ([`4fed028`](https://github.com/d-biehl/robotcode/commit/4fed028a42b3705568639469de24615d23152de3))
* **robotlangserver:** Loading documents hardened ([`eab71f8`](https://github.com/d-biehl/robotcode/commit/eab71f87b3e16eeb34e62a811235e5126b2734cf))
* Generating keyword specs for keywords with empty lineno ([`60d76aa`](https://github.com/d-biehl/robotcode/commit/60d76aa25c9437d1c3029322d3c576738c0406cb))

## v0.20.0 (2023-01-06)
### Feature
* **robotlangserver:** Implement embedded keyword precedence for RF 6.0, this also speedups keyword analysing ([`f975be8`](https://github.com/d-biehl/robotcode/commit/f975be8d53ac2ef6a0cbcc8d69dbf815e04312e8))
* **robotlangserver:** Support for robot:private keywords for RF>6.0.0 ([`e24603f`](https://github.com/d-biehl/robotcode/commit/e24603f07319e2730fb59d62e1f8f4bc8c245368))
* **robotlangserver:** Show keyword tags in keyword documentation ([`c82b60b`](https://github.com/d-biehl/robotcode/commit/c82b60b281c70eb6aa3cb4227a494d1b1f026f12))
* **debugger:** Add `include` and `exclude` properties to launch configurations ([`f4681eb`](https://github.com/d-biehl/robotcode/commit/f4681ebedffa8f43eda31fadc80e3adc16b9572e))

### Fix
* **robotlangserver:**  Ignore parsing errors in test discovery ([`470723b`](https://github.com/d-biehl/robotcode/commit/470723b3f064ba496fb59dba600fc099901c0433))
* **vscode-testexplorer:** Correctly combine args and paths in debug configurations ([`4b7e7d5`](https://github.com/d-biehl/robotcode/commit/4b7e7d527eb209746ffe1d8ae903d44e79a4d4d3))
* Speedup loading and analysing tests ([`9989edf`](https://github.com/d-biehl/robotcode/commit/9989edf8868ddd3360939b93bbaf395aa939bb85))

## v0.19.1 (2023-01-05)
### Fix
* **debugger:** Use default target if there is no target specified in launch config with purpose test ([`f633cc5`](https://github.com/d-biehl/robotcode/commit/f633cc5d27e1ad7ab9cc304d3977540365848211))

## v0.19.0 (2023-01-05)
### Feature
* New command `Clear Cache and Restart Language Servers` ([`a2ffdc6`](https://github.com/d-biehl/robotcode/commit/a2ffdc6c63150387a0bd7077cb0d31ce80e36076))
* **debugger:** Possibility to disable the target `.` in a robotcode launch configurations with `null`, to append your own targets in `args` ([`42e528d`](https://github.com/d-biehl/robotcode/commit/42e528d995c63efbdfa6aa3336749f4c92bbc442))
* **robotlangserver:** New setting `.analysis.cache.saveLocation` where you can specify the location where robotcode saves cached data ([`22526e5`](https://github.com/d-biehl/robotcode/commit/22526e532d4294d84e894c4017a6be55deddd5e7))

### Fix
* **robotlangserver:** Don't report load workspace progress if progressmode is off ([`6dca5e0`](https://github.com/d-biehl/robotcode/commit/6dca5e0f9e8380dc43f5389f7656c3b054da7ede))

## v0.18.0 (2022-12-15)
### Feature
* **robotlangserver:** Speedup loading of class and module libraries ([`975661c`](https://github.com/d-biehl/robotcode/commit/975661c7d33d2736355be66d7e1b26979ef9b0aa))

### Fix
* **robotlangserver:** Update libraries when editing not work ([`9adc6c8`](https://github.com/d-biehl/robotcode/commit/9adc6c866d8164a97224bef6a6b21b867355c4ec))

## v0.17.3 (2022-12-11)
### Fix
* **vscode:** Highlightning comments in text mate mode ([`1c1cb9a`](https://github.com/d-biehl/robotcode/commit/1c1cb9a22a02c89dd604418d883b570a68d199b1))
* **vscode:** Some tweaks for better highlightning ([`40b7512`](https://github.com/d-biehl/robotcode/commit/40b751223ea77b0c978f9252b3e946c02f9437d6))

### Performance
* **robotlangserver:** Speedup keyword completion ([`6bcaa22`](https://github.com/d-biehl/robotcode/commit/6bcaa22ab492bad7882f5585ae852be87384f497))
* **robotlangserver:** Refactor some unnecessary async/await methods ([`0f8c134`](https://github.com/d-biehl/robotcode/commit/0f8c1349f9bcdeb817f28247afc11c076c9747d0))

## v0.17.2 (2022-12-09)
### Fix
* **vscode:** Enhance tmLanguage to support thing  like variables, assignments,... better ([`ec3fce0`](https://github.com/d-biehl/robotcode/commit/ec3fce062019ba8fa9fcdea2480d6e5be69fccf5))

## v0.17.1 (2022-12-08)


## v0.17.0 (2022-12-08)
### Feature
* **vscode:** Add configuration defaults for `editor.tokenColorCustomizations` and `editor.semanticTokenColorCustomizations` ([`ce927d9`](https://github.com/d-biehl/robotcode/commit/ce927d98565be3d481927cea64b8db630cde43d3))

## v0.16.0 (2022-12-08)
### Feature
* **vscode:** Provide better coloring in the debug console. ([`c5de757`](https://github.com/d-biehl/robotcode/commit/c5de757ad132fb06a07be80d39c512568a18aa08))
* **robotlangserver:** Highlight dictionary keys and values with different colors ([`9596540`](https://github.com/d-biehl/robotcode/commit/9596540bfdf2e027c1a1963a2c8b3ae81d42485a))
* **robotlangserver:** Optimization of the analysis of keywords with embedded arguments ([`0995a2e`](https://github.com/d-biehl/robotcode/commit/0995a2ee73561162b823d43c5e8077a8daa28053))
* **robotlangserver:** Highlight embedded arguments ([`d8b23e4`](https://github.com/d-biehl/robotcode/commit/d8b23e45951e660baea327b3534026da9ee27286))
* **vscode:** Add new command `Restart Language Server` ([`2b4c9c6`](https://github.com/d-biehl/robotcode/commit/2b4c9c6b90520234e4277364563c37e979c2f409))

### Fix
* **robotlangserver:** Try to hover, goto, ... for keyword with variables in names ([`ec2c444`](https://github.com/d-biehl/robotcode/commit/ec2c44457d936431e62fcdb9cb5ef7ca941e3e8b))
* **vscode:** Capitalize commands categories ([`b048ca4`](https://github.com/d-biehl/robotcode/commit/b048ca4a5fc3379ff4107ccfeebcbceac2785dd9))

## v0.15.1 (2022-12-07)


## v0.15.0 (2022-12-07)
### Feature
* Simplifying implementation of discovering of tests ([`c8abfae`](https://github.com/d-biehl/robotcode/commit/c8abfae067b3ae98b7330bdacb8027d184df4297))

### Fix
* Debugger now also supports dictionary expressions ([`f80cbd9`](https://github.com/d-biehl/robotcode/commit/f80cbd9ea9c91ebbe2b4f0cba20cfd6fb2d830a1))

##  0.14.5

- Improve analysing, find references and renaming of environment variables
- Optimize reference handling.
  - This allows updating references when creating and deleting files, if necessary.

##  0.14.4

- Correct resolving paths for test execution

##  0.14.3

- Optimize locking
- Speedup collect available testcases

##  0.14.2

- Add sponsor to package

##  0.14.1

- Connection to the debugger stabilized.

##  0.14.0

- Implement inlay hints for import namespaces and parameter names
  - by default inlay hints for robotcode are only showed if you press <kbd>CONTROL</kbd>+<kbd>ALT</kbd>
  - there are 2 new settings
    `robotcode.inlayHints.parameterNames` and `robotcode.inlayHints.namespaces` where you can enable/disable the inline hints
##  0.13.28

- Remove `--language` argument if using robot < 6
  - fixes #84

##  0.13.27

- Remote Debugging

  - by installing `robotcode` via pip in your environment, you can now run the `robotcode.debugger` (see `--help` for help) from command line and attach VSCode via a remote launch config
  - more documentation comming soon.
  - closes [#86](https://github.com/d-biehl/robotcode/issues/86)

##  0.13.26

- none so far

##  0.13.25

- none so far

##  0.13.24

- The code action "Show documentation" now works for all positions where a keyword can be used or defined
- The code action "Show documentation" now respects the theme activated in VSCode. (dark, light)

##  0.13.23

- Support for Robocop >= 2.6
- Support for Tidy >= 3.3
- Speed improvements

##  0.13.22

- none so far

##  0.13.21

- none so far

##  0.13.20

- Reimplement workspace analysis
- Optimize the search for unused references

##  0.13.19

- Add a the setting `robotcode.completion.filterDefaultLanguage` to filter english language in completion, if there is another language defined for workspace or in file
- Correct naming for setting `robotcode.syntax.sectionStyle` to `robotcode.completion.headerStyle`
- Filter singular header forms for robotframework >= 6

##  0.13.18

- none so far

##  0.13.17

- Support for simple values (number, bool, str) from variable and yaml files
- Shortened representation of variable values in hover

##  0.13.16

- none so far

##  0.13.15

- none so far

##  0.13.14

- Documentation server now works also in remote and web versions of VSCode like [gitpod.io](https://gitpod.io/) and [GitHub CodeSpaces](https://github.com/features/codespaces)

##  0.13.13

- add colors to debug console
- fix resolving of ${CURDIR} in variables
- Open Documentation action now resolves variables correctly and works on resource files

##  0.13.12

- none so far

##  0.13.11

- none so far

##  0.13.10

- Correct reporting of loading built-in modules errors

##  0.13.9

- Correct analysing of "Run Keyword If"
  - fixes [#80](https://github.com/d-biehl/robotcode/issues/80)

##  0.13.8

- Support for Robocop >= 2.4
- Rework handling of launching and debugging tests
  - fixes [#54](https://github.com/d-biehl/robotcode/issues/54)
  - a launch configuration can now have a `purpose`:
    - `test`: Use this configuration when running or debugging tests.
    - `default`: Use this configuration as default for all other configurations.
- Finetuning libdoc generation and code completion
  - support for reST documentions
    - `docutils` needs to be installed
    - show documentations at library and resource import completions
- Experimental support for Source action `Open Documentation`
  - left click on a resource or library import, select Source Action and then "Open Documentation"
  - a browser opens left of the document and shows the full documentation of the library
  - works also an keyword calls
  - Tip: bind "Source Action..." to a keyboard short cut, i.e <kbd>Shift</kbd>+<kbd>Alt</kbd>+<kbd>.</kbd>

##  0.13.7

- Don't explicitly set suites to failed if there is an empty failed message
  - fixes [#76](https://github.com/d-biehl/robotcode/issues/76)

##  0.13.6

- Extensive adjustments for multiple language support for RobotFramework 5.1, BDD prefixes now works correctly for mixed languages
- New deprecated message for tags that start with hyphen, RF 5.1

##  0.13.5

- Some fixes in analysing and highlightning

##  0.13.4

- none so far

##  0.13.3

- Highlight localized robot files (RobotFramework >= 5.1)

##  0.13.2

- Support for robotidy 3.0
- References are now collected at source code analyze phase
  - this speeds up thinks like find references/renaming/highlight and so on

##  0.13.1

- Switching to LSP Client 8.0.0 requires a VSCode version >= 1.67
- Create snippets for embedded argument keywords

##  0.13.0

- Some corrections in highlightning to provide better bracket matching in arguments

##  0.12.1

- Implement API Changes for RobotTidy >= 2.2
  - fixes [#55](https://github.com/d-biehl/robotcode/issues/55)
- Switch to new LSP Protocol Version 3.17 and vscode-languageclient 8.0.0
- Disable 4SpacesTab if [GitHub CoPilot](https://copilot.github.com/) is showing inline suggestions
  - Thanks: @Snooz82

##  0.12.0

- Find references, highlight references and rename for tags
- Correct handling of keyword only arguments
- Fix the occurrence of spontaneous deadlocks

##  0.11.17

### added

- Information about possible circular imports
  - if one resource file imports another resource file and vice versa an information message is shown in source code and problems list
- References for arguments also finds named arguments

##  0.11.16

- none so far

##  0.11.15

- none so far

##  0.11.14

- none so far

##  0.11.13

- none so far

##  0.11.12

### added

- Reference CodeLenses
  - Code lenses are displayed above the keyword definitions showing the usage of the keyword
  - You can enable/disable this with the new setting `robotcode.analysis.referencesCodeLens`

##  0.11.11

### added

- Project wide code analysis
  - There are some new settings that allow to display project-wide problems:
    - `robotcode.analysis.diagnosticMode` Analysis mode for diagnostics.
      - `openFilesOnly` Analyzes and reports problems only on open files.
      - `workspace` Analyzes and reports problems on all files in the workspace.
      - default: `openFilesOnly`
    - `robotcode.analysis.progressMode` Progress mode for diagnostics.
      - `simple` Show only simple progress messages.
      - `detailed` Show detailed progress messages. Displays the filenames that are currently being analyzed.
      - default: `simple`
    - `robotcode.analysis.maxProjectFileCount` Specifies the maximum number of files for which diagnostics are reported for the whole project/workspace folder. Specifies 0 or less to disable the limit completely.
      - default: `1000`
    - `robotcode.workspace.excludePatterns` Specifies glob patterns for excluding files and folders from analysing by the language server.
- Rework loading and handling source documents
  - this speedups a lot of things like:
    - UI response
    - finding references
    - renaming of keywords and variables
    - loading reloading libraries and resources
  - When you create/rename/delete files, keywords, variables, you get an immediate response in the UI


##  0.11.10

- renaming of keywords and variables
- speedup loading of resources

##  0.11.9

### added

- Return values of keywords calls can be assigned to variables in the debugger console
  - You can call keywords in the debugger console just as you would write your keyword calls in robot files.
    Everything that starts with `'! '` (beware the space) is handled like a keyword call, for example:

    ```
    ! Log  Hello
    ```

    would call the keyword `Log` and writes `Hello` to report.

    ```
    !  Evaluate  1+2
    ```

    calls `Evaluate` and writes the result to the log.

    To assign the result of a keyword to a variable write something like

    ```
    ! ${result}  Evaluate  1+2
    ```

    This will assign the result of the expression to the variable `${result}` in the current execution context.

    A more complex example:

    ```
    ! ${a}  @{c}=  ${b}  Evaluate  "Hello World!!! How do you do?".split(' ')
    ```

    A side effect of this is that the keyword calls are logged in log.html when you continue your debug session.



##  0.11.8

### added
- Test Templates argument analysis
  - Basic usage
  - Templates with embedded arguments
  - Templates with FOR loops and IF/ELSE structures
  - see also [Robot Framework documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-templates)

##  0.11.7

### added

- optimize restart language clients if configuration changed
- support for progress feature of language server protocol
- correct WHILE snippets
- handle invalid regular expressions in embedded keywords
- correct handling of templates with embedded arguments

##  0.11.6

- none so far

##  0.11.5

- Enable automatic publication of releases on github

##  0.11.4

- none so far

##  0.10.2

- Correct error in find variable references with invalid variables in variable section

##  0.11.3

- Fix selection range on white space

##  0.11.2

- Implement [Selection Range](https://code.visualstudio.com/docs/editor/codebasics#_shrinkexpand-selection) support for Robot Framework
  - starting from a point in the source code you can select the surrounding keyword, block (IF/WHILE,...), test case, test section and so on

##  0.11.1

- Provide better error messages if python and robot environment not matches RobotCode requirements
  - fixes [#40](https://github.com/d-biehl/robotcode/issues/40)
- Correct restart of language server client if python interpreter changed
- Correct start of root test item if `robotcode.robot.paths` is used

##  0.11.0

- Correct find references at token ends
  - If the cursor is at the end of a keyword, for example, the keyword will also be highlighted and the references will be found.

##  0.10.1

### added
- Analyse variables in documentation or metadata settings shows a hint instead of an error if variable is not found
  - fixes [#47](https://github.com/d-biehl/robotcode/issues/47)
- Correct robocop shows false "Invalid number of empty lines between sections"
  - fixes [#46](https://github.com/d-biehl/robotcode/issues/46)]

##  0.10.0

### added
- Introduce setting `robotcode.robot.paths` and correspondend launch config property `paths`
  - Specifies the paths where robot/robotcode should discover test suites. Corresponds to the 'paths' option of robot
- Introduce new RF 5 `${OPTIONS}` variable

##  0.9.6

### added

- Variable analysis, finds undefined variables
  - in variables, also inner variables like ${a+${b}}
  - in inline python expression like ${{$a+$b}}
  - in expression arguments of IF/WHILE statements like $a<$b
  - in BuiltIn keywords which contains an expression or condition argument, like `Evaluate`, `Should Be True`, `Skip If`, ...
- Improve handling of completion for argument definitions
- Support for variable files
  - there is a new setting `robotcode.robot.variableFiles` and corresponding `variableFiles` launch configuration setting
  - this corresponds to the `--variablefile` option from robot

##  0.9.5

### added

- Correct handling of argument definitions wich contains a default value from an allready defined argument

##  0.9.4

### added

- Correct handling of argument definitions wich contains a default value with existing variable with same name
- Implement "Uncaughted Failed Keywords" exception breakpoint
  - from now this is the default breakpoint, means debugger stops only if a keyword failed and it is not called from:
    - BuiltIn.Run Keyword And Expect Error
    - BuiltIn.Run Keyword And Ignore Error
    - BuiltIn.Run Keyword And Warn On Failure
    - BuiltIn.Wait Until Keyword Succeeds
    - BuiltIn.Run Keyword And Continue On Failure
  - partially fixes [#44](https://github.com/d-biehl/robotcode/issues/44)
  - speedup updating test explorers view

##  0.9.3

### added

- Introduce setting `robotcode.robot.variableFiles` and correspondend launch config property `variableFiles`
  - Specifies the variable files for robotframework. Corresponds to the '--variablefile' option of robot.
- Rework debugger termination
  - if you want to stop the current run
    - first click on stop tries to break the run like if you press <kbd>CTRL</kbd>+<kbd>c</kbd> to give the chance that logs and reports are written
    - second click stops/kill execution
- 'None' values are now shown correctly in debugger

##  0.9.2

- none so far

##  0.9.1

### added

- Rework handling keywords from resource files with duplicate names
  - also fixes [#43](https://github.com/d-biehl/robotcode/issues/43)

##  0.9.0

### added

- Optimize collecting model errors
  - also fixes [#42](https://github.com/d-biehl/robotcode/issues/42)
- Add `mode` property to launch configuration and `robotcode.robot.mode` setting for global/workspace/folder
  - define the robot running mode (default, rpa, norpa)
  - corresponds to the '--rpa', '--norpa' option of the robot module.
  - fixes [#21](https://github.com/d-biehl/robotcode/issues/21)

##  0.8.0

### added

- Introduce new version scheme to support pre-release versions of the extension
  - see [README](https://github.com/d-biehl/robotcode#using-pre-release-version)
- Rework handling VSCode test items to ensure all defined tests can be executed, also when they are ambiguous
  - see [#37](https://github.com/d-biehl/robotcode/issues/37)
- Semantic highlighting of new WHILE and EXCEPT options for RF 5.0
- Support for inline IF for RF 5.0
- Support for new BREAK, CONTINUE, RETURN statements for RF 5.0


##  0.7.0

### added

- Add `dryRun` property to launch configuration
- Add "Dry Run" and "Dry Debug" profile to test explorer
  - You can select it via Run/Debug dropdown or Right Click on the "green arrow" before the test case/suite or in test explorer and then "Execute Using Profile"
- Mark using reserved keywords like "Break", "While",... as errors
- Support for NONE in Setup/Teardowns
  - see [here](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-setup-and-teardown)
  - fixes [#38](https://github.com/d-biehl/robotcode/issues/38)
- Decrease size of extension package
- Sligtly correct displayName and description of VSCode package, for better relevance in Marketplace search
  - See [#39](https://github.com/d-biehl/robotcode/issues/39)

##  0.6.0

### added

- Improved variable analysis
  - In an expression like `${A+'${B+"${F}"}'+'${D}'} ${C}`, every single 'inner' variable will be recognized, you can hover over it, it can be found as reference, you can go to the definition, ...
  - Also in python expressions like `${{$a+$b}}` variables are recognized
  - Support for variables in expression in IF and WHILE statements
    - in something like `$i<5` the variables are recognized
  - Only the name of the variable is used for hovering, goto and ..., not the surrounding ${}
- Support importing variable files as module for RobotFramework 5
- Depending on selected testcase names contains a colon, a semicolon is used as separator of prerunmodifier for executing testcases
    - fixes [#20](https://github.com/d-biehl/robotcode/issues/20)
    - note: i think you should not use colons or semicolon in testcase names ;-)
- Improve Debugger
  - The debugger shows variables as inline values and when hovering, it shows the current variable value not the evaluted expression
  - Variables in the debugger are now resolved correctly and are sorted into Local/Test/Suite and Global variables
  - Fix stepping/halt on breakpoint for IF/ELSE statements if the expression is evaluated as False
  - Rework of stepping and stacktrace in the debugger
    - Only the real steps are displayed in the stack trace
- Optimize keyword matching
  - all keyword references also with embedded arguments + regex are found
  - ambigous embedded keywords are recognized correctly, also with regex
  - speed up finding keyword references
  - fix [#28](https://github.com/d-biehl/robotcode/issues/28)
  - addresses [#24](https://github.com/d-biehl/robotcode/issues/24)
- Ignoring robotcode diagnostics
  - you can put a line comment to disable robotcode diagnostics (i.e errors or warnings) for a single line, like this:

  ```robotcode
  *** Test cases ***
  first
      unknown keyword  a param   # robotcode: ignore
      Run Keyword If    ${True}
      ...    Log    ${Invalid var        # robotcode: ignore
      ...  ELSE
      ...    Unknown keyword  No  # robotcode: ignore
  ```

- Propagate import errors from resources
  - errors like: `Resource file with 'Test Cases' section is invalid` are shown at import statement
  - Note: Robocop has it's own ignore mechanism
- Initialize logging only of "--log" parameter is set from commandline
  - fixes [#30](https://github.com/d-biehl/robotcode/issues/30)
- Optimize loading of imports and collecting keywords
  - this addresses [#24](https://github.com/d-biehl/robotcode/issues/24)
  - one of the big points here is, beware of namespace pollution ;-)
- Full Support for BDD Style keywords
  - includes hover, goto, highlight, references, ...

##  0.5.5

### added

- correct semantic highlightning for "run keywords"
  - now also named arguments in inner keywords are highlighted
- correct handling of parameter names in "run keywords" and inner keywords
- correct handling of resource keywords arguments

##  0.5.4

### added

- Keyword call analysis
  - shows if parameters are missing or too much and so on...
- Highlight of named arguments
- Improve handling of command line variables when resolving variables
- Remove handling of python files to reduce the processor load in certain situations

##  0.5.3

### added

- Resolving static variables, closes [#18](https://github.com/d-biehl/robotcode/issues/18)
  - RobotCode tries to resolve variables that are definied at variables section, command line variables and builtin variables. This make it possible to import libraries/resources/variables with the correct path and parameters.
  Something like this:

  ```robotframework
  *** Settings ***
  Resource          ${RESOURCE_DIR}/some_settings.resource
  Library           alibrary    a_param=${LIB_ARG}
  Resource          ${RESOURCE_DIR}/some_keywords.resource
  ```

  - If you hover over a variable, you will see, if the variable can be resolved

- show quick pick for debug/run configuration
  - if there is no launch configuration selected and you want to run code with "Start Debugging" or "Run without Debugging", robotcode will show you a simple quick pick, where you can select a predefined configuration
- some cosmetic changes in updating Test Explorer
- correct handling of showing inline values and hover over variables in debugger
- correct handling of variable assignment with an "equal" sign
- add more regression tests

##  0.5.2

- some testing

##  0.5.1

### added

- extend README.md
  - added section about style customization
  - extend feature description
- added file icons for robot files
  - starting with VSCode Version 1.64, if the icon theme does not provide an icon for robot files, these icons are used
- add automatic debug configurations
  - you don't need to create a launch.json to run tests in the debugger view
- correct step-in FINALLY in debugger
- test explorer activates now only if there are robot files in workspace folder


##  0.5.0

### added

- Added support for RobotFramework 5.0
  - Debugger supports TRY/EXCEPT, WHILE,... correctly
  - (Semantic)- highlighter detects new statements
  - Formatter not uses internal tidy tool
  - handle EXPECT AS's variables correctly
  - Complete new statements
  - Some completion templates for WHILE, EXCEPT, ...
- Discovering tests is now more error tolerant
- Semantic tokenizing now also detects ERROR and FATAL_ERROR tokens
- some cosmetic corrections in discoring tests

note: RobotFramework 5.0 Alpha 1 has a bug when parsing the EXCEPT AS statement,
so the highlighter does not work correctly with this version.
This bug is fixed in the higher versions.

##  0.4.10

### added

- fix correct reverting documents on document close

##  0.4.9

### added

- correct CHANGELOG

##  0.4.8

### added

- extend [README](./README.md)
- extend highlight of references in fixtures and templates
- correct updating test explorer if files are deleted or reverted
- some cosmetic changes

##  0.4.7

### added

- hover/goto/references/highlight... differentiate between namespace and keyword in keyword calls like "BuiltIn.Log"
- increase test coverage

##  0.4.6
### added

- some small fixes in completion, command line parameters and variable references

##  0.4.5

### added

- correct semantic highlight of variables and settings
- completion window for keywords is now opened only after triggering Ctrl+Space or input of the first character

##  0.4.4

### added

- implement InlineValuesProvider and EvaluatableExpressionProvider in language server

##  0.4.3

### added

- implement find references for libraries, resources, variables import
- implement document highlight for variables and keywords

##  0.4.2

### added

- added support for variables import
  - completion
  - hover
  - goto
  - static and dynamic variables
- correct debugger hover on variables and last fail message
- implement find references for variables


##  0.4.1

### added

- for socket connections now a free port is used
- collect variables and arguments to document symbols
- analysing, highlighting of "Wait Until Keyword Succeeds" and "Repeat Keyword"

##  0.4.0

### added

- Big speed improvements
  - introduce some classes for threadsafe asyncio
- Implement pipe/socket transport for language server
  - default is now pipe transport
- Improve starting, stopping, restarting language server client, if ie. python environment changed, arguments changed or server crashed
- some refactoring to speedup loading and parsing documents
- semantic tokens now highlight
  - builtin keywords
  - run keywords, also nested run keywords
- analysing run keywords now correctly unescape keywords

##  0.3.2

### added

- remove deadlock in resource loading

##  0.3.1

### added

- implement find keyword references
  - closes [#13](https://github.com/d-biehl/robotcode/issues/13)
- improve parsing and analysing of "run keywords ..."
  - closes [#14](https://github.com/d-biehl/robotcode/issues/14)

##  0.3.0

### added

- remove pydantic dependency
    - closes [#11](https://github.com/d-biehl/robotcode/issues/11)
    - big refactoring of LSP and DAP types
- fix overlapping semantic tokens

##  0.2.11

### added

- fix [#10](https://github.com/d-biehl/robotcode/issues/10)
- start implementing more unit tests
- extend hover and goto for variables

##  0.2.10

### added

- extend sematic higlightning
    - builtin library keywords are declared as default_library modifier
    - higlight variables in keyword names and keyword calls
- complete embedded arguments

##  0.2.9

### added

- some correction to load libraries/resources with same name
    - fixes [#9](https://github.com/d-biehl/robotcode/issues/9)

##  0.2.8

### added

- update readme
- Added some more configuration options for log and debug messages when running tests in the debug console
- debug console now shows source and line number from log messages
- use of debugpy from vscode Python extension, no separate installation of debugpy required
- implement test tags in test controller
- implement completion, hover and goto for variables

##  0.2.7

### added

- update readme
- add run and debug menus to editor title and context menu

##  0.2.6

### added

- update readme
- semantic tokens now iterate over nodes

##  0.2.5

### added

- correct loading and closing documents/library/resources
- correct casefold in completion of namespaces

##  0.2.4

### added

- improve performance
- implement semantic syntax highlightning

##  0.2.2

### added

- integrate robotframework-tidy for formatting

## 0.2.1

### added

- improve test run messages
- add "Taks" to section completion
- add colors to test output

## 0.2.0

- Initial release


---

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.
