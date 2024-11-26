import os
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable, List, Literal, Optional, Union

from .path import same_file


class ChDir(AbstractContextManager[Any]):
    def __init__(
        self, path: "Union[str, os.PathLike[str], None]", verbose_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        self.path = path
        self._old_cwd: List[Optional[Path]] = []
        self._verbose_callback = verbose_callback

    def __enter__(self) -> Optional[Path]:
        result = Path.cwd()

        if self.path is None or (self._old_cwd and same_file(self.path, Path.cwd())):
            self._old_cwd.append(None)
        else:
            self._old_cwd.append(result)

            if self.path:
                if self._verbose_callback:
                    self._verbose_callback(f"Changing directory to {self.path}")

                os.chdir(self.path)

        return result

    def __exit__(self, _exc_type: Any, _exc_value: Any, _traceback: Any) -> Literal[False]:
        old_path = self._old_cwd.pop()
        if old_path is not None:
            if self._verbose_callback:
                self._verbose_callback(f"Changing directory back to {old_path}")

            os.chdir(old_path)

        return False


chdir = ChDir
