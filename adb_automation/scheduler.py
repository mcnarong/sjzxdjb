from __future__ import annotations

from ._bytecode_loader import exec_recovered_module as _exec_recovered_module

_exec_recovered_module(globals(), 'adb_automation\\scheduler.pyc')

del _exec_recovered_module

import sys as _sys
import json as _json
from datetime import datetime as _dt_datetime
from pathlib import Path as _Path
from .adb import RESOURCE_ROOT as _ADB_RESOURCE_ROOT
from .adb import RUNTIME_ROOT as _ADB_RUNTIME_ROOT


MIN_DAILY_TIME_COUNT = 1
MAX_DAILY_TIME_COUNT = 4
SCHEDULE_MODE_DAILY_TIMES = "daily_times"
SCHEDULE_MODE_FINISH_INTERVAL = "finish_interval"
SCHEDULE_MODES = {SCHEDULE_MODE_DAILY_TIMES, SCHEDULE_MODE_FINISH_INTERVAL}
DEFAULT_FINISH_INTERVAL_HOURS = 8.0
DEFAULT_FINISH_INTERVAL_MINUTES = 0
MIN_FINISH_INTERVAL_HOURS = 0.0
MAX_FINISH_INTERVAL_HOURS = 24.0
MIN_FINISH_INTERVAL_TOTAL_MINUTES = 1
MAX_FINISH_INTERVAL_TOTAL_MINUTES = 24 * 60
LAST_FINISHED_AT_KEY = "last_finished_at"
LAST_FINISHED_AT_FORMAT = "%Y-%m-%d %H:%M"

try:
    DEFAULT_SCHEDULE_CONFIG.setdefault(LAST_FINISHED_AT_KEY, "")
except Exception:
    pass


_ORIGINAL_NORMALIZE_SCHEDULE_CONFIG = normalize_schedule_config
_ORIGINAL_VALIDATE_SCHEDULE_CONFIG = validate_schedule_config
_ORIGINAL_NEXT_RUN_TIME = next_run_time
_ORIGINAL_PROJECT_PATH = _project_path
_ORIGINAL_LOAD_SCHEDULE_CONFIG = load_schedule_config
_ORIGINAL_SCHEDULER_SCHEDULE_NEXT = AutomationScheduler._schedule_next
_ORIGINAL_SCHEDULER_RUN_FOREVER = AutomationScheduler.run_forever
_ORIGINAL_SCHEDULER_EXECUTE_TASK = AutomationScheduler._execute_task
PROJECT_ROOT = _ADB_RUNTIME_ROOT
SCHEDULE_CONFIG_PATH = PROJECT_ROOT / "schedule_config.json"


def _project_path_with_bundle_fallback(path: str | Path) -> Path:
    candidate = _ORIGINAL_PROJECT_PATH(path)
    if candidate.exists():
        return candidate
    raw = _Path(path)
    if raw.is_absolute():
        return candidate
    bundle_root = getattr(_sys, "_MEIPASS", None)
    for root in (_Path(bundle_root) if bundle_root else None, _ADB_RESOURCE_ROOT):
        if root is None:
            continue
        bundled = root / raw
        if bundled.exists():
            return bundled
    return candidate


_project_path = _project_path_with_bundle_fallback


def load_schedule_config(path: str | Path = SCHEDULE_CONFIG_PATH) -> dict[str, Any]:
    config_path = _Path(path)
    if not config_path.exists():
        bundle_config = _ADB_RESOURCE_ROOT / "schedule_config.json"
        if bundle_config.exists():
            return _sync_saved_wireless_serial(_ORIGINAL_LOAD_SCHEDULE_CONFIG(bundle_config))
    return _sync_saved_wireless_serial(_ORIGINAL_LOAD_SCHEDULE_CONFIG(path))


def _schedule_mode(config: dict[str, Any]) -> str:
    mode = str(config.get("mode", SCHEDULE_MODE_DAILY_TIMES)).strip() or SCHEDULE_MODE_DAILY_TIMES
    return mode


def _parse_finish_interval_hours(value: Any) -> float:
    if value is None or str(value).strip() == "":
        return DEFAULT_FINISH_INTERVAL_HOURS
    try:
        hours = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("结束后倒计时间隔必须是数字小时，例如 8 或 9") from exc
    if hours < MIN_FINISH_INTERVAL_HOURS or hours > MAX_FINISH_INTERVAL_HOURS:
        raise ValueError(
            f"结束后倒计时间隔必须在 {MIN_FINISH_INTERVAL_HOURS:g}-{MAX_FINISH_INTERVAL_HOURS:g} 小时之间"
        )
    return hours


def _parse_finish_interval_minutes(value: Any) -> int:
    if value is None or str(value).strip() == "":
        return DEFAULT_FINISH_INTERVAL_MINUTES
    try:
        minutes = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("结束后倒计时分钟必须是 0-59 的整数") from exc
    if minutes < 0 or minutes > 59:
        raise ValueError("结束后倒计时分钟必须是 0-59 的整数")
    return minutes


def _finish_interval_total_minutes(config: dict[str, Any]) -> int:
    hours = _parse_finish_interval_hours(config.get("interval_hours"))
    minutes = _parse_finish_interval_minutes(config.get("interval_minutes"))
    total_minutes = int(round(hours * 60)) + minutes
    if (
        total_minutes < MIN_FINISH_INTERVAL_TOTAL_MINUTES
        or total_minutes > MAX_FINISH_INTERVAL_TOTAL_MINUTES
    ):
        raise ValueError("结束后倒计时间隔必须在 1 分钟到 24 小时之间")
    return total_minutes


def _parse_hhmm_today(text: str, now: datetime | None = None) -> datetime | None:
    parts = text.split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    current = (now or _dt_datetime.now(BEIJING_TZ)).astimezone(BEIJING_TZ)
    return current.replace(hour=hour, minute=minute, second=0, microsecond=0)


def parse_last_finished_at(value: Any, now: datetime | None = None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None

    hhmm_value = _parse_hhmm_today(text, now)
    if hhmm_value is not None:
        return hhmm_value

    iso_text = text.replace("T", " ")
    if iso_text.endswith("Z"):
        iso_text = iso_text[:-1] + "+00:00"

    parsed = None
    try:
        parsed = _dt_datetime.fromisoformat(iso_text)
    except ValueError:
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ):
            try:
                parsed = _dt_datetime.strptime(text, fmt)
                break
            except ValueError:
                pass

    if parsed is None:
        raise ValueError("上次运行完毕时间必须是 YYYY-MM-DD HH:MM，或 HH:MM 表示今天")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=BEIJING_TZ)
    return parsed.astimezone(BEIJING_TZ)


def format_last_finished_at(value: datetime) -> str:
    return value.astimezone(BEIJING_TZ).replace(second=0, microsecond=0).strftime(LAST_FINISHED_AT_FORMAT)


def normalize_last_finished_at(value: Any, now: datetime | None = None) -> str:
    parsed = parse_last_finished_at(value, now)
    if parsed is None:
        return ""
    return format_last_finished_at(parsed)


def format_finish_interval_hours(hours: Any, minutes: Any = 0) -> str:
    total_minutes = _finish_interval_total_minutes(
        {"interval_hours": hours, "interval_minutes": minutes}
    )
    hour_value, minute_value = divmod(total_minutes, 60)
    parts = []
    if hour_value:
        parts.append(f"{hour_value}小时")
    if minute_value:
        parts.append(f"{minute_value}分钟")
    return "".join(parts) if parts else "0分钟"


def normalize_schedule_config(config: dict[str, Any]) -> dict[str, Any]:
    source = config if isinstance(config, dict) else {}
    normalized = _ORIGINAL_NORMALIZE_SCHEDULE_CONFIG(source)
    mode = _schedule_mode(source)
    normalized["mode"] = mode
    normalized["interval_hours"] = _parse_finish_interval_hours(source.get("interval_hours"))
    normalized["interval_minutes"] = _parse_finish_interval_minutes(source.get("interval_minutes"))
    normalized[LAST_FINISHED_AT_KEY] = normalize_last_finished_at(source.get(LAST_FINISHED_AT_KEY))
    return normalized


def validate_schedule_config(config: dict[str, Any]) -> None:
    target = config.get("target")
    if target not in SCHEDULE_TARGETS:
        raise ValueError("定时任务目标必须是 full_flow、delta_force、qq_switch 或 script")

    mode = _schedule_mode(config)
    if mode not in SCHEDULE_MODES:
        raise ValueError("定时模式必须是 daily_times 或 finish_interval")

    config_for_base_validation = dict(config)
    config_for_base_validation["daily_times"] = ["08:00", "20:00"]
    if mode == SCHEDULE_MODE_DAILY_TIMES:
        daily_times = normalize_daily_times(config.get("daily_times"))
        if (
            len(daily_times) < MIN_DAILY_TIME_COUNT
            or len(daily_times) > MAX_DAILY_TIME_COUNT
            or len(set(daily_times)) != len(daily_times)
        ):
            raise ValueError("每天固定时间必须填写 1-4 个 HH:MM")
    else:
        _finish_interval_total_minutes(config)
    if config.get(LAST_FINISHED_AT_KEY):
        normalize_last_finished_at(config.get(LAST_FINISHED_AT_KEY))

    _ORIGINAL_VALIDATE_SCHEDULE_CONFIG(config_for_base_validation)


def _finish_interval_next_run_info(
    now: datetime,
    config: dict[str, Any],
) -> tuple[datetime, datetime | None, int]:
    current = now.astimezone(BEIJING_TZ)
    interval_minutes = _finish_interval_total_minutes(config)
    anchor = parse_last_finished_at(config.get(LAST_FINISHED_AT_KEY), current)
    if anchor is None:
        return current + timedelta(minutes=interval_minutes), None, 0
    candidate = anchor + timedelta(minutes=interval_minutes)
    if candidate <= current:
        interval_seconds = interval_minutes * 60
        skipped = int((current - candidate).total_seconds() // interval_seconds) + 1
        candidate += timedelta(minutes=interval_minutes * skipped)
        return candidate, anchor, skipped
    return candidate, anchor, 0


def _schedule_next_with_finish_interval(self: AutomationScheduler, now: datetime) -> None:
    if _schedule_mode(self.config) != SCHEDULE_MODE_FINISH_INTERVAL:
        _ORIGINAL_SCHEDULER_SCHEDULE_NEXT(self, now)
        return
    self.next_run_at, anchor, skipped = _finish_interval_next_run_info(now, self.config)
    interval_label = format_finish_interval_hours(self.config.get("interval_hours"), self.config.get("interval_minutes"))
    if anchor is not None and skipped:
        self.log(
            f"倒计时起算点: {format_last_finished_at(anchor)}，间隔 {interval_label}，"
            f"已顺延 {skipped} 个过期周期，下次运行: {format_beijing_time(self.next_run_at)}"
        )
        return
    if anchor is not None:
        self.log(
            f"倒计时起算点: {format_last_finished_at(anchor)}，间隔 {interval_label}，"
            f"下次运行: {format_beijing_time(self.next_run_at)}"
        )
        return
    self.log(
        f"倒计时开始: {interval_label} 后运行，"
        f"下次运行: {format_beijing_time(self.next_run_at)}"
    )


def next_run_time(now: datetime, config: dict[str, Any]) -> datetime:
    if _schedule_mode(config) == SCHEDULE_MODE_FINISH_INTERVAL:
        next_at, _anchor, _skipped = _finish_interval_next_run_info(now, config)
        return next_at
    return _ORIGINAL_NEXT_RUN_TIME(now, config)


def _run_forever_with_finish_interval(self: AutomationScheduler) -> None:
    if _schedule_mode(self.config) != SCHEDULE_MODE_FINISH_INTERVAL:
        _ORIGINAL_SCHEDULER_RUN_FOREVER(self)
        return

    if not self.config.get("enabled", False):
        self.log("定时任务未启用，已退出。请先在 schedule_config.json 或 GUI 中启用。")
        return

    target_label = SCHEDULE_TARGETS.get(str(self.config["target"]), str(self.config["target"]))
    interval_label = format_finish_interval_hours(self.config.get("interval_hours"), self.config.get("interval_minutes"))
    self.log(f"定时任务已启动: {target_label}，每次任务结束后倒计时 {interval_label} 再运行")

    if self.config.get("run_on_start", False) and not self.stop_event.is_set():
        self.log("已配置启动后立即执行一次")
        self._execute_task()
        if self.stop_event.is_set():
            self.log("定时任务已停止")
            return

    self._schedule_next(datetime.now(BEIJING_TZ))

    while not self.stop_event.is_set():
        while not self.stop_event.is_set():
            if self.next_run_at is None:
                raise AssertionError
            now = datetime.now(BEIJING_TZ)
            if now >= self.next_run_at:
                break
            seconds = max(0.0, (self.next_run_at - now).total_seconds())
            self.stop_event.wait(min(30.0, seconds))
        if self.stop_event.is_set():
            break

        self.log("倒计时结束，开始本轮任务")
        self._execute_task()
        if self.stop_event.is_set():
            break
        self._schedule_next(datetime.now(BEIJING_TZ))

    self.log("定时任务已停止")


def _is_wireless_serial(value: object) -> bool:
    text = str(value or "").strip()
    if ":" not in text:
        return False
    host, port = text.rsplit(":", 1)
    return bool(host.strip()) and port.isdigit()


def _saved_wireless_serial() -> str:
    path = PROJECT_ROOT / "wireless_adb.json"
    try:
        import json as _json

        data = _json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    serial = str(data.get("serial") or "").strip()
    if _is_wireless_serial(serial):
        return serial
    host = str(data.get("host") or "").strip()
    port = data.get("connect_port")
    if host and str(port or "").isdigit():
        serial = f"{host}:{int(port)}"
        if _is_wireless_serial(serial):
            return serial
    return ""


def _sync_saved_wireless_serial(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        return config
    saved = _saved_wireless_serial()
    if not saved:
        return config
    mode = str(config.get("connection_mode") or "").strip()
    if mode == "wireless" or _is_wireless_serial(config.get("serial")) or _is_wireless_serial(config.get("wireless_serial")):
        config = dict(config)
        config["connection_mode"] = "wireless"
        config["serial"] = saved
        config["wireless_serial"] = saved
    return config


def _resolve_wireless_serial_from_config(config: dict[str, Any]) -> str:
    for key in ("serial", "wireless_serial"):
        value = str(config.get(key) or "").strip()
        if _is_wireless_serial(value):
            return value
    return ""


def _auto_connect_wireless_for_schedule(log) -> str:
    try:
        from .wireless_adb import auto_connect_saved

        connected, serial, message = auto_connect_saved()
        if message:
            log(f"Wireless ADB: {message}")
        if connected and _is_wireless_serial(serial):
            return serial
    except Exception as exc:
        log(f"Wireless ADB: auto discovery failed: {exc}")
    return ""


def _record_last_finished_at(config: dict[str, Any], finished_at: datetime, log) -> None:
    if _schedule_mode(config) != SCHEDULE_MODE_FINISH_INTERVAL:
        return
    value = format_last_finished_at(finished_at)
    config[LAST_FINISHED_AT_KEY] = value

    try:
        try:
            payload = _json.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload[LAST_FINISHED_AT_KEY] = value
        SCHEDULE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCHEDULE_CONFIG_PATH.write_text(
            _json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log(f"已记录上次运行完毕时间: {value}")
    except Exception as exc:
        log(f"记录上次运行完毕时间失败: {exc}")


def _execute_task_with_wireless_reconnect(self: AutomationScheduler) -> None:
    mode = str(self.config.get("connection_mode") or "").strip()
    serial = _resolve_wireless_serial_from_config(self.config)
    should_reconnect = mode == "wireless" or _is_wireless_serial(self.config.get("serial"))
    auto_connected = False
    if should_reconnect and not serial:
        serial = _auto_connect_wireless_for_schedule(self.log)
        auto_connected = bool(serial)
        if serial:
            self.config["serial"] = serial
            self.config["wireless_serial"] = serial
    if should_reconnect and serial and not auto_connected:
        try:
            from .wireless_adb import connect_serial

            self.log(f"无线 ADB: 定时任务开始前确认连接 {serial}")
            resolved_serial, message = connect_serial(serial)
            self.config["serial"] = resolved_serial
            self.config["wireless_serial"] = resolved_serial
            self.log(f"无线 ADB: {message}")
        except Exception as exc:
            self.log(f"无线 ADB: 自动连接失败：{exc}")
    try:
        from .preflight import run_preflight

        check = run_preflight(
            serial=str(self.config.get("serial") or ""),
            connection_mode=mode,
            workflow_config=self.config,
            auto_fix=True,
        )
        for line in check.lines():
            self.log(line)
        if check.serial:
            self.config["serial"] = check.serial
            if _is_wireless_serial(check.serial):
                self.config["wireless_serial"] = check.serial
        if not check.ok:
            self.log("Preflight blocked this scheduled run.")
            return None
    except Exception as exc:
        self.log(f"Preflight check failed: {exc}")
        return None
    result = _ORIGINAL_SCHEDULER_EXECUTE_TASK(self)
    _record_last_finished_at(self.config, datetime.now(BEIJING_TZ), self.log)
    return result


AutomationScheduler._schedule_next = _schedule_next_with_finish_interval
AutomationScheduler.run_forever = _run_forever_with_finish_interval
AutomationScheduler._execute_task = _execute_task_with_wireless_reconnect
