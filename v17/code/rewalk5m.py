"""PLAN follow-up amendment (22:20 IST): re-walk crypto trades and B1 random entries on 5-minute bars. Usage: rewalk5m.py ASSET"""
import sys, ctypes
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core
try: ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception: pass


@njit(cache=True)
def walk5(t5, o, h, l, c, tent, E, S, T, d):
    n = len(c)
    i0 = np.searchsorted(t5, tent)
    if i0 >= n:
        return np.nan
    for k in range(i0, n):
        if d == 1:
            if l[k] <= S:
                X = min(S, o[k]) if k > i0 else S
                return X
            if h[k] >= T:
                return T
        else:
            if h[k] >= S:
                X = max(S, o[k]) if k > i0 else S
                return X
            if l[k] <= T:
                return T
    return c[n - 1]


@njit(cache=True)
def strat5(t5, o5, h5, l5, c5, tent, E, risk, d, tgt):
    out = np.empty(len(E))
    for i in range(len(E)):
        S = E[i] - d[i] * risk[i]; T = E[i] + d[i] * tgt[i] * risk[i]
        X = walk5(t5, o5, h5, l5, c5, tent[i], E[i], S, T, d[i])
        out[i] = d[i] * (X - E[i]) / risk[i]
    return out


@njit(cache=True)
def rand5(t5, o5, h5, l5, c5, tcoarse, o, a, story, elig, s_risk, s_tgt, use_story, plong, reps, seed):
    np.random.seed(seed)
    ntr = len(s_risk); out = np.full(reps, np.nan)
    for r in range(reps):
        tot = 0.0; cnt = 0; tries = 0
        while cnt < ntr and tries < ntr * 50:
            tries += 1
            q = np.random.randint(0, ntr)
            j = elig[np.random.randint(0, len(elig))]
            if use_story:
                d = story[j]
                if d == 0: continue
            else:
                d = 1 if np.random.random() < plong else -1
            risk = s_risk[q] * a[j]
            if risk <= 0: continue
            E = o[j + 1]; S = E - d * risk; T = E + d * s_tgt[q] * risk
            X = walk5(t5, o5, h5, l5, c5, tcoarse[j + 1], E, S, T, d)
            if np.isnan(X): continue
            tot += d * (X - E) / risk; cnt += 1
        if cnt > 0: out[r] = tot / cnt
    return out


asset = sys.argv[1]
d5 = pd.read_parquet(core.PQ / f"{asset}_5m.parquet"); d5 = d5[~d5.index.duplicated()].sort_index(); d5 = d5[d5.index < core.CUT_CRYPTO]
t5 = d5.index.asi8 if hasattr(d5.index, "asi8") else d5.index.view("int64")
unit = d5.index.unit if hasattr(d5.index, "unit") else "ns"
mult = {"ns": 1, "us": 1000, "ms": 10**6, "s": 10**9}[unit]
t5 = (t5 * mult).astype(np.int64)   # ns
o5, h5, l5, c5 = (d5[k].to_numpy(float) for k in ("open", "high", "low", "close"))
tr_all = pd.read_parquet(core.ROOT / f"results/cells/{asset}_new_trades.parquet"); tr_all = tr_all[tr_all.window == "FULL"]
cells = pd.read_csv(core.ROOT / f"results/cells/{asset}_new_cells.csv"); cells = cells[cells.window == "FULL"]
d1, sm, so, fx = core.load_series(asset)
rows, trows = [], []
seed0 = (sum(ord(ch) * (i + 1) for i, ch in enumerate(asset)) * 15485863) % 900000
for ti, tf in enumerate(core.TFS):
    cell = core.build_cell(asset, tf, d1, sm, so, fx)
    bars = cell["bars"]; tcoarse = (bars.index.asi8 * {"ns": 1, "us": 1000, "ms": 10**6, "s": 10**9}[bars.index.unit]).astype(np.int64)
    n = cell["n"]; valid = ~np.isnan(cell["a"]); m = np.zeros(n, bool); m[cell["first"]:n - 1] = True; m &= valid
    elig = np.where(m)[0].astype(np.int64)
    for vi, v in enumerate(core.VARIANTS):
        t = tr_all[(tr_all.tf == tf) & (tr_all.variant == v)]
        if len(t) == 0: continue
        sj = t.sig_j.to_numpy(int)
        g5 = strat5(t5, o5, h5, l5, c5, tcoarse[sj + 1], t.E.to_numpy(float), t.risk.to_numpy(float), t.dir.to_numpy(np.int64), t.tgtR.to_numpy(float))
        row = dict(asset=asset, tf=tf, variant=v, trades=len(t), gross_coarse=float(t.grossR.mean()), gross_5m=float(np.nanmean(g5)))
        if len(t) >= 5:
            use_story = cell["sigs"][v][3]
            res = rand5(t5, o5, h5, l5, c5, tcoarse, cell["o"], cell["a"], cell["story"], elig, t.risk_atr.to_numpy(float), t.tgtR.to_numpy(float), use_story, float((t.dir == 1).mean()), 100, seed0 + 100 * ti + vi)
            row["rand_5m"] = float(np.nanmean(res)); row["rand_5m_sd"] = float(np.nanstd(res, ddof=1))
        cr = cells[(cells.tf == tf) & (cells.variant == v)]
        if len(cr): row["rand_coarse_B1"] = float(cr.B1_mean.iloc[0])
        rows.append(row)
        trows.append(pd.DataFrame(dict(asset=asset, tf=tf, variant=v, sig_j=sj, gross_5m=g5, month=pd.to_datetime(t.sig_time).dt.strftime("%Y-%m").to_numpy())))
    print(asset, tf, flush=True)
pd.DataFrame(rows).to_csv(core.ROOT / f"results/cells/{asset}_5m_cells.csv", index=False)
pd.concat(trows).to_parquet(core.ROOT / f"results/cells/{asset}_5m_trades.parquet")
