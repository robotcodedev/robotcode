# Configuration

## Introducing the `robot.toml` file
The `robot.toml` file offers an alternative way of setting up your project in VS Code. Usually those setting would be done via the `settings.json` file, doing so comes though at the cost of several limitations and inconvienences. Using `robot.toml` eliviates many of those by:
- providing a simpler way of defining project settings in one file
- creating a file that can be easily shared and uploaded to a git repository
- removing the need to create an argument file
- simplyfying the command line execution
- allowing to define multiple, easily expandable, profiles

## How to use `robot.toml`
The following documentation serves as a quick introduction on how to use the `robot.toml` file and will cover only the essentials. For a complete  documentation please refer to INSERT_LINK_HERE. You can also access a full list of available setting by excetuting `robot --help` into the terminal.

### Settings configuration
Using the `robot.toml` file, we can configure a wide range of setting for our project. The example below shows how we can setup the output directory, language and global project variables. In toml, `[variables]` is a tabular setting, meaning it can store multiple name-vaule pairs.
```toml
output-dir = "output"
languages = ["english"]

[variables]
NAME = "Tim"
AGE = "25"
MAIL = "hotmail.de"
```

### Profiles
Lorem ipsum
#### Defining profiles
You can define a profile with `[profiles.YOUR_PROFILE_NAME]`. Follow it up with the settings that you want to configure for that particular profile. For tabular settings like `[variables]` you will need to create a seperate entry using `[profiles.YOUR_PROFILE_NAME.variables]`. Your profiles will use any global configuration, that has not been defines within the profile. In example belov, dev2 will use english as the language and *output* as the output directory.
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

#### Overriding and extending settings
Tabular settings like `[variables]` can be either overriden or expanded. In the example below, dev1 and dev2 are overriding `[variables]`. Override will prevent dev1 and dev2 from using any of the values defined in lines 4-7. This means that dev2 will not use  `NAME = "Tim"` defined in line 5 but instead whatever is defined in the relevant .robot files.
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

#### Inheriting and merging profiles
lorem ipsum
```toml
[profiles.dev3]
output-dir = "dev3output"

[profiles.dev3inherited]
inherits = ["dev3"]
languages = ["german"]
```
lorem ipsum

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
#### Profile management
- default profile
- hiding profiles
- enabling profiles

#### Selecting profiles
You can select a profile to work with, by entering "RobotCode: Select Configuration Profiles" in the command palette (ctrl+shift+p). TEXT ABOUT SELECTING MULTIPLE PROFILES
![Select Profile](./../images/config%20images/toml-profiles-command-selection.PNG)

### Running tests
- requirement.txt robotcode-runner
- pip install robotcode-runner
- robotcode robot TESTFILE_LOC
- robotcode -p YOUR_PROFILE_NAME robot TESTFILE_LOC
- robotcode -p YOUR_PROFILE_NAME  -p YOUR_OTHER_PROFILE_NAME robot TESTFILE_LOC
- robotcode -p YOUR_PROFILE_NAME -v NAME:Carl robot TESTFILE_LOC
- robotcode robot -t "TEST_CASE_NAME"
- robotcode robot - TAG_NAME

## TODO
- ~~[ ]  What is a robot.toml file~~
- ~~[ ]  How to use `robot.toml`~~
  - [ ] in vscode
  - [ ] on command line
  - [ ] in other editors/CI Pipelines, ...
- ~~[ ] robot.toml~~
  - [ ] RobotCode settings
  - [ ] RobotFramework Settings
  - ~~[ ] Profiles~~
    - ~~[ ] Define profiles~~
    - ~~[ ] override vs expand settings~~
    - ~~[ ] Use profiles~~
