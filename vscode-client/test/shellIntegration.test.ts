import * as assert from "assert";

import { commandLineSequence, escapeOscValue, runHeader } from "../extension/shellIntegration";

suite("shellIntegration", () => {
  test("escapes backslashes, semicolons, spaces and control characters as VS Code reads them", () => {
    assert.strictEqual(escapeOscValue("C:\\shop\\python.exe"), "C:\\\\shop\\\\python.exe");
    assert.strictEqual(escapeOscValue("-v a;b"), "-v\\x20a\\x3bb");
    assert.strictEqual(escapeOscValue("line\nnext"), "line\\x0anext");
    assert.strictEqual(escapeOscValue("robot"), "robot");
  });

  test("writes the command line as an OSC 633 sequence", () => {
    assert.strictEqual(commandLineSequence("robot -p ci"), "\x1b]633;E;robot\\x20-p\\x20ci\x07");
  });

  test("shows the short command line before a run and gives VS Code the full one", () => {
    assert.strictEqual(
      runHeader("robotcode debug", "/project/.venv/bin/python /ext/bundled/tool/robotcode debug"),
      "\x1b]633;A\x07\x1b[0m\x1b[7m * \x1b[0m Executing: \x1b]633;B\x07robotcode debug\r\n" +
        "\x1b]633;C\x07\x1b]633;E;/project/.venv/bin/python\\x20/ext/bundled/tool/robotcode\\x20debug\x07",
    );
  });
});
