from pathlib import Path
from string import Template
from typing import Dict, List, Type, cast

from robot.conf.languages import Language
from robot.utils import normalize

from robotcode.robot.utils import RF_VERSION


def get_available_languages() -> "Dict[str, Type[Language]]":
    available = {}
    for lang in Language.__subclasses__():
        available[normalize(cast(str, lang.code), ignore="-")] = lang
        # available[normalize(cast(str, lang.name))] = lang
    if "" in available:
        available.pop("")
    return available


variables_header: List[str] = []
settings_header: List[str] = []
test_cases_header: List[str] = []
tasks_header: List[str] = []
keywords_header: List[str] = []
comments_header: List[str] = []
documentation_setting: List[str] = []
library_setting: List[str] = []
arguments_setting: List[str] = []

for k in get_available_languages():
    lang = Language.from_name(k)
    if lang.variables_header:
        v = lang.variables_header.lower()
        if k == "en":
            v = v + "?"
        if v not in variables_header:
            variables_header.append(v)

    if lang.settings_header:
        v = lang.settings_header.lower()
        if k == "en":
            v = v + "?"
        if v not in settings_header:
            settings_header.append(v)

    if lang.test_cases_header:
        v = lang.test_cases_header.lower()
        if k == "en":
            v = v + "?"
        if v not in test_cases_header:
            test_cases_header.append(v)

    if lang.tasks_header:
        v = lang.tasks_header.lower()
        if k == "en":
            v = v + "?"
        if v not in tasks_header:
            tasks_header.append(v)

    if lang.keywords_header:
        v = lang.keywords_header.lower()
        if k == "en":
            v = v + "?"
        if v not in keywords_header:
            keywords_header.append(v)

    if lang.comments_header:
        v = lang.comments_header.lower()
        if k == "en":
            v = v + "?"
        if v not in comments_header:
            comments_header.append(v)

    if lang.documentation_setting:
        v = lang.documentation_setting.lower()
        if v not in documentation_setting:
            documentation_setting.append(v)

    if lang.library_setting:
        v = lang.library_setting.lower()
        if v not in library_setting:
            library_setting.append(v)

    if lang.arguments_setting:
        v = lang.arguments_setting.lower()
        if v not in arguments_setting:
            arguments_setting.append(v)

    # Terms deprecated by Robot Framework (7.5 or newer) are still accepted, so they
    # stay in the grammar: `{deprecated term: (new term, version)}`.
    if RF_VERSION >= (7, 5):
        for old_term, (new_term, _) in lang.deprecations.items():
            for attribute, terms in (
                ("variables_header", variables_header),
                ("settings_header", settings_header),
                ("test_cases_header", test_cases_header),
                ("tasks_header", tasks_header),
                ("keywords_header", keywords_header),
                ("comments_header", comments_header),
                ("documentation_setting", documentation_setting),
                ("library_setting", library_setting),
                ("arguments_setting", arguments_setting),
            ):
                if getattr(lang, attribute) == new_term and old_term.lower() not in terms:
                    terms.append(old_term.lower())

# Terms of older Robot Framework versions that newer versions no longer accept. RobotCode supports these
# versions, so the grammar keeps the terms.
for old_term, terms in (
    ("sleutelwoorden", keywords_header),  # Dutch, Robot Framework 6.0 to 7.0
):
    if old_term not in terms:
        terms.append(old_term)

template = Template(Path("syntaxes/robotframework.tmLanguage.template.json").read_text(encoding="utf-8"))

headers = {
    "variables_header": "|".join(variables_header),
    "settings_header": "|".join(settings_header),
    "test_cases_header": "|".join(test_cases_header),
    "tasks_header": "|".join(tasks_header),
    "keywords_header": "|".join(keywords_header),
    "comments_header": "|".join(comments_header),
    "documentation_setting": "|".join(documentation_setting),
    "library_setting": "|".join(library_setting),
    "arguments_setting": "|".join(arguments_setting),
}

# lines that continue a setting, test, task or keyword: `...` continuations, comments and empty lines
continuation = r"(\\s*(\\.\\.\\.((( {2}| ?\\t)\\s*\\S.*)|(\\s*))?$))|(\\s*#.*$)|(\\s*$)"


def json_lines(*items: str) -> str:
    return ",\n".join(f"        {item}" for item in items)


# a file with sections, such as a .robot or .resource file
suite = {
    "top_patterns": json_lines(
        *(
            f'{{ "include": "#{rule}" }}'
            for rule in (
                "comment_line",
                "settings_section",
                "variables_section",
                "testcases_section",
                "tasks_section",
                "keywords_section",
                "comments_section",
                "section",
                "block_comment",
            )
        )
    ),
    "indent_quantifier": "",
    "name": "Robot Framework",
    "file_types": json_lines('"robotframework"', '"robot"'),
    "aliases": json_lines('"robot"', '"robotframework"'),
}

# Markdown lists and block quotes consume their prefix before the code block content is matched, so the
# grammar for the Markdown code block injection also matches right after that prefix and continues blocks
# with `while` rules. IntelliJ's TextMate implementation rejects that variable-length look-behind (Joni)
# and overflows its stack on these `while` rules, so Robot Framework files get line anchors and `end` rules.
for path, values in (
    (
        "syntaxes/robotframework.tmLanguage.json",
        {
            **suite,
            "scope_name": "source.robotframework",
            "line_start": "^",
            "line_start_indented": "^",
            "block_continuation": f'"end": "^(?!{continuation})"',
        },
    ),
    (
        "syntaxes/robotframework-markdown.tmLanguage.json",
        {
            **suite,
            "scope_name": "source.robotframework-markdown",
            "line_start": r"(?:^|\\G(?<=^[ \\t>]*))",
            "line_start_indented": r"(?:^|\\G(?<=^[ \\t>]*)[ \\t]*)",
            "block_continuation": rf'"while": "(?:^|\\G(?<=^[ \\t>]*))(?={continuation})"',
        },
    ),
    # REPL scripts and notebook cells hold only statements, which need no indentation
    (
        "syntaxes/robotframework-repl.tmLanguage.json",
        {
            "top_patterns": json_lines('{ "include": "#comment_line" }', '{ "include": "#block_statements" }'),
            "indent_quantifier": "?",
            "name": "Robot Framework REPL",
            "file_types": json_lines('"robotframework-repl"', '"robot-repl"'),
            "aliases": json_lines('"robot-repl"', '"robotframework-repl"'),
            "scope_name": "source.robotframework-repl",
            "line_start": "^",
            "line_start_indented": "^",
            "block_continuation": f'"end": "^(?!{continuation})"',
        },
    ),
):
    Path(path).write_text(template.safe_substitute(headers, **values), encoding="utf-8")
