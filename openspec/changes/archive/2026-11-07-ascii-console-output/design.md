# Design

## Context

See proposal.md for the motivation. What I measured before planning:

- **How Python writes.** Python encodes `sys.stdout` with `errors="strict"`.
  - On Windows a pipe or file gets the ANSI code page. On the maintainer's Windows 11 VM that is cp1252 (OEM code page 850), and PowerShell 7.6 reads the output of programs as ibm850.
  - A console gets UTF-16 through the console API, and Linux gets the locale (UTF-8 almost everywhere).
  - Python 3.15 turns UTF-8 mode on by default (PEP 686): 3.15.2 reports `utf8_mode 1`, 3.14.9 `0` under a UTF-8 locale. On 3.15 the bug doesn't occur.
- **What fails on main.** With `PYTHONIOENCODING=cp1252`, `results summary`, `show`, `stats`, `log` and `diff` exit with 128 and a traceback, with and without `--color`. `compare` and `--format json` pass only because their characters (`—`, `·`, `…`) are in cp1252.
- **On the VM** (test `Grüße ✓`, status ❌):
  - today the command exits with 128;
  - `cp1252:replace` gives `? **FAIL** T.Grüße ?`;
  - UTF-8 is right only for readers that decode UTF-8;
  - PowerShell variables garble umlauts in every variant, because PowerShell decodes with cp850.
- **Which code page lacks what:**
  - the emoji and 😥 are in no Windows ANSI code page;
  - `→` is missing in cp1250–cp1258 and cp874;
  - `—` is missing in cp932 and cp949, and `·` in cp874 and cp932;
  - `…` is in all of them.
- **Where the characters are:**
  - 109 strings in 22 files, plus docstrings that are output: the help of Click commands and the help of the REPL dot-commands, which `.help` takes from the methods' docstrings in `console_interpreter.py`;
  - box-drawing `─` and `—` as an empty value in `analyze cache`;
  - 😥 in `config` and `profiles`;
  - the German message in the debugger was translated before this change (225834f12).
- **rich** doesn't fall back to ASCII. Rendering Markdown to a cp1252, cp932 or ASCII stream fails on its own bullet `•` and quote bar `▌`. **prompt_toolkit** draws its own frames with `─│┌`.
- **JSON** output goes through `as_json` (`core/utils/dataclasses.py`) with `ensure_ascii=False`. `--format json results show` with a test `Grüße ✓` fails under cp1252. `as_json` also writes the messages of the JSON-RPC and DAP protocols.
- **`robotcode doc`** writes `library_doc`'s Markdown and signatures, the same code that builds the hovers:
  - `(⟶table, column, *names, 🏷limit: int = ${10}, **options)`;
  - argument tables with `` `⟶table` `` and `` `🏷limit` ``;
  - `**Return Type**: \`int\` — The number of rows.`

  Libdoc writes the same signature as `table, /, column, *names, limit: int = 10, **options`. Robot Framework's argument list holds the markers as entries of kind `POSITIONAL_ONLY_MARKER` and `NAMED_ONLY_MARKER`.

## Goals / Non-Goals

**Goals:**

- The text robotcode composes for the console is ASCII, so it works on any stream encoding.
- `--format json` works on any stream encoding without losing a character.
- Tests catch a non-ASCII character that comes back.

**Non-Goals:**

- The user's data (names, messages, documentation, metadata, paths). Decided by the user: that is Python's business; `PYTHONUTF8=1`, or Python 3.15, gives UTF-8 output for it.
- `errors="replace"` or forcing UTF-8 on the streams. The user chose ASCII text instead.
- The language server and the debug adapter. LSP and DAP are UTF-8 by protocol, and the hovers keep 🏷, `⟶` and `—`.
- The prompt_toolkit interface of the REPL (doc viewer, completion menu, toolbar). prompt_toolkit draws its own frames with box-drawing characters, and the interface only runs in a real terminal.
- `robotcode robot`'s Robot Framework console output. Robot Framework encodes it itself with `errors="replace"`.
- `--format toml`. `tomli_w` has no ASCII mode.
- Docstrings that are never shown, and comments.

## Decisions

### D1: Replace the characters where robotcode writes them

The strings change at their source. Alternatives:

- **A filter on the stream** (`str.translate` before writing): it would also change the user's data, which stays as it is.
- **`errors="replace"`, or UTF-8 on the streams:** rejected by the user. Replacing loses the status and every character outside the code page; UTF-8 garbles text for readers that expect the code page.

### D2: The equivalents

| Character | Where | Becomes |
|---|---|---|
| ✅ ❌ ⏭ ⏸ ⚪ | status icon before the bold status | nothing; `**FAIL**` stays |
| 😥 | end of a message | nothing |
| `→`, `⟶` | between statuses, in the `diff` heading, in sort orders, `artefact(s) → dir` | `->` |
| `—` | between a heading and its subject (`# Summary — file`) | `: ` |
| `—` | between an item and its detail (`` `.cmd` — description ``, `` `T` — description ``, `(embedded x — see artefacts)`) | ` - ` |
| `—` | inside a sentence (help texts, messages, dot-command help) | the sentence rewritten with `:`, `;`, `,` or parentheses; never `--`, which reads as an option |
| `—` | an empty value (`analyze cache`) | `-` |
| `·` | between values (`23:51:01 · 1 ms`, `0/5 · 4/5`, `F1=help · Tab=complete`, the lines of a cache entry name) | `, ` |
| `…` | omission (`_… 3 more not shown_`, cut messages, `Run Keyword And …`) | `...` |
| `─` | separator line | `-` |
| `±` | dot-command help (`±5`) | `+/-` |
| 🏷, `⟶`, zero-width joiner | `robotcode doc` on the console | Libdoc's markers, see D5 |

### D3: Status markers

`_markdown.py` drops the icon table; `bold_status` writes `**FAIL**`. In a colored terminal rich still renders the name in bold.

Alternative: keep the icons on UTF-8 streams. Decided by the user: no emoji.

### D4: JSON escapes in the CLI only

`as_json` gets an `ensure_ascii` argument, `False` by default, and the CLI's JSON output passes `True`:

- `Application.print_data` for `json` and `json_indent`;
- the JSON reports of `analyze code`, written or echoed;
- the dump of `analyze`'s model dump command.

The protocols keep writing UTF-8. Alternative: change the default of `as_json`. That would also escape every LSP and DAP message, which has no reason for it.

### D5: ASCII decoration for `robotcode doc`

`library_doc`'s signature and Markdown builders get a switch for an ASCII decoration, which `doc_cli.py` sets and the language server leaves off. With it:

- signatures write the marker entries of Robot Framework's argument list as `/` and `*`, like Libdoc;
- arguments carry no 🏷 or `⟶` prefix, and no zero-width joiner, which is not needed in code spans;
- the return line is `**Return Type**: \`T\` - description`.

Text from the library's documentation stays as it is.

Alternative: post-process the Markdown in `doc_cli.py`. Replacing ` — ` there would also change a library's own documentation.

### D6: Colors only on a UTF stream

`echo_as_markdown` takes the plain path, the raw Markdown, when `Console().encoding` is not a UTF encoding, also when colors are on. Without colors, the default for a pipe, nothing changes.

### D7: Tests

- In-process, the help of every command and subcommand of the root group (`get_help` over the Click tree) is ASCII.
- Every `results` command and view, with ASCII test data, writes only ASCII. So do `discover`, `analyze cache`, `config`/`profiles` and `doc`.
- In a subprocess with a real stream encoding:
  - `results summary --failed` under cp1252, the #683 case;
  - `--format json results show` with `Grüße ✓` under cp1252;
  - `--color results summary` under cp1252;
  - `.help` of every dot-command in `robotcode repl` with piped input under ASCII.
- The hover tests of the language server keep asserting 🏷 and `⟶`.
- Tests that assert the old characters change with the output.

### D8: Docs

The example outputs in the guides are produced again with the new output:

- `guides/cli/analyzing-results.md`;
- `getting-started/command-line.md`;
- `guides/tips/variable-not-found.md`;
- any other page whose example shows the characters.

`analyzing-results.md` gets a short note: robotcode's own text is ASCII, and for names or messages outside the code page `PYTHONUTF8=1` gives UTF-8 output, as Python 3.15 does by default. `reference/cli.md` is regenerated.

## Risks / Trade-offs

- [Scripts that search the text output for ✅ or `→` stop matching] → The text output is for people; `--format json` is the interface for scripts. Not marked breaking; that is the user's call.
- [A non-ASCII character comes back in a later change] → The tests of D7 cover the help of every command and the output of the commands above, and they run in CI.
- [The console and the hovers show argument kinds differently] → Decided by the user: only the console text is ASCII.
- [JSON with escapes is harder to read by eye] → `jq` and every JSON parser decode the escapes.
- [Help texts get long rewrites] → Each sentence keeps its meaning; `reference/cli.md` shows the result for review.
