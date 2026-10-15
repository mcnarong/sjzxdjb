from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from .adb import RUNTIME_ROOT


POWER_CONFIG_FILENAME = "power_control.json"
POWER_CONFIG_PATH = RUNTIME_ROOT / POWER_CONFIG_FILENAME
POWER_TASK_NAME = "DeltaAssistantPowerAction"
WAKE_TASK_NAME = "DeltaAssistantWake"
WAKE_DISPLAY_SCRIPT_NAME = "delta_assistant_wake_display.ps1"
SLEEP_COUNTDOWN_SCRIPT_NAME = "delta_assistant_sleep_countdown.ps1"
POWER_EVENT_LOG_FILENAME = "power_events.log"


POWER_ACTIONS = {
    "shutdown": {
        "label": "关机",
        "command": "shutdown.exe",
        "args": lambda force: "/s /t 0" + (" /f" if force else ""),
    },
    "restart": {
        "label": "重启",
        "command": "shutdown.exe",
        "args": lambda force: "/r /t 0" + (" /f" if force else ""),
    },
    "sleep": {
        "label": "睡眠",
        "command": "powershell.exe",
        "args": lambda force: (
            "-NoProfile -WindowStyle Hidden -Command "
            "\"Add-Type -AssemblyName System.Windows.Forms; "
            "[System.Windows.Forms.Application]::SetSuspendState('Suspend',$false,$false)\""
        ),
    },
    "hibernate": {
        "label": "休眠",
        "command": "shutdown.exe",
        "args": lambda force: "/h",
    },
}


DEFAULT_POWER_CONFIG = {
    "power_action": "shutdown",
    "power_time": "23:30",
    "force_close": False,
    "wake_time": "08:00",
}


def power_action_items() -> list[tuple[str, str]]:
    return [(key, value["label"]) for key, value in POWER_ACTIONS.items()]


def action_label(action: str) -> str:
    return POWER_ACTIONS.get(action, POWER_ACTIONS["shutdown"])["label"]


def action_from_label(label: str) -> str:
    for key, value in POWER_ACTIONS.items():
        if value["label"] == label:
            return key
    return "shutdown"


def load_power_config(path: Path | None = None) -> dict:
    target = path or POWER_CONFIG_PATH
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_POWER_CONFIG)
    if not isinstance(payload, dict):
        return dict(DEFAULT_POWER_CONFIG)
    config = dict(DEFAULT_POWER_CONFIG)
    config.update(payload)
    config["power_action"] = config["power_action"] if config["power_action"] in POWER_ACTIONS else "shutdown"
    config["power_time"] = normalize_hhmm(config.get("power_time"), DEFAULT_POWER_CONFIG["power_time"])
    config["wake_time"] = normalize_hhmm(config.get("wake_time"), DEFAULT_POWER_CONFIG["wake_time"])
    config["force_close"] = bool(config.get("force_close", False))
    return config


def save_power_config(config: dict, path: Path | None = None) -> dict:
    target = path or POWER_CONFIG_PATH
    normalized = load_power_config(path=None)
    normalized.update(config)
    normalized["power_action"] = (
        normalized["power_action"] if normalized["power_action"] in POWER_ACTIONS else "shutdown"
    )
    normalized["power_time"] = normalize_hhmm(normalized.get("power_time"), DEFAULT_POWER_CONFIG["power_time"])
    normalized["wake_time"] = normalize_hhmm(normalized.get("wake_time"), DEFAULT_POWER_CONFIG["wake_time"])
    normalized["force_close"] = bool(normalized.get("force_close", False))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized


def normalize_hhmm(value, fallback: str | None = None) -> str:
    text = str(value or "").strip()
    try:
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError
        return f"{hour:02d}:{minute:02d}"
    except (TypeError, ValueError):
        if fallback is not None:
            return normalize_hhmm(fallback)
        raise ValueError("时间格式必须是 HH:MM，例如 23:30")


def next_run_datetime(hhmm: str, now: datetime | None = None) -> datetime:
    normalized = normalize_hhmm(hhmm)
    hour, minute = (int(part) for part in normalized.split(":", 1))
    current = now or datetime.now()
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return target


def _power_action_datetimes(action: str, hhmm: str) -> tuple[datetime, datetime]:
    actual_at = next_run_datetime(hhmm)
    start_at = actual_at
    if action == "sleep":
        candidate = actual_at - timedelta(seconds=10)
        if candidate > datetime.now():
            start_at = candidate
    return start_at, actual_at


def _run_schtasks(args: list[str]) -> str:
    completed = subprocess.run(
        ["schtasks.exe", *args],
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        raise RuntimeError(output or f"schtasks failed with exit code {completed.returncode}")
    return output


def power_event_log_path() -> Path:
    return RUNTIME_ROOT / "log" / POWER_EVENT_LOG_FILENAME


def _ps_single_quoted(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _power_log_function_text() -> str:
    return "$PowerLogPath = " + _ps_single_quoted(power_event_log_path()) + r"""
function Write-DeltaAssistantPowerLog {
    param([string]$Message)
    $dir = Split-Path -Parent $PowerLogPath
    if ($dir) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $stamp = Get-Date -Format 'HH:mm:ss'
    Add-Content -LiteralPath $PowerLogPath -Value "[$stamp] 电脑电源: $Message" -Encoding UTF8
}
"""


def _wake_display_script_path() -> Path:
    return RUNTIME_ROOT / WAKE_DISPLAY_SCRIPT_NAME


def _sleep_countdown_script_path() -> Path:
    return RUNTIME_ROOT / SLEEP_COUNTDOWN_SCRIPT_NAME


def _wake_display_script_text() -> str:
    return _power_log_function_text() + r"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class DeltaAssistantWakeDisplay {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);

    [DllImport("user32.dll")]
    public static extern IntPtr SendMessage(IntPtr hWnd, int Msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);

    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
}
"@

$ES_CONTINUOUS = 0x80000000
$ES_SYSTEM_REQUIRED = 0x00000001
$ES_DISPLAY_REQUIRED = 0x00000002
$HWND_BROADCAST = [IntPtr]0xffff
$WM_SYSCOMMAND = 0x0112
$SC_MONITORPOWER = [IntPtr]0xF170
$MONITOR_ON = [IntPtr](-1)
$MOUSEEVENTF_MOVE = 0x0001
$VK_SHIFT = 0x10
$KEYEVENTF_KEYUP = 0x0002

Write-DeltaAssistantPowerLog '系统已按计划唤醒，正在点亮屏幕'
[DeltaAssistantWakeDisplay]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_DISPLAY_REQUIRED) | Out-Null
Start-Sleep -Milliseconds 500
[DeltaAssistantWakeDisplay]::SendMessage($HWND_BROADCAST, $WM_SYSCOMMAND, $SC_MONITORPOWER, $MONITOR_ON) | Out-Null
Start-Sleep -Milliseconds 500
[DeltaAssistantWakeDisplay]::mouse_event($MOUSEEVENTF_MOVE, 1, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 100
[DeltaAssistantWakeDisplay]::mouse_event($MOUSEEVENTF_MOVE, 4294967295, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 100
[DeltaAssistantWakeDisplay]::keybd_event($VK_SHIFT, 0, 0, [UIntPtr]::Zero)
Start-Sleep -Milliseconds 60
[DeltaAssistantWakeDisplay]::keybd_event($VK_SHIFT, 0, $KEYEVENTF_KEYUP, [UIntPtr]::Zero)
Start-Sleep -Seconds 10
[DeltaAssistantWakeDisplay]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null
Write-DeltaAssistantPowerLog '系统开启完毕，继续执行定时任务'
"""


def _sleep_countdown_script_text() -> str:
    return _power_log_function_text() + r"""
$ErrorActionPreference = 'SilentlyContinue'
Write-DeltaAssistantPowerLog '10秒后系统睡眠'
Start-Sleep -Seconds 5
Write-DeltaAssistantPowerLog '5秒后系统睡眠'
Start-Sleep -Seconds 2
Write-DeltaAssistantPowerLog '3秒后系统睡眠'
Start-Sleep -Seconds 1
Write-DeltaAssistantPowerLog '2秒后系统睡眠'
Start-Sleep -Seconds 1
Write-DeltaAssistantPowerLog '1秒后系统睡眠'
Start-Sleep -Seconds 1
Write-DeltaAssistantPowerLog '系统进入睡眠'
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::SetSuspendState('Suspend',$false,$false) | Out-Null
"""


def _ensure_wake_display_script() -> Path:
    path = _wake_display_script_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_wake_display_script_text(), encoding="utf-8-sig")
    return path


def _ensure_sleep_countdown_script() -> Path:
    path = _sleep_countdown_script_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_sleep_countdown_script_text(), encoding="utf-8-sig")
    return path


def _wake_display_command() -> tuple[str, str]:
    script_path = _ensure_wake_display_script()
    arguments = (
        "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden "
        f'-File "{script_path}"'
    )
    return "powershell.exe", arguments


def _sleep_countdown_command() -> tuple[str, str]:
    script_path = _ensure_sleep_countdown_script()
    arguments = (
        "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden "
        f'-File "{script_path}"'
    )
    return "powershell.exe", arguments


def _power_action_command(action: str, force_close: bool = False) -> tuple[str, str]:
    if action == "sleep":
        return _sleep_countdown_command()
    item = POWER_ACTIONS[action]
    return item["command"], item["args"](force_close)


def _current_user_id() -> str:
    domain = os.environ.get("USERDOMAIN", "").strip()
    username = os.environ.get("USERNAME", "").strip()
    if domain and username:
        return f"{domain}\\{username}"
    return username or "INTERACTIVE"


def _trigger_xml(start_at: datetime, daily: bool = False) -> str:
    boundary = start_at.strftime("%Y-%m-%dT%H:%M:%S")
    if daily:
        return f"""<CalendarTrigger>
      <StartBoundary>{boundary}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>"""
    return f"""<TimeTrigger>
      <StartBoundary>{boundary}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>"""


def _task_xml(
    start_at: datetime,
    command: str,
    arguments: str = "",
    wake_to_run: bool = False,
    daily: bool = False,
) -> str:
    wake_value = "true" if wake_to_run else "false"
    user_id = escape(_current_user_id())
    command_text = escape(command)
    args_text = escape(arguments)
    trigger_xml = _trigger_xml(start_at, daily)
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Created by Delta Assistant.</Description>
  </RegistrationInfo>
  <Triggers>
    {trigger_xml}
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user_id}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>{wake_value}</WakeToRun>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command_text}</Command>
      <Arguments>{args_text}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def _create_task(
    task_name: str,
    start_at: datetime,
    command: str,
    arguments: str = "",
    wake_to_run: bool = False,
    daily: bool = False,
) -> str:
    xml_text = _task_xml(start_at, command, arguments, wake_to_run, daily)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-16",
            suffix=".xml",
            prefix="delta_assistant_task_",
            dir=str(RUNTIME_ROOT),
            delete=False,
        ) as handle:
            handle.write(xml_text)
            temp_path = Path(handle.name)
        return _run_schtasks(["/Create", "/TN", task_name, "/XML", str(temp_path), "/F"])
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass


def schedule_power_action(action: str, hhmm: str, force_close: bool = False) -> str:
    if action not in POWER_ACTIONS:
        raise ValueError("电源动作不正确")
    start_at, actual_at = _power_action_datetimes(action, hhmm)
    item = POWER_ACTIONS[action]
    command, arguments = _power_action_command(action, force_close)
    _create_task(
        POWER_TASK_NAME,
        start_at,
        command,
        arguments,
        wake_to_run=False,
    )
    return f"已创建{item['label']}计划：{actual_at.strftime('%Y-%m-%d %H:%M')}"


def schedule_daily_power_action(action: str, hhmm: str, force_close: bool = False) -> str:
    if action not in POWER_ACTIONS:
        raise ValueError("电源动作不正确")
    start_at, _actual_at = _power_action_datetimes(action, hhmm)
    item = POWER_ACTIONS[action]
    command, arguments = _power_action_command(action, force_close)
    _create_task(
        POWER_TASK_NAME,
        start_at,
        command,
        arguments,
        wake_to_run=False,
        daily=True,
    )
    return f"已创建每天{item['label']}计划：{normalize_hhmm(hhmm)}"


def schedule_wake(hhmm: str) -> str:
    start_at = next_run_datetime(hhmm)
    command, arguments = _wake_display_command()
    _create_task(WAKE_TASK_NAME, start_at, command, arguments, wake_to_run=True)
    return f"已创建唤醒计划：{start_at.strftime('%Y-%m-%d %H:%M')}，唤醒后会点亮屏幕"


def schedule_daily_wake(hhmm: str) -> str:
    start_at = next_run_datetime(hhmm)
    command, arguments = _wake_display_command()
    _create_task(WAKE_TASK_NAME, start_at, command, arguments, wake_to_run=True, daily=True)
    return f"已创建每天唤醒计划：{normalize_hhmm(hhmm)}，唤醒后会点亮屏幕"


def schedule_daily_sleep_wake_cycle(sleep_time: str, wake_time: str, force_close: bool = False) -> str:
    sleep_hhmm = normalize_hhmm(sleep_time)
    wake_hhmm = normalize_hhmm(wake_time)
    sleep_created = False
    try:
        schedule_daily_power_action("sleep", sleep_hhmm, force_close)
        sleep_created = True
        schedule_daily_wake(wake_hhmm)
    except Exception:
        if sleep_created:
            cancel_power_action()
        raise
    return f"已创建每天省电循环：{sleep_hhmm} 睡眠，{wake_hhmm} 唤醒"


def cancel_power_action() -> str:
    try:
        _run_schtasks(["/Delete", "/TN", POWER_TASK_NAME, "/F"])
    except RuntimeError:
        pass
    try:
        subprocess.run(
            ["shutdown.exe", "/a"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass
    return "已取消关机/重启/睡眠计划"


def cancel_wake() -> str:
    try:
        _run_schtasks(["/Delete", "/TN", WAKE_TASK_NAME, "/F"])
    except RuntimeError:
        pass
    return "已取消唤醒计划"
