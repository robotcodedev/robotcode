from subprocess import run

from scripts.tools import get_current_version_from_git


def main() -> None:
    version = get_current_version_from_git()
    alias = "latest"

    if version.prerelease:
        version = version.next_minor()
        alias = "dev"

    version.major, version.minor

    run(
        "mike deploy --push --update-aliases --rebase --force "
        f'--title "v{version.major}.{version.minor}.x ({alias})" {version.major}.{version.minor} {alias}',
        shell=True,
    ).check_returncode()


if __name__ == "__main__":
    main()
