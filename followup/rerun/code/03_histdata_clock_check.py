"""Audit check: are the phase-3 metals timestamps (histdata M1, stored as 'UTC') true UTC?
Phase 3 was NOT part of the clock-fix reruns. This reads only the index + close of the stored M1 parquet.
Test: the weekly re-open happens at a fixed New York wall-clock time. If the stored label were true UTC the
weekly open would move by one hour between January and July; if the label is 'NY wall clock + 5h' it does not.
Also: what NY wall-clock hour does phase 3's daily cut (label 22:00) correspond to in each case.
Run (about 1 min): D:\\Malaysian-SNR\\.venv\\Scripts\\python.exe -B D:\\Research-Publishing\\02-malaysian-snr\\code\\03_histdata_clock_check.py
"""
import os
from pathlib import Path
import numpy as np, pandas as pd

assert os.path.exists("D:/"), "D: offline"
OUT = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/rerun/results")
rows = []
for sym in ("XAUUSD", "XAGUSD"):
    d = pd.read_parquet(rf"D:/Malaysian-SNR/phase3/data/{sym}_m1.parquet", columns=["close"])
    idx = d.index
    gap = idx.to_series().diff() > pd.Timedelta(hours=40)
    wk = idx[gap.to_numpy()]
    for name, months in (("Jan-Feb", (1, 2)), ("Jun-Jul", (6, 7))):
        w = wk[np.isin(wk.month, months) & (wk.year >= 2012)]
        lab = pd.Series(w.hour * 100 + w.minute).value_counts(normalize=True).head(3)
        as_utc_ny = w.tz_convert("America/New_York")
        true_ny = pd.Series(as_utc_ny.hour * 100 + as_utc_ny.minute).value_counts(normalize=True).head(2)
        rows.append(dict(symbol=sym, season=name, n_weekly_opens=len(w),
                         label_hhmm_top=" ".join(f"{int(k):04d}:{v:.2f}" for k, v in lab.items()),
                         NY_time_if_label_were_true_UTC=" ".join(f"{int(k):04d}:{v:.2f}" for k, v in true_ny.items())))
    print(sym, "done", flush=True)
R = pd.DataFrame(rows)
R.to_csv(OUT / "check_phase3_histdata_clock.csv", index=False)
pd.set_option("display.width", 220)
print(R.to_string(index=False))
print("""
Reading: if 'label_hhmm_top' is the SAME in winter and summer, the label follows New York wall clock (+5h), i.e. it is
NOT true UTC in summer (it is one hour late), and 'NY_time_if_label_were_true_UTC' will differ by one hour between seasons.
Phase 3 buckets metals days at label 22:00 = New York 17:00 wall clock in BOTH seasons under that reading, so the daily and
weekly bars are New-York-close bars all year (the usual FX convention); only fixed-UTC-hour logic (the 'sess' filter and the
MCX-proxy session window) is displaced by one hour during US daylight-saving time.""")
