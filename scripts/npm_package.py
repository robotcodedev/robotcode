from subprocess import run


def main() -> None:
    run(["npm", "run", "package"], shell=True).check_returncode()


if __name__ == "__main__":
    main()
