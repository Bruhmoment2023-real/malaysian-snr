# 03 - Formal rule specification of the tested method (draft appendix)

Purpose: a specification precise enough that another person could re-code the test. It describes what the code does (`D:\Malaysian-SNR\backtest\msnr.py`, `run_all.py`, `phase3\topdown.py`, `phase3\p3_msnr.py`), read line by line on 2026-10-13. Sean should rewrite it in his own words for the paper and check each clause against the code.

**Source tags.** Each rule carries one tag.
- **[C]** consensus across the teaching sources. **[S]** taught by some sources. **[A]** the author's operationalisation: no source gives a number or a precise rule, so one was chosen.
- Source keys: **V** = Vesath, "MSNR Key Levels MTF", MQL5 code 76993. **TG** = trading-guide, "Malaysian SnR Levels", TradingView. **DJ** = DoN_JCT, "Malaysian SnR and Decision Levels", TradingView (open source). **ZD** = zacdivan, "Malaysian SnR + Storyline", TradingView. **JZ** = Jithuze, "MSNR Jithuze Fresh Levels", TradingView. **CI** = Crow Investing, "MSNR Trading Explained (2026 Guide)". **SS** = "Malaysian SNR" PDF on SlideShare. **SC** = Scribd/CourseHero MSNR guides. **TK** = TikTok @toby.fx1 summary. Full URLs: `D:\Malaysian-SNR\research\MSNR-rules-and-sources.md`. Every quotation must be re-verified on the page by Sean before use.

## Notation

Bars on timeframe TF are indexed i = 1, 2, ... with open O_i, high H_i, low L_i, close C_i. A bar is bullish if C_i > O_i and bearish if C_i < O_i. ATR_i is the simple mean of the true range over the last 14 bars up to and including i **[A]**. All decisions at bar i use only bars up to i that have closed. "R" is the distance between entry price and stop price; results are in multiples of R.

## Part A - Core method (phase 1; five variants)

### A1. Levels (support and resistance are single prices taken from closes, never zones)

| # | Rule | Tag / source |
|---|---|---|
| A1.1 | **A-level (resistance), literal form:** if bar i-1 is bullish and bar i is bearish, a resistance level is created at price C_(i-1). | [C] V, TG |
| A1.2 | **V-level (support), literal form:** if bar i-1 is bearish and bar i is bullish, a support level is created at C_(i-1). | [C] V, TG |
| A1.3 | A level exists only once bar i has closed; it can first be used on bar i+1. | [C] V ("closed candles only") |
| A1.4 | **"Obvious" levels (pivot form):** bar p is a peak if C_p is strictly greater than each of the 3 closes before and the 3 closes after it; a valley if strictly lower. A peak gives a resistance at C_p, a valley a support at C_p. Usable from bar p+4. | [S] depth 3 = DJ default; the idea that only obvious peaks count = SS. Strict inequality and "3 on each side" = [A] |
| A1.5 | Gap levels (two same-colour candles with a close/open gap) are **not used**. | Departure from [C]; reason: 24-hour markets have almost no gaps |

### A2. Level state

| # | Rule | Tag / source |
|---|---|---|
| A2.1 | A new level is **fresh**. | [C] |
| A2.2 | **Body break:** if a bar closes above a resistance (C_j > level) it becomes a support, and becomes fresh again; mirror for support. | [C] role flip (SBR/RBS); re-freshening on a body cross = [S] TG, V |
| A2.3 | **Flip limit:** literal variant V0 allows unlimited flips; all other variants allow one flip, and the level is deleted at the next body break. | [S] unlimited = TG, V; limited use = JZ, UAlgo. "Exactly one" = [A] |
| A2.4 | **Retest:** bar j retests a resistance if H_j >= level, C_j <= level, and H_(j-1) < level (price had moved away and came back); mirror for support with lows. | Wick touch with close back = [C]. The "previous bar did not reach it" condition = [A] |
| A2.5 | After a retest the level is **unfresh** and gives no further signal until a body break re-freshens it. | [C]; strict "any wick touch" mode = V |

### A3. Signal, entry, stop, target

| # | Rule | Tag / source |
|---|---|---|
| A3.1 | **Signal:** a retest (A2.4) of a **fresh** level. Short at resistance, long at support. | [C] rejection entry |
| A3.2 | If the same bar signals both long and short, no trade. | [A] |
| A3.3 | **Entry:** market order at the open of bar j+1. | [S] CI ("open of the next candle") |
| A3.4 | **Stop:** long: L_j - 0.1 x ATR_j; short: H_j + 0.1 x ATR_j (just beyond the rejection wick). | Beyond the wick = [C] CI, SS. Buffer of 0.1 ATR = [A] (0.3 also run) |
| A3.5 | Skip the trade if the stop is not on the losing side of the entry price (R <= 0). | [A] |
| A3.6 | **Target:** entry + 2R (long) or entry - 2R (short). | [S] CI "minimum 1:2". Also run: 1R, 3R, and nearest fresh opposite level if at least 1R away ([C] "next opposing level") |
| A3.7 | **One position at a time** per instrument and timeframe; signals during an open trade are ignored. | [A] |
| A3.8 | **Exit simulation:** on each bar from the entry bar on, the stop is checked before the target. A bar that opens beyond the stop exits at the open. If neither is hit by the end of data the trade is closed at the last close. | [A] conservative convention; see audit F4 for its size |

### A4. Higher-timeframe bias ("storyline") and Quasimodo

| # | Rule | Tag / source |
|---|---|---|
| A4.1 | Higher timeframe: 4H for 1H trades, 1D for 4H, 1W for 1D. | [C] multi-timeframe hierarchy; the exact pairs = [A] |
| A4.2 | On the higher timeframe find alternating close pivots of depth 2 (confirmed 2 bars later). Bias becomes +1 when a higher-timeframe bar closes above the last confirmed pivot high, -1 when it closes below the last confirmed pivot low; otherwise unchanged. Only closed higher-timeframe bars count. | [S] pivot-based storyline = ZD. Depth 2 and the break rule = [A]. The taught storyline (rejection at a higher-timeframe level, then a lower-timeframe breakout) is used in Part B |
| A4.3 | **Quasimodo level (QML), bullish:** three consecutive confirmed close pivots (depth 2) low L1, high H1, low L2 with L2 < L1, followed by a close above H1. The QML is a support at L1 (the left shoulder). Bearish is the mirror. | [S] TK, QM school. Close pivots rather than wicks, depth 2 = [A] |
| A4.4 | A QML gives one signal on its first retest and is then deleted; a body close through it deletes it without a flip. | [S] one-time use; [A] detail |

### A5. The five variants

| Variant | Levels | Flip limit | Bias filter |
|---|---|---|---|
| V0 literal | A1.1-A1.2 on the trade timeframe | unlimited | none |
| V1 obvious levels | A1.4 on the trade timeframe | one | none |
| V2 | as V1 | one | trade only when the signal direction equals the bias (A4.2) |
| V3 Quasimodo | A4.3 only | none | as V2 |
| V4 higher-timeframe levels | A1.4 computed on the higher timeframe, retested on the trade timeframe | one | as V2 |

### A6. Fixed parameters and tested alternatives

| Parameter | Default | Also run |
|---|---|---|
| ATR length | 14 | - |
| Pivot depth for levels | 3 | 2 (phase 3) |
| Stop buffer | 0.1 ATR | 0.3 ATR |
| Target | 2R | 1R, 3R, nearest fresh opposite level (min 1R) |
| Sample split | first 60% of bars in-sample, last 40% out-of-sample | - |
| Random benchmark | 300 repetitions per cell | - |

## Part B - Canonical top-down method (phase 3)

Four timeframes T1 > T2 > T3 > T4. Three "ladders" are tested: (1W, 1D, 4H, 1H), (1D, 4H, 1H, 15m), (4H, 1H, 15m, 5m). Hierarchy as taught: storyline timeframe, roadblock timeframe one step lower, point-of-interest level, entry timeframe **[C] CI, SC**.

| # | Rule | Tag / source |
|---|---|---|
| B1 | **Levels** on T1, T2 and T3: pivot form A1.4 (depth 3), state rules A2.1-A2.5 with one flip. No gap levels. On T3, a level farther than 50 x ATR(T3) from the current T3 close is dropped. | [C]/[S] as Part A; pruning = [A] |
| B2 | **Storyline start:** a fresh T1 level is retested and rejected (A2.4 on T1). This sets a pending direction. | [C] SC: "price has to tap into a higher timeframe SNR and give a rejection" |
| B3 | **Storyline confirmation:** within 2 T1 bars, a T2 bar closes beyond the last confirmed T2 swing (wick pivot, depth 2) in that direction. The storyline is then active. | [C] SC: "then wait for a breakout on 1 or 2 time frames lower". Window and swing definition = [A] |
| B4 | **Storyline end:** price reaches the nearest fresh opposing T1 level that existed at the T1 rejection (the storyline target), or a T2 bar closes beyond the T1 rejection wick, or a new opposite storyline starts. | [C] SC: "only ends on an SNR level on that same time frame". Invalidation rule = [A] |
| B5 | **Point of interest:** a T4 wick touches a fresh T3 level (support for longs, resistance for shorts). The level becomes unfresh. A setup window opens for 3 T3 bars and closes early if a T4 bar closes more than 0.25 x ATR(T3) through the level. | Fresh-level touch = [C]. Window and invalidation = [A] |
| B6 | **Direction filter:** take the setup only if its direction equals the active storyline at the touch. | [C] |
| B7 | **Confirmation on T4**, the earlier of: (a) an engulfing candle in the trade direction (current body covers the previous opposite-colour body); (b) a break of structure: a T4 close beyond the last confirmed T4 swing high/low (wick pivot, depth 2). | [S] CI: rejection or engulfing confirmation; BOS = SMC overlap noted in the sources. Exact candle definitions = [A] |
| B8 | **Entry:** market order at the open of the T4 bar after the confirmation bar. | [S] CI |
| B9 | **Stop:** long: min(level, lowest low since the touch) - 0.1 x ATR(T3); short mirrored ("beyond the zone"). Trades with R below 0.05% of price are skipped. | Beyond the zone = [C] CI. Buffer and floor = [A] |
| B10 | **Target:** 3R. | [S] minimum 1:2 (CI); 3R chosen within the taught 1:2-1:4 range = [A] |
| B11 | **Roadblock filter:** skip the trade if a fresh opposing T2 level lies between entry and target. | [S] CI: roadblocks are levels one timeframe below the storyline |
| B12 | One position at a time; stop checked before target within a bar; gap through the stop filled at the open. | [A], as A3.7-A3.8 |
| B13 | **Not in the canonical rule, tested as variants:** liquidity (at least one unswept T3 swing point within 1 ATR beyond the level), miss (price came within 0.5 ATR without touching), London/New York session hours, limit entry at the level, storyline-end or roadblock targets, 2R/4R, pivot depth 2, gap levels, five extra indicator filters. | [S]/[D] proxies of discretionary filters; all thresholds = [A] |

## Part C - Benchmark and costs (needed to reproduce the results)

| # | Rule |
|---|---|
| C1 | **Random-entry benchmark:** in the same instrument and window, draw the same number of trades as the strategy. Each random trade enters at the open after a uniformly drawn bar. Its stop distance (in ATR units) and target multiple are drawn jointly from the strategy's own trades and scaled by the ATR at the random bar. Direction is a coin flip, or the storyline direction at that bar for variants that use a storyline (bars with no storyline are redrawn). Same exit logic and costs. Repeat 300 times (phase 1) or 200/60 times (phases 2-3). |
| C2 | **Comparison statistic:** strategy mean gross R minus the mean of the repetition means; p = share of repetitions at or above the strategy (one-sided, with +1 correction); pooled z across instruments weights by trade count. |
| C3 | **Costs** are subtracted per trade in R: see `results\table7_cost_assumptions_as_coded.csv`. Carry 2-3% per year pro rata to holding time. |
| C4 | **Position size** (only for the equity-curve charts): 1% of equity risked per trade, leverage capped at 10x. Results in R do not depend on it. |

## Known departures from the method as taught (state these in the paper)

1. Levels are selected by a pivot rule, not by a trader's judgement of which peaks are "obvious" or "have liquidity".
2. No M1-M5 "sniper" refinement of entries below the entry timeframe (the finest entry bar is 5 minutes).
3. Gap levels omitted (A1.5).
4. Fixed R targets by default; the taught "next opposing level" target is a tested alternative, not the default.
5. Session timing, news avoidance and manual trade management are not modelled.
