# mypy: disable-error-code="attr-defined"

import os

__all__ = ["pid_exists"]

if os.name == "posix":

    def pid_exists(pid: int) -> bool:
        import errno

        if pid < 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError as e:
            return e.errno == errno.EPERM
        else:
            return True

else:

    def pid_exists(pid: int) -> bool:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        synchronize: int = 0x100000

        process = kernel32.OpenProcess(synchronize, 0, pid)
        if process != 0:
            kernel32.CloseHandle(process)
            return True
        return False
