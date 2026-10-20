# Scopus and Web of Science queries - paper 02 (Malaysian SnR: multiple-testing-controlled test of a support/resistance method)

Status: **not run.** There is no Scopus or Web of Science login on this machine. `scopus-drop\` was empty on 2026-10-13.
The strings mirror the three sub-literatures in `search-protocol.md`; Scopus has no field for the retail "Malaysian SnR" teaching vocabulary, so sub-literature B includes the retail terms (smart money, order block) that only the 2026 working papers use.

How to use
- Scopus: Advanced document search -> paste -> Search -> Export -> **CSV**; tick *Citation information, Bibliographical information, Abstract & keywords, Include references* (with references the cap is 2,000 records per file: export in year slices).
- Web of Science: Advanced Search (Core Collection) -> paste -> Export -> **BibTeX** or *Plain text file*, Record Content = **Full Record and Cited References** (500 per file).
- Save each export into `bibliometrics\scopus-drop\`; the R script merges whatever is there with `bibliometrix::convert2df()` + `mergeDbSources()`.
- Record the date, database and number of hits under each query.

## A. Technical analysis and trading-rule profitability

Scopus
```
TITLE-ABS-KEY ( ( "technical analysis" OR "technical trading" OR "technical indicator*" OR "technical rule*" OR "trading rule*" OR "moving average*" OR "chart pattern*" OR candlestick*
    OR "filter rule*" OR "trend following" OR "trend-following" OR "momentum strateg*" OR "channel breakout" OR "trading range break*" OR "retail trader*" OR "day trad*" )
  AND ( profitab* OR "excess return*" OR "predictive" OR predictab* OR "out-of-sample" OR "transaction cost*" OR "abnormal return*" )
  AND ( stock* OR equit* OR "foreign exchange" OR currenc* OR forex OR futures OR commodit* OR gold OR bitcoin OR crypto* ) )
AND NOT TITLE ( "deep learning" OR "neural network*" OR lstm OR "reinforcement learning" OR "random forest" OR "support vector" OR "genetic algorithm" OR transformer )
AND PUBYEAR > 1959 AND LANGUAGE ( english )
AND ( LIMIT-TO ( SUBJAREA , "ECON" ) OR LIMIT-TO ( SUBJAREA , "BUSI" ) OR LIMIT-TO ( SUBJAREA , "MATH" ) OR LIMIT-TO ( SUBJAREA , "DECI" ) )
```
Web of Science
```
TS=(("technical analysis" OR "technical trading" OR "technical indicator*" OR "technical rule*" OR "trading rule*" OR "moving average*" OR "chart pattern*" OR candlestick*
    OR "filter rule*" OR "trend following" OR "trend-following" OR "momentum strateg*" OR "channel breakout" OR "trading range break*" OR "retail trader*" OR "day trad*")
  AND (profitab* OR "excess return*" OR predictive OR predictab* OR "out-of-sample" OR "transaction cost*" OR "abnormal return*")
  AND (stock* OR equit* OR "foreign exchange" OR currenc* OR forex OR futures OR commodit* OR gold OR bitcoin OR crypto*))
NOT TI=("deep learning" OR "neural network*" OR lstm OR "reinforcement learning" OR "random forest" OR "support vector" OR "genetic algorithm" OR transformer)
AND PY=(1960-2026) AND LA=(English)
```
Refine by Web of Science Categories: Business, Finance; Economics; Mathematics, Interdisciplinary Applications.

## B. Support and resistance, price levels, order clustering

Scopus
```
TITLE-ABS-KEY ( ( "support and resistance" OR "support/resistance" OR "support level*" OR "resistance level*" OR "price barrier*" OR "round number*" OR "price clustering" OR "order clustering"
    OR "stop-loss order*" OR "take-profit order*" OR "supply and demand zone*" OR "smart money" OR "order block*" OR "fair value gap*" OR "liquidity sweep*" OR "inner circle trader" OR quasimodo )
  AND ( stock* OR equit* OR "foreign exchange" OR currenc* OR forex OR futures OR commodit* OR gold OR bitcoin OR crypto* OR trading OR trader* OR price* ) )
AND NOT TITLE ( antibiotic* OR antimicrob* OR "drug resistan*" OR cancer OR tumo* OR "resistance training" OR clinical OR patient* OR "social support" OR "peer support" OR "supply chain" )
AND PUBYEAR > 1959 AND LANGUAGE ( english )
AND ( LIMIT-TO ( SUBJAREA , "ECON" ) OR LIMIT-TO ( SUBJAREA , "BUSI" ) OR LIMIT-TO ( SUBJAREA , "MATH" ) OR LIMIT-TO ( SUBJAREA , "PHYS" ) OR LIMIT-TO ( SUBJAREA , "COMP" ) )
```
Web of Science
```
TS=(("support and resistance" OR "support/resistance" OR "support level*" OR "resistance level*" OR "price barrier*" OR "round number*" OR "price clustering" OR "order clustering"
    OR "stop-loss order*" OR "take-profit order*" OR "supply and demand zone*" OR "smart money" OR "order block*" OR "fair value gap*" OR "liquidity sweep*" OR "inner circle trader" OR quasimodo)
  AND (stock* OR equit* OR "foreign exchange" OR currenc* OR forex OR futures OR commodit* OR gold OR bitcoin OR crypto* OR trading OR trader* OR price*))
NOT TI=(antibiotic* OR antimicrob* OR "drug resistan*" OR cancer OR tumo* OR "resistance training" OR clinical OR patient* OR "social support" OR "peer support" OR "supply chain")
AND PY=(1960-2026) AND LA=(English)
```

## C. Data snooping, multiple testing and backtest overfitting in finance

Scopus
```
TITLE-ABS-KEY ( ( "data snooping" OR "data-snooping" OR "data mining" OR "multiple testing" OR "multiple hypothesis testing" OR "multiple comparison*" OR backtest* OR overfit* OR "false discover*"
    OR "reality check" OR "superior predictive ability" OR "deflated Sharpe" OR "p-hacking" OR "selection bias" OR "Sharpe ratio haircut*" OR "stepwise test*" OR familywise OR "family-wise" )
  AND ( "trading rule*" OR "trading strateg*" OR "technical analysis" OR anomal* OR "asset pricing" OR "stock return*" OR "mutual fund*" OR "hedge fund*" OR portfolio OR alpha OR Sharpe OR "investment strateg*" ) )
AND NOT TITLE ( "deep learning" OR "neural network*" OR lstm OR "reinforcement learning" OR medical OR genom* OR clinical )
AND PUBYEAR > 1959 AND LANGUAGE ( english )
AND ( LIMIT-TO ( SUBJAREA , "ECON" ) OR LIMIT-TO ( SUBJAREA , "BUSI" ) OR LIMIT-TO ( SUBJAREA , "MATH" ) OR LIMIT-TO ( SUBJAREA , "DECI" ) )
```
Web of Science
```
TS=(("data snooping" OR "data-snooping" OR "data mining" OR "multiple testing" OR "multiple hypothesis testing" OR "multiple comparison*" OR backtest* OR overfit* OR "false discover*"
    OR "reality check" OR "superior predictive ability" OR "deflated Sharpe" OR "p-hacking" OR "selection bias" OR "Sharpe ratio haircut*" OR "stepwise test*" OR familywise OR "family-wise")
  AND ("trading rule*" OR "trading strateg*" OR "technical analysis" OR anomal* OR "asset pricing" OR "stock return*" OR "mutual fund*" OR "hedge fund*" OR portfolio OR alpha OR Sharpe OR "investment strateg*"))
NOT TI=("deep learning" OR "neural network*" OR lstm OR "reinforcement learning" OR medical OR genom* OR clinical)
AND PY=(1960-2026) AND LA=(English)
```
Refine by Web of Science Categories: Business, Finance; Economics; Statistics & Probability; Mathematics, Interdisciplinary Applications.

## D. Seed check (should all be returned by the combined searches)
Osler (2000) "Support for resistance"; Brock, Lakonishok, LeBaron (1992); Sullivan, Timmermann, White (1999); White (2000) "A reality check for data snooping"; Hansen (2005) SPA test; Bajgrowicz and Scaillet (2012);
Bailey and Lopez de Prado (2014) Deflated Sharpe Ratio; Harvey, Liu, Zhu (2016); Chung and Bellotti (2021); Darmanin (2026, arXiv); Mahadzva (2026, SSRN). The 2026 SSRN papers are not in Scopus; add them from `01-prior-work.md`.
