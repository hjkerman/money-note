"""D3C-A01 독립 재감사. 새 disposable DB만 사용하며 구현 source는 바꾸지 않는다."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing, contextmanager
import ctypes
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
from threading import Barrier
import time
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docs/benchmarks/t66d3c-audit"))
import test_audit as prior  # noqa: E402
from isolated_sync import owned_sqlite, retention_schema  # noqa: E402

REAL_CONNECT = sqlite3.connect
OUT = Path("/tmp/mn-d3c-a01-reaudit")
OUT.mkdir(exist_ok=True)
template = prior.template
db = prior.db


def identity(path):
    st = Path(path).stat()
    return (st.st_dev, st.st_ino)


def snapshot(path):
    """다른 helper를 거치지 않고 fresh SQLite connection으로 모든 persisted rows를 읽는다."""
    with closing(REAL_CONNECT(path, timeout=2)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        names = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        result = {
            t: sorted(conn.execute('SELECT * FROM "' + t + '"').fetchall(), key=repr)
            for t in names
        }
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        conn.rollback()
        return result


def objects(state):
    return {r[0] for r in state["sync_objects"]}


def record(name, **observed):
    value = dict(
        scenario=name, result="PASS", unauthorized_committed_deletions=0, **observed
    )
    (OUT / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2))


@contextmanager
def clone(db):
    with prior.RetentionSandbox() as other:
        with (
            closing(REAL_CONNECT(db.path)) as source,
            closing(REAL_CONNECT(other.path)) as target,
        ):
            source.backup(target)
        other.install()
        assert identity(db.path) != identity(other.path)
        yield other


@contextmanager
def swapped(db, other, mode):
    original = db.path
    saved = original.with_name("independent-owned-held.sqlite3")
    original.rename(saved)
    if mode == "symlink":
        original.symlink_to(other.path)
    else:
        other.path.replace(original)
    try:
        yield saved
    finally:
        if mode == "symlink":
            original.unlink()
        else:
            original.replace(other.path)
        saved.rename(original)


@pytest.mark.parametrize("when", ["before", "after", "aba"])
@pytest.mark.parametrize("mode", ["symlink", "atomic"])
def test_independent_open_replacement(db, when, mode):
    for n in (1, 2, 3):
        prior.mutate(db, n)
    gc = prior.Collector(prior.repository(db))
    mark = gc.mark()
    before_a = snapshot(db.path)
    with clone(db) as other:
        before_b = snapshot(other.path)
        identities = dict(
            authorized=identity(db.path), replacement=identity(other.path)
        )
        armed = [True]
        with ExitStack() as stack:

            def opening(path, *args, **kwargs):
                if Path(path) != db.path or not armed[0]:
                    return REAL_CONNECT(path, *args, **kwargs)
                armed[0] = False
                if when == "after":
                    connection = REAL_CONNECT(path, *args, **kwargs)
                swap = swapped(db, other, mode)
                stack.enter_context(swap)
                if when == "after":
                    return connection
                try:
                    return REAL_CONNECT(path, *args, **kwargs)
                finally:
                    if when == "aba":
                        stack.close()

            with patch.object(retention_schema.sqlite3, "connect", opening):
                with pytest.raises(prior.CanonicalError, match="OWNERSHIP") as rejected:
                    gc.sweep(mark, batch=1)
        after_a, after_b = snapshot(db.path), snapshot(other.path)
        assert after_b == before_b and after_a == before_a and not armed[0]
        prior.check_current(db)
        record(
            "swap_" + when + "_" + mode,
            identities=identities,
            original_count=len(objects(before_a)),
            replacement_count=len(objects(before_b)),
            replacement_deleted=sorted(objects(before_b) - objects(after_b)),
            error=str(rejected.value),
        )


def test_independent_between_batches_and_new_connection(db):
    prior.mutate(db)
    gc = prior.Collector(prior.repository(db))
    before = snapshot(db.path)
    result, following = gc.sweep(gc.mark(), batch=1)
    authorized = snapshot(db.path)
    assert len(objects(before) - objects(authorized)) == result["objects_deleted"] == 1
    with clone(db) as other:
        before_b = snapshot(other.path)
        with swapped(db, other, "atomic"):
            with pytest.raises(prior.CanonicalError, match="OWNERSHIP"):
                gc.sweep(following, batch=1)
            with pytest.raises(prior.CanonicalError, match="OWNERSHIP"):
                db.connect()
        assert snapshot(other.path) == before_b and snapshot(db.path) == authorized
    record(
        "between_batches", authorized_prior_deletions=1, unauthorized_later_deletions=0
    )


def test_same_inode_hardlink_alias_is_positive_identity(db):
    alias = db.path.with_name("same-inode.sqlite3")
    os.link(db.path, alias)
    before = snapshot(db.path)
    try:
        with patch.object(type(db), "path", property(lambda self: alias)):
            with closing(db.connect()) as conn:
                assert conn._ownership[2] == identity(alias) == db._owned_file
                conn.execute("BEGIN IMMEDIATE")
                conn.commit()
    finally:
        alias.unlink()
    assert snapshot(db.path) == before
    record("hardlink_alias", same_inode_authorized=True, maintenance_changes=0)


def test_open_fd_is_main_and_live_until_connection_close(db):
    with closing(db.connect()) as conn:
        fd, expected = conn._ownership[1:]
        assert fd != db._identity_fd
        assert identity("/proc/self/fd/" + str(fd)) == expected == db._owned_file
        assert os.readlink("/proc/self/fd/" + str(fd)) == str(db.path)
        assert conn.execute("PRAGMA database_list").fetchall()[0][1] == "main"
        actual_fd = fd
    # No other DB connection is active: the SQLite FD must not be usable now.
    with pytest.raises(OSError):
        os.fstat(actual_fd)
    assert identity("/proc/self/fd/" + str(db._identity_fd)) == db._owned_file
    record(
        "main_fd_lifetime",
        sqlite_fd=actual_fd,
        anchor_fd=db._identity_fd,
        sqlite_fd_closed=True,
        anchor_kept=True,
    )


def test_closed_connection_and_fd_number_reuse_cannot_authorize_sql(db, tmp_path):
    conn = db.connect()
    fd = conn._ownership[1]
    conn.close()
    unrelated = tmp_path / "unrelated-disposable-file"
    unrelated.write_bytes(b"independent audit")
    replacement_fd = os.open(unrelated, os.O_RDWR)
    try:
        # Kernel normally reuses the lowest free number; dup2 is never used on a live SQLite FD.
        with pytest.raises(prior.CanonicalError, match="OWNERSHIP"):
            owned_sqlite.assert_identity(replacement_fd, db._owned_file)
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("DELETE FROM sync_objects")
    finally:
        os.close(replacement_fd)
    prior.check_current(db)
    record(
        "closed_fd_reuse",
        original_fd=fd,
        replacement_fd=replacement_fd,
        fd_number_reused=fd == replacement_fd,
        closed_sql_rejected=True,
    )


def test_commit_revalidates_after_delete_and_rolls_back(db):
    prior.mutate(db)
    gc = prior.Collector(prior.repository(db))
    before = snapshot(db.path)
    with clone(db) as other:
        before_b = snapshot(other.path)
        with ExitStack() as stack:

            def fault(stage, conn):
                if stage == "before_commit":
                    stack.enter_context(swapped(db, other, "atomic"))
                    assert conn._ownership[2] == identity(
                        "/proc/self/fd/" + str(conn._ownership[1])
                    )

            with pytest.raises(prior.CanonicalError, match="OWNERSHIP"):
                gc.sweep(gc.mark(), batch=1, fault=fault)
        assert snapshot(db.path) == before and snapshot(other.path) == before_b
    record(
        "commit_after_delete_revalidates", committed_deletions=0, rollback_verified=True
    )


def test_authorized_fd_stays_original_if_path_changes_after_last_check(db):
    prior.mutate(db)
    gc = prior.Collector(prior.repository(db))
    plan = gc.mark()
    before = snapshot(db.path)
    real_assert = prior.RetentionConnection._assert_owned
    armed = [False]
    fired = []
    with clone(db) as other:
        before_b = snapshot(other.path)
        with ExitStack() as stack:

            def checking(conn):
                real_assert(conn)
                if armed[0]:
                    armed[0] = False
                    stack.enter_context(swapped(db, other, "atomic"))
                    fired.append(
                        dict(
                            opened_identity=identity(
                                "/proc/self/fd/" + str(conn._ownership[1])
                            ),
                            visible_identity=identity(db.path),
                        )
                    )

            def fault(stage, conn):
                if stage == "before_commit":
                    armed[0] = True

            with patch.object(prior.RetentionConnection, "_assert_owned", checking):
                with pytest.raises(prior.CanonicalError, match="OWNERSHIP"):
                    gc.sweep(plan, batch=1, fault=fault)
        after = snapshot(db.path)
        assert len(objects(before) - objects(after)) == 1
        assert snapshot(other.path) == before_b
        assert fired[0]["opened_identity"] != fired[0]["visible_identity"]
        prior.check_current(db)
    record(
        "late_path_change",
        observations=fired,
        authorized_original_deletions=1,
        rejection_after_authorized_commit=True,
    )


def test_parallel_gc_and_tls_witness_are_database_specific(db):
    prior.mutate(db)
    with clone(db) as other:
        barrier = Barrier(2)
        before_a, before_b = snapshot(db.path), snapshot(other.path)

        def work(value):
            with closing(value.connect()) as conn:
                fd, expected = conn._ownership[1:]
                barrier.wait(10)
                assert (
                    identity("/proc/self/fd/" + str(fd))
                    == expected
                    == value._owned_file
                )
            return prior.Collector(prior.repository(value)).collect(
                apply=True, batch=1024
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(work, db)
            two = pool.submit(work, other)
            results = [one.result(30), two.result(30)]
        for value, before, result in zip((db, other), (before_a, before_b), results):
            after = snapshot(value.path)
            assert len(objects(before) - objects(after)) == result["objects_deleted"]
            prior.check_current(value)
        record(
            "parallel_tls_gc",
            distinct_identities=[db._owned_file, other._owned_file],
            actual_deletions=[r["objects_deleted"] for r in results],
        )


def test_wal_reader_checkpoint_and_repeated_connections(db):
    prior.mutate(db)
    before = snapshot(db.path)
    with closing(db.connect()) as reader:
        reader.execute("BEGIN")
        visible = reader.execute("SELECT count(*) FROM sync_objects").fetchone()[0]
        result = prior.Collector(prior.repository(db)).collect(apply=True, batch=1024)
        assert (
            reader.execute("SELECT count(*) FROM sync_objects").fetchone()[0] == visible
        )
        with closing(db.connect()) as writer:
            with writer._metadata():
                checkpoint = tuple(
                    writer.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
                )
            assert writer._ownership[2] == identity(
                "/proc/self/fd/" + str(writer._ownership[1])
            )
        reader.rollback()
    after = snapshot(db.path)
    assert len(objects(before) - objects(after)) == result["objects_deleted"]
    prior.check_current(db)
    record(
        "wal_reader_checkpoint",
        checkpoint=checkpoint,
        authorized_deletions=result["objects_deleted"],
        reader_snapshot_preserved=True,
    )


def test_legitimate_gc_has_independent_reachability_and_http_reconstruction(db):
    repo = prior.repository(db)
    observation = prior.create(repo)
    old_rows = prior.raw_state(db)
    for n in (1, 2, 3):
        prior.mutate(db, n)
    expected = prior.oracle(db)
    before = snapshot(db.path)
    result = prior.Collector(repo).collect(apply=True, batch=1024)
    after = snapshot(db.path)
    assert objects(before) - objects(after) == expected["candidates"]
    for name in (
        *prior.TABLES,
        "sync_commits",
        "sync_capture_commits",
        "sync_authority_fence",
        "sync_current",
        "sync_observations",
        "sync_observation_pins",
    ):
        assert before[name] == after[name]
    prior.check_current(db)
    rebuilt = prior.asyncio.run(
        prior.http_graph(prior.http.create_app(repo), observation, old_rows)
    )
    second = prior.Collector(repo).collect(apply=True)
    assert second["objects_deleted"] == second["rows_deleted"] == 0
    record(
        "legitimate_gc",
        authorized_deletions=result["objects_deleted"],
        retained_objects=len(expected["reachable"]),
        reconstruction=rebuilt,
        second_deletions=0,
    )


FAILURES = (
    "os",
    "version",
    "vfs",
    "compiler_missing",
    "compiler_execution",
    "compiler_result",
    "compiler_timeout",
    "helper_load",
    "hook",
    "fd",
    "library",
    "concurrent_initialization",
)


@pytest.mark.parametrize("mode", FAILURES)
def test_unsupported_or_failed_native_admission_is_fail_closed(db, mode, tmp_path):
    prior.mutate(db)
    before = snapshot(db.path)
    recv, send = multiprocessing.Pipe(duplex=False)

    def child():
        patches = ExitStack()
        restore_vfs = None
        try:
            installed = owned_sqlite._install()
            lib, vfs, get, set_, original, native, temporary, pointer = installed
            if mode not in ("hook", "fd"):
                patches.enter_context(patch.object(owned_sqlite, "_installed", None))
            if mode == "os":
                patches.enter_context(
                    patch.object(owned_sqlite.sys, "platform", "unsupported-audit")
                )
            elif mode == "version":
                patches.enter_context(
                    patch.object(owned_sqlite.sqlite3, "sqlite_version_info", (0, 0, 0))
                )
            elif mode == "vfs":
                alternate = lib.sqlite3_vfs_find(b"unix-dotfile")
                assert alternate
                lib.sqlite3_vfs_register.argtypes = [
                    ctypes.POINTER(owned_sqlite._VFS),
                    ctypes.c_int,
                ]
                lib.sqlite3_vfs_register.restype = ctypes.c_int
                assert lib.sqlite3_vfs_register(alternate, 1) == 0

                def restore_vfs():
                    return lib.sqlite3_vfs_register(vfs, 1)
            elif mode in (
                "compiler_missing",
                "compiler_execution",
                "compiler_result",
                "compiler_timeout",
                "concurrent_initialization",
            ):
                error = {
                    "compiler_missing": FileNotFoundError("audit missing compiler"),
                    "compiler_execution": PermissionError("audit compiler denied"),
                    "compiler_result": subprocess.CalledProcessError(1, "/usr/bin/cc"),
                    "compiler_timeout": subprocess.TimeoutExpired("/usr/bin/cc", 30),
                    "concurrent_initialization": FileNotFoundError(
                        "audit concurrent compiler unavailable"
                    ),
                }[mode]
                patches.enter_context(
                    patch.object(owned_sqlite.subprocess, "run", side_effect=error)
                )
            elif mode == "helper_load":
                actual_load = ctypes.CDLL

                def loading(path, *args, **kwargs):
                    if Path(path).name == "owned.so":
                        raise OSError("audit helper load denied")
                    return actual_load(path, *args, **kwargs)

                patches.enter_context(
                    patch.object(owned_sqlite.ctypes, "CDLL", loading)
                )
            elif mode == "hook":
                assert set_(vfs, b"fstat", original) == 0

                def restore_vfs():
                    return set_(vfs, b"fstat", pointer)
            elif mode == "fd":

                @contextmanager
                def missing(expected):
                    yield [expected, -1, False]

                patches.enter_context(
                    patch.object(owned_sqlite, "opened_identity", missing)
                )
            elif mode == "library":
                # 실제 별도 library image를 로드한다. Python connection은 원래 SQLite를 사용한다.
                library = next(
                    Path(line.split()[-1])
                    for line in Path("/proc/self/maps").read_text().splitlines()
                    if "libsqlite3.so" in line
                )
                copied = tmp_path / "independent-other-sqlite.so"
                shutil.copyfile(library, copied)
                patches.enter_context(
                    patch.object(owned_sqlite._sqlite3, "__file__", str(copied))
                )

            def attempt():
                try:
                    prior.Collector(prior.repository(db)).collect(apply=True)
                except (prior.CanonicalError, OSError) as error:
                    return str(error)
                raise AssertionError("destructive maintenance unexpectedly admitted")

            if mode == "concurrent_initialization":
                with ThreadPoolExecutor(max_workers=4) as pool:
                    errors = list(pool.map(lambda _: attempt(), range(4)))
            else:
                errors = [attempt()]
            patches.close()
            if restore_vfs:
                restore_vfs()
                restore_vfs = None
            assert snapshot(db.path) == before
            send.send(dict(errors=errors, persisted_unchanged=True))
        except BaseException as error:
            send.send(dict(failure=repr(error)))
        finally:
            patches.close()
            if restore_vfs:
                restore_vfs()
            send.close()

    process = multiprocessing.get_context("fork").Process(target=child)
    process.start()
    process.join(45)
    if process.is_alive():
        process.kill()
        process.join()
        pytest.fail("bounded native failure injection timeout")
    assert process.exitcode == 0 and recv.poll()
    result = recv.recv()
    assert "failure" not in result, result
    assert snapshot(db.path) == before
    record(
        "environment_" + mode,
        injection="REAL_LIBRARY_MISMATCH"
        if mode == "library"
        else "REAL_VFS_CHANGE"
        if mode == "vfs"
        else "MOCKED_FAILURE_INJECTION",
        **result,
    )


@pytest.mark.parametrize(
    "boundary",
    [
        "before_fd",
        "after_fd",
        "before_sql",
        "deleted",
        "before_commit",
        "after_commit",
        "cleanup",
    ],
)
def test_independent_crash_boundary_and_restart(db, boundary):
    prior.mutate(db)
    before = snapshot(db.path)

    def child():
        def kill():
            os.kill(os.getpid(), signal.SIGKILL)

        if boundary in ("before_fd", "after_fd"):
            real = REAL_CONNECT

            def opening(path, *args, **kwargs):
                if Path(path) == db.path and boundary == "before_fd":
                    kill()
                conn = real(path, *args, **kwargs)
                if Path(path) == db.path:
                    kill()
                return conn

            with patch.object(retention_schema.sqlite3, "connect", opening):
                db.connect()
        else:
            gc = prior.Collector(prior.repository(db))
            plan = gc.mark()
            if boundary == "before_sql":
                actual = prior.RetentionConnection.execute

                def executing(conn, sql, params=()):
                    if sql.startswith("DELETE FROM sync_object_edges"):
                        kill()
                    return actual(conn, sql, params)

                with patch.object(prior.RetentionConnection, "execute", executing):
                    gc.sweep(plan, batch=1)
            elif boundary == "cleanup":
                actual = prior.RetentionConnection.close

                def closing_(conn):
                    actual(conn)
                    kill()

                with patch.object(prior.RetentionConnection, "close", closing_):
                    gc.sweep(plan, batch=1)
            else:
                gc.sweep(
                    plan,
                    batch=1,
                    fault=lambda stage, conn: kill() if stage == boundary else None,
                )
        os._exit(99)

    process = multiprocessing.get_context("fork").Process(target=child)
    process.start()
    process.join(30)
    assert not process.is_alive() and process.exitcode == -signal.SIGKILL
    after = snapshot(db.path)
    removed = objects(before) - objects(after)
    assert len(removed) == (1 if boundary in ("after_commit", "cleanup") else 0)
    prior.check_current(db)
    prior.Collector(prior.repository(db)).mark()
    with closing(db.connect()) as conn:
        assert identity("/proc/self/fd/" + str(conn._ownership[1])) == db._owned_file
    record(
        "crash_" + boundary,
        actual_signal="SIGKILL",
        authorized_deletions=len(removed),
        current_reconstructable=True,
        restart_ownership_verified=True,
    )


def test_fixed_cost_open_and_fd_cleanup(db):
    before_count = len(list(Path("/proc/self/fd").iterdir()))
    samples = []
    compiled = []
    original = owned_sqlite.subprocess.run

    def compilation(*args, **kwargs):
        compiled.append(args[0])
        return original(*args, **kwargs)

    with patch.object(owned_sqlite.subprocess, "run", compilation):
        for trial in range(43):
            start = time.perf_counter()
            with closing(db._open()) as conn:
                fd, expected = conn._ownership[1:]
                assert identity("/proc/self/fd/" + str(fd)) == expected
            elapsed = (time.perf_counter() - start) * 1000
            if trial >= 3:
                samples.append(elapsed)
    assert len(list(Path("/proc/self/fd").iterdir())) == before_count
    assert compiled == []
    record(
        "steady_open_resources",
        samples_ms=samples,
        steady_compilations=0,
        fd_before=before_count,
        fd_after=before_count,
    )


def test_actual_public_vfs_abi_and_sqlite_library(db, tmp_path):
    """Host compiler/header와 실제 로드된 library/SQL connection을 대조한다."""
    source = r"""
#include <stddef.h>
#include <stdint.h>
#include <sys/stat.h>
#include <sqlite3.h>
size_t mn_size(void) { return sizeof(sqlite3_vfs); }
size_t mn_offset(int n) {
    size_t offsets[] = {offsetof(sqlite3_vfs, iVersion),
        offsetof(sqlite3_vfs, szOsFile), offsetof(sqlite3_vfs, mxPathname),
        offsetof(sqlite3_vfs, pNext), offsetof(sqlite3_vfs, zName),
        offsetof(sqlite3_vfs, pAppData), offsetof(sqlite3_vfs, xOpen),
        offsetof(sqlite3_vfs, xDelete), offsetof(sqlite3_vfs, xAccess),
        offsetof(sqlite3_vfs, xFullPathname), offsetof(sqlite3_vfs, xDlOpen),
        offsetof(sqlite3_vfs, xDlError), offsetof(sqlite3_vfs, xDlSym),
        offsetof(sqlite3_vfs, xDlClose), offsetof(sqlite3_vfs, xRandomness),
        offsetof(sqlite3_vfs, xSleep), offsetof(sqlite3_vfs, xCurrentTime),
        offsetof(sqlite3_vfs, xGetLastError),
        offsetof(sqlite3_vfs, xCurrentTimeInt64),
        offsetof(sqlite3_vfs, xSetSystemCall),
        offsetof(sqlite3_vfs, xGetSystemCall),
        offsetof(sqlite3_vfs, xNextSystemCall)};
    return n >= 0 && n < 22 ? offsets[n] : (size_t)-1;
}
size_t mn_dev_size(void) { return sizeof(((struct stat *)0)->st_dev); }
size_t mn_ino_size(void) { return sizeof(((struct stat *)0)->st_ino); }
int mn_header_version(void) { return SQLITE_VERSION_NUMBER; }
"""
    binary = tmp_path / "audit-public-abi.so"
    header = Path(os.environ.get("AUDIT_SQLITE_INCLUDE", str(OUT / "sqlite-3.45.1")))
    subprocess.run(
        [
            "/usr/bin/cc",
            "-I",
            str(header),
            "-std=c11",
            "-shared",
            "-fPIC",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-x",
            "c",
            "-",
            "-o",
            str(binary),
        ],
        input=source.encode(),
        capture_output=True,
        check=True,
        timeout=30,
    )
    compiled = ctypes.CDLL(str(binary))
    for name in ("mn_size", "mn_dev_size", "mn_ino_size", "mn_offset"):
        getattr(compiled, name).restype = ctypes.c_size_t
    compiled.mn_offset.argtypes = [ctypes.c_int]
    offsets = {
        name: compiled.mn_offset(i)
        for i, (name, _) in enumerate(owned_sqlite._VFS._fields_)
    }
    assert compiled.mn_size() == ctypes.sizeof(owned_sqlite._VFS)
    assert all(
        offset == getattr(owned_sqlite._VFS, name).offset
        for name, offset in offsets.items()
    )
    assert compiled.mn_dev_size() <= 8 and compiled.mn_ino_size() <= 8
    assert compiled.mn_header_version() == 3045001
    lib, vfs, _, _, _, _, temporary, _ = owned_sqlite._install()
    lib.sqlite3_libversion.restype = ctypes.c_char_p
    lib.sqlite3_sourceid.restype = ctypes.c_char_p

    class DlInfo(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_void_p) for name in ("fname", "fbase", "sname", "saddr")
        ]

    libc = ctypes.CDLL(None)
    libc.dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(DlInfo)]
    location = DlInfo()
    assert (
        libc.dladdr(
            ctypes.cast(lib.sqlite3_sourceid, ctypes.c_void_p), ctypes.byref(location)
        )
        == 1
    )
    library_path = ctypes.cast(location.fname, ctypes.c_char_p).value.decode()
    with closing(db.connect()) as conn:
        runtime, sourceid = conn.execute(
            "SELECT sqlite_version(),sqlite_source_id()"
        ).fetchone()
        assert runtime == lib.sqlite3_libversion().decode() == "3.45.1"
        assert sourceid == lib.sqlite3_sourceid().decode()
    assert vfs.contents.zName == b"unix" and vfs.contents.iVersion == 3
    assert Path(temporary.name).stat().st_mode & 0o777 == 0o700
    record(
        "actual_abi",
        runtime=runtime,
        sourceid=sourceid,
        library_path=library_path,
        header_version=compiled.mn_header_version(),
        public_vfs_bytes=compiled.mn_size(),
        offsets=offsets,
        device_bytes=compiled.mn_dev_size(),
        inode_bytes=compiled.mn_ino_size(),
        helper_directory_mode="0700",
    )


def test_actual_attachment_is_refused(db, tmp_path):
    other = tmp_path / "new-empty-disposable.sqlite3"
    with closing(REAL_CONNECT(other)) as conn:
        conn.execute("CREATE TABLE audit_marker(value)")
        conn.commit()
    before, other_before = snapshot(db.path), snapshot(other)
    with closing(db.connect()) as conn:
        with pytest.raises(sqlite3.DatabaseError, match="authorized"):
            conn.execute("ATTACH DATABASE ? AS other", (str(other),))
        assert [r[1] for r in conn.execute("PRAGMA database_list")] == ["main"]
    assert snapshot(db.path) == before and snapshot(other) == other_before
    record("attachment", real_execution=True, attached_database_count=0)


def test_concurrent_first_initialization_compiles_once(db):
    before = snapshot(db.path)
    recv, send = multiprocessing.Pipe(duplex=False)

    def child():
        calls = []
        original = subprocess.run
        start = time.perf_counter()

        def compile_(*args, **kwargs):
            calls.append(args[0])
            return original(*args, **kwargs)

        def opening(_):
            with closing(db._open()) as conn:
                assert (
                    identity("/proc/self/fd/" + str(conn._ownership[1]))
                    == db._owned_file
                )

        try:
            with (
                patch.object(owned_sqlite, "_installed", None),
                patch.object(owned_sqlite.subprocess, "run", compile_),
            ):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(opening, range(8)))
                assert len(calls) == 1
                send.send(
                    dict(
                        compilations=len(calls),
                        connections=8,
                        threads=4,
                        elapsed_ms=(time.perf_counter() - start) * 1000,
                    )
                )
        except BaseException as error:
            send.send(dict(failure=repr(error)))

    process = multiprocessing.get_context("fork").Process(target=child)
    process.start()
    process.join(40)
    if process.is_alive():
        process.kill()
        process.join()
        pytest.fail("native initialization timeout")
    assert process.exitcode == 0 and recv.poll()
    observed = recv.recv()
    assert "failure" not in observed, observed
    assert snapshot(db.path) == before
    record("single_initialization", **observed)


@pytest.mark.parametrize(
    "boundary", ["helper_initialization", "before_connection_binding"]
)
def test_additional_native_crash_boundaries(db, boundary):
    before = snapshot(db.path)

    def child():
        def kill(*args, **kwargs):
            os.kill(os.getpid(), signal.SIGKILL)

        if boundary == "helper_initialization":
            with (
                patch.object(owned_sqlite, "_installed", None),
                patch.object(owned_sqlite.subprocess, "run", kill),
            ):
                db._open()
        else:
            actual = owned_sqlite.opened_identity

            @contextmanager
            def observed(expected):
                with actual(expected) as scope:
                    yield scope
                assert scope[1] >= 0
                kill()

            with patch.object(owned_sqlite, "opened_identity", observed):
                db._open()
        os._exit(99)

    process = multiprocessing.get_context("fork").Process(target=child)
    process.start()
    process.join(30)
    assert not process.is_alive() and process.exitcode == -signal.SIGKILL
    assert snapshot(db.path) == before
    prior.check_current(db)
    prior.Collector(prior.repository(db)).mark()
    record(
        "crash_" + boundary,
        actual_signal="SIGKILL",
        committed_deletions=0,
        restart_verified=True,
    )


def test_real_unsupported_sqlite_runtime_refuses_before_open(db):
    executable = Path(
        os.environ.get(
            "AUDIT_UNSUPPORTED_PYTHON", "/home/hjkerman/anaconda3/bin/python3"
        )
    )
    if not executable.is_file():
        pytest.skip("별도의 unsupported SQLite Python interpreter가 필요하다")
    before = snapshot(db.path)
    code = """
import json,sqlite3,sys
sys.path.insert(0,sys.argv[1])
from isolated_sync import owned_sqlite
assert sqlite3.sqlite_version_info != (3,45,1)
opened=[]
def opening(*args,**kwargs):
    opened.append(True)
    raise AssertionError("unsupported runtime opened database")
sqlite3.connect=opening
try:
    with owned_sqlite.opened_identity((0,0)):
        sqlite3.connect(":memory:")
except Exception as error:
    assert str(error)=="REJECT_SYNTHETIC_OWNERSHIP_PLATFORM"
    assert not opened
    print(json.dumps(dict(runtime=sqlite3.sqlite_version,python=sys.version.split()[0],error=str(error),opened_databases=0)))
else:
    raise AssertionError("unsupported runtime was admitted")
"""
    output = subprocess.run(
        [str(executable), "-c", code, str(ROOT / "backend")],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert snapshot(db.path) == before
    record(
        "real_unsupported_runtime",
        injection="REAL_RUNTIME",
        **json.loads(output.stdout),
    )
