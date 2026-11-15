import * as assert from "assert";

import { documentFormatSelectors } from "../extension/languageclientsmanger";

suite("documentFormatSelectors", () => {
  test("a selector for each extension of the Markdown format, in the folder", () => {
    assert.deepStrictEqual(
      documentFormatSelectors("/work/shop", [{ name: "markdown", extensions: ["md", "robot.md"] }]),
      [
        { scheme: "file", pattern: "/work/shop/**/*.md" },
        { scheme: "file", pattern: "/work/shop/**/*.robot.md" },
      ],
    );
  });

  test("no selector without a format", () => {
    assert.deepStrictEqual(documentFormatSelectors("/work/shop", []), []);
  });

  test("no selector for the formats the language server does not serve", () => {
    assert.deepStrictEqual(
      documentFormatSelectors("/work/shop", [
        { name: "robot", extensions: ["robot", "txt"] },
        { name: "json", extensions: ["rbt"] },
        { name: "rest", extensions: ["robot.rst"] },
        { name: "markdown", extensions: ["robot.md"] },
      ]),
      [{ scheme: "file", pattern: "/work/shop/**/*.robot.md" }],
    );
  });
});
