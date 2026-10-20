import * as assert from "assert";

import { escapeRobotGlobPatterns } from "../extension/utils";

suite("escapeRobotGlobPatterns", () => {
  test("puts every glob character of Robot Framework's patterns in brackets", () => {
    assert.strictEqual(escapeRobotGlobPatterns("Project.A*b [x]"), "Project.A[*]b [[]x[]]");
    assert.strictEqual(escapeRobotGlobPatterns("a*b.robot"), "a[*]b.robot");
    assert.strictEqual(escapeRobotGlobPatterns("Suite?"), "Suite[?]");
  });

  test("leaves a name without glob characters as it is", () => {
    assert.strictEqual(
      escapeRobotGlobPatterns("Electron & Vscode.Vscode.Open Vs Code"),
      "Electron & Vscode.Vscode.Open Vs Code",
    );
  });
});
