import contextlib
import re
import sys
from pathlib import Path

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from scripts.tools import get_version

# GitHub rejects longer release notes
MAX_LENGTH = 125000

FOOTER = (
    "This list shows only the features, bug fixes and performance improvements. "
    "See the [full list of changes](https://github.com/robotcodedev/robotcode/blob/main/CHANGELOG.md)."
)


def shorten(notes: str) -> str:
    # like the change notes of the PyCharm plugin: only the subject lines of what users notice, as many as fit, each
    # with the headings of its type and its scope; git-cliff writes the type headings with an ordering prefix, like
    # "### <!-- 0 -->Features", and subject lines without indentation
    subjects: list[tuple[str, str | None, str]] = []
    type_heading = ""
    scope_heading: str | None = None
    for line in notes.splitlines():
        if line.startswith("### "):
            type_heading, scope_heading = line, None
        elif line.startswith("#### "):
            scope_heading = line
        elif line.startswith("- ") and type_heading.partition("-->")[2].strip() in (
            "Features",
            "Bug Fixes",
            "Performance",
        ):
            subjects.append((type_heading, scope_heading, line))

    def outline(count: int) -> str:
        lines: list[str] = []
        last_type: str | None = None
        last_scope: str | None = None
        for subject_type, subject_scope, subject in subjects[:count]:
            headings = []
            if subject_type != last_type:
                headings.append(subject_type)
                last_type, last_scope = subject_type, None
            if subject_scope is not None and subject_scope != last_scope:
                headings.append(subject_scope)
            last_scope = subject_scope
            for heading in headings:
                if lines and lines[-1]:
                    lines.append("")
                lines += [heading, ""]
            lines.append(subject)
        return "\n".join([*lines, "", FOOTER]).strip()

    return next(text for text in map(outline, range(len(subjects), -1, -1)) if len(text) <= MAX_LENGTH)


def main() -> None:
    version = get_version()

    changelog = Path("CHANGELOG.md").read_text()
    if version.prerelease:
        version = "Unreleased"

    regex = re.compile(
        rf"^\#\#\s*\[({version})\][^\n]*?\n(?P<text>.*?)^\#\#\s+",
        re.MULTILINE | re.DOTALL,
    )

    for match in regex.finditer(changelog):
        notes = match.group("text").strip()
        print(notes if len(notes) <= MAX_LENGTH else shorten(notes))


if __name__ == "__main__":
    main()
