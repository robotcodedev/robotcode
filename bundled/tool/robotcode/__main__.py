import os
import pathlib
import site
import sys


def update_sys_path(path_to_add: str, strategy: str) -> None:
    if path_to_add not in sys.path and pathlib.Path(path_to_add).is_dir():
        if any(p for p in pathlib.Path(path_to_add).iterdir() if p.suffix == ".pth"):
            old_sys_path = list(sys.path)
            site.addsitedir(path_to_add)
            if strategy == "useBundled":
                # addsitedir appends, which would let packages from the environment win over the bundled ones
                sys.path[:] = [p for p in sys.path if p not in old_sys_path] + old_sys_path
            return

        if strategy == "useBundled":
            sys.path.insert(0, path_to_add)
        elif strategy == "fromEnvironment":
            sys.path.append(path_to_add)


if __name__ == "__main__":
    update_sys_path(
        os.fspath(pathlib.Path(__file__).parent.parent.parent / "libs"),
        os.getenv("LS_IMPORT_STRATEGY", "useBundled"),
    )

    from robotcode.cli import robotcode

    robotcode(
        windows_expand_args=False,
        default_map={"launcher_script": str(pathlib.Path(__file__).parent)},
    )
