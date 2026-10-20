"""Shared phase-2 code: data, per-cell preparation, config construction and evaluation."""
import sys, math
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead/code_copy")
import msnr, engine2 as E2, indicators as IND

DATA = Path(r"D:/Malaysian-SNR/data")
HOLDOUT_DAYS = 365
WARMUP = 260
NFOLDS = 5

CRYPTO = dict(metals=False, m_eabs=0.0, m_epct=0.0007, l_eabs=0.0, l_epct=0.0002, tabs=0.0, tpct=0.0002,
              sabs=0.0, spct=0.0007, carry=0.02)
PAXG = dict(metals=False, m_eabs=0.0, m_epct=0.0015, l_eabs=0.0, l_epct=0.00075, tabs=0.0, tpct=0.00075,
            sabs=0.0, spct=0.0015, carry=0.02)
GOLD = dict(metals=True, m_eabs=0.35, m_epct=0.0, l_eabs=0.30, l_epct=0.0, tabs=0.0, tpct=0.0,
            sabs=0.05, spct=0.0, carry=0.03)
SILV = dict(metals=True, m_eabs=0.035, m_epct=0.0, l_eabs=0.030, l_epct=0.0, tabs=0.0, tpct=0.0,
            sabs=0.005, spct=0.0, carry=0.03)
ASSETS = {
    "BTCUSDT": dict(file="BTCUSDT_{res}.parquet", cost=CRYPTO, crypto=True, metal=None),
    "ETHUSDT": dict(file="ETHUSDT_{res}.parquet", cost=CRYPTO, crypto=True, metal=None),
    "SOLUSDT": dict(file="SOLUSDT_{res}.parquet", cost=CRYPTO, crypto=True, metal=None),
    "PAXGUSDT": dict(file="PAXGUSDT_1h.parquet", cost=PAXG, crypto=True, metal="gold", nofunding=True),
    "GC=F": dict(file="yf_GC_F_1h.parquet", cost=GOLD, crypto=False, metal="gold"),
    "SI=F": dict(file="yf_SI_F_1h.parquet", cost=SILV, crypto=False, metal="silver"),
    "GC=F_D2011": dict(file="yf_GC_F_1d_clean2011.parquet", cost=GOLD, crypto=False, metal="gold", daily=True),
}
CELLS = [(a, t) for a in ("BTCUSDT", "ETHUSDT", "SOLUSDT") for t in ("15m", "1h", "4h", "1d")] + \
        [("PAXGUSDT", t) for t in ("1h", "4h", "1d")] + \
        [("GC=F", "1h"), ("GC=F", "4h"), ("SI=F", "1h"), ("SI=F", "4h"), ("GC=F_D2011", "1d")]
HTF = {"15m": "1h", "1h": "4h", "4h": "1d", "1d": "1w"}
BAR_H = {"15m": 0.25, "1h": 1.0, "4h": 4.0, "1d": 24.0}

EXITS = [(0, 1.0, 0.0), (0, 2.0, 0.0), (0, 3.0, 0.0), (1, 1.0, 0.0), (2, 2.0, 1.0), (2, 3.0, 1.0),
         (3, 2.0, 0.0), (3, 3.0, 0.0), (4, 3.0, 0.0), (5, 2.0, 10.0), (5, 2.0, 20.0)]
DEFAULT_EXIT = (0, 2.0, 0.0)
STATE_FILTERS = {"ema200", "ema50x200", "adx_gt25", "adx_lt20", "donchian55", "rsi_35_65", "macd_turn",
                 "stoch_25_75", "atrpct_lo", "atrpct_hi", "bb_squeeze", "vwap_trend", "vwap_revert",
                 "session_ldn_ny", "funding_contra", "funding_trend", "dxy_weak", "realyield_falling", "gsr", "story"}


def xname(x):
    m, p1, p2 = x
    return {0: f"TP{p1:g}R", 1: f"nextlvl{p1:g}R", 2: f"BE{p2:g}R_TP{p1:g}R", 3: f"trail{p1:g}ATR",
            4: f"partial1R_TP{p1:g}R", 5: f"time{int(p2)}_TP{p1:g}R"}[m]


def load_src(asset, tf):
    spec = ASSETS[asset]
    res = "15m" if tf == "15m" else "1h"
    f = DATA / spec["file"].format(res=res)
    d = pd.read_parquet(f)
    d.columns = [x.lower() for x in d.columns]
    if "volume" not in d:
        d["volume"] = np.nan
    d = d[["open", "high", "low", "close", "volume"]].copy()
    if d.index.tz is None:
        d.index = d.index.tz_localize("UTC")
    d.index = d.index.tz_convert("UTC")
    d = d[~d.index.duplicated()].sort_index()
    base = pd.Timedelta(minutes=15) if res == "15m" else (pd.Timedelta(days=1) if spec.get("daily") else pd.Timedelta(hours=1))
    return d, base


def make_bars_v(df, tf, metals, base):
    shift = pd.Timedelta(hours=2) if metals else pd.Timedelta(0)
    t = df.index + shift
    if tf == "15m":
        key = t.floor("15min")
    elif tf == "1h":
        key = t.floor("1h")
    elif tf == "4h":
        key = t.floor("4h")
    elif tf == "1d":
        key = t.floor("1D")
    else:
        key = t.tz_localize(None).to_period("W-SUN").start_time.tz_localize("UTC")
    g = df.assign(_k=key, _t=df.index).groupby("_k", sort=True)
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                        "volume": g.volume.sum(min_count=1), "start": g._t.first(), "end": g._t.last() + base})
    return out.set_index("start")


def macro_extras(asset):
    spec = ASSETS[asset]; ex = {}
    if spec["crypto"] and not spec.get("nofunding"):
        f = pd.read_parquet(DATA / f"funding_{asset}.parquet").fundingRate
        ex["funding"] = f          # known at settlement time
    if spec["metal"]:
        lag = pd.Timedelta(days=2)
        dx = pd.read_parquet(DATA / "yf_DXY_1d.parquet")
        dx.columns = [x.lower() for x in dx.columns]
        cl = dx.close.dropna()
        sig = np.sign(cl.ewm(span=50, adjust=False).mean() - cl)
        sig.index = pd.to_datetime(sig.index).tz_localize("UTC") + lag
        ex["dxy"] = sig
        ry = pd.read_csv(DATA / "fred_DFII10.csv")
        ry.columns = ["date", "v"]; ry["v"] = pd.to_numeric(ry.v, errors="coerce"); ry = ry.dropna()
        s = pd.Series(ry.v.to_numpy(), index=pd.to_datetime(ry.date).dt.tz_localize("UTC") + lag)
        ex["ry"] = -np.sign(s.diff(20))
        g = pd.read_parquet(DATA / "yf_GC_F_1d.parquet").Close
        sv = pd.read_parquet(DATA / "yf_SI_F_1d.parquet").Close
        r = (g / sv).dropna(); r = r[r.index >= "2003-01-01"]
        z = (r - r.rolling(250).mean()) / r.rolling(250).std()
        zz = -np.sign(z) if spec["metal"] == "gold" else np.sign(z)
        zz.index = pd.to_datetime(zz.index).tz_localize("UTC") + lag
        ex["gsr"] = zz
    return ex


class Cell:
    """Everything needed to evaluate configs on one asset/timeframe, on data up to `cut`."""

    def __init__(self, asset, tf, phase="A"):
        self.asset, self.tf = asset, tf
        spec = ASSETS[asset]; self.cost = spec["cost"]
        src, base = load_src(asset, tf)
        self.hold_start = src.index[-1] - pd.Timedelta(days=HOLDOUT_DAYS)
        if phase == "A":
            src = src[src.index < self.hold_start]       # holdout data never loaded in phase A
        metals = spec["cost"]["metals"]
        bars = make_bars_v(src, tf, metals, base); hb = make_bars_v(src, HTF[tf], metals, base)
        self.bars = bars
        self.o, self.h, self.l, self.c = (bars[k].to_numpy() for k in ("open", "high", "low", "close"))
        self.a = msnr.atr(bars)
        self.n = len(bars)
        st = msnr.storyline(hb)
        hi = np.searchsorted(hb.end.to_numpy(), bars.end.to_numpy(), side="right") - 1
        self.story = np.where(hi >= 0, st[np.clip(hi, 0, None)], 0).astype(np.int64)
        o, h, l, c = self.o, self.h, self.l, self.c
        evR = msnr.map_events_to_bars(msnr.level_events(bars, include_qm=False, av_mode="raw"), bars)
        evP = msnr.map_events_to_bars(msnr.level_events(bars, include_qm=False), bars)
        self.ev = {"V0": (evR, 99), "V1": (evP, 1)}
        self.base = {}
        for b, (ev, mf) in self.ev.items():
            s0, _, l0, _, nr, ns = msnr.run_levels(o, h, l, c, ev[0], ev[1], ev[2], ev[3], mf)
            self.base[b] = (s0, l0, nr, ns)
        F, S, G, aux = IND.build(bars, asset, spec["crypto"], macro_extras(asset))
        if tf == "1d":
            F.pop("session_ldn_ny", None); G.pop("session_ldn_ny", None)
        F["story"] = (self.story == 1, self.story == -1)
        G["story"] = self.story.copy()
        self.F, self.S, self.G, self.aux = F, S, G, aux
        step = 10.0 ** (np.floor(np.log10(np.maximum(c, 1e-9))) - 1)
        self.levelF = {}
        for b in self.base:
            lv = self.base[b][1]
            lf = IND.level_filters(lv, c, aux["atr"], aux, step)
            bu, be = IND.fvg_contains(h, l, lv, 50)
            lf["fvg"] = (bu, be)
            self.levelF[b] = lf
        self.limit = {}
        first = WARMUP
        self.first = first
        self.edges = np.linspace(first, self.n, NFOLDS + 1).astype(int)
        self.bar_h = BAR_H[tf]
        self.end_days = ((bars.end - bars.end.iloc[0]).dt.total_seconds() // 86400).astype(int).to_numpy()

    # ------------------------------------------------------------------ filters
    def filt(self, base, names):
        n = self.n
        L = np.ones(n, bool); S = np.ones(n, bool)
        for f in names:
            if f in self.F:
                a, b = self.F[f]
            else:
                a, b = self.levelF[base][f]
            L &= np.asarray(a, bool); S &= np.asarray(b, bool)
        return L, S

    def limit_fills(self, base, eps):
        key = (base, eps)
        if key not in self.limit:
            ev, mf = self.ev[base]
            self.limit[key] = E2.run_levels_limit(self.o, self.h, self.l, self.c, self.a, ev[0], ev[1], ev[2], eps, mf)
        return self.limit[key]

    # ------------------------------------------------------------------ evaluate
    def trades(self, cfg, j_lo=None, j_hi=None):
        j_lo = self.first if j_lo is None else j_lo
        j_hi = self.n if j_hi is None else j_hi
        cs = self.cost; m, p1, p2 = cfg["exit"]
        o, h, l, c, a = self.o, self.h, self.l, self.c, self.a
        if cfg["kind"] == "mkt":
            s0, lv, nr, ns = self.base[cfg["base"]]
            Lk, Sk = self.filt(cfg["base"], cfg["filters"])
            sig = np.where((s0 == 1) & Lk, 1, np.where((s0 == -1) & Sk, -1, 0)).astype(np.int64)
            return E2.sim_market(o, h, l, c, a, sig, nr, ns, j_lo, j_hi, cfg.get("buf", 0.1), m, p1, p2,
                                 cs["m_eabs"], cs["m_epct"], cs["tabs"], cs["tpct"], cs["sabs"], cs["spct"], cs["carry"], self.bar_h)
        if cfg["kind"] == "alone":
            sig = np.asarray(self.S[cfg["trigger"]], dtype=np.int64)
            nr = self.base["V1"][2]; ns = self.base["V1"][3]
            return E2.sim_market(o, h, l, c, a, sig, nr, ns, j_lo, j_hi, cfg.get("buf", 0.1), m, p1, p2,
                                 cs["m_eabs"], cs["m_epct"], cs["tabs"], cs["tpct"], cs["sabs"], cs["spct"], cs["carry"], self.bar_h)
        if cfg["kind"] == "lim":
            fd, fp, fl, nr, ns = self.limit_fills(cfg["base"], cfg["eps"])
            Lk, Sk = self.filt(cfg["base"], cfg["filters"])
            Lk = np.roll(Lk, 1); Sk = np.roll(Sk, 1); Lk[0] = False; Sk[0] = False   # filters as of j-1
            return E2.sim_limit(o, h, l, c, a, fd, fp, fl, nr, ns, Lk, Sk, j_lo, j_hi, cfg["sl_atr"], m, p1, p2,
                                cs["l_eabs"], cs["l_epct"], cs["tabs"], cs["tpct"], cs["sabs"], cs["spct"], cs["carry"], self.bar_h)
        raise ValueError(cfg)

    def dir_mask(self, cfg):
        """Direction array for the config's own random baseline: random bars where the config's
        non-MSNR conditions hold (2 = both directions allowed -> coin flip)."""
        n = self.n
        if cfg["kind"] == "alone":
            g = self.G.get(cfg["trigger"])
            return (np.full(n, 2, np.int64) if g is None else g.astype(np.int64)), 1
        names = [f for f in cfg["filters"] if f in self.F]
        if not names:
            return np.full(n, 2, np.int64), 0
        L, S = self.filt(cfg["base"], names)
        if cfg["kind"] == "lim":
            L = np.roll(L, 1); S = np.roll(S, 1)
        return np.where(L & S, 2, np.where(L, 1, np.where(S, -1, 0))).astype(np.int64), 1

    def random(self, cfg, tr, j_lo, j_hi, reps=200, seed=1):
        if len(tr) < 5:
            return np.array([np.nan]), np.array([np.nan])
        cs = self.cost; m, p1, p2 = cfg["exit"]
        if len(tr) > 3000:
            reps = min(reps, 60)          # very large trade lists: fewer reps (mean is already tight)
        dirs, use = self.dir_mask(cfg)
        eabs, epct = (cs["l_eabs"], cs["l_epct"]) if cfg["kind"] == "lim" else (cs["m_eabs"], cs["m_epct"])
        return E2.random_baseline2(self.o, self.h, self.l, self.c, self.a, dirs, use, j_lo, j_hi, len(tr),
                                   tr[:, 9].copy(), tr[:, 10].copy(), m, p1, p2, eabs, epct, cs["tabs"], cs["tpct"],
                                   cs["sabs"], cs["spct"], cs["carry"], self.bar_h, reps, seed)


def cfg_name(cfg):
    if cfg["kind"] == "alone":
        return f"alone|{cfg['trigger']}|{xname(cfg['exit'])}"
    f = "+".join(cfg["filters"]) if cfg["filters"] else "-"
    s = f"{cfg['kind']}|{cfg['base']}|{f}|{xname(cfg['exit'])}"
    if cfg["kind"] == "lim":
        s += f"|eps{cfg['eps']:g}_sl{cfg['sl_atr']:g}"
    return s


def tstat_p(x):
    n = len(x)
    if n < 5:
        return np.nan, 1.0
    sd = x.std(ddof=1)
    if sd == 0:
        return np.nan, 1.0
    t = x.mean() / (sd / math.sqrt(n))
    return t, 0.5 * math.erfc(t / math.sqrt(2))


def equity_stats(tr, cell, risk=0.01, levcap=10.0):
    """CAGR / MaxDD / Sharpe of 1%-risk compounding on a trade list (marked at exits)."""
    if len(tr) == 0:
        return np.nan, np.nan, np.nan
    bars = cell.bars
    netR = tr[:, 7] - tr[:, 8]
    rf = np.abs(tr[:, 4] - tr[:, 5]) / tr[:, 4]
    sc = np.minimum(1.0, levcap * rf / risk)
    eq = np.cumprod(1 + risk * netR * sc)
    t_ex = bars.end.to_numpy()[tr[:, 2].astype(int)]
    t0 = bars.index[int(tr[0, 0])]
    s = pd.Series(eq, index=pd.DatetimeIndex(t_ex)).groupby(level=0).last()
    s = pd.concat([pd.Series([1.0], index=[t0]), s]).groupby(level=0).last()
    yrs = max((s.index[-1] - s.index[0]).days / 365.25, 0.25)
    daily = s.resample("1D").last().ffill()
    dr = daily.pct_change().dropna()
    sh = dr.mean() / dr.std() * math.sqrt(365) if dr.std() > 0 else np.nan
    cagr = s.iloc[-1] ** (1 / yrs) - 1 if s.iloc[-1] > 0 else -1.0
    return cagr, (s / s.cummax() - 1).min(), sh
