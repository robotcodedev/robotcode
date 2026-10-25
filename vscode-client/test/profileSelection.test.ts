import * as assert from "assert";

import { selectionWithout, unknownNamesOfSelection, unknownSelectedProfilesMessage } from "../extension/utils";

suite("unknownSelectedProfilesMessage", () => {
  test("names one profile and the folder", () => {
    assert.strictEqual(
      unknownSelectedProfilesMessage(["typo"], "robotcode-demo"),
      'The selected profile "typo" is not defined in the configuration of the folder "robotcode-demo".',
    );
  });

  test("names several profiles and the folder", () => {
    assert.strictEqual(
      unknownSelectedProfilesMessage(["typo", "ci-*"], "robotcode-demo"),
      'The selected profiles "typo", "ci-*" are not defined in the configuration of the folder "robotcode-demo".',
    );
  });
});

suite("selectionWithout", () => {
  test("keeps the order of the names that stay", () => {
    assert.deepStrictEqual(selectionWithout(["ci", "typo", "dev", "ci-*"], ["typo", "ci-*"]), ["ci", "dev"]);
  });
});

suite("unknownNamesOfSelection", () => {
  test("keeps only the reported names that the selection contains", () => {
    // `typo` comes from `robotcode.extraArgs`, `missing` from the selection
    assert.deepStrictEqual(unknownNamesOfSelection(["ci", "missing"], ["typo", "missing"]), ["missing"]);
  });

  test("leaves patterns and hidden profiles that select a profile in the selection", () => {
    assert.deepStrictEqual(unknownNamesOfSelection(["ci-*", "_local", "typo"], ["typo"]), ["typo"]);
  });

  test("names nothing when the list reports no such names", () => {
    assert.deepStrictEqual(unknownNamesOfSelection(["ci"], undefined), []);
  });
});
