from scripts.tools import get_version


def main() -> None:

    version = get_version()

    preview = version.minor % 2 != 0

    print(str(preview).lower())


if __name__ == "__main__":
    main()
