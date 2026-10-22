import * as assert from "assert";

import { commandLine } from "../extension/commandLine";

suite("commandLine", () => {
  test("leaves plain arguments as they are", () => {
    const args = ["/home/me/.venv/bin/python", "-p", "ci", "--tcp", "49199", "-I", "tests/login.robot"];
    assert.strictEqual(commandLine(args, "linux"), args.join(" "));
    assert.strictEqual(
      commandLine(["C:\\shop\\.venv\\Scripts\\python.exe", "-p", "ci"], "win32"),
      "C:\\shop\\.venv\\Scripts\\python.exe -p ci",
    );
  });

  test("quotes an argument with a space", () => {
    assert.strictEqual(commandLine(["-s", "Tests.Env Probe"], "linux"), "-s 'Tests.Env Probe'");
    assert.strictEqual(commandLine(["-s", "Tests.Env Probe"], "win32"), '-s "Tests.Env Probe"');
  });

  test("quotes an argument with a single quote", () => {
    assert.strictEqual(commandLine(["it's"], "linux"), `'it'"'"'s'`);
    assert.strictEqual(commandLine(["it's"], "win32"), `"it's"`);
  });

  test("quotes an argument with a double quote", () => {
    assert.strictEqual(commandLine(['say "hi"'], "linux"), `'say "hi"'`);
    assert.strictEqual(commandLine(['say "hi"'], "win32"), `"say \\"hi\\""`);
  });

  test("quotes an empty argument", () => {
    assert.strictEqual(commandLine(["-v", ""], "linux"), "-v ''");
    assert.strictEqual(commandLine(["-v", ""], "win32"), '-v ""');
  });

  test("quotes an argument with a character a shell reads", () => {
    assert.strictEqual(commandLine(["-v", "URL:https://shop?a=1&b=2"], "linux"), "-v 'URL:https://shop?a=1&b=2'");
    assert.strictEqual(commandLine(["-v", "URL:https://shop?a=1&b=2"], "win32"), '-v "URL:https://shop?a=1&b=2"');
  });
});
