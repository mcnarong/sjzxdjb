from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\run_log.pyc')

del _exec_recovered_module

import shutil as _shutil
import sys as _sys
import threading as _threading
from contextlib import suppress as _suppress
from datetime import datetime as _datetime
from pathlib import Path as _Path
from zipfile import ZIP_DEFLATED as _ZIP_DEFLATED
from zipfile import ZIP_STORED as _ZIP_STORED
from zipfile import ZipFile as _ZipFile


_MAX_RUN_ARCHIVES = 5
_STAGING_DIR_NAME = "_archive_staging"
_ARCHIVE_THREADS_LOCK = _threading.Lock()
_ARCHIVE_WORK_LOCK = _threading.Lock()
_ACTIVE_STAGING_ARCHIVES = set()


def _runtime_root():
    if getattr(_sys, "frozen", False):
        return _Path(_sys.executable).resolve().parent
    return _Path(PROJECT_ROOT)


def _unique_archive_path(archive_dir):
    stamp = _datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for index in range(100):
        suffix = "" if index == 0 else f"_{index:02d}"
        path = archive_dir / f"run_{stamp}{suffix}.zip"
        if not path.exists():
            return path
    raise RuntimeError("无法创建唯一归档文件")


def _move_legacy_log_archives(log_dir, archive_dir):
    for path in sorted(log_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime):
        target = archive_dir / path.name
        if target.exists():
            target = archive_dir / f"legacy_{_datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{path.name}"
        with _suppress(OSError):
            _shutil.move(str(path), str(target))


def _prune_run_archives(archive_dir, max_archives=_MAX_RUN_ARCHIVES):
    archives = sorted(
        (path for path in archive_dir.glob("*.zip") if path.is_file()),
        key=lambda item: item.stat().st_mtime,
    )
    for path in archives[:-max_archives]:
        with _suppress(OSError):
            path.unlink()


def _is_nonempty_dir(path):
    try:
        next(path.iterdir())
    except StopIteration:
        return False
    except OSError:
        return False
    return True


def _unique_staging_path(staging_root):
    stamp = _datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    for index in range(100):
        suffix = "" if index == 0 else f"_{index:02d}"
        path = staging_root / f"run_{stamp}{suffix}"
        if not path.exists():
            return path
    raise RuntimeError("无法创建唯一归档暂存目录")


def _stage_dir(source, staging_dir, name):
    if not source.exists():
        return False
    if source.is_dir() and not _is_nonempty_dir(source):
        return False
    target = staging_dir / name
    try:
        source.rename(target)
    except OSError:
        return False
    return True


def _stage_previous_run(root):
    log_dir = root / "log"
    captures_dir = root / "captures"
    archive_dir = root / "archives"
    staging_root = root / _STAGING_DIR_NAME

    archive_dir.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    staging_dir = _unique_staging_path(staging_root)
    staging_dir.mkdir(parents=True, exist_ok=False)

    moved = False
    moved = _stage_dir(log_dir, staging_dir, "log") or moved
    moved = _stage_dir(captures_dir, staging_dir, "captures") or moved

    log_dir.mkdir(parents=True, exist_ok=True)
    captures_dir.mkdir(parents=True, exist_ok=True)

    if not moved:
        with _suppress(OSError):
            staging_dir.rmdir()
        return None

    return staging_dir


def _iter_stage_files(base_dir):
    if not base_dir.exists():
        return []
    return sorted(
        (path for path in base_dir.rglob("*") if path.is_file()),
        key=lambda item: str(item.relative_to(base_dir)).lower(),
    )


def _move_staged_legacy_log_archives(log_dir, archive_dir):
    if not log_dir.exists():
        return
    for path in sorted(log_dir.glob("*.zip"), key=lambda item: item.stat().st_mtime):
        target = archive_dir / path.name
        if target.exists():
            target = archive_dir / f"legacy_{_datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{path.name}"
        with _suppress(OSError):
            _shutil.move(str(path), str(target))


def _archive_staged_run(staging_dir, root, *, max_archives=_MAX_RUN_ARCHIVES):
    archive_dir = root / "archives"
    log_stage = staging_dir / "log"
    captures_stage = staging_dir / "captures"

    with _ARCHIVE_WORK_LOCK:
        archive_dir.mkdir(parents=True, exist_ok=True)
        _move_staged_legacy_log_archives(log_stage, archive_dir)

        log_files = _iter_stage_files(log_stage)
        step_checks_stage = captures_stage / "step_checks"
        if step_checks_stage.exists():
            with _suppress(OSError):
                _shutil.rmtree(step_checks_stage)
        capture_files = [
            path
            for path in _iter_stage_files(captures_stage)
            if "step_checks" not in path.relative_to(captures_stage).parts
        ]

        if not log_files and not capture_files:
            with _suppress(OSError):
                _shutil.rmtree(staging_dir)
            _prune_run_archives(archive_dir, max_archives)
            with _suppress(OSError):
                staging_dir.parent.rmdir()
            return None

        archive_path = _unique_archive_path(archive_dir)
        wrote = False

        try:
            with _ZipFile(archive_path, "w", compression=_ZIP_STORED) as archive:
                for path in log_files:
                    archive.write(path, arcname=f"log/{path.name}", compress_type=_ZIP_DEFLATED)
                    wrote = True
                for path in capture_files:
                    relative = path.relative_to(captures_stage).as_posix()
                    archive.write(path, arcname=f"captures/{relative}", compress_type=_ZIP_STORED)
                    wrote = True
        except Exception:
            with _suppress(OSError):
                archive_path.unlink()
            return None

        if not wrote:
            with _suppress(OSError):
                archive_path.unlink()
            with _suppress(OSError):
                _shutil.rmtree(staging_dir)
            return None

        with _suppress(OSError):
            _shutil.rmtree(staging_dir)
        with _suppress(OSError):
            staging_dir.parent.rmdir()
        _prune_run_archives(archive_dir, max_archives)
        return archive_path


def _archive_staging_in_background(root, staging_dir, *, max_archives=_MAX_RUN_ARCHIVES):
    key = str(staging_dir.resolve())
    with _ARCHIVE_THREADS_LOCK:
        if key in _ACTIVE_STAGING_ARCHIVES:
            return
        _ACTIVE_STAGING_ARCHIVES.add(key)

    def worker():
        try:
            _archive_staged_run(staging_dir, root, max_archives=max_archives)
        finally:
            with _ARCHIVE_THREADS_LOCK:
                _ACTIVE_STAGING_ARCHIVES.discard(key)

    thread = _threading.Thread(target=worker, name="archive-previous-run", daemon=True)
    thread.start()


def _start_pending_staging_archives(root, *, max_archives=_MAX_RUN_ARCHIVES):
    staging_root = root / _STAGING_DIR_NAME
    if not staging_root.exists():
        return
    try:
        staging_dirs = sorted(path for path in staging_root.iterdir() if path.is_dir())
    except OSError:
        return
    for staging_dir in staging_dirs:
        _archive_staging_in_background(root, staging_dir, max_archives=max_archives)


def start_archive_previous_run(root=None, *, max_archives=_MAX_RUN_ARCHIVES):
    root = _Path(root) if root is not None else _runtime_root()
    _start_pending_staging_archives(root, max_archives=max_archives)
    try:
        staging_dir = _stage_previous_run(root)
    except Exception:
        return None
    if staging_dir is None:
        return None
    _archive_staging_in_background(root, staging_dir, max_archives=max_archives)
    return staging_dir


def archive_previous_run(root=None, *, max_archives=_MAX_RUN_ARCHIVES):
    root = _Path(root) if root is not None else _runtime_root()
    try:
        staging_dir = _stage_previous_run(root)
    except OSError:
        return None
    if staging_dir is None:
        _prune_run_archives(root / "archives", max_archives)
        return None
    return _archive_staged_run(staging_dir, root, max_archives=max_archives)


def create_log_path():
    root = _runtime_root()
    log_dir = root / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    start_archive_previous_run(root)
    log_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        stamp = _datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = log_dir / f"{stamp}_pid{os.getpid()}.log"
        try:
            with path.open("x", encoding="utf-8"):
                pass
            return path
        except FileExistsError:
            time.sleep(0.001)
    raise RuntimeError(f"无法创建唯一日志文件: {log_dir}")
