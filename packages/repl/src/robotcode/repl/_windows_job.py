"""Windows job objects, by which `session start` ends a session process together with the processes it has started, as
the process group does on Linux and macOS."""

import _winapi
import ctypes
import sys
from ctypes import wintypes

assert sys.platform == "win32"

CREATE_SUSPENDED = 0x00000004

_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001
_TH32CS_SNAPTHREAD = 0x00000004
_THREAD_SUSPEND_RESUME = 0x0002
_INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
_RESUME_FAILED = 0xFFFFFFFF


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _ThreadEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
_kernel32.CreateJobObjectW.restype = wintypes.HANDLE
_kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD)
_kernel32.SetInformationJobObject.restype = wintypes.BOOL
_kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
_kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
_kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
_kernel32.TerminateJobObject.restype = wintypes.BOOL
_kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel32.Thread32First.argtypes = (wintypes.HANDLE, ctypes.POINTER(_ThreadEntry))
_kernel32.Thread32First.restype = wintypes.BOOL
_kernel32.Thread32Next.argtypes = (wintypes.HANDLE, ctypes.POINTER(_ThreadEntry))
_kernel32.Thread32Next.restype = wintypes.BOOL
_kernel32.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
_kernel32.OpenThread.restype = wintypes.HANDLE
_kernel32.ResumeThread.argtypes = (wintypes.HANDLE,)
_kernel32.ResumeThread.restype = wintypes.DWORD


def _error() -> OSError:
    return ctypes.WinError(ctypes.get_last_error())


def _set_limits(job: int, flags: int) -> None:
    info = _ExtendedLimitInformation()
    info.BasicLimitInformation.LimitFlags = flags
    if not _kernel32.SetInformationJobObject(
        job, _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)
    ):
        raise _error()


def job_with(pid: int) -> int:
    """A new job with the process `pid` in it, and every process it starts from then on. The processes of the job may
    start processes outside of it, as some programs ask for; a job that forbids it makes their `CreateProcess` fail.

    Until `release`, Windows ends the processes of the job once its handle is closed, also when this process ends in
    whatever way."""
    job = _kernel32.CreateJobObjectW(None, None)
    if not job:
        raise _error()
    try:
        _set_limits(job, _JOB_OBJECT_LIMIT_BREAKAWAY_OK | _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
        process = _winapi.OpenProcess(_PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, pid)
        try:
            if not _kernel32.AssignProcessToJobObject(job, process):
                raise _error()
        finally:
            _winapi.CloseHandle(process)
    except BaseException:
        _winapi.CloseHandle(job)
        raise
    return int(job)


def resume(pid: int) -> None:
    """Let the process `pid`, started with `CREATE_SUSPENDED`, run: `subprocess` closes the handle of its thread, so
    the thread is found by the process ID."""
    snapshot = _kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPTHREAD, 0)
    if snapshot == _INVALID_HANDLE_VALUE:
        raise _error()
    try:
        entry = _ThreadEntry()
        entry.dwSize = ctypes.sizeof(entry)
        resumed = 0
        found = _kernel32.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == pid:
                thread = _kernel32.OpenThread(_THREAD_SUSPEND_RESUME, False, entry.th32ThreadID)
                if not thread:
                    raise _error()
                try:
                    if _kernel32.ResumeThread(thread) == _RESUME_FAILED:
                        raise _error()
                finally:
                    _winapi.CloseHandle(thread)
                resumed += 1
            found = _kernel32.Thread32Next(snapshot, ctypes.byref(entry))
        if not resumed:
            raise OSError(f"Found no thread of process {pid} to resume.")
    finally:
        _winapi.CloseHandle(snapshot)


def release(job: int) -> None:
    """Let the processes of `job` run on once its handle is closed."""
    _set_limits(job, _JOB_OBJECT_LIMIT_BREAKAWAY_OK)


def terminate(job: int) -> None:
    """End every process in `job`."""
    if not _kernel32.TerminateJobObject(job, 1):
        raise _error()
