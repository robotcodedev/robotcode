import contextlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__" and not __package__:
    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[1]

    if str(top) not in sys.path:
        sys.path.append(str(top))

    with contextlib.suppress(ValueError):
        sys.path.remove(str(parent))

    __package__ = "scripts"


from scripts.tools import get_version


def replace_in_file(filename: Path, pattern: "re.Pattern[str]", to: str) -> None:
    text = filename.read_text()
    new = pattern.sub(to, text)
    filename.write_text(new)


def run(title: str, *args: Any, **kwargs: Any) -> None:
    try:
        print(f"running {title}")
        subprocess.run(*args, **kwargs)
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as e:
        print(f"{title} failed: {e}", file=sys.stderr)


def main() -> None:
    version = get_version()
    version_files = list(Path("packages").rglob("__version__.py"))

    for f in [Path("src/robotcode/cli/__version__.py"), *version_files]:
        replace_in_file(
            f,
            re.compile(r"""(^_*version_*\s*=\s*['"])([^'"]*)(['"])""", re.MULTILINE),
            rf"\g<1>{version or ''}\g<3>",
        )

    # replace_in_file(
    #     Path("package.json"),
    #     re.compile(
    #         r"""(\"version\"\s*:\s*['"])([0-9]+\.[0-9]+\.[0-9]+.*)(['"])""",
    #         re.MULTILINE,
    #     ),
    #     rf"\g<1>{version or ''}\g<3>",
    # )

    run(
        "npm version",
        f"npm --no-git-tag-version version {version}",
        shell=True,
        timeout=600,
    )

    pyproject_files = list(Path("packages").rglob("pyproject.toml"))

    for f in [Path("pyproject.toml"), *pyproject_files]:
        replace_in_file(
            f,
            re.compile(r'("robotcode\S*==)([0-9]+\.[0-9]+\.[0-9]+.*)(")', re.MULTILINE),
            rf"\g<1>{version or ''}\g<3>",
        )


if __name__ == "__main__":
    main()
