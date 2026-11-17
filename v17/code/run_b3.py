"""Post-hoc benchmark B3 (candle without level), see PLAN amendments. Usage: run_b3.py ASSET. Reads results/cells/<asset>_new_trades.parquet (FULL window),
writes results/cells/<asset>_b3.csv."""
import sys, ctypes
import numpy as np, pandas as pd
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core
try: ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception: pass
asset = sys.argv[1]
tr_all = pd.read_parquet(core.ROOT / f"results/cells/{asset}_new_trades.parquet")
d1, sm, so, fx = core.load_series(asset)
rows = []
seed0 = (sum(ord(ch) * (i + 1) for i, ch in enumerate(asset)) * 104729) % 900000
for ti, tf in enumerate(core.TFS):
    cell = core.build_cell(asset, tf, d1, sm, so, fx)
    o, h, l, c, a = cell["o"], cell["h"], cell["l"], cell["c"], cell["a"]
    n = cell["n"]
    okS = np.zeros(n, bool); okL = np.zeros(n, bool)
    okS[1:] = (h[1:] > h[:-1]) & (c[1:] < h[:-1])
    okL[1:] = (l[1:] < l[:-1]) & (c[1:] > l[:-1])
    valid = ~np.isnan(a); valid[n - 1] = False
    first, nn = cell["first"], n
    for vi, v in enumerate(core.VARIANTS):
        t = tr_all[(tr_all.tf == tf) & (tr_all.variant == v) & (tr_all.window == "FULL")]
        if len(t) < 5: continue
        use_story = cell["sigs"][v][3]
        mL = okL & valid; mS = okS & valid
        mL[:first] = False; mS[:first] = False
        eL = np.where(mL)[0].astype(np.int64); eS = np.where(mS)[0].astype(np.int64)
        plong = float((t.dir == 1).mean())
        res = core.rand_bench_dir(o, h, l, c, a, cell["story"], eL, eS, mL, mS, t.risk_atr.to_numpy(float), t.tgtR.to_numpy(float), use_story, plong, 500, seed0 + 100 * ti + vi)
        ok = res[~np.isnan(res)]; g = float(t.grossR.mean())
        ge = (np.sum(ok >= g) + 1) / (len(ok) + 1); le = (np.sum(ok <= g) + 1) / (len(ok) + 1)
        rows.append(dict(asset=asset, tf=tf, variant=v, trades=len(t), gross=g, B3_mean=float(ok.mean()), B3_sd=float(ok.std(ddof=1)), B3_p_two=float(min(1, 2 * min(ge, le))),
                         B3_z=float((g - ok.mean()) / ok.std(ddof=1))))
    print(asset, tf, flush=True)
pd.DataFrame(rows).to_csv(core.ROOT / f"results/cells/{asset}_b3.csv", index=False)
