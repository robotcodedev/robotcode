# Proposal

## Why

In the IntelliJ plugin, variables and keyword calls are drawn as plain text in every colour scheme JetBrains ships (Darcula, Dark, Islands Dark, Light, IntelliJ Light). Their fallback keys, `DEFAULT_GLOBAL_VARIABLE` and `DEFAULT_FUNCTION_CALL`, have no colour of their own in those schemes. So the two look the same, and Robot Framework files look much flatter than in VS Code. On top of that, the plugin ships hard-coded colours for three schemes only. When the language server's semantic tokens arrive, they cover a whole variable such as `${NAME}`, which removes even the blue braces from those colours (issue #655: "for one second it displays ok").

## What Changes

- Remove the bundled per-scheme colour files (`RobotDarculaColorScheme.xml`, `RobotDarkColorScheme.xml`, `RobotLightColorScheme.xml`) and their `additionalTextAttributes` registrations. Every Robot Framework colour then comes from the active scheme through its fallback key.
- Re-pick the fallback keys so that every token class inherits from the general language colour that matches the category VS Code gives it. Prefer categories that colour schemes actually colour (function declaration, instance field) over ones they commonly leave plain (function call, global variable). No decision depends on a particular scheme, because JetBrains changes its schemes often:
  - keyword calls fall back to the function declaration colour, as in VS Code, where calls and definitions share the function colour;
  - variables fall back to the field colour;
  - variable braces, `${{ }}` delimiters and index brackets keep inheriting from the brace and bracket colours, because they are brackets, not part of the name;
  - BDD prefixes fall back to the keyword colour.
- Fix the TextMate fallback lookup for grammar scopes that have no Robot Framework key, such as the Python expressions in `IF` and `WHILE` conditions and regular expressions. Today it only matches single scope segments, so keys such as `keyword.operator` or `constant.numeric` never apply, and `>` in a condition gets the keyword colour. Map the `$` of a bare `$name` in expressions like the other variable prefixes.
- Make the semantic token colour provider cover every token type the server sends (`config`, `escape`, embedded arguments). Unknown types no longer write a warning to the log for every token.
- Let semantic highlighting add only what the colour scheme or the user actually defines (colour, font style, effects), as VS Code does. Today, a semantic token whose category the scheme does not colour paints plain text over the grammar colour, because every key resolves to the plain-text colour in the end. This happens with namespaces such as `BuiltIn` in `BuiltIn.Log`, with named argument names such as `level=`, and with `[Arguments]` parameters.
- Users who changed Robot Framework colours in their own scheme keep their settings. Users of an unmodified scheme see the new defaults. For example, keyword names in Darcula move from the hard-coded blue to Darcula's function colour, and bold names and underlined headers go away.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-syntax-highlighting`: adds requirements on
  - where highlighting colours come from (the active scheme only);
  - which general language colour each token class inherits from;
  - how variable names and their delimiters look;
  - that semantic highlighting only adds what the scheme defines;
  - how unmapped grammar scopes are coloured;
  - that every semantic token type the server sends has a colour setting.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/Colors.kt`: fallback keys.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeSyntaxHighlighter.kt`: TextMate scope fallback.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeSemanticTokensColorsProvider.kt`: token type mapping, logging, check against the active scheme.
- `intellij-client/src/main/resources/colorSchemes/*.xml` (removed) and `intellij-client/src/main/resources/META-INF/plugin.xml` (`additionalTextAttributes` entries removed).
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/RobotCodeLexer.kt`: one more scope mapping (the `$` of `$name`).
- New highlighting tests under `intellij-client/src/test/kotlin/`.
- No language server, VS Code or grammar change. Addresses #655: variable names no longer change colour when semantic tokens arrive. The braces still do, because the server sends a variable as one token (see design).
