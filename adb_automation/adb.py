from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\adb.pyc')

del _exec_recovered_module

import os as _os
import shutil as _shutil
import sys as _sys
import time as _time
from pathlib import Path as _Path


def _bundle_root():
    bundle_root = getattr(_sys, "_MEIPASS", None)
    return _Path(bundle_root) if bundle_root else None


def _runtime_root():
    if getattr(_sys, "frozen", False):
        return _Path(_sys.executable).resolve().parent
    return _Path(PROJECT_ROOT)


RUNTIME_ROOT = _runtime_root()
RESOURCE_ROOT = _bundle_root() or RUNTIME_ROOT


def _copy_missing_profile_files(source_dir, target_dir):
    if not source_dir.is_dir():
        return
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    for source in source_dir.iterdir():
        if not source.is_file() or source.suffix.lower() not in {".txt", ".json"}:
            continue
        target = target_dir / source.name
        if target.exists():
            continue
        try:
            _shutil.copy2(source, target)
        except OSError:
            pass


def _bootstrap_runtime_defaults():
    if not getattr(_sys, "frozen", False):
        return
    if RESOURCE_ROOT == RUNTIME_ROOT:
        return
    _copy_missing_profile_files(RESOURCE_ROOT / "device_profiles", RUNTIME_ROOT / "device_profiles")


_bootstrap_runtime_defaults()

if getattr(_sys, "frozen", False):
    PROJECT_ROOT = RESOURCE_ROOT


def _patch_find_adb_for_onefile():
    original_screenshot = AdbClient.screenshot

    def _screen_awake(self):
        try:
            text = self.shell("dumpsys", "power", timeout=6)
        except Exception:
            return True
        markers = (
            "mAwake=true",
            "mWakefulness=Awake",
            "Display Power: state=ON",
            "state=ON",
        )
        return any(marker in text for marker in markers)

    def _prepare_screen_for_screenshot(self):
        try:
            if not _screen_awake(self):
                self.shell("input", "keyevent", "KEYCODE_WAKEUP", timeout=6)
                _time.sleep(0.8)
            self.run("shell", "wm", "dismiss-keyguard", timeout=6, check=False)
            if self.is_keyguard_locked():
                width, height = self.screen_size()
                self.swipe(
                    round(width * 0.5),
                    round(height * 0.85),
                    round(width * 0.5),
                    round(height * 0.25),
                    300,
                )
                _time.sleep(0.8)
        except Exception:
            try:
                self.wake_and_unlock()
            except Exception:
                pass

    def _kill_stale_screencap(self):
        try:
            self.run("shell", "pkill", "-f", "screencap", timeout=5, check=False)
        except Exception:
            pass

    def find_adb(self):
        executable = "adb.exe" if _os.name == "nt" else "adb"
        candidates = []

        env_path = _os.environ.get("ADB_PATH")
        if env_path:
            candidates.append(_Path(env_path))

        for root in (RUNTIME_ROOT, RESOURCE_ROOT, PROJECT_ROOT, _bundle_root()):
            if root is None:
                continue
            candidates.extend(
                [
                    root / "platform-tools" / executable,
                    root / "scrcpy" / executable,
                ]
            )

        path_adb = _shutil.which("adb")
        if path_adb:
            candidates.append(_Path(path_adb))

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        searched = "\n".join(str(candidate) for candidate in candidates)
        raise AdbError(f"找不到 adb，可设置 ADB_PATH 或放到 platform-tools 目录。\n{searched}")

    def screenshot_with_runtime_root(self, output):
        path = _Path(output)
        if not path.is_absolute():
            path = RUNTIME_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        _prepare_screen_for_screenshot(self)
        try:
            completed = self.run("exec-out", "screencap", "-p", timeout=18, check=True, text=False)
            data = completed.stdout or b""
            if not data:
                raise AdbError("手机截图失败: screencap 没有返回图片数据")
            path.write_bytes(data)
            return path
        except Exception:
            _kill_stale_screencap(self)
            raise

    AdbClient._find_adb = find_adb
    AdbClient.screenshot = screenshot_with_runtime_root


_patch_find_adb_for_onefile()
del _patch_find_adb_for_onefile
