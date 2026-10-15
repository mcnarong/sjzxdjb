$PowerLogPath = 'D:\github\ADBAutomation_recovered\log\power_events.log'
function Write-DeltaAssistantPowerLog {
    param([string]$Message)
    $dir = Split-Path -Parent $PowerLogPath
    if ($dir) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $stamp = Get-Date -Format 'HH:mm:ss'
    Add-Content -LiteralPath $PowerLogPath -Value "[$stamp] 电脑电源: $Message" -Encoding UTF8
}

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
