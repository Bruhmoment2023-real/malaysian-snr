# Runs ONE script in a fresh process, logs full output, records wall time, CPU time and peak memory.
# Kills the process if it exceeds the wall-clock or memory limit. Environment variables are process-local.
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [string]$Py = "D:\Malaysian-SNR\.venv\Scripts\python.exe",
    [string]$LogDir = "D:\Research-Publishing\02-malaysian-snr\followup\rerun\logs",
    [string]$NumbaCache = "D:\Research-Publishing\02-malaysian-snr\followup\rerun\.numba_cache",
    [int]$MaxSeconds = 600,
    [double]$MaxGB = 4.0,
    [string]$ScriptArgs = "",
    [string]$Tag = ""
)
if (-not (Test-Path D:\)) { Write-Output "D: OFFLINE - abort"; exit 2 }
New-Item -ItemType Directory -Force $LogDir | Out-Null
New-Item -ItemType Directory -Force $NumbaCache | Out-Null
$name = [IO.Path]::GetFileNameWithoutExtension($Script)
if ($Tag) { $name = "$name.$Tag" }
$out = Join-Path $LogDir "$name.stdout.log"
$err = Join-Path $LogDir "$name.stderr.log"
$env:NUMBA_CACHE_DIR = $NumbaCache
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:MPLCONFIGDIR = Join-Path (Split-Path $LogDir) ".mplconfig"
$env:PYTHONIOENCODING = "utf-8"
$start = Get-Date
$al = @("-B", "`"$Script`""); if ($ScriptArgs) { $al += $ScriptArgs }
$p = Start-Process -FilePath $Py -ArgumentList $al -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow -PassThru
$h = $p.Handle  # keep handle so ExitCode is available
$peak = 0; $status = "completed"; $cpu = 0.0; $child = $null
# The venv python.exe is a launcher that starts the real interpreter as a child process: measure the child.
while (-not $p.HasExited) {
    Start-Sleep -Milliseconds 300
    if ($child -eq $null) {
        try { $c = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($p.Id)" | Select-Object -First 1
              if ($c) { $child = Get-Process -Id $c.ProcessId -ErrorAction Stop } } catch {}
    }
    $m = if ($child) { $child } else { $p }
    try { $m.Refresh(); if ($m.PeakWorkingSet64 -gt $peak) { $peak = $m.PeakWorkingSet64 }; $t = $m.TotalProcessorTime.TotalSeconds; if ($t -ne $null -and $t -gt $cpu) { $cpu = $t } } catch {}
    $el = ((Get-Date) - $start).TotalSeconds
    if ($el -gt $MaxSeconds) { $status = "KILLED_TIME_LIMIT"; try { if ($child) { $child.Kill() }; $p.Kill() } catch {}; break }
    if ($peak / 1GB -gt $MaxGB) { $status = "KILLED_MEMORY_LIMIT"; try { if ($child) { $child.Kill() }; $p.Kill() } catch {}; break }
}
$p.WaitForExit()
$wall = ((Get-Date) - $start).TotalSeconds
if ($child) { try { $t = $child.TotalProcessorTime.TotalSeconds; if ($t -ne $null -and $t -gt $cpu) { $cpu = $t } } catch {} }
$rec = [ordered]@{ script = $name; started = $start.ToString("s"); status = $status; exit_code = $p.ExitCode
    wall_seconds = [math]::Round($wall, 1); cpu_seconds = if ($cpu -ne $null) { [math]::Round($cpu, 1) } else { $null }
    peak_working_set_MB = [math]::Round($peak / 1MB, 0) }
$rec | ConvertTo-Json | Out-File -Encoding utf8 (Join-Path $LogDir "$name.run.json")
$rec | ConvertTo-Json
