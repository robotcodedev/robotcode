# Design

## Context

Highlighting in the IntelliJ plugin has two layers:

1. **Grammar layer.** `RobotCodeLexer` maps known TextMate scopes to element types. `RobotCodeSyntaxHighlighter` gives each element type a `Colors` key. Scopes without an element type go through a small scope→default-key table (`textMateElementMap`).
2. **Semantic layer.** LSP4IJ draws the language server's semantic tokens on top. `RobotCodeSemanticTokensColorsProvider` maps each token type to a `Colors` key. For a non-null key, LSP4IJ adds a highlight above the grammar layer. For `null`, it adds nothing.

Each `Colors` key falls back to a `DefaultLanguageHighlighterColors` key. In addition, `plugin.xml` registers `additionalTextAttributes` files with hex colours for the schemes "Darcula", "Dark" (also the Darcula file; `RobotDarkColorScheme.xml` is unused) and "Light".

Facts these decisions rest on. Each one was checked against the PyCharm 2026.1 jars or the 261 platform source. The facts about individual schemes are a snapshot: JetBrains changes its schemes and default themes often. They explain why a category was chosen. The plugin must not depend on them.

- **Fallback keys without a colour.** In Darcula, Dark, Islands Dark, Light and IntelliJ Light, `DEFAULT_FUNCTION_CALL` and `DEFAULT_GLOBAL_VARIABLE` have no colour of their own. Both fall back to `DEFAULT_IDENTIFIER`, which is plain text.
- **Fallback keys with a colour.** `DEFAULT_FUNCTION_DECLARATION` (`ffc66d` / `56a8f5` / `00627a`) and `DEFAULT_INSTANCE_FIELD` (`9876aa` / `c77dbb` / `871094`) are coloured in all five schemes. The bundled third-party schemes colour them too, except WarmNeon, which has no function declaration colour. The "Default" scheme ("Classic Light") colours instance fields (`660e7a`, bold) but has no function colour at all, so Java method names are plain text there as well.
- **No merge with the fallback.** `EditorColorsSchemeImpl.getAttributes` returns attributes that a scheme defines directly, without merging them with the fallback key. A bundled entry that only sets bold therefore removes the fallback colour. That is why keyword names are black and bold in Light today.
- **Variables are one token.** The server sends a variable reference as one `variable` token that covers prefix, braces and name (design D7 of the semantic model, "legacy-compat emission"). It also sends a whole `${{ … }}` as one `variable` token. It sends no token for `IF` and `WHILE` conditions or for item-access suffixes such as `[0]` in arguments.
- **The `$` of a bare variable is unmapped.** In conditions, the grammar scopes it `punctuation.definition.variable.python.begin.robotframework`, which `RobotCodeLexer` does not map.
- **Grammar scopes with several names.** Some grammar rules give one token several space-separated scope names, mostly the Python string and regular expression rules. The last name is the innermost.
- **Layers merge per attribute, in both IDEs.** IntelliJ's `IterationState` goes through the layers from top to bottom:
  - foreground and background: the first value that is not `null` wins;
  - font type: the first value that is not plain wins;
  - effects: merged per slot (frame, underline, strike), with the upper layer winning each slot (`TextAttributesEffectsBuilder.slipUnder`).

  VS Code applies only the properties a semantic style sets (`SEMANTIC_USE_*` flags in `sparseTokensStore.ts`) and drops tokens without any style (`NO_STYLING`).
- **Where IntelliJ differs from VS Code.** In IntelliJ, every key resolves through its fallback chain, at worst to `DEFAULT_IDENTIFIER` or `TEXT`. Both have an explicit plain-text foreground in every scheme. So a semantic key whose category the scheme does not colour still paints plain text over the grammar colour, for example:
  - `namespace` → `CLASS_REFERENCE` in Light, Dark and Islands Dark;
  - `namedArgument` → `PARAMETER`;
  - the LSP4IJ default for `parameter`.

  In VS Code, the grammar colour would stay in these cases.
- **Semantic colours follow scheme changes.** LSP4IJ asks the provider for keys on every highlighting pass, and the tokens themselves come from its cache (`LSPSemanticTokensHighlightVisitor`, `SemanticTokensData.highlight`). The platform restarts those passes on `EditorColorsManager.TOPIC` (`DaemonListeners`). That topic fires on a scheme switch and when the colour page applies a change to the active scheme (`ColorAndFontOptions.apply` → `schemeChangedOrSwitched`).
- **Namespace tokens.** Once its libraries are loaded, the server sends `BuiltIn.Log` as `namespace` (+ `builtin`), `.` as `operator` and `Log` as `keywordCall`. It sends `level=INFO` as `namedArgument` for `level` and `operator` for `=`, with no token for `INFO`.

## Goals / Non-Goals

**Goals:**
- Robot Framework colours come only from the active scheme, through fallback keys (spec: highlighting colours come from the active colour scheme).
- The plugin decides only which general category each token class belongs to. Nothing in the code, the spec or the tests names a particular scheme.
- Lexer and semantic layer agree on variable names, so names do not change colour when semantic tokens arrive (#655).
- The semantic layer only adds what the scheme or the user defines, as in VS Code (spec: semantic highlighting only adds what the colour scheme defines).

**Non-Goals:**
- No language server change. The server sends a variable reference as one `variable` token that covers its delimiters, so semantic highlighting draws the variable look over the braces. The braces keep their bracket look only where the server sends no token, for example in conditions, and until the semantic tokens arrive. Two ways out are left for a follow-up:
  - the provider leaves plain `variable` tokens to the lexer, which already splits braces and name;
  - the server sends the parts separately. The semantic model already knows them, but its renderer emits variables atomically, and the parity spec requires the same output as the legacy path.
- No VS Code change (`semanticTokenTypes` with `superType`, scope alignment). That is a separate change.
- No new colour settings and no grammar change.
- No bold or underline styling. See D1.

## Decisions

### D1: Remove the bundled colour files instead of fixing them

Delete the three `colorSchemes/*.xml` files and their three `additionalTextAttributes` entries in `plugin.xml`.

Alternatives considered:
- **Keep per-scheme colours, but register them for the root schemes "Default" and "Darcula".** The JetBrains Shell plugin does this. Hex colours only fit the scheme they were picked for, and they are exactly what makes the plugin theme-dependent.
- **Keep only the font styles** (bold names, underlined headers). A directly defined entry is not merged with its fallback (see Context), so a font-only entry costs the token its colour. Bold could only come back through a second, layered key with its own per-scheme definitions, which again means bundled scheme data. Users who want bold names can set it on the colour page.

### D2: Fallback keys

| Key(s) | Fallback before | Fallback after | Why |
|---|---|---|---|
| `KEYWORD_CALL` | `FUNCTION_CALL` | `FUNCTION_DECLARATION` | VS Code gives calls and definitions the same `entity.name.function` colour. Schemes commonly colour declarations and leave calls plain (as of 2026.1, every JetBrains scheme except "Default" does). |
| `KEYWORD_CALL_INNER`, `NAME_CALL` | `FUNCTION_CALL` | `KEYWORD_CALL` | One change on the colour page covers all calls. |
| `VARIABLE` | `GLOBAL_VARIABLE` | `INSTANCE_FIELD` | The usual "named value" colour of a scheme. As of 2026.1, it is coloured in every JetBrains scheme, while `GLOBAL_VARIABLE` is coloured in none. |
| `VARIABLE_EXPRESSION` | `GLOBAL_VARIABLE` | `VARIABLE` | Same colour as variables. |
| `EMBEDDED_ARGUMENT` | `STRING` | `VARIABLE` | The server marks embedded values as `variable` + `embedded`. VS Code shows them in the variable colour. |
| `BDD_PREFIX` | `METADATA` | `KEYWORD` | VS Code scopes it `keyword.modifier.*`. |

All other keys keep their fallback:
- variable and expression delimiters → `BRACES`, index brackets → `BRACKETS`, because they are brackets, not part of the name (see Non-Goals for how semantic highlighting draws over them);
- header, setting, setting import, control flow and `VAR` → `KEYWORD`;
- names → `FUNCTION_DECLARATION`;
- argument → `STRING`;
- named argument → `PARAMETER`;
- namespace → `CLASS_REFERENCE`;
- operator → `OPERATION_SIGN`;
- continuation → `DOT`;
- escape → `VALID_STRING_ESCAPE`;
- error → `INVALID_STRING_ESCAPE`;
- comments → line and block comment.

Named arguments and namespaces stay uncoloured in the JetBrains schemes. That matches how those schemes treat parameters and class references. With D5, their tokens then keep the grammar look instead of turning into plain text, which is also what VS Code shows in most themes.

Alternatives considered:
- **For variables: `STATIC_FIELD` or `CONSTANT`.** Same colours, but italic in every bundled scheme, which is noisy for the most frequent token. `GLOBAL_VARIABLE` is uncoloured.
- **For calls: `STATIC_METHOD` or `INSTANCE_METHOD`.** Both fall back to `FUNCTION_DECLARATION`, but schemes that style them, for example italic, would make calls look like static methods for no reason.

### D3: TextMate fallback lookup

Replace the per-segment loop in `RobotCodeSyntaxHighlighter.getTokenHighlights`:
1. Split the scope name on whitespace.
2. Go through the names from innermost to outermost, that is from last to first.
3. For each name, try its prefixes from longest to shortest (`a.b.c`, `a.b`, `a`) against `textMateElementMap`.
4. The first hit wins and is returned as the only key.
5. With no hit, return `HighlighterColors.TEXT`.

Remove the duplicate `entity.name.section` entry while there.

In `RobotCodeLexer.mapping`, add `punctuation.definition.variable.python.begin.robotframework` → `VARIABLE_BEGIN`, so the `$` of a bare `$name` looks like the `${` of a braced variable.

Alternative considered: hand unmapped scopes to the platform's TextMate theme colouring. That is a larger change built on platform internals, and the existing table covers the scopes that occur.

### D4: Semantic token provider

- Add `config` → `LINE_COMMENT`. VS Code scopes it `comment.line.configuration`.
- Add `escape` → `ESCAPE`.
- Add `variable,embedded` → `EMBEDDED_ARGUMENT`.
- Remove the unreachable entries `embeddedArgument` and `argument,embedded`.
- For a type without a mapping, after the type-plus-modifiers lookup, the type lookup and the LSP4IJ default, return `null`, so the grammar colour stays. Log the type once, using a concurrent set of reported types, instead of `warn` per token.

### D5: The semantic layer only draws what the scheme defines

After D4 has chosen a key, the provider checks it against `EditorColorsManager.getInstance().globalScheme`. It returns `null` if the key's resolved attributes in that scheme meet any of these conditions:
- they are `null` or empty (`TextAttributes.isEmpty`);
- they equal the scheme's attributes for `DefaultLanguageHighlighterColors.IDENTIFIER`;
- they equal the scheme's attributes for `HighlighterColors.TEXT`.

In these cases nothing along the fallback chain defines anything, and the grammar look stays. Otherwise, it returns the key. Because the layers merge per attribute (see Context), the merge then applies exactly what is defined:
- a style-only definition, such as italic or an underline without colour, keeps the grammar foreground and adds the style;
- a definition with a colour overrides the foreground.

The check lives in a small function that takes the key and the scheme, so tests can call it without LSP4IJ. It applies to every key the provider returns, including the LSP4IJ defaults for standard types such as `parameter` and `operator`. Scheme changes are picked up because the platform restarts the highlighting passes (see Context), so the provider caches nothing.

Alternatives considered:
- **Only more fallbacks (`parameter` and named arguments to the variable colour).** This does not work for namespaces. VS Code keeps whatever the grammar shows there (string in `Library    Collections`, function colour in `BuiltIn.Log`), and no single key can reproduce that.
- **Separate keys for the semantic layer that have no fallback**, so they are transparent by default. Semantic refinements the grammar cannot make, for example a keyword call in `Test Setup    Log`, would then lose the theme's colours.
- **Remove only the foreground from a key's attributes.** Not possible, because LSP4IJ takes a `TextAttributesKey`, not `TextAttributes`.

Remaining differences from VS Code:
- A key that has a colour always brings it. That is intended, because then the scheme colours that category.
- Bold or italic from the grammar layer cannot be switched off from above, because a plain font type means "inherit".
- If a scheme explicitly defines a category with exactly the plain-text attributes, it is treated as undefined.
- Editors with their own scheme, such as consoles or diffs, use the decision made for the global scheme. Robot Framework files open in normal editors.

### D6: Verification

The plugin has no highlighting tests yet. Add `BasePlatformTestCase` tests for three things. None of them asserts the colours of a particular scheme.
- **TextMate fallback lookup**, with the scope names from the spec scenarios.
- **Inheritance structure from D2**: the fallback key of each changed `Colors` key and of the delimiter keys. Also, in every scheme the test environment loads, these resolve to the same attributes as their fallback:
  - the variable expression and embedded argument keys as `Colors.VARIABLE`;
  - the brace keys as `BRACES`;
  - the index keys as `BRACKETS`.
- **The D5 check, on a copy of the global scheme:**
  - a key that falls through to `IDENTIFIER` yields `null`;
  - a key set to italic only is returned;
  - a key with a colour is returned;
  - a key whose general category gets a colour in the copy is returned.

Check the semantic layer and scheme switches by hand in `runIde`, with a few of the schemes the IDE currently bundles.

## Risks / Trade-offs

- **[Visible change for users of unmodified bundled schemes]** Keyword names in Darcula turn from hard-coded blue to Darcula's yellow function colour, and bold and underline go away. → The commit message states it, so it appears in the generated changelog. Users who want the old style back can set it under *Settings → Editor → Color Scheme → Robot Framework*.
- **[Calls and definitions share one colour]** → They are easy to tell apart by position: definitions start at column 0 in their own section. Users can set bold on "Keyword name" and "Test case name".
- **[A scheme styles a category unexpectedly]** For example, "Default" (Classic Light) shows instance fields in bold. → Accepted. It is the scheme's own style for that category.
- **[A scheme leaves a category uncoloured]** For example, "Default" and WarmNeon have no function declaration colour. → Keyword calls and names stay plain there, the same as function names in that scheme's other languages. The spec states this explicitly instead of promising colours in particular schemes.
- **[Delimiters drawn over by semantic highlighting]** The semantic `variable` token covers the braces and the whole `${{ }}`. So the bracket look of the delimiters, a user-set brace colour, and the Python colours inside `${{ }}` only show until the semantic tokens arrive, and wherever the server sends no token. → Known limitation of this change. The ways out are listed under Non-Goals.
- **[D5 reads the scheme per token]** One attribute lookup and up to two `equals` calls per token on each highlighting pass. → These are map lookups on small objects. If profiling shows a cost, cache the result per scheme and key, and clear the cache on `EditorColorsManager.TOPIC`.

## Migration Plan

Nothing to migrate. User changes are stored in the user's scheme and stay. Rollback is a revert of the change.
