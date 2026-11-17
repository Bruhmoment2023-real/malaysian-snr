"""PLAN P9: truncation (look-ahead) test of the frozen engine on the new-data series. For each asset, timeframe and cut (35/60/85% of the 1h series),
all per-bar quantities (storyline, five variant signals, ATR) computed on the truncated series must equal those of the full series on every bar
that is complete in the truncated set (all but its last bar)."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/rework-v3/code")
import core
assets = sys.argv[1:]
rows = []
for asset in assets:
    d1, sm, so, fx = core.load_series(asset)
    for tf in core.TFS:
        full = core.build_cell(asset, tf, d1, sm, so, fx)
        for frac in (0.35, 0.6, 0.85):
            cut = d1.index[int(len(d1) * frac)]
            k = d1.index < cut
            part = core.build_cell(asset, tf, d1[k], sm[k] if sm is not None else None, so[k] if so is not None else None, fx)
            nb = part["n"] - 1
            series = {"story": (full["story"], part["story"]), "atr": (np.nan_to_num(full["a"], nan=-1), np.nan_to_num(part["a"], nan=-1))}
            for v in core.VARIANTS:
                series[v] = (full["sigs"][v][0], part["sigs"][v][0])
                series[v + "_nres"] = (np.nan_to_num(full["sigs"][v][1], nan=-1), np.nan_to_num(part["sigs"][v][1], nan=-1))
            for nm, (a, b) in series.items():
                bad = int((np.abs(a[:nb].astype(float) - b[:nb].astype(float)) > 1e-9).sum())
                rows.append(dict(asset=asset, tf=tf, cut=frac, series=nm, bars=nb, mismatches=bad))
    print(asset, "done", flush=True)
R = pd.DataFrame(rows); R.to_csv(core.ROOT / "results" / "truncation_test_new_data.csv", index=False)
print("checks", len(R), "bars compared", int(R.bars.sum()), "mismatches", int(R.mismatches.sum()))
print(R[R.mismatches > 0].to_string(index=False))
