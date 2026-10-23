import * as assert from "assert";

import {
  EnvironmentInfoValues,
  environmentInfoText,
  pythonVersionText,
  robotFrameworkVersionText,
} from "../extension/environmentInfo";

const plain: EnvironmentInfoValues = {
  vscodeVersion: "1.142.0",
  appName: "Visual Studio Code",
  os: "Linux x64 6.8.0",
  extensionVersion: "2.8.0",
  projectInfo: { robotVersionString: "7.5", robocopVersionString: "6.2.0", robotCodeVersionString: "2.8.0" },
  environment: { state: "usable", robotVersion: "7.5" },
  provisional: false,
  python: { version: "3.13.12", kind: "venv" },
};

suite("environmentInfoText", () => {
  test("lists the six fields of the bug report template for a plain setup", () => {
    assert.strictEqual(
      environmentInfoText(plain),
      [
        "- VS Code Version: 1.142.0",
        "- RobotCode Version: 2.8.0",
        "- OS: Linux x64 6.8.0",
        "- Python Version: 3.13.12 (venv)",
        "- RobotFramework Version: 7.5",
        "- Additional tools: robotframework-robocop==6.2.0",
      ].join("\n"),
    );
  });

  test("names an editor that isn't VS Code after the VS Code version", () => {
    assert.ok(
      environmentInfoText({ ...plain, appName: "Cursor" }).startsWith("- VS Code Version: 1.142.0\n- Editor: Cursor\n"),
    );
    assert.ok(!environmentInfoText({ ...plain, appName: "Visual Studio Code - Insiders" }).includes("Editor"));
  });

  test("names the remote after the OS", () => {
    assert.ok(environmentInfoText({ ...plain, remoteName: "wsl" }).includes("- OS: Linux x64 6.8.0\n- Remote: wsl\n"));
  });

  test("names the language server's RobotCode version only when it differs from the extension's", () => {
    const projectInfo = { ...plain.projectInfo, robotCodeVersionString: "2.7.0" };
    assert.ok(
      environmentInfoText({ ...plain, projectInfo }).includes(
        "- RobotCode Version: 2.8.0\n- RobotCode Language Server Version: 2.7.0\n",
      ),
    );
    assert.ok(!environmentInfoText(plain).includes("Language Server"));
  });

  test("names no Robocop as none, and an unknown one without an answer of the language server", () => {
    assert.ok(
      environmentInfoText({ ...plain, projectInfo: { robotVersionString: "7.5" } }).endsWith(
        "- Additional tools: none",
      ),
    );
    assert.ok(environmentInfoText({ ...plain, projectInfo: undefined }).endsWith("- Additional tools: unknown"));
  });

  test("takes Robot Framework from the environment check without a language server", () => {
    const text = environmentInfoText({
      ...plain,
      projectInfo: undefined,
      environment: { state: "unusable", problem: "robotMissing" },
    });
    assert.ok(text.includes("- RobotFramework Version: not installed\n- Additional tools: unknown"));
  });
});

suite("pythonVersionText", () => {
  test("adds the kind of the environment when the Python side reports it", () => {
    assert.strictEqual(pythonVersionText({ version: "3.13.12", kind: "venv" }, undefined, false), "3.13.12 (venv)");
    assert.strictEqual(pythonVersionText({ version: "3.13.12" }, undefined, false), "3.13.12");
  });

  test("says that no interpreter is selected", () => {
    assert.strictEqual(
      pythonVersionText(undefined, { state: "unusable", problem: "noInterpreter" }, false),
      "no interpreter selected",
    );
  });

  test("is unknown when the Python side reports nothing, and in the startup phase", () => {
    assert.strictEqual(pythonVersionText(undefined, undefined, false), "unknown");
    assert.strictEqual(pythonVersionText(undefined, { state: "unusable", problem: "noInterpreter" }, true), "unknown");
  });
});

suite("robotFrameworkVersionText", () => {
  test("takes the language server's version first", () => {
    assert.strictEqual(robotFrameworkVersionText("7.5", { state: "unusable", problem: "robotMissing" }, false), "7.5");
  });

  test("takes the version the environment check found", () => {
    assert.strictEqual(
      robotFrameworkVersionText(undefined, { state: "usable", robotVersion: "7.4.1" }, false),
      "7.4.1",
    );
  });

  test("marks a version older than 5.0 as not supported", () => {
    assert.strictEqual(
      robotFrameworkVersionText(undefined, { state: "unusable", problem: "robotTooOld", robotVersion: "4.1.3" }, false),
      "4.1.3 (not supported)",
    );
  });

  test("says that Robot Framework isn't installed", () => {
    assert.strictEqual(
      robotFrameworkVersionText(undefined, { state: "unusable", problem: "robotMissing" }, false),
      "not installed",
    );
  });

  test("is unknown while the check runs, without a check and in the startup phase", () => {
    assert.strictEqual(robotFrameworkVersionText(undefined, { state: "checking" }, false), "unknown");
    assert.strictEqual(robotFrameworkVersionText(undefined, undefined, false), "unknown");
    assert.strictEqual(
      robotFrameworkVersionText(undefined, { state: "unusable", problem: "robotMissing" }, true),
      "unknown",
    );
  });
});
