$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

$Existing = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -like "python*" -and
        $_.CommandLine -like "*main.py schedule*" -and
        $_.CommandLine -like "*$Root*"
    } |
    Select-Object -First 1

if ($Existing) {
    Write-Host "Schedule is already running. PID: $($Existing.ProcessId)"
} else {
    $Process = Start-Process -FilePath "python" -ArgumentList "main.py schedule" -WorkingDirectory $Root -PassThru
    Write-Host "Schedule started. PID: $($Process.Id)"
}

$LogDir = Join-Path $Root "log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$LogFile = $null
for ($i = 0; $i -lt 20 -and -not $LogFile; $i++) {
    $LogFile = Get-ChildItem -LiteralPath $LogDir -Filter "*.log" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $LogFile) { Start-Sleep -Milliseconds 500 }
}

if ($LogFile) {
    Write-Host "Log file: $($LogFile.FullName)"
    Write-Host "Showing latest 30 log lines. Closing this window does not stop the schedule process."
    Get-Content -LiteralPath $LogFile.FullName -Encoding UTF8 -Tail 30 -Wait
} else {
    Write-Host "No log file found. Check the log directory."
}
