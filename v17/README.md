# Archive v17: Malaysian SnR test

Contents: code/ (frozen engine msnr_frozen.py, downloaders, runners, analysis, figures), PLAN_2026-11-17.md (time-stamped pre-specification and labelled amendments), results/ (CSV tables and logs), figures/ (600 dpi PNG and PDF), manifests/ (file names, byte sizes, SHA-256 and source URLs of every vendor file used), ENGINE_CHECKSUM.txt.

NOT included, on purpose: any vendor price data (Binance Vision klines, histdata.com bars, Dukascopy candles) and the trade-level files derived from them. Terms: Binance Vision (github.com/binance/binance-public-data TERMS_AND_CONDITIONS.md) allows academic research and personal back-testing and prohibits hosting or redistributing the datasets; no licence text was found for the Dukascopy feed and histdata.com data, so they are treated the same way.

Reproduction: (1) python code/dl_binance_vision.py 1h and 5m (checks sizes and checksums against manifests/binance_vision_zips_sha256.csv); (2) metals: download the histdata.com XAUUSD and XAGUSD M1 files listed in manifests/histdata_zips_sha256.csv, aggregate with the M1 loader of the earlier version, then code/make_metals.py; (3) code/run_batch.sh, run_metals.sh, run_b3.py per asset, rewalk5m.py per crypto asset; (4) code/final_run.sh. Paths in the scripts are the author's D: paths and must be edited. Seeds are fixed in code.
