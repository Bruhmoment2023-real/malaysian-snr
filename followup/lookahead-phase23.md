# Look-ahead in the phase-2 and phase-3 pipelines (task 5)

Everything here ran on **copies** of the code in `followup\lookahead\code_copy\` (SHA-256 of each original and every changed line in `code_copy_manifest.json`; only module search paths and output folders were redirected). Price data were read from `D:\Malaysian-SNR` read-only. Nothing in that folder or in the pack's `results\` was written. All runs were one job at a time, each under about 10 minutes and under 2.2 GB, with logs and run times in `lookahead\logs\`.

## 1. Verdict in six lines
1. **Truncation tests of the phase-2 and phase-3 pipelines: no bar-level look-ahead found** (details in section 2). Every per-bar series, every POI setup row and every closed trade is identical when the data after the cut are deleted, except the items in 2 and 3 below.
2. **Audit F9 (limit entries) is real and large for one family, and zero for the canonical method.** Reading the storyline, target, roadblock, indicator filter, liquidity count and ATR as of the *previous* bar instead of the touch bar's close lowers the walk-forward net R of limit-entry configurations by **0.107 R on average (15 real cells, configurations with at least 100 trades; 79% get worse)**. Almost all of it comes from the **liquidity filter**: limit configurations with liq=1 lose 0.216 R, with liq=0 only 0.0025 R. The best large-sample limit variants named in the audit (XAUUSD weekly ladder, simple storyline, 470-830 trades, +0.09 to +0.23 R, p down to 0.011) become **-0.016 to -0.127 R, p = 0.58 to 0.98**. Of 352 limit configurations with at least 400 walk-forward trades and a positive shipped result, **16 stay positive, and the 11 with p < 0.05 become 0**.
3. **The reported headline numbers do not move:** the canonical method uses market entries (not affected); phase 1 has no limit entries; Table 6's "canonical with limit entry" row moves from -0.4517 to -0.4523 mean walk-forward net R over 18 cells (0 of 18 cells positive before and after). Table 5's family counts change in the safe direction: p < 0.05 count 90 -> 65; BH q < 0.10 stays 0; the smallest p among configurations with at least 100 trades goes from 0.0111 to 0.0250.
4. **A second, previously unreported look-ahead exists in the close-pivot storyline** (`msnr._close_pivots` / `storyline`, used by phase 1 V2-V4 and Quasimodo, phase 2's story filter and phase 3's "simple" storyline). It affects **about 2.7% of entry bars in every phase**, but its effect on results is tiny: for the 20,004 phase-3 story=simple configurations with at least 100 trades the mean change in walk-forward net R is **-0.002 R** (5th to 95th percentile -0.032 to +0.032). It is not touched by the canonical method (which uses the separate top-down storyline).
5. **The original 3-cut truncation tests could not see the second leak** (power problem explained in section 4); a strict every-cut-point comparison does.
6. **Unstable-sort tie-breaking** in phase-3 trade selection makes trade lists differ between a cut run and the full run (section 3). It is arbitrary tie-breaking, not information leakage; with a stable sort the differences are 0.

## 2. Truncation tests (written, run, results)

Method (same idea as `code\06_truncation_lookahead_test.py`): build the whole object for the pipeline on the full series and on the series cut at 35%, 60% and 85%; compare every per-bar array on every bar that is complete in the cut set; compare setup rows whose zone had closed; simulate a sample of configurations both ways and compare every trade that closed before the last two bars of the cut series. Scripts: `07_truncation_phase2.py`, `08_truncation_phase3.py` (and `make_copies.py` for the copies). Heavy cells were split into separate runs or the last N rows to stay inside the limits (first attempt of 07 was killed at the 600 s limit, as logged).

| Pipeline | Cells | Series checks / bar comparisons | Mismatches | Setup rows compared | Closed trades compared | Trades differing |
|---|---|---|---|---|---|---|
| Phase 2 (run A: BTC 4h/1d, PAXG 4h, GC=F 1h/4h, SI=F 1h, GC=F 2011 daily) | 7 | 2,688 / 16.56 M | 33 (24 after the 260-bar warm-up) | - | 2,349,468 (3,501 configuration checks) | 0 |
| Phase 2 (run B: SOL 1h, BTC 15m, BTC 1h) | 3 | 1,134 / 39.43 M | 3 (0 after warm-up) | - | 6,056,981 (1,485 checks) | 0 |
| Phase 3 (stable sort): XAUUSD weekly ladder; BTC weekly and daily ladders; BTC 5-minute ladder (last 250,000 5-minute bars) | 4 | 57 + 126 + 63 per 3 cuts = 246 / 28.1 M | 0 | 1.80 M | 7,719 + 28,045 + 19,274 | 0 |

- Phase-2 mismatches explained: (a) `trigger_vwap_cross` at **bar 0** only (12 cases, all inside the warm-up; the first bar has no previous VWAP gap); (b) **SI=F 1h, 35% cut, `story` series, bars 4797-4802** (6 bars x 4 derived series = 24). Diagnosed in `07b_story_boundary_diag.py` (log `logs\07b_story_boundary_diag.stdout.log`): this is the pivot-overwrite effect of section 4, not a cut artefact.
- Not truncated (read in code): the macro side-series (DXY, real yield, gold/silver ratio, funding). They enter through an as-of merge with a 2-day lag (funding at settlement time) and use backward-looking ewm/rolling/diff only.
- What this test cannot see: a trade entered *inside* bar j using a value computed at bar j's close. That is the limit-entry problem of section 5.

## 3. Trade lists differ in the shipped phase-3 code: unstable sort, not leakage
- With the shipped code (`np.argsort(ent)`, quicksort, not stable), cut runs and full runs give different trade sequences: BTC weekly+daily ladders 17,230 of 28,193 compared trades differ by position (1,844 trades of the cut run are absent or different in the full run when matched by setup row and entry bar); BTC 5-minute 11,542 of 19,319 (1,178 absent); XAUUSD weekly 3,160 of 7,735 (0 absent). Setups and series are identical (0 mismatches).
- Cause: several setups can share an entry bar; the order in which numpy breaks ties depends on the array it is given, which differs between the cut and the full run, and "one position at a time" then picks a different one. A copy with a stable sort (`topdown_stable.py`, a one-line change) gives **0 differing trades and 0 absent** in all three runs. The original ordering is arbitrary but uses no future information.
- Not measured: how much arbitrary tie-breaking moves any reported mean (it is an arbitrary choice of which of two simultaneous setups is taken). The expected effect is small and unsigned; a stable-sort rerun of phase 3 is "ready to run" with the same scripts.

## 4. New finding: the pivot-overwrite look-ahead in `storyline`
- `msnr._close_pivots` keeps one alternating list of close pivots. When a later pivot of the same type is more extreme it **overwrites** the earlier entry (new price, new confirmation bar). The earlier pivot was already confirmed and usable in real time from its own confirmation bar, but in the shipped list it vanishes until the later pivot is confirmed. The storyline at the bars in between therefore uses information about a pivot that did not exist yet. Example from the diagnostic: SI=F 1h, bars 4797-4802, shipped storyline +1, strictly causal storyline -1.
- Reference implementation: `causal_ref.py` (keeps every accepted pivot as an event at its own confirmation bar). `10_storyline_overwrite_check.py` compares it with the shipped function on every price series used by phases 1-3 (this equals a truncation test at every cut point): `check_storyline_overwrite_prevalence.csv`.

| Phase | Series | Entry bars | Entry bars where shipped and causal storylines differ | Share |
|---|---|---|---|---|
| 1 (BTC, SOL, gold futures; 1h/4h/1d) | 9 | 190,862 | 5,155 | 2.7% |
| 2 (all 20 cells) | 20 | 1,238,871 | 34,735 | 2.8% |
| 3 (`story=simple` on all 18 cells) | 18 | 8,236,113 | 225,042 | 2.7% |

- Nearly all differences are sign flips (+1 against -1). The old phase-1 test (`code\06`) cut each series at three points, so it only sees the effect if a cut falls inside the few-bar window between the two confirmation bars; the new test compares every bar.
- **Effect on results (phase 3, measured):** `09_limit_entry_leak.py` re-runs every `story=simple` configuration with the causal storyline: 22,428 configurations (20,004 with at least 100 trades in both versions) on 15 real cells. Mean change in walk-forward net R **-0.0020**, median -0.0018, 5th/95th percentile -0.032/+0.032; 4.6% of configurations move by more than 0.05 R (largest +0.238 / -0.295, small samples). Smallest p changes from 0.0111 to 0.0115; Table 5 counts unchanged (BH 0). Direction is not systematic (60% of configurations move down), so there is no evidence it flatters or hurts the method.
- **Not re-run (ready to run):** phase 1 variants V2-V4 and V3 (Quasimodo), and phase 2's story filter, with the causal storyline. Their storyline is the same function and the same 2.7-2.8% of bars; by analogy with phase 3 the expected change is within a few thousandths of R, but that is an inference. The phase-1 headline (gross -0.058 against random -0.060) is dominated by V0, which has no storyline.

## 5. Audit F9 quantified: limit-entry look-ahead (`09_limit_entry_leak.py`, `09b_summarise.py`)
- **What was changed** (`make_lagged_topdown.py` writes `code_copy\topdown_lag.py`; the six-replacement diff is `topdown_lag.diff`): for limit-entry configurations only, the storyline (top-down and simple), storyline target, roadblock level, extra-indicator filter, T3 ATR (stop sizing and liquidity window) and ATR for the fill threshold are read at bar j-1 instead of j, and the liquidity count uses swing points known and not yet swept as of bar j-1. The session flag is a clock fact and was left alone; the touch/fill rule, stop-first rule, exits and costs are unchanged. Where the previous bar's ATR is 0 (flat 5-minute spells) the setup is skipped (this made the first 5-minute crypto runs crash with a division by zero; fixed and re-run).
- **Validation:** with no change applied, the re-run reproduces `phase3_configs_compact.parquet` exactly for **38,076 of 38,076** configurations (trade count and walk-forward net R identical to 1e-9). Output per cell: `limit_leak\<asset>_<ladder>[.limit|.simple].csv`; summary text `limit_leak_summary.txt`, `limit_leak_extra_stats.txt`.
- **Coverage:** all 18 cells (the three crypto 5-minute cells were run in two parts, limit and simple, to fit the 10-minute limit). 10,080 limit configurations (9,468 with at least 100 walk-forward trades in both versions; 7,200 / 6,762 on the 15 real cells), plus 31,356 `story=simple` configurations.

| 15 real-data cells, configurations with at least 100 walk-forward trades | Shipped | Lagged | Change |
|---|---|---|---|
| Limit-entry configurations: mean walk-forward net R | -0.362 | -0.469 | **-0.107** (median -0.036; 5th/95th percentile -0.308/+0.019) |
| Same, gross R | +0.045 | -0.054 | -0.098 |
| Number with net R > 0 | 670 | 159 | -511 |
| Best net R | +1.186 | +0.810 | - |
| Smallest p (net > 0) | 0.0111 | 0.0628 | - |
| of which liq=0 (3,473) | -0.442 | -0.445 | -0.0025 |
| of which liq=1 (3,289) | -0.278 | -0.495 | **-0.216** |
| Limit configurations with at least 400 trades and positive shipped net R (352): positive after lag | 352 | 16 | mean +0.063 -> -0.149 |
| ... with p < 0.05 | 11 | 0 | - |

- **The F9 family named in the audit** (XAUUSD, weekly ladder, limit entry, simple storyline, liq=1, miss=1): shipped +0.225 R (509 trades, p = 0.011) and +0.188 R (470 trades, p = 0.032) become **-0.016 R (726 trades, p = 0.58) and -0.047 R (672 trades, p = 0.72)** with the lagged reads; the 4R/3R/2R siblings with 500-1,020 trades move from +0.11 to +0.16 R to -0.07 to -0.13 R (p = 0.89 to 0.98). Using the causal storyline as well changes these by under 0.01 R. File: `limit_leak_xau_weekly_limit_simple.csv`.
- **Why the liquidity filter carries it:** the count of unswept swing points near the level is read after bar j has been processed, so a swing that is swept by the very bar that touches the level is already excluded, and swings confirmed at that bar are already counted; the likely mechanism is that this makes the filter select touches that already went on to reject (an inference from the code, not separately tested). The trade count rises (509 -> 726) because the honest count is less selective.
- **Reported numbers that move, and by how much** (phase-3 family of 94,068 configurations, all 18 cells re-run):

| Number in the pack | Shipped | After lagging limit entries | After lag + causal storyline |
|---|---|---|---|
| Configurations with p < 0.05 (Table 5) | 90 | 65 | 66 |
| BH q < 0.10 (all / at least 100 trades) | 0 / 0 | 0 / 0 | 0 / 0 |
| Configurations with at least 100 trades and net R > 0 | 3,328 | 2,620 | 2,511 |
| Smallest p among configurations with at least 100 trades | 0.0111 | 0.0250 | 0.0250 |
| Max walk-forward net R (at least 100 trades) | +2.167 | +2.167 (not a limit configuration) | +2.167 |
| Table 6 row "canonical with limit entry", mean walk-forward net R over 18 cells | -0.4517 | -0.4523 | - |
| Canonical method (market entry, top-down storyline) | unchanged by construction | unchanged | unchanged |

- Not recomputed: the Deflated Sharpe values (they need the per-configuration skew/kurtosis and cell variance for the changed rows; they were below 0.06 for every configuration with at least 100 trades and the smallest p only gets larger, so the conclusion cannot flip), and the holdout figures of the few limit configurations that went to holdout.
- Direction of bias for the paper: the leak **flattered limit-entry variants** (by about 0.1 R on average, and by about 0.2 R when the liquidity filter is on). It does not affect the core claim (the method fails); it removes the only appendix variants that looked positive with a reasonable sample.

## 6. What remains untested or inexact
- Phase 1 V2-V4/Quasimodo and phase 2 story-filter results were not re-run with the causal storyline (inference above).
- Phase-3 trade-selection tie-breaking (unstable sort) effect on reported means not quantified.
- Holdout (final 365 days) effects of the two leaks not computed (phase A data only, as in the walk-forward).
- The phase-2 limit-entry code was read as correct (filters as of the previous bar) and the truncation test found no trade differences (1.57 M closed limit-entry trades compared in run A, 4.06 M in run B); the trade-level test cannot see an intrabar read, so this rests on the code reading plus the audit's.
- MCX proxy cells are included in the 18-cell figures and excluded from the 15-real-cell figures.

## 7. Files (all under `followup\lookahead\`)
`07_truncation_phase2.py`, `07b_story_boundary_diag.py`, `08_truncation_phase3.py`, `09_limit_entry_leak.py`, `09b_summarise.py`, `09c_table4_15cells.py` (paper Table 4 rows 9-10 on the 15 real-data cells; output `table4_15cells_summary.txt`), `10_storyline_overwrite_check.py`, `causal_ref.py`, `make_copies.py`, `make_lagged_topdown.py`, `run_09_all.sh`, `run_09_parts.sh`; results `check_phase2_truncation_*.csv`, `check_phase3_truncation_*.csv`, `check_storyline_overwrite_prevalence.csv`, `limit_leak\*.csv`, `limit_leak_summary.txt`, `limit_leak_extra_stats.txt`; logs `logs\`; code copies `code_copy\`. The numba cache `.numba_cache\` is safe to delete.
