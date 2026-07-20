# Semantic Model for RobotCode

## Motivation

### Problem: Duplicated Analysis Across LSP Features

Currently, every LSP feature (semantic tokens, hover, completion, inlay hints, signature help, code actions) independently interprets the Robot Framework AST. Each feature must:

- Walk the AST tree
- Determine context (keyword call vs. template data vs. fixture vs. import)
- Resolve keywords via `find_keyword()`
- Handle BDD prefixes (Given/When/Then)
- Parse namespace qualifiers (`BuiltIn.Log`)
- Tokenize embedded variables via `tokenize_variables()`
- Handle Run Keyword variants with nested keyword arguments
- Understand template argument rows vs. regular keyword arguments

This leads to:
- **~400 LOC `KeywordTokenAnalyzer`** in `semantic_tokens.py` that duplicates `NamespaceAnalyzer._analyze_run_keyword()`
- **7+ `find_keyword()` calls per file** in `SemanticTokenGenerator` alone
- **Re-resolution** in `inlay_hint.py`, `signature_help.py`, `code_action_quick_fixes.py`
- **Inconsistent behavior** when different features interpret the same token differently

### Solution: A Single Pre-Computed Semantic Model

The NamespaceAnalyzer already walks the entire AST and resolves all keywords and variables. Instead of throwing that analysis away and re-doing it per LSP feature, we build a **Semantic Model** — a pre-computed, position-indexed representation of what every token means.

The new `SemanticAnalyzer` is a **complete replacement** for the `NamespaceAnalyzer` —
not just a model builder. It produces all existing outputs (diagnostics, keyword references,
variable references, namespace references, test case definitions, tag references, metadata
references, scope tracking) **plus** the `SemanticModel` as an additional output.

```
Current:
  RF Parser AST
       │
       ├── NamespaceAnalyzer     → references, diagnostics
       │
       ├── SemanticTokenGenerator → walks AST again, re-resolves
       ├── InlayHintProvider      → walks AST again, re-resolves
       ├── CompletionProvider     → walks AST again, interprets context
       ├── HoverProvider          → walks AST again, looks up definitions
       ├── SignatureHelp          → walks AST again, re-resolves
       └── CodeActions            → walks AST again, extracts namespace info

Proposed:
  RF Parser AST
       │
       ▼
  SemanticAnalyzer (replaces NamespaceAnalyzer entirely)
       │
       ├── → diagnostics             (same as before)
       ├── → keyword_references      (same as before)
       ├── → variable_references     (same as before)
       ├── → namespace_references    (same as before)
       ├── → test_case_definitions   (same as before)
       ├── → tag/metadata_references (same as before)
       ├── → SemanticModel           (NEW — pre-resolved token tree)
       │
       ├── SemanticTokenGenerator → reads model, pure mapping
       ├── InlayHintProvider      → reads model, argument lookup
       ├── CompletionProvider     → reads model, context-aware
       ├── HoverProvider          → reads model, has definitions
       ├── SignatureHelp          → reads model, has keyword + args
       └── CodeActions            → reads model, has everything
```

---

## Design

### Architecture Overview

The `SemanticAnalyzer` is a **complete replacement** for the `NamespaceAnalyzer`. It
produces from the start the **same complete output** as the `NamespaceAnalyzer` — it is
not merely a model builder, it takes over **all responsibilities** of the current
`NamespaceAnalyzer`:

- **Diagnostics** — emitting warnings and errors (unused variables, unknown keywords, etc.)
- **Keyword references** — tracking which keywords are called and where
- **Variable references** — tracking which variables are used and where
- **Local variable assignments** — tracking assignment ranges for variable definitions
- **Namespace references** — tracking which libraries/resources are referenced where
- **Test case definitions** — collecting test case metadata
- **Tag and metadata references** — tracking tag and metadata usage
- **Scope tracking** — managing variable visibility (replacing `ScopeTree`)

**Additionally**, it produces the `SemanticModel` — a pre-resolved, position-indexed
token tree that LSP features can query directly without re-walking the AST.

The `SemanticAnalyzer`'s output is a **superset** of the `NamespaceAnalyzer`'s output:
same `AnalyzerResult` type with all existing fields, plus the new `semantic_model` field.
This means `SemanticAnalyzer.run()` is a drop-in replacement for `NamespaceAnalyzer.run()`
— the result can be used anywhere the old result was expected.

The Semantic Model lives in the `robot` package (LSP-agnostic) and is implemented as a
**subpackage** (`semantic_analyzer/`) within `robot.diagnostics`, with a clear separation
of concerns across files:

```
packages/robot/src/robotcode/robot/diagnostics/
├── semantic_analyzer/            # NEW: Subpackage
│   ├── __init__.py               # Re-exports (SemanticModel, SemanticAnalyzer, etc.)
│   ├── model.py                  # SemanticModel container + query API
│   │                             #   (statement_at, token_at, token_path_at,
│   │                             #    find_variable, get_variables_at, build_index,
│   │                             #    enclosing_definition_block,
│   │                             #    enclosing_block_of_kind, enclosing_section,
│   │                             #    path_from_root)
│   ├── nodes.py                  # SemanticNode base, SemanticStatement (leaf) +
│   │                             #   12 subclasses, SemanticBlock + DefinitionBlock
│   │                             #   (containers), SemanticToken dataclass
│   ├── enums.py                  # NodeKind (unified enum for blocks + statements),
│   │                             #   TokenKind, ForFlavor, VarScope, OnLimitAction,
│   │                             #   ForZipMode, ImportType.
│   ├── analyzer.py               # SemanticAnalyzer — independent class, inherits ONLY
│   │                             #   from robot.utils.visitor.Visitor (NOT from
│   │                             #   NamespaceAnalyzer). FULL replacement for
│   │                             #   NamespaceAnalyzer. Uses NamespaceAnalyzer as
│   │                             #   template for structure and logic.
│   │                             #   Visitor pattern dispatches visit_*() per AST node.
│   │                             #   Produces ALL outputs: diagnostics, references,
│   │                             #   test case definitions, tag/metadata references,
│   │                             #   AND the SemanticModel.
│   ├── variable_tokenizer.py     # Variable decomposition into sub_tokens
│   │                             #   (all 15 variable forms, nested variables,
│   │                             #    index access, Python expressions)
│   ├── run_keyword.py            # Layered Run Keyword detection strategy
│   │                             #   (Type Hints → RUN_KW_REGISTER → Hardcoded)
│   └── serialization.py          # resolve_references() for post-unpickle,
│                                 #   pickle helper utilities
├── namespace_analyzer.py  # OLD: Unchanged during parallel development
├── model_helper.py        # OLD: Eliminated in Phase 4 (see ModelHelper section)
├── namespace.py           # MODIFIED: Stores + serializes model
```

**Design principle:** The `semantic_analyzer` subpackage is **self-contained** and does
not import or delegate to `ModelHelper`. All functionality that `ModelHelper` provides
(variable tokenization, BDD prefix handling, Run Keyword resolution, argument analysis,
keyword definition lookup) is **re-implemented from scratch** in the appropriate module
within the subpackage. `ModelHelper` can be consulted for implementation ideas, but the
new code must stand on its own. The goal is to eliminate `ModelHelper` entirely once the
migration is complete.

### Relationship to NamespaceAnalyzer

**The `SemanticAnalyzer` is the designated replacement for the `NamespaceAnalyzer`.**

The current `NamespaceAnalyzer` has two responsibilities:
1. **Analysis & diagnostics** — resolving keywords, variables, imports; emitting diagnostics
2. **Reference collection** — building `keyword_references`, `variable_references`, etc.

The `SemanticAnalyzer` takes over **both** roles and adds a third:
3. **Model building** — constructing the `SemanticModel` as a queryable token tree

The `SemanticModel` is a *by-product* of the analysis, not its sole purpose. The analyzer
still walks the AST, still resolves keywords via `KeywordFinder`, still resolves variables
via `VariableScope`, still emits `Diagnostic` objects, and still collects reference
locations. The model-building code hooks into the existing visitor methods — no additional
AST walk is needed.

#### Interface Contract (Same Inputs, Superset Outputs)

The `SemanticAnalyzer` exposes the **exact same 3-step lifecycle** as the
`NamespaceAnalyzer` — same constructor parameters, same `resolve()` signature, same
`run()` signature. The only difference is that `AnalyzerResult` gains the additional
`semantic_model` field. This makes the `SemanticAnalyzer` a true **drop-in replacement**
— callers (i.e. `Namespace`) can swap one for the other without changing any call site.

```python
# Step 1: Construction — identical parameters
analyzer = SemanticAnalyzer(
    model=ast_model,         # ast.AST — parsed RF AST (File node)
    source=source_path,      # str — file path on disk
    document_uri=uri,        # str — LSP document URI
    languages=languages,     # Optional[Languages] — RF ≥6 localization
)

# Step 2: Import resolution — identical signature and return type
resolved_imports: ResolvedImports = analyzer.resolve(
    library_doc=library_doc,       # ResourceDoc
    imports_manager=imports_manager,  # ImportsManager
    sentinel=sentinel,             # object (optional, for cycle detection)
)

# Step 3: Analysis — identical signature, superset return type
result: AnalyzerResult = analyzer.run(
    finder=keyword_finder,   # KeywordFinder
)
# result contains ALL fields from NamespaceAnalyzer's AnalyzerResult
# PLUS result.semantic_model: SemanticModel
```

After migration, the `AnalyzerResult` returned by `SemanticAnalyzer.run()` contains
exactly the same fields as today, plus `semantic_model: SemanticModel`:

```python
@dataclass(slots=True, frozen=True)
class AnalyzerResult:
    diagnostics: List[Diagnostic]                              # unchanged
    keyword_references: Dict[KeywordDoc, Set[Location]]        # unchanged
    variable_references: Dict[VariableDefinition, Set[Location]]  # unchanged
    local_variable_assignments: Dict[VariableDefinition, Set[Range]]  # unchanged
    namespace_references: Dict[LibraryEntry, Set[Location]]    # unchanged
    test_case_definitions: List[TestCaseDefinition]             # unchanged
    keyword_tag_references: Dict[str, Set[Location]]           # unchanged
    testcase_tag_references: Dict[str, Set[Location]]          # unchanged
    metadata_references: Dict[str, Set[Location]]              # unchanged
    scope_tree: ScopeTree                                       # transitional — removed in Phase 4
    semantic_model: Optional[SemanticModel]                     # NEW
```

The `scope_tree` field is carried for source compatibility with the existing `Namespace`
constructor; once Phase 4 removes `ScopeTree` (variable scope moves entirely into the
`SemanticModel`), this field is dropped.

#### Transition Period (Phase 2–3) — Feature Flag

The `SemanticAnalyzer` is a drop-in replacement for the `NamespaceAnalyzer`, controlled
by the single feature flag `robotcode.experimental.semanticModel`. The flag governs
both the analyzer selection and the LSP feature code path:

| Flag | Analyzer used | `namespace.semantic_model` | Migrated LSP features |
|------|---------------|----------------------------|-----------------------|
| `false` (default) | `NamespaceAnalyzer` only | `None` | Fall back to old `ModelHelper` path — zero overhead, identical behavior |
| `true` | `SemanticAnalyzer` only (replaces, not parallel) | `SemanticModel` instance | Use new model-based path |

LSP features never check the flag directly — they branch on
`if model := namespace.semantic_model:`, which is `None` exactly when the flag is
off. This makes it possible to run snapshot tests under both flag states and assert
identical output.

#### Final State (Phase 4)

The flag defaults to `true` and is eventually removed. `Namespace` always uses
`SemanticAnalyzer`. `NamespaceAnalyzer`, `ModelHelper`, and `ScopeTree` are deleted.

### Data Structures — Tree-Based Semantic Model

Instead of flat dicts (position → annotation), the Semantic Model is a **tree** that
mirrors the RF AST structure but is simplified, pre-resolved, and optimized for queries.

The RF AST is execution-oriented: deep nesting, many node types, raw unresolved tokens,
`isinstance` checks everywhere. The Semantic Model is query-oriented: few node types,
resolved references, direct access to what every token means.

#### Unified Node Hierarchy

All nodes in the SemanticModel share a common base class `SemanticNode` with a single
`NodeKind` enum that covers both blocks (structural containers) and statements (leaves):

```
SemanticNode (base — kind, line_start, line_end, parent: Optional[SemanticNode])
├── SemanticStatement (leaf — adds tokens: List[SemanticToken])
│   ├── KeywordCallStatement
│   │   └── RunKeywordCallStatement (parent of inner KeywordCallStatements)
│   ├── ForStatement, WhileStatement, IfStatement, ExceptStatement
│   ├── VarStatement, ReturnStatement, ImportStatement, SettingStatement
│   ├── DefinitionStatement, TemplateDataStatement
│   └── (base used directly for BREAK, CONTINUE, END, ELSE, etc.)
└── SemanticBlock (container — adds header: SemanticStatement, body: List[SemanticNode])
    └── DefinitionBlock (adds name, arguments_spec, local_variables, etc.)
```

Every node carries a `parent` back-pointer (set during analysis, `None` only for the
root `FILE` block). This enables bottom-up traversal — given any statement, walk up
to the enclosing definition, section, or control-flow block without re-querying the
model by line. See [Parent Navigation](#parent-navigation) below.

The model provides dual representation:
- **Tree** (`root: SemanticBlock`) for structural queries (outline, folding, scoping)
- **Flat list** (`statements: List[SemanticStatement]`) for O(1) indexed access

#### Comparison: RF AST vs. Semantic Model

```
RF AST (complex, unresolved):              Semantic Model (simple, resolved):

File                                       SemanticModel
├── SettingSection                           ├── root: SemanticBlock(kind=FILE)
│   ├── LibraryImport                       │   ├── SemanticBlock(kind=SETTING_SECTION)
│   │   ├── Token(NAME, "BuiltIn")          │   │   ├── ImportStatement(kind=IMPORT)
│   │   └── Token(ARGUMENT, "WITH NAME")    │   │   │   import_type=LIBRARY, tokens: [...]
│   └── ResourceImport                      │   │   └── ImportStatement(kind=IMPORT)
│       └── Token(NAME, "common.resource")  │   │       import_type=RESOURCE, tokens: [...]
├── TestCaseSection                          │   ├── SemanticBlock(kind=TESTCASE_SECTION)
│   └── TestCase                            │   │   └── DefinitionBlock(kind=TESTCASE)
│       ├── Token(TESTCASE_NAME, "My Test") │   │       ├── header: DefinitionStatement(TEST_CASE_DEF)
│       ├── Template                         │   │       ├── KeywordCallStatement(TEMPLATE_KEYWORD)
│       │   └── Token(NAME, "My KW")        │   │       │   tokens: [SemanticToken(KEYWORD, ...)]
│       ├── KeywordCall                      │   │       ├── KeywordCallStatement(KEYWORD_CALL)
│       │   ├── Token(KEYWORD, "Given ...")  │   │       │   tokens: [BDD_PREFIX, NAMESPACE, KEYWORD, ...]
│       │   ├── Token(ARGUMENT, "${msg}")   │   │       └── TemplateDataStatement(TEMPLATE_DATA)
│       │   └── Token(ARGUMENT, "INFO")     │   │           tokens: [ARGUMENT, ARGUMENT]
│       └── TemplateArguments                │   │
│           ├── Token(ARGUMENT, "arg1")     │   └── (flat list mirror in model.statements)
│           └── Token(ARGUMENT, "arg2")     │
                                             ├── statements: List[SemanticStatement]  (flat, indexed)
                                             └── file_scope: VariableScope
```

#### Core Data Structures

```python
class NodeKind(Enum):
    """What kind of semantic node this is — determines valid queries.

    Covers both structural blocks (FILE, sections, control flow containers)
    and leaf statements (keyword calls, settings, imports, etc.).

    Every concrete RF AST node maps to a dedicated NodeKind — there is no
    catch-all UNKNOWN value. The analyzer is expected to know what every
    statement is.
    """

    # --- Block kinds (structural containers) ---
    # Built during Phase 2 — visit_File / visit_*Section / visit_TestCase /
    # visit_Keyword / visit_For / visit_While / visit_If / visit_Try / visit_Group
    # produce a SemanticBlock or DefinitionBlock that is hooked into the
    # parent block's body. `model.root` is always populated.
    FILE = "file"
    SETTING_SECTION = "setting_section"
    TESTCASE_SECTION = "testcase_section"
    KEYWORD_SECTION = "keyword_section"
    VARIABLE_SECTION = "variable_section"
    COMMENT_SECTION = "comment_section"
    INVALID_SECTION = "invalid_section"
    TESTCASE = "testcase"
    KEYWORD = "keyword"
    FOR = "for"
    WHILE = "while"
    IF = "if"
    TRY = "try"
    GROUP = "group"

    # --- Statement kinds (leaf nodes) ---

    # Definitions
    TEST_CASE_DEF = "test_case_def"   # TestCaseName (covers tasks too)
    KEYWORD_DEF = "keyword_def"       # KeywordName
    VARIABLE_DEF = "variable_def"     # Var (RF 7.0+) and Variable (Variables section)

    # Keyword calls
    KEYWORD_CALL = "keyword_call"         # KeywordCall
    TEMPLATE_KEYWORD = "template_keyword" # TestTemplate / Template
    TEMPLATE_DATA = "template_data"       # TemplateArguments
    SETUP = "setup"                       # Fixture/Setup/TestSetup/SuiteSetup
    TEARDOWN = "teardown"                 # Fixture/Teardown/TestTeardown/SuiteTeardown

    # Control flow headers
    FOR_HEADER = "for_header"             # ForHeader
    IF_HEADER = "if_header"               # IfHeader
    ELSE_IF_HEADER = "else_if_header"     # ElseIfHeader
    ELSE_HEADER = "else_header"           # ElseHeader
    INLINE_IF_HEADER = "inline_if_header" # InlineIfHeader (no END, optional assign)
    WHILE_HEADER = "while_header"         # WhileHeader
    TRY_HEADER = "try_header"             # TryHeader
    EXCEPT_HEADER = "except_header"       # ExceptHeader
    FINALLY_HEADER = "finally_header"     # FinallyHeader
    GROUP_HEADER = "group_header"         # GroupHeader (RF 7.3+)

    # Control flow body statements
    END = "end"                           # End (closes FOR/IF/WHILE/TRY/GROUP)
    RETURN_STATEMENT = "return_statement" # ReturnStatement (RETURN keyword, RF 5.0+)
    RETURN_SETTING = "return_setting"     # Return / ReturnSetting ([Return] setting, deprecated)
    BREAK_STATEMENT = "break_statement"   # Break
    CONTINUE_STATEMENT = "continue_statement"  # Continue

    # Imports
    IMPORT = "import"                     # LibraryImport / ResourceImport / VariablesImport

    # Settings (Tags, Documentation, Timeout, Arguments, Metadata, ...)
    # Specific subclasses share NodeKind=SETTING; SettingStatement.setting_name
    # carries the discriminator (e.g. "Tags", "Documentation", "Timeout").
    SETTING = "setting"

    # Document structure
    SECTION_HEADER = "section_header"     # SectionHeader (*** Test Cases *** etc.)
    COMMENT = "comment"                   # Comment lines
    EMPTY_LINE = "empty_line"             # EmptyLine
    CONFIG = "config"                     # Config (RF 7.3+)
    ERROR = "error"                       # Error statement (parse error)


class TokenKind(Enum):
    """What this token represents — already resolved."""

    # Keyword-related
    KEYWORD = "keyword"                  # Resolved keyword name
    BDD_PREFIX = "bdd_prefix"            # "Given ", "When ", "Then ", ...
    NAMESPACE = "namespace"              # "BuiltIn" in "BuiltIn.Log"

    # Variable-related
    VARIABLE = "variable"                # ${var} — resolved
    VARIABLE_NOT_FOUND = "variable_not_found"  # ${var} — unresolved

    # Variable sub-parts (sub-tokens within VARIABLE / VARIABLE_NOT_FOUND)
    VARIABLE_PREFIX = "variable_prefix"              # $ @ & %
    VARIABLE_OPEN_BRACE = "variable_open_brace"      # {
    VARIABLE_CLOSE_BRACE = "variable_close_brace"    # }
    VARIABLE_BASE = "variable_base"                  s# name part: "name" in ${name}
    VARIABLE_EXTENDED = "variable_extended"           # .attr, * 5, etc. (extended variable syntax)
    VARIABLE_TYPE_SEPARATOR = "variable_type_separator"    # ": " before type hint
    VARIABLE_TYPE_HINT = "variable_type_hint"              # int, list[str], Secret, etc.
    VARIABLE_DEFAULT_SEPARATOR = "variable_default_separator"  # = in %{NAME=default}
    VARIABLE_DEFAULT_VALUE = "variable_default_value"          # default value text
    VARIABLE_PATTERN_SEPARATOR = "variable_pattern_separator"  # : before regex in embedded args
    VARIABLE_PATTERN = "variable_pattern"                      # regex pattern in embedded args
    VARIABLE_ASSIGN_MARK = "variable_assign_mark"              # = in ${result}=

    # Inline Python expression sub-parts (for ${{...}} variables)
    VARIABLE_EXPRESSION_OPEN = "variable_expression_open"    # {{
    VARIABLE_EXPRESSION_CLOSE = "variable_expression_close"  # }}
    PYTHON_EXPRESSION = "python_expression"                  # expression body inside ${{...}}
    PYTHON_VARIABLE_REF = "python_variable_ref"              # $var inside Python expressions

    # Index access sub-parts (after VARIABLE in token list)
    VARIABLE_INDEX = "variable_index"                  # [0], [key] as a group
    VARIABLE_INDEX_OPEN = "variable_index_open"        # [
    VARIABLE_INDEX_CLOSE = "variable_index_close"      # ]
    VARIABLE_INDEX_CONTENT = "variable_index_content"  # content between [ and ]

    # Text fragments (literal text between variables)
    TEXT_FRAGMENT = "text_fragment"                     # "Hello " in "Hello ${name}"

    # Arguments
    ARGUMENT = "argument"                # Positional argument value
    NAMED_ARGUMENT_NAME = "named_argument_name"   # "name" in name=value
    NAMED_ARGUMENT_VALUE = "named_argument_value"  # "value" in name=value

    # Control flow
    CONTROL_FLOW = "control_flow"        # AND, ELSE, ELSE IF in Run Keywords
    CONDITION = "condition"              # Condition expression in IF/WHILE

    # Definitions (used in definition headers and defining contexts)
    # These mark tokens where a name is *defined*, not *referenced*:
    #   TEST_NAME      — the name in a test case header line
    #   KEYWORD_NAME   — the name in a keyword definition header line
    #   VARIABLE_NAME  — the name in a defining context: VAR statement,
    #                     FOR loop variable, [Arguments] parameter, EXCEPT AS variable,
    #                     inline assignment (${result}=), inline IF assignment
    # In contrast, VARIABLE/VARIABLE_NOT_FOUND mark *references* to variables
    # in expressions and arguments (e.g. ${name} used in a keyword call).
    TEST_NAME = "test_name"
    KEYWORD_NAME = "keyword_name"
    VARIABLE_NAME = "variable_name"

    # Structure
    SETTING_NAME = "setting_name"        # "Tags", "Documentation", "Timeout", ...
    IMPORT_NAME = "import_name"          # Library/resource path
    HEADER = "header"                    # Section header (*** Test Cases *** etc.)
    SEPARATOR = "separator"              # The dot in "BuiltIn.Log"
    CONTINUATION = "continuation"        # ...
    COMMENT = "comment"
    TAG = "tag"
    CONFIG = "config"                    # Task group config (RF 7.3+)
    ERROR = "error"                      # Syntax error token


@dataclass(slots=True)
class SemanticToken:
    """A single resolved token in the Semantic Model.

    Contains both position info and resolved semantic information.
    All resolution has already happened — consumers just read fields.
    """

    # Position (from original RF Token)
    # Note: Robot Framework tokens are always single-line (one cell = one line).
    # Multi-line constructs use continuation lines (...) which are separate tokens
    # on separate lines. Therefore a single `line` field is sufficient — no
    # `end_line` is needed.
    kind: TokenKind
    value: str
    line: int            # 1-indexed (matches RF Token.lineno)
    col_offset: int      # 0-indexed (matches RF Token.col_offset)
    length: int

    # Sub-tokens (for tokens that contain embedded content)
    # e.g. ARGUMENT "${name} is ${age}" → sub_tokens with VARIABLE tokens
    sub_tokens: Optional[List["SemanticToken"]] = None

    # Pre-computed LSP `Range` covering this token. Built once in
    # __post_init__ so consumers get the canonical (0-indexed) Range
    # without re-deriving it from `line - 1` / `col_offset` / `length`.
    # Enables direct LSP semantics — `position in tok.range`,
    # `other_range in tok.range`, `tok.range.extend(end_character=2)`,
    # `position < tok.range.end` — instead of bespoke per-coordinate
    # arithmetic at every call site.
    range: Range = field(init=False, repr=False)

    def __post_init__(self) -> None:
        line0 = self.line - 1  # SemanticToken.line is 1-indexed; LSP is 0-indexed
        self.range = Range(
            start=Position(line=line0, character=self.col_offset),
            end=Position(line=line0, character=self.col_offset + self.length),
        )


@dataclass(slots=True)
class SemanticNode:
    """Common base for all nodes in the SemanticModel.

    Both statements (leaf nodes with tokens) and blocks (structural containers
    with children) share kind, position fields, and a back-pointer to their
    direct parent in the tree.
    """

    kind: NodeKind
    line_start: int = 0   # 1-indexed
    line_end: int = 0     # 1-indexed, inclusive

    # Back-pointer to the directly enclosing node (block OR statement).
    # `None` only for the root SemanticBlock(kind=FILE).
    #
    # Type is `SemanticNode` rather than `SemanticBlock` because some
    # statements logically contain other statements without a wrapping block:
    # `RunKeywordCallStatement.inner_calls` are `KeywordCallStatement`s whose
    # parent is the outer Run-Keyword statement, not a block. Keeping the
    # type open lets us model these without inventing fake wrapper blocks.
    #
    # Set during analysis by `_add_statement` / `_add_block` /
    # `RunKeywordCallStatement.__post_init__`. The model is immutable after `build_index()`,
    # so the parent reference is stable for the lifetime of the model.
    #
    # Excluded from `repr`/`compare` (`field(repr=False, compare=False)`)
    # to avoid infinite recursion in `__repr__` / `__eq__` through the cycle.
    parent: Optional["SemanticNode"] = field(default=None, repr=False, compare=False)


@dataclass(slots=True)
class SemanticStatement(SemanticNode):
    """Leaf node — a single resolved statement with tokens.

    Corresponds roughly to one RF AST node (KeywordCall, Fixture, etc.)
    but with all tokens pre-resolved and the statement kind determined.
    Subclasses add type-specific properties for completion, inlay hints, etc.

    Used directly for simple statements like BREAK, CONTINUE, COMMENT,
    END, ELSE, TRY, FINALLY, section headers.

    Subclass hierarchy:
        SemanticStatement (base — leaf nodes with tokens)
        ├── KeywordCallStatement     — keyword calls, setup, teardown, template keyword
        │   └── RunKeywordCallStatement — Run Keyword variants with nested inner calls
        ├── ForStatement             — FOR loop header line (block data on ForBlock)
        ├── WhileStatement           — WHILE loop header line (block data on WhileBlock)
        ├── IfStatement              — block-form IF / ELSE IF header line (block data on IfBlock)
        ├── InlineIfStatement        — inline IF (no block; condition + assign on the statement)
        ├── ExceptStatement          — EXCEPT header line (lives inside a TryBlock)
        ├── VarStatement             — VAR statement (RF 7.0+)
        ├── ReturnStatement          — deprecated [Return] setting (RETURN keyword
        │                              uses base SemanticStatement with kind=RETURN_STATEMENT)
        ├── ImportStatement          — Library / Resource / Variables import
        ├── SettingStatement         — [Tags], [Documentation], [Timeout], etc.
        │                              (one NodeKind per concrete setting type)
        ├── DefinitionStatement      — Test case / Task / Keyword definition header
        └── TemplateDataStatement    — Template argument rows
    """

    tokens: List[SemanticToken] = field(default_factory=list)


# --- Keyword-executing statements ---

@dataclass(slots=True)
class KeywordCallStatement(SemanticStatement):
    """A statement that executes a keyword: keyword calls, setup, teardown, template.

    Covers NodeKind: KEYWORD_CALL, SETUP, TEARDOWN, TEMPLATE_KEYWORD.
    """

    # Resolved keyword
    keyword_doc: Optional[KeywordDoc] = None

    # Resolved library entry for namespace qualifier ("BuiltIn" in "BuiltIn.Log")
    # Only set when the keyword is called with a namespace prefix.
    lib_entry: Optional[LibraryEntry] = None

    # Variables that receive the return value: ${result}=    My Keyword
    assign_variables: List[SemanticToken] = field(default_factory=list)


@dataclass(slots=True)
class RunKeywordCallStatement(KeywordCallStatement):
    """A keyword call containing nested keyword calls (Run Keyword variants,
    robot:keyword-call type hints).

    The outer keyword (e.g. Run Keyword If) is in keyword_doc.
    Inner keyword calls are full KeywordCallStatements with own keyword_doc,
    tokens (BDD prefix, namespace, keyword name, arguments), and potentially
    own inner_calls (deeply nested: Run Keyword If ... Run Keyword ... nested_kw).

    CONTROL_FLOW tokens (ELSE, AND, ELSE IF) stay on this statement's tokens
    list — they belong to the outer Run Keyword syntax, not to any inner call.

    Only created for actual Run Keyword variants — normal keyword calls use
    KeywordCallStatement directly, avoiding the extra inner_calls slot.
    isinstance(stmt, KeywordCallStatement) matches both types.
    """

    inner_calls: List[KeywordCallStatement] = field(default_factory=list)


# --- Control flow statements ---

class ForFlavor(Enum):
    """FOR loop variant — determines available options."""
    IN = "IN"
    IN_RANGE = "IN RANGE"
    IN_ENUMERATE = "IN ENUMERATE"
    IN_ZIP = "IN ZIP"


class ForZipMode(Enum):
    """IN ZIP mode= option values."""
    SHORTEST = "SHORTEST"
    LONGEST = "LONGEST"
    STRICT = "STRICT"


@dataclass(slots=True)
class ForStatement(SemanticStatement):
    """FOR loop header (the single line `FOR ${item} IN ...`).

    The header carries only its tokens. Block-level data (`flavor`,
    `loop_variables`, options) lives on the enclosing `ForBlock`.
    """


class OnLimitAction(Enum):
    """WHILE on_limit= option values."""
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(slots=True)
class WhileStatement(SemanticStatement):
    """WHILE loop header (the single line `WHILE ... [limit=...]`).

    Block-level data (`condition`, `limit`, `on_limit`, `on_limit_message`)
    lives on the enclosing `WhileBlock`.
    """


@dataclass(slots=True)
class IfStatement(SemanticStatement):
    """Block-form IF or ELSE IF header (the single line `IF ${cond}`).

    Covers NodeKind: IF_HEADER, ELSE_IF_HEADER. The block is closed by an END.
    Block-level data lives on the enclosing `IfBlock`. For the single-line
    form (no END, optional assign target, keyword inline) see `InlineIfStatement`.
    """


@dataclass(slots=True)
class InlineIfStatement(SemanticStatement):
    """Single-line inline IF.

    Covers NodeKind: INLINE_IF_HEADER.

    Inline IF is *not* a block (no `IfBlock` wraps it), so condition and
    assign target are kept on the statement directly:
    - no `END` closes it,
    - it can have an optional assign target (``${result}=    IF    ...``),
    - the body keyword + arguments live on the same line as the header.
    """

    # Condition expression
    condition: Optional[str] = None

    # Optional assign target: ${result}=    IF    ${cond}    My Keyword
    # Uses TokenKind.VARIABLE_NAME (defining context).
    assign_variable: Optional[SemanticToken] = None


@dataclass(slots=True)
class ExceptStatement(SemanticStatement):
    """EXCEPT header (single line `EXCEPT pattern [type=…] [AS ${err}]`).

    Lives inside a `TryBlock`; pattern values, the `type=` option, and the
    AS variable are read from the header tokens (TokenKind.ARGUMENT,
    NAMED_ARGUMENT_NAME/VALUE, VARIABLE_NAME).
    """


# --- Variable / Return statements ---

class VarScope(Enum):
    """VAR scope= option values."""
    LOCAL = "LOCAL"
    TEST = "TEST"
    TASK = "TASK"
    SUITE = "SUITE"
    GLOBAL = "GLOBAL"


@dataclass(slots=True)
class VarStatement(SemanticStatement):
    """VAR statement.

    Completable options: scope= (LOCAL|TEST|TASK|SUITE|GLOBAL), separator=
    """

    # Variable being defined
    variable_name: Optional[SemanticToken] = None

    # Options
    scope: Optional[VarScope] = None
    separator: Optional[str] = None

    # Values (the assigned value tokens)
    values: List[SemanticToken] = field(default_factory=list)


@dataclass(slots=True)
class ReturnStatement(SemanticStatement):
    """Deprecated [Return] setting.

    Covers NodeKind: RETURN_SETTING ([Return] setting, deprecated since RF 5.0).
    The modern RETURN keyword (RF 5.0+) is captured by the generic visit_Statement()
    fallback as kind=RETURN_STATEMENT with a CONTROL_FLOW token, not via this subclass.
    Values are in tokens as TokenKind.ARGUMENT.
    """

    return_values: List[SemanticToken] = field(default_factory=list)


# --- Import statements ---

class ImportType(Enum):
    """Type of import."""
    LIBRARY = "LIBRARY"
    RESOURCE = "RESOURCE"
    VARIABLES = "VARIABLES"


@dataclass(slots=True)
class ImportStatement(SemanticStatement):
    """Library / Resource / Variables import.

    Completable: import path, WITH NAME alias, library arguments.
    """

    import_type: Optional[ImportType] = None

    # Import name/path
    import_name: Optional[str] = None

    # WITH NAME / AS alias
    alias: Optional[str] = None

    # Library arguments (only for LIBRARY)
    arguments: List[SemanticToken] = field(default_factory=list)

    # Resolved library entry
    lib_entry: Optional[LibraryEntry] = None

    # First __init__ KeywordDoc of the imported library/variables file, if any.
    # Pre-resolved during analysis so consumers (inlay hints, signature help)
    # don't need a second AST walk + libdoc lookup. Falls back to the
    # imports_manager's default-libdoc when the resolved entry has errors —
    # matches the legacy inlay-hint behaviour.
    init_keyword_doc: Optional[KeywordDoc] = None


# --- Settings ---

@dataclass(slots=True)
class SettingStatement(SemanticStatement):
    """A setting line: [Tags], [Documentation], [Timeout], [Arguments], etc.

    Each concrete setting has its own NodeKind (`SETTING_TAGS`,
    `SETTING_DOCUMENTATION`, `SETTING_TIMEOUT`, `SETTING_ARGUMENTS`, …).
    Consumers should branch on `kind`; the `setting_name` field is kept
    for display purposes (matches the RF source label).
    """

    # Display label, e.g. "Tags", "Documentation", "Timeout", "Arguments".
    setting_name: Optional[str] = None

    # For [Arguments]: the defined argument variables
    argument_definitions: List[SemanticToken] = field(default_factory=list)

    # For [Tags]: the tag values
    tag_values: List[str] = field(default_factory=list)


# --- Definitions ---

@dataclass(slots=True)
class DefinitionStatement(SemanticStatement):
    """Test case, task, or keyword definition header.

    Covers NodeKind: TEST_CASE_DEF, KEYWORD_DEF.
    Note: Tasks and test cases share the same AST node class (TestCase)
    in Robot Framework, so both use TEST_CASE_DEF.

    Also carries the block-local variable scope — replaces ScopeTree's LocalScope.
    Robot Framework has no nested function scopes: FOR/IF/TRY variables "leak"
    to the containing Keyword/TestCase, so one flat list per DefinitionStatement
    is sufficient.
    """

    # Name of the test/keyword
    name: Optional[str] = None

    # For keywords: resolved argument spec, return type, tags
    arguments_spec: Optional["KeywordArgumentSpec"] = None
    return_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Block-local variables with visibility positions (replaces LocalScope)
    # Includes: [Arguments] parameters, FOR loop variables, inline assignments,
    # VAR LOCAL definitions, EXCEPT AS variables.
    # Each entry is (VariableDefinition, visible_from_line: int).
    # Variables are visible from their definition line to the end of this block.
    local_variables: List[Tuple[VariableDefinition, int]] = field(default_factory=list)


# --- Template data ---

@dataclass(slots=True)
class TemplateDataStatement(SemanticStatement):
    """Template argument row — not a keyword call, just argument values.

    The template keyword is in the parent test/keyword definition.
    Covers NodeKind: TEMPLATE_DATA.
    """

    # Reference to the template's keyword doc (for argument matching)
    template_keyword_doc: Optional[KeywordDoc] = None


# --- Blocks (structural containers) ---

@dataclass(slots=True)
class SemanticBlock(SemanticNode):
    """Container node — structural nesting in the SemanticModel.

    Represents RF AST blocks: File, Sections, TestCase, Keyword,
    and control flow containers (FOR, WHILE, IF, TRY, GROUP).

    The `header` is the block's opening statement (e.g. ForHeader,
    IfHeader, SectionHeader). For File blocks, header is None.

    The `body` contains the block's children — a mix of statements
    and nested blocks.

    Subclass hierarchy:
        SemanticBlock (base — used directly for File and Sections)
        ├── DefinitionBlock  — TestCase / Keyword with scope data
        ├── ForBlock         — FOR ... END loop with flavor / loop variables / options
        ├── WhileBlock       — WHILE ... END loop with condition / limit / on_limit
        ├── IfBlock          — IF / ELSE IF / ELSE ... END (multi-branch via nesting)
        ├── TryBlock         — TRY / EXCEPT / ELSE / FINALLY ... END
        └── GroupBlock       — GROUP ... END (RF 7.3+)
    """

    header: Optional[SemanticStatement] = None
    body: List[SemanticNode] = field(default_factory=list)


@dataclass(slots=True)
class DefinitionBlock(SemanticBlock):
    """TestCase or Keyword block — carries scope and definition metadata.

    Covers NodeKind: TESTCASE, KEYWORD.

    The header is a DefinitionStatement (TEST_CASE_DEF or KEYWORD_DEF).
    Block-local variables live here because RF has no nested function scopes:
    FOR/IF/TRY variables "leak" to the containing Keyword/TestCase.
    """

    name: Optional[str] = None
    arguments_spec: Optional["ArgumentSpec"] = None
    return_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Block-local variables with visibility positions (replaces LocalScope).
    # Each entry is (VariableDefinition, visible_from_line: int).
    # Variables are visible from their definition line to the end of this block.
    local_variables: List[Tuple[VariableDefinition, int]] = field(default_factory=list)


@dataclass(slots=True)
class ForBlock(SemanticBlock):
    """Container for a complete `FOR ... END` construct.

    Covers NodeKind: FOR. `header` is a `ForStatement`. `body` carries the
    loop body statements plus the closing END.

    Completable options depend on flavor:
    - IN RANGE: start, end, step
    - IN ENUMERATE: start= (starting index)
    - IN ZIP: mode= (SHORTEST|LONGEST|STRICT), fill=
    - IN: no options
    """

    flavor: Optional[ForFlavor] = None
    loop_variables: List[SemanticToken] = field(default_factory=list)
    start: Optional[str] = None        # IN ENUMERATE: start=
    mode: Optional[ForZipMode] = None  # IN ZIP: mode=
    fill: Optional[str] = None         # IN ZIP: fill=


@dataclass(slots=True)
class WhileBlock(SemanticBlock):
    """Container for a complete `WHILE ... END` construct.

    Covers NodeKind: WHILE. `header` is a `WhileStatement`.

    Completable options: limit=, on_limit=, on_limit_message=
    """

    condition: Optional[str] = None
    limit: Optional[str] = None
    on_limit: Optional[OnLimitAction] = None
    on_limit_message: Optional[str] = None


@dataclass(slots=True)
class IfBlock(SemanticBlock):
    """Container for a complete `IF / ELSE IF / ELSE ... END` construct.

    Covers NodeKind: IF. `header` is an `IfStatement` (for IF / ELSE IF) or
    a base `SemanticStatement(kind=ELSE_HEADER)` for ELSE. Multi-branch
    chains are represented as nested `IfBlock` entries inside the parent's
    body, mirroring RF's recursive `If` AST.
    """

    condition: Optional[str] = None  # set on IF / ELSE IF, None on ELSE


@dataclass(slots=True)
class TryBlock(SemanticBlock):
    """Container for a complete `TRY / EXCEPT* / [ELSE] / [FINALLY] ... END`.

    Covers NodeKind: TRY. The body holds protected statements plus nested
    `TryBlock` entries for EXCEPT / ELSE / FINALLY branches, then the END.
    """


@dataclass(slots=True)
class GroupBlock(SemanticBlock):
    """Container for a complete `GROUP ... END` construct (RF 7.3+).

    Covers NodeKind: GROUP. `header` is a base `SemanticStatement(kind=GROUP_HEADER)`.
    """
```

#### Parent Navigation

Top-down navigation alone isn't enough for many LSP features. Once a feature has
gotten hold of a node — typically via `model.statement_at(line)` or
`model.token_at(line, col)` — it often needs to walk **upward** to find scope or
context: which `DefinitionBlock` contains this statement? Which `IfBlock` is this
inside? What's the outer `RunKeywordCallStatement` for this inner call?

Without parent pointers the only options are (a) re-querying the model by line
(works for blocks but loses precision for nested calls), or (b) walking the entire
tree from `root` to find the node again.

**Design**: every `SemanticNode` carries a `parent: Optional[SemanticNode]`
back-pointer:

```python
@dataclass(slots=True)
class SemanticNode:
    kind: NodeKind
    line_start: int = 0
    line_end: int = 0
    parent: Optional["SemanticNode"] = field(default=None, repr=False, compare=False)
```

**Why `SemanticNode` and not `SemanticBlock`** — `RunKeywordCallStatement.inner_calls`
contain `KeywordCallStatement`s whose direct parent is the outer Run-Keyword
*statement*, not a wrapping block. Typing `parent` as `SemanticNode` keeps this
honest. For the common block-parent case, callers either `isinstance`-check or
use the model helpers (see below) that already filter to blocks.

**Where parents are set**:

| Call site | Sets parent on | Parent value |
|---|---|---|
| `_add_statement(stmt)` in `analyzer.py` | `stmt` | `self._block_stack[-1]` (the currently open block) |
| `_add_block(block)` in `analyzer.py` | `block` | `self._block_stack[-1]` |
| `visit_TestCase` / `visit_Keyword` in `analyzer.py` | `defn` (the `DefinitionStatement` header) | the just-built `DefinitionBlock` (bypasses `_add_statement` because the header lives as `block.header`, not as a body sibling) |
| `RunKeywordCallStatement.__post_init__` in `nodes.py` | each `inner` in `inner_calls` | `self` (the outer Run-Keyword statement) |

Headers of control-flow blocks (For / While / If / Try / Group) flow through
`_add_statement` while their block is on top of `_block_stack`, so their
parent is set to the block. For TestCase / Keyword the header bypasses
`_add_statement` (it must not also live in `body`), so `visit_TestCase` /
`visit_Keyword` set `defn.parent = defn_block` explicitly.

In all cases the header's `parent` is the block it heads (not the enclosing
block) — i.e., for `IfBlock { header: IfStatement }`, the
`IfStatement.parent` is the `IfBlock`. "The block owns its header."

The root `SemanticBlock(kind=FILE)` is the only node with `parent = None`.

Inner-call wiring lives on `RunKeywordCallStatement` itself rather than in
the analyzer because inner statements are constructed before they're
attached: a deeply-nested `Run Keyword If ... Run Keyword ...` builds the
innermost statement first and bubbles it up through `_make_inner_keyword_call`.
A `__post_init__` on `RunKeywordCallStatement` runs after every construction
and wires the parent unconditionally — works for both the analyzer and any
direct unit-test construction.

**Helper methods on `SemanticModel`** — instead of forcing every consumer to
re-implement upward walks, typed `@staticmethod`s do the parent-chain walk:

```python
class SemanticModel:
    @staticmethod
    def enclosing_block_of_kind(
        node: SemanticNode,
        kinds: FrozenSet[NodeKind],
    ) -> Optional[SemanticBlock]:
        """Walk parents until a SemanticBlock with kind in `kinds` is found."""

    @staticmethod
    def enclosing_definition_block(node: SemanticNode) -> Optional[DefinitionBlock]:
        """Walk parents until a DefinitionBlock (TestCase / Keyword) is found.
        Returns None if `node` is at file level (e.g. an import statement)."""

    @staticmethod
    def enclosing_section(node: SemanticNode) -> Optional[SemanticBlock]:
        """Walk parents until a section block (SETTING/TESTCASE/KEYWORD/...) is found."""

    @staticmethod
    def path_from_root(node: SemanticNode) -> List[SemanticNode]:
        """Return [root, ..., node] — useful for breadcrumbs / debugging."""
```

They're `@staticmethod` because the walk only needs `node.parent` — no
model-instance state. Callers use `SemanticModel.enclosing_definition_block(node)`
which keeps the namespace clean and conveys "this is a model-level utility,
not a node-level method".

These mirror the existing line-based accessors (`enclosing_definition(line)`,
`block_at(line)`) but take a node instead of a position — no need to round-trip
through `line_start`.

**Design tradeoffs**:

| Concern | Mitigation |
|---|---|
| **Cycles in `__repr__` / `__eq__`** | `field(repr=False, compare=False)` excludes parent from both. |
| **Pickle bloat** | Python's pickle handles cycles via the memo table — no extra code. Pickle gets ~10–20 % bigger because every node now references its parent (already serialized via the tree path). Acceptable; can add `__getstate__` / `__setstate__` on `SemanticNode` to drop and re-derive parents on unpickle if it ever bites. |
| **Mutation drift** | Model is immutable after `build_index()`; parent is set once during analysis and never updated. |
| **Memory** | One `Optional[SemanticNode]` per node — ~8 B per slot on CPython. For a 10K-node file that's ~80 KB. Negligible vs. the rest of the model. |
| **Test snapshots** | `repr=False` keeps YAML / regtest dumps clean — parent doesn't appear in serialized output. |

**Out of scope (for now)**: `SemanticToken` parents. Tokens have `sub_tokens`
that point downward, but no back-pointer to the parent token or owning statement.
`model.token_path_at(line, col)` covers the click-to-path case. Adding token-level
parent pointers should wait until a Tier 2/3 feature actually needs it — the
indirection through `token_path_at` is fine for now and avoids paying the memory
cost (~5–10× more tokens than nodes per file) prematurely.

```python
@dataclass(slots=True)
class SemanticModel:
    """Pre-computed semantic tree for a Robot Framework file.

    Built by SemanticAnalyzer during analysis.
    Dual representation:
    - Tree structure (`root`) mirrors the document hierarchy for structural
      queries (outline, folding, breadcrumbs, scoping).
    - Flat list (`statements`) provides O(1) indexed access via `statement_at()`.

    Optimized for queries: statement_at(), token_at(), find_variable(),
    block_at(), enclosing_definition(), and node-based parent walks
    (enclosing_definition_block, enclosing_block_of_kind, enclosing_section,
    path_from_root).

    Replaces ScopeTree by integrating variable scope tracking:
    - File-level variables are in `file_scope` (VariableScope)
    - Block-local variables are in each `DefinitionBlock.local_variables`
    - `find_variable(name, line)` provides position-aware lookup
    """

    # Tree structure: root is a SemanticBlock(kind=FILE) containing sections,
    # which contain definitions and statements. None before analysis completes.
    root: Optional[SemanticBlock] = None

    # Flat list of all statements for indexed access (document order).
    statements: List[SemanticStatement] = field(default_factory=list)

    # File-level variable scope (command-line, own, imported, builtin)
    # Replaces ScopeTree.file_scope
    file_scope: Optional[VariableScope] = None

    # Position indexes for O(1) lookups (built once by build_index())
    _line_index: Dict[int, SemanticStatement] = field(default_factory=dict, repr=False)
    _definition_index: List[DefinitionBlock] = field(default_factory=list, repr=False)
    _block_line_index: Dict[int, SemanticBlock] = field(default_factory=dict, repr=False)

    # Legacy: DefinitionStatements from flat list when no tree is built yet.
    _legacy_definition_index: List[DefinitionStatement] = field(default_factory=list, repr=False)

    def build_index(self) -> None:
        """Build all position indexes. Called once after construction by SemanticAnalyzer.

        After this call, the model is considered immutable — no further mutations
        to statements, tokens, or indexes should occur.

        When multiple statements cover the same line (e.g. a DefinitionStatement
        block and a body statement within it), the statement with the **smallest
        line range** wins. This ensures `statement_at()` returns the most specific
        statement for any given line.
        """
        self._line_index.clear()
        self._definition_index.clear()
        self._block_line_index.clear()
        self._legacy_definition_index.clear()

        # Index flat statement list
        for stmt in self.statements:
            stmt_size = stmt.line_end - stmt.line_start
            for line in range(stmt.line_start, stmt.line_end + 1):
                existing = self._line_index.get(line)
                if existing is None or stmt_size < (existing.line_end - existing.line_start):
                    self._line_index[line] = stmt
            # Legacy: track DefinitionStatements from flat list
            if isinstance(stmt, DefinitionStatement):
                self._legacy_definition_index.append(stmt)

        # Index tree structure (blocks)
        if self.root is not None:
            self._index_block(self.root)

    def _index_block(self, block: SemanticBlock) -> None:
        """Recursively index a block and its children."""
        block_size = block.line_end - block.line_start
        for line in range(block.line_start, block.line_end + 1):
            existing = self._block_line_index.get(line)
            if existing is None or block_size < (existing.line_end - existing.line_start):
                self._block_line_index[line] = block

        if isinstance(block, DefinitionBlock):
            self._definition_index.append(block)

        for child in block.body:
            if isinstance(child, SemanticBlock):
                self._index_block(child)

    def statement_at(self, line: int) -> Optional[SemanticStatement]:
        """Get the statement at a given line (1-indexed). O(1).

        Returns the most specific (smallest range) statement covering the line.
        For lines between statements (empty lines, comment-only lines), returns
        the definition header if the line falls within a test case or keyword block,
        or None if the line is outside any block.
        """
        stmt = self._line_index.get(line)
        if stmt is not None:
            return stmt

        defn = self.enclosing_definition(line)
        if defn is None:
            return None
        if isinstance(defn, DefinitionBlock):
            return defn.header
        # Legacy: DefinitionStatement is itself a statement
        return defn

    def token_at(self, line: int, col: int) -> Optional[SemanticToken]:
        """Get the deepest (most granular) token at a given position.

        Recursively descends into sub_tokens to find the most specific match.
        O(n) in tokens per statement, O(d) in sub_token depth.
        """
        stmt = self.statement_at(line)
        if stmt is None:
            return None
        for token in stmt.tokens:
            if token.line == line and token.col_offset <= col < token.col_offset + token.length:
                return self._deepest_token_at(token, line, col)
        return None

    def token_path_at(self, line: int, col: int) -> List[SemanticToken]:
        """Get the full path from outermost to innermost token at a position.

        Useful when consumers need parent context (e.g., hover on VARIABLE_BASE
        needs the parent VARIABLE token to call model.find_variable()).
        Returns empty list if no token matches.
        """
        stmt = self.statement_at(line)
        if stmt is None:
            return []
        for token in stmt.tokens:
            if token.line == line and token.col_offset <= col < token.col_offset + token.length:
                path = [token]
                self._collect_token_path(token, line, col, path)
                return path
        return []

    @staticmethod
    def _deepest_token_at(token: SemanticToken, line: int, col: int) -> SemanticToken:
        """Recursively find the deepest sub_token matching the position."""
        if token.sub_tokens:
            for sub in token.sub_tokens:
                if sub.line == line and sub.col_offset <= col < sub.col_offset + sub.length:
                    return SemanticModel._deepest_token_at(sub, line, col)
        return token

    @staticmethod
    def _collect_token_path(
        token: SemanticToken, line: int, col: int, path: List[SemanticToken],
    ) -> None:
        """Recursively collect the token path from parent to deepest child."""
        if token.sub_tokens:
            for sub in token.sub_tokens:
                if sub.line == line and sub.col_offset <= col < sub.col_offset + sub.length:
                    path.append(sub)
                    SemanticModel._collect_token_path(sub, line, col, path)
                    return

    def enclosing_definition(self, line: int) -> Optional["DefinitionBlock | DefinitionStatement"]:
        """Find the enclosing definition (Keyword/TestCase) containing the given line.

        Returns a DefinitionBlock if the tree is built, or falls back to
        DefinitionStatement from the flat list during the migration period.

        O(d) where d = number of definitions (typically 10–50 per file).
        """
        for defn in self._definition_index:
            if defn.line_start <= line <= defn.line_end:
                return defn
        # Legacy fallback: DefinitionStatement from flat list
        for defn_stmt in self._legacy_definition_index:
            if defn_stmt.line_start <= line <= defn_stmt.line_end:
                return defn_stmt
        return None

    def block_at(self, line: int) -> Optional[SemanticBlock]:
        """Get the most specific (smallest range) block at a given line. O(1)."""
        return self._block_line_index.get(line)

    # --- Node-based parent walks (use SemanticNode.parent back-pointer) ---

    @staticmethod
    def enclosing_block_of_kind(
        node: SemanticNode,
        kinds: frozenset[NodeKind],
    ) -> Optional[SemanticBlock]:
        """Walk parent chain from `node` upward; return the first SemanticBlock
        whose kind is in `kinds`, or None if no match before the root.

        Use this for control-flow / section lookups when you already have a
        node (e.g. from `statement_at`) and don't want to round-trip through
        a line-based query.
        """
        current = node.parent
        while current is not None:
            if isinstance(current, SemanticBlock) and current.kind in kinds:
                return current
            current = current.parent
        return None

    @staticmethod
    def enclosing_definition_block(node: SemanticNode) -> Optional[DefinitionBlock]:
        """Walk parent chain; return the enclosing DefinitionBlock (TestCase /
        Keyword) or None if `node` is at file level (e.g. an import statement).

        Cheaper than `enclosing_definition(line)` when you already have the node:
        no line-range scan, just parent pointer hops.
        """
        current = node.parent
        while current is not None:
            if isinstance(current, DefinitionBlock):
                return current
            current = current.parent
        return None

    @staticmethod
    def enclosing_section(node: SemanticNode) -> Optional[SemanticBlock]:
        """Walk parent chain; return the enclosing section block
        (SETTING_SECTION / TESTCASE_SECTION / KEYWORD_SECTION / VARIABLE_SECTION /
        COMMENT_SECTION / INVALID_SECTION), or None if outside any section."""
        return SemanticModel.enclosing_block_of_kind(node, _SECTION_KINDS)

    @staticmethod
    def path_from_root(node: SemanticNode) -> List[SemanticNode]:
        """Return the chain `[root, ..., node]` by walking parents.

        Useful for breadcrumb UI, debugging, and tests that need to assert
        structural placement without depending on line ranges.
        """
        chain: List[SemanticNode] = [node]
        current = node.parent
        while current is not None:
            chain.append(current)
            current = current.parent
        chain.reverse()
        return chain

    def find_variable(
        self, name: str, line: int,
        skip_commandline_variables: bool = False,
        skip_local_variables: bool = False,
    ) -> Optional[VariableDefinition]:
        """Position-aware variable lookup. Replaces ScopeTree.find_variable().

        Use this for VARIABLE *reference* tokens (TokenKind.VARIABLE) to find
        the VariableDefinition they refer to. NOT needed for VARIABLE_NAME tokens
        (definitions) — those create the VariableDefinition and are accessible
        via DefinitionBlock.local_variables or file_scope directly.

        Handles Extended Variable Syntax and Index Access automatically:
        - ``${obj.attr}`` → strips ``.attr`` → looks up ``${obj}``
        - ``${var}[0]`` → strips ``[0]`` → looks up ``${var}``
        - ``${SPACE * 5}`` → strips `` * 5`` → looks up ``${SPACE}``
        - ``${{expr}}`` → inline Python expression, no variable lookup

        Search order:
        1. Block-local variables (visible_from_line <= line) in enclosing definition
        2. File-scope variables (command-line, own, imported, builtin)
        """
        # Strip extended syntax / index access to get the base variable name
        base_name = self._normalize_variable_name(name)
        if base_name is None:
            return None  # e.g. inline Python ${{...}}

        if not skip_local_variables:
            definition = self.enclosing_definition(line)
            if definition is not None:
                # Search block-local variables (reverse order → latest definition wins)
                for var_def, visible_from in reversed(definition.local_variables):
                    if visible_from <= line and var_def.matcher.match(base_name):
                        return var_def

        if self.file_scope is not None:
            return self.file_scope.find(
                base_name, skip_commandline=skip_commandline_variables
            )

        return None

    @staticmethod
    def _normalize_variable_name(name: str) -> Optional[str]:
        """Strip Extended Syntax, Index Access, and Expression syntax
        to recover the base variable name for lookup.

        Returns None for inline Python expressions (``${{...}}``).
        """
        if not name:
            return None

        # Inline Python expression — no variable to look up
        if name.startswith("${{") and name.endswith("}}"):
            return None

        # Strip index access: ${var}[0][key] → ${var}
        base = name
        while base.endswith("]"):
            bracket_start = base.rfind("[")
            if bracket_start < 0:
                break
            base = base[:bracket_start]

        # Strip extended syntax inside braces: ${obj.attr} → ${obj}
        # Extended syntax starts after the variable base name and includes
        # dots, arithmetic, slicing, etc.
        if base.startswith(("${", "@{", "&{", "%{")):
            inner = base[2:-1]  # strip ${...} → inner content
            # Find extended syntax: first occurrence of '.', '[', or ' '
            # after the base name (RF uses these as extended syntax markers)
            for i, ch in enumerate(inner):
                if ch in ".[ ":
                    prefix = base[:2]  # e.g. "${"
                    return f"{prefix}{inner[:i]}}}"
        return base

    def get_variables_at(
        self, line: int, skip_commandline_variables: bool = False,
    ) -> Dict[VariableMatcher, VariableDefinition]:
        """Get all available variables at a position. Replaces ScopeTree.get_variable_matchers()."""
        result: Dict[VariableMatcher, VariableDefinition] = {}

        # File-scope variables first (lower precedence)
        if self.file_scope is not None:
            for var_def in self.file_scope.iter_all(
                skip_commandline=skip_commandline_variables
            ):
                result[var_def.matcher] = var_def

        # Block-local variables override (higher precedence)
        definition = self.enclosing_definition(line)
        if definition is not None:
            for var_def, visible_from in definition.local_variables:
                if visible_from <= line:
                    result[var_def.matcher] = var_def

        return result
```

#### Example: How a Complex Line Looks in the Model

Robot Framework source:
```robot
*** Test Cases ***
My Test
    [Setup]    Given BuiltIn.Log    ${message}    level=INFO
    Run Keyword If    ${condition}    My KW    arg1    ELSE    Other KW    arg2
```

Semantic Model tree:
```python
SemanticModel(statements=[
    # [Setup]    Given BuiltIn.Log    ${message}    level=INFO
    KeywordCallStatement(
        kind=NodeKind.SETUP,
        keyword_doc=<KeywordDoc for Log>,
        lib_entry=<BuiltInEntry>,
        tokens=[
            SemanticToken(kind=TokenKind.BDD_PREFIX, value="Given", line=3, col_offset=15, length=5),
            SemanticToken(kind=TokenKind.NAMESPACE, value="BuiltIn", line=3, col_offset=21, length=7),
            SemanticToken(kind=TokenKind.SEPARATOR, value=".", line=3, col_offset=28, length=1),
            SemanticToken(kind=TokenKind.KEYWORD, value="Log", line=3, col_offset=29, length=3),
            SemanticToken(kind=TokenKind.ARGUMENT, value="${message}", line=3, col_offset=36, length=10,
                          sub_tokens=[
                              SemanticToken(kind=TokenKind.VARIABLE, value="${message}",
                                            sub_tokens=[
                                                SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$", ...),
                                                SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{", ...),
                                                SemanticToken(kind=TokenKind.VARIABLE_BASE, value="message", ...),
                                                SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}", ...),
                                            ]),
                          ]),
            SemanticToken(kind=TokenKind.NAMED_ARGUMENT_NAME, value="level", line=3, ...),
            SemanticToken(kind=TokenKind.NAMED_ARGUMENT_VALUE, value="INFO", line=3, ...),
        ],
    ),

    # Run Keyword If    ${condition}    My KW    arg1    ELSE    Other KW    arg2
    # The analyzer populates the full inner_calls structure shown below —
    # KEYWORD (with BDD/Namespace splits) and ARGUMENT (with named-arg and
    # variable sub-tokens) tokens on each inner call.
    RunKeywordCallStatement(
        kind=NodeKind.KEYWORD_CALL,
        keyword_doc=<KeywordDoc for Run Keyword If>,
        tokens=[
            SemanticToken(kind=TokenKind.KEYWORD, value="Run Keyword If", ...),
            SemanticToken(kind=TokenKind.CONDITION, value="${condition}", ...,
                          sub_tokens=[
                              SemanticToken(kind=TokenKind.VARIABLE, value="${condition}",
                                            sub_tokens=[
                                                SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$", ...),
                                                SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{", ...),
                                                SemanticToken(kind=TokenKind.VARIABLE_BASE, value="condition", ...),
                                                SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}", ...),
                                            ]),
                          ]),
            SemanticToken(kind=TokenKind.CONTROL_FLOW, value="ELSE", ...),
        ],
        inner_calls=[
            KeywordCallStatement(
                kind=NodeKind.KEYWORD_CALL,
                keyword_doc=<KeywordDoc for My KW>,
                tokens=[
                    SemanticToken(kind=TokenKind.KEYWORD, value="My KW", ...),
                    SemanticToken(kind=TokenKind.ARGUMENT, value="arg1", ...),
                ],
            ),
            KeywordCallStatement(
                kind=NodeKind.KEYWORD_CALL,
                keyword_doc=<KeywordDoc for Other KW>,
                tokens=[
                    SemanticToken(kind=TokenKind.KEYWORD, value="Other KW", ...),
                    SemanticToken(kind=TokenKind.ARGUMENT, value="arg2", ...),
                ],
            ),
        ],
    ),
])
```

#### Example: Statement Subclasses with Type-Specific Properties

```robot
*** Test Cases ***
Process Data
    [Tags]    smoke    regression
    VAR    ${result}    initial    scope=SUITE
    FOR    ${item}    IN ZIP    ${list_a}    ${list_b}    mode=STRICT
        WHILE    ${item} > 0    limit=10    on_limit=PASS
            ${status}=    Process Item    ${item}
        END
    END
    TRY
        Validate Result    ${result}
    EXCEPT    ValueError    TypeError    type=GLOB    AS    ${err}
        Log    Error: ${err}
    END
    IF    ${status}    RETURN    ${result}
```

```python
# [Tags]    smoke    regression
SettingStatement(
    kind=NodeKind.SETTING,
    setting_name="Tags",
    tag_values=["smoke", "regression"],
    tokens=[...],
)

# VAR    ${result}    initial    scope=SUITE
VarStatement(
    kind=NodeKind.VARIABLE_DEF,
    variable_name=SemanticToken(kind=TokenKind.VARIABLE_NAME, value="${result}", ...),
    scope=VarScope.SUITE,
    separator=None,
    values=[SemanticToken(kind=TokenKind.ARGUMENT, value="initial", ...)],
    tokens=[...],
)

# FOR    ${item}    IN ZIP    ${list_a}    ${list_b}    mode=STRICT
ForStatement(
    kind=NodeKind.FOR_HEADER,
    flavor=ForFlavor.IN_ZIP,
    loop_variables=[
        SemanticToken(kind=TokenKind.VARIABLE_NAME, value="${item}", ...),
    ],
    mode=ForZipMode.STRICT,
    fill=None, start=None,
    tokens=[...],
)

# WHILE    ${item} > 0    limit=10    on_limit=PASS
WhileStatement(
    kind=NodeKind.WHILE_HEADER,
    condition="${item} > 0",
    limit="10",
    on_limit=OnLimitAction.PASS,
    on_limit_message=None,
    tokens=[...],
)

# ${status}=    Process Item    ${item}
KeywordCallStatement(
    kind=NodeKind.KEYWORD_CALL,
    keyword_doc=<KeywordDoc for Process Item>,
    assign_variables=[
        SemanticToken(kind=TokenKind.VARIABLE_NAME, value="${status}", ...),
    ],
    tokens=[...],
)

# EXCEPT    ValueError    TypeError    type=GLOB    AS    ${err}
ExceptStatement(
    kind=NodeKind.EXCEPT_HEADER,
    patterns=["ValueError", "TypeError"],
    pattern_type="GLOB",
    as_variable=SemanticToken(kind=TokenKind.VARIABLE_NAME, value="${err}", ...),
    tokens=[...],
)

# IF    ${status}    RETURN    ${result}
# (IF header)
IfStatement(
    kind=NodeKind.IF_HEADER,
    condition="${status}",
    assign_variable=None,
    tokens=[...],
)
# (RETURN inside IF — caught by the generic visit_Statement() fallback)
SemanticStatement(
    kind=NodeKind.RETURN_STATEMENT,
    tokens=[
        SemanticToken(kind=TokenKind.CONTROL_FLOW, value="RETURN", ...),
        SemanticToken(kind=TokenKind.ARGUMENT, value="${result}", ...,
                      sub_tokens=[
                          SemanticToken(kind=TokenKind.VARIABLE, value="${result}", ...,
                                        sub_tokens=[
                                            SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$", ...),
                                            SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{", ...),
                                            SemanticToken(kind=TokenKind.VARIABLE_BASE, value="result", ...),
                                            SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}", ...),
                                        ]),
                      ]),
    ],
)
```

### How the Model Is Built

The `SemanticAnalyzer` is an **independent class** that inherits **only** from Robot
Framework's `robot.utils.visitor.Visitor` base class — it does **not** inherit from or
extend the `NamespaceAnalyzer`. The existing `NamespaceAnalyzer` serves as **template**
for the implementation — its structure, visitor methods, and resolution logic are used
as reference, but the `SemanticAnalyzer` is written as a standalone class with no class
hierarchy relationship to the `NamespaceAnalyzer`.

It has the **same constructor**, **same `resolve()` method**, and **same `run()` method**
as the `NamespaceAnalyzer` (see *Interface Contract* section above for full signatures).
The only output difference: `AnalyzerResult` includes the additional `semantic_model` field.

The Visitor pattern dispatches each AST node to the matching `visit_*()` method
(e.g., `visit_KeywordCall`, `visit_ForHeader`, `visit_Fixture`). Nodes without a
specific visitor method fall through to `generic_visit()` for recursive traversal.
Model building is integrated into the existing visitor methods — the same AST walk that
resolves keywords, collects references, and emits diagnostics also constructs the
`SemanticModel`. No additional AST walk is needed.

#### Keyword Calls

In `_analyze_keyword_call()`, after the keyword is resolved:

```python
# _analyze_keyword_call() already computes all of this:
#   result (KeywordDoc), bdd_prefix, kw_namespace, lib_entry, argument_tokens

tokens = []

# BDD prefix
if bdd_prefix:
    tokens.append(SemanticToken(
        kind=TokenKind.BDD_PREFIX, value=bdd_prefix.strip(),
        line=..., col_offset=..., length=len(bdd_prefix) - 1,
    ))

# Namespace qualifier
if kw_namespace and lib_entry:
    tokens.append(SemanticToken(
        kind=TokenKind.NAMESPACE, value=kw_namespace,
        line=..., col_offset=..., length=len(kw_namespace),
    ))
    tokens.append(SemanticToken(kind=TokenKind.SEPARATOR, value=".", ...))
    # lib_entry is set on the statement, not on the token
    self._current_statement.lib_entry = lib_entry

# Keyword name
# keyword_doc is always on the statement, never on the token
tokens.append(SemanticToken(
    kind=TokenKind.KEYWORD,
    value=keyword_name, ...
))

# Arguments (with variable sub-tokens)
for arg_token in argument_tokens:
    tokens.append(self._build_argument_token(arg_token))

self._current_statement.tokens.extend(tokens)
```

#### Variable References

In `_handle_find_variable_result()`, variables are added as sub-tokens
of their parent ARGUMENT token:

```python
# Variables are sub-tokens because they're embedded in larger tokens
# e.g. "Hello ${name} world" → ARGUMENT with sub_tokens
# TokenKind encodes resolution status: VARIABLE (resolved) vs VARIABLE_NOT_FOUND
sub_token = SemanticToken(
    kind=TokenKind.VARIABLE if var_def else TokenKind.VARIABLE_NOT_FOUND,
    value=var_token.value,
    ...
)
```

#### Variable Resolution Coverage

The `NamespaceAnalyzer` already resolves **all** variable variations that Robot Framework
supports. The Semantic Model inherits this completeness without additional work — each
resolved variable becomes a `SemanticToken` sub-token with `TokenKind.VARIABLE` (resolved)
or `TokenKind.VARIABLE_NOT_FOUND` (unresolved). The `VariableDefinition` is not stored on
the token — consumers recover it on demand via `model.find_variable(token.value, token.line)`.

| Variable Variation | Example | Resolution Mechanism | Model Representation |
|--------------------|---------|----------------------|----------------------|
| Scalar | `${name}` | `_iter_variables_from_token()` → `_find_variable()` | `SemanticToken(VARIABLE)` |
| List | `@{items}` | Same as scalar, different identifier prefix | `SemanticToken(VARIABLE)` |
| Dict | `&{config}` | Same as scalar, different identifier prefix | `SemanticToken(VARIABLE)` |
| Environment | `%{HOME}` | `_find_variable()` checks env scope | `SemanticToken(VARIABLE)` |
| Indexed access | `${var}[0]` | `remove_index_from_variable_token()` strips `[0]` before resolution | `SemanticToken(VARIABLE)` for base, index is text |
| Dict key access | `${var}[key]` | Same as indexed — `remove_index_from_variable_token()` | Same as indexed |
| Nested | `${${inner}}` | Recursive handling in `_iter_variables_token()` | Nested `sub_tokens`: outer VARIABLE contains inner VARIABLE as sub_token |
| Inline Python | `${{len(items)}}` | `_iter_expression_variables_from_token()` using Python `tokenizer` | `SemanticToken(VARIABLE)` — expression body as value |
| Type-hinted (RF 7.0+) | `${count: int}` | `VariableDefinition.value_type` stores type info | `SemanticToken(VARIABLE)` — type info via `find_variable()` |
| Numbered args | `${1}`, `${2}` | `NumberedVariableDefinition` type | `SemanticToken(VARIABLE)` |

**Resolution scope chain** (checked in order by `_find_variable()`):
1. Block-local variables (FOR loop variables, inline assignments)
2. Command-line variables (`--variable`, `--variablefile`)
3. Own variables (Variables section, VAR statements)
4. Imported variables (resource files, variable files)
5. Built-in variables (`${CURDIR}`, `${EMPTY}`, `${TRUE}`, etc.)

**Mapping to `SemanticModel.find_variable()`:** Step 1 maps to
`enclosing_definition().local_variables`. Steps 2–5 are handled internally by
`file_scope.find()` (which is `VariableScope.find()` — it chains through command-line,
own, imported, and built-in scopes in that order). The two-level API
(`local_variables` + `file_scope`) thus covers all 5 resolution steps.

Each `VariableDefinition` carries:
- `name` — the full variable name including decoration
- `type` — `VariableDefinitionType` enum (VARIABLE, LOCAL_VARIABLE, ARGUMENT, GLOBAL_VARIABLE, etc.)
- `value_type` — RF 7.0+ type hint (e.g., `"int"`, `"list[str]"`)
- `matcher` — `VariableMatcher` for case/space-insensitive matching
- Source location info for goto-definition

#### Nested Variable Resolution (Static Name Resolution) ✅

Nested variables like `${cfg_${env}}` contain inner variable references inside the
outer variable's name. Robot Framework resolves these at runtime by evaluating the inner
variable first. The SemanticAnalyzer (and the NamespaceAnalyzer, for parity) now attempt
**static resolution** of nested variable names at analysis time — when the inner variable's
value is known at compile time, the outer variable can be resolved too.

##### Overview

When a variable reference contains nested variables (e.g., `${INVALID VAR ${a}}`), the
analyzer:
1. Resolves each inner variable reference (e.g., `${a}`) independently — these get
   hover, go-to-definition, and diagnostics as normal variable references
2. Attempts to statically resolve the outer variable's full name by substituting inner
   variables with their known values
3. If resolution succeeds → creates/finds the outer variable definition with the resolved name
4. If resolution fails (inner variable not found) → emits ERROR diagnostic
5. If resolution is not statically possible (value unknown at analysis time) → emits HINT

##### Key Methods (Both Analyzers)

Both `SemanticAnalyzer` (`analyzer.py`) and `NamespaceAnalyzer` (`namespace_analyzer.py`)
implement the same nested variable resolution pipeline for output parity:

| Method | Location | Purpose |
|--------|----------|---------|
| `_try_resolve_nested_variable_base(identifier, base, name_token)` | Both analyzers | Entry point: attempts static resolution of a nested variable name. Returns `str` (resolved name), `False` (not resolvable), or `None` (error) |
| `_resolve_variable_to_string(var_match)` | Both analyzers | Resolves a single `${}` variable to its string value by looking up the definition's default value |
| `_resolve_list_var_to_string(var_match)` | Both analyzers | Resolves `@{list}` to its joined string representation |
| `_resolve_dict_var_to_string(var_match)` | Both analyzers | Resolves `&{dict}` to its joined string representation |
| `_try_resolve_number_literal(value)` | Both analyzers | Handles RF number literal prefixes (`0b`, `0o`, `0x`) for numeric variable values |
| `_is_extended_with_known_base(var_ref)` | Both analyzers | Checks if a variable reference uses extended syntax (`.attr`, ` * 5`) with a known base variable — used to skip nested resolution for extended expressions |
| `normalize_variable_lookup_name(token_value)` | `variable_tokenizer.py` | Strips extended syntax from a variable name to get the base lookup name (e.g., `${obj.attr}` → `obj`) |

##### Resolution Pipeline

```
Variable Reference: ${INVALID VAR ${a}}
                                   ↑ inner var
    ↓
Step 1: Parse inner variables → find ${a} → resolve to VariableDefinition
    ↓
Step 2: _try_resolve_nested_variable_base("$", "INVALID VAR ${a}", token)
    ↓
Step 3: For each inner variable match in base:
    ├── _resolve_variable_to_string(match) → e.g., "foo"
    ├── Replace match text with resolved value → "INVALID VAR foo"
    └── If any resolution fails → return None (error) or False (not resolvable)
    ↓
Step 4: Resolved name = "${INVALID VAR foo}" → look up in variable scope
```

##### Definition-Site Behavior (Option A)

At all 6 definition call sites (3 per analyzer), when `_try_resolve_nested_variable_base`
returns `False` (not statically resolvable), the analyzer performs an **early return** —
no `VariableDefinition` is created for that variable. This prevents phantom variable
definitions with unresolved names from polluting the scope.

##### Diagnostics

Three new error codes support nested variable resolution:

| Error Code | Severity | Context | Condition |
|------------|----------|---------|-----------|
| `VARIABLE_NAME_NOT_RESOLVABLE` | ERROR | Definition sites | Inner variable in nested name not found in scope |
| `VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE` | HINT | Definition sites | Inner variable exists but value cannot be determined at analysis time |
| `VARIABLE_REFERENCE_NOT_STATICALLY_RESOLVABLE` | HINT | Usage/reference sites (Call Site 4) | Variable reference contains nested vars that can't be resolved |

##### Guards for Special Cases

Two guards prevent false positives:

1. **Extended Expression Guard** (namespace_analyzer, Call Site 4): When processing a
   variable reference like `${A + '${B}'}`, the `ModelHelper.MATCH_EXTENDED` regex detects
   that the extension starts with a non-variable character. The `is_pure_nested` flag
   prevents the analyzer from treating this as a nested variable — it falls through to
   the existing `ExtendedFinder` block for extended expression evaluation.

2. **Inline Python Guard** (semantic_analyzer, Call Site 4): Variables like `${{${n} - 1}}`
   where `${n}` appears inside inline Python `${{...}}` are not subject to nested variable
   resolution. The guard checks `occurrence.value.startswith("${{") and occurrence.value.endswith("}}")`.

##### Inner Variable References

Inner variables in nested constructs get **full first-class treatment**: hover shows their
definition, go-to-definition navigates to the defining location, and diagnostics are emitted
if they're undefined. For example, in `${INVALID VAR ${a}}`, hovering over `${a}` shows
the definition of variable `a`, not the outer unresolved composite name.

#### Variable Architecture: Single Parse, Multiple Consumers (Phase 1.1 ✅)

Variable syntax is parsed **once** per RF token into a dedicated IR
(`VariableOccurrence` in [variable_tokenizer.py](../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/variable_tokenizer.py)),
then consumed by two paths:

```text
RF token
    ↓
iter_variable_occurrences_from_token(...)
    ↓
VariableOccurrence (carries lookup_name, identifier, base, type hint, pattern,
                    extended-syntax part, index segments, nested occurrences,
                    inline-Python `$var` refs, semantic_sub_tokens)
    ├── analyzer-side: resolves against scope → diagnostics + references
    └── renderer-side: returns the prebuilt `semantic_sub_tokens` for the model
```

`SemanticToken` deliberately stays a *presentation* model, not the parser's
source of truth — the IR carries semantic state (parse errors, assign-target
vs. reference, etc.) that doesn't belong on a render-time token. Both
consumers read the same parse result, so variable text is never split twice.

#### Sub-Token Decomposition (Granular Variable Structure)

**Design Decision:** Sub-tokens are decomposed to **maximum granularity**. Every structural
part of a variable is represented as its own `SemanticToken` — prefixes, braces, name body,
type hints, index brackets, extended syntax parts, Python expressions, and text fragments
between variables. This enables:

- **Precise syntax highlighting**: Different colors for `$`, `{`, name, type hint, `}`
- **Position-accurate hover**: Hovering on the type hint shows type info, on the name shows definition
- **Targeted goto-definition**: Click on `name` in `${name: int}` → goes to definition
- **Intelligent completion**: Inside `${...}` offers variable names, after `: ` offers types
- **Precise error ranges**: Error on just the unresolved name, not the entire `${...}`

> **Open question — granularity audit (Tier 2/3 follow-up):** the current
> spec defines 28+ variable-related `TokenKind` values. Tier 1 Semantic
> Tokens collapses many of them to the same LSP token type
> (`VARIABLE_PREFIX`, `VARIABLE_OPEN_BRACE`, `VARIABLE_INDEX_OPEN` →
> all `VARIABLE_BEGIN`). Whether the finer split actually pays off should
> be re-evaluated once Tier 2 (Inlay Hints, Signature Help, Doc Actions)
> and Tier 3 (Hover, Rename) consume `token_path_at()` — those are the
> features that benefit from finer leaves. If a kind is never branched
> on by any consumer, it should be merged.

**Key Principles:**
1. Every character in a variable expression belongs to exactly one sub_token
2. Sub_tokens can nest recursively (variables inside variables, variables in index access)
3. The parent `VARIABLE` / `VARIABLE_NOT_FOUND` token's `TokenKind` encodes resolution status —
   sub-tokens provide structural decomposition. To get the `VariableDefinition`, use
   `model.find_variable(token.value, token.line)`
4. `TEXT_FRAGMENT` captures literal text between variables in compound tokens (ARGUMENT, CONDITION, etc.)
5. For lookup, `token_path_at()` returns the full chain from outermost to innermost —
   consumers can access parent context (e.g., `TokenKind`) and leaf detail (e.g., `VARIABLE_BASE`)

##### Decomposition Rules

| Variable Form | Parent TokenKind | Sub-Token Sequence |
|---------------|------------------|-------------------|
| `${name}` | VARIABLE | PREFIX `$` → OPEN_BRACE `{` → BASE `name` → CLOSE_BRACE `}` |
| `@{items}` | VARIABLE | PREFIX `@` → OPEN_BRACE `{` → BASE `items` → CLOSE_BRACE `}` |
| `&{config}` | VARIABLE | PREFIX `&` → OPEN_BRACE `{` → BASE `config` → CLOSE_BRACE `}` |
| `%{HOME}` | VARIABLE | PREFIX `%` → OPEN_BRACE `{` → BASE `HOME` → CLOSE_BRACE `}` |
| `${age: int}` | VARIABLE | PREFIX → OPEN_BRACE → BASE `age` → TYPE_SEP `: ` → TYPE_HINT `int` → CLOSE_BRACE |
| `${name: Secret}` | VARIABLE | PREFIX → OPEN_BRACE → BASE `name` → TYPE_SEP → TYPE_HINT `Secret` → CLOSE_BRACE |
| `%{NAME=default}` | VARIABLE | PREFIX `%` → OPEN_BRACE → BASE `NAME` → DEFAULT_SEP `=` → DEFAULT_VALUE `default` → CLOSE_BRACE |
| `${obj.attr}` | VARIABLE | PREFIX → OPEN_BRACE → BASE `obj` → EXTENDED `.attr` → CLOSE_BRACE |
| `${SPACE * 5}` | VARIABLE | PREFIX → OPEN_BRACE → BASE `SPACE` → EXTENDED ` * 5` → CLOSE_BRACE |
| `${${inner}}` | VARIABLE | PREFIX `$` → OPEN_BRACE → nested VARIABLE `${inner}` → CLOSE_BRACE |
| `${cfg_${env}}` | VARIABLE | PREFIX `$` → OPEN_BRACE → TEXT_FRAGMENT `cfg_` → nested VARIABLE `${env}` → CLOSE_BRACE |
| `${{expr}}` | VARIABLE | PREFIX `$` → EXPR_OPEN `{{` → PYTHON_EXPRESSION `expr` → EXPR_CLOSE `}}` |
| `${arg:\d+}` | VARIABLE | PREFIX → OPEN_BRACE → BASE `arg` → PATTERN_SEP `:` → PATTERN `\d+` → CLOSE_BRACE |
| `${name: str:\w+}` | VARIABLE | PREFIX → OPEN_BRACE → BASE `name` → TYPE_SEP `: ` → TYPE_HINT `str` → PATTERN_SEP `:` → PATTERN `\w+` → CLOSE_BRACE |
| `${result}=` | VARIABLE | PREFIX → OPEN_BRACE → BASE `result` → CLOSE_BRACE → ASSIGN_MARK `=` |

**Index access** is represented as sibling tokens after the VARIABLE in the parent's sub_token list
(matching the existing `remove_index_from_variable_token()` split):

| Index Form | Sub-Tokens |
|------------|-----------|
| `${var}[0]` | VARIABLE `${var}` (with sub-tokens), VARIABLE_INDEX `[0]` (with INDEX_OPEN `[` → INDEX_CONTENT `0` → INDEX_CLOSE `]`) |
| `${var}[key]` | VARIABLE, VARIABLE_INDEX `[key]` |
| `${var}[1:]` | VARIABLE, VARIABLE_INDEX `[1:]` |
| `${var}[0][key]` | VARIABLE, VARIABLE_INDEX `[0]`, VARIABLE_INDEX `[key]` |
| `${var}[${idx}]` | VARIABLE, VARIABLE_INDEX (INDEX_OPEN → nested VARIABLE `${idx}` → INDEX_CLOSE) |

##### Comprehensive Examples

**1. Simple scalar variable in argument:**

Robot Framework: `Log    Hello ${name}, you are ${age: int} years old`

```python
SemanticToken(
    kind=TokenKind.ARGUMENT,
    value="Hello ${name}, you are ${age: int} years old",
    sub_tokens=[
        SemanticToken(kind=TokenKind.TEXT_FRAGMENT, value="Hello ",
                      line=1, col_offset=7, length=6),
        SemanticToken(kind=TokenKind.VARIABLE, value="${name}",
                      line=1, col_offset=13, length=7,
                      sub_tokens=[
                          SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$",
                                        line=1, col_offset=13, length=1),
                          SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{",
                                        line=1, col_offset=14, length=1),
                          SemanticToken(kind=TokenKind.VARIABLE_BASE, value="name",
                                        line=1, col_offset=15, length=4),
                          SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}",
                                        line=1, col_offset=19, length=1),
                      ]),
        SemanticToken(kind=TokenKind.TEXT_FRAGMENT, value=", you are ",
                      line=1, col_offset=20, length=10),
        SemanticToken(kind=TokenKind.VARIABLE, value="${age: int}",
                      line=1, col_offset=30, length=11,
                      sub_tokens=[
                          SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$",
                                        line=1, col_offset=30, length=1),
                          SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{",
                                        line=1, col_offset=31, length=1),
                          SemanticToken(kind=TokenKind.VARIABLE_BASE, value="age",
                                        line=1, col_offset=32, length=3),
                          SemanticToken(kind=TokenKind.VARIABLE_TYPE_SEPARATOR, value=": ",
                                        line=1, col_offset=35, length=2),
                          SemanticToken(kind=TokenKind.VARIABLE_TYPE_HINT, value="int",
                                        line=1, col_offset=37, length=3),
                          SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}",
                                        line=1, col_offset=40, length=1),
                      ]),
        SemanticToken(kind=TokenKind.TEXT_FRAGMENT, value=" years old",
                      line=1, col_offset=41, length=10),
    ]
)
```

**2. Nested variable:** `${config_${env}}`

```python
SemanticToken(
    kind=TokenKind.VARIABLE_NOT_FOUND,  # Cannot statically resolve — depends on ${env} value
    value="${config_${env}}",
    sub_tokens=[
        SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$",
                      line=1, col_offset=0, length=1),
        SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{",
                      line=1, col_offset=1, length=1),
        SemanticToken(kind=TokenKind.TEXT_FRAGMENT, value="config_",
                      line=1, col_offset=2, length=7),
        SemanticToken(kind=TokenKind.VARIABLE, value="${env}",
                      line=1, col_offset=9, length=6,
                      sub_tokens=[
                          SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$",
                                        line=1, col_offset=9, length=1),
                          SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{",
                                        line=1, col_offset=10, length=1),
                          SemanticToken(kind=TokenKind.VARIABLE_BASE, value="env",
                                        line=1, col_offset=11, length=3),
                          SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}",
                                        line=1, col_offset=14, length=1),
                      ]),
        SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}",
                      line=1, col_offset=15, length=1),
    ]
)
```

**3. Inline Python expression:** `${{os.path.join($base, "sub")}}`

```python
SemanticToken(
    kind=TokenKind.VARIABLE,
    value='${{os.path.join($base, "sub")}}',
    sub_tokens=[
        SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$",
                      line=1, col_offset=0, length=1),
        SemanticToken(kind=TokenKind.VARIABLE_EXPRESSION_OPEN, value="{{",
                      line=1, col_offset=1, length=2),
        SemanticToken(kind=TokenKind.PYTHON_EXPRESSION,
                      value='os.path.join($base, "sub")',
                      line=1, col_offset=3, length=26,
                      sub_tokens=[
                          # Python tokenizer extracts $-prefixed variable references
                          SemanticToken(kind=TokenKind.PYTHON_VARIABLE_REF, value="$base",
                                        line=1, col_offset=16, length=5),
                      ]),
        SemanticToken(kind=TokenKind.VARIABLE_EXPRESSION_CLOSE, value="}}",
                      line=1, col_offset=29, length=2),
    ]
)
```

**4. Extended variable syntax:** `${obj.attribute.method()}`

```python
SemanticToken(
    kind=TokenKind.VARIABLE,
    value="${obj.attribute.method()}",
    sub_tokens=[
        SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$",
                      line=1, col_offset=0, length=1),
        SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{",
                      line=1, col_offset=1, length=1),
        SemanticToken(kind=TokenKind.VARIABLE_BASE, value="obj",
                      line=1, col_offset=2, length=3),
        SemanticToken(kind=TokenKind.VARIABLE_EXTENDED, value=".attribute.method()",
                      line=1, col_offset=5, length=19),
        SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}",
                      line=1, col_offset=24, length=1),
    ]
)
```

**5. Index access with nested variable:** `${data}[${idx}][name]`

```python
# Parent ARGUMENT sub_tokens:
[
    SemanticToken(kind=TokenKind.VARIABLE, value="${data}",
                  sub_tokens=[
                      SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$", ...),
                      SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{", ...),
                      SemanticToken(kind=TokenKind.VARIABLE_BASE, value="data", ...),
                      SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}", ...),
                  ]),
    SemanticToken(kind=TokenKind.VARIABLE_INDEX, value="[${idx}]",
                  sub_tokens=[
                      SemanticToken(kind=TokenKind.VARIABLE_INDEX_OPEN, value="[", ...),
                      SemanticToken(kind=TokenKind.VARIABLE, value="${idx}",
                                    sub_tokens=[
                                        SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$", ...),
                                        SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{", ...),
                                        SemanticToken(kind=TokenKind.VARIABLE_BASE, value="idx", ...),
                                        SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}", ...),
                                    ]),
                      SemanticToken(kind=TokenKind.VARIABLE_INDEX_CLOSE, value="]", ...),
                  ]),
    SemanticToken(kind=TokenKind.VARIABLE_INDEX, value="[name]",
                  sub_tokens=[
                      SemanticToken(kind=TokenKind.VARIABLE_INDEX_OPEN, value="[", ...),
                      SemanticToken(kind=TokenKind.VARIABLE_INDEX_CONTENT, value="name", ...),
                      SemanticToken(kind=TokenKind.VARIABLE_INDEX_CLOSE, value="]", ...),
                  ]),
]
```

**6. Embedded argument with type and pattern:** `${count: int:\d+}`

```python
SemanticToken(
    kind=TokenKind.VARIABLE, value="${count: int:\\d+}",
    sub_tokens=[
        SemanticToken(kind=TokenKind.VARIABLE_PREFIX, value="$", ...),
        SemanticToken(kind=TokenKind.VARIABLE_OPEN_BRACE, value="{", ...),
        SemanticToken(kind=TokenKind.VARIABLE_BASE, value="count", ...),
        SemanticToken(kind=TokenKind.VARIABLE_TYPE_SEPARATOR, value=": ", ...),
        SemanticToken(kind=TokenKind.VARIABLE_TYPE_HINT, value="int", ...),
        SemanticToken(kind=TokenKind.VARIABLE_PATTERN_SEPARATOR, value=":", ...),
        SemanticToken(kind=TokenKind.VARIABLE_PATTERN, value="\\d+", ...),
        SemanticToken(kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}", ...),
    ]
)
```

Other forms — environment defaults `%{NAME=default}`, list/dict prefixes `@{}` `&{}`,
assign mark `${result}=`, expression syntax `${SPACE * 5}`, pure-variable arguments
without surrounding text — follow the same decomposition rules from the table above.

##### Implementation Notes

**Building sub-tokens from `VariableMatch`:**

The `VariableMatch` from RF's `search_variable()` provides all raw data needed:
- `identifier` → VARIABLE_PREFIX value
- `base` → content between braces (may need further parsing for type hint, extended syntax)
- `type` → VARIABLE_TYPE_HINT value (when `parse_type=True`, RF ≥ 7.3)
- `items` → tuple of index access strings
- `start` / `end` → positions for computing col_offsets

```python
def _build_variable_sub_tokens(
    self, match: VariableMatch, token: Token, var_def: Optional[VariableDefinition],
) -> List[SemanticToken]:
    """Decompose a VariableMatch into granular sub-tokens."""
    sub_tokens = []
    col = token.col_offset + match.start

    # 1. Prefix: $ @ & %
    sub_tokens.append(SemanticToken(
        kind=TokenKind.VARIABLE_PREFIX, value=match.identifier,
        line=token.lineno, col_offset=col, length=1))
    col += 1

    # 2. Check for inline Python (${{...}}) vs regular ({...})
    is_inline_python = match.base.startswith("{") and match.base.endswith("}")

    if is_inline_python:
        # {{ opening
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_EXPRESSION_OPEN, value="{{",
            line=token.lineno, col_offset=col, length=2))
        col += 2

        # Python expression body (strip outer { })
        expr_body = match.base[1:-1]
        expr_token = SemanticToken(
            kind=TokenKind.PYTHON_EXPRESSION, value=expr_body,
            line=token.lineno, col_offset=col, length=len(expr_body))

        # Find $var references inside the expression
        expr_sub_tokens = self._extract_python_variable_refs(expr_body, token.lineno, col)
        if expr_sub_tokens:
            expr_token.sub_tokens = expr_sub_tokens

        sub_tokens.append(expr_token)
        col += len(expr_body)

        # }} closing
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_EXPRESSION_CLOSE, value="}}",
            line=token.lineno, col_offset=col, length=2))
    else:
        # { opening
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_OPEN_BRACE, value="{",
            line=token.lineno, col_offset=col, length=1))
        col += 1

        # Parse the base content: name, type hint, extended syntax, etc.
        base = match.base
        self._decompose_variable_base(base, token.lineno, col, sub_tokens)
        col += len(base)

        # } closing
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_CLOSE_BRACE, value="}",
            line=token.lineno, col_offset=col, length=1))

    # 3. Index access (from match.items)
    # Position tracked after the closing brace
    col += 1
    for item in match.items:
        idx_token = self._build_index_sub_tokens(item, token.lineno, col)
        sub_tokens.append(idx_token)
        col += len(item) + 2  # +2 for [ and ]

    return sub_tokens
```

**Parsing the base content** (name, type hint, extended syntax, default value):

```python
def _decompose_variable_base(
    self, base: str, line: int, col: int, sub_tokens: List[SemanticToken],
) -> None:
    """Parse the content between { and } into sub-tokens."""

    # Check for nested variables first
    if contains_variable(base, "$@&%"):
        # Recursively tokenize — yields TEXT_FRAGMENT + nested VARIABLE tokens
        self._decompose_nested_base(base, line, col, sub_tokens)
        return

    # Check for type hint (RF 7.0+): "name: type" or "name: type:pattern"
    if ": " in base:
        name_part, _, rest = base.partition(": ")
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_BASE, value=name_part,
            line=line, col_offset=col, length=len(name_part)))
        col += len(name_part)
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_TYPE_SEPARATOR, value=": ",
            line=line, col_offset=col, length=2))
        col += 2
        # Check for pattern after type: "type:pattern"
        if ":" in rest:
            type_part, _, pattern_part = rest.partition(":")
            sub_tokens.append(SemanticToken(
                kind=TokenKind.VARIABLE_TYPE_HINT, value=type_part,
                line=line, col_offset=col, length=len(type_part)))
            col += len(type_part)
            sub_tokens.append(SemanticToken(
                kind=TokenKind.VARIABLE_PATTERN_SEPARATOR, value=":",
                line=line, col_offset=col, length=1))
            col += 1
            sub_tokens.append(SemanticToken(
                kind=TokenKind.VARIABLE_PATTERN, value=pattern_part,
                line=line, col_offset=col, length=len(pattern_part)))
        else:
            sub_tokens.append(SemanticToken(
                kind=TokenKind.VARIABLE_TYPE_HINT, value=rest,
                line=line, col_offset=col, length=len(rest)))
        return

    # Check for environment variable default: "NAME=default"
    if "=" in base:
        name_part, _, default_part = base.partition("=")
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_BASE, value=name_part,
            line=line, col_offset=col, length=len(name_part)))
        col += len(name_part)
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_DEFAULT_SEPARATOR, value="=",
            line=line, col_offset=col, length=1))
        col += 1
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_DEFAULT_VALUE, value=default_part,
            line=line, col_offset=col, length=len(default_part)))
        return

    # Check for extended variable syntax: "name.attr" or "name[key]" etc.
    ext_match = _MATCH_EXTENDED.match(base)  # local regex, NOT from ModelHelper
    if ext_match:
        name_part = ext_match.group(1)
        ext_part = ext_match.group(2)
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_BASE, value=name_part,
            line=line, col_offset=col, length=len(name_part)))
        col += len(name_part)
        sub_tokens.append(SemanticToken(
            kind=TokenKind.VARIABLE_EXTENDED, value=ext_part,
            line=line, col_offset=col, length=len(ext_part)))
        return

    # Simple variable name
    sub_tokens.append(SemanticToken(
        kind=TokenKind.VARIABLE_BASE, value=base,
        line=line, col_offset=col, length=len(base)))
```

**`token_path_at()` usage example** (hover on type hint):

```python
# User hovers at line 5, col 37 which is inside "int" in "${age: int}"
path = model.token_path_at(5, 37)
# path = [
#   SemanticToken(ARGUMENT, "Hello ${age: int}"),
#   SemanticToken(VARIABLE, "${age: int}", var_def=<VariableDef>),
#   SemanticToken(VARIABLE_TYPE_HINT, "int"),
# ]

# Hover provider can now:
# - See it's a VARIABLE_TYPE_HINT → show "Type conversion: int"
# - Access path[-2] for the parent VARIABLE token → model.find_variable(path[-2].value, path[-2].line)
# - Access path[-3] for the parent ARGUMENT context
```

#### Statement Lifecycle

The Visitor base class dispatches each RF AST node to the matching `visit_*()` method.
Each visitor creates the appropriate `SemanticStatement` subclass and sets it as the
current statement before delegating to analysis methods that populate the token list:

```python
# Visitor dispatches: ForHeader → visit_ForHeader, KeywordCall → visit_KeywordCall, etc.
# Nodes without a specific visit_*() fall through to generic_visit().
def visit_KeywordCall(self, node: KeywordCall) -> None:
    stmt = KeywordCallStatement(
        kind=NodeKind.KEYWORD_CALL,
        line_start=node.lineno, line_end=node.end_lineno,
    )
    self._current_statement = stmt

    # ... existing analysis (populates stmt.tokens via _analyze_keyword_call) ...

    stmt.keyword_doc = resolved_keyword_doc
    self._model.statements.append(stmt)

# Simple nodes without special fields use the base SemanticStatement via the
# generic visit_Statement() fallback. _node_kind_for_statement() picks the
# appropriate NodeKind from the AST node's type (END, BREAK, COMMENT, ELSE_HEADER,
# TRY_HEADER, ...). _build_tokens_from_node() then populates tokens via
# _RF_TOKEN_TO_TOKEN_KIND. There is no UNKNOWN fallback — every concrete RF
# Statement subclass maps to a dedicated NodeKind.
def visit_Statement(self, node: Statement) -> None:
    self._analyze_statement_variables(node)
    stmt = SemanticStatement(
        kind=self._node_kind_for_statement(node),
        line_start=node.lineno, line_end=node.end_lineno or node.lineno,
        tokens=self._build_tokens_from_node(node),
    )
    self._add_statement(stmt)
```

#### Invariants

These rules are **non-negotiable** — violations are bugs, not TODOs.

1. **Every `SemanticStatement` in `model.statements` MUST have a non-empty `tokens` list.**
   The only exception is `DefinitionStatement` for block containers (`TestCase`, `Keyword`)
   where the block-level statement spans the entire block and the name is on a separate
   `TestCaseName`/`KeywordName` node.

   **Rationale:** `token_at()` and `token_path_at()` search through `stmt.tokens` —
   a statement with `tokens=[]` is invisible to all position-based queries. LSP features
   that iterate tokens (semantic highlighting, hover, completion) will skip it entirely.
   The whole point of the SemanticModel is to provide pre-resolved token data. A statement
   without tokens is an empty shell that serves no purpose.

2. **Every visitor that creates a `SemanticStatement` is responsible for populating its `tokens`.**
   The analysis methods (`_analyze_keyword_call`, `_visit_settings_statement`, etc.) must
   append `SemanticToken` objects to `stmt.tokens` before the statement is added to the model.
   The generic `visit_Statement()` fallback handles this automatically via RF token mapping.
   Specialized visitors must do it explicitly.

3. **`SemanticToken` position fields (`line`, `col_offset`, `length`) MUST be accurate.**
   They are used for `token_at()` hit-testing. Incorrect positions cause hover/completion
   to miss or hit the wrong token.

4. **Variable sub-tokens MUST be built from the variable IR (`VariableOccurrence`),
   not by re-parsing the token text.** This is the single-parse pipeline invariant from
   Phase 1.1. Parsing happens once, rendering and resolution consume the same IR.

#### Error Handling

The `SemanticAnalyzer` does **not** need explicit error recovery for missing or
unreadable files — `Namespace` already handles I/O errors, invalid encodings, and
parse failures before the analyzer runs. The analyzer always receives a valid RF AST.

If an unexpected exception occurs during analysis (e.g., a bug in the analyzer code),
it propagates normally — the existing error handling in `Namespace` catches it and
reports a diagnostic. The model is either fully built or not built at all; partial
models are never exposed to LSP features.

#### Nested Variable Diagnostics ✅

The analyzer emits three dedicated error codes for nested variable resolution (see
"Nested Variable Resolution" section for the full pipeline). These are defined in
`errors.py` alongside the existing 44 diagnostic codes:

| Error Code | Severity | When Emitted |
|------------|----------|-------------|
| `VARIABLE_NAME_NOT_RESOLVABLE` | ERROR | At variable **definition** sites when a nested inner variable is not found in scope (e.g., `${cfg_${UNDEFINED}}` where `${UNDEFINED}` doesn't exist) |
| `VARIABLE_NAME_NOT_STATICALLY_RESOLVABLE` | HINT | At variable **definition** sites when the inner variable exists but its value cannot be determined at analysis time (e.g., `${cfg_${arg}}` where `${arg}` is a keyword argument) |
| `VARIABLE_REFERENCE_NOT_STATICALLY_RESOLVABLE` | HINT | At variable **usage/reference** sites (Call Site 4 in both analyzers) when the variable reference text contains nested variables that cannot be statically resolved |

The ERROR severity for `VARIABLE_NAME_NOT_RESOLVABLE` is justified: if the inner variable
doesn't exist, Robot Framework will also fail at runtime. The HINT severity for the other
two codes reflects that the analyzer simply lacks enough static information — the code may
be perfectly valid at runtime.

#### RF AST Node → Semantic Node Mapping

Every RF AST node that the Visitor encounters maps to either a `SemanticStatement`
subclass (leaf) or a `SemanticBlock` subclass (container), with a dedicated
`NodeKind` value. No AST nodes are lost: nodes without a specialized `visit_*()`
method flow through `visit_Statement()`, which uses `_node_kind_for_statement()`
to select the right `NodeKind` (e.g. `END`, `BREAK_STATEMENT`, `COMMENT`,
`ELSE_HEADER`, `TRY_HEADER`) based on the AST class. Tokens are mapped via
`_RF_TOKEN_TO_TOKEN_KIND`. There is no `UNKNOWN` fallback.

**Block nodes** (containers with children):

| RF AST Node | Block Type | NodeKind | Notes |
|---|---|---|---|
| `File` | `SemanticBlock` | `FILE` | Root container, header=None |
| `SettingSection` | `SemanticBlock` | `SETTING_SECTION` | |
| `TestCaseSection` / `TaskSection` | `SemanticBlock` | `TESTCASE_SECTION` | |
| `KeywordSection` | `SemanticBlock` | `KEYWORD_SECTION` | |
| `VariableSection` | `SemanticBlock` | `VARIABLE_SECTION` | |
| `CommentSection` | `SemanticBlock` | `COMMENT_SECTION` | |
| `InvalidSection` | `SemanticBlock` | `INVALID_SECTION` | |
| `TestCase` / `Task` | `DefinitionBlock` | `TESTCASE` | header=DefinitionStatement(TEST_CASE_DEF) |
| `Keyword` | `DefinitionBlock` | `KEYWORD` | header=DefinitionStatement(KEYWORD_DEF) |
| `For` | `ForBlock` | `FOR` | header=ForStatement(FOR_HEADER); block carries flavor / loop_variables / options |
| `While` | `WhileBlock` | `WHILE` | header=WhileStatement(WHILE_HEADER); block carries condition / limit / on_limit |
| `If` / `IfElse` | `IfBlock` | `IF` | header=IfStatement(IF_HEADER) for IF/ELSE IF, base SemanticStatement(ELSE_HEADER) for ELSE; multi-branch via nested IfBlocks in body |
| `Try` / `TryExcept` | `TryBlock` | `TRY` | header=SemanticStatement(TRY_HEADER); EXCEPT/ELSE/FINALLY branches as nested TryBlock entries |
| `Group` (RF 7.3+) | `GroupBlock` | `GROUP` | header=SemanticStatement(GROUP_HEADER) |

**Statement nodes** (leaves with tokens):

| RF AST Node | Statement Type | NodeKind | Notes |
|---|---|---|---|
| `TestCaseName` | `DefinitionStatement` | `TEST_CASE_DEF` | Name token within test/task block |
| `KeywordName` | `DefinitionStatement` | `KEYWORD_DEF` | Name token within keyword block |
| `KeywordCall` | `KeywordCallStatement` | `KEYWORD_CALL` | |
| `Fixture` (Setup) | `KeywordCallStatement` | `SETUP` | Both test-level `[Setup]` and suite-level `Setup` |
| `Teardown` | `KeywordCallStatement` | `TEARDOWN` | Both test-level `[Teardown]` and suite-level `Teardown` |
| `TestTemplate` / `Template` | `KeywordCallStatement` | `TEMPLATE_KEYWORD` | `[Template]` setting |
| `TemplateArguments` | `TemplateDataStatement` | `TEMPLATE_DATA` | |
| `ForHeader` | `ForStatement` | `FOR_HEADER` | |
| `WhileHeader` | `WhileStatement` | `WHILE_HEADER` | |
| `IfHeader` | `IfStatement` | `IF_HEADER` | |
| `IfElseHeader` (ELSE IF) | `IfStatement` | `ELSE_IF_HEADER` | |
| `ElseHeader` | `SemanticStatement` | `ELSE_HEADER` | Identified via `CONTROL_FLOW` token "ELSE". |
| `InlineIfHeader` | `IfStatement` | `INLINE_IF_HEADER` | Inline IF with optional assign — distinct from regular `IF_HEADER` (no `END`). |
| `ExceptHeader` | `ExceptStatement` | `EXCEPT_HEADER` | |
| `TryHeader` | `SemanticStatement` | `TRY_HEADER` | Identified via `CONTROL_FLOW` token "TRY". |
| `FinallyHeader` | `SemanticStatement` | `FINALLY_HEADER` | Identified via `CONTROL_FLOW` token "FINALLY". |
| `End` | `SemanticStatement` | `END` | Closes FOR/IF/WHILE/TRY/GROUP. |
| `Var` (RF 7.0+) | `VarStatement` | `VARIABLE_DEF` | |
| `Return` (RF < 7.0) | `ReturnStatement` | `RETURN_SETTING` | `[Return]` setting (deprecated) |
| `ReturnSetting` (RF 7.0+) | `ReturnStatement` | `RETURN_SETTING` | Same as above, different AST class name |
| `ReturnStatement` | `SemanticStatement` | `RETURN_STATEMENT` | `RETURN` keyword (RF 5.0+). Captured with `CONTROL_FLOW` token. |
| `Break` | `SemanticStatement` | `BREAK_STATEMENT` | Identified via `CONTROL_FLOW` token "BREAK". |
| `Continue` | `SemanticStatement` | `CONTINUE_STATEMENT` | Identified via `CONTROL_FLOW` token "CONTINUE". |
| `LibraryImport` | `ImportStatement` | `IMPORT` | `import_type=LIBRARY` |
| `ResourceImport` | `ImportStatement` | `IMPORT` | `import_type=RESOURCE` |
| `VariablesImport` | `ImportStatement` | `IMPORT` | `import_type=VARIABLES` |
| `Tags` | `SettingStatement` | `SETTING_TAGS` | `[Tags]` (test- or keyword-level) |
| `KeywordTags` | `SettingStatement` | `SETTING_KEYWORD_TAGS` | `*** Settings *** Keyword Tags` |
| `ForceTags` | `SettingStatement` | `SETTING_FORCE_TAGS` | deprecated since RF 6.0 |
| `TestTags` | `SettingStatement` | `SETTING_TEST_TAGS` | |
| `DefaultTags` | `SettingStatement` | `SETTING_DEFAULT_TAGS` | deprecated since RF 6.0 |
| `Arguments` | `SettingStatement` | `SETTING_ARGUMENTS` | `[Arguments]` |
| `Documentation` | `SettingStatement` | `SETTING_DOCUMENTATION` | |
| `Metadata` | `SettingStatement` | `SETTING_METADATA` | |
| `Timeout` / `TestTimeout` | `SettingStatement` | `SETTING_TIMEOUT` | both forms map to the same NodeKind |
| `SuiteName` (RF 7.0+) | `SettingStatement` | `SETTING_SUITE_NAME` | suite-level `Name` setting |
| _(any unrecognized setting)_ | `SettingStatement` | `SETTING_OTHER` | defensive fallback for new RF versions |
| `SectionHeader` | `SemanticStatement` | `SECTION_HEADER` | Section headers (`*** Test Cases ***` etc.). |
| `Comment` | `SemanticStatement` | `COMMENT` | Comment lines. |
| `EmptyLine` | `SemanticStatement` | `EMPTY_LINE` | Blank line within a block (kept for position coverage). |
| `Variable` (Variables section) | `SemanticStatement` | `VARIABLE_DEF` | `*** Variables ***` entries. The `_visit_Variable` pre-visit collects the `VariableDefinition`; the generic `visit_Statement()` fallback creates the statement. |
| `GroupHeader` (RF 7.3+) | `SemanticStatement` | `GROUP_HEADER` | Task group header. |
| `Config` (RF 7.3+) | `SemanticStatement` | `CONFIG` | Task group config. |
| `Error` | `SemanticStatement` | `ERROR` | Parse error statement. |

**`*** Comments ***` section:** Comment lines and the entire `*** Comments ***` section
are represented as `SemanticStatement(kind=COMMENT)` with `SemanticToken(kind=COMMENT)`
tokens. The NamespaceAnalyzer does not analyze comments (falls through to
`generic_visit()`), but the SemanticModel preserves them for position coverage so that
`statement_at()` returns a valid result on every line.

**`[Return]` (deprecated):** Both RF's `Return` (RF < 7.0) and `ReturnSetting` (RF 7.0+)
AST nodes are represented as `ReturnStatement(kind=RETURN_SETTING)`. This reuses the
existing `ReturnStatement` subclass (with its `return_values` field) but uses a distinct
`NodeKind` to differentiate from the modern `RETURN` keyword statement. RF 7.0+
additionally emits a deprecation diagnostic via `token.error`.

### Run Keyword Detection Strategy

The Semantic Model needs to identify which keyword arguments are themselves keyword names
(inner keywords) vs. regular arguments. This is critical for correct inner keyword
resolution and `RunKeywordCallStatement.inner_calls` construction.

#### Current State: Hardcoded Name Lists

RobotCode currently uses hardcoded name detection in `library_doc.py`:

```python
# packages/robot/src/robotcode/robot/diagnostics/library_doc.py
RUN_KEYWORD_NAMES = {
    "runkeyword", "runkeywordandcontinueonfailure",
    "runkeywordandexpecterror", "runkeywordandignoreerror",
    "runkeywordandreturn", "runkeywordandreturnstatus",
    "runkeywordandwarnonfailure", "runkeywordiftestfailed",
    "runkeywordiftestpassed", "runkeywordiftimeoutoccurred",
    "runkeywordifanycriterialfailed", "runkeywordifalltestspassed",
}

RUN_KEYWORD_WITH_CONDITION_NAMES = {
    "runkeywordif": 1,           # 1 condition arg before keyword name
    "runkeywordunless": 1,
    "runkeywordandreturnif": 1,
    "runkeywordandexpecterror": 1,
    "repeatkeyword": 1,
    "waituntilkeywordsucceeds": 2,  # 2 args (retry, interval) before keyword name
}

RUN_KEYWORD_IF_NAME = "runkeywordif"
RUN_KEYWORDS_NAME = "runkeywords"
```

The `_analyze_run_keyword()` method in `NamespaceAnalyzer` handles four cases:
1. **Run Keyword** — first argument is keyword name, rest are keyword arguments
2. **Run Keyword With Condition** — skip N condition args, then keyword name + args
3. **Run Keywords** — all arguments are keyword names, split by `AND`
4. **Run Keyword If** — recursive: condition, keyword, args, ELSE IF/ELSE branches

Additionally, `RUN_KW_REGISTER.is_run_keyword()` checks for third-party libraries that
registered themselves via `robot.libraries.BuiltIn.register_run_keyword()`.

**Limitations of the current approach:**
- Only works for known BuiltIn keywords and explicitly registered third-party keywords
- Positional index logic is fragile and must be maintained manually
- Cannot detect keyword arguments in arbitrary library keywords

#### RF 7.4 Type Hints: `KeywordName` and `KeywordArgument`

Robot Framework 7.4 introduced two type hint classes in `robot.api.types` that
library developers can use to annotate which arguments are keyword names and which
are keyword arguments:

```python
# robot/api/types.py (RF 7.4+)

class KeywordName(str):
    """Name of a keyword executed by another keyword.

    Used as a type hint to mark that a certain argument of a keyword contains
    a keyword name. External tools can recognize special arguments using these
    types and handle them adequately.
    """

class KeywordArgument:
    """Argument of a keyword executed by another keyword.

    Used as a type hint to mark that a certain argument of a keyword contains
    an argument for a keyword being executed. External tools can recognize
    special arguments using these types and handle them adequately.
    """
```

**BuiltIn annotates every Run Keyword variant** with these types — `run_keyword`,
`run_keywords`, `run_keyword_if`/`unless`, `run_keyword_and_*`, `repeat_keyword`,
`wait_until_keyword_succeeds`, etc. Examples of representative signatures:

```python
# robot/libraries/BuiltIn.py (RF 7.4+)
from robot.api.types import KeywordArgument, KeywordName

def run_keyword(self, name: KeywordName, /, *args: KeywordArgument) -> object: ...
def run_keywords(self, *names_and_args: "KeywordName | KeywordArgument"): ...
def run_keyword_if(self, condition: Expression, name: KeywordName, /, *args: KeywordArgument) -> object: ...
def wait_until_keyword_succeeds(self, retry, retry_interval, name: KeywordName, /, *args: KeywordArgument): ...
```

**This means any library can now annotate its arguments this way**, not just BuiltIn.
For example, a custom library:

```python
from robot.api.types import KeywordName, KeywordArgument

class MyLibrary:
    def execute_with_retry(self, times: int, name: KeywordName, *args: KeywordArgument):
        """Runs the given keyword the specified number of times."""
        for _ in range(times):
            BuiltIn().run_keyword(name, *args)
```

RobotCode would automatically detect `name` as a keyword name and `args` as keyword
arguments — **without hardcoding `execute_with_retry` in any name list**.

#### Proposed Detection Strategy: Layered Fallback

The Semantic Model builder should use a layered approach for maximum compatibility:

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Type Hint Detection (RF 7.4+)                  │
│                                                         │
│ Inspect KeywordDoc argument type annotations:           │
│   • Argument type is KeywordName  → inner_calls entry      │
│   • Argument type is KeywordArgument → ARGUMENT             │
│   • Union of both (Run Keywords) → context-dependent    │
│                                                         │
│ Works for ANY library. General. Future-proof.           │
├─────────────────────────────────────────────────────────┤
│ Layer 2: RUN_KW_REGISTER (all RF versions)              │
│                                                         │
│ Check RUN_KW_REGISTER.is_run_keyword(libname, kwname):  │
│   • Third-party libraries that called                   │
│     register_run_keyword() at import time               │
│   • Returns args_to_process count                       │
│                                                         │
│ Works for libraries using the traditional API.          │
├─────────────────────────────────────────────────────────┤
│ Layer 3: Hardcoded Name Lists (fallback)                │
│                                                         │
│ RUN_KEYWORD_NAMES, RUN_KEYWORD_WITH_CONDITION_NAMES,    │
│ RUN_KEYWORD_IF_NAME, RUN_KEYWORDS_NAME                  │
│                                                         │
│ Only for BuiltIn keywords on RF < 7.4 where type hints  │
│ are not available. Will eventually become unnecessary.  │
└─────────────────────────────────────────────────────────┘
```

**Resolution order:**
1. If `KeywordDoc` has arguments with `KeywordName`/`KeywordArgument` type annotations → use them
2. Else if `RUN_KW_REGISTER.is_run_keyword()` → use `args_to_process` positional logic
3. Else if keyword name matches hardcoded lists → use current `_analyze_run_keyword()` logic
4. Otherwise → all arguments are regular `TokenKind.ARGUMENT`

#### Impact on KeywordDoc

Layer 1 requires `KeywordDoc` to expose type hint information per argument.
This is implemented as two boolean flags on `ArgumentInfo` (not as new
`KeywordArgumentKind` enum values):

```python
@dataclass
class ArgumentInfo:
    name: str
    kind: KeywordArgumentKind   # Python-level kind (positional, named, variadic)
    # ...
    is_keyword_name: bool = False        # type annotation is KeywordName
    is_keyword_argument: bool = False    # type annotation is KeywordArgument
```

Rationale: `KeywordArgumentKind` describes the Python-level argument kind, while
`KeywordName`/`KeywordArgument` describe the semantic role. They are orthogonal —
a `KeywordName` argument can be positional-only (as in `run_keyword(self, name: KeywordName, /)`).

The dispatcher in `run_keyword.py` checks the layers in order:

```python
def get_keyword_argument_strategy(keyword_doc) -> Optional[KeywordArgumentStrategy]:
    if any(arg.is_keyword_name or arg.is_keyword_argument for arg in keyword_doc.arguments):
        return KeywordArgumentStrategy.TYPE_HINTS
    if keyword_doc.is_registered_run_keyword:
        return KeywordArgumentStrategy.REGISTERED
    if keyword_doc.is_any_run_keyword():
        return KeywordArgumentStrategy.HARDCODED
    return None
```

#### Example: How Type Hints Map to Model Tokens

Given `Wait Until Keyword Succeeds    3x    200ms    My KW    arg1    arg2`:

```python
# KeywordDoc for Wait Until Keyword Succeeds:
# wait_until_keyword_succeeds(retry, retry_interval, name: KeywordName, /, *args: KeywordArgument)
#
# Argument analysis:
#   retry           → regular argument       → TokenKind.ARGUMENT
#   retry_interval  → regular argument       → TokenKind.ARGUMENT
#   name            → is_keyword_name=True   → inner_calls entry
#   *args           → is_keyword_argument    → ARGUMENT (on inner KeywordCallStatement)
#
# NOTE: inner `tokens` lists are fully populated by the analyzer (KEYWORD
# with BDD/Namespace splits + ARGUMENT with named-arg + variable sub-tokens),
# matching the shape shown below.

RunKeywordCallStatement(
    kind=NodeKind.KEYWORD_CALL,
    keyword_doc=<KeywordDoc for Wait Until Keyword Succeeds>,
    tokens=[
        SemanticToken(kind=TokenKind.KEYWORD, value="Wait Until Keyword Succeeds", ...),
        SemanticToken(kind=TokenKind.ARGUMENT, value="3x", ...),
        SemanticToken(kind=TokenKind.ARGUMENT, value="200ms", ...),
    ],
    inner_calls=[
        KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            keyword_doc=<KeywordDoc for My KW>,
            tokens=[
                SemanticToken(kind=TokenKind.KEYWORD, value="My KW", ...),
                SemanticToken(kind=TokenKind.ARGUMENT, value="arg1", ...),
                SemanticToken(kind=TokenKind.ARGUMENT, value="arg2", ...),
            ],
        ),
    ],
)
```

Given a custom library keyword `execute_with_retry(times: int, name: KeywordName, *args: KeywordArgument)`:

```python
# RobotCode automatically detects keyword arguments via type hints.
# No hardcoding needed — works for any library on RF 7.4+.

# Robot source: Execute With Retry    5    My Custom Keyword    ${data}

RunKeywordCallStatement(
    kind=NodeKind.KEYWORD_CALL,
    keyword_doc=<KeywordDoc for Execute With Retry>,
    tokens=[
        SemanticToken(kind=TokenKind.KEYWORD, value="Execute With Retry", ...),
        SemanticToken(kind=TokenKind.ARGUMENT, value="5", ...),
    ],
    inner_calls=[
        KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            keyword_doc=<KeywordDoc for My Custom Keyword>,
            tokens=[
                SemanticToken(kind=TokenKind.KEYWORD, value="My Custom Keyword", ...),
                SemanticToken(kind=TokenKind.ARGUMENT, value="${data}", ...,
                              sub_tokens=[
                                  SemanticToken(kind=TokenKind.VARIABLE, value="${data}", ...),
                              ]),
            ],
        ),
    ],
)
```

### Serialization (NamespaceData)

The Semantic Model must be persisted in `NamespaceData` for cache-restored namespaces.
Since `NamespaceData` is serialized via **pickle** (`pickle.dumps()` / `pickle.loads()`
in `data_cache.py`), the subclass hierarchy is preserved automatically — pickle stores
the full type of each object. **No discriminator fields or parallel `*Data` classes needed.**

#### What Pickle Handles Automatically

- `SemanticNode` subclass types (`SemanticStatement`, `SemanticBlock`, `DefinitionBlock`)
- `SemanticStatement` subclass types (`ForStatement`, `WhileStatement`, etc.)
- `NodeKind` and `TokenKind` enum values
- `ForFlavor`, `VarScope`, `OnLimitAction`, `ForZipMode`, `ImportType` enums
- All primitive fields (`str`, `int`, `bool`, `Optional`, `List`)
- Nested `SemanticToken` objects including `sub_tokens`
- Tree structure (`SemanticBlock.body` containing `SemanticNode` children)

#### What Pickle Cannot Handle: Live Object References

Live objects like `KeywordDoc`, `VariableDefinition`, and `LibraryEntry` are shared
across the entire workspace and cannot be pickled as part of `NamespaceData` — they
would create duplicated, disconnected copies. These references must be replaced with
`stable_id` strings before pickling and resolved back to live objects after unpickling.

This follows the existing pattern already used for `keyword_references` and
`variable_references` in `NamespaceData`.

#### Pickle Preparation: `__getstate__` / `__setstate__`

`SemanticToken` has no live references — it is a pure value object and needs no
custom pickle handling. Only statement subclasses carry resolved references
(`keyword_doc`, `lib_entry`, `template_keyword_doc`) that must be replaced with
`stable_id` strings before pickling.

After unpickling, the string ids need to be resolved back to live objects:

```python
def resolve_references(
    model: SemanticModel,
    kw_by_id: Dict[str, KeywordDoc],
    entry_by_key: Dict[str, LibraryEntry],
) -> None:
    """Resolve stable_id strings back to live objects after unpickling.

    Called in Namespace.from_data() after the lookup maps are built.
    Mutates the model in-place. Traverses both the flat statement list
    and the tree structure (if root is set) to resolve all references.
    """
    for stmt in model.statements:
        _resolve_statement(stmt, kw_by_id, entry_by_key)

    # Also traverse tree structure
    if model.root is not None:
        _resolve_block(model.root, kw_by_id, entry_by_key)


def _resolve_block(block, kw_by_id, entry_by_key):
    """Recursively resolve references in a block and its children."""
    if block.header is not None:
        _resolve_statement(block.header, kw_by_id, entry_by_key)
    for child in block.body:
        if isinstance(child, SemanticBlock):
            _resolve_block(child, kw_by_id, entry_by_key)
        elif isinstance(child, SemanticStatement):
            _resolve_statement(child, kw_by_id, entry_by_key)


def _resolve_statement(stmt, kw_by_id, entry_by_key):
    """Resolve statement-level references based on subclass type."""
    if isinstance(stmt, RunKeywordCallStatement):
        # Resolve inner calls recursively (check RunKeyword before KeywordCall
        # since RunKeywordCallStatement is a subclass of KeywordCallStatement)
        for inner in stmt.inner_calls:
            _resolve_statement(inner, kw_by_id, entry_by_key)
        if isinstance(stmt.keyword_doc, str):
            stmt.keyword_doc = kw_by_id.get(stmt.keyword_doc)
        if isinstance(stmt.lib_entry, str):
            stmt.lib_entry = entry_by_key.get(stmt.lib_entry)
    elif isinstance(stmt, KeywordCallStatement):
        if isinstance(stmt.keyword_doc, str):
            stmt.keyword_doc = kw_by_id.get(stmt.keyword_doc)
        if isinstance(stmt.lib_entry, str):
            stmt.lib_entry = entry_by_key.get(stmt.lib_entry)
    elif isinstance(stmt, TemplateDataStatement):
        if isinstance(stmt.template_keyword_doc, str):
            stmt.template_keyword_doc = kw_by_id.get(stmt.template_keyword_doc)
    elif isinstance(stmt, ImportStatement):
        if isinstance(stmt.lib_entry, str):
            stmt.lib_entry = entry_by_key.get(stmt.lib_entry)
```

#### In NamespaceData

```python
@dataclass
class NamespaceData:
    ...
    # The model is pickled directly — no parallel Data classes needed.
    # Tokens are pure value objects (no live references).
    # Statement-level live references (keyword_doc, lib_entry) are replaced
    # with stable_id strings via __getstate__ on the statement subclasses.
    semantic_model: Optional[SemanticModel] = None
```

#### to_data() / from_data() Integration

```python
# to_data() — no special handling needed, pickle calls __getstate__ on statements automatically
def to_data(self) -> NamespaceData:
    ...
    return NamespaceData(
        ...
        semantic_model=self._semantic_model,  # pickle handles the rest
    )

# from_data() — resolve stable_ids after unpickling
def from_data(cls, data, ...):
    ...
    # After building kw_by_id, entry_by_key maps:
    if data.semantic_model is not None:
        resolve_references(data.semantic_model, kw_by_id, entry_by_key)
        data.semantic_model.build_index()
    ...
```

---

## Impact on LSP Features

### Semantic Tokens (HIGH impact)

**Before:** ~1600 LOC with `KeywordTokenAnalyzer` (~400 LOC), 7+ `find_keyword()` calls, duplicated BDD/namespace/Run Keyword parsing.

**After:** Iterate the model tree, map `TokenKind` → LSP `SemanticTokenType`.

```python
for stmt in model.statements:
    for token in stmt.tokens:
        sem_type = TOKEN_KIND_TO_SEM_TYPE.get(token.kind)
        if sem_type is None:
            continue

        sem_mod = set()
        if token.kind == TokenKind.KEYWORD and isinstance(stmt, KeywordCallStatement) and stmt.keyword_doc:
            if stmt.keyword_doc.libname == "BuiltIn":
                sem_mod.add(RobotSemTokenModifiers.BUILTIN)

        if token.kind == TokenKind.VARIABLE:
            var_def = model.find_variable(token.value, token.line)
            if var_def is not None:
                if isinstance(var_def, BuiltInVariableDefinition):
                    sem_mod.add("builtin")
                elif isinstance(var_def, LocalVariableDefinition):
                    sem_mod.add("local")

        yield SemTokenInfo(token.line, token.col_offset, token.length, sem_type, sem_mod)

        # Sub-tokens (recursively: variables inside arguments, variable structure parts)
        if token.sub_tokens:
            for sub in token.sub_tokens:
                yield from generate_sub_token(sub)

# Granular variable sub-parts map to LSP types for fine-grained highlighting:
# VARIABLE_PREFIX      → RobotSemTokenTypes.VARIABLE_BEGIN  (or custom "variablePrefix")
# VARIABLE_OPEN_BRACE  → RobotSemTokenTypes.VARIABLE_BEGIN
# VARIABLE_CLOSE_BRACE → RobotSemTokenTypes.VARIABLE_END
# VARIABLE_BASE        → RobotSemTokenTypes.VARIABLE (inherits modifiers from parent)
# VARIABLE_TYPE_HINT   → SemanticTokenTypes.TYPE
# VARIABLE_EXTENDED    → SemanticTokenTypes.PROPERTY
# PYTHON_EXPRESSION    → SemanticTokenTypes.STRING (or custom)
# PYTHON_VARIABLE_REF  → RobotSemTokenTypes.VARIABLE
# TEXT_FRAGMENT         → SemanticTokenTypes.STRING
# VARIABLE_INDEX_*     → RobotSemTokenTypes.VARIABLE_BEGIN / content / VARIABLE_END
# VARIABLE_PATTERN     → SemanticTokenTypes.REGEXP
```

The entire `KeywordTokenAnalyzer` class and all `find_keyword()` fallback logic disappears.

### Inlay Hints (HIGH impact) — ✅ migrated (Tier 2)

**Before:** Calls `get_keyworddoc_and_token_from_position()` → `find_keyword()` for every keyword call. Plus a separate AST walk for `LibraryImport` / `VariablesImport` to fetch the init `KeywordDoc` via `namespace.get_imported_library_libdoc(...)` (with a fallback through `imports_manager.get_libdoc_for_*_import(...)` when the libdoc has errors).

**After:** Single pass over `model.statements`, no second find_keyword / libdoc lookup at request time. The analyzer pre-resolves both:
- `KeywordCallStatement.keyword_doc` for keyword calls / setup / teardown / template / test_template (one shared statement type, distinguished by `kind`).
- `ImportStatement.init_keyword_doc` for Library and Variables imports — populated in `_visit_import_node` from the resolved `LibraryEntry.library_doc.inits[0]`, with the same fallback behaviour as the legacy path (uses `imports_manager.get_libdoc_for_*_import(name, (), ...)` when `lib_doc.errors` is non-empty).

```python
for stmt in model.statements:
    if isinstance(stmt, KeywordCallStatement) and stmt.keyword_doc:
        # Parameter-name + namespace hints from pre-resolved keyword_doc.
        ...
    elif (
        isinstance(stmt, ImportStatement)
        and stmt.init_keyword_doc is not None
        and stmt.import_type in (ImportType.LIBRARY, ImportType.VARIABLES)
    ):
        # Init-arg hints from pre-resolved init_keyword_doc — no AST re-walk.
        ...
```

Equivalence with the legacy path is covered by E2E tests in
`test_inlay_hint_model.py` across all 8 RF versions (14 source-level cases ×
3 config axes for the cross-product, plus dedicated tests for library aliases,
library/variables-import init args, and Run-Keyword-If inner-call
non-leakage).

### Signature Help (MEDIUM impact) — ✅ migrated (Tier 2)

**Before:** Calls `get_keyworddoc_and_token_from_position()` (re-runs `find_keyword`)
plus `get_argument_info_at_position()` (~150 LOC RF-Token walk in `ModelHelper`)
on every keystroke.

**After:** Pure SemanticModel path — no AST walk, no `ModelHelper`. Cursor →
SemanticStatement → pre-resolved `keyword_doc` → SemanticToken-based
arg-index math:

```python
stmt = model.statement_at(position.line + 1)
if isinstance(stmt, KeywordCallStatement):
    if stmt.kind not in (KEYWORD_CALL, SETUP, TEARDOWN):  # legacy parity
        return None
    if stmt.keyword_doc is None:
        return None
    if not _cursor_past_keyword_name(stmt, position):  # +2-char grace
        return None
    if not _cursor_within_line_extent(stmt, position): # past EOL → no popup
        return None
    arg_tokens = [t for t in stmt.tokens if t.kind is TokenKind.ARGUMENT]
    return _build_signature_help(stmt.keyword_doc, arg_tokens, position)

if isinstance(stmt, ImportStatement) and stmt.import_type in (LIBRARY, VARIABLES):
    # …`init_keyword_doc` instead of the libdoc lookup, WITH NAME guard
    # via the CONTROL_FLOW SemanticToken.
```

`_active_argument_from_semantic_tokens` is the SemanticToken-based
replacement for `get_argument_info_at_position`. It uses pre-detected
NAMED_ARGUMENT_NAME sub-tokens, so no `split_from_equals` at request
time. CONTINUATION/EOL edge cases are handled by checking the token's
own `range`.

Run-Keyword inner-call signatures are deliberately NOT yet handled — see
the Ideas Collection.

### Code Action — Open Documentation (MEDIUM impact) — ✅ migrated (Tier 2)

**Before:** Calls `get_keyworddoc_and_token_from_position()` for the
keyword-call branch (re-runs `find_keyword`); `LibraryEntry` lookup walks
`namespace.libraries.values()`.

**After:** Pure SemanticModel — three branches dispatched by
`isinstance(stmt, …)`:

```python
stmt = model.statement_at(range.start.line + 1)

# Library / Resource import
if isinstance(stmt, ImportStatement) and stmt.import_type in (LIBRARY, RESOURCE):
    name_tok = next(t for t in stmt.tokens if t.kind is IMPORT_NAME)
    if range in name_tok.range:
        return _build_url(stmt.import_name, _import_args(stmt))

# KeywordCall / Fixture
if isinstance(stmt, KeywordCallStatement) and stmt.keyword_doc:
    if _cursor_on_keyword_reference(range.start, stmt):  # NAMESPACE+SEPARATOR+KEYWORD union
        return _build_keyword_action(stmt.keyword_doc)

# KeywordName definition header
if isinstance(stmt, DefinitionStatement) and stmt.kind is KEYWORD_DEF:
    name_tok = next(t for t in stmt.tokens if t.kind is KEYWORD_NAME)
    if range in name_tok.range:
        return _build_url(document_name, target=name_tok.value)
```

Required a small analyzer fix: `DefinitionStatement.tokens` was previously
empty for TestCase / Keyword headers (the visitor created the statement
without populating tokens). Now `visit_TestCase` / `visit_Keyword` call
`_build_tokens_from_node(node.header)` so the KEYWORD_NAME / TEST_NAME
SemanticToken is discoverable from the model — also a foundation for
Tier 3 hover / rename on definition headers.

### Code Action Quick Fixes / Refactor (MEDIUM impact) — ✅ migrated (Tier 2)

Migrated (commit `6a3d5a39`). The two actions that need keyword resolution
follow the Open Documentation pattern (model branch + legacy fallback):

- **Quick Fixes — "Create Keyword"**: `_resolve_create_keyword_target_from_model()`
  resolves the target via `model.statement_at()` + `isinstance(stmt,
  KeywordCallStatement)`; the `[Arguments]` placeholder list is built from the
  statement's ARGUMENT SemanticTokens. `ModelHelper`
  (`get_namespace_info_from_keyword_token`) survives only inside the legacy
  fallback path.
- **Refactor — "Assign Result to Variable"**:
  `_assign_result_insert_position_from_model()` finds the insert position from
  the model. `code_action_refactor.py` no longer imports `ModelHelper` at all —
  its remaining `namespace.find_keyword()` call only probes for a free
  "New Keyword N" name in Extract Keyword, not cursor resolution.

The other actions in both files (surround with TRY/EXCEPT, Extract Keyword,
disable-diagnostics fixes, …) are AST/text manipulation without ModelHelper
keyword resolution — nothing further to migrate there.

Equivalence covered by `test_code_action_quick_fixes_model.py` (9 tests) and
`test_code_action_refactor_model.py` (3 tests).

### Completion (MEDIUM impact)

**Before:** Must interpret AST to determine context (keyword? argument? template data?).

**After:**
```python
stmt = model.statement_at(cursor_line)
if stmt is None:
    # New line — check surrounding statements for context
    return default_completions()

if isinstance(stmt, KeywordCallStatement):
    token = model.token_at(cursor_line, cursor_col)
    if token is None or token.kind == TokenKind.KEYWORD:
        return keyword_completions()
    elif token.kind in (TokenKind.ARGUMENT, TokenKind.NAMED_ARGUMENT_NAME):
        # Know exactly which parameter position → type-aware completions
        return argument_completions(stmt.keyword_doc, token)

elif isinstance(stmt, TemplateDataStatement):
    # Don't offer keyword completions — these are template arguments
    return template_argument_completions(stmt.template_keyword_doc)

elif isinstance(stmt, ImportStatement):
    return import_completions(stmt.import_type)

elif isinstance(stmt, ForStatement):
    # Offer flavor-dependent completions: start=, mode=, fill=
    return for_option_completions(stmt.flavor)

elif isinstance(stmt, WhileStatement):
    # Offer limit=, on_limit=, on_limit_message=
    return while_option_completions(stmt)

elif isinstance(stmt, VarStatement):
    # Offer scope=, separator=
    return var_option_completions(stmt.scope)

elif isinstance(stmt, ExceptStatement):
    # Offer type=, AS
    return except_option_completions(stmt.pattern_type)
```

**Note:** Completion at the cursor still works with incomplete code — the model is
incomplete only for the cursor line. Surrounding statements provide context.

### Goto / Document Highlight (NO change needed)

These use pre-computed `keyword_references` and `variable_references` (def → locations).
The `SemanticAnalyzer` produces the same reference dicts as part of `AnalyzerResult` —
these features work unchanged because they consume references, not the model directly.

### Hover / References / Rename (GRADUAL migration — Tier 3)

These use pre-computed reference dicts for their core lookup but **also** depend on
`ModelHelper` via inheritance for keyword resolution at cursor position, definition
lookup, or reference walking. They continue to work unchanged via the reference dicts
but can be simplified in Tier 3 by replacing `ModelHelper` calls with direct model
queries (`model.token_at()` → `model.find_variable()` / `stmt.keyword_doc`).

For variable hover and rename, `find_variable(name, line)` already does the
heavy lifting via `enclosing_definition(line)`. Where the call site has a
node in hand instead of a line (e.g. iterating `model.statements`), the new
`SemanticModel.enclosing_definition_block(node)` saves a line-range scan
and avoids ambiguity when multiple definitions overlap on one line.

---

## Context-Dependent Token Interpretations

With the tree-based model, context is **implicit in the structure**:

| Context | How the Tree Represents It |
|---------|---------------------------|
| Regular keyword call | `KeywordCallStatement(kind=KEYWORD_CALL)` with `SemanticToken(kind=KEYWORD)` |
| BDD prefix | Separate `SemanticToken(kind=BDD_PREFIX)` before the keyword token |
| Namespace-qualified | `SemanticToken(kind=NAMESPACE)` + `SemanticToken(kind=SEPARATOR)` + `SemanticToken(kind=KEYWORD)` |
| Run Keyword inner keywords | `RunKeywordCallStatement.inner_calls` — separate `KeywordCallStatement` per inner keyword |
| AND/ELSE/ELSE IF in Run Keywords | `SemanticToken(kind=CONTROL_FLOW)` |
| Template keyword | `KeywordCallStatement(kind=TEMPLATE_KEYWORD)` |
| Template data rows | `TemplateDataStatement(kind=TEMPLATE_DATA)` — no keyword tokens at all |
| Fixture keyword | `KeywordCallStatement(kind=SETUP/TEARDOWN)` |
| Variable references | `SemanticToken(kind=VARIABLE)` as sub_token of ARGUMENT |
| Named arguments | `SemanticToken(kind=NAMED_ARGUMENT_NAME)` + `NAMED_ARGUMENT_VALUE` |

Transformations that **remain in the generator** (purely visual, no resolution needed):

| Transformation | Why It Stays |
|----------------|-------------|
| `[Setting]` → `[` + Content + `]` | Pure bracket rendering |
| Embedded keyword regex split | Uses `keyword_doc.matcher` from token, but splitting is visual |
| Import path escape highlighting | Pure text processing |
| Continuation (`...`) rendering | Pure text processing |

---

## Testing Strategy

The old `NamespaceAnalyzer` has **zero unit tests** — its behavior is only verified
indirectly through LSP integration snapshot tests (semantic tokens, hover, goto, etc.).
The Semantic Model is the opportunity to establish comprehensive, multi-level test
coverage from the start.

### Current Test Gaps

| Area | Unit Tests | Integration Tests |
|------|-----------|-------------------|
| NamespaceAnalyzer `visit_*()` | **None** | Indirect via LSP snapshots |
| Variable resolution / scope lookup | **None** | Indirect via hover/goto |
| Run Keyword handling | **None** | Indirect via hover snapshots |
| Scope tracking (enter/exit) | **None** | — |
| Diagnostics output | **None** | Explicitly disabled (`DiagnosticsMode.OFF`) |
| Individual AST node types | **None** | Partial via `.robot` test files |

All tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/` — **495+ tests passing on RF 7.4** (variants per RF version due to feature gates).
Test files: `test_model.py`, `test_run_keyword.py`, `test_run_keyword_integration.py`, `test_serialization.py`, `test_variable_tokenizer.py`, `test_analyzer.py`, `test_argument_info.py`, `test_analyzer_snapshot.py`, `test_variable_pipeline_comparison.py`, `test_nested_variable_resolution.py`, `test_parent_navigation.py`.

LSP-feature-side equivalence tests for the semantic-model migration live separately under
`tests/robotcode/language_server/robotframework/parts/`: `test_inlay_hint_model.py`,
`test_signature_help_model.py`, `test_code_action_documentation_model.py`,
`test_code_action_quick_fixes_model.py`, `test_code_action_refactor_model.py`, and
`test_semantic_tokens_flag_parity.py` (dual-protocol flag OFF/ON comparison — **currently
vacuous**, the flag never reaches the server; see the Tier 1 checklist item).

**Test conventions (project-wide)**:
- Mocks use `mocker: MockerFixture` (pytest-mock), never `unittest.mock.MagicMock` directly. `mocker.create_autospec(KeywordFinder, instance=True)` is preferred for typed mocks.
- Shared fixtures live in `tests/robotcode/conftest.py` and propagate via pytest's conftest inheritance: `parse_robot(text)`, `make_resource_doc(source)` (plain helpers), `make_finder(keyword_map)`, `analyzer_factory(text, keyword_map=...)`, `make_library_doc_mock(...)` (fixture-based). Sub-directories add module-specific fixtures (e.g. `run_kw_analyzer`, `run_both`).

### Test Levels

All tests live under `tests/robotcode/robot/diagnostics/test_semantic_analyzer/`.

#### Level A: Data Structures & Query API (Pure Unit Tests)

Tests for `model.py`, `nodes.py`, `enums.py` — **no RF parser, no file I/O**.
Handcrafted `SemanticModel` instances with synthetic statements and tokens.

- **`test_model_query.py`** — `statement_at()`, `token_at()`, `token_path_at()`,
  `find_variable()`, `get_variables_at()`, `build_index()`. Tests for exact line hits,
  multi-line ranges, overlapping ranges (smallest wins), empty lines inside definitions,
  recursive sub_token descent, boundary conditions (inclusive start, exclusive end),
  position-aware variable visibility, local-overrides-file precedence, case-insensitive
  matching, skip flags, empty model edge cases.

- **`test_nodes.py`** — Statement subclass construction, default field values,
  inheritance from `SemanticStatement`, enum value correctness.

#### Level B: Transformer Module Tests (Unit Tests with RF Parser)

Tests for `variable_tokenizer.py`, `run_keyword.py`, `serialization.py`.
These use RF's parser/types but not the full analyzer pipeline.

- **`test_variable_tokenizer.py`** — Parametrized over all 15 variable forms
  (`${name}`, `${age: int}`, `%{NAME=default}`, `${obj.attr}`, `${config_${env}}`,
  `${{expr}}`, `${result}=`, `${arg:\d+}`, `@{items}`, `&{config}`, etc.).
  Verifies correct sub-token sequence (kind + value), contiguous positions
  (no gaps, no overlaps), and compound tokens with mixed text/variables.

- **`test_run_keyword.py`** — Layered detection strategy (Type Hints → RK Register →
  Hardcoded → regular keyword). Parametrized inner keyword position detection for
  `Run Keyword`, `Run Keywords` (AND-splitting), `Run Keyword If` (ELSE-branching),
  `Run Keyword And Continue On Failure`.

- **`test_serialization.py`** — Pickle roundtrip: references become stable IDs in
  `__getstate__`, restored via `resolve_references()`. Sub-token trees survive
  serialization. Unknown IDs become `None`.

#### Level C: Analyzer Integration Tests (Real `.robot` Files)

Level C exists and is active in `test_analyzer_snapshot.py`.

Current Level C coverage snapshots deterministic analyzer output and includes
explicit semantic assertions (not snapshot-only):
- statement kind sequence per scenario
- local variable collection per `DefinitionStatement`
- referenced variable name expectations

This keeps the tests meaningful even with mocked `KeywordFinder`.

The **full** Level C target (real namespace integration + richer keyword/lib
resolution fidelity) is still completed in Phase 2 when `SemanticAnalyzer` is
integrated into the real `Namespace` pipeline and Level D/E tests are added.

**Planned test data** — dedicated `.robot` files per category:
`keyword_calls`, `control_flow`, `variables`, `imports`, `settings`,
`definitions`, `templates`, `run_keywords`, `var_statement`, `return_statement`,
`inline_if`, `edge_cases`, plus `version_specific/` for RF 5.0/7.0/7.4 features.

- **`test_analyzer_model_output.py`** — Parametrized snapshot tests: each `.robot` file
  produces a YAML snapshot of the full model tree (statement kinds, token kinds, values,
  resolved references as names, sub-token structure, statement-specific properties).

- **`test_analyzer_statement_types.py`** — Parametrized mapping: each RF AST node type →
  correct `NodeKind` + `SemanticStatement` subclass.

#### Level D: LSP Regression Tests (Feature Flag Toggle)

Existing LSP snapshot tests (semantic tokens, hover, goto, etc.) run with a parametrized
fixture that toggles the feature flag. Both `old_analyzer` and `semantic_model` modes
must produce **identical** output. No new test files — only a fixture addition.
After Phase 4, the parameterization is removed.

#### Level E: Comparison & Performance Tests (Temporary)

**Transitional tests** — exist during Phase 2–3, removed in Phase 4 with the old analyzer.

- **`test_variable_pipeline_comparison.py`** ✅ — **IMPLEMENTED.** Runs both analyzers on 14 synthetic parity cases plus every real `.robot` file in the LSP test data and compares **all** `AnalyzerResult` fields: `diagnostics`, `keyword_references`, `variable_references`, `local_variable_assignments`, `namespace_references`, `test_case_definitions`, `keyword_tag_references`, `testcase_tag_references`, `metadata_references`, `scope_tree`. Three known parity exceptions (`variables.robot`, `versions/rf73/variable_conversion.robot`, and `hover.robot` for RF < 7.0) are documented as xfails — in all three cases the SemanticAnalyzer is the *more* correct one.

- **`test_nested_variable_resolution.py`** ✅ — **IMPLEMENTED.** 105+ focused tests for nested variable resolution parity: static resolution, inner variable references, error/hint diagnostics, extended expression guards, inline Python guards, number literals, list/dict variable resolution, and definition-site early-return behavior.

- **Full `AnalyzerResult` parity** — covered by `test_variable_pipeline_comparison.py` (see above). No separate `test_analyzer_comparison.py` is needed.

- **`test_analyzer_performance.py`** — Relative benchmarks (not absolute timings):
  - **Overhead:** `SemanticAnalyzer` ≤ 30% slower than `NamespaceAnalyzer` (warmup + N runs)
  - **Memory:** `SemanticModel` ≤ 500KB per file (estimated via pickle size)
  - **Serialization:** pickle roundtrip + `resolve_references()` ≤ 50ms per file

### Test Level Summary

| Level | Scope | Test Pattern | Lifecycle |
|-------|-------|-------------|-----------|
| **A** | Data structures, query API | Pure unit tests (synthetic models) | Permanent |
| **B** | Variable tokenizer, Run Keyword, serialization | Unit tests with RF parser types | Permanent |
| **C** | Full analyzer pipeline | Integration + snapshot (regtest2) | Permanent |
| **D** | LSP feature regression | Existing snapshots, parameterized fixture | Phase 2–3, then simplified |
| **E** | Old vs. new comparison + performance | Comparison + benchmarks | Phase 2–3, then **deleted** |

### Test Data Principles

1. **Dedicated test data files** — `.robot` files designed to cover specific features,
   not copied from production. Each file focuses on one category.
2. **Minimal but complete** — each test file exercises all variants of its category
   (e.g., `control_flow.robot` has FOR IN, FOR IN RANGE, FOR IN ENUMERATE, FOR IN ZIP,
   WHILE, IF/ELSE IF/ELSE, TRY/EXCEPT/FINALLY, BREAK, CONTINUE, RETURN, END).
3. **Version-aware** — `version_specific/` subdirectory for RF-version-dependent features.
   Tests use `pytest.mark.skipif(RF_VERSION < ...)` guards.
4. **Diffable snapshots** — model output serialized as YAML with human-readable
   reference names (not object IDs). Easy to review in PRs.
5. **Independent** — each test file is self-contained. No implicit dependencies
   between test files.

### Phase Integration

| Phase | Test Activities |
|-------|----------------|
| **Phase 1** | Write Level A + B + C tests. All green before moving to Phase 2. |
| **Phase 2** | Add Level D (feature flag fixture). Add Level E (comparison + performance). Run comparison tests on every PR. |
| **Phase 3** | All Level D tests pass with both analyzers. Level E confirms identical output. Performance within bounds. |
| **Phase 4** | Remove Level E tests (old analyzer deleted). Simplify Level D (remove parameterization). |
| **Phase 5** | Extend Level C with new test data for advanced features (Call Hierarchy, etc.). |

---

## Advantages of Tree vs. Flat Dicts

| Aspect | Flat Dicts (previous design) | Tree (current design) |
|--------|------|------|
| **Context** | Lost — need AST for statement kind | Implicit — `stmt.kind` |
| **Arguments** | Separate annotation type needed | Part of statement's token list |
| **Ordering** | Dict gives random access only | Natural document order in list |
| **Run Keywords** | Only keyword position annotated, args unknown | Full structure including CONTROL_FLOW tokens + `RunKeywordCallStatement.inner_calls` |
| **Iteration** | Must iterate AST + look up dict per position | Iterate model directly |
| **Extensibility** | New dict per annotation type | New `TokenKind` or `NodeKind` value |
| **Serialization** | Multiple parallel dicts to serialize | Single tree to walk |
| **Named args** | Needs `ArgumentAnnotation` | Already in token list as `NAMED_ARGUMENT_*` |

---

## Ideas Unlocked by the SemanticModel

A brainstorm — LSP features that became easier (or possible at all) once
the SemanticModel pre-resolves keyword docs, lib entries, scope, and
block-level data. **Not a plan, not a phase** — just a place to capture
observations made during the migration so they're not lost when we
revisit. What ends up actually built is decided once the migration
itself is done. Add new ideas here as they come up.

### Inlay Hints

- **TemplateArguments rows** — show the template keyword's parameter
  names on each `T1    Alice    Hi` data row under `[Template]` / `Test
  Template`. Enabler: `TemplateDataStatement.template_keyword_doc` is
  already resolved by the analyzer; legacy never wired this up because
  it required a separate AST walk + `find_keyword` per row.
- **Run-Keyword inner calls** — `Run Keyword If    cond    Log    msg`
  → `message=` next to `msg`. Enabler:
  `RunKeywordCallStatement.inner_calls[*]` are full `KeywordCallStatement`s
  with their own `keyword_doc` and pre-decomposed tokens.
- **Inline IF assign** — `${r}=    IF    ${cond}    My Keyword    arg`
  → parameter-name hint on the inline-IF body keyword. Enabler:
  the inner-call resolution already runs for the inline-IF body.
- **VAR scope hint** — `VAR    ${x}    1` → trailing `LOCAL` to surface
  the implicit default. Enabler: `VarStatement.scope`.
- **Variable type from KeywordDoc return** — `${result}=    My Keyword`
  → `${result}: int` hint. Enabler:
  `KeywordCallStatement.keyword_doc.return_type` paired with
  `assign_variables`.

### Signature Help

- **TemplateArguments** — cursor in a template-data row → signature of
  the template keyword. Enabler: same `template_keyword_doc`.
- **TestTemplate / Template setting value** — cursor on the keyword
  name in a `Test Template    My KW` line shows `My KW`'s signature.
  Enabler: legacy has no handler at all (`signature_help_TestTemplate`
  doesn't exist); the model already produces a `KeywordCallStatement`
  with `kind=TEMPLATE_KEYWORD` and resolved `keyword_doc`.
- **Run-Keyword inner calls** — cursor on an inner call's arguments
  shows the inner call's signature, not the outer Run-Keyword's.
  Enabler: per-inner `keyword_doc` + `tokens` on
  `RunKeywordCallStatement.inner_calls`.
- **Block-option signatures** — cursor on `start=` / `mode=` / `fill=`
  in `FOR ... IN ZIP/ENUMERATE`, on `limit=` / `on_limit=` in `WHILE`,
  on `type=` in `EXCEPT`, on `scope=` / `separator=` in `VAR`. Enabler:
  per-block fields (`ForBlock.flavor`, `WhileBlock.limit`, …) tell us
  which option set is valid; the option enums (`ForZipMode`,
  `OnLimitAction`, `VarScope`) provide the value space.

### Hover

- **Variable hover** — definition + scope + visibility range, including
  whether it's local to this `DefinitionBlock` or file-scoped.
  Enabler: `find_variable(name, line)` +
  `enclosing_definition_block(node)` + `local_variables` carry
  `(VariableDefinition, visible_from_line)` tuples.
- **Tag hover** — list other tests / keywords carrying the same tag
  (cross-file, click-to-jump). Enabler: `keyword_tag_references` /
  `testcase_tag_references` are already collected.
- **Library import hover** — resolved source path, version, aliases.
  Enabler: `ImportStatement.lib_entry`.
- **Run-Keyword inner-call hover** — hover on an inner keyword's name
  shows the inner keyword's docs (currently only the outer Run-Keyword
  docs surface). Enabler: per-inner `keyword_doc`.

### Completion

- **Named-argument completion** — once a keyword is resolved, suggest
  its un-set parameters as `name=` completions inside the call. Enabler:
  `KeywordCallStatement.keyword_doc.arguments` is right on the
  statement; the NAMED_ARGUMENT_NAME tokens already in `tokens` tell
  us which names are taken.
- **Template-row argument completion** — inside a `[Template]` data row,
  suggest the template keyword's parameter names. Enabler:
  `TemplateDataStatement.template_keyword_doc`.
- **Block-option completion** — `FOR ... IN ENUMERATE    start=`,
  `WHILE    cond    limit=`, `EXCEPT    type=`, `VAR    scope=`. Each
  option has a fixed enum (`ForFlavor`, `ForZipMode`, `OnLimitAction`,
  `VarScope`).
- **BDD prefix completion** — `Given|When|Then|And|But` at the start of
  a keyword-call cell. Enabler: `BDD_PREFIX` is a first-class TokenKind
  on the keyword-name; the model can tell whether one is already there.

### Code Actions / Quick Fixes

- **Convert positional ↔ named arguments** for a keyword call. Enabler:
  `NAMED_ARGUMENT_NAME` / `NAMED_ARGUMENT_VALUE` splits + the resolved
  `keyword_doc.arguments` make the bidirectional mapping trivial.
- **Inline a `Run Keyword If`** into a real `IF ... END` block. Enabler:
  `RunKeywordCallStatement.inner_calls` carries the branches in their
  resolved form.
- **Extract a complex IF condition into a variable** —
  `IF ${a + b > 10}` → `${cond}=    Evaluate    ${a + b > 10}` +
  `IF ${cond}`. Enabler: `IfBlock.condition` is parsed.
- **Convert FOR flavour** — `FOR ... IN RANGE    n` ↔ `FOR ... IN
  ENUMERATE` etc. Enabler: `ForBlock.flavor` + `loop_variables` +
  options.
- **"Strip namespace prefix"** when a `Lib.Keyword` could be unqualified
  (no ambiguity). Enabler: `KeywordCallStatement.lib_entry` +
  `namespace.libraries` membership check.

### Diagnostics / Linting

- **Mixed argument styles** in one call (positional after named).
  Enabler: NAMED_ARGUMENT_NAME tokens are pre-marked.
- **Unreachable code after `RETURN` / `BREAK` / `CONTINUE`** within a
  block. Enabler: walk `block.body` and stop at the terminator.
- **Unused local variables** in a `DefinitionBlock`. Enabler:
  `local_variables` (definitions) ∩ `variable_references` (uses).
- **`Run Keyword X` where direct call would do** — `Run Keyword    Log
      msg` could just be `Log    msg` when no condition / loop is
  involved. Enabler: detect single inner-call without control-flow
  tokens.
- **`Run Keyword If    True/False    ...`** — constant condition →
  always / never. Enabler: parsed condition + literal detection.
- **Suggest `Test Template` when the same keyword repeats** across
  multiple tests in a section with only data differing. Enabler: walk
  `TestCaseSection.body`'s definition blocks and compare.
- **Empty `[Setup]    NONE` flag** — informational hint that this
  explicitly disables an inherited setup. Enabler: the analyzer already
  recognises `NONE` as the no-fixture marker.

### Document Symbols / Outline / Folding

- **Block-aware outline** — `FOR`, `WHILE`, `IF`, `TRY`, `GROUP` appear
  as nested foldable nodes inside the test/keyword they belong to.
  Enabler: `SemanticBlock.body` already encodes the nesting; folding
  ranges fall straight out of `block.line_start` / `line_end`.
- **GROUP blocks (RF 7.3+)** as named foldable regions. Enabler:
  `GroupBlock` is its own block class.

### Code Lens

- **Reference counts on keyword/test definitions** ("3 references").
  Enabler: `keyword_references` already aggregated; the
  `DefinitionBlock` gives the anchor line.
- **"Used in N tests"** lens above a tag in `[Tags]`. Enabler:
  `keyword_tag_references` / `testcase_tag_references`.

### Document Highlight

- **Scope-aware variable highlight** — clicking `${x}` highlights only
  the references in the same `DefinitionBlock`, not identically-named
  variables in unrelated tests / keywords. Enabler:
  `enclosing_definition_block(node)` + `local_variables`.

### Rename

- **Tag rename** across the workspace. Enabler: tag-reference dicts.
- **Library-alias rename** — change `Library    X    WITH NAME    Foo`
  and update every `Foo.Keyword` call. Enabler:
  `KeywordCallStatement.lib_entry` exposes the aliasing entry directly.
- **Scope-confined variable rename** — `${x}` defined inside a keyword
  doesn't leak to other definitions. Enabler:
  `DefinitionBlock.local_variables` keeps the boundaries explicit.

### Workspace-Level Features

- **Call Hierarchy** (already P1 in Phase 5) — bottom-up via
  `keyword_references`; top-down via walking `DefinitionBlock.body` for
  `KeywordCallStatement`s plus `RunKeywordCallStatement.inner_calls`.
- **Test impact graph** — for a changed keyword, list every test whose
  call chain reaches it. Enabler: same data as Call Hierarchy, just
  reversed reachability.
