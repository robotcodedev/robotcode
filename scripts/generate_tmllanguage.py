from pathlib import Path
from string import Template
from typing import Dict, List, Type, cast

from robot.conf.languages import Language
from robot.utils import normalize


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

template = Template(Path("syntaxes/robotframework.tmLanguage.template.json").read_text(encoding="utf-8"))

result = template.safe_substitute(
    {
        "variables_header": "|".join(variables_header),
        "settings_header": "|".join(settings_header),
        "test_cases_header": "|".join(test_cases_header),
        "tasks_header": "|".join(tasks_header),
        "keywords_header": "|".join(keywords_header),
        "comments_header": "|".join(comments_header),
        "documentation_setting": "|".join(documentation_setting),
    }
)

Path("syntaxes/robotframework.tmLanguage.json").write_text(result, encoding="utf-8")
