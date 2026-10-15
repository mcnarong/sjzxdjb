from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .adb import AdbClient, RUNTIME_ROOT


CONFIG_PATH = RUNTIME_ROOT / "wireless_adb.json"
SCHEDULE_CONFIG_PATH = RUNTIME_ROOT / "schedule_config.json"
_HOST_PORT_RE = re.compile(r"((?:\d{1,3}\.){3}\d{1,3}):(\d{2,5})")


class WirelessAdbError(RuntimeError):
    pass


@dataclass
class WirelessDevice:
    host: str
    name: str = ""
    pairing_port: int | None = None
    connect_port: int | None = None

    @property
    def serial(self) -> str:
        if not self.connect_port:
            return ""
        return f"{self.host}:{self.connect_port}"

    @property
    def label(self) -> str:
        parts = []
        if self.name:
            parts.append(self.name)
        ports = []
        if self.connect_port:
            ports.append(f"连接 {self.connect_port}")
        if self.pairing_port:
            ports.append(f"配对 {self.pairing_port}")
        suffix = " / ".join(ports)
        address = self.host if not suffix else f"{self.host} ({suffix})"
        parts.append(address)
        return " - ".join(parts)


def _subprocess_window_kwargs() -> dict[str, object]:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": startupinfo, "creationflags": subprocess.CREATE_NO_WINDOW}


def _adb_path() -> str:
    return str(AdbClient().adb_path)


def is_wireless_serial(value: str | None) -> bool:
    text = str(value or "").strip()
    if ":" not in text:
        return False
    host, port = text.rsplit(":", 1)
    return bool(host.strip()) and port.isdigit()


def parse_wireless_serial(value: str | None) -> tuple[str, int]:
    text = str(value or "").strip()
    if not is_wireless_serial(text):
        raise WirelessAdbError("无线地址格式应为 IP:端口，例如 192.168.1.23:37121")
    host, port = text.rsplit(":", 1)
    return host.strip(), int(port)


def _connectable_devices(devices: list[WirelessDevice]) -> list[WirelessDevice]:
    return [device for device in devices if device.connect_port]


def _select_dynamic_device(
    devices: list[WirelessDevice],
    saved_config: dict | None = None,
    *,
    preferred_host: str = "",
) -> WirelessDevice | None:
    candidates = _connectable_devices(devices)
    if not candidates:
        return None

    preferred_host = str(preferred_host or "").strip()
    if preferred_host:
        for device in candidates:
            if device.host == preferred_host:
                return device

    saved_name = str((saved_config or {}).get("name") or "").strip().casefold()
    if saved_name:
        named = [device for device in candidates if str(device.name or "").strip().casefold() == saved_name]
        if len(named) == 1:
            return named[0]

    if len(candidates) == 1:
        return candidates[0]
    return None


def run_adb(args: list[str], timeout: float = 20.0, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [_adb_path(), *args]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            **_subprocess_window_kwargs(),
        )
    except subprocess.TimeoutExpired as exc:
        raise WirelessAdbError("ADB 命令超时，请确认手机和电脑在同一局域网") from exc
    except OSError as exc:
        raise WirelessAdbError(f"无法执行 ADB：{exc}") from exc
    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise WirelessAdbError(detail or f"ADB 命令失败：退出码 {completed.returncode}")
    return completed


def discover_wireless_devices(timeout: float = 12.0) -> list[WirelessDevice]:
    completed = run_adb(["mdns", "services"], timeout=timeout, check=False)
    output = (completed.stdout or "") + "\n" + (completed.stderr or "")
    if completed.returncode != 0:
        detail = output.strip()
        raise WirelessAdbError(detail or "ADB 无法读取局域网无线调试服务")

    devices: dict[str, WirelessDevice] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or "List of discovered" in line:
            continue
        match = _HOST_PORT_RE.search(line)
        if not match:
            continue
        host = match.group(1)
        port = int(match.group(2))
        lower = line.lower()
        if "_adb-tls-pairing" in lower:
            service = "pairing"
        elif "_adb-tls-connect" in lower or "_adb._tcp" in lower:
            service = "connect"
        else:
            continue

        device = devices.setdefault(host, WirelessDevice(host=host))
        name = line.split()[0].strip()
        if name and name != host:
            device.name = name
        if service == "pairing":
            device.pairing_port = port
        else:
            device.connect_port = port

    saved_config = load_config()
    saved_serial = str(saved_config.get("serial") or "").strip()
    if not saved_serial:
        saved_host = str(saved_config.get("host") or "").strip()
        saved_port = saved_config.get("connect_port")
        if saved_host and saved_port:
            saved_serial = f"{saved_host}:{int(saved_port)}"
    if is_wireless_serial(saved_serial):
        try:
            host, port = parse_wireless_serial(saved_serial)
            existing = devices.get(host)
            if existing is None or not existing.connect_port:
                probe = run_adb(["connect", f"{host}:{port}"], timeout=3.0, check=False)
                probe_output = ((probe.stdout or "") + "\n" + (probe.stderr or "")).strip()
                lowered = probe_output.lower()
                bad_markers = ("failed", "unable", "cannot", "refused", "timed out", "no route", "offline")
                if probe.returncode == 0 and not any(marker in lowered for marker in bad_markers):
                    device = devices.setdefault(host, WirelessDevice(host=host))
                    if not device.name:
                        device.name = str(saved_config.get("name") or "").strip() or "上次保存设备"
                    device.connect_port = port
        except Exception:
            pass

    connected = run_adb(["devices", "-l"], timeout=8.0, check=False)
    connected_output = (connected.stdout or "") + "\n" + (connected.stderr or "")
    for raw_line in connected_output.splitlines():
        line = raw_line.strip()
        if not line or "List of devices" in line:
            continue
        parts = line.split()
        if len(parts) < 2 or parts[1] != "device":
            continue
        serial = parts[0]
        if not is_wireless_serial(serial):
            continue
        host, port = parse_wireless_serial(serial)
        device = devices.setdefault(host, WirelessDevice(host=host))
        device.connect_port = port
        if not device.name:
            model = next((item.split(":", 1)[1] for item in parts[2:] if item.startswith("model:")), "")
            device.name = model or "已连接无线设备"

    return sorted(devices.values(), key=lambda item: (item.name or item.host, item.host))


def pair_device(host: str, pairing_port: int, pairing_code: str) -> str:
    code = str(pairing_code or "").strip()
    if not code:
        raise WirelessAdbError("请输入手机上显示的配对码")
    completed = run_adb(["pair", f"{host}:{int(pairing_port)}", code], timeout=30.0, check=False)
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    lowered = output.lower()
    if completed.returncode != 0 or "failed" in lowered or "unable" in lowered:
        raise WirelessAdbError(output or "无线配对失败，请检查配对码和配对端口")
    return output or "配对成功"


def connect_device(host: str, connect_port: int) -> str:
    serial = f"{host}:{int(connect_port)}"
    completed = run_adb(["connect", serial], timeout=20.0, check=False)
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    lowered = output.lower()
    if completed.returncode != 0 or "failed" in lowered or "unable" in lowered or "cannot" in lowered:
        raise WirelessAdbError(output or f"无线连接失败：{serial}")
    return output or f"已连接 {serial}"


def connect_serial(serial: str, *, fallback_mdns: bool = True) -> tuple[str, str]:
    host, port = parse_wireless_serial(serial)
    try:
        return f"{host}:{port}", connect_device(host, port)
    except WirelessAdbError as first_error:
        if not fallback_mdns:
            raise
        refreshed = discover_wireless_devices(timeout=8.0)
        target = _select_dynamic_device(refreshed, load_config(), preferred_host=host)
        if target is None:
            raise first_error
        message = connect_device(target.host, int(target.connect_port))
        save_connected_device(target)
        return target.serial, f"{message}；端口已更新为 {target.serial}"


def disconnect_device(serial: str) -> str:
    target = str(serial or "").strip()
    if not target:
        raise WirelessAdbError("没有可断开的无线设备")
    completed = run_adb(["disconnect", target], timeout=12.0, check=False)
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    if completed.returncode != 0:
        raise WirelessAdbError(output or f"断开失败：{target}")
    return output or f"已断开 {target}"


def load_config(path: Path = CONFIG_PATH) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(config: dict, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_schedule_wireless_serial(serial: str, path: Path = SCHEDULE_CONFIG_PATH) -> None:
    target = str(serial or "").strip()
    if not is_wireless_serial(target):
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data["connection_mode"] = "wireless"
    data["serial"] = target
    data["wireless_serial"] = target
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def save_connected_device(device: WirelessDevice) -> dict:
    if not device.connect_port:
        raise WirelessAdbError("没有可保存的连接端口")
    config = {
        "host": device.host,
        "connect_port": int(device.connect_port),
        "serial": device.serial,
        "name": device.name,
        "auto_connect": True,
    }
    if device.pairing_port:
        config["pairing_port"] = int(device.pairing_port)
    save_config(config)
    sync_schedule_wireless_serial(device.serial)
    return config


def auto_connect_saved() -> tuple[bool, str, str]:
    config = load_config()
    if not config.get("auto_connect", True):
        return False, "", "无线自动连接未启用"
    host = str(config.get("host") or "").strip()
    port = config.get("connect_port")
    if not host or not port:
        refreshed = discover_wireless_devices(timeout=8.0)
        target = _select_dynamic_device(refreshed, config)
        if target is None:
            return False, "", "No saved wireless device, and no unique wireless device is available."
        message = connect_device(target.host, int(target.connect_port))
        save_connected_device(target)
        return True, target.serial, message
        return False, "", "没有已保存的无线设备"
    serial, message = connect_serial(f"{host}:{int(port)}")
    sync_schedule_wireless_serial(serial)
    return True, serial, message
