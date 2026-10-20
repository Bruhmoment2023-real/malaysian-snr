"""Phase-3 data layer: base series (5m), multi-TF bars, MCX synthetic proxy, cost models.
No OptionsAI data is used anywhere (not approved directly by Sean)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(r"D:/Malaysian-SNR"); D3 = ROOT / "phase3" / "data"; D1 = ROOT / "data"
sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead/code_copy")

TF_MIN = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
LADDERS = {"W-D-4H-1H": ("1w", "1d", "4h", "1h"), "D-4H-1H-15m": ("1d", "4h", "1h", "15m"), "4H-1H-15m-5m": ("4h", "1h", "15m", "5m")}

# per-side costs. m_* market entry, l_* limit (maker) entry, t* = TP exit (limit), s* = stop exit (taker+slip)
CRYPTO = dict(m_eabs=0.0, m_epct=0.0007, l_eabs=0.0, l_epct=0.0002, tabs=0.0, tpct=0.0002, sabs=0.0, spct=0.0007, carry=0.02)
XAU = dict(m_eabs=0.35, m_epct=0.0, l_eabs=0.30, l_epct=0.0, tabs=0.0, tpct=0.0, sabs=0.05, spct=0.0, carry=0.03)
XAG = dict(m_eabs=0.035, m_epct=0.0, l_eabs=0.030, l_epct=0.0, tabs=0.0, tpct=0.0, sabs=0.005, spct=0.0, carry=0.03)
# MCX GOLD futures, % of notional per side: exchange txn 0.0021% + GST/SEBI ~0.0005% + avg(CTT 0.01% sell, stamp 0.002% buy)=0.006%
# + brokerage ~0 (flat Rs20 on ~Rs1 crore lot) + slippage/spread 0.005%  -> ~0.0136%/side; stops +0.005% extra slippage.
MCX = dict(m_eabs=0.0, m_epct=0.000136, l_eabs=0.0, l_epct=0.000086, tabs=0.0, tpct=0.000086, sabs=0.0, spct=0.000186, carry=0.0)

ASSETS = {
    "BTCUSDT": dict(src="binance", cost=CRYPTO, shift_h=0.0, gaps=False),
    "ETHUSDT": dict(src="binance", cost=CRYPTO, shift_h=0.0, gaps=False),
    "SOLUSDT": dict(src="binance", cost=CRYPTO, shift_h=0.0, gaps=False),
    "XAUUSD": dict(src="histdata", cost=XAU, shift_h=2.0, gaps=False),
    "XAGUSD": dict(src="histdata", cost=XAG, shift_h=2.0, gaps=False),
    "MCXGOLD_SYN": dict(src="mcxsyn", cost=MCX, shift_h=-3.5, gaps=True),
}


def load_base(asset):
    """5-minute base OHLC (UTC index = bar start) with a 'volume' column (NaN if none)."""
    spec = ASSETS[asset]
    if spec["src"] == "binance":
        d = pd.read_parquet(D3 / f"{asset}_5m.parquet")
    elif spec["src"] == "histdata":
        m = pd.read_parquet(D3 / f"{asset}_m1.parquet")
        g = m.groupby(m.index.floor("5min"))
        d = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last()})
        d["volume"] = np.nan
    else:
        d = pd.read_parquet(D3 / "MCXGOLD_SYN_5m.parquet")
    return d[["open", "high", "low", "close", "volume"]]


def bars(base, tf, shift_h):
    """Aggregate 5m base into tf bars. Bucket boundaries shifted by shift_h hours (metals: FX day
    at 22:00 UTC; MCX: session start 03:30 UTC). 'end' = time the bar is closed."""
    sh = pd.Timedelta(hours=shift_h)
    t = base.index + sh
    if tf == "1w":
        key = (t.tz_localize(None).to_period("W-SUN").start_time).tz_localize("UTC")
    else:
        key = t.floor(f"{TF_MIN[tf]}min")
    g = base.assign(_k=key, _t=base.index).groupby("_k", sort=True)
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                        "volume": g.volume.sum(min_count=1), "start": g._t.first(), "end": g._t.last() + pd.Timedelta(minutes=5)})
    return out.set_index("start")


# ------------------------------------------------------------------ MCX synthetic proxy
def _wk(a, b):
    x = pd.concat([a.resample("W").last().pct_change().rename("a"), b.resample("W").last().pct_change().rename("b")], axis=1).dropna()
    x = x[x.b.abs() < 0.2]
    return x.corr().iloc[0, 1]


def build_mcx_proxy():
    """MCX GOLD (Rs per 10 g) proxy = XAUUSD x USDINR(prev day close) / 31.1035 x 10 x (1 + premium).
    premium = domestic premium over import parity, calibrated MONTHLY on the gold ETFs GOLDBEES/SETFGOLD
    (real NSE prices that embed import duty), used with a one-month lag (causal).
    Bars restricted to MCX hours Mon-Fri 03:30-18:00 UTC (09:00-23:30 IST)."""
    xau = load_base("XAUUSD")
    inr = pd.read_parquet(D3 / "yf_INR_X_1d.parquet")["Close"].dropna()
    inr.index = pd.to_datetime(inr.index).as_unit("ns").tz_localize("UTC")
    inr_prev = inr.shift(1)                       # use previous day's close (known before the day)
    inr_prev.index = inr_prev.index.as_unit("us")
    fx = inr_prev.reindex(xau.index.floor("1D"), method="ffill").to_numpy()
    parity = 10.0 / 31.1035 * fx                  # multiply by XAU price
    etf = pd.read_parquet(D3 / "yf_GOLDBEES_NS_1d.parquet")["Close"].dropna()
    etf.index = pd.to_datetime(etf.index).as_unit("ns").tz_localize("UTC")
    xd = xau.close.resample("1D").last().dropna()
    par_d = (xd * 10.0 / 31.1035 * inr.reindex(xd.index, method="ffill")).dropna()
    j = pd.concat([etf.rename("etf"), par_d.rename("par")], axis=1).dropna()
    # GOLDBEES units changed (split) -> work with the ratio and its monthly median; ETF/parity = k*(1+prem)
    ratio = (j.etf / j.par)
    mon = ratio.resample("ME").median()
    # yfinance GOLDBEES is split-adjusted, so the ratio is unit-consistent (checked: 0.00087-0.00106 over 2009-2026).
    # premium index normalised to 1.13 in Jan 2015 (10% basic duty + 3% GST-equivalent), lagged one month.
    scale = pd.Series(1.0, index=mon.index)
    prem = (mon / mon.loc["2015-01"].iloc[0] * 1.13).shift(1)
    prem.index = prem.index.as_unit("us")
    day = xau.index.floor("1D")
    prem_5m = prem.reindex(day, method="ffill").bfill().to_numpy()
    parity = np.asarray(parity, float)
    k = parity * prem_5m
    out = xau[["open", "high", "low", "close"]].mul(k, axis=0)
    out["volume"] = np.nan
    hm = out.index.hour * 60 + out.index.minute
    sess = (out.index.dayofweek < 5) & (hm >= 210) & (hm < 1080)
    out = out[sess].dropna(subset=["close"])
    out.to_parquet(D3 / "MCXGOLD_SYN_5m.parquet")
    # validation vs real ETF prices (daily returns, which are unit-free)
    syn_d = out.close.resample("1D").last().dropna()
    v = pd.concat([syn_d.pct_change().rename("syn"), etf.pct_change().rename("etf")], axis=1).dropna()
    v = v[(v.etf.abs() < 0.2)]                       # drop split days
    lvl = pd.concat([syn_d.rename("syn"), (etf * scale.reindex(etf.index, method="ffill")).rename("etf")], axis=1).dropna()
    rep = dict(rows_5m=len(out), start=str(out.index[0]), end=str(out.index[-1]),
               daily_return_corr=float(v.corr().iloc[0, 1]), daily_tracking_err_pct=float((v.syn - v.etf).std() * 100),
               weekly_return_corr=float(_wk(syn_d, etf)),
               premium_monthly_min=float(prem.min()), premium_monthly_max=float(prem.max()),
               level_ratio_cv=float((lvl.syn / lvl.etf).std() / (lvl.syn / lvl.etf).mean()))
    json.dump(rep, open(D3 / "qc_mcx_proxy.json", "w"), indent=1)
    return rep
