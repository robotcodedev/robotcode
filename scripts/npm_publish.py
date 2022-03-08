from subprocess import run


def main() -> None:
    run(["npm", "run", "publish"], shell=True).check_returncode()


if __name__ == "__main__":
    main()
