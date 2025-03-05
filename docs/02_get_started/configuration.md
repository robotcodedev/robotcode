# Configuration

## Introduction to the `robot.toml` File

The `robot.toml` file serves as a centralized configuration system for your Robot Framework projects. Instead of managing multiple argument files, batch scripts, or command-line parameters, you can define all your project settings in one structured file.

Similar to how `pyproject.toml` has become the standard for Python project configuration, `robot.toml` aims to provide the same benefits for Robot Framework projects by:

- Centralizing all configuration in one location
- Making settings easily shareable through version control
- Supporting different environments through profiles
- Providing a clear, readable format for configuration

While fully compatible with development environments like VS Code, the `robot.toml` file is primarily designed to simplify Robot Framework project setup and maintenance.

## About TOML Files

TOML (Tom's Obvious, Minimal Language) is a configuration file format designed to be easy to read and write. It uses simple key-value pairs organized into sections, making it more human-friendly than formats like JSON or XML.

Example of TOML syntax:
```toml
# This is a comment
key = "value"

[section]
nested_key = "nested value"
```

For full details on TOML syntax, visit the [official TOML documentation](https://toml.io/en/).

## Basic Configuration

### Core Settings

Every command-line option available in Robot Framework can be configured in your `robot.toml` file:

```toml
# Basic settings
output-dir = "output"
log-level = "INFO"
languages = ["en", "fi"]

# Global variables
[variables]
BROWSER = "Chrome"
LOGIN_URL = "https://example.com/login"
TIMEOUT = "20s"
```

Multi-word options use hyphens in `robot.toml` (e.g., `--outputdir` becomes `output-dir`).

To see all available options:
- Run `robot --help` for standard Robot Framework options
- Run `robotcode config info` for RobotCode-specific options
- Check the [Configuration Reference](../03_reference/config.md) documentation

## Working with Profiles

Profiles allow you to define multiple configurations for different environments or testing scenarios.

### Creating Basic Profiles

```toml
# Default settings (applies to all profiles)
output-dir = "results"
log-level = "INFO"

# Development environment profile
[profiles.dev]
output-dir = "results/dev"
variables = { ENVIRONMENT = "development", API_URL = "http://dev-api.example.com" }

# Production testing profile
[profiles.prod]
output-dir = "results/prod"
variables = { ENVIRONMENT = "production", API_URL = "https://api.example.com" }
```

### Profile Inheritance

Profiles can inherit settings from other profiles to avoid duplication:

```toml
# Base profile with common settings
[profiles.base]
log-level = "INFO"
variables = { TIMEOUT = "20s" }

# Development profile builds on base settings
[profiles.dev]
inherits = ["base"]
variables = { ENVIRONMENT = "development", API_URL = "http://dev-api.example.com" }

# Testing profile also builds on base settings
[profiles.test]
inherits = ["base"]
variables = { ENVIRONMENT = "testing", API_URL = "http://test-api.example.com" }
```

### Conditional Profiles

Profiles can be hidden or enabled based on conditions:

```toml
# Hidden profile (not shown in listings)
[profiles.internal]
hidden = true

# Conditionally enabled profiles
[profiles.windows]
enabled.if = "platform.system() == 'Windows'"
variables = { DRIVER_PATH = "C:\\drivers" }

[profiles.linux]
enabled.if = "platform.system() == 'Linux'"
variables = { DRIVER_PATH = "/usr/local/bin" }
```

### Profile Precedence

When multiple profiles are used together, you can control which settings take priority:

```toml
# Base settings (low precedence)
[profiles.base]
variables = { LOG_LEVEL = "INFO", BROWSER = "chrome" }

# Override with higher precedence
[profiles.debug]
precedence = 100
variables = { LOG_LEVEL = "DEBUG" }

# Highest priority settings
[profiles.critical]
precedence = 200
variables = { RETRIES = 3 }
```

## Test Execution

### Running Tests with RobotCode

To execute tests, install the `robotcode-runner` package:

```bash
pip install robotcode[runner]
```

Common test execution commands:

```bash
# Run all tests in a directory
robotcode robot tests/

# Run with a specific profile
robotcode -p dev robot tests/

# Combine multiple profiles
robotcode -p base -p windows robot tests/

# Override variables on command line
robotcode -p dev -v BROWSER:firefox robot tests/

# Run tests by tag
robotcode robot -i smoke -i regression tests/
```

You can also define paths directly in the configuration:

```toml
paths = ["tests"]

```

then it is not needed to give specific paths at the commandline, just type:

```bash
# run all tests
robotcode run

# run tests and only include/exclude tests with specific tags
robotcode run -i regression -e wip
```

## Advanced Configuration

### Extending vs. Replacing Settings

By default, when merging profiles, list and dictionary settings are completely replaced. To add to these settings instead, use the `extend-` prefix:

```toml
# Default settings
variables = { BROWSER = "chrome", TIMEOUT = "20s" }
include = ["smoke"]

[profiles.api]
# Completely replaces the default variables
variables = { API_KEY = "123456" }  # BROWSER and TIMEOUT are removed

[profiles.extended]
# Adds to the default variables
extend-variables = { API_KEY = "123456" }  # Results in {BROWSER = "chrome", TIMEOUT = "20s", API_KEY = "123456"}
extend-include = ["api"]  # Results in ["smoke", "api"]
```

Settings that support the `extend-` prefix include:
- `variables`
- `include` / `exclude`
- `python-path`
- `metadata`

and many more, see the [`robot.toml` reference](../03_reference/config.md) for all posibilities.

## Configuration Loading Order

RobotCode loads configuration files in a specific sequence, with each file potentially overriding settings from previous ones:

1. **Global user configuration**
   - Located at `~/.robot.toml` (user's home directory)
   - Sets system-wide defaults

2. **Project `pyproject.toml`**
   - Located in the project root
   - Robot settings stored in the `[tool.robot]` section

3. **Project `robot.toml`**
   - Located in the project root
   - Main project configuration (should be in version control)

4. **Personal `.robot.toml`**
   - Located in the project root
   - User-specific overrides (should be added to `.gitignore`)

When multiple profiles are specified, they're applied in this order:
1. Default settings (top-level settings not in any profile)
2. Profiles ordered by precedence (lowest to highest)
3. For equal precedence, the order specified on the command line
