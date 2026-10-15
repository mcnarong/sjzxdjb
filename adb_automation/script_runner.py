from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\script_runner.pyc')

del _exec_recovered_module

from pathlib import Path as _Path
import re as _re
import time as _time
from .adb import RESOURCE_ROOT as _ADB_RESOURCE_ROOT
from .adb import RUNTIME_ROOT as _ADB_RUNTIME_ROOT


PROJECT_ROOT = _ADB_RUNTIME_ROOT


def _patch_fast_qq_finish_to_home():
    original_run_file = ScriptRunner.run_file

    def finish_qq_switch_to_home_fast(self):
        self.log("QQ 切号完成，直接返回手机桌面")
        self.client.keyevent("HOME")

    def run_file_with_bundle_fallback(self, script_path):
        path = _Path(script_path)
        if not path.is_absolute():
            runtime_path = _ADB_RUNTIME_ROOT / path
            resource_path = _ADB_RESOURCE_ROOT / path
            path = resource_path if resource_path.exists() and not runtime_path.exists() else runtime_path
        return original_run_file(self, path)

    ScriptRunner._finish_qq_switch_to_home = finish_qq_switch_to_home_fast
    ScriptRunner.run_file = run_file_with_bundle_fallback


_patch_fast_qq_finish_to_home()
del _patch_fast_qq_finish_to_home


def _foreground_package(client):
    patterns = (
        r"\bu\d+\s+([A-Za-z0-9_.]+)/[A-Za-z0-9_.$]+",
        r"\b([A-Za-z0-9_.]+)/[A-Za-z0-9_.$]+",
    )
    for command in (("dumpsys", "window"), ("dumpsys", "activity", "activities")):
        try:
            text = client.shell(*command, timeout=6)
        except Exception:
            continue
        lines = [
            line
            for line in str(text).splitlines()
            if any(token in line for token in ("mCurrentFocus", "mFocusedApp", "topResumedActivity", "mResumedActivity"))
        ]
        for line in lines:
            for pattern in patterns:
                match = _re.search(pattern, line)
                if match:
                    return match.group(1)
    return ""


def _patch_wait_foreground_package_action():
    original_run_step = ScriptRunner.run_step

    def wait_foreground_package(self, step):
        packages = step.get("packages") or step.get("package") or []
        if isinstance(packages, str):
            packages = [packages]
        packages = [str(package).strip() for package in packages if str(package).strip()]
        if not packages:
            raise ValueError("wait_foreground_package requires package or packages")
        timeout = float(step.get("timeout", 30.0))
        poll_seconds = max(0.2, float(step.get("poll_seconds", 0.8)))
        settle_seconds = max(0.0, float(step.get("settle_seconds", 0.0)))
        label = step.get("note") or "waiting foreground package"
        self.log(f"{label}: waiting for {', '.join(packages)}")
        deadline = _time.monotonic() + timeout
        last_package = ""
        while _time.monotonic() < deadline:
            self.check_cancelled()
            current = _foreground_package(self.client)
            if current:
                last_package = current
            if current in packages:
                if settle_seconds:
                    self.sleep_interruptible(settle_seconds)
                self.log(f"{label}: foreground is {current}")
                return
            self.sleep_interruptible(poll_seconds)
        detail = f"last foreground package: {last_package or 'unknown'}"
        raise TimeoutError(f"{label} timed out after {timeout:g}s; expected {', '.join(packages)}; {detail}")

    def run_step_with_wait_foreground(self, action, step):
        if action == "wait_foreground_package":
            return wait_foreground_package(self, step)
        return original_run_step(self, action, step)

    ScriptRunner.run_step = run_step_with_wait_foreground


_patch_wait_foreground_package_action()
del _patch_wait_foreground_package_action


def _patch_improved_special_office_detection():
    global delta_force_special_office_score
    _orig_score = delta_force_special_office_score

    def delta_force_special_office_score_robust(image_path):
        base_score = _orig_score(image_path)
        if base_score is None:
            return None
        # 正常特勤处综合亮灰占比在 0.12 ~ 0.22 之间，过高说明是大厅密集文字或弹窗误判
        if base_score > 0.28:
            return None
        try:
            with Image.open(image_path) as image:
                screenshot = image.convert("RGB")
            width, height = screenshot.size
            if width < height:
                return None
            # 特勤处左上角必有返回箭头与标题 "< 特勤处"（约 x: 5.5%~9.5%, y: 3%~7%）
            box = (round(width * 0.055), round(height * 0.03), round(width * 0.095), round(height * 0.07))
            crop = screenshot.crop(box)
            data = list(crop.getdata())
            bright_ratio = sum(p[0] > 150 and p[1] > 150 and p[2] > 150 for p in data) / len(data) if data else 0.0
            if bright_ratio < 0.08:
                return None
        except Exception:
            return None
        return base_score

    delta_force_special_office_score = delta_force_special_office_score_robust

    def verify_with_self_healing(self, step):
        screenshot_path = self._resolve_path(
            str(step.get("screenshot_path") or "captures/delta_force_special_office_check.png")
        )
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.screenshot(screenshot_path)
        score = delta_force_special_office_score(screenshot_path)
        self.log(f"三角洲特勤处界面校验截图保存到: {screenshot_path}")

        if score is None:
            for attempt in range(2):
                self.log(
                    f"未识别到特勤处升级制造界面（可能停在大厅或有弹窗遮挡），正在自愈进入 (第 {attempt + 1}/2 次)..."
                )
                # 尝试关闭可能存在的活动弹窗 / 空白处跳过
                self.client.tap(2160, 80)
                self.sleep_interruptible(1.0)
                self.client.tap(1800, 820)
                self.sleep_interruptible(1.0)
                # 重新点击特勤处入口
                self.client.tap(1020, 1032)
                self.sleep_interruptible(3.5)
                self.client.screenshot(screenshot_path)
                score = delta_force_special_office_score(screenshot_path)
                if score is not None:
                    self.log(f"自愈成功：已重新进入三角洲特勤处升级制造界面，识别分数 {score:.3f}")
                    return

        if score is None:
            raise StepVerificationError(
                "点击特勤处后未识别到升级制造界面，可能是特勤处坐标偏移、页面还在大厅或被弹窗遮挡。"
                f"请手动切到特勤处升级制造界面后点继续执行，截图: {screenshot_path}"
            )
        self.log(f"已确认进入三角洲特勤处升级制造界面，识别分数 {score:.3f}")

    ScriptRunner._verify_delta_force_special_office = verify_with_self_healing


_patch_improved_special_office_detection()
del _patch_improved_special_office_detection

