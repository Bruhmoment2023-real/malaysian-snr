"""Hand-written evidence notes for paper 02: one line per paper, taken from the abstract held in data/clean/master.csv.
'metadata only' rows had no abstract in OpenAlex, Crossref or Semantic Scholar: nothing is claimed about their findings.
Run: python evidence_notes_p02.py -> data/clean/evidence_notes.json (then python kit/pdfs.py <dir> download|evidence)"""
import json, os
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AR, MO = "abstract read", "metadata only (no abstract available)"
N = []
def add(i, study, country, data, method, finding, rel, status=AR):
    N.append(dict(oa_id=i, study_type=study, country=country, data=data, method=method, finding=finding, relation=rel, read_status=status))
def mo(i, study, country, rel, what="not stated in the record"):
    add(i, study, country, what, "not stated in the record", "No abstract in OpenAlex, Crossref or Semantic Scholar; findings not summarised.", rel, MO)

# ---------------- B. support and resistance, price levels, order clustering
add("W2136854181", "journal article, empirical", "foreign exchange (intraday)", "support and resistance levels supplied to customers by six FX firms", "tests whether the published levels predict intraday trend interruptions",
    "Strong evidence that the levels help predict intraday trend interruptions, but predictive power varies across exchange rates and firms.", "The classic 'levels carry information' result; its benchmark of real versus other levels parallels the random-entry design. Published (firm-supplied) levels, not close-line levels.")
add("W2080887613", "journal article, empirical", "foreign exchange", "individual currency stop-loss and take-profit orders (first such data)", "order clustering analysis",
    "Take-profit orders cluster at round numbers and stop-loss orders just beyond them, offering an explanation for reversals at support/resistance and for fast moves after levels are crossed.", "Mechanism for 'liquidity at levels' stories; says nothing about net profitability.")
add("W3124405065", "journal article, empirical", "US equities", "limit order book depth", "relation of technical levels to book depth",
    "Support and resistance levels coincide with peaks in depth on the limit order book, and moving-average forecasts reveal where depth sits; technical rules locate depth already in place.", "Supports 'levels reflect resting liquidity'; no profit test.")
add("W3122388722", "working paper (arXiv), empirical", "intraday financial series", "intraday price series", "heuristic discovery algorithm for support and resistance levels",
    "Discovered levels reverse price trends at a statistically significant rate; levels with more previous bounces are more likely to bounce again, and bounce probability decays as a level ages.", "Direct evidence on 'fresh versus tested' levels: more past bounces raise bounce probability, which cuts against 'fresh is best'.")
add("W2108762681", "journal article, empirical", "stocks", "price time series", "criterion to detect supports and resistances; memory-effect test",
    "Memory effects in price dynamics are associated with the detected support/resistance values: prices more likely re-bounce than cross them.", "Same direction as Chung and Bellotti on repeated bounces.")
add("W1986675767", "journal article, empirical", "US stocks (NASDAQ, NYSE)", "daily closes, last two decades, adjusted for dividends and splits", "rule-based identification of horizontal support/resistance levels, tested as trend-reversal predictors and for abnormal returns",
    "Results are described as aligned with the efficient market hypothesis (abstract truncated in this read).", "Shows how a codified level definition is validated on stocks.")
add("W2123305298", "journal article, empirical", "US (DJIA)", "Dow Jones Industrial Average", "tests with Monte Carlo and comparison indices",
    "The index's rise and fall is restrained at support and resistance levels at multiples of 100, and after breaking a 100-level it moves more than otherwise warranted.", "Round-number barrier evidence.")
add("W1530852332", "working paper, empirical", "three exchange rates", "chartist-supplied support and resistance levels", "profitability of signals from breaking of levels, with transaction costs",
    "Trading-range breaks generate profitable signals even after transaction costs, and signals built from chartists' inputs are more frequent and profitable.", "Level-break rules in FX; era and data are old.")
add("W1971669226", "journal article, empirical", "intraday foreign exchange", "filter rules supplied by technical analysts", "intraday simulation with transaction costs",
    "Some profits are available in trending periods but not on average, and the result is strengthened after transaction costs.", "Intraday FX rules lose after costs, as the paper expects.")
mo("W2570892994", "journal article", "foreign exchange", "Stop-loss orders and price cascades in currency markets (title): relevant to breaks of levels.")
add("W2003569572", "journal article, empirical", "US stocks", "transaction prices", "econometric model of price clustering",
    "Stock prices cluster on round fractions; clustering rises with price level and volatility and falls with capitalisation and transaction frequency.", "Round-number clustering background.")
mo("W2736872974", "journal article", "Bitcoin", "Price clustering in Bitcoin (title): the crypto market of the paper.")

# ---------------- A. technical analysis, trading-rule profitability
add("W2101544483", "journal article, empirical", "US (DJIA 1897-1986)", "Dow Jones Index", "moving average and trading-range-break rules with bootstrap against four null models",
    "Results provide strong support for the technical strategies: returns are not consistent with random walk, AR(1), GARCH-M or EGARCH nulls, and buy signals generate higher returns than sell signals.", "The positive result that data-snooping papers stress-test; includes trading-range-break (support/resistance) rules.")
add("W2143152597", "journal article, empirical", "US (DJIA, 100 years)", "daily Dow Jones data", "White's Reality Check over the full universe of rules (expands Brock et al.'s 26 rules)",
    "Evaluates all rules examined with the data-snooping bias fully adjusted for (full conclusions truncated in this read).", "Template for 'count everything you tried'.")
add("W2171059853", "journal article, empirical", "foreign exchange", "2,127 technical trading rules", "Reality Check applied to FX rules",
    "The best rules are significantly profitable by standard tests; data-snooping adjustment does not change the full-sample conclusion, but profitability is much weaker in the more recent period.", "Decline of rule profits over time.")
add("W1587271453", "journal article, empirical", "US futures (17 markets, 1985-2004)", "futures prices", "White's Reality Check and Hansen's SPA",
    "The best rules generate significant economic profits in only two of 17 futures markets after correcting for data snooping.", "Large-universe snooping-corrected test.")
add("W2100376816", "journal article, empirical", "four stock indices", "simple rules and complex strategies", "Reality Check and SPA",
    "Significantly profitable rules and strategies exist in 'young' markets (NASDAQ Composite, Russell 2000) but not in 'mature' markets such as the Dow (abstract truncated).", "Market-maturity dependence.")
add("W2337071880", "journal article, empirical", "30 currencies, 45 years", "daily data", "stepwise test over more than 21,000 rules, out-of-sample cross-validation",
    "Finds substantial predictability and excess profitability in both developed and emerging currencies, with time-series and cross-sectional variation (abstract truncated).", "Large-scale benchmark for a serious rule search; contrasts with 'decline over time' papers.")
mo("W3122236376", "journal article, empirical", "US (7,846 rules)", "Bajgrowicz and Scaillet: false discoveries, persistence tests and transaction costs (title).")
mo("W3122057860", "journal article", "US indices", "Hsu, Hsu and Kuan: stepwise test without data-snooping bias (title).")
add("W2134658143", "journal article, review", "mostly US/FX/futures", "95 modern studies reviewed", "survey of the empirical literature",
    "Early studies find technical strategies profitable in FX and futures but not stocks; of 95 modern studies, 56 find positive results (abstract truncated).", "Opening-paragraph survey.")
add("W2130180922", "journal article, survey review", "foreign exchange", "literature and surveys", "stylised facts and four explanations",
    "Technical analysis is widely used in FX and applying certain rules over a sustained period may give significant positive excess returns; the paper analyses four arguments explaining this.", "Why practitioners keep using it.")
add("W2077894872", "journal article, survey", "FX dealers and fund managers", "survey responses", "extension of earlier survey studies",
    "Technical analysis is the most equally spread kind of analysis, by far the most important in FX dealing and second in fund management; charts dominate for shorter horizons.", "Use of chart analysis among professionals.")
add("W1980988541", "journal article, empirical", "foreign exchange", "head-and-shoulder rule definitions", "variants of the pattern definition",
    "For various combinations of definitions the result is generally negative: returns to head-and-shoulder rules are not significantly positive.", "Codifying a visual pattern into rules.")
add("W2890714735", "journal article, empirical", "currency futures 1976-1990", "currency futures", "bootstrap",
    "Simple technical trading rules have often led to profits that are highly unusual; profitability of some rules declined in the latest sub-period.", "Early bootstrap evidence for FX rules.")
add("W2104955455", "journal article, empirical", "foreign exchange", "FX series", "genetic programming", "Only the citation is given in the abstract field; no finding available.", "Data-snooping-free rule generation.", MO)
add("W2947760525", "journal article, empirical", "Bitcoin (high frequency)", "high-frequency Bitcoin returns", "moving-average oscillator and trading-range breakout (support/resistance) strategies",
    "Significant support for moving-average strategies, with the variable-length moving-average rule performing best and buy signals earning more than sell signals.", "Crypto rules including level breakouts.")
add("W3036304463", "journal article, empirical", "cryptocurrencies", "crypto prices, several frequencies", "reality check for machine-learning and technical rules",
    "After controlling for data snooping and frictions, significant positive excess returns are rarely achieved; trading rules mostly capture market risk premiums.", "Closest crypto analogue of the paper's multiple-testing design.")
add("W2970972678", "journal article, empirical", "Bitcoin and three other cryptocurrencies", "almost 15,000 rules from five classes", "multiple hypothesis procedures against data snooping",
    "Finds significant predictability and profitability for each class of rule in each cryptocurrency, with breakeven transaction costs well above typical crypto costs.", "Contradicts Anghel et al.; shows result depends on the rule universe and period.")
add("W2967069906", "journal article, empirical", "Bitcoin 2010-2019", "daily prices", "seven trend-following indicators, bootstrapped Sharpe",
    "Specific rules, mainly trading-range breakout, have significant forecasting power and outperform buy-and-hold on Sharpe ratio.", "Range-breakout evidence in crypto.")
add("W2902273645", "journal article, empirical", "WTI crude oil futures", "daily prices", "the 7,846-rule Sullivan-Timmermann-White universe in five families including support and resistance",
    "Applies the full universe (filter, moving average, support and resistance, channel breakout, on-balance volume) to crude oil; findings truncated in this read.", "Includes a support/resistance family on a commodity.")
add("W3215706775", "journal article, empirical", "spreads, 1990-2016", "daily data", "18,410 rules with a false-discovery control",
    "Evidence of predictability is stronger for commodity spreads than for equity and currency spreads, and out-of-sample portfolios of significant rules exceed cost estimates (Sharpe 3.67 in 2016).", "False-discovery-controlled rule search.")
add("W2885189127", "journal article, empirical", "asset allocation", "15,376 monthly rules", "RC, SPA, extensions and FDR",
    "None of 15,376 technical trading rules at monthly frequency outperforms buy-and-hold in terms of a 1/N portfolio.", "Another null result under snooping control.")
add("W7170163211", "working paper (arXiv), multiple-testing study", "US equities", "index and cross-sectional panels", "predeclared gates, stationary bootstrap, Benjamini-Yekutieli, equivalence tests",
    "Four of six candidate retail signal families are refuted, trend and a momentum benchmark are inconclusive, none supported.", "Nearest competitor; no support/resistance rule. Method to borrow: three-way verdict.")
mo("W7212746204", "working paper (SSRN)", "G10 FX", "Mahadzva (2026), ICT / smart-money-concepts rules in G10 FX (title). The pack read its abstract: closest relative.")
mo("W7212621260", "working paper (SSRN)", "G10 FX", "Mahadzva (2026), deflated-Sharpe reassessment of retail trading rules (title). Same toolkit as the paper.")
add("W2343368277", "journal article, empirical", "Malaysia (KLSE Composite 1977-1999)", "daily index returns", "variance ratio test and moving-average rules",
    "Results indicate non-randomness of successive price changes and that the rules show technical attractiveness even with transaction costs.", "Malaysian equity context; not the MSNR method.")
add("W1984961676", "journal article, empirical", "16 European stock markets 1990-2006", "index data", "moving-average rules with White's Reality Check",
    "Increasing moving-average rules have predictive power even after accounting for data-snooping bias.", "Positive result under RC.")
add("W2137770255", "journal article, empirical", "China (SSCI, CSI 300)", "index data 1992-2013", "more than 7,000 rules with SPA", "Tests whether an effective rule can be found using performance measures (findings truncated in this read).", "Large rule universe outside the US.")
add("W2765547313", "journal article, empirical", "Chinese stock market", "19 years daily", "stepwise SPA over more than 28,000 signals", "Substantial evidence of profitability of technical rules measured by market timing or Sharpe gain (abstract truncated).", "Positive result under stepwise SPA.")
add("W2170117595", "journal article, empirical", "Taiwan stock market", "two broad rule sets", "White and Hansen bootstrap tests with institutional adjustments", "Tests whether a superior rule exists in Brock et al. and Sullivan et al. rule sets (findings truncated in this read).", "Snooping-corrected test in Asia.")
add("W2133621418", "journal article, empirical", "five Southeast Asian stock indices 2000-2013", "index data", "RSI, stochastic, MACD and others", "Examines the profitability of technical rules in SET, FTSE Bursa Malaysia KLCI, STI, JCI and PSEi (findings truncated in this read).", "Regional context for the 'Malaysian' label.")
add("W2527757929", "journal article, empirical", "Malaysia", "stocks", "variable moving-average rules and Elliott wave with Fibonacci numbers", "Of 42 variable-moving-average rules tested, only 10 gave buy-signal mean returns significantly above the unconditional return (abstract truncated).", "Malaysian-market TA; Fibonacci tools used by retail methods.")

# ---------------- C. data snooping, multiple testing, overfitting
add("W2135606128", "journal article, theory + method", "n/a", "none", "bootstrap Reality Check for the best of many models",
    "Provides a straightforward procedure for testing the null that the best model among many has no superior predictive ability, accounting for data reuse (abstract truncated).", "Defines the Reality Check used in the pack's phases 2-3.")
add("W3123939061", "journal article, theory", "n/a", "none", "stepwise multiple testing controlling the familywise error rate",
    "A stepwise procedure that asymptotically controls the familywise error rate, more powerful than single-step methods and capturing joint dependence; studentisation advocated.", "Identifies which rules are significant, not only whether the best is.")
add("W2110065044", "journal article, theory", "n/a", "none", "false discovery rate control",
    "Proposes controlling the expected proportion of falsely rejected hypotheses, equivalent to FWER when all hypotheses are true and smaller otherwise.", "The BH procedure used in the pack; assumes independence or positive dependence.")
add("W3124863268", "journal article, theory", "n/a", "none", "deflated Sharpe ratio",
    "The DSR corrects for selection bias under multiple testing and for non-normal returns, to separate legitimate findings from statistical flukes.", "Formula coded in the pack's phase 2; check against the paper.")
add("W2732395805", "journal article, method", "n/a", "none", "combinatorially symmetric cross-validation",
    "Proposes estimating the probability of backtest overfitting (PBO) through CSCV and shows it gives accurate estimates; says hold-out tends to be unreliable for investment backtests.", "Not computed in the pack; compute it or do not claim it.")
add("W4211170237", "journal article, method + historical review", "US factor literature", "historical factor tests since 1967", "multiple-testing framework with historical cutoffs",
    "A new factor needs a t-statistic above 3.0; most claimed research findings in financial economics are likely false.", "Hurdle for new claims; here t-values are far below zero, not above.")
add("W3004991387", "journal article, method", "finance", "simulations", "evaluation of multiple-testing methods",
    "A guide to multiple-testing methods with simulation evidence on relative performance; a t-statistic of 2.0 is not enough when five variables are tried.", "Single source for the methods section.")
add("W2118989259", "journal article, empirical", "US mutual funds", "fund alphas", "false-discovery technique separating unskilled, zero-alpha and skilled funds",
    "75% of funds have zero alpha net of expenses; a significant share of skilled funds before 1996 but almost none by 2006.", "FDR applied in finance; analogous to 'luck among many'.")
add("W3125595766", "magazine/notice article (AMS Notices)", "n/a", "none", "backtest overfitting argument", "The abstract field holds only a quotation about vague theories and indefinite computation; no finding is available.", "Readable general introduction to overfitting.", MO)
add("W2100697778", "journal article, method", "n/a", "simulations", "SPA test using a covariance decomposition and a GLR test", "Proposes a new test for superior predictive ability of technical rules without data-snooping bias; the GLR test is reported to dominate (abstract truncated).", "Alternative SPA variant; low priority.")

json.dump(N, open(os.path.join(B, "data", "clean", "evidence_notes.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(N), "notes;", sum(n["read_status"] == AR for n in N), "abstract read")
