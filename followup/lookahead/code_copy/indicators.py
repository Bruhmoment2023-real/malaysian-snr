"""Confluence filters and standalone triggers. Every array value at index j uses only data up
to and including bar j's close (macro series lagged >= 1 extra day). Returns dicts of:
  filters[name]    = (ok_long bool[n], ok_short bool[n])   evaluated at bar j
  needs_level      = set of filter names that test the MSNR level price (computed in runner)
  standalone[name] = sig int[n]  (+1/-1/0) event trigger for the confluence ALONE
  regimes[name]    = dir int[n]  (+1/-1 allowed direction, 2 = both, 0 = none) for
                     'random entry inside the regime' baselines
"""
import numpy as np
import pandas as pd
from numba import njit


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()


def adx(h, l, c, n=14):
    up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr_ = pd.Series(tr).ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=1 / n, adjust=False).mean() / atr_
    mdi = 100 * pd.Series(mdm).ewm(alpha=1 / n, adjust=False).mean() / atr_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean().fillna(0).to_numpy()


@njit(cache=True)
def pct_rank(x, w):
    n = len(x); out = np.full(n, np.nan)
    for j in range(w, n):
        if np.isnan(x[j]):
            continue
        cnt = 0; tot = 0
        for k in range(j - w, j):
            if not np.isnan(x[k]):
                tot += 1
                if x[k] < x[j]:
                    cnt += 1
        if tot > 0:
            out[j] = cnt / tot
    return out


@njit(cache=True)
def rolling_poc(h, l, c, v, w, nb):
    n = len(c); out = np.full(n, np.nan)
    hist = np.zeros(nb)
    for j in range(w, n):
        lo = np.inf; hi = -np.inf
        for k in range(j - w + 1, j + 1):
            lo = min(lo, l[k]); hi = max(hi, h[k])
        if hi <= lo:
            continue
        hist[:] = 0.0
        bw = (hi - lo) / nb
        for k in range(j - w + 1, j + 1):
            tp = (h[k] + l[k] + c[k]) / 3.0
            b = int((tp - lo) / bw)
            if b >= nb:
                b = nb - 1
            hist[b] += v[k]
        out[j] = lo + (np.argmax(hist) + 0.5) * bw
    return out


@njit(cache=True)
def hl_pivots(h, l, d):
    """Confirmed swing highs/lows on wicks (depth d). Returns last swing high/low known at each
    bar (value and bar index), using only pivots confirmed by bar j (p + d <= j)."""
    n = len(h)
    sh = np.full(n, np.nan); sl = np.full(n, np.nan); shi = np.full(n, -1); sli = np.full(n, -1)
    cur_h = np.nan; cur_l = np.nan; ch_i = -1; cl_i = -1
    for j in range(n):
        p = j - d
        if p >= d:
            ish = True; isl = True
            for k in range(p - d, p + d + 1):
                if k == p:
                    continue
                if h[k] >= h[p]:
                    ish = False
                if l[k] <= l[p]:
                    isl = False
            if ish:
                cur_h = h[p]; ch_i = p
            if isl:
                cur_l = l[p]; cl_i = p
        sh[j] = cur_h; sl[j] = cur_l; shi[j] = ch_i; sli[j] = cl_i
    return sh, sl, shi, sli


@njit(cache=True)
def fvg_contains(h, l, lvl, lookback):
    """For each bar j: does an unmitigated bullish (bearish) FVG formed in the last `lookback`
    bars (complete by bar j-1) contain lvl[j]?  Bullish FVG at i: l[i] > h[i-2], zone [h[i-2], l[i]].
    Mitigated (dead) once a later low goes below the zone bottom (bear: high above top)."""
    n = len(h); bull = np.zeros(n, np.bool_); bear = np.zeros(n, np.bool_)
    for j in range(3, n):
        if np.isnan(lvl[j]):
            continue
        L = lvl[j]
        for i in range(max(2, j - lookback), j):
            if l[i] > h[i - 2]:
                bot = h[i - 2]; top = l[i]
                if bot <= L <= top:
                    dead = False
                    for k in range(i + 1, j):
                        if l[k] < bot:
                            dead = True; break
                    if not dead:
                        bull[j] = True
            if h[i] < l[i - 2]:
                bot = h[i]; top = l[i - 2]
                if bot <= L <= top:
                    dead = False
                    for k in range(i + 1, j):
                        if h[k] > top:
                            dead = True; break
                    if not dead:
                        bear[j] = True
    return bull, bear


@njit(cache=True)
def rsi_div(c, r, d):
    """Bullish divergence at bar j: current close-pivot low candidate (bar j is the lowest close of
    the last d+1 bars) lower than the previous confirmed close-pivot low while RSI is higher."""
    n = len(c); bull = np.zeros(n, np.bool_); bear = np.zeros(n, np.bool_)
    pl = np.nan; plr = np.nan; ph = np.nan; phr = np.nan
    for j in range(n):
        p = j - d
        if p >= d:
            islo = True; ishi = True
            for k in range(p - d, p + d + 1):
                if k == p:
                    continue
                if c[k] <= c[p]:
                    islo = False
                if c[k] >= c[p]:
                    ishi = False
            if islo:
                pl = c[p]; plr = r[p]
            if ishi:
                ph = c[p]; phr = r[p]
        if j >= d:
            mn = True; mx = True
            for k in range(j - d, j):
                if c[k] <= c[j]:
                    mn = False
                if c[k] >= c[j]:
                    mx = False
            if mn and not np.isnan(pl) and c[j] < pl and r[j] > plr:
                bull[j] = True
            if mx and not np.isnan(ph) and c[j] > ph and r[j] < phr:
                bear[j] = True
    return bull, bear


def _roll_any(x, w):
    return pd.Series(x.astype(float)).rolling(w, min_periods=1).max().to_numpy() > 0


def build(bars, asset, is_crypto, extras):
    """bars: DataFrame open/high/low/close/volume/end (index = bar start, UTC).
    extras: dict with optional 'funding' (Series), 'dxy' (Series daily), 'ry' (Series daily),
    'gsr' (Series daily). Returns filters, standalone, regimes, aux (arrays the runner needs)."""
    o, h, l, c = (bars[k].to_numpy() for k in ("open", "high", "low", "close"))
    v = bars["volume"].to_numpy() if "volume" in bars and bars["volume"].notna().any() else None
    n = len(c)
    end = bars["end"]
    F, S, G = {}, {}, {}
    both = lambda m: (m, m)
    # ---- trend
    e50, e200 = ema(c, 50), ema(c, 200)
    F["ema200"] = (c > e200, c < e200)
    F["ema50x200"] = (e50 > e200, e50 < e200)
    up = (c > e200) & (l <= e50) & (c > e50); dn = (c < e200) & (h >= e50) & (c < e50)
    S["ema_pullback"] = np.where(up, 1, np.where(dn, -1, 0))
    G["ema200"] = np.where(c > e200, 1, -1)
    ad = adx(h, l, c)
    F["adx_gt25"] = both(ad > 25); F["adx_lt20"] = both(ad < 20)
    G["adx_gt25"] = np.where(ad > 25, 2, 0); G["adx_lt20"] = np.where(ad < 20, 2, 0)
    dh = pd.Series(h).rolling(55).max().to_numpy(); dl = pd.Series(l).rolling(55).min().to_numpy()
    mid = (dh + dl) / 2
    F["donchian55"] = (c > mid, c < mid)
    pdh = np.roll(dh, 1); pdl = np.roll(dl, 1); pdh[0] = np.nan; pdl[0] = np.nan
    S["donchian_break"] = np.where(c > pdh, 1, np.where(c < pdl, -1, 0))
    G["donchian55"] = np.where(c > mid, 1, np.where(c < mid, -1, 0))
    # ---- momentum
    r = rsi(c)
    F["rsi_35_65"] = (r < 35, r > 65)
    pr = np.roll(r, 1); pr[0] = 50
    S["rsi_cross"] = np.where((pr < 30) & (r >= 30), 1, np.where((pr > 70) & (r <= 70), -1, 0))
    bd, brd = rsi_div(c, r, 3)
    F["rsi_div"] = (_roll_any(bd, 5), _roll_any(brd, 5))
    S["rsi_div"] = np.where(bd, 1, np.where(brd, -1, 0))
    m = ema(c, 12) - ema(c, 26); hist = m - ema(m, 9); ph = np.roll(hist, 1); ph[0] = 0
    F["macd_turn"] = (hist > ph, hist < ph)
    S["macd_cross"] = np.where((ph <= 0) & (hist > 0), 1, np.where((ph >= 0) & (hist < 0), -1, 0))
    ll = pd.Series(l).rolling(14).min().to_numpy(); hh = pd.Series(h).rolling(14).max().to_numpy()
    k = pd.Series(100 * (c - ll) / np.where(hh - ll == 0, np.nan, hh - ll)).rolling(3).mean().to_numpy()
    F["stoch_25_75"] = (k < 25, k > 75)
    pk = np.roll(k, 1)
    S["stoch_cross"] = np.where((pk < 20) & (k >= 20), 1, np.where((pk > 80) & (k <= 80), -1, 0))
    # ---- volatility
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    ap = pct_rank(atr / c, 250)
    F["atrpct_lo"] = both(ap < 0.5); F["atrpct_hi"] = both(ap >= 0.5)
    G["atrpct_lo"] = np.where(ap < 0.5, 2, 0); G["atrpct_hi"] = np.where(ap >= 0.5, 2, 0)
    ma = pd.Series(c).rolling(20).mean().to_numpy(); sd = pd.Series(c).rolling(20).std().to_numpy()
    lb, ub = ma - 2 * sd, ma + 2 * sd
    wp = pct_rank(4 * sd / ma, 250)
    F["bb_squeeze"] = both(wp < 0.25); G["bb_squeeze"] = np.where(wp < 0.25, 2, 0)
    F["bb_touch"] = (l <= lb, h >= ub)
    S["bb_reentry"] = np.where((l <= lb) & (c > lb), 1, np.where((h >= ub) & (c < ub), -1, 0))
    # ---- volume
    aux = {"atr": atr}
    if v is not None and np.nansum(v) > 0:
        vm = pd.Series(v).rolling(20).mean().shift(1).to_numpy()
        spike = v > 1.5 * vm
        F["vol_spike"] = both(spike); G["vol_spike"] = np.where(spike, 2, 0)
        day = (bars.index + (pd.Timedelta(hours=2) if not is_crypto else pd.Timedelta(0))).floor("1D")
        tp = (h + l + c) / 3
        df = pd.DataFrame({"pv": tp * v, "v": v, "d": day})
        vw = (df.groupby("d").pv.cumsum() / df.groupby("d").v.cumsum().replace(0, np.nan)).to_numpy()
        F["vwap_trend"] = (c > vw, c < vw); F["vwap_revert"] = (c < vw, c > vw)
        pcv = np.roll(c - vw, 1)
        S["vwap_cross"] = np.where((pcv <= 0) & (c - vw > 0), 1, np.where((pcv >= 0) & (c - vw < 0), -1, 0))
        aux["poc"] = rolling_poc(h, l, c, np.nan_to_num(v), 200, 50)
    # ---- structure / SMC
    sh, sl, shi, sli = hl_pivots(h, l, 3)
    psh = np.roll(sh, 1); psl = np.roll(sl, 1); psh[0] = np.nan; psl[0] = np.nan
    sweep_l = (l < psl) & (c > psl); sweep_s = (h > psh) & (c < psh)
    F["sweep"] = (sweep_l, sweep_s)
    S["sweep"] = np.where(sweep_l, 1, np.where(sweep_s, -1, 0))
    bos_u = (c > psh) & (np.roll(c, 1) <= psh); bos_d = (c < psl) & (np.roll(c, 1) >= psl)
    F["bos10"] = (_roll_any(bos_u, 10), _roll_any(bos_d, 10))
    S["bos"] = np.where(bos_u, 1, np.where(bos_d, -1, 0))
    rng = sh - sl
    upswing = sli < shi; dnswing = shi < sli
    z_top = sh - 0.618 * rng; z_bot = sh - 0.786 * rng          # long OTE zone in an up swing
    zs_bot = sl + 0.618 * rng; zs_top = sl + 0.786 * rng        # short OTE zone in a down swing
    aux.update(dict(ote_long=(z_bot, z_top, upswing), ote_short=(zs_bot, zs_top, dnswing)))
    pl1 = np.roll(l, 1); ph1 = np.roll(h, 1)
    S["fib_ote"] = np.where(upswing & (l <= z_top) & (c > z_bot) & (pl1 > z_top), 1,
                   np.where(dnswing & (h >= zs_bot) & (c < zs_top) & (ph1 < zs_bot), -1, 0))
    # ---- candles
    po, pc_ = np.roll(o, 1), np.roll(c, 1)
    eng_l = (c > o) & (pc_ < po) & (c >= po) & (o <= pc_)
    eng_s = (c < o) & (pc_ > po) & (c <= po) & (o >= pc_)
    F["engulfing"] = (eng_l, eng_s); S["engulfing"] = np.where(eng_l, 1, np.where(eng_s, -1, 0))
    body = abs(c - o); rg = h - l
    pin_l = ((np.minimum(o, c) - l) >= 2 * body) & ((np.minimum(o, c) - l) >= 0.6 * rg) & (rg > 0)
    pin_s = ((h - np.maximum(o, c)) >= 2 * body) & ((h - np.maximum(o, c)) >= 0.6 * rg) & (rg > 0)
    F["pinbar"] = (pin_l, pin_s); S["pinbar"] = np.where(pin_l, 1, np.where(pin_s, -1, 0))
    # ---- session (bar CLOSE hour, UTC) - only meaningful intraday
    hr = end.dt.hour.to_numpy()
    sess = ((hr >= 7) & (hr <= 10)) | ((hr >= 12) & (hr <= 16))
    F["session_ldn_ny"] = both(sess); G["session_ldn_ny"] = np.where(sess, 2, 0)
    # ---- macro / crypto extras (as-of merge on bar end; series already lagged by caller)
    def asof(series):
        s = series.dropna().sort_index()
        idx = np.searchsorted(s.index.to_numpy(), end.to_numpy(), side="right") - 1
        return np.where(idx >= 0, s.to_numpy()[np.clip(idx, 0, None)], np.nan)
    if "funding" in extras:
        f = asof(extras["funding"])
        F["funding_contra"] = (f < 0.0001, f > 0.0001); F["funding_trend"] = (f > 0.0001, f < 0.0001)
        G["funding_contra"] = np.where(f < 0.0001, 1, np.where(f > 0.0001, -1, 0))
    if "dxy" in extras:
        x = asof(extras["dxy"])     # +1 = dollar below its 50d EMA (bullish metals)
        F["dxy_weak"] = (x > 0, x < 0); G["dxy_weak"] = np.where(x > 0, 1, np.where(x < 0, -1, 0))
    if "ry" in extras:
        x = asof(extras["ry"])      # +1 = real yield fell over 20d
        F["realyield_falling"] = (x > 0, x < 0); G["realyield_falling"] = np.where(x > 0, 1, np.where(x < 0, -1, 0))
    if "gsr" in extras:
        x = asof(extras["gsr"])     # +1 = favour long this metal
        F["gsr"] = (x > 0, x < 0); G["gsr"] = np.where(x > 0, 1, np.where(x < 0, -1, 0))
    return F, S, G, aux


LEVEL_FILTERS = ["round_number", "poc_near", "fvg", "fib_ote_lvl"]


def level_filters(lvl, c, atr, aux, asset_step):
    """Filters that depend on the MSNR level price at the signal bar."""
    out = {}
    L = lvl
    step = asset_step
    near = np.abs(L - np.round(L / step) * step) <= 0.2 * atr
    out["round_number"] = (near, near)
    if "poc" in aux:
        pn = np.abs(L - aux["poc"]) <= 0.5 * atr
        out["poc_near"] = (pn, pn)
    zb, zt, up = aux["ote_long"]; sb, st, dn = aux["ote_short"]
    out["fib_ote_lvl"] = (up & (L >= zb) & (L <= zt), dn & (L >= sb) & (L <= st))
    return out
