# Data dictionary - paper 02 (Malaysian SnR test)

Row counts: lines minus header, checked 2026-10-17. The study's raw inputs and run outputs live OUTSIDE this folder in `D:\Malaysian-SNR` (read-only for the pack; never modified here). Column meanings are taken from the pack's audit notes (`02-audit.md`), the script docstrings and column names; meanings inferred from names alone are marked (inferred). R = the stop distance risked per trade ("R multiple"); `netR`/`avg_R` are after costs, `grossR` before costs.

## A. Source data in `D:\Malaysian-SNR\data` and phase folders (not copied into this folder)
| File(s) | Source, access | Contents and known problems |
|---|---|---|
| `data\BTCUSDT_1h/15m`, `ETHUSDT_*`, `SOLUSDT_*` `.parquet` | Binance spot klines (public download), fetched 2026-10-05 per `fetch_log.txt` | OHLCV bars (timestamps UTC). Survivor coins only (BTC, ETH, SOL: no delisted coins), spot not perpetuals. |
| `data\PAXGUSDT_1h.parquet` | Binance | Gold-backed token hourly from 2020; trades 24/7, not the gold futures market. |
| `data\yf_GC_F_1d.parquet`, `yf_GC_F_1d_clean2011.parquet`, `yf_GC_F_1h.parquet`, `yf_SI_F_*` | Yahoo Finance (unofficial), 2026-10-05 | Gold and silver continuous futures. Unadjusted rollover; flat rows dropped in the "clean2011" file; hourly history only from 2024-05 (about 2.4 years); the audit flags this as a weakness. |
| `data\yf_DXY_1d.parquet`, `data\fred_DFII10.csv`, `funding_*.parquet` | Yahoo; FRED series DFII10 (10-year TIPS yield, columns `observation_date`, `DFII10`); Binance funding rates | Regime/filter inputs. |
| `phase3\data\*_5m.parquet`, `XAUUSD_m1`, `XAGUSD_m1` | Binance Vision zips; histdata.com M1 bid bars | Histdata timestamps are New York wall clock, not true UTC (pack audit F2, `results\check_phase3_histdata_clock.csv`). `MCXGOLD_SYN_5m.parquet` is a synthetic loose series that the audit says to exclude. Quality reports: `qc_*.json`. |
| `phase3\data\yf_GOLDBEES_*`, `yf_HDFCGOLD_*`, `yf_INR_X_*`, `yf_SETFGOLD_*` | Yahoo | Indian gold ETF / INR series for the synthetic MCX proxy (not part of the canonical result). |

## B. Run outputs the pack's scripts read (`D:\Malaysian-SNR\...`)
| File | Rows x selected columns | Meaning |
|---|---|---|
| `phase2\results\all_configs_phaseA.csv` | 116,708-config search (per the pack): about 60 columns incl. `asset, tf, name, tag, kind, base, nfilt, filters, exit, n0..n4, s0..g4` (trades, sharpe, gross per sub-period, inferred), `wf_n, wf_netR, wf_grossR, wf_win, wf_PF, wf_t, wf_p` (walk-forward results), `sr_trade, skew, kurt` (per-trade Sharpe and moments), `n_configs_cell, cell_p_RC, cell_p_SPA` (Reality Check and SPA p-values of the cell), `DSR` (Deflated Sharpe), `rand_netR, p_vs_random` (random-entry benchmark), `q_BH` (Benjamini-Hochberg q), `hold_*` (holdout results) | Phase 2: configuration search. Holdout year was viewed twice (audit F8). |
| `phase3\results\msnr_all_configs.csv` | columns `asset, ladder, name, depth, gaps, story, conf, stop, tgt, rb, liq, miss, sess, xf` (rule parameters), `wf_*`, `DSR`, `q_BH`, `hold_*`, `regime_*` | Phase 3: top-down MSNR variants. Session-filter variants carry a one-hour clock shift (audit F2). |
| `results\trades_default_full.csv`, `key_table_*.csv`, `pooled_by_tf_variant.csv`, `summary_all_runs.csv` | phase 1 trades and tables | Phase 1 canonical run (V0-V4 variants x asset x timeframe). The script docstring mentions a 56 MB and a 12 MB CSV read from the study folder; which files those are was not checked. |

## C. Files in this paper folder
| Path | Rows | Contents |
|---|---|---|
| `results\reproduction_check.csv` | 61 | `phase, item, reported, recomputed, source_file, note`: every headline number of phases 1-3 recomputed from stored files. |
| `results\check_phase1_full_cells_vs_trades.csv` | 95 | one row per phase-1 cell (asset, timeframe, variant): trades, win rate, `avg_R_rep` vs recomputed, PF, `gross_avg_R`, `avg_cost_R`, CAGR, MaxDD, Sharpe, buy-and-hold columns (`BH_*`), random benchmark (`rand_avg_R`, `p_vs_random`, `rand_gross_R`, `p_gross_vs_random`, `gross_edge_vs_random_R`). |
| `results\check_phase1_truncation_test.csv` | 216 | look-ahead test: `cut_frac` (where data are truncated), `series`, `bars_compared`, `mismatches` (all 0). |
| `results\check_phase3_histdata_clock.csv` | 4 | per symbol and season: number of weekly opens, the stored label of the weekly open, the New York time it would imply if the label were true UTC. |
| `results\dsr_sensitivity_*.csv` | 2 / 15 / 15 | Deflated Sharpe recomputed with null variance `V = 1/(n-1)` and N = configurations in cell or all. |
| `results\robustness_R1_intrabar_by_cell.csv`, `..._pooled.csv` | 120 / 41 | stop-first resolution on coarse bars vs 5-minute bars; strategy minus random gross R (`edge_coarse`, `edge_5m`, z). |
| `results\table1a..table7*.csv`, `fig4_stats.csv` | 1-95 | paper tables: data inventory, pooled by timeframe and variant, OOS cells, multiple-testing summary (`configs, p_lt_05, expected_p_lt_05, bh_q_lt_10, max_DSR, min_RC_p, min_SPA_p`), ablations, cost assumptions as coded (`entry_cost, exit_cost, carry_per_year, source`). |
| `results\*.parquet` | compact config tables and tidy canonical trades (0.3 - 3.5 MB) | derived from the phase outputs for the scripts. |
| `followup\` | many | follow-up agents' notes, raw fetched pages (`raw\novelty`), teaching-source snapshots (`sources\snapshots`; copyrighted third-party pages: do not redistribute), clock-fix reruns (`rerun\`), look-ahead logs (`lookahead\`). Not opened column by column in this pass. |

## D. Literature map (`bibliometrics\`)
See `bibliometrics\README.md`; main table `bibliometrics\data\clean\master.csv` (one row per corpus record; columns as in the kit: `oa_id, doi, title, year, authors, countries, cited_by_count, local_citations, n_refs, sublit, origin, relevance, abstract, ...`), edges in `citation_edges.csv`, cited references in `cited_references.csv`. Known problems: OpenAlex under-indexes SSRN working papers; the acronym "ICT" matches information-technology papers (removed by the hand screen, `tables\hand_screen_removed.csv`).
