# Task 1 - Re-run of the six scripts in `code\`

Done 2026-10-13. Method: each script was run one at a time in a fresh process by `rerun\run_one.ps1` (Start-Process, process-local env vars only: NUMBA_CACHE_DIR, MPLCONFIGDIR, PYTHONDONTWRITEBYTECODE, PYTHONIOENCODING; fresh empty numba cache in `rerun\.numba_cache`). Limits enforced by the wrapper: 600 s wall, 4 GB. The scripts were copied to `rerun\code\` with ONLY the output path changed (one line each, verified by diff against `code\`), so the pack's `results\` was not overwritten. Inputs read-only from `D:\Malaysian-SNR`. Full stdout/stderr and a per-script `.run.json` are in `rerun\logs\`. Outputs in `rerun\results\`. Comparison: `rerun\compare_outputs.py` -> `rerun\compare_outputs.csv`, `rerun\logs\compare_outputs.log`.

Before running I checked that no earlier-agent process was still working in this folder (the other python processes on the machine belong to other projects).

## Versions
Python 3.12.10 (MSC v.1943 64-bit), Windows 11 10.0.26200; numpy 2.5.3; pandas 3.0.6; scipy 1.18.1; matplotlib 3.11.2; numba 0.68.0; pyarrow 25.0.1 (interpreter: `D:\Malaysian-SNR\.venv\Scripts\python.exe`).

## One line per script
| # | Script | Result | Wall s | CPU s | Peak MB | Exit | stderr |
|---|---|---|---|---|---|---|---|
| 1 | 01_reproduce_headlines.py | PASS - 61-row `reproduction_check.csv` byte-identical to the stored one | 3.4 | 3.0 | 347 | 0 | empty |
| 2 | 02_intrabar_resolution_check.py | PASS - `robustness_R1_intrabar_by_cell.csv`, `_pooled.csv` byte-identical; console log has the same 52 non-empty lines as the stored `robustness_R1_log.txt` | 10.9 | 10.7 | 437 | 0 | empty |
| 3 | 03_histdata_clock_check.py | PASS - `check_phase3_histdata_clock.csv` byte-identical | 1.9 | 1.8 | 601 | 0 | empty |
| 4 | 04_figures_and_tables.py | PASS - tables 1a, 1b, 2, 3, 3b, 4, 5, 6, 7, `fig4_stats.csv`, the three parquet files and all 8 PNG figures byte-identical | 9.4 | 7.9 | 252 | 0 | empty |
| 5 | 05_dsr_sensitivity.py | PASS - the three `dsr_sensitivity_*.csv` byte-identical (0 configs above DSR 0.95 in both phases) | 3.9 | 3.5 | 284 | 0 | empty |
| 6 | 06_truncation_lookahead_test.py | PASS - `check_phase1_truncation_test.csv` byte-identical; "TOTAL mismatches: 0 in 216 checks" | 56.1 | 55.1 | 261 | 0 | empty |

Total runtime about 86 s.

## Comparison summary
- 30 of 30 output files that exist in both `results\` and `rerun\results\` are byte-identical (SHA-256 equal; hashes in `compare_outputs.csv`).
- The two files not compared as files, `reproduce_log.txt` and `robustness_R1_log.txt`, were captured console output in the original run. Compared against the new stdout logs: log 1 is 62 vs 62 non-empty lines, the only difference being the output directory in the final "WROTE ..." line; log 2 is 52 vs 52 lines, no differences.
- Caveat on what "reproduces" means: script 01 recomputes the headline numbers from the stored trade files and compares with the earlier reports. Its output (the same 61 rows) includes the known wording slips the audit listed (for example trade count 9,155 reported vs 9,145 recomputed; best ablation -0.22 reported vs -0.234 recomputed). The rerun reproduces those discrepancies exactly; it does not remove them. They are described in `02-audit.md`.
- The scripts do not re-run the original backtests from raw prices (phase 1-3 engines); they test stored outputs, plus scripts 02 and 06 which re-simulate from price data. That limit is in the pack already.
- Results are deterministic here: identical bytes on re-run, same machine.
