# Configuration

## Introducing the `robot.toml` file

The `robot.toml` file offers an alternative way of setting up your project in VS Code. Usually, those settings  would be done via the `settings.json` file, doing so comes though at the cost of several limitations and inconveniences. Using `robot. toml` alleviates many of those by:

- providing a simpler way of defining settings for the Robot Framework project in one file
- creating a file that can be easily shared and uploaded to a git repository
- removing the need to create an argument file
- simplifying the command line execution
- allowing to define multiple, easily expandable, profiles

::: info
The following documentation serves as a quick introduction on how to use the `robot.toml` file and will not cover all *Robot Framework* command line options. For a complete documentation of these options, please refer to the [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html "Robot Framework User Guide").
:::

::: tip
If you want to have code completion and such things for TOML files, install the **[Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml)** extension before attempting to work with `robot.toml`.
:::


## Settings configuration

Using the `robot.toml` file, we can configure a wide range of settings for our project. The example below shows how we can setup the output directory, language and global project variables. In toml, `[variables]` is a tabular setting, meaning it can store multiple name-value pairs.

```toml
output-dir = "output"
languages = ["english"]

[variables]
NAME = "Tim"
AGE = "25"
MAIL = "hotmail.de"
```

You can access a full list of available setting by excetuting `robot --help` in the CLI.


## Profiles

Profiles allow you to store multiple configurations, in an easily accessible way. This can be useful if for example you need a different set of configurations, for testing on multiple platforms. Profiles are easily expandable and can be easily shared between developers by simply providing them the robot.toml file.


### Defining profiles

You can define a profile with `[profiles.YOUR_PROFILE_NAME]`. Follow it up with the settings that you want to configure for that particular profile. For tabular settings like `[variables]` you will need to create a separate entry using `[profiles.YOUR_PROFILE_NAME.variables]`. Your profiles will use any global configuration, that has not been defined within the profile. In example below, dev2 will use English as the language and *output* as the output directory.

```toml
output-dir = "output"
languages = ["english"]

[variables]
NAME = "Tim"
AGE = "25"
MAIL = "hotmail.de"

[profiles.dev1]
output-dir = "dev1output"
languages = ["german"]

[profiles.dev1.variables]
NAME = "Lisa"
AGE = "32"
MAIL = "web.de"

[profiles.dev2.variables]
NAME = "Andrew"
AGE = "19"
MAIL = "gmail.com"

[profiles.dev3]
output-dir = "dev3output"
```


### Overriding and extending settings

Tabular settings like `[variables]` can be either overridden or expanded. In the example below, dev1 and dev2 are overriding `[variables]`. Override will prevent dev1 and dev2 from using any of the values defined in lines 4-7. This means that dev2 will not use  `NAME = "Tim"` defined in line 5 but instead whatever is defined in the relevant .robot files.

```toml
output-dir = "output"
languages = ["english"]

[variables]
NAME = "Tim"
AGE = "25"
MAIL = "hotmail.de"

[profiles.dev1.variables]
NAME = "Lisa"
AGE = "32"
MAIL = "web.de"

[profiles.dev2.variables]
AGE = "19"
MAIL = "gmail.com"
```

In order to change only selected values or add new ones, the 'extend-' prefix is needed. In the example below, dev2 will still use `NAME` and `AGE` defined in lines 2 and 3.

```toml
[variables]
NAME = "Tim"
AGE = "25"
MAIL = "hotmail.de"

[profiles.dev2.extend-variables]
MAIL = "gmail.com"
LOCATION = "Berlin"
```


### Inheriting and merging profiles

Profiles can inherit from an already existing profile.

```toml
[profiles.dev3]
output-dir = "dev3output"

[profiles.inheritedFromDev3]
inherits = ["dev3"]
languages = ["german"]
```

It is also possible to inherit from multiple profiles.

```toml
[profiles.dev1]
output-dir = "dev1output"
languages = ["german"]

[profiles.dev1.variables]
NAME = "Lisa"
AGE = "32"
MAIL = "web.de"

[profiles.dev3]
output-dir = "dev3output"

[profiles.dev1and3]
inherits = ["dev1, dev3"]
```

If a variable is present in multiple of the inherited profiles, the value of that variable will be the one, present in the last relevant inherited profile. In the example above, the value of `output-dir` for the dev1and2 profile, will be "dev3output".


### Profile management

#### Selecting profiles

You can select a profile to work with, by entering "RobotCode: Select Configuration Profiles" in the command palette (ctrl+shift+p).

![Select Profile1](./../images/config%20images/toml-profiles-command-selection.PNG)

Should you select more than one profile, a merged version of those profiles will be executed.
Alternatively, you can select a profile to run or debug with, by clicking on the buttons, marked in the image below.

![Select Profile2](./../images/config%20images/config_selec_buttons.PNG)

Using this method however, does not allow you to select multiple profiles at once.


#### Default profiles

It is possible to select a list of default profiles, using the `default-profiles` option. Those profiles will be selected by default, if no other profile has been selected for execution.
Should you select more than one default profile, a merged version of those profiles will be executed.

```toml
default-profiles = ["dev1", "dev2"]

[profiles.dev1.variables]
NAME = "Lisa"
AGE = "32"
MAIL = "web.de"

[profiles.dev2.variables]
AGE = "19"
MAIL = "gmail.com"

[profiles.dev3.variables]
MAIL = "hotmail.com"

```


#### Hiding profiles

If, for whatever reason, you wish for individual profiles to not be displayed as selectable options, you can hide them by using the `hidden` option.

```toml
[profiles.dev1]
hidden = true
```

It is also possible to hide a profile based on user defined conditions, using python expressions.

```toml
[profiles.dev1]
hidden.if = "platform.system()=='Windows'"
```

Hidden profiles can be still merged and inherited from.


#### Enabling profiles

Similar to hiding, profiles can be also disabled using the `enabled` option.

```toml
[profiles.dev1]
enabled = false
```

It is also possible to enable or disable a profile based on user defined conditions, using python expressions.

```toml
[profiles.dev1]
enabled.if = "platform.system()=='Windows'"
```

Disabled profiles cannot be merged or inherited from.


### Test Execution

In order to execute tests using the CLI, you will need to install the `robotcode-runner` pip package and add it to your requirements.txt.


#### Executing tests

Here are some of the most common ways, to execute tests via the CLI.


- `robotcode robot PATH`

  Executes all tests (including in subfolders) within a given location. This command can be also executed with the command `robotcode robot`, if you add `paths = "TESTFILE_LOC"` to your robot.toml file.

- `robotcode robot -t "TEST_CASE_NAME"`

  Executes the test case called `TEST_CASE_NAME`

- `robotcode -p PROFILE_NAME robot PATH`

  Executes all tests (including in subfolders) within a given location, with the selected profile.

- `robotcode -p PROFILE_NAME_1  -p PROFILE_NAME_2 robot PATH`

  Executes all tests (including in subfolders) within a given location, with a merged version the selected profiles.

- `robotcode -p PROFILE_NAME -v NAME:Carl robot PATH`

  Executes all tests (including in subfolders) within a given location. Changes the value of the variable `NAME` to `Carl`.


- `robotcode robot -i TAG_NAME`

    Executes all tests with a given tag. Tags can be assigned either globally in the settings or individually for each test case.

    <IMG src="./../images/config%20images/tags_robot.PNG"/>
