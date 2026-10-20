// The tests of the VS Code extension, run by `vscode-test` (npm test) in a downloaded VS Code. The extension's
// extensionDependencies (ms-python.python, ms-python.debugpy) are installed into it from the Marketplace.
import { readFileSync } from "node:fs";
import path from "node:path";

import { defineConfig } from "@vscode/test-cli";

// The minimum VS Code version that the extension declares in engines.vscode, without the range character.
// `npm test -- --code-version stable` runs the tests with the newest one; the CI runs both.
const { engines } = JSON.parse(readFileSync(path.join(import.meta.dirname, "package.json"), "utf8"));
const minimumVersion = engines.vscode.replace(/^[^0-9]*/, "");

export default defineConfig({
  files: "out/test/**/*.test.js",
  version: minimumVersion,
  mocha: {
    ui: "tdd",
    // Where the xunit reporter of the CI writes the results (npm test -- --reporter xunit). `vscode-test` passes
    // `--reporter-option` to Mocha unparsed, so the file is set here.
    reporterOptions: { output: path.join(import.meta.dirname, "test-results", "vscode", "test-results.xml") },
  },
});
