from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .adb import AdbClient


@dataclass
class PreflightIssue:
    level: str
    code: str
    message: str


@dataclass
class PreflightResult:
    serial: str = ""
    device_info: Any | None = None
    issues: list[PreflightIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.level == "error" for issue in self.issues)

    def add(self, level: str, code: str, message: str) -> None:
        self.issues.append(PreflightIssue(level, code, message))

    def lines(self) -> list[str]:
        if not self.issues:
            return ["[Preflight][OK] Device is ready."]
        labels = {"error": "ERROR", "warning": "WARN", "info": "OK"}
        return [
            f"[Preflight][{labels.get(issue.level, issue.level.upper())}] {issue.message}"
            for issue in self.issues
        ]


def _is_wireless_serial(value: object) -> bool:
    text = str(value or "").strip()
    if ":" not in text:
        return False
    host, port = text.rsplit(":", 1)
    return bool(host.strip()) and port.isdigit()


def _device_pairs(info: Any) -> set[tuple[int, int]]:
    values = (
        (getattr(info, "screen_width", 0), getattr(info, "screen_height", 0)),
        (getattr(info, "display_width", 0), getattr(info, "display_height", 0)),
    )
    pairs: set[tuple[int, int]] = set()
    for width, height in values:
        try:
            width = int(width or 0)
            height = int(height or 0)
        except (TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            pairs.add((width, height))
            pairs.add((height, width))
    return pairs


def _profile_screen_pair(profile: dict[str, Any] | None) -> tuple[int, int] | None:
    if not isinstance(profile, dict):
        return None
    screen = profile.get("screen")
    if not isinstance(screen, dict):
        return None
    try:
        width = int(screen.get("dry_run_width") or 0)
        height = int(screen.get("dry_run_height") or 0)
    except (TypeError, ValueError):
        return None
    if width > 0 and height > 0:
        return width, height
    return None


def _workflow_section(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    workflow = config.get("workflow")
    if isinstance(workflow, dict):
        return workflow
    return config


def _find_profile(kind: str, key: str) -> dict[str, Any] | None:
    if not key:
        return None
    try:
        from . import workflows

        workflows.refresh_device_profiles()
        profiles = (
            workflows.QQ_DEVICE_PROFILES
            if kind == "qq"
            else workflows.DELTA_FORCE_DEVICE_PROFILES
        )
    except Exception:
        return None
    for profile in profiles:
        if str(profile.get("key") or "") == key:
            return profile
    return None


def _check_profiles(result: PreflightResult, workflow_config: dict[str, Any] | None) -> None:
    info = result.device_info
    if info is None:
        return
    workflow = _workflow_section(workflow_config)
    selected = {
        "qq": str(workflow.get("qq_profile_key") or "").strip(),
        "delta_force": str(workflow.get("delta_force_profile_key") or "").strip(),
    }
    try:
        from . import workflows

        workflows.refresh_device_profiles()
    except Exception as exc:
        result.add("warning", "profile_reload_failed", f"Profile reload failed: {exc}")
        return

    device_pairs = _device_pairs(info)
    for kind, selected_key in selected.items():
        profile = _find_profile(kind, selected_key) if selected_key else None
        if selected_key and profile is None:
            result.add(
                "warning",
                f"{kind}_profile_missing",
                f"Selected {kind} profile is missing: {selected_key}.",
            )
        expected_pair = _profile_screen_pair(profile)
        if expected_pair and expected_pair not in device_pairs:
            result.add(
                "warning",
                f"{kind}_screen_mismatch",
                f"Selected {kind} profile resolution is {expected_pair[0]}x{expected_pair[1]}, "
                "which does not match the current phone.",
            )
        try:
            matched = workflows.matching_device_profile(info, kind)
        except Exception as exc:
            result.add("warning", f"{kind}_match_failed", f"Profile match check failed for {kind}: {exc}")
            matched = None
        if not matched:
            result.add(
                "warning",
                f"{kind}_no_match",
                f"No verified {kind} coordinate profile matches the current phone. Calibrate once if taps are wrong.",
            )
            continue
        matched_profile, source = matched
        matched_key = str(matched_profile.get("key") or "")
        if selected_key and matched_key and selected_key != matched_key:
            label = matched_profile.get("label") or matched_key
            result.add(
                "warning",
                f"{kind}_auto_profile",
                f"Selected {kind} profile is {selected_key}, but current phone matches {label} from {source}. "
                "The workflow will prefer the matched profile.",
            )


def _screen_awake(client: AdbClient) -> bool:
    try:
        text = client.shell("dumpsys", "power", timeout=6)
    except Exception:
        return True
    if any(marker in text for marker in ("mAwake=true", "mWakefulness=Awake", "state=ON")):
        return True
    if any(marker in text for marker in ("mAwake=false", "mWakefulness=Asleep", "mWakefulness=Dozing", "state=OFF")):
        return False
    return True


def _keyguard_secure(client: AdbClient) -> bool | None:
    try:
        text = client.shell("dumpsys", "window", "policy", timeout=6)
    except Exception:
        text = ""
    lowered = text.lower()
    if "secure=false" in lowered or "missecure=false" in lowered or "msimsecure=false" in lowered:
        return False
    if "secure=true" in lowered or "missecure=true" in lowered or "msimsecure=true" in lowered:
        return True
    try:
        trust = client.shell("dumpsys", "trust", timeout=6).lower()
    except Exception:
        trust = ""
    if "devicelocked=0" in trust:
        return False
    if "devicelocked=1" in trust:
        return True
    return None


def _prepare_screen(client: AdbClient, result: PreflightResult, *, auto_fix: bool) -> None:
    if not auto_fix:
        return
    try:
        client.run("shell", "pkill", "-f", "screencap", timeout=4, check=False)
    except Exception:
        pass
    try:
        if not _screen_awake(client):
            client.keyevent("KEYCODE_WAKEUP")
            time.sleep(0.8)
            result.add("info", "woke_screen", "Phone screen was asleep and was woken before running.")
        client.run("shell", "wm", "dismiss-keyguard", timeout=6, check=False)
        locked = client.is_keyguard_locked()
        if locked:
            width, height = client.screen_size()
            client.swipe(
                round(width * 0.5),
                round(height * 0.85),
                round(width * 0.5),
                round(height * 0.25),
                300,
            )
            time.sleep(0.8)
            locked = client.is_keyguard_locked()
        if locked:
            secure = _keyguard_secure(client)
            if secure is False:
                result.add(
                    "warning",
                    "non_secure_keyguard",
                    "Phone shows a non-secure lock screen; automation will continue after wake/swipe.",
                )
            else:
                result.add(
                    "error",
                    "keyguard_locked",
                    "Phone is still securely locked. Unlock it once, or disable secure lock while automation runs.",
                )
    except Exception as exc:
        result.add("warning", "screen_prepare_failed", f"Screen wake/unlock check failed: {exc}")


def _ensure_wireless_serial(
    result: PreflightResult,
    *,
    serial: str,
    connection_mode: str,
) -> str:
    mode = str(connection_mode or "").strip().lower()
    if mode != "wireless" and not _is_wireless_serial(serial):
        return serial
    try:
        from .wireless_adb import auto_connect_saved, connect_serial, sync_schedule_wireless_serial
    except Exception as exc:
        result.add("warning", "wireless_import_failed", f"Wireless ADB helper failed to load: {exc}")
        return serial

    if not serial:
        try:
            connected, resolved, message = auto_connect_saved()
            if message:
                result.add("info", "wireless_auto_connect", message)
            if connected and resolved:
                sync_schedule_wireless_serial(resolved)
                return resolved
        except Exception as exc:
            result.add("error", "wireless_auto_connect_failed", f"Wireless ADB auto connect failed: {exc}")
        return serial

    if _is_wireless_serial(serial):
        try:
            resolved, message = connect_serial(serial)
            if resolved:
                sync_schedule_wireless_serial(resolved)
                if resolved != serial:
                    result.add("info", "wireless_serial_updated", f"Wireless ADB address updated to {resolved}.")
                elif message:
                    result.add("info", "wireless_connected", message)
                return resolved
        except Exception as exc:
            result.add("error", "wireless_connect_failed", f"Wireless ADB connect failed for {serial}: {exc}")
    return serial


def run_preflight(
    *,
    serial: str = "",
    connection_mode: str = "",
    workflow_config: dict[str, Any] | None = None,
    auto_fix: bool = True,
) -> PreflightResult:
    result = PreflightResult(serial=str(serial or "").strip())
    result.serial = _ensure_wireless_serial(
        result,
        serial=result.serial,
        connection_mode=connection_mode,
    )

    try:
        base = AdbClient()
        devices = base.list_devices()
    except Exception as exc:
        result.add("error", "adb_failed", f"ADB is not ready: {exc}")
        return result

    online = [device for device in devices if getattr(device, "state", "") == "device"]
    if result.serial:
        selected = next((device for device in devices if getattr(device, "serial", "") == result.serial), None)
        if selected is None:
            result.add("error", "selected_missing", f"Selected device is not visible in adb devices: {result.serial}.")
            return result
        if getattr(selected, "state", "") != "device":
            result.add(
                "error",
                "selected_not_ready",
                f"Selected device {result.serial} is {getattr(selected, 'state', 'unknown')}. Re-authorize USB debugging.",
            )
            return result
    else:
        if len(online) == 1:
            result.serial = getattr(online[0], "serial", "")
            result.add("info", "single_device_selected", f"Using the only online device: {result.serial}.")
        elif len(online) == 0:
            states = ", ".join(f"{getattr(d, 'serial', '')}:{getattr(d, 'state', '')}" for d in devices) or "none"
            result.add("error", "no_online_device", f"No online ADB device. Current adb devices: {states}.")
            return result
        else:
            serials = ", ".join(getattr(device, "serial", "") for device in online)
            result.add("error", "multiple_devices", f"Multiple ADB devices are online ({serials}). Select one device first.")
            return result

    client = base.for_serial(result.serial)
    try:
        info = client.device_info()
        result.device_info = info
        size = f"{getattr(info, 'screen_width', 0)}x{getattr(info, 'screen_height', 0)}"
        display = f"{getattr(info, 'display_width', 0)}x{getattr(info, 'display_height', 0)}"
        density = getattr(info, "density", None)
        model = f"{getattr(info, 'manufacturer', '')} {getattr(info, 'model', '')}".strip()
        result.add("info", "device_info", f"Device ready: {result.serial} {model}, screen {size}, display {display}, dpi {density}.")
        if not getattr(info, "screen_width", 0) or not getattr(info, "screen_height", 0):
            result.add("error", "screen_size_unknown", "Could not read phone screen size.")
        if density is None:
            result.add("warning", "density_unknown", "Could not read phone DPI; coordinate matching may be weaker.")
    except Exception as exc:
        result.add("error", "device_info_failed", f"Could not read phone info: {exc}")
        return result

    _prepare_screen(client, result, auto_fix=auto_fix)
    _check_profiles(result, workflow_config)
    return result
