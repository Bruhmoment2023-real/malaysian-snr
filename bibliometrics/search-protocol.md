# Search protocol - 02-malaysian-snr

- Paper question: A multiple-testing-controlled test of a social-media support/resistance trading method (Malaysian SnR) in gold, silver and crypto
- Date of search and data pull: **2026-10-13**
- Years covered: 1960-2026; language: English (OpenAlex language field `en` or missing)
- Built by an AI agent (Claude) with the scripts in `python\` and `R\`; all numbers below are read from the run logs.

## 1. Databases

| Role | Database | Access | Note |
|---|---|---|---|
| Discovery | Crossref REST API | free, no key, `mailto` polite pool | relevance-ranked keyword search; top N per query |
| Discovery | Semantic Scholar Graph API (bulk search) | free, no key | boolean search on title/abstract; top N by citations per query |
| Discovery | ERIC API | free, no key | education topics only |
| Discovery | arXiv API | free, no key | preprints |
| Enrichment (authors, institutions, countries, topics, keywords, abstracts, references, citation counts, OA links) | **OpenAlex** single-record lookups (`/works/doi:...`, `/works/mag:...`, `/works/W...`) | free, no key | see limit 1 below |
| Forward citations for snowballing | OpenCitations Index API v2 | free, no key | DOI-to-DOI citations only |
| Cross-check | Crossref (per-DOI), Semantic Scholar (batch) | free, no key | citation counts and reference-list coverage compared in `tables\coverage_crosscheck.csv` |
| Not used | Scopus, Web of Science, Lens, Dimensions | need accounts | equivalent strings are in `scopus-queries.md` |
| Not usable | RePEc/IDEAS | its API needs a registered access code; the public search page returned no parseable result list to a script | economics working papers still enter via Crossref, Semantic Scholar and snowballing |

**Why OpenAlex was not the search engine.** Since 2026 OpenAlex charges keyless list/search calls against a small daily budget shared by everyone on the same IP address ($0.10/day). On the day of the pull that budget was already exhausted by other work on this network, and an API key needs an account (ruled out). Single-record lookups remain free and unlimited, so records were *discovered* in Crossref / Semantic Scholar / ERIC / arXiv and then *enriched* one by one from OpenAlex. Consequence: a work that is in OpenAlex but not found by any of the four discovery databases is missed, except where snowballing caught it.

## 2. Exact search strings

### a_technical_analysis: Technical analysis and trading-rule profitability

| database | query | hits in database | records retrieved | status |
|---|---|---|---|---|
| crossref | technical analysis trading rule profitability | 7023272.0 | 250 | ok |
| crossref | simple technical trading rules stochastic properties of returns | 3283711.0 | 250 | ok |
| crossref | profitability of technical analysis foreign exchange | 7465754.0 | 250 | ok |
| crossref | technical trading rules out-of-sample profitability transaction costs | 1488720.0 | 250 | ok |
| crossref | do technical trading rules work cryptocurrency | 3252362.0 | 250 | ok |
| crossref | trend following trading rules gold | 1025217.0 | 250 | ok |
| crossref | candlestick patterns profitability | 531082.0 | 250 | ok |
| crossref | retail traders technical analysis use performance | 10397085.0 | 250 | ok |
| crossref | moving average rules predictability stock returns | 527196.0 | 250 | ok |
| crossref | technical analysis survey profitability evidence | 8458342.0 | 250 | ok |
| crossref | trading range break rules returns | 529878.0 | 250 | ok |
| s2 | "technical analysis" \| "technical trading" \| "trading rules" + (profitability \| profitable \| predictive \| returns) | 4287.0 | 800 | ok |
| s2 | ("technical trading rules" \| "technical indicators") + (cryptocurrency \| bitcoin \| gold \| "foreign exchange" \| commodities) | 713.0 | 713 | ok |
| s2 | ("candlestick" \| "chart patterns" \| "moving average") + (profitability \| "trading strategy" \| "trading rule") | 1476.0 | 800 | ok |
| arxiv | all:"technical analysis" AND cat:q-fin.* | 76.0 | 76 | ok |
| arxiv | all:"trading rules" AND (cat:q-fin.TR OR cat:q-fin.ST) | 37.0 | 37 | ok |
| arxiv | all:"technical trading" AND cat:q-fin.* | 17.0 | 17 | ok |

### b_support_resistance: Support and resistance, price levels and order clustering

| database | query | hits in database | records retrieved | status |
|---|---|---|---|---|
| crossref | support and resistance levels technical analysis | 8602029.0 | 250 | ok |
| crossref | support for resistance technical analysis intraday exchange rates | 8651533.0 | 250 | ok |
| crossref | price barriers round numbers | 589017.0 | 250 | ok |
| crossref | support resistance levels empirical test stocks | 2794350.0 | 250 | ok |
| crossref | stop-loss orders price cascades currency markets | 1000881.0 | 250 | ok |
| crossref | technical analysis liquidity provision limit order book support resistance | 9538500.0 | 250 | ok |
| crossref | memory effects stock price dynamics technical trading bounces | 5380230.0 | 250 | ok |
| crossref | support and resistance prediction accuracy intraday | 2260355.0 | 250 | ok |
| crossref | smart money concepts trading rules evaluation | 3039454.0 | 250 | ok |
| crossref | order clustering at round numbers foreign exchange | 1438809.0 | 250 | ok |
| crossref | price clustering and support resistance levels | 2317714.0 | 250 | ok |
| s2 | ("support and resistance" \| "support resistance" \| "resistance level" \| "support level") + (price \| trading \| stock \| currency \| market) | 878.0 | 800 | ok |
| s2 | ("round numbers" \| "price barriers" \| "price clustering" \| "order clustering") + (stock \| currency \| exchange \| trading \| futures) | 361.0 | 361 | ok |
| s2 | ("smart money concepts" \| "order block" \| "fair value gap" \| "inner circle trader" \| "ICT") + (trading \| forex \| strategy) | 27903.0 | 800 | ok |
| arxiv | all:"support and resistance" AND cat:q-fin.* | 9.0 | 9 | ok |
| arxiv | all:"support and resistance" | 25.0 | 25 | ok |
| arxiv | all:"smart money" AND all:trading | 1.0 | 1 | ok |
| arxiv | all:"price levels" AND all:"technical analysis" | 0.0 | 0 | ok |

### c_multiple_testing: Data snooping, multiple testing and backtest overfitting in finance

| database | query | hits in database | records retrieved | status |
|---|---|---|---|---|
| crossref | data snooping technical trading rule performance bootstrap | 5478779.0 | 250 | ok |
| crossref | a reality check for data snooping | 2752323.0 | 250 | ok |
| crossref | test for superior predictive ability | 1128469.0 | 250 | ok |
| crossref | false discoveries technical trading rules transaction costs | 1095798.0 | 250 | ok |
| crossref | backtesting multiple testing Sharpe ratio haircut | 1611234.0 | 250 | ok |
| crossref | deflated Sharpe ratio selection bias backtest overfitting | 806274.0 | 250 | ok |
| crossref | probability of backtest overfitting | 174369.0 | 250 | ok |
| crossref | cross-section of expected returns multiple testing t-statistic hurdle | 2732207.0 | 250 | ok |
| crossref | stepwise multiple testing data snooping | 3813794.0 | 250 | ok |
| crossref | false discovery rate mutual fund performance | 3208432.0 | 250 | ok |
| crossref | pseudo-mathematics financial charlatanism | 1645752.0 | 250 | ok |
| crossref | evaluation of alternative multiple testing methods finance | 5494006.0 | 250 | ok |
| crossref | does academic research destroy stock return predictability | 10327708.0 | 250 | ok |
| s2 | ("data snooping" \| "data-snooping" \| "reality check" \| "superior predictive ability") + (trading \| technical \| strategy \| rules) | 982.0 | 800 | ok |
| s2 | ("backtest overfitting" \| "backtest" \| "deflated Sharpe" \| "multiple testing" \| "false discovery") + (finance \| trading \| strategy \| factors \| "asset pricing" \| Sharpe) | 14418.0 | 800 | ok |
| s2 | ("p-hacking" \| "data mining") + (finance \| "asset pricing" \| anomalies \| "trading strategies") | 5490.0 | 800 | ok |
| arxiv | all:"backtest overfitting" | 13.0 | 13 | ok |
| arxiv | all:"multiple testing" AND cat:q-fin.* | 11.0 | 11 | ok |
| arxiv | all:"deflated Sharpe" | 6.0 | 6 | ok |
| arxiv | all:"data snooping" AND cat:q-fin.* | 9.0 | 9 | ok |
| arxiv | all:"false discovery" AND cat:q-fin.* | 13.0 | 13 | ok |

Per-query retrieval caps: crossref = 250, s2 = 800, arxiv = 100. Crossref totals are large because its search is an OR-type relevance ranking; only the top-ranked records were taken. Raw responses for every query are in `data\raw\<database>\`.

### Seed papers (known key works, each verified to exist by a Crossref title match; they bypass the keyword rules)

| seed title | result |
|---|---|
| Support for Resistance: Technical Analysis and Intraday Exchange Rates | NOT MATCHED in Crossref |
| Evidence and behaviour of support and resistance levels in financial time series | NOT MATCHED in Crossref |
| Retail Trader's Ruin: An Anatomy of Popular Signal Failure | NOT MATCHED in Crossref |
| Data-Snooping, Technical Trading Rule Performance, and the Bootstrap | matched 10.1111/0022-1082.00163 |
| A Reality Check for Data Snooping | matched 10.1111/1468-0262.00152 |
| Simple Technical Trading Rules and the Stochastic Properties of Stock Returns | matched 10.1111/j.1540-6261.1992.tb04681.x |
| Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis | matched 10.1111/1540-6261.00588 |
| Technical Analysis and Liquidity Provision | matched 10.1093/rfs/hhg057 |
| Memory effects in stock price dynamics: evidences of technical trading | matched 10.1038/srep04487 |
| Technical trading revisited: false discoveries, persistence tests, and transaction costs | matched 10.2139/ssrn.1095202 |
| Technical trading: is it still beating the foreign exchange market? | matched 10.1016/j.jinteco.2016.03.012 |
| The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality | matched 10.3905/jpm.2014.40.5.094 |
| The Probability of Backtest Overfitting | matched 10.21314/jcf.2016.322 |
| Smart Money or Costly Folklore? A Systematic Evaluation of ICT/Smart-Money-Concepts Trading Rules in G10 FX | matched 10.2139/ssrn.7430998 |

Seed arXiv ids (from the PDFs the substance agent saved in the paper folder): 2607.20093, 2101.07410, 2103.02331

## 3. Inclusion and exclusion rules (applied identically to search hits and snowballed records)

A record is **included** if all of the following hold:
1. It resolves to an OpenAlex work record (by DOI, MAG id, or a Crossref title match of at least 93% similarity).
2. OpenAlex type is article, review, preprint, book chapter, book, dissertation, report or other (editorials, errata, paratext, datasets, peer reviews are dropped).
3. Publication year 1960-2026; language English or unrecorded.
4. It satisfies at least one sub-literature rule below: every `include` pattern must match in title + abstract, and every `title_must` pattern must match in the title.
5. Its title does not match the exclusion pattern.
6. Citation floor: records older than 3 years need at least 1 citation(s).

Book-series and proceedings trap: a record whose abstract is a series/proceedings blurb (detected by wording such as 'this volume constitutes the refereed proceedings', or the same abstract shared by 3+ records) is screened on its title alone; whole-volume records (titles starting 'Proceedings of', 'Front matter', etc.) are dropped.

The patterns are case-insensitive regular expressions (`\b` = word boundary, `\w*` = any word ending, `.{0,80}` = within 80 characters).

**a_technical_analysis - Technical analysis and trading-rule profitability**

- include (title+abstract): `(technical analysis|technical trading|technical (indicators?|rules?|signals?)|trading rules?|moving[- ]average|chart(ing)? patterns?|candlestick|filter rules?|trend[- ]following|momentum (strateg|trading)|channel breakout|trading range break|head and shoulders|retail (traders?|trading)|day[- ]trad\w+)`
- include (title+abstract): `\b(stock|equit\w*|financ\w*|trad(er|ers|ing|e)|invest\w*|market|portfolio|asset|currenc\w*|exchange rates?|foreign exchange|forex|\bfx\b|futures|commodit\w*|gold|bitcoin|crypto\w*|returns?|prices?|securit\w*|funds?)\b`
- title_must (title): `(technical|trading rules?|chart|moving average|candlestick|indicators?|trend|momentum|filter|breakout|profitab|retail|day[- ]trad|rule-based|pattern)`

**b_support_resistance - Support and resistance, price levels and order clustering**

- include (title+abstract): `(support and resistance|support[/-]resistance|support levels?|resistance levels?|price barriers?|round numbers?|price clustering|order clustering|clusters? of (stop|limit)|stop[- ]loss orders?|take[- ]profit orders?|supply and demand zones?|smart money|order blocks?|fair value gaps?|liquidity (sweep|grab|pool)s?|inner circle trader|\bict\b|quasimodo|price levels?|price (reversal|bounce)s?|limit order book depth)`
- include (title+abstract): `\b(stock|equit\w*|financ\w*|trad(er|ers|ing|e)|invest\w*|market|portfolio|asset|currenc\w*|exchange rates?|foreign exchange|forex|\bfx\b|futures|commodit\w*|gold|bitcoin|crypto\w*|returns?|prices?|securit\w*|funds?)\b`
- title_must (title): `(support|resistance|barrier|round|level|cluster|smart money|order block|stop[- ]loss|take[- ]profit|liquidity|orders?|reversal|bounce|price|ict\b|supply and demand|gap)`

**c_multiple_testing - Data snooping, multiple testing and backtest overfitting in finance**

- include (title+abstract): `(data[- ]snooping|data[- ]mining|multiple (hypothesis )?testing|multiple comparisons?|backtest\w*|back-test\w*|overfit\w*|false discover\w*|reality check|superior predictive ability|deflated sharpe|p-?hacking|selection bias|sharpe ratio haircut|stepwise (multiple )?test\w*|familywise|family-wise|probability of backtest|cross-section of expected returns|\bt-?(stat|hurdle)\w*)`
- include (title+abstract): `(trading rules?|trading strateg\w*|technical|anomal\w*|factors?|portfolio|asset pricing|investment strateg\w*|stock returns?|mutual funds?|fund managers?|alpha|sharpe|predictab\w*|backtest\w*|hedge funds?)`
- title_must (title): `(snooping|multiple|overfit|false discover|reality check|predictive ability|sharpe|p-?hack|backtest|back-test|haircut|factor|anomal|significan|testing|data[- ]mining|selection|luck|skill|trading rules?|technical|replicat|cross-section|hurdle|alpha)`

**Exclusion pattern (title):** `(antibiotic|antimicrob|drug[- ]resistan|insulin|cancer|tumou?r|electrical resistance|resistance (training|exercise)|exercise|clinical|patients?|bacteri|pathogen|\bplants?\b|\bsoil|social support|peer support|supply chain|deep learning|neural network|\blstm\b|transformer|reinforcement learning|random forest|support vector|genetic algorithm|deep q|covid|resistance to change|employee|consumer resistance|organi[sz]ational|\bhiv\b|vaccin)`

A record matching several rules is assigned to the first one in the order listed (its other matches are kept in `sublits_all`).

## 4. Snowballing (one round)

- Central papers: the 25 corpus records ranked highest on local citations + topical relevance + log(global citations) - listed in `data\clean\snowball_central_papers.csv`.
- Backward: every OpenAlex `referenced_works` entry of those papers not already in the corpus (684 candidates).
- Forward: citing DOIs from OpenCitations, up to 150 per central paper (2359 candidates). OpenCitations only knows DOI-to-DOI links, so citing preprints and books without DOIs are missed.
- All candidates were looked up in OpenAlex and screened with the rules in section 3: 41 backward and 309 forward records were added.

## 5. PRISMA-style counts

| stage | n |
|---|---|
| Records identified through database searching (all query hits) | 15697 |
|    of which from arxiv | 217 |
|    of which from crossref | 8750 |
|    of which from s2 | 6674 |
|    of which from seed | 56 |
| Duplicates removed (same DOI / id / title across queries and databases) | 3842 |
| Unique records screened on title (+ abstract where the database supplied one) | 11855 |
| Removed at title pre-screen (off-topic) | 8052 |
| Records looked up in OpenAlex | 3803 |
| Duplicates removed after OpenAlex matching (same work / same title) | 22 |
| Excluded at full screen: offtopic_fails_inclusion_rule | 1753 |
| Excluded at full screen: type_excluded | 337 |
| Excluded at full screen: no_openalex_record (no DOI / not indexed) | 182 |
| Excluded at full screen: uncited_older_record (citation floor) | 134 |
| Excluded at full screen: language_not_english | 23 |
| Excluded at full screen: paratext_or_container_record | 3 |
| Excluded at full screen: offtopic_exclusion_term_in_title | 2 |
| Included after search screening | 1347 |
| Snowball: central papers used | 25 |
| Snowball: backward-reference candidates | 684 |
| Snowball: forward-citation candidates (OpenCitations) | 2359 |
| Snowball: duplicates of corpus records | 55 |
| Snowball excluded: offtopic_fails_inclusion_rule | 1985 |
| Snowball excluded: no_openalex_record | 220 |
| Snowball excluded: type_excluded | 175 |
| Snowball excluded: offtopic_exclusion_term_in_title | 133 |
| Snowball excluded: uncited_older_record (citation floor) | 50 |
| Snowball excluded: language_not_english | 43 |
| Snowball excluded: year_out_of_range | 16 |
| Snowball excluded: paratext_or_container_record | 16 |
| Snowball: included (backward) | 41 |
| Snowball: included (forward) | 309 |
| Corpus before hand-screening | 1697 |
| Removed at hand-screening (see tables/hand_screen_removed.csv) | 337 |
| FINAL CORPUS | 1360 |
|    with abstract | 899 |
|    with DOI | 1244 |
|    with a reference list in OpenAlex | 1185 |
| Distinct cited references / resolved to metadata | 33158 / 7677 |

Figure: `figures\py_01_prisma_flow.png`.

## 6. Hand-screening

After rule screening and snowballing, the agent read the titles (with source and year) of the whole corpus and removed 337 records as off-topic or mis-matched; every removal and its reason is in `tables\hand_screen_removed.csv`. This is a single-screener pass by an AI agent on titles, not a two-person human screen; borderline records were kept.

Removal reasons:
- off-topic: non-finance field (Computer Science) and no finance term in title or abstract: 61
- off-topic: ICT = information and communication technology (acronym clash with 'ICT' trading method): 53
- off-topic: general data mining / anomaly detection / statistics, no finance or trading-rule term in title: 39
- off-topic: non-finance field (Engineering) and no finance term in title or abstract: 28
- off-topic: non-finance field (Medicine) and no finance term in title or abstract: 18
- off-topic: non-finance field (Biochemistry, Genetics and Molecular Biology) and no finance term in title or abstract: 18
- off-topic: non-finance field (Agricultural and Biological Sciences), no finance term in title: 17
- off-topic: non-finance field (Mathematics) and no finance term in title or abstract: 12
- off-topic: non-finance field (Biochemistry, Genetics and Molecular Biology), no finance term in title: 11
- off-topic: non-finance field (Engineering), no finance term in title: 10
- off-topic: non-finance field (Medicine), no finance term in title: 9
- off-topic: non-finance field (Social Sciences), no finance term in title: 9
- off-topic: non-finance field (Decision Sciences) and no finance term in title or abstract: 5
- off-topic: non-finance field (Environmental Science), no finance term in title: 5
- off-topic: non-finance field (Immunology and Microbiology), no finance term in title: 4
- off-topic: non-finance field (Energy), no finance term in title: 4
- off-topic: non-finance field (Earth and Planetary Sciences) and no finance term in title or abstract: 4
- off-topic: non-finance field (Chemistry) and no finance term in title or abstract: 3
- off-topic: non-finance field (Health Professions) and no finance term in title or abstract: 3
- off-topic: non-finance field (Environmental Science) and no finance term in title or abstract: 3
- off-topic: non-finance field (Social Sciences) and no finance term in title or abstract: 3
- off-topic: non-finance field (Psychology) and no finance term in title or abstract: 2
- off-topic: non-finance field (Neuroscience) and no finance term in title or abstract: 2
- off-topic: non-finance field (Health Professions), no finance term in title: 2
- off-topic: non-finance field (Energy) and no finance term in title or abstract: 2
- off-topic: agriculture / pests / tourism: 2
- off-topic: non-finance field (Veterinary), no finance term in title: 1
- off-topic: non-finance field (Chemistry), no finance term in title: 1
- off-topic: non-finance field (Immunology and Microbiology) and no finance term in title or abstract: 1
- off-topic: non-finance field (Dentistry) and no finance term in title or abstract: 1
- off-topic: non-finance field (Agricultural and Biological Sciences) and no finance term in title or abstract: 1
- off-topic: non-finance field (Dentistry), no finance term in title: 1
- off-topic: non-finance field (Earth and Planetary Sciences), no finance term in title: 1
- off-topic: non-finance field (Psychology), no finance term in title: 1

## 7. Coverage and cross-checks

| item | value |
|---|---|
| corpus records | 1360.0 |
| records with DOI | 1244.0 |
| found in Crossref (DOI lookup) | 1199.0 |
| found in Semantic Scholar (batch DOI lookup) | 1137.0 |
| Spearman corr. OpenAlex vs Crossref cited-by | 0.945 |
| Spearman corr. OpenAlex vs Semantic Scholar cited-by | 0.953 |
| median cited-by: OpenAlex | 11.0 |
| median cited-by: Crossref | 8.0 |
| median cited-by: Semantic Scholar | 13.0 |
| records with no reference list in OpenAlex | 175.0 |
|   of which Crossref holds a reference list | 5.0 |
| records with no institution/country data | 230.0 |
| records without abstract | 461.0 |
| open-access records (OpenAlex) | 691.0 |
| origin: search | 978.0 |
| origin: snowball_forward | 306.0 |
| origin: snowball_backward | 40.0 |
| origin: seed | 36.0 |
| retrieved by: s2 | 974.0 |
| retrieved by: openalex_snowball | 346.0 |
| retrieved by: arxiv | 38.0 |
| retrieved by: seed | 37.0 |
| retrieved by: crossref | 1.0 |


- 182 title-screened candidates could not be matched to any OpenAlex record (no DOI or MAG id, or not indexed) and are **not** in the corpus. They are listed in `data\clean\unresolved_candidates.csv` (s2: 175, seed: 3, arxiv: 3, crossref: 1). ERIC reports and theses and Indian or legal journal articles without DOIs dominate this list.

- Cited references: 33158 distinct works are cited by the corpus (63475 links); 7677 of the 22000 outside the corpus were resolved to metadata for the co-citation and RPYS analyses.


### Named prior work (seed list / the substance agent's saved papers) - is it in the corpus?

| id | kind | in_corpus | title |
|---|---|---|---|
| 10.1016/j.finmar.2013.05.006 | doi | 1 |  |
| 10.1016/j.jempfin.2010.01.001 | doi | 1 |  |
| 10.1016/j.jfineco.2012.06.001 | doi | 1 |  |
| 10.1016/j.jimonfin.2004.12.002 | doi | 1 |  |
| 10.1016/j.jinteco.2016.03.012 | doi | 1 |  |
| 10.1038/srep04487 | doi | 1 |  |
| 10.1080/01621459.1994.10476870 | doi | 0 |  |
| 10.1080/09603107.2012.663469 | doi | 1 |  |
| 10.1090/noti1105 | doi | 1 |  |
| 10.1093/rapstu/raaa003 | doi | 1 |  |
| 10.1093/rfs/hhg057 | doi | 1 |  |
| 10.1093/rfs/hhv059 | doi | 1 |  |
| 10.1111/0022-1082.00163 | doi | 1 |  |
| 10.1111/0022-1082.00265 | doi | 1 |  |
| 10.1111/1468-0262.00152 | doi | 1 |  |
| 10.1111/1540-6261.00588 | doi | 1 |  |
| 10.1111/j.1467-6419.2007.00519.x | doi | 1 |  |
| 10.1111/j.1468-0262.2005.00615.x | doi | 1 |  |
| 10.1111/j.1540-6261.1992.tb04681.x | doi | 1 |  |
| 10.1111/j.1540-6261.2009.01527.x | doi | 1 |  |
| 10.1111/j.2517-6161.1995.tb02031.x | doi | 1 |  |
| 10.1111/jofi.12365 | doi | 0 |  |
| 10.1198/073500105000000063 | doi | 0 |  |
| 10.1257/jel.45.4.936 | doi | 1 |  |
| 10.21314/jcf.2016.322 | doi | 1 |  |
| 10.2139/ssrn.3423101 | doi | 1 |  |
| 10.2139/ssrn.6725880 | doi | 1 |  |
| 10.2139/ssrn.7430758 | doi | 1 |  |
| 10.2139/ssrn.7430898 | doi | 0 |  |
| 10.2139/ssrn.7430998 | doi | 1 |  |
| 10.2139/ssrn.7431518 | doi | 1 |  |
| 10.2139/ssrn.7434881 | doi | 1 |  |
| 10.2139/ssrn.7434900 | doi | 1 |  |
| 10.2139/ssrn.7435081 | doi | 1 |  |
| 10.2139/ssrn.7435180 | doi | 1 |  |
| 10.2307/2331416 | doi | 1 |  |
| 10.3905/jpm.2014.40.5.094 | doi | 1 |  |
| 10.3905/jpm.2015.42.1.013 | doi | 1 |  |
| arXiv:1110.5197 | arxiv | 1 | Memory effects in stock price dynamics: evidences of technical trading |
| arXiv:2101.07410 | arxiv | 1 | Evidence and Behaviour of Support and Resistance Levels in Financial Time Series |
| arXiv:2103.02331 | arxiv | 1 | The support and resistance line method: an analysis via optimal stopping |
| arXiv:2607.20093 | arxiv | 1 | Retail Trader's Ruin: An Anatomy of Popular Signal Failure |

## 8. API failures during the run

- pmap: OperationalError('database is locked') (x12365)
- api.openalex.org: failed after retries: {"error":"Rate limit exceeded","message":"Rate l (x1682)


## 9. Scopus / Web of Science exports
- `scopus-drop\`: EMPTY - no Scopus/WoS export to merge; corpus is OpenAlex-only.
- Ready-to-paste strings: `scopus-queries.md`.
