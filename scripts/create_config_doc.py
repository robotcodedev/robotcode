import contextlib
import os
import re
import subprocess
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


from scripts.create_robot_toml_json_schema import _to_anchor

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
FENCE = re.compile(r"^\s*(```+|~~~+)")


def generate() -> str:
    """The settings as `robotcode config info desc` describes them, without its H1; every setting heading gets the
    ID that the documentation links of the JSON schema point to."""
    desc = subprocess.run(
        [sys.executable, "-m", "robotcode.cli", "--no-color", "config", "info", "desc"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    ).stdout

    lines = desc.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("`robotcode config info desc` does not start with an H1")

    result = []
    fence = None
    for line in lines[1:]:
        if fence is None:
            m = FENCE.match(line)
            if m:
                fence = m.group(1)
            elif line.startswith("## "):
                line = f"{line} {{#{_to_anchor(line[3:])}}}"
        elif line.strip().startswith(fence):
            fence = None
        result.append(line)

    return "\n".join(result).strip("\n") + "\n"


def main() -> None:
    config_doc = Path("docs/src/content/docs/reference/config.md")

    # The frontmatter is maintained in the page.
    frontmatter = FRONTMATTER.match(config_doc.read_text("utf-8"))
    if frontmatter is None:
        raise SystemExit(f"{config_doc}: no frontmatter")

    config_doc.write_text(f"{frontmatter.group(0)}\n{generate()}", "utf-8")


if __name__ == "__main__":
    main()
