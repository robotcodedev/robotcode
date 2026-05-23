"""prompt_toolkit-driven pieces used by `PromptToolkitConsoleInterpreter`.

Five leaf modules: `lexer` (RobotLexer for the prompt), `doc_viewer`
(standalone markdown viewer Application), `components` (completer,
key-bindings, style sheet, toolbar), `completion` (Robot-aware
candidate generation), `history` (history file path + size cap).
Plain mode (`ConsoleInterpreter`) never reaches into this package.
"""
