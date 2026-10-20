// The tests of the VS Code extension, run by `vscode-test` (npm test) in a downloaded VS Code. The extension's
// extensionDependencies (ms-python.python, ms-python.debugpy) are installed into it from the Marketplace.
import path from "node:path";

import { defineConfig } from "@vscode/test-cli";

export default defineConfig({
  files: "out/test/**/*.test.js",
  // The minimum the extension declares; the newest VS Code is covered by the checks in the harness.
  version: "1.127.0",
  mocha: {
    ui: "tdd",
    // Where the xunit reporter of the CI writes the results (npm test -- --reporter xunit). `vscode-test` passes
    // `--reporter-option` to Mocha unparsed, so the file is set here.
    reporterOptions: { output: path.join(import.meta.dirname, "test-results", "vscode", "test-results.xml") },
  },
});
