import sys
from subprocess import run


def main() -> int:
    args = f"npm run {' '.join(sys.argv[1:])}"
    return run(args, shell=True).returncode


if __name__ == "__main__":
    main()
