"""Connection-bound admission for the disposable D3c Unix SQLite profile.

Python's sqlite3 exposes neither the opened descriptor nor file_control().
Observe Unix SQLite's *actual* fstat descriptor using the public VFS v3 syscall
interface, not a pathname stat, a copied DB marker, or CPython/unixFile layouts.
No hook is installed by importing this module. Unsupported platforms fail shut.
"""

import atexit
from contextlib import contextmanager
import ctypes
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Lock

import _sqlite3

from isolated_sync.canonical import fail


class _VFS(ctypes.Structure):
    # Public sqlite3_vfs v3 ABI; function fields not called here are opaque.
    _fields_ = [("iVersion", ctypes.c_int), ("szOsFile", ctypes.c_int), ("mxPathname", ctypes.c_int),
                ("pNext", ctypes.c_void_p), ("zName", ctypes.c_char_p), ("pAppData", ctypes.c_void_p)] + [
        (name, ctypes.c_void_p) for name in (
            "xOpen", "xDelete", "xAccess", "xFullPathname", "xDlOpen", "xDlError", "xDlSym", "xDlClose",
            "xRandomness", "xSleep", "xCurrentTime", "xGetLastError", "xCurrentTimeInt64",
            "xSetSystemCall", "xGetSystemCall", "xNextSystemCall")]


_Get = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p)
_Set = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p)
_lock = Lock()
_installed = None

# Build-embedded source: the existing financial_engine source manifest includes
# these exact bytes. Compiled only for an explicitly owned synthetic profile.
_NATIVE_SOURCE = r"""
#include <errno.h>
#include <stdint.h>
#include <sys/stat.h>
typedef int (*fstat_fn)(int, struct stat *);
static fstat_fn delegate;
static _Thread_local struct {
    uint64_t dev, ino;
    int active, fd, failed;
} witness;
void mn_owned_configure(fstat_fn fn) { delegate = fn; }
int mn_owned_begin(uint64_t dev, uint64_t ino) {
    if (witness.active) return -1;
    witness.dev = dev;
    witness.ino = ino;
    witness.fd = -1;
    witness.failed = 0;
    witness.active = 1;
    return 0;
}
int mn_owned_fstat(int fd, struct stat *buffer) {
    int rc = delegate(fd, buffer);
    if (witness.active) {
        if (rc || (uint64_t)buffer->st_dev != witness.dev ||
            (uint64_t)buffer->st_ino != witness.ino ||
            (witness.fd >= 0 && witness.fd != fd)) {
            witness.failed = 1;
            errno = EACCES;
            return -1;
        }
        witness.fd = fd;
    }
    return rc;
}
int mn_owned_end(void) {
    int fd = witness.active && !witness.failed ? witness.fd : -1;
    witness.active = 0;
    return fd;
}
"""


def _install():
    global _installed
    with _lock:
        if _installed is not None:
            return _installed
        # The fstat/open relationship below is reviewed against Unix 3.45.1.
        # Never silently broaden native ABI/platform admission on an upgrade.
        if sys.platform != "linux" or sqlite3.sqlite_version_info != (3, 45, 1):
            fail("REJECT_SYNTHETIC_OWNERSHIP_PLATFORM")
        lib = ctypes.CDLL(_sqlite3.__file__)
        lib.sqlite3_vfs_find.argtypes = [ctypes.c_char_p]
        lib.sqlite3_vfs_find.restype = ctypes.POINTER(_VFS)
        vfs = lib.sqlite3_vfs_find(None)
        if (not vfs or vfs.contents.iVersion != 3 or vfs.contents.zName != b"unix" or
                not vfs.contents.xGetSystemCall or not vfs.contents.xSetSystemCall):
            fail("REJECT_SYNTHETIC_OWNERSHIP_PLATFORM")
        get, set_ = _Get(vfs.contents.xGetSystemCall), _Set(vfs.contents.xSetSystemCall)
        original = get(vfs, b"fstat")
        if not original:
            fail("REJECT_SYNTHETIC_OWNERSHIP_PLATFORM")
        # Explicit synthetic profile only. No Python callback under SQLite's
        # native inode mutex (including GC/finalizer/GIL reentrancy). Compile a
        # tiny host-ABI shim, not SQLite itself or a new Python/native package.
        temporary = TemporaryDirectory(prefix="money-note-gc-witness-")
        binary = Path(temporary.name)/"owned.so"
        try:
            subprocess.run(["/usr/bin/cc", "-std=c11", "-shared", "-fPIC", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-x", "c", "-", "-o", str(binary)], input=_NATIVE_SOURCE.encode("ascii"),
                           check=True, capture_output=True, timeout=30, env={"PATH": "/usr/bin:/bin"})
            native = ctypes.CDLL(str(binary))
        except (OSError, subprocess.SubprocessError):
            temporary.cleanup()
            fail("REJECT_SYNTHETIC_OWNERSHIP_PLATFORM")
        native.mn_owned_configure.argtypes = [ctypes.c_void_p]
        native.mn_owned_configure.restype = None
        native.mn_owned_begin.argtypes = [ctypes.c_uint64, ctypes.c_uint64]
        native.mn_owned_begin.restype = ctypes.c_int
        native.mn_owned_end.argtypes = []
        native.mn_owned_end.restype = ctypes.c_int
        native.mn_owned_configure(original)
        pointer = ctypes.cast(native.mn_owned_fstat, ctypes.c_void_p).value
        if set_(vfs, b"fstat", pointer) != 0:
            fail("REJECT_SYNTHETIC_OWNERSHIP_PLATFORM")
        # Keep the native library alive while SQLite can call it. No hook
        # replacement per request, no process-wide admission lock/FD scanning.
        _installed = (lib, vfs, get, set_, original, native, temporary, pointer)

        def restore():
            if get(vfs, b"fstat") == pointer:
                set_(vfs, b"fstat", original)
        atexit.register(restore)
        return _installed


@contextmanager
def opened_identity(expected):
    """Observe only the current thread's one sqlite3.connect() native open.

Unix findInodeInfo fstats the main FD, including a reused UnixUnusedFd. An
absent, failed, ambiguous, or mismatching observation never admits a connection.
Other threads and non-admitted SQLite calls delegate fstat without inspection.
"""
    lib, vfs, get, _, _, native, _, pointer = _install()
    current = lib.sqlite3_vfs_find(None)
    if (not current or ctypes.addressof(current.contents) != ctypes.addressof(vfs.contents) or
            get(vfs, b"fstat") != pointer or native.mn_owned_begin(*expected) != 0):
        fail("REJECT_SYNTHETIC_OWNERSHIP_HOOK")
    scope = [expected, None, False]
    try:
        try:
            yield scope
        except sqlite3.Error:
            if native.mn_owned_end() < 0:
                fail("REJECT_SYNTHETIC_OWNERSHIP")
            raise
        scope[1] = native.mn_owned_end()
        if scope[1] < 0:
            fail("REJECT_SYNTHETIC_OWNERSHIP")
    finally:
        native.mn_owned_end()


def assert_identity(fd, expected):
    try:
        stat = os.fstat(fd)
        if (stat.st_dev, stat.st_ino) == expected:
            return
    except OSError:
        pass
    fail("REJECT_SYNTHETIC_OWNERSHIP")
