# 02 - Referee-style audit of the Malaysian-SNR study

Date: 2026-10-13. Auditor: AI research agent, working read-only from the code and result files in `D:\Malaysian-SNR`, not only from the reports. Nothing in that folder was changed (checked: no file there is newer than the start of this audit). All scripts are in `D:\Research-Publishing\02-malaysian-snr\code\`, all outputs in `results\`.

## 0. What the study actually is (this changes the brief)

| Phase | Question | About MSNR? | Evidence for the paper |
|---|---|---|---|
| 1 (`backtest\`, `results\`) | Five MSNR variants on 19 asset/timeframe cells, random-entry benchmark | **Yes** | Core |
| 2 (`phase2\`) | MSNR plus 31 confluences, exits, limit entries: 22,640 configurations | **Yes** | Search appendix |
| 3 (`phase3\`) | Canonical top-down MSNR on 18 cells, plus 94,068 variants | **Yes** (273 further non-MSNR systems and a prop-firm simulation are not) | Core (canonical) + appendix (variants) |
| 4, 5, 6 | Generic search for any edge: 255,421 + about 258 million rule configurations, factors, carry, etc. | **No** | Not for this paper |
| 7 | 25 published strategies; MSNR canonical re-run as "S24" | One row | Optional cross-check |
| clockfix | Timestamp fix and reruns of phases 4 and 5 | **No** | Not for this paper |

Consequences:
- **The "258 million configurations" and the "unseen-instrument lockbox, 0 of 10" are not tests of Malaysian SnR.** They test whether any indicator rule works. Putting them in this paper would mislead. The multiple-testing-controlled search that is about MSNR is phases 2 and 3: 22,640 + 94,068 = 116,708 configurations.
- **"Clock-fixed numbers supersede the originals" applies only to phases 4 and 5.** None of the MSNR phases (1, 2, 3) was re-run after the clock fix. Phases 1-2 use Binance (true UTC) and Yahoo data, so the bug cannot touch them. Phase 3 uses histdata for gold and silver and is affected in a limited way (finding F2).
- Final numbers for the paper are therefore the **original phase 1, 2 and 3 files**, with the corrections listed below.

## 1. Reproduction of headline numbers

Script `code\01_reproduce_headlines.py` recomputes each figure from the stored trade or result files (no backtest re-run). Full list of 61 checks: `results\reproduction_check.csv`.

| Item | Reported | Recomputed | Source file | Verdict |
|---|---|---|---|---|
| Phase 1: per-cell trades and mean R (95 cells, full period) rebuilt from the 121,916 stored trades | key table | max count difference 0; max difference in mean R 0.00005 | `results\trades_default_full.csv` | Reproduces |
| Phase 1: out-of-sample cells losing money | 84 of 95 | 84 of 95 | `key_table_default_OOS.csv` | Reproduces |
| Phase 1: cells with at least 30 trades that are net positive | 4 of 73 | 4 of 73 (gold futures 4H V2 +0.007; silver futures 4H V1 +0.050; gold daily V1 +0.095; gold daily V2 +0.083) | same | Reproduces |
| Phase 1: cells whose gross result beats random at p < 0.05 | 3 of 89 (4.5 expected by chance) | 3 of 89; 6 cells are in the opposite 5% tail; smallest BH q = 0.29 | same | Reproduces |
| Phase 1: pooled 1H V0, out of sample, net R / z vs random | -0.680 / 2.60 | -0.680 / 2.60 (n = 19,613) | same | Reproduces |
| Phase 1: pooled 1H V0, in sample, z vs random | 7.3 | 7.31 (gross edge +0.061 R; average cost 0.534 R) | `key_table_default_IS.csv` | Reproduces |
| Phase 1: pooled 4H V3 and 1D V3 (Quasimodo) z | -2.39, -2.26 | -2.39, -2.26 | same | Reproduces |
| Phase 1: gold daily V1 out of sample | +0.095 R, 130 trades, PF 1.15; in sample -0.30 | +0.095, 130, 1.15; in sample -0.300 (n = 167) | same | Reproduces |
| Phase 1: win rates "25-38%" | 25-38% | 18.1%-40.5% across the 73 cells; median 30.6%; 88% of cells lie in 25-38% | same | **Report rounds; use the exact range** |
| Phase 1: all out-of-sample trades pooled | not reported | 50,108 trades; net -0.547 R; gross -0.058 R; random gross -0.060 R; z = 0.26 | same | New summary figure |
| Phase 2: configurations | 22,640 | 22,640 | `phase2\results\all_configs_phaseA.csv` | Reproduces |
| Phase 2: p < 0.05 / BH q < 0.10 / Deflated Sharpe > 0.95 | 138 / 3 / 0 | 138 / 3 / 0 (BH recomputed independently, identical; the 3 are 5-trade SOL daily configurations; 0 with at least 100 trades) | same | Reproduces |
| Phase 2: fixed V1 2R, walk-forward and holdout | -0.519 (66,274); -0.599 (13,079) | -0.519 (66,274); -0.599 (13,079) | same | Reproduces |
| Phase 3: MSNR configurations and criteria histogram | 94,068; 0:7,720 1:77,974 2:5,990 3:2,325 4:55 5:4 | identical | `phase3\results\msnr_all_configs.csv` | Reproduces |
| Phase 3: canonical pooled walk-forward | -0.496 R, 9,155 trades | -0.496 R on 9,147 trades from the per-cell table; -0.498 R on 9,145 trades from the raw trade arrays | `msnr_canonical_by_cell.csv`; `B3\trades_*_6656813.npy` | Reproduces; trade count differs by 8-10 (0.1%) because the walk-forward was run fold by fold |
| Phase 3: canonical pooled holdout | -0.325 R, 1,262 trades | -0.325 (1,262) from the table; -0.326 (1,264) from raw trades | same | Reproduces |
| Phase 3: canonical cells positive / beating random | 2 / 1 of 18 | 2 / 1 | same | Reproduces |
| Phase 3: "DSR about 0" | about 0 | max 0.057 among configurations with at least 100 trades; max 0.54 including tiny samples | `msnr_all_configs.csv` | Report is loose; say "below 0.06 for every configuration with at least 100 trades" |
| Phase 3: "best ablation -0.22" | -0.22 | the -0.216 row covers 3 cells only (gap levels, defined only for the synthetic MCX series); the best 18-cell ablation is -0.234 | `msnr_ablations.csv` | **Correct the wording** |

New figures the paper will need, computed here for the first time:
- Canonical method, **15 real-data cells only** (synthetic MCX proxy removed): walk-forward 8,125 trades, net -0.511 R, gross -0.033 R; holdout 1,134 trades, net -0.383 R; 1 cell positive.
- Canonical gross R, 15 real cells, from raw trades: -0.034 R per trade, 95% interval [-0.071, +0.003] (treating trades as independent).
- Canonical win rate 24.5% against a 25% break-even at a 3R target; 53% of trades long.
- Excluding silver as well: 6,268 trades, net -0.336 R, gross -0.019 R. Silver's cost per trade (about 1.26 R on the 5-minute ladder) drives the pooled net figure.

## 2. Findings, ranked by severity

### F1 (HIGH). Nothing about MSNR was pre-registered; "fixed in advance" cannot be proven
- Phases 1, 2 and 3 have **no protocol file**. The only protocols on disk are for phases 5, 6 and 7, which are not MSNR tests.
- There is no version control (`D:\Malaysian-SNR` is not a git repository), no external registry (OSF, AsPredicted), no hash published anywhere. "Defaults fixed in advance" (phase 1) and "canonical config, fixed in advance" (phase 3) rest on the AI agent's own reports and on file modification times on a local disk.
- Timeline from file times: rules document 5 Oct 22:58; engine 23:02; runner 23:05; phase-1 results 23:06. Phase 2 code 23:13-23:53, results 6 Oct 00:14. Phase 3 engine 00:57, phase-A results 01:18, **`p3_msnr.py` last modified 01:21 (after phase A finished, before the holdout run at 01:27)**; what changed in that edit cannot be recovered.
- The phase-5 protocol says "file mtime is the timestamp of record", but its mtime is 11 Oct 15:44 because amendments were appended. The original text cannot be shown to be unedited.
- **What was decided before results (by construction of the code, in one sitting):** phase-1 variants V0-V4, the default parameters (0.1 ATR buffer, 2R), the 60/40 split, the 8-point parameter grid, tuning on the first 60% only.
- **What was decided after seeing results:**
  - Phase 1 report admits "mild data peeking when choosing the flip rule" (all three options were negative).
  - Phase 2's whole design followed the phase-1 results. A bug fix (5 bp minimum-risk floor) was made after the holdout had been evaluated once; the holdout was then evaluated a second time.
  - Phase 3's canonical configuration (engulfing or break-of-structure confirmation, 3R, roadblock filter) was specified after phases 1-2. Phase 2 had already shown that engulfing was the most helpful confluence. Its 12-month holdout is the same calendar window phase 2 had opened twice.
  - Dropping the synthetic MCX proxy, pooling choices, and every table in this folder are post hoc.
- **Why this does not sink the paper:** every forking path that was resolved after seeing data was resolved in the method's favour or made no difference, and the method still loses. Selection bias works against a null result only if the analyst was trying to make the method fail; the search for winning variants shows the opposite intent. Say exactly this.
- **Required action:** remove "pre-registered" from title and text. Use "out-of-sample" and "walk-forward" precisely, and include a table "decided before / decided after" (drafted in `04-outline.md`).

### F2 (HIGH for wording, LOW for numbers). Phase 3 metals were never clock-fixed; the report labels the time zone wrongly
- `phase3\fetch_histdata.py` assumes histdata timestamps are fixed EST and adds 5 hours to get "UTC". The clock-fix work later showed the labels follow New York wall clock (daylight saving included).
- Verified today on the phase-3 files (`code\03_histdata_clock_check.py`, `results\check_phase3_histdata_clock.csv`): the weekly re-open of XAUUSD and XAGUSD sits at label 23:00-23:01 in **both** January-February and June-July (128 and 131 weekly opens, 2012 onward). True UTC would differ by one hour between seasons. So phase-3 metals timestamps are one hour late during US daylight-saving time.
- Effect on the canonical result: **none of substance.** Phase 3 cuts metals days at label 22:00, which is New York 17:00 wall clock all year, the standard FX day. The canonical configuration has no session filter. The paper must simply describe daily and weekly bars as "New York 17:00 close", not "22:00 UTC".
- Effect elsewhere: the `sess` filter (label hours 7-11 and 12-17) is shifted by one hour for about two-thirds of the year in every configuration that uses it (half of the 94,068), and the synthetic MCX session window is shifted likewise. These configurations are in the search appendix only. Disclose; a rerun is listed as optional (section 5).
- Phase 7's "S24" MSNR row imports the same phase-3 code, so it carries the same labels.

### F3 (HIGH). A mechanical test of a discretionary method; source traceability is incomplete
- The method's own teachers say not every A/V level counts ("it MUST have liquidity"), and that "obvious" levels, misses, sessions and M5 refinement matter. The study codes proxies (pivot depth, counted swing points near the level, counted near-misses, a session flag) and tests them, but a proxy is not the trader's judgement.
- Honest claim available: "the rules that can be written down do not work, and the written-down versions of the discretionary filters do not rescue them". Not available: "MSNR traders cannot be profitable".
- `research\MSNR-rules-and-sources.md` tags every rule as consensus, some sources, or discretionary, and its section 8 lists each disagreement and the choice made. That is good. But the file itself states that YouTube and several Scribd/CourseHero documents could not be read in full, that some quotes come from search snippets, and that one TradingView script returned 404. Each quoted rule needs Sean to open the page, archive it, and confirm the wording.
- Choices that are **not traceable to any source** and must be labelled "author's operationalisation" (full list in `03-rule-spec.md`): ATR(14) and the 0.1 ATR stop buffer; the "retest" condition (previous bar must not have reached the level); ignoring bars that signal both ways; one position at a time; storyline as a close-pivot break; Quasimodo from depth-2 close pivots; in phase 3 the zone life of 3 bars, the 0.25 ATR invalidation, the 2-bar window for storyline activation, the 50 ATR pruning of far levels, the 5 bp minimum stop.
- Gap levels are taught as part of the method by most sources but are **omitted** in phase 1 and in the canonical phase-3 configuration (tested only on the synthetic MCX series). The reason (24-hour markets have almost no close/open gaps) is sound; state it.

### F4 (MEDIUM-HIGH). The simulator is pessimistic by 0.03-0.07 R per trade, and the one "real effect" in the report is weaker than stated
- When stop and target both lie inside one bar, the code counts a stop. Proof that this matters: the **random** benchmark, which should average about zero before costs, shows -0.03 to -0.10 R gross (for example -0.080 R on 1H V0).
- New check R1 (`code\02_intrabar_resolution_check.py`): 92,075 of the 92,329 stored BTC/ETH/SOL trades were re-walked on 5-minute bars. The re-walk on the original bars reproduces the stored gross R for 99.98% of them, so the check is measuring the right thing.
  - Random entries, 5-minute resolution: -0.008 R (1H), -0.010 R (4H), +0.011 R (1D). The bias disappears, as theory says it should.
  - Strategy gross R rises by the same 0.03-0.06 R. Win rates move from about 31-32% to 32-34%, against a 33.3% break-even.
  - **Edge over random is almost unchanged**, which is what matters:

| Crypto pooled | Period | Trades | Edge, original bars (z) | Edge, 5-minute resolution (z) |
|---|---|---|---|---|
| 1H V0 literal rule | first 60% | 21,272 | +0.049 R (4.9) | +0.037 R (3.7) |
| 1H V0 literal rule | last 40% | 14,919 | +0.019 R (1.6) | +0.009 R (0.7) |
| 4H V0 literal rule | first 60% | 5,378 | +0.058 R (3.0) | +0.049 R (2.5) |
| 4H V0 literal rule | last 40% | 3,958 | +0.003 R (0.1) | 0.000 R (0.0) |
| 1H V1 pivot levels | last 40% | 6,824 | -0.030 R (-1.8) | -0.040 R (-2.3) |
| 4H V1 pivot levels | last 40% | 1,738 | -0.046 R (-1.4) | -0.067 R (-2.0) |

- Consequences for the paper:
  - Every absolute "R per trade" in phases 1-3 is understated by a few hundredths of R. Costs (0.13-1.3 R) are many times larger, so no verdict changes, but the paper must say the simulator is conservative and by how much.
  - The phase-1 report's sentence "the one real effect ... z = 7.3 in-sample, 2.6 out-of-sample" should become: a small gross advantage of the literal rule over random entries is visible in the first 60% of crypto data (+0.04 to +0.05 R) and is **not distinguishable from zero in the last 40%** (+0.01 R, z = 0.7 at 5-minute resolution). The filtered "obvious level" variant is, if anything, slightly worse than random.
- Limits of R1: crypto only; the trade list is held fixed; phase 3 (which also uses stop-first, on bars as fine as 5 minutes) was not re-resolved.

### F5 (MEDIUM). The random-entry benchmark is matched on geometry, not on everything
Matched correctly (read from `msnr.random_baseline` and `engine2.random_baseline2`):
- same instrument, same window, same number of trades per repetition;
- stop distance drawn from the strategy's own trades, in ATR units, scaled by the ATR at the random bar;
- target multiple drawn jointly with the stop distance; same exit logic, same stop-first rule, same gap handling;
- same costs and carry;
- direction follows the higher-timeframe storyline for the variants that use it (V2-V4, canonical), so a trend filter cannot be mistaken for a level effect. This is the design's best feature.

Not matched:
- Direction is a 50/50 coin flip for V0 and V1. The strategy's long share is 49.2% and 51.5% pooled, but ranges from 44.7% to 63.9% by cell. In a strongly trending cell this lets drift leak into the comparison.
- Random bars are uniform in time. Strategy signals follow a rejection candle, so they cluster in particular volatility states and hours. ATR scaling handles part of this.
- Random trades may overlap; the strategy holds one position at a time.
- The pooled z uses only the spread of the random means, 300 repetitions (200 or 60 in phases 2-3). The smallest attainable p-value is 1/301.
- The comparison is one-sided ("beats random"). Six of 89 cells sit in the opposite tail and the Quasimodo variant is significantly **worse** than random (z = -2.3, -2.4); report two-sided.

### F6 (MEDIUM). Data quality and coverage
- **Gold and silver in phases 1-2:** Yahoo continuous futures. Hourly history covers about 2.4 years (May 2024 to Oct 2026), a strong bull market; the out-of-sample part of the hourly cells is one year. Daily gold starts in 2011 after flat rows were dropped; silver daily was discarded. No roll adjustment, so roll days contain artificial jumps that can trigger stops or levels.
- **Yahoo intraday data cannot be re-downloaded later** (rolling 730-day window), so the stored parquet files are the only copy. Reproducibility for outsiders depends on sharing derived data, which Yahoo's terms may not allow. Flag in the data statement.
- **PAXG** is thin and its result is almost entirely fees.
- **Phase 3 gold and silver:** histdata M1, **bid prices only**. With bid-only bars a long entry is filled at the bid (too cheap), a short's stop is triggered by the bid high (too late). Both errors flatter the strategy. The cost model adds a fixed $0.35 (gold) and $0.035 (silver) per entry to stand in for the spread; this is plausible for a retail account in normal hours and too low around news and the daily roll. The strategy loses anyway, so the bias is in the safe direction for the conclusion.
- **Synthetic MCX gold proxy:** built from XAUUSD, USDINR and an ETF-based premium. Its own QC file shows a daily return correlation of 0.34 with the ETF at session close (0.74 only after time-matching) and a level-ratio coefficient of variation of 2.0. Its 3 cells contain the best-looking results in phase 3. **Exclude it from the paper**, and say that 3 of the 18 phase-3 cells were dropped for this reason.
- **Survivorship:** BTC, ETH and SOL were chosen in 2026 because they are large today. This inflates buy-and-hold, not a long/short level test. Delete the buy-and-hold comparison from the headline or keep it as context only.
- **Costs** (as coded, `results\table7_cost_assumptions_as_coded.csv`): crypto 0.07% per side (0.02% for limit entries and target exits in phases 2-3) applied to **spot** bars but described as perpetual-futures fees; carry 2-3% a year as a flat proxy. Costs are not under-stated for a retail trader; if anything a careful trader on a low-fee venue pays less. Because the conclusion is "costs dominate", a referee will push here: add a cost-sensitivity line (break-even cost per trade is simply the gross R, which is at or below zero in almost every cell, so **no positive cost level rescues the method**; that argument is stronger than any cost table).

### F7 (MEDIUM). The multiple-testing machinery does little work here, and one input is questionable
- The p-values test "net R per trade > 0". Almost every configuration is far below zero, so p-values pile up at 1: 138 of 22,640 (phase 2) and 90 of 94,068 (phase 3) are below 0.05, against 1,132 and 4,703 expected if all rules had zero net edge (`results\fig7_pvalue_histograms.png`). There is nothing for BH or the Deflated Sharpe to deflate. A referee will say the corrections are decoration. The honest framing: they are a safeguard on the search appendix, proving that the handful of positive-looking variants are no more than a search of this size produces by chance.
- The three BH "survivors" in phase 2 are 5-trade configurations: a t-test on 5 trades is meaningless. Require a minimum sample before testing, and say so.
- The Deflated Sharpe uses the cross-sectional variance of Sharpe ratios across **all** configurations in a cell. Most are strongly negative, so the variance measures how different the rules are, not luck, and the hurdle is inflated. (The project's own phase-7 amendment noticed the same problem.) Sensitivity run today (`code\05_dsr_sensitivity.py`): with the null sampling variance instead, the maximum DSR among configurations with at least 100 trades is 0.23 (phase 2) and 0.07 (phase 3); with N = all configurations, 0.06 and 0.02. **Zero configurations exceed 0.95 under any of the three choices.** The conclusion is robust; report the gentler version alongside.
- Reality Check and SPA use only 300 bootstrap draws and a mean block of 10 days. Smallest cell-level p: RC 0.073 (phase 2), 0.147 (phase 3); SPA 0.62 and 0.85. Fine as supporting evidence; too coarse to headline.
- BH assumes independence or positive dependence. The configurations are heavily overlapping variants. Mention Benjamini-Yekutieli as the conservative alternative; with q = 1 for every sizeable configuration it cannot change anything.
- The probability of backtest overfitting (Bailey et al.) was **not** computed. Do not list it among methods used.

### F8 (MEDIUM). Holdout hygiene
- Phase 1 has an in-sample/out-of-sample split, not a locked holdout.
- Phase 2's holdout (last 365 days) was evaluated twice (disclosed in its report).
- Phase 3's holdout is the same calendar year. For crypto it is the same Binance history at a finer bar size. So by phase 3 the "holdout" had informed design decisions at least indirectly.
- The phase-5 protocol itself calls the phase 1-4 holdout "contaminated". Use that word in the paper.
- Phase 3 phase A filters the holdout out after loading the file; the holdout rows never reach any calculation (checked in `Cell3.__init__`).
- Selection steps (fold-1 ranking of filters, walk-forward picks) use only earlier folds (checked in `p2_phaseA.py` and `p3_msnr.py`). No selection step reads the holdout.

### F9 (LOW-MEDIUM). Small look-ahead in phase-3 limit-entry variants; an unexamined pocket
- For limit entries in `topdown.py` the fill happens inside the touch bar, but the storyline, liquidity count and session filter are read at that bar's **close**. That is up to one entry-timeframe bar of look-ahead. Phase 2's limit code does this correctly (filters as of the previous bar).
- The canonical configuration uses market entries after confirmation and is not affected.
- The best large-sample phase-3 variants are exactly this type: XAUUSD weekly-ladder limit entries with a simple storyline, 470-830 trades, +0.09 to +0.23 R walk-forward (`results\dsr_sensitivity_top15_phase3.csv`). They were never taken to the holdout (only the top 15 by mean R per cell were), fail BH (q = 1) and DSR (below 0.08). A referee who reads the appendix table will ask about them. Answer: optimistic fill model plus the look-ahead above; list as a limitation, or run the optional check in section 5.

### F10 (LOW). Look-ahead in the core engine: none found
- Code reading of `msnr.py`: a level is usable only from the bar after its confirming candle closes; pivot levels only after `depth` further closes; higher-timeframe bias only from bars that have closed; entry at the next bar's open; ATR from bars up to the signal bar.
- The phase-1 report says a truncation test passed "0 mismatches in 9 checks", but no test script or log is stored. Re-done today (`code\06_truncation_lookahead_test.py`): BTC, SOL and gold futures; 1H, 4H, 1D; cuts at 35%, 60% and 85% of the data; eight series (four signal types, storyline, nearest levels, ATR). **0 mismatches in 216 checks covering 343,559 bar comparisons per series.**
- Not re-tested today: phase-2 indicators and the phase-3 top-down pipeline (reports say they passed; the test code is not stored).

### F11 (LOW). Reporting slips to fix when writing
- Win-rate range (see section 1).
- "Buy-and-hold beat every variant on every asset" compares a 1%-risk-per-trade account with a fully invested one and uses survivor coins. Drop or caveat.
- CAGR, drawdown and Sharpe figures are computed from equity marked only at trade exits, with a 10x leverage cap. Sharpe values such as -26 are artefacts of near-certain small losses. Report R per trade, win rate and profit factor; leave Sharpe out.
- Pooled figures are trade-weighted, so 1H and 5-minute cells dominate; always show the per-cell table next to them (unweighted canonical cell mean is -0.352 R against -0.496 R trade-weighted).
- The MCX proxy "correlation 0.74" quoted in the phase-3 report is the time-matched figure.
- Trade-level confidence intervals assume independent trades. Trades are sequential and non-overlapping within a cell but cells overlap in time across variants and assets (BTC/ETH/SOL are highly correlated). Treat pooled z-values as upper bounds on significance.

## 3. Direct answers to the audit questions

| Question | Answer |
|---|---|
| Is the rule specification traceable to cited sources? | Core definitions yes (A/V levels, fresh/unfresh, role flip, QM, storyline idea, stop beyond the wick, minimum 1:2). About a dozen numeric choices are the coder's own and are now listed. Source quotes need re-verification by Sean (F3). |
| Is every discretionary choice documented? | The big ones are, in section 8 of the rules file and in the code docstrings. The phase-3 engine constants were documented only in code; they are now in `03-rule-spec.md`. |
| Which numbers are final? | Phases 1-3 originals. Clock-fixed reruns concern phases 4-5 only and are out of scope. Use the 15-real-cell canonical figures computed here instead of the 18-cell figures. |
| Look-ahead? | None in the phase-1 engine (re-tested). Minor, in phase-3 limit-entry variants only (F9). |
| Survivorship? | Yes in asset choice; affects buy-and-hold comparison, not the level test (F6). |
| Cost under-statement? | No. Costs are at or above realistic retail levels except possibly gold/silver spread at news and roll times. The method fails before costs as well (gross R at or below random). |
| Bid-only bias? | Present in phase-3 metals; direction favours the strategy (F6). |
| Selection step touching the holdout? | No selection code reads the holdout. But the holdout year was viewed in phase 2 before phase 3 was designed (F8). |
| What was pre-registered? | Nothing for MSNR (F1). |
| Random-entry benchmark matched correctly? | Yes on geometry, costs and storyline direction; not on long/short mix for V0/V1, timing, or overlap (F5). |
| Do headline numbers reproduce? | Yes, all of them, to the third decimal; three wording corrections (section 1). |

## 4. What the evidence supports, stated carefully

1. **Net of costs the codified method loses on every market and timeframe with a meaningful sample.** Phase 1: 84 of 95 out-of-sample cells negative, the positive ones small-sample or contradicted in-sample. Phase 3 canonical, 15 real cells: -0.51 R per trade over 8,125 walk-forward trades, -0.38 R over 1,134 holdout trades.
2. **Before costs, entries at MSNR levels are statistically indistinguishable from random entries with the same stop and target.** Phase 1 out of sample: gross -0.058 R against -0.060 R for random over 50,108 trades (z = 0.26). Canonical phase 3: gross -0.034 R, interval [-0.071, +0.003].
3. **Win rates are what the stop/target geometry implies** (median 30.6% at 2R where 33.3% breaks even; 24.5% at 3R where 25% breaks even), not 80-90%.
4. **The Quasimodo variant is worse than random** in two of three timeframes (z about -2.3); with 15 variant-timeframe tests this is suggestive, not established.
5. **Searching 116,708 variants finds no configuration that survives false-discovery control with at least 100 trades**, under three different Deflated Sharpe settings.
6. **Not supported:** "support and resistance has no information" (the literature and the in-sample V0 result say there may be a little); "no discretionary MSNR trader can profit"; anything about FX pairs, equities or sub-5-minute execution.

## 5. Reruns: done, ready to run, and optional

Done today (all under 5 minutes each, outputs in `results\`):

| Script | Purpose | Runtime |
|---|---|---|
| `code\01_reproduce_headlines.py` | recompute 61 headline figures; build tables 1a, 2, 3, 3b, 4, 5, 6 | about 1 min |
| `code\02_intrabar_resolution_check.py` | robustness R1 (F4) | about 2 min |
| `code\03_histdata_clock_check.py` | phase-3 timestamp check (F2) | about 1 min |
| `code\04_figures_and_tables.py` | figures 1-8, tables 1b and 7 | about 1 min |
| `code\05_dsr_sensitivity.py` | Deflated Sharpe sensitivity (F7) | about 1 min |
| `code\06_truncation_lookahead_test.py` | look-ahead test of the phase-1 engine (F10) | about 3 min |

Command pattern (PowerShell, one at a time; the environment variable is set for that window only):
```
$env:NUMBA_CACHE_DIR = "D:\Research-Publishing\02-malaysian-snr\.numba_cache"
D:\Malaysian-SNR\.venv\Scripts\python.exe -B D:\Research-Publishing\02-malaysian-snr\code\01_reproduce_headlines.py
```

Not run, optional, in order of value (none is required for a go decision):
1. **Phase 1 on a locked copy with a fixed seed, by Sean, to show he can reproduce it:** `D:\Malaysian-SNR\.venv\Scripts\python D:\Malaysian-SNR\backtest\run_all.py` (about 90 s per the report; it overwrites `D:\Malaysian-SNR\results\`, so copy that folder first). Not run here because the brief forbids modifying the folder.
2. **Phase-3 canonical with true-UTC metals timestamps.** Needs a three-line change in a copy of `p3common.load_base` using `clockfix\cf_clock.fix_frame`. Expected to change nothing for the canonical configuration (F2). Runtime about 10-15 minutes for the 10 metals cells per the phase-A log (49-271 s per cell for all 4,464 configurations; far less for one). Script not written; only worth doing if a referee asks.
3. **Intrabar resolution for phase 3 and for the metals cells.** Not possible for 5-minute entries without tick data; state as a limitation.
4. **Direction-matched benchmark for V0/V1** (random side drawn with the strategy's own long share per cell). A ten-line extension of script 02; about 2 minutes.
