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
