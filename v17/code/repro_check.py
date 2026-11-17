"""Reproduction check (PLAN P1): frozen engine on the stored v16 Binance-API parquet files vs the stored v16 phase-1 results."""
import sys, glob
import numpy as np, pandas as pd
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core
R = core.ROOT / "results"
old = pd.read_csv(r"D:/Malaysian-SNR/results/key_table_default_OOS.csv")
old = old[old.asset.isin(["BTCUSDT", "ETHUSDT", "SOLUSDT"])]
cells = pd.concat([pd.read_csv(f) for f in glob.glob(str(R / "cells/*_legacy_cells.csv"))])
tr = pd.concat([pd.read_parquet(f) for f in glob.glob(str(R / "cells/*_legacy_trades.parquet"))])
tr["cost"] = (2 * 7 / 1e4 * tr.E) / tr.risk + 0.02 * tr.hold_h / 8760 * tr.E / tr.risk
tr["net"] = tr.grossR - tr.cost
n = tr[tr.window == "OOS"].groupby(["asset", "tf", "variant"]).agg(trades=("net", "size"), net=("net", "mean"), gross=("grossR", "mean")).reset_index()
m = old[["asset", "tf", "variant", "trades", "avg_R", "gross_avg_R"]].merge(n, on=["asset", "tf", "variant"], suffixes=("_v16", "_new"))
m["d_trades"] = m.trades_v16 - m.trades_new; m["d_net"] = m.avg_R - m.net; m["d_gross"] = m.gross_avg_R - m.gross
m.to_csv(R / "repro_check_phase1_legacy.csv", index=False)
print(len(m), "cells; max |d_trades| =", m.d_trades.abs().max(), "; max |d_gross| =", m.d_gross.abs().max(), "; max |d_net| =", m.d_net.abs().max())
