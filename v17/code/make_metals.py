"""Build 1h bid bars for XAUUSD/XAGUSD from the stored histdata.com M1 BID series (v16 phase-3 source, D:/Malaysian-SNR/phase3/data).
Index convention is kept exactly as in v16 phase 3 (shift_h = 2 in make_bars gives the New-York-17:00 trading day). Bid only (see paper)."""
import pandas as pd
for a in ("XAUUSD", "XAGUSD"):
    m = pd.read_parquet(rf"D:/Malaysian-SNR/phase3/data/{a}_m1.parquet")
    m = m[~m.index.duplicated()].sort_index()
    g = m.groupby(m.index.floor("1h"))
    h = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last()})
    h.to_parquet(rf"D:/Research-Publishing/02-malaysian-snr/rework-v3/data/parquet/{a}_hd_1h.parquet")
    print(a, len(h), h.index[0], h.index[-1])
