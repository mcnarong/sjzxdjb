from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from .adb import RUNTIME_ROOT


WAIT_SETTINGS_FILENAME = "wait_settings.json"
WAIT_SETTINGS_PATH = RUNTIME_ROOT / WAIT_SETTINGS_FILENAME


WAIT_SETTING_ITEMS = [
    {
        "key": "launch_game_load",
        "label": "启动游戏等待登录页加载",
        "default": 17.0,
        "minimum": 1.0,
        "maximum": 60.0,
    },
    {
        "key": "after_qq_login",
        "label": "点击 QQ 登录后等待",
        "default": 3.0,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "qq_login_open_timeout",
        "label": "QQ authorization page max wait",
        "default": 25.0,
        "minimum": 3.0,
        "maximum": 90.0,
    },
    {
        "key": "after_first_authorization",
        "label": "第一层授权后等待",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "after_second_authorization",
        "label": "第二层授权后等待",
        "default": 12.0,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "qq_login_return_timeout",
        "label": "Return to Delta Force max wait after QQ auth",
        "default": 45.0,
        "minimum": 5.0,
        "maximum": 120.0,
    },
    {
        "key": "after_start_game",
        "label": "点击开始游戏后等待",
        "default": 3.0,
        "minimum": 1.0,
        "maximum": 60.0,
    },
    {
        "key": "start_popup_check",
        "label": "开始游戏后弹窗检查等待",
        "default": 3.0,
        "minimum": 0.5,
        "maximum": 20.0,
    },
    {
        "key": "after_special_office",
        "label": "点击特勤处后等待",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "station_action",
        "label": "工位、收取、生产、补货通用等待",
        "default": 3.0,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "qq_reset",
        "label": "重置 QQ 当前页面后等待",
        "default": 1.0,
        "minimum": 0.2,
        "maximum": 15.0,
    },
    {
        "key": "qq_home_load",
        "label": "等待 QQ 首页加载",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "qq_security",
        "label": "QQ 安全提醒处理等待",
        "default": 2.0,
        "minimum": 0.2,
        "maximum": 15.0,
    },
    {
        "key": "qq_settings_open",
        "label": "QQ 设置页打开等待",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 20.0,
    },
    {
        "key": "qq_account_security_open",
        "label": "账号与安全页打开等待",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 20.0,
    },
    {
        "key": "qq_switch_complete",
        "label": "QQ 完成账号切换等待",
        "default": 3.5,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "phone_home_show",
        "label": "返回手机桌面等待",
        "default": 1.5,
        "minimum": 0.2,
        "maximum": 20.0,
    },
    {
        "key": "back_to_lobby",
        "label": "从特勤处返回大厅等待",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 30.0,
    },
    {
        "key": "open_settings",
        "label": "打开右上角设置等待",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 20.0,
    },
    {
        "key": "logout_confirm",
        "label": "退出登录后等待",
        "default": 2.0,
        "minimum": 0.5,
        "maximum": 20.0,
    },
    {
        "key": "close_game_process",
        "label": "关闭游戏进程后等待",
        "default": 1.0,
        "minimum": 0.2,
        "maximum": 20.0,
    },
    {
        "key": "login_page_after_logout",
        "label": "退出后等待登录页加载",
        "default": 12.0,
        "minimum": 1.0,
        "maximum": 60.0,
    },
    {
        "key": "agreement_effect",
        "label": "协议勾选生效等待",
        "default": 2.0,
        "minimum": 0.2,
        "maximum": 20.0,
    },
]


def wait_setting_items() -> list[dict]:
    return deepcopy(WAIT_SETTING_ITEMS)


def default_wait_settings() -> dict[str, float]:
    return {item["key"]: float(item["default"]) for item in WAIT_SETTING_ITEMS}


def _item_by_key() -> dict[str, dict]:
    return {item["key"]: item for item in WAIT_SETTING_ITEMS}


def _coerce_seconds(key: str, value) -> float:
    item = _item_by_key()[key]
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        seconds = float(item["default"])
    minimum = float(item["minimum"])
    maximum = float(item["maximum"])
    return max(minimum, min(maximum, seconds))


def normalize_wait_settings(values: dict | None) -> dict[str, float]:
    raw = values or {}
    normalized = {}
    for item in WAIT_SETTING_ITEMS:
        key = item["key"]
        normalized[key] = _coerce_seconds(key, raw.get(key, item["default"]))
    return normalized


def load_wait_settings(path: Path | None = None) -> dict[str, float]:
    target = path or WAIT_SETTINGS_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_wait_settings()
    if isinstance(payload, dict) and isinstance(payload.get("values"), dict):
        payload = payload["values"]
    if not isinstance(payload, dict):
        return default_wait_settings()
    return normalize_wait_settings(payload)


def save_wait_settings(values: dict[str, float], path: Path | None = None) -> dict[str, float]:
    target = path or WAIT_SETTINGS_PATH
    normalized = normalize_wait_settings(values)
    data = {
        "version": 1,
        "values": normalized,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def reset_wait_settings(path: Path | None = None) -> dict[str, float]:
    return save_wait_settings(default_wait_settings(), path=path)


def get_wait_seconds(key: str, path: Path | None = None) -> float:
    settings = load_wait_settings(path=path)
    defaults = default_wait_settings()
    return float(settings.get(key, defaults[key]))
