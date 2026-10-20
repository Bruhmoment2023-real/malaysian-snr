# 01 - Prior work and novelty verdict

Compiled 2026-10-13. Every entry says how far it was read: **[FULL]** full text opened, **[ABS]** abstract only, **[META]** bibliographic record only (Crossref), **[NOT OPENED]** cited in the project's earlier notes but not opened by anyone in this project. Sean must open every paper he cites; a citation he has not read is a risk in a viva.

## Novelty verdict

**The subject is new; the genre is not.**

- **No academic or working-paper test of "Malaysian SnR" / "MSNR" was found.** Searches run today:
  - arXiv API, exact phrases, all fields: "Malaysian SnR" 0 hits; "smart money concepts" 0; "inner circle trader" 0; "fair value gap" 0; "supply and demand zones" 0; "order block" + trading 2 hits, both unrelated (networks, blockchain); quasimodo + trading 1 hit, unrelated.
  - arXiv "support and resistance" in q-fin: 9 hits, listed below; none tests a retail close-line/fresh-level method.
  - Crossref bibliographic search: "Malaysian SNR" trading returned only signal-to-noise and unrelated Malaysian finance papers in the top results.
  - OpenAlex and Semantic Scholar: **both returned HTTP 429 (rate limited)**, so those two indexes were NOT searched. Google Scholar was not searched (no API, search budget). The verdict is therefore "none found in arXiv and Crossref", not "none exists".
- **Close relatives HAVE been tested in 2026, in unreviewed working papers.** This was missed by the earlier scoping pass and changes the framing:
  - Mahadzva (2026), SSRN, tests six ICT / smart-money-concepts rules (liquidity sweeps, order blocks, change of character, fair value gaps) on four FX pairs.
  - Mahadzva (2026), SSRN "Deflated Alpha Series" (at least eight papers found): retail FX rules, Fibonacci, session breakouts, calendar, mean reversion, COT, cross-asset divergence, all with walk-forward, random-entry permutation test, Deflated Sharpe and a holdout.
  - Darmanin (2026), arXiv: five retail signal families on US equities with multiplicity control.
- **What remains genuinely unoccupied** (as far as these searches go):
  1. MSNR itself: close-only "A/V" levels, the fresh/unfresh state rule, role flips, Quasimodo levels, storyline/roadblock top-down process.
  2. A direct test of the "fresh level is best" belief against a matched random benchmark (Chung and Bellotti find the opposite direction for tested levels, on different level definitions).
  3. The markets where MSNR is actually taught: gold, silver, crypto. Mahadzva covers G10 FX (plus gold in one paper); Darmanin covers US equities.
  4. A rule specification traced clause by clause to the teaching sources, with consensus/some/discretionary tags.
- **Safe wording for the paper:** "To my knowledge, and based on searches of arXiv and Crossref on 13 October 2026, no prior study tests the Malaysian SnR method. Related social-media methods have been examined in recent working papers (Darmanin 2026; Mahadzva 2026)." Do not write "first study of retail trading methods" or "first multiple-testing-controlled test".
- **Still to do:** repeat the search in Google Scholar and SSRN by hand (terms: "Malaysian SnR", "MSNR trading", "Malaysian support and resistance", "QML Quasimodo trading", "fresh level"), and record the date and hit counts.

## A. Nearest competitors (read these first)

| Work | Read | What it does | How Sean's study differs |
|---|---|---|---|
| Darmanin, A. (2026). *Retail Trader's Ruin: An Anatomy of Popular Signal Failure.* arXiv:2607.20093 (q-fin.ST), v1 22 Jul 2026, 12 pages, "not externally peer reviewed". https://arxiv.org/abs/2607.20093 | **[FULL]** (HTML version) | Five families: trend (50/200 SMA cross), oscillator (RSI 14, MACD 12/26/9, Bollinger 20/2), a 7-pattern candlestick battery, volume (OBV, monthly, Russell 3000), calendar (Sell-in-May selected). Data: NASDAQ-100 and SPY daily, point-in-time Russell 3000 and S&P 500. Three "predeclared" gates: Sharpe gap vs an exposure-matched benchmark with stationary-bootstrap CI; CAGR gap net of 10 bp; bankroll survival under leverage. Multiplicity: two-stage Benjamini-Yekutieli. Result: 4 of 6 refuted, trend and momentum inconclusive, none supported. States no pristine holdout and no external registry. Code "will be made available". | (1) **No support/resistance or price-level rule at all**; it explicitly excludes breakout/channel rules and chart patterns beyond candlesticks. (2) US equities daily; Sean tests gold, silver, crypto from 5-minute to daily. (3) Benchmark is exposure-matched buy-and-hold/cash, not random entries with matched stop/target geometry. (4) Darmanin tests indicator rules with fixed textbook parameters; Sean codifies a multi-step discretionary method from teaching sources. (5) Darmanin uses equivalence tests and a three-way verdict (refuted / inconclusive / supported), which is **better practice** than Sean's study and worth borrowing. |
| Mahadzva, S. (2026). *Smart Money or Costly Folklore? A Systematic Evaluation of ICT/Smart-Money-Concepts Trading Rules in G10 FX.* SSRN. https://doi.org/10.2139/ssrn.7430998 | **[ABS]** (full abstract via Crossref; SSRN page not opened) | Six mechanical ICT/SMC rules on EURUSD, GBPUSD, AUDUSD, USDJPY intraday; walk-forward, bootstrap, permutation, holdout. "No evidence that ICT/SMC concepts work as literally taught." Reports that swept levels predict continuation not reversal, one "flagship" faded setup with p = 0.0192 that fails the Deflated Sharpe at every trial count, and a tight-stop cost finding. | **The closest relative.** Differences: MSNR is not among the rules; FX majors only; no fresh/unfresh level state; Sean's sample is larger per rule (tens of thousands of trades vs 33-60 for the flagship) and uses a matched random benchmark on gross R. Similarity to acknowledge: same finding that tight stops make fixed costs dominate. |
| Mahadzva, S. (2026). *Multiple Testing and the Mirage of Technical Alpha: A Deflated-Sharpe Reassessment of Retail Trading Rules in G10 Spot FX* (Deflated Alpha Series, paper 1 of 10). SSRN. https://doi.org/10.2139/ssrn.7430758 | **[ABS]** | MA crossovers, Bollinger, Donchian on four FX pairs, six years; "fully pre-registered" six-fold anchored walk-forward, 15% holdout; random-entry permutation test, Deflated Sharpe over 7,708 trials; 0 of 45 combinations pass. | Same toolkit (walk-forward, random-entry null, DSR, holdout). Sean cannot claim the toolkit as a contribution. Different rules and markets. |
| Mahadzva, S. (2026). *The Fibonacci Illusion ...* https://doi.org/10.2139/ssrn.7430898; *Session Microstructure and the Momentum Mirage ...* https://doi.org/10.2139/ssrn.7435081; *Fading the Almanac ...* https://doi.org/10.2139/ssrn.7434881; *How Fast do Currencies Really Mean-revert? ...* https://doi.org/10.2139/ssrn.7435180; *Does Positioning Data Predict Currency Returns? ...* https://doi.org/10.2139/ssrn.7434900; *Divergence in Disguise ...* (gold and G10 FX) https://doi.org/10.2139/ssrn.7431518 | **[ABS]** (first ~700 characters each) | Same protocol applied to other retail ideas. None is about support/resistance levels as far as the abstracts show. Two of the ten papers in the series were not found; one of them could concern support/resistance. | Check the two missing papers by hand on SSRN (author page) before claiming the gap. |
| StatOasis, "ICT backtest: what survives" (web page, non-academic). https://statoasis.com/overfit/research/ict-backtest-what-survives | **[NOT OPENED today]** (opened by the earlier scoping pass) | Practitioner backtest of ICT entries. | Grey literature; cite only as context, if at all. |
| Bindra, T. (2026). *Multi-Asset A/A+ Momentum Fair Value Gap Strategy.* SSRN. https://doi.org/10.2139/ssrn.6725880 | **[ABS]** | Claims 78% win rate, +265 R, 132.5% in one calendar year (2025) on histdata M1, 473 trades. No out-of-sample or multiple-testing control is mentioned in the abstract. | Useful as an example of the kind of claim the paper tests. Do not treat as evidence. |

## B. Support and resistance: does the idea have any academic support?

| Work | Read | Relevance |
|---|---|---|
| Osler, C. L. (2000). Support for resistance: technical analysis and intraday exchange rates. *FRBNY Economic Policy Review* 6(2), 53-68. https://www.newyorkfed.org/medialibrary/media/research/epr/2000/eprvol6no2.pdf | **[NOT OPENED today]**; pages 53-68 are from memory and must be checked | Published support/resistance levels from six firms predicted intraday trend interruptions better than arbitrary levels. The classic "levels have some information" result. Note the benchmark design: real levels vs artificial levels - the same logic as Sean's random-entry benchmark. |
| Osler, C. L. (2003). Currency orders and exchange rate dynamics: an explanation for the predictive success of technical analysis. *Journal of Finance* 58(5), 1791-1819. https://doi.org/10.1111/1540-6261.00588 | **[META]** | Stop-loss and take-profit orders cluster at round numbers; gives a mechanism for reversals at levels and fast moves through them. This is the nearest academic counterpart of the "liquidity" story in MSNR teaching. |
| Osler, C. L. (2005). Stop-loss orders and price cascades in currency markets. *Journal of International Money and Finance* 24(2), 219-241. https://doi.org/10.1016/j.jimonfin.2004.12.002 | **[META]** | Price cascades when stop clusters are hit. Relevant to "break of a level" behaviour. |
| Kavajecz, K. A. and Odders-White, E. R. (2004). Technical analysis and liquidity provision. *Review of Financial Studies* 17(4), 1043-1071. https://doi.org/10.1093/rfs/hhg057 | **[META]** | Support/resistance levels coincide with peaks of depth in the limit order book. Supports "levels reflect resting liquidity"; says nothing about profitability after costs. |
| Chung, K. and Bellotti, A. (2021). Evidence and behaviour of support and resistance levels in financial time series. arXiv:2101.07410. https://arxiv.org/abs/2101.07410 | **[ABS]** | Heuristic level-finding on intraday prices. Levels reverse price at a statistically significant rate; **more previous bounces make a further bounce more likely; bounce probability decays as the level ages.** The first finding cuts against "fresh is best"; the second is mildly consistent with preferring recent levels. The paper must present both, not only the convenient one. Assets and frequency are not in the abstract: open the PDF. |
| Donaldson, R. G. and Kim, H. Y. (1993). Price barriers in the Dow Jones Industrial Average. *Journal of Financial and Quantitative Analysis* 28(3), 313-330. https://doi.org/10.2307/2331416 | **[META]** (end page from memory) | Round-number barriers in an index. |
| Zapranis, A. and Tsinaslanidis, P. E. (2012). Identifying and evaluating horizontal support and resistance levels: an empirical study on US stock markets. *Applied Financial Economics* 22(19), 1571-1585. https://doi.org/10.1080/09603107.2012.663469 | **[META]** | Algorithmic horizontal levels on US stocks. Sean should open it to see how they validate levels. |
| Garzarelli, F., Cristelli, M., Pompa, G., Zaccaria, A. and Pietronero, L. (2014). Memory effects in stock price dynamics: evidences of technical trading. *Scientific Reports* 4, 4487. https://doi.org/10.1038/srep04487 (open access; arXiv:1110.5197) | **[META]** | Bounce probability rises with the number of previous bounces. Same direction as Chung and Bellotti; again against "fresh". |
| Lo, A. W., Mamaysky, H. and Wang, J. (2000). Foundations of technical analysis. *Journal of Finance* 55(4), 1705-1765. https://doi.org/10.1111/0022-1082.00265 | **[META]** | The standard reference for turning chart patterns into algorithms. Supports the legitimacy of codifying a visual method. |
| (authors not looked up) (2021). The support and resistance line method: an analysis via optimal stopping. arXiv:2103.02331 | **[META]** (title and id only, from the arXiv listing) | Theory paper. Optional. Verify authors before citing. |

## C. Data snooping in technical trading rules

| Work | Read | Relevance |
|---|---|---|
| Brock, W., Lakonishok, J. and LeBaron, B. (1992). Simple technical trading rules and the stochastic properties of stock returns. *Journal of Finance* 47(5), 1731-1764. https://doi.org/10.1111/j.1540-6261.1992.tb04681.x | **[META]** | Includes trading-range-break (support/resistance) rules on the Dow, 1897-1986. The positive result that later papers stress-test. |
| Sullivan, R., Timmermann, A. and White, H. (1999). Data-snooping, technical trading rule performance, and the bootstrap. *Journal of Finance* 54(5), 1647-1691. https://doi.org/10.1111/0022-1082.00163 | **[META]** | 7,846 rules; the best rule's significance must be judged against the whole searched universe. The model for Sean's "count everything you tried". |
| White, H. (2000). A reality check for data snooping. *Econometrica* 68(5), 1097-1126. https://doi.org/10.1111/1468-0262.00152 | **[META]** | Defines the Reality Check used in phases 2-3. |
| Hansen, P. R. (2005). A test for superior predictive ability. *Journal of Business and Economic Statistics* 23(4), 365-380. https://doi.org/10.1198/073500105000000063 | **[META]** | SPA: a studentised, less conservative version; handles many poor rules better. Used in phases 2-3. |
| Politis, D. N. and Romano, J. P. (1994). The stationary bootstrap. *Journal of the American Statistical Association* 89(428), 1303-1313. https://doi.org/10.1080/01621459.1994.10476870 | **[META]** | The resampling scheme inside both tests. |
| Romano, J. P. and Wolf, M. (2005). Stepwise multiple testing as formalized data snooping. *Econometrica* 73(4), 1237-1282. https://doi.org/10.1111/j.1468-0262.2005.00615.x | **[META]** | Identifies which rules are significant, not only whether the best is. Not used in the study; cite as the alternative. |
| Hsu, P.-H., Hsu, Y.-C. and Kuan, C.-M. (2010). Testing the predictive ability of technical analysis using a new stepwise test without data snooping bias. *Journal of Empirical Finance* 17(3), 471-484. https://doi.org/10.1016/j.jempfin.2010.01.001 | **[META]** | Stepwise SPA. |
| Bajgrowicz, P. and Scaillet, O. (2012). Technical trading revisited: false discoveries, persistence tests, and transaction costs. *Journal of Financial Economics* 106(3), 473-491. https://doi.org/10.1016/j.jfineco.2012.06.001 | **[META]** | FDR applied to the 7,846 rules; apparent winners do not persist and vanish after costs. The closest methodological precedent for "FDR + costs + persistence" - and Sean's Figure 4 is a persistence test in the same spirit. |
| Hsu, P.-H., Taylor, M. P. and Wang, Z. (2016). Technical trading: is it still beating the foreign exchange market? *Journal of International Economics* 102, 188-208. https://doi.org/10.1016/j.jinteco.2016.03.012 | **[META]** | Over 21,000 rules on 30 currencies with stepwise tests; profitability declines over time. Large-scale benchmark for what a serious rule search looks like. |
| Park, C.-H. and Irwin, S. H. (2007). What do we know about the profitability of technical analysis? *Journal of Economic Surveys* 21(4), 786-826. https://doi.org/10.1111/j.1467-6419.2007.00519.x | **[META]** | Survey; use for the opening paragraph. |
| Menkhoff, L. and Taylor, M. P. (2007). The obstinate passion of foreign exchange professionals: technical analysis. *Journal of Economic Literature* 45(4), 936-972. https://doi.org/10.1257/jel.45.4.936 | **[META]** | Why practitioners keep using it. |

## D. Multiple testing and backtest overfitting

| Work | Read | Relevance |
|---|---|---|
| Benjamini, Y. and Hochberg, Y. (1995). Controlling the false discovery rate. *Journal of the Royal Statistical Society B* 57(1), 289-300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x | **[META]** | The BH procedure used in phases 2-3. Note: BH assumes independent or positively dependent tests; Darmanin uses Benjamini-Yekutieli (2001) for arbitrary dependence. A referee may ask why BH and not BY. |
| Harvey, C. R. and Liu, Y. (2015). Backtesting. *Journal of Portfolio Management* 42(1), 13-28. https://doi.org/10.3905/jpm.2015.42.1.013 | **[META]** | Sharpe-ratio haircuts for multiple testing. |
| Harvey, C. R., Liu, Y. and Zhu, H. (2016). ... and the cross-section of expected returns. *Review of Financial Studies* 29(1), 5-68. https://doi.org/10.1093/rfs/hhv059 | **[META]** | Raises the t-hurdle to about 3 for new factors. |
| Harvey, C. R., Liu, Y. and Saretto, A. (2020). An evaluation of alternative multiple testing methods for finance applications. *Review of Asset Pricing Studies* 10(2), 199-248. https://doi.org/10.1093/rapstu/raaa003 | **[META]** | Compares the methods; good single source for the methods section. |
| Bailey, D. H. and Lopez de Prado, M. (2014). The Deflated Sharpe Ratio: correcting for selection bias, backtest overfitting and non-normality. *Journal of Portfolio Management* 40(5), 94-107. https://doi.org/10.3905/jpm.2014.40.5.094 | **[META]** | The DSR formula coded in `phase2\p2_phaseA.py`. Sean must check the code against the paper's equations himself (expected maximum Sharpe under N trials; the variance-of-trials input). |
| Bailey, D. H., Borwein, J. M., Lopez de Prado, M. and Zhu, Q. J. (2017). The probability of backtest overfitting. *Journal of Computational Finance* 20(4), 39-69. https://doi.org/10.21314/JCF.2016.322 | **[META]** (volume/pages from memory; Crossref shows 2016 online) | PBO via combinatorially symmetric cross-validation. **PBO was not computed in this study**; either compute it or do not claim it. |
| Bailey, D. H., Borwein, J. M., Lopez de Prado, M. and Zhu, Q. J. (2014). Pseudo-mathematics and financial charlatanism. *Notices of the AMS* 61(5), 458-471. https://doi.org/10.1090/noti1105 | **[META]** | Readable and free; best first read on overfitting. |
| Barras, L., Scaillet, O. and Wermers, R. (2010). False discoveries in mutual fund performance. *Journal of Finance* 65(1), 179-216. https://doi.org/10.1111/j.1540-6261.2009.01527.x | **[META]** | FDR in finance; optional. |
| McLean, R. D. and Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance* 71(1), 5-32. https://doi.org/10.1111/jofi.12365 | **[META]** | Out-of-sample decay; optional. |

## E. Do retail traders make money? (motivation paragraph)

| Work | Read | Relevance |
|---|---|---|
| Barber, B. M., Lee, Y.-T., Liu, Y.-J. and Odean, T. (2014). The cross-section of speculator skill: evidence from day trading. *Journal of Financial Markets* 18, 1-24. https://doi.org/10.1016/j.finmar.2013.05.006 | **[META]** | Fewer than 1% of Taiwanese day traders are reliably profitable. |
| Chague, F., De-Losso, R. and Giovannetti, B. (2020). Day trading for a living? SSRN 3423101. https://doi.org/10.2139/ssrn.3423101 | **[NOT OPENED]** | 97% of Brazilian day traders who persisted lost money. Check the exact figure in the paper. |
| SEBI press release, 23 Sept 2024: 93% of individual equity-derivatives traders lost money, FY22-FY24. | **[NOT OPENED today]** (confirmed by the earlier scoping pass) | The Indian angle; get the PR number and URL from sebi.gov.in. |

## F. Primary sources for the method itself

All listed with URLs in `D:\Malaysian-SNR\research\MSNR-rules-and-sources.md` (accessed 2026-10-05 by an AI agent). Status for the paper:
- That file states that YouTube pages and several Scribd/CourseHero documents "could not be read in full" and that some quotes come from search-result snippets; the UAlgo TradingView script returned 404.
- **Sean must re-open each source himself, save a dated copy (web.archive.org "Save Page Now" is free and needs no account) and quote only what he has seen on the page.** A rule tagged to a source that a referee cannot open is not traceable.
- Strongest, most citable sources because they contain explicit code or rules: the Vesath MQL5 indicator (exact A/V definition), the DoN_JCT open-source Pine script (pivot depth 3), the trading-guide TradingView script (fresh/unfresh re-freshening), Crow Investing guide (entry, stop, minimum 1:2).

## Sources used for this file

- arXiv API queries (export.arxiv.org), 13 Oct 2026.
- Crossref REST API (api.crossref.org) for every DOI above, 13 Oct 2026.
- arXiv HTML full text of 2607.20093v1; arXiv abstract page of 2101.07410.
- Not reached: OpenAlex (HTTP 429), Semantic Scholar (HTTP 429), SSRN pages, Google Scholar.
