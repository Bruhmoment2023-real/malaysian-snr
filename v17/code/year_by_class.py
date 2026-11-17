"""Post hoc descriptive: edge over regime-matched random by signal year, separately for crypto and metals (all variants pooled, B1). Uses the same trade-level excess as analysis.py section F3."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core
from scipy import stats
RES = core.ROOT / "results"; CELLS = RES / "cells"
tr = pd.concat([pd.read_parquet(f) for f in sorted(CELLS.glob("*_new_trades.parquet"))], ignore_index=True)
tr = tr[tr.window == "FULL"]
rg = pd.concat([pd.read_csv(f) for f in sorted(CELLS.glob("*_new_regime.csv"))], ignore_index=True)
bm = rg[rg.scheme == "year"][["asset", "tf", "variant", "bucket", "B1_mean"]].rename(columns={"B1_mean": "rm"})
tt = tr.assign(bucket=tr.year).merge(bm, on=["asset", "tf", "variant", "bucket"], how="left").dropna(subset=["rm"])
tt["exc"] = tt.grossR - tt.rm; tt["cls"] = tt.asset.map(core.ASSET_CLASS); tt["month"] = pd.to_datetime(tt.sig_time).dt.strftime("%Y-%m")
rows = []
def boot(df, B=2000, seed=3):
    gm = df.groupby("month").exc.agg(["sum", "count"]); S = gm["sum"].to_numpy(); N = gm["count"].to_numpy(float)
    idx = np.random.default_rng(seed).integers(0, len(S), size=(B, len(S))); bs = S[idx].sum(1) / N[idx].sum(1)
    return S.sum() / N.sum(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)
for (cl, y), g in tt.groupby(["cls", "bucket"]):
    if len(g) < 500: continue
    e, lo, hi = boot(g); rows.append(dict(cls=cl, year=int(y), trades=len(g), edge=e, lo=lo, hi=hi))
d = pd.DataFrame(rows); d.to_csv(RES / "regimes_year_by_class_new.csv", index=False)
print(d.round(3).to_string())
for cl, g in d.groupby("cls"):
    a = g[g.year.between(2018, 2020)]; b = g[g.year >= 2024]
    if len(a) and len(b): print(cl, "2018-2020 weighted", round(np.average(a.edge, weights=a.trades), 3), "2024+ weighted", round(np.average(b.edge, weights=b.trades), 3))
