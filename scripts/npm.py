import sys
from subprocess import run


def main() -> None:
    run(f"npm run {' '.join(sys.argv[1:])}", shell=True).check_returncode()


if __name__ == "__main__":
    main()
