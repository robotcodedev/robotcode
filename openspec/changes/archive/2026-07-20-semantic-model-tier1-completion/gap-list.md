# Task 1.3 — Real parity gap list (recorded from the repaired suite)

> **Historical red-phase record.** This list drove the concept rework (D6/D7:
> model carries final render semantics, renderer is declarative). All gaps are
> closed as of 2026-07-20 — parity is byte-exact on all 8 RF versions except
> the two reasoned xfails documented in `test_semantic_tokens_flag_parity.py`.

Measured with the honest red baseline (fixture fix + vacuity guard in place),
comparing legacy vs. model semantic-token output across the full corpus
(34 `.robot` files, RF 5.0–7.4). Categories are `TYPE:old->new`,
`MOD:type:old->new`, `LEN:old->new`, `OLD-ONLY:type`, `NEW-ONLY:type`,
aggregated by occurrence count.

## Structural (model emits tokens legacy suppresses)

- **NEW-ONLY:separator (6576)** — model emits whitespace `SEPARATOR` tokens;
  legacy drops `Token.SEPARATOR`/`EOL`/`EOS`. The `.` in `Namespace.Keyword`
  is also a model `SEPARATOR` but legacy renders it as `operator`
  (see `TYPE:operator->separator` 57).
- **NEW-ONLY:comment (1220)** — model emits `COMMENT` tokens everywhere;
  legacy drops comments unless inside an `InvalidSection`.

## Granularity lost by the single `HEADER` / generic kinds

- **TYPE:headerSettings/Variable/Testcase/Task/Keyword/Comment->header (~115)** —
  model collapses all section headers to one `HEADER` kind; legacy renders
  `headerSettings`, `headerVariable`, `headerTestcase`, `headerTask`,
  `headerKeyword`, `headerComment`.
- **TYPE:forSeparator->controlFlow (14)** — model maps `Token.FOR_SEPARATOR`
  to `CONTROL_FLOW`; legacy renders the FOR `IN`/`IN RANGE`/… word as
  `forSeparator`.

## Sub-token descent (2.1)

- **TYPE:variable->argument (310) + OLD-ONLY:variable (1855) + LEN:variable->argument (25)** —
  arguments/values containing variables render flat as one `argument` in the
  model; legacy emits text/variable fragments.

## Inner keyword calls (2.2)

- **TYPE:keywordCallInner->argument (25) + OLD-ONLY:keywordCall + TYPE:controlFlow->argument (15)** —
  Run Keyword variants: inner keyword names render as `argument` in the model;
  legacy renders `keywordCallInner` and `controlFlow` (ELSE/AND).

## Modifiers (2.3)

- **MOD:keywordCall:('builtin',)->() (375)** — builtin keyword modifier missing.
- **MOD:namespace:('builtin',)->() (20)** — builtin namespace modifier missing.
- **MOD:variable:()->('declaration',) (21)** — model adds `declaration` to
  assign/`VARIABLE_NAME` tokens; legacy renders those as plain `variable`.

## Embedded-argument keyword split (2.4)

- **OLD-ONLY:keywordCall (7171) + LEN:keywordCall->keywordCall (3394) +
  OLD-ONLY:argument (3399, `embedded` mod) + OLD-ONLY:variable (`embedded`)** —
  dominant in `very_big_file.robot`: embedded-argument keywords split the name
  into keyword text + `argument('embedded')` fragments + variable fragments;
  the model emits the whole keyword name as one `keywordCall`.

## Imports & settings mapping

- **TYPE:settingImport->setting (55)** — import keyword (`Library`/`Resource`/
  `Variables`) is `SETTING_NAME` in the model → `setting`; legacy → `settingImport`.
- **TYPE:namespace->settingImport (39)** — import path is `IMPORT_NAME` →
  `settingImport`; legacy → `namespace`.
- **TYPE:settingImport->controlFlow (12)** — `WITH NAME`/`AS` alias keyword.
- **LEN:operator->setting (118) + OLD-ONLY:setting (120) + OLD-ONLY:operator (199)** —
  bracket settings (`[Documentation]` etc.): legacy splits into
  `operator([) + setting + operator(])`; model emits one `setting` token.

## Named arguments

- **TYPE:namedArgument->variable (69), LEN:namedArgument->argument (38),
  LEN:parameter->variable (32), TYPE:variable->namedArgument (6),
  NEW-ONLY:namedArgument (4)** — model's `NAMED_ARGUMENT_NAME`/`VALUE` shape
  vs. legacy's `namedArgument + operator(=) + value`, plus `[Arguments]`
  parameter rendering differences.
</content>
