# Rebuild paper 02's main audit results in order (PowerShell).
#   .\rerun.ps1 -DryRun   # check interpreter, input folder and imports; print the commands (seconds)  <- the only mode tested in this pass
#   .\rerun.ps1 -Run      # run the six read-only scripts (about 10-15 minutes in total on a quiet laptop)
# IMPORTANT: the scripts READ D:\Malaysian-SNR (never modified) and WRITE into this paper's results\ folder, overwriting the existing
# verified tables and figures with the re-computed ones. Copy results\ somewhere first if you want to diff.
# The 116,708-variant search of phases 2-3 and the phase-1 backtest themselves are NOT re-run here (hours; see D:\Malaysian-SNR\REPORT.md and backtest\run_all.py).
# The literature map is rebuilt from bibliometrics\README.md (network steps are slow and cached).
param([switch]$DryRun, [switch]$Run, [string]$Pack = "D:\Research-Publishing\02-malaysian-snr")
$ErrorActionPreference = "Stop"
if (-not (Test-Path "D:\")) { throw "D: is missing - stopping." }
$py = "D:\Malaysian-SNR\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Interpreter not found: $py" }
if (-not (Test-Path "D:\Malaysian-SNR\phase2\results\all_configs_phaseA.csv")) { throw "Study results folder is missing" }
Write-Host "Interpreter:" (& $py --version)
& $py -c "import numpy, pandas, matplotlib, pyarrow; print('imports ok: numpy', numpy.__version__, 'pandas', pandas.__version__)"
$env:NUMBA_CACHE_DIR = "$Pack\.numba_cache"      # this shell only
$scripts = "01_reproduce_headlines.py","02_intrabar_resolution_check.py","03_histdata_clock_check.py","04_figures_and_tables.py","05_dsr_sensitivity.py","06_truncation_lookahead_test.py"
foreach ($s in $scripts) {
    $cmd = "$py -B $Pack\code\$s"
    Write-Host "== $cmd"
    if ($Run -and -not $DryRun) { & $py -B "$Pack\code\$s"; if ($LASTEXITCODE -ne 0) { throw "$s failed" } }
}
if (-not $Run) { Write-Host "Dry run only. Use -Run to execute." }
