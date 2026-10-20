"""Audit sensitivity: the stored Deflated Sharpe Ratio (phases 2-3) uses V = cross-sectional variance of per-trade Sharpe
across ALL configurations in a cell. Most configurations are strongly negative after costs, so V mostly measures how
different the rules are, not luck, and the hurdle becomes very high. Here the DSR is recomputed with the null sampling
variance of one Sharpe estimate, V = 1/(n-1), and with N = configurations in the cell and N = all configurations.
Same formula as phase2/p2_phaseA.py dsr(). READ-ONLY on D:/Malaysian-SNR.  Runtime about 1 min.
Run: D:\\Malaysian-SNR\\.venv\\Scripts\\python.exe -B D:\\Research-Publishing\\02-malaysian-snr\\code\\05_dsr_sensitivity.py
"""
import math, os
from pathlib import Path
from statistics import NormalDist
import numpy as np, pandas as pd

ND = NormalDist(); G = 0.5772156649
OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/rerun/results"); assert os.path.exists("D:/")


def dsr(sr, n, skew, kurt, N, V):
    if n < 10 or not np.isfinite(sr) or N < 2 or not np.isfinite(V) or V <= 0:
        return np.nan
    sr0 = math.sqrt(V) * ((1 - G) * ND.inv_cdf(1 - 1 / N) + G * ND.inv_cdf(1 - 1 / (N * math.e)))
    den = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    return ND.cdf((sr - sr0) * math.sqrt(n - 1) / math.sqrt(den)) if den > 0 else np.nan


rows = []
for name, f, cellcols in (("phase2", r"D:/Malaysian-SNR/phase2/results/all_configs_phaseA.csv", ["asset", "tf"]),
                          ("phase3", r"D:/Malaysian-SNR/phase3/results/msnr_all_configs.csv", ["asset", "ladder"])):
    a = pd.read_csv(f, low_memory=False, usecols=lambda c: c in {"asset", "tf", "ladder", "name", "wf_n", "wf_netR", "sr_trade", "skew", "kurt", "DSR", "hold_n", "hold_netR"})
    a = a[a.wf_n >= 100].copy()
    ncell = pd.read_csv(f, usecols=cellcols).groupby(cellcols).size().rename("N_cell").reset_index()
    a = a.merge(ncell, on=cellcols); Nall = int(ncell.N_cell.sum())
    a["DSR_null_Ncell"] = [dsr(s, n, sk, ku, N, 1 / (n - 1)) for s, n, sk, ku, N in zip(a.sr_trade, a.wf_n, a["skew"], a["kurt"], a.N_cell)]
    a["DSR_null_Nall"] = [dsr(s, n, sk, ku, Nall, 1 / (n - 1)) for s, n, sk, ku in zip(a.sr_trade, a.wf_n, a["skew"], a["kurt"])]
    top = a.sort_values("DSR_null_Ncell", ascending=False).head(15)
    top.to_csv(OUT / f"dsr_sensitivity_top15_{name}.csv", index=False)
    rows.append(dict(study=name, configs_total=Nall, configs_ge100_trades=len(a), stored_DSR_max=a.DSR.max(), stored_DSR_gt_095=int((a.DSR > 0.95).sum()),
                     nullvar_Ncell_max=a.DSR_null_Ncell.max(), nullvar_Ncell_gt_095=int((a.DSR_null_Ncell > 0.95).sum()),
                     nullvar_Nall_max=a.DSR_null_Nall.max(), nullvar_Nall_gt_095=int((a.DSR_null_Nall > 0.95).sum())))
    print(name); print(top[cellcols + ["name", "wf_n", "wf_netR", "DSR", "DSR_null_Ncell", "DSR_null_Nall", "hold_n", "hold_netR"]].to_string(index=False))
R = pd.DataFrame(rows); R.round(4).to_csv(OUT / "dsr_sensitivity_summary.csv", index=False); print(R.round(4).to_string(index=False))
