from scripts.tools import get_version


def main() -> None:

    version = get_version()
    preview = 1 if version.prerelease else 0

    print(preview)


if __name__ == "__main__":
    main()
