# Configuration

## Introduction to the `robot.toml` File

The `robot.toml` file provides a structured and flexible way to configure your Robot Framework project. Rather than relying on various argument files, batch files or command-line arguments, you can consolidate all key settings in this one centralized file. This makes it easier to manage and maintain settings across different environments and use cases.

Similar to how `pyproject.toml` has become a standard for configuring Python projects, the `robot.toml` file aims to serve the same role for Robot Framework projects. It allows you to define project settings such as output directories, environment variables, and profiles for different testing scenarios. This unified configuration approach simplifies project management and makes it easier to share and version control configurations.

While the `robot.toml` file can be integrated with development environments like VS Code, its primary function is to centralize configuration for Robot Framework projects, streamlining the setup and maintenance process.

This guide provides an overview of how to set up and use the `robot.toml` file to manage various aspects of your Robot Framework project.

---

## About TOML Files

TOML (Tom's Obvious, Minimal Language) is a file format designed to be easy to read and write due to its clear structure. TOML files use key-value pairs to define configuration settings, similar to JSON or YAML, but with a more human-friendly syntax. In the context of the `robot.toml` file, TOML is used to structure the configuration settings for your Robot Framework project, allowing for well-organized and readable project settings.

For a full and detailed description of the TOML format, please refer to the official [TOML documentation](https://toml.io/en/).

---

## Configuring Settings

The `robot.toml` file allows you to configure various settings for your project. Below is an example that demonstrates how to configure the output directory, language preferences, and some global project variables. In TOML, `[variables]` is used to store multiple name-value pairs.

```toml
output-dir = "output"
languages = ["en", "fi"]

[variables]
NAME = "Tim"
AGE = "25"
MAIL = "hotmail.de"
```

The key concept is that for every option you can set via the command line in a `robot` call, there is a corresponding key in the `robot.toml` file. Options that can be specified multiple times, such as `--variable` or `--tag`, are stored as lists. To view all available options, you can run `robot --help` in the command line or refer

For better readability, multi-word options are written with hyphens in the `robot.toml` file. For example, `--outputdir` becomes `output-dir`. In addition to standard command-line options, the `robot.toml` file offers additional configuration settings. To view the full list, you can run the `robotcode config info` command or consult the [Configuration Reference](../03_reference/config.md).


## Profiles

Profiles in the `robot.toml` file allow you to store multiple configurations in an easily accessible way. This is particularly helpful when you need different settings for various testing environments, such as different platforms or testing conditions.

### Example of Profiles

Below is an example showing how to set up two profiles: `dev` and `prod`, each with distinct settings.

```toml
[profiles.dev]
output-dir = "output/dev"
variables = { NAME = "Developer" }

[profiles.prod]
output-dir = "output/prod"
variables = { NAME = "Production" }
```

### Inheriting Profiles

Profiles can also inherit settings from each other to reduce duplication. The `merge` keyword allows you to combine settings from multiple profiles.

```toml
[profiles.shared]
output-dir = "output/shared"

[profiles.dev]
merge = ["shared"]
variables = { NAME = "Dev" }
```

### Hiding Profiles

Profiles can be hidden using the `hidden` option or based on specific conditions through Python expressions.

```toml
[profiles.dev]
hidden = true

[profiles.dev]
hidden.if = "platform.system()=='Windows'"
```

### Enabling Profiles

Similarly, profiles can be enabled or disabled using the `enabled` option. This can also be based on user-defined conditions.

```toml
[profiles.dev]
enabled = false

[profiles.dev]
enabled.if = "platform.system()=='Windows'"
```

Disabled profiles cannot be merged or inherited from.

---

## Test Execution

To execute tests using the CLI, ensure that the `robotcode-runner` pip package is installed and added to your `requirements.txt` file.

### Executing Tests

Here are some common ways to execute tests using the CLI:

- Execute all tests within a location:
  ```bash
  robotcode robot PATH
  ```
  Alternatively, you can specify paths in the `robot.toml` file:
  ```toml
  paths = "TESTFILE_LOC"
  ```

- Execute a specific test case:
  ```bash
  robotcode robot -t "TEST_CASE_NAME"
  ```

- Execute tests with a specific profile:
  ```bash
  robotcode -p PROFILE_NAME robot PATH
  ```

- Merge and execute tests from multiple profiles:
  ```bash
  robotcode -p PROFILE_NAME_1 -p PROFILE_NAME_2 robot PATH
  ```

- Execute tests with a variable override:
  ```bash
  robotcode -p PROFILE_NAME -v NAME:Carl robot PATH
  ```

- Execute tests by tag:
  ```bash
  robotcode robot -i TAG_NAME
  ```

Tags can be set globally or individually for each test case.
