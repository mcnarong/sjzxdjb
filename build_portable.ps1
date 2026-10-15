$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt

$DistRoot = Join-Path $PWD "dist\ADBAutomation"
$PreservedScheduleConfig = $null
$ExistingScheduleConfig = Join-Path $DistRoot "schedule_config.json"
if (Test-Path -LiteralPath $ExistingScheduleConfig) {
  $PreservedScheduleConfig = Join-Path $env:TEMP ("ADBAutomation_schedule_config_{0}.json" -f [guid]::NewGuid().ToString("N"))
  Copy-Item -LiteralPath $ExistingScheduleConfig -Destination $PreservedScheduleConfig -Force
}

# The recovered project loads the original application bytecode from
# recovered_bytecode at runtime. PyInstaller cannot see those imports
# statically, so keep this hidden-import list in sync with adb_automation/*.pyc.
pyinstaller --noconfirm --clean --windowed --name ADBAutomation `
  --icon "assets\app_icon.ico" `
  --hidden-import adb_automation.adb `
  --hidden-import adb_automation.calibration `
  --hidden-import adb_automation.cli `
  --hidden-import adb_automation.adb_keepalive `
  --hidden-import adb_automation.desktop_app `
  --hidden-import adb_automation.diagnostics `
  --hidden-import adb_automation.delta_force_calibrator `
  --hidden-import adb_automation.failure_guidance `
  --hidden-import adb_automation.gui `
  --hidden-import adb_automation.license_gate `
  --hidden-import adb_automation.maintenance `
  --hidden-import adb_automation.run_log `
  --hidden-import adb_automation.scheduler `
  --hidden-import adb_automation.script_runner `
  --hidden-import adb_automation.webapp `
  --hidden-import adb_automation.wireless_adb `
  --hidden-import adb_automation.workflows `
  --hidden-import PIL `
  --hidden-import PIL.Image `
  --hidden-import PIL.ImageChops `
  --hidden-import PIL.ImageTk `
  --hidden-import tkinter `
  --hidden-import tkinter.filedialog `
  --hidden-import tkinter.messagebox `
  --hidden-import tkinter.simpledialog `
  --hidden-import tkinter.ttk `
  --collect-submodules tkinter `
  --collect-submodules PIL `
  --add-data "recovered_bytecode;recovered_bytecode" `
  --add-data "device_profiles;device_profiles" `
  --add-data "examples;examples" `
  --add-data "platform-tools;platform-tools" `
  --add-data "assets;assets" `
  main.py

foreach ($Name in @("device_profiles", "examples", "platform-tools", "assets")) {
  $Source = Join-Path $PWD $Name
  $Destination = Join-Path $DistRoot $Name
  if (Test-Path -LiteralPath $Source) {
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
  }
}
foreach ($Name in @("README.md", "README_RECOVERY.md", "必看说明.txt", "schedule_config.json")) {
  $Source = Join-Path $PWD $Name
  if (Test-Path -LiteralPath $Source) {
    Copy-Item -LiteralPath $Source -Destination (Join-Path $DistRoot $Name) -Force
  }
}
if ($PreservedScheduleConfig -and (Test-Path -LiteralPath $PreservedScheduleConfig)) {
  Copy-Item -LiteralPath $PreservedScheduleConfig -Destination (Join-Path $DistRoot "schedule_config.json") -Force
  Remove-Item -LiteralPath $PreservedScheduleConfig -Force
}
New-Item -ItemType Directory -Force -Path (Join-Path $DistRoot "captures") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $DistRoot "log") | Out-Null

Set-Content -LiteralPath (Join-Path $DistRoot "00-device-check.bat") -Encoding ASCII -Value @"
@echo off
chcp 65001 >nul
cd /d "%~dp0"
"ADBAutomation.exe" doctor --screenshot
pause
"@

Set-Content -LiteralPath (Join-Path $DistRoot "01-start-gui.bat") -Encoding ASCII -Value @"
@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" "ADBAutomation.exe"
"@

Set-Content -LiteralPath (Join-Path $DistRoot "02-start-schedule.bat") -Encoding ASCII -Value @"
@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_schedule_with_log.ps1"
pause
"@

Set-Content -LiteralPath (Join-Path $DistRoot "start_schedule_with_log.ps1") -Encoding UTF8 -Value @'
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

$Exe = Join-Path $Root "ADBAutomation.exe"
$ResolvedExe = (Resolve-Path -LiteralPath $Exe).Path
$Existing = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -eq "ADBAutomation.exe" -and
        $_.CommandLine -like "* schedule*" -and
        $_.ExecutablePath -eq $ResolvedExe
    } |
    Select-Object -First 1

if ($Existing) {
    Write-Host "Schedule is already running. PID: $($Existing.ProcessId)"
} else {
    $Process = Start-Process -FilePath $Exe -ArgumentList "schedule" -PassThru
    Write-Host "Schedule started. PID: $($Process.Id)"
}

$LogDir = Join-Path $Root "log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$LogFile = $null
for ($i = 0; $i -lt 20 -and -not $LogFile; $i++) {
    $LogFile = Get-ChildItem -LiteralPath $LogDir -Filter "*.log" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $LogFile) {
        Start-Sleep -Milliseconds 500
    }
}

if ($LogFile) {
    Write-Host "Log file: $($LogFile.FullName)"
    Write-Host "Showing latest 30 log lines. Closing this window does not stop the schedule process."
    Get-Content -LiteralPath $LogFile.FullName -Encoding UTF8 -Tail 30 -Wait
} else {
    Write-Host "No log file found. Check the log directory."
}
'@
