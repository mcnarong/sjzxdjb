param(
  [switch]$InstallBuildDeps
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ProjectRoot = (Resolve-Path -LiteralPath $PWD).Path

function Remove-GeneratedDirectory {
  param([string]$RelativePath)

  $Target = Join-Path $ProjectRoot $RelativePath
  $ResolvedParent = (Resolve-Path -LiteralPath (Split-Path -Parent $Target)).Path
  if (-not $Target.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path outside project root: $Target"
  }
  if (-not $ResolvedParent.StartsWith($ProjectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove path with parent outside project root: $Target"
  }
  if (Test-Path -LiteralPath $Target) {
    Remove-Item -LiteralPath $Target -Recurse -Force
  }
}

function Invoke-Checked {
  param(
    [string]$FilePath,
    [string[]]$Arguments
  )

  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "$FilePath failed with exit code $LASTEXITCODE"
  }
}

if ($InstallBuildDeps) {
  py -3.13 -m pip install -r requirements.txt
  py -3.13 -m pip install -r requirements-build.txt
}

$DistRoot = Join-Path $PWD "dist_release"
$PreserveRoot = Join-Path $PWD ".dist_release_preserve"
$IconPath = Join-Path $ProjectRoot "assets\app_icon.ico"
$RecoveredBytecode = Join-Path $ProjectRoot "recovered_bytecode"
$DeviceProfiles = Join-Path $ProjectRoot "device_profiles"
$Examples = Join-Path $ProjectRoot "examples"
$PlatformTools = Join-Path $ProjectRoot "platform-tools"
$Assets = Join-Path $ProjectRoot "assets"
$MainEntry = Join-Path $ProjectRoot "main.py"
$GeneratorEntry = Join-Path $ProjectRoot "license_generator.pyw"

$PreservedFiles = @(
  "gitee_token.txt",
  "wireless_adb.json",
  "wait_settings.json",
  "power_control.json",
  "schedule_config.json",
  "activation.dat",
  "revocation_cache.dat"
)
$PreservedDirectories = @(
  "archives",
  "captures",
  "debug_crops",
  "device_profiles",
  "log"
)

# 上次打包中途失败时会留下保留目录，此时 dist_release 仍存在，
# 必须沿用旧的保留文件，否则会把用户已丢失的配置当作已废弃。
if ((Test-Path -LiteralPath $PreserveRoot) -and (-not (Test-Path -LiteralPath $DistRoot))) {
  Remove-GeneratedDirectory ".dist_release_preserve"
}
if (Test-Path -LiteralPath $DistRoot) {
  New-Item -ItemType Directory -Force -Path $PreserveRoot | Out-Null
  foreach ($Name in $PreservedFiles) {
    $Source = Join-Path $DistRoot $Name
    if (Test-Path -LiteralPath $Source) {
      Copy-Item -LiteralPath $Source -Destination (Join-Path $PreserveRoot $Name) -Force
    }
  }
  foreach ($Name in $PreservedDirectories) {
    $Source = Join-Path $DistRoot $Name
    if (Test-Path -LiteralPath $Source) {
      Copy-Item -LiteralPath $Source -Destination (Join-Path $PreserveRoot $Name) -Recurse -Force
    }
  }
}

foreach ($Path in @("build_single", "build_single_generator", "dist_release", "__pycache__", "adb_automation\__pycache__")) {
  Remove-GeneratedDirectory $Path
}

New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null

Invoke-Checked "py" @(
  "-3.13", "-m", "PyInstaller",
  "--noconfirm", "--clean", "--windowed", "--onefile", "--name", "ADBAutomation",
  "--distpath", "$DistRoot",
  "--workpath", "build_single",
  "--specpath", "build_single",
  "--icon", "$IconPath",
  "--hidden-import", "adb_automation.adb",
  "--hidden-import", "adb_automation.calibration",
  "--hidden-import", "adb_automation.cli",
  "--hidden-import", "adb_automation.adb_keepalive",
  "--hidden-import", "adb_automation.desktop_app",
  "--hidden-import", "adb_automation.diagnostics",
  "--hidden-import", "adb_automation.delta_force_calibrator",
  "--hidden-import", "adb_automation.failure_guidance",
  "--hidden-import", "adb_automation.gui",
  "--hidden-import", "adb_automation.license_gate",
  "--hidden-import", "adb_automation.maintenance",
  "--hidden-import", "adb_automation.power_control",
  "--hidden-import", "adb_automation.preflight",
  "--hidden-import", "adb_automation.run_log",
  "--hidden-import", "adb_automation.scheduler",
  "--hidden-import", "adb_automation.script_runner",
  "--hidden-import", "adb_automation.webapp",
  "--hidden-import", "adb_automation.wait_settings",
  "--hidden-import", "adb_automation.wireless_adb",
  "--hidden-import", "adb_automation.workflows",
  "--hidden-import", "PIL",
  "--hidden-import", "PIL.Image",
  "--hidden-import", "PIL.ImageChops",
  "--hidden-import", "PIL.ImageTk",
  "--hidden-import", "tkinter",
  "--hidden-import", "tkinter.filedialog",
  "--hidden-import", "tkinter.messagebox",
  "--hidden-import", "tkinter.simpledialog",
  "--hidden-import", "tkinter.ttk",
  "--collect-submodules", "tkinter",
  "--collect-submodules", "PIL",
  "--add-data", "$RecoveredBytecode;recovered_bytecode",
  "--add-data", "$DeviceProfiles;device_profiles",
  "--add-data", "$Examples;examples",
  "--add-data", "$PlatformTools;platform-tools",
  "--add-data", "$Assets;assets",
  "$MainEntry"
)

Invoke-Checked "py" @(
  "-3.13", "-m", "PyInstaller",
  "--noconfirm", "--clean", "--windowed", "--onefile", "--name", "ADBLicenseGenerator",
  "--distpath", "$DistRoot",
  "--workpath", "build_single_generator",
  "--specpath", "build_single_generator",
  "--icon", "$IconPath",
  "--hidden-import", "adb_automation.license_gate",
  "--hidden-import", "tkinter",
  "--hidden-import", "tkinter.messagebox",
  "--hidden-import", "tkinter.ttk",
  "$GeneratorEntry"
)

foreach ($Path in @("build_single", "build_single_generator", "__pycache__", "adb_automation\__pycache__")) {
  Remove-GeneratedDirectory $Path
}

if (Test-Path -LiteralPath $PreserveRoot) {
  foreach ($Name in $PreservedFiles) {
    $Source = Join-Path $PreserveRoot $Name
    if (Test-Path -LiteralPath $Source) {
      Copy-Item -LiteralPath $Source -Destination (Join-Path $DistRoot $Name) -Force
    }
  }
  foreach ($Name in $PreservedDirectories) {
    $Source = Join-Path $PreserveRoot $Name
    if (Test-Path -LiteralPath $Source) {
      Copy-Item -LiteralPath $Source -Destination (Join-Path $DistRoot $Name) -Recurse -Force
    }
  }
}

foreach ($Name in $PreservedFiles) {
  $Destination = Join-Path $DistRoot $Name
  $Source = Join-Path $ProjectRoot $Name
  if ((-not (Test-Path -LiteralPath $Destination)) -and (Test-Path -LiteralPath $Source)) {
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
  }
}

Remove-GeneratedDirectory ".dist_release_preserve"

Write-Host "Built exe files:"
Write-Host (Join-Path $DistRoot "ADBAutomation.exe")
Write-Host (Join-Path $DistRoot "ADBLicenseGenerator.exe")
