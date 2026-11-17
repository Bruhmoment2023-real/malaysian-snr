"""Pooled inference for the 5-minute re-walk of the new crypto trades (PLAN follow-up amendment). Same month-cluster bootstrap as analysis.py."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core
C = core.ROOT / "results" / "cells"
cells = pd.concat([pd.read_csv(f) for f in sorted(C.glob("*_5m_cells.csv"))], ignore_index=True)
tr = pd.concat([pd.read_parquet(f) for f in sorted(C.glob("*_5m_trades.parquet"))], ignore_index=True)
orig = pd.concat([pd.read_parquet(f) for f in sorted(C.glob("*_new_trades.parquet"))], ignore_index=True); orig = orig[(orig.window == "FULL") & orig.asset.isin(cells.asset.unique())]
tr = tr.merge(orig[["asset", "tf", "variant", "sig_j", "grossR"]], on=["asset", "tf", "variant", "sig_j"], how="left")
tr = tr.merge(cells[["asset", "tf", "variant", "rand_5m", "rand_coarse_B1"]], on=["asset", "tf", "variant"], how="left").dropna(subset=["rand_5m", "rand_coarse_B1", "gross_5m"])
tr["exc5"] = tr.gross_5m - tr.rand_5m; tr["excC"] = tr.grossR - tr.rand_coarse_B1
def boot(df, col, B=5000, seed=1):
    gm = df.groupby("month")[col].agg(["sum", "count"]); S = gm["sum"].to_numpy(); N = gm["count"].to_numpy(float)
    idx = np.random.default_rng(seed).integers(0, len(S), size=(B, len(S))); bs = S[idx].sum(1) / N[idx].sum(1)
    est = S.sum() / N.sum(); se = bs.std(ddof=1)
    return est, se, np.percentile(bs, 2.5), np.percentile(bs, 97.5)
tr["all"] = "all crypto"; tr["vt"] = tr.variant + "|" + tr.tf
rows = []
for name, col in (("all", "all"), ("variant", "variant"), ("variant_tf", "vt")):
    for k, g in tr.groupby(col):
        if len(g) < 200: continue
        e5, s5, l5, h5 = boot(g, "exc5"); eC, sC, lC, hC = boot(g, "excC", seed=2)
        d, sd, _, _ = boot(g.assign(dd=g.exc5 - g.excC), "dd", seed=3)
        rows.append(dict(grouping=name, group=k, trades=len(g), edge_coarse=eC, se_coarse=sC, lo_coarse=lC, hi_coarse=hC, edge_5m=e5, se_5m=s5, lo_5m=l5, hi_5m=h5,
                         change=e5 - eC, change_se=sd, gross_coarse=g.grossR.mean(), gross_5m=g.gross_5m.mean(), rand_coarse=g.rand_coarse_B1.mean(), rand_5m=g.rand_5m.mean()))
d = pd.DataFrame(rows); d.to_csv(core.ROOT / "results" / "intrabar5m_pooled_new.csv", index=False)
print(d.round(4).to_string())
