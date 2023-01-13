from scripts.tools import get_version


def main() -> None:

    version = get_version()
    if version.prerelease:
        preview = 1
    else:
        preview = 0

    print(preview)


if __name__ == "__main__":
    main()
