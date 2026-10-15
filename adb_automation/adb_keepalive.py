from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .adb import AdbClient, RUNTIME_ROOT
from .wireless_adb import connect_serial, load_config, save_config


DEFAULT_TCP_PORT = 5555
DEFAULT_KEEPALIVE_INTERVAL_SECONDS = 60
SCHEDULE_CONFIG_PATH = RUNTIME_ROOT / "schedule_config.json"
_IP_RE = re.compile(r"\b(?:inet\s+)?((?:\d{1,3}\.){3}\d{1,3})(?:/\d+)?\b")


@dataclass
class DeviceView:
    serial: str
    state: str
    details: str = ""

    @property
    def is_wireless(self) -> bool:
        return ":" in self.serial and self.serial.rsplit(":", 1)[1].isdigit()

    @property
    def is_online(self) -> bool:
        return self.state == "device"


@dataclass
class ConnectionSnapshot:
    devices: list[DeviceView]
    usb_devices: list[DeviceView]
    wireless_devices: list[DeviceView]
    abnormal_devices: list[DeviceView]
    mode_label: str
    current_serial: str
    current_label: str

    @property
    def usb_label(self) -> str:
        return _join_serials(self.usb_devices)

    @property
    def wireless_label(self) -> str:
        return _join_serials(self.wireless_devices)

    @property
    def abnormal_label(self) -> str:
        if not self.abnormal_devices:
            return "无"
        return "，".join(f"{item.serial}({item.state})" for item in self.abnormal_devices)


@dataclass
class LongWirelessResult:
    serial: str
    usb_serial: str
    host: str
    port: int
    message: str


@dataclass
class KeepAliveEvent:
    serial: str
    online: bool
    checked_at: datetime
    message: str


def _join_serials(devices: list[DeviceView]) -> str:
    if not devices:
        return "未连接"
    return "，".join(item.serial for item in devices)


def _looks_wireless_serial(value: object) -> bool:
    text = str(value or "").strip()
    if ":" not in text:
        return False
    host, port = text.rsplit(":", 1)
    return bool(host.strip()) and port.isdigit()


def list_adb_devices() -> list[DeviceView]:
    client = AdbClient()
    return [
        DeviceView(serial=str(item.serial), state=str(item.state), details=str(item.details))
        for item in client.list_devices()
    ]


def get_connection_snapshot(current_serial: str = "") -> ConnectionSnapshot:
    devices = list_adb_devices()
    online = [item for item in devices if item.is_online]
    usb_devices = [item for item in online if not item.is_wireless]
    wireless_devices = [item for item in online if item.is_wireless]
    abnormal_devices = [item for item in devices if not item.is_online]

    if usb_devices and wireless_devices:
        mode_label = "有线 + 无线"
    elif wireless_devices:
        mode_label = "无线模式"
    elif usb_devices:
        mode_label = "有线模式"
    elif abnormal_devices:
        mode_label = "连接异常"
    else:
        mode_label = "未连接"

    current = str(current_serial or "").strip()
    online_serials = {item.serial for item in online}
    if current and current in online_serials:
        current_label = ("无线" if _looks_wireless_serial(current) else "有线") + f" {current}"
    elif current:
        current_label = f"{current} 未在线"
    elif wireless_devices:
        current = wireless_devices[0].serial
        current_label = f"无线 {current}"
    elif usb_devices:
        current = usb_devices[0].serial
        current_label = f"有线 {current}"
    else:
        current_label = "未指定"

    return ConnectionSnapshot(
        devices=devices,
        usb_devices=usb_devices,
        wireless_devices=wireless_devices,
        abnormal_devices=abnormal_devices,
        mode_label=mode_label,
        current_serial=current,
        current_label=current_label,
    )


def choose_usb_serial(preferred: str = "") -> str:
    preferred = str(preferred or "").strip()
    snapshot = get_connection_snapshot()
    if preferred and not _looks_wireless_serial(preferred):
        for item in snapshot.usb_devices:
            if item.serial == preferred:
                return item.serial
    if len(snapshot.usb_devices) == 1:
        return snapshot.usb_devices[0].serial
    if snapshot.usb_devices:
        return snapshot.usb_devices[0].serial
    return ""


def _extract_ip(text: str) -> str:
    for match in _IP_RE.finditer(text):
        ip = match.group(1)
        if ip.startswith("127.") or ip == "0.0.0.0":
            continue
        parts = ip.split(".")
        if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return ip
    return ""


def get_wifi_ip(usb_serial: str) -> str:
    client = AdbClient().for_serial(usb_serial)
    output = client.shell("ip", "-f", "inet", "addr", "show", "wlan0", timeout=10)
    ip = _extract_ip(output)
    if ip:
        return ip
    output = client.shell("ip", "route", "get", "8.8.8.8", timeout=10)
    route_match = re.search(r"\bsrc\s+((?:\d{1,3}\.){3}\d{1,3})", output)
    if route_match:
        return route_match.group(1)
    raise RuntimeError("没有读取到手机 Wi-Fi IP，请确认手机已连接 Wi-Fi")


def _adb_tcpip(usb_serial: str, port: int) -> str:
    completed = AdbClient().run("-s", usb_serial, "tcpip", int(port), timeout=20, check=False)
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    if completed.returncode != 0:
        raise RuntimeError(output or f"adb tcpip {port} 失败")
    lowered = output.lower()
    if any(marker in lowered for marker in ("failed", "unable", "cannot", "error")):
        raise RuntimeError(output or f"adb tcpip {port} 失败")
    return output or f"restarting in TCP mode port: {port}"


def _model_name_from_details(details: str) -> str:
    match = re.search(r"\bmodel:([^\s]+)", details or "")
    return match.group(1) if match else ""


def save_keepalive_config(serial: str, *, enabled: bool, interval_seconds: int = DEFAULT_KEEPALIVE_INTERVAL_SECONDS) -> dict:
    host, port_text = serial.rsplit(":", 1)
    config = load_config()
    config.update(
        {
            "host": host,
            "connect_port": int(port_text),
            "serial": serial,
            "auto_connect": True,
            "keepalive_enabled": bool(enabled),
            "keepalive_interval_seconds": max(5, int(interval_seconds)),
        }
    )
    save_config(config)
    return config


def update_schedule_wireless(serial: str, *, mode: str = "wireless") -> dict:
    data: dict = {}
    try:
        data = json.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    if mode == "wireless":
        data["connection_mode"] = "wireless"
        data["serial"] = serial
        data["wireless_serial"] = serial
    else:
        data["connection_mode"] = "usb"
        if _looks_wireless_serial(data.get("serial")):
            data["serial"] = ""
        if serial:
            data["wireless_serial"] = serial
    SCHEDULE_CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def enable_long_wireless_debug(
    *,
    usb_serial: str = "",
    port: int = DEFAULT_TCP_PORT,
    interval_seconds: int = DEFAULT_KEEPALIVE_INTERVAL_SECONDS,
) -> LongWirelessResult:
    target_usb = choose_usb_serial(usb_serial)
    if not target_usb:
        saved = str(load_config().get("serial") or "").strip()
        if _looks_wireless_serial(saved):
            resolved, message = connect_serial(saved)
            save_keepalive_config(resolved, enabled=True, interval_seconds=interval_seconds)
            update_schedule_wireless(resolved, mode="wireless")
            host, port_text = resolved.rsplit(":", 1)
            return LongWirelessResult(
                serial=resolved,
                usb_serial="",
                host=host,
                port=int(port_text),
                message=f"{message}；已开启24小时无线保活",
            )
        raise RuntimeError("请先用 USB 连接手机并允许调试授权，再开启24小时无线连接")

    host = get_wifi_ip(target_usb)
    tcpip_message = _adb_tcpip(target_usb, int(port))
    time.sleep(1.2)
    serial = f"{host}:{int(port)}"
    resolved, connect_message = connect_serial(serial, fallback_mdns=False)

    snapshot = get_connection_snapshot()
    usb_detail = next((item.details for item in snapshot.usb_devices if item.serial == target_usb), "")
    config = save_keepalive_config(resolved, enabled=True, interval_seconds=interval_seconds)
    if not str(config.get("name") or "").strip():
        config["name"] = _model_name_from_details(usb_detail) or "无线设备"
        save_config(config)
    update_schedule_wireless(resolved, mode="wireless")

    return LongWirelessResult(
        serial=resolved,
        usb_serial=target_usb,
        host=host,
        port=int(port),
        message=f"{tcpip_message}；{connect_message}；已开启24小时无线保活",
    )


def disable_keepalive_config() -> dict:
    config = load_config()
    config["keepalive_enabled"] = False
    save_config(config)
    return config


class AdbKeepAlive:
    def __init__(
        self,
        serial: str,
        *,
        interval_seconds: int = DEFAULT_KEEPALIVE_INTERVAL_SECONDS,
        log: Callable[[str], None] | None = None,
        on_event: Callable[[KeepAliveEvent], None] | None = None,
    ) -> None:
        self.serial = str(serial or "").strip()
        self.interval_seconds = max(5, int(interval_seconds))
        self.log = log
        self.on_event = on_event
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if not self.serial:
            raise RuntimeError("无线 serial 为空，无法启动保活")
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="ADBWirelessKeepAlive", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def ensure_connected(self) -> KeepAliveEvent:
        checked_at = datetime.now()
        snapshot = get_connection_snapshot(self.serial)
        if any(item.serial == self.serial for item in snapshot.wireless_devices):
            event = KeepAliveEvent(self.serial, True, checked_at, "无线在线")
            self._emit(event)
            return event
        try:
            resolved, message = connect_serial(self.serial)
            if resolved != self.serial:
                self.serial = resolved
                save_keepalive_config(
                    resolved,
                    enabled=True,
                    interval_seconds=self.interval_seconds,
                )
                update_schedule_wireless(resolved, mode="wireless")
            event = KeepAliveEvent(resolved, True, checked_at, message or "无线已重连")
        except Exception as exc:
            event = KeepAliveEvent(self.serial, False, checked_at, f"无线重连失败：{exc}")
        self._emit(event)
        return event

    def _emit(self, event: KeepAliveEvent) -> None:
        if self.log is not None:
            try:
                self.log(event.message)
            except Exception:
                pass
        if self.on_event is not None:
            try:
                self.on_event(event)
            except Exception:
                pass

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.ensure_connected()
            self._stop_event.wait(self.interval_seconds)
