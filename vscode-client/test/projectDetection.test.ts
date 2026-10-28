import * as assert from "assert";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as vscode from "vscode";

import { isRobotProject, isSkippedByRobotFilesSearch } from "../extension/languageclientsmanger";

const FILE_EXTENSIONS = ["robot", "resource"];

suite("isRobotProject", () => {
  const roots: string[] = [];

  // A folder outside the workspace with the given files, relative path → content.
  async function folderWith(files: Record<string, string>): Promise<vscode.WorkspaceFolder> {
    const root = await fs.promises.mkdtemp(path.join(os.tmpdir(), "robotcode-project-detection-"));
    roots.push(root);
    for (const [name, content] of Object.entries(files)) {
      const file = path.join(root, ...name.split("/"));
      await fs.promises.mkdir(path.dirname(file), { recursive: true });
      await fs.promises.writeFile(file, content);
    }
    return { uri: vscode.Uri.file(root), name: path.basename(root), index: 0 };
  }

  const suiteFile = "*** Test Cases ***\nExample\n    Log    hello\n";
  const typeScriptProject = {
    "package.json": '{ "name": "ts-project" }\n',
    "README.md": "# ts-project\n",
    ".gitignore": "node_modules/\n",
    "src/index.ts": "export const answer = 42;\n",
  };

  suiteTeardown(async () => {
    for (const root of roots) await fs.promises.rm(root, { recursive: true, force: true });
  });

  test("a TypeScript project is none", async () => {
    assert.strictEqual(await isRobotProject(await folderWith(typeScriptProject), FILE_EXTENSIONS), false);
  });

  test("a Robot Framework file in an installed package does not count", async () => {
    const folder = await folderWith({
      ...typeScriptProject,
      "node_modules/fake-pkg/fixtures/example.robot": suiteFile,
    });
    assert.strictEqual(await isRobotProject(folder, FILE_EXTENSIONS), false);
  });

  test("a Robot Framework file in the folder makes it one", async () => {
    const folder = await folderWith({ ...typeScriptProject, "tests/example.robot": suiteFile });
    assert.strictEqual(await isRobotProject(folder, FILE_EXTENSIONS), true);
  });

  test("a robot.toml makes it one without Robot Framework files", async () => {
    assert.strictEqual(await isRobotProject(await folderWith({ "robot.toml": "" }), FILE_EXTENSIONS), true);
  });

  test("a .robot.toml makes it one without Robot Framework files", async () => {
    assert.strictEqual(await isRobotProject(await folderWith({ ".robot.toml": "" }), FILE_EXTENSIONS), true);
  });

  test("a pyproject.toml that depends on Robot Framework makes it one", async () => {
    const folder = await folderWith({
      "pyproject.toml": '[project]\nname = "demo"\ndependencies = ["robotframework>=7.0"]\n',
    });
    assert.strictEqual(await isRobotProject(folder, FILE_EXTENSIONS), true);
  });

  test("a requirements.txt that lists RobotCode makes it one", async () => {
    const folder = await folderWith({ "requirements.txt": "requests\nrobotcode\n" });
    assert.strictEqual(await isRobotProject(folder, FILE_EXTENSIONS), true);
  });

  test("Robot Framework installed into the folder's virtual environment does not count", async () => {
    const folder = await folderWith({
      ...typeScriptProject,
      "venv/pyvenv.cfg": "home = /usr/bin\n",
      "venv/lib/python3.14/site-packages/robot/__init__.py": "",
      "venv/lib/python3.14/site-packages/SomeLibrary/keywords.resource": "*** Keywords ***\n",
    });
    assert.strictEqual(await isRobotProject(folder, FILE_EXTENSIONS), false);
  });

  for (const skipped of ["build", ".hidden", "_private", "venv"]) {
    test(`Robot Framework files only in ${skipped}/ do not count`, async () => {
      const folder = await folderWith({ [`${skipped}/suites/example.robot`]: suiteFile });
      assert.strictEqual(await isRobotProject(folder, FILE_EXTENSIONS), false);
    });
  }

  test("a search cancelled before it starts finds no files", async () => {
    const folder = await folderWith({ "tests/example.robot": suiteFile });
    const cancellation = new vscode.CancellationTokenSource();
    cancellation.cancel();
    try {
      assert.strictEqual(await isRobotProject(folder, FILE_EXTENSIONS, cancellation.token), false);
    } finally {
      cancellation.dispose();
    }
  });
});

suite("isSkippedByRobotFilesSearch", () => {
  // the paths need not exist; the platform's own form, with a drive letter on Windows
  const root = path.join(os.tmpdir(), "robotcode-skipped");
  const folder: vscode.WorkspaceFolder = { uri: vscode.Uri.file(root), name: "robotcode-skipped", index: 0 };
  const uriOf = (relative: string) => vscode.Uri.file(path.join(root, ...relative.split("/")));

  test("a file in the folder counts", () => {
    for (const relative of ["tests/example.robot", "example.resource", "tests"]) {
      assert.strictEqual(isSkippedByRobotFilesSearch(folder, uriOf(relative), true), false, relative);
    }
  });

  test("a file in a skipped folder does not count", () => {
    for (const relative of [
      "node_modules/fake-pkg/fixtures/example.robot",
      "src/node_modules/example.robot",
      "build/suites/example.robot",
      "dist/example.robot",
      "target/example.robot",
      "venv/lib/example.resource",
      "CVS/example.robot",
      ".hidden/example.robot",
      "_private/example.robot",
    ]) {
      assert.strictEqual(isSkippedByRobotFilesSearch(folder, uriOf(relative), true), true, relative);
    }
  });

  test("a new file or folder with a skipped name does not count", () => {
    for (const relative of ["node_modules", "src/.vscode", ".robotcode_cache", "__pycache__", "_draft.robot"]) {
      assert.strictEqual(isSkippedByRobotFilesSearch(folder, uriOf(relative), true), true, relative);
    }
  });

  test("a configuration file counts by the folders it lies in, not by its own name", () => {
    for (const relative of [".robot.toml", ".gitignore", "robot.toml"]) {
      assert.strictEqual(isSkippedByRobotFilesSearch(folder, uriOf(relative), false), false, relative);
    }
    assert.strictEqual(isSkippedByRobotFilesSearch(folder, uriOf("node_modules/fake-pkg/robot.toml"), false), true);
  });

  test("the folder itself counts", () => {
    assert.strictEqual(isSkippedByRobotFilesSearch(folder, folder.uri, true), false);
  });

  test("a path in another case counts by its names below the folder", () => {
    const upper = vscode.Uri.file(path.join(root.toUpperCase(), "tests", "example.robot"));
    assert.strictEqual(isSkippedByRobotFilesSearch(folder, upper, true), false);
  });
});
