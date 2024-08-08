# Get Started

Welcome to RobotCode! In this section, we will get your Visual Studio Code set up and go through the basics: installing the extension, setting up your environment, and verifying everything is working smoothly.

## Requirements
- Python 3.8 or above
- Robotframework version 4.1 and above
- VSCode version 1.82 and above

## Installing RobotCode

1. Open Visual Studio Code.
2. Inside Visual Studio Code, create a new project folder or open an existing one where you want to set up your Robot Framework project.
3. Go to the **Extensions** tab (Shortcut key `CTRL + SHIFT + X`).
4. Search for **RobotCode** and install the extension ![RobotCode Icon](../robotcode-logo.svg "RobotCode Icon"){.inline-icon} [RobotCode - Robot Framework Support](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode "RobotCode Extension"). This will also install the **Python** and **Python Debugger** extensions.
5. **(Recommended)** Install the **Even Better TOML** extension for handling `.toml` files more effectively.  This will be helpful when setting up your project settings in the [Configuration](./configuration) section.

After installation:
   - Right-click on the RobotCode extension in the Extensions tab.
   - Click **Add to Workspace Recommendations** to ensure that all team members working on this project are prompted to install the RobotCode extension, creating a consistent development environment for everyone.

![RobotCode](../robotcode-add-to-workspace.gif){style="width: 30%;"}

## Initialize an Empty Project

To get started with your Robot Framework project, we'll create a `requirements.txt` file to list all necessary dependencies, and set up a virtual Python environment to ensure these dependencies are installed in an isolated space, avoiding conflicts with other projects.

1. **Create a `requirements.txt` file** in the root folder of your project and add the following dependencies:
::: code-group
```txt:line-numbers [requirements.txt]
robotframework
robotframework-tidy
```
:::

2. **Set up your Python environment:**

A virtual environment is a self-contained directory that contains a Python installation for a particular version of Python, plus a number of additional packages. This helps keep your project dependencies isolated from other projects. In this step we will let Visual Studio Code create a virtual environment using the selected Python version, install the dependencies listed in requirements.txt, and activate the virtual environment. This ensures that your project has all the necessary packages and an isolated environment for development.

1. Click on **Create Environment** in Visual Studio Code. If this button isn't visible, you can alternatively open the Command Palette by pressing `CTRL + SHIFT + P`, then search for **Python: Create Environment**, and select it.
2. Choose **Venv**, which stands for Virtual Environment.
3. Select your preferred Python version.
4. Check the box for requirements.txt and click OK.

![Create python environment](../python-create-env.gif)

## Verifying the Installation
1. Open the terminal in Visual Studio Code. Make sure you are in the root folder of your project.
2. Run the command `robot --version` to check if Robot Framework is installed correctly.

If the command returns the Robot Framework version number, your installation is successful! If you encounter any errors, ensure that your virtual environment is activated and that all dependencies in `requirements.txt` have been installed.

## Create and Run Your First Suite/Test
Create a `first.robot` file in your project with the following code to demonstrate a basic example of logging a string message to the debug console:

::: code-group
```robot:line-numbers [first.robot]
*** Test Cases ***
First Test Case
    Log    Hello world

```
:::

To run this test file, press the green play button next to the `First Test Case` keyword in the code.
You should see the `Hello world` output displayed in the **Debug Console** of Visual Studio Code.

![RobotCode](../robotcode-first-test-case.gif){style="width: 70%;"}

And that's it! If you have any questions or run into issues, check out the RobotCode documentation or join our community in slack for support. Happy coding!
