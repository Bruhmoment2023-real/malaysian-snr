"""Malaysian SnR (MSNR) rule engine + trade simulator. No look-ahead by construction.

Codified rules (community consensus, see research/MSNR-rules-and-sources.md):
  A-level (resistance): bullish candle i-1 followed by bearish candle i -> level = close[i-1]
                         (= a peak of the close-only line chart).
  V-level (support)    : bearish candle i-1 followed by bullish candle i -> level = close[i-1].
  The level only exists after candle i has CLOSED -> usable from bar i+1.
  Fresh   : no wick has touched the level since it was created / last body-crossed.
  Unfresh : a wick touched it but the candle body closed back on the original side.
  Body cross (close beyond the level) -> role flip (resistance->support = RBS,
            support->resistance = SBR) and the level is FRESH again.
  Signal  : bar j's wick touches a FRESH level and bar j closes back on the level's side
            (a rejection). Short at resistance / long at support. Entry = OPEN of bar j+1.
  SL      : beyond the rejection wick: low[j] - buf*ATR (long) / high[j] + buf*ATR (short).
  TP      : fixed k*R, or the nearest FRESH opposite level (skip if < min_rr R away).
  Same-bar SL & TP -> SL assumed first. Gap through SL -> filled at the open (worse).
  QM (Quasimodo) level: on close-based swing pivots (depth d). Bullish QM = swing low L1,
  swing high H1, lower swing low L2 < L1, then a CLOSE above H1 -> QML = L1 (support).
  Bearish mirror. QML is fresh until first wick touch (trade) and dies on a body close
  through it (no role flip).
  Storyline (HTF bias): close-based swing pivots on the higher timeframe (depth d);
  bias = +1 after an HTF close above the last confirmed swing high, -1 after an HTF close
  below the last confirmed swing low. Only known once the HTF bar has closed.
Gap levels are NOT used: on 24/7 crypto and on hourly-resampled spot metals the next bar
opens at the previous close, so close/open gaps are essentially nonexistent.
"""
import numpy as np
import pandas as pd
from numba import njit

# ----------------------------------------------------------------------------- bars

def make_bars(df1h: pd.DataFrame, tf: str, metals: bool) -> pd.DataFrame:
    """Resample 1H to tf in {'1h','4h','1d','1w'}. Metals use the FX-broker day that
    starts 22:00 UTC (NY 17:00 winter); crypto uses UTC. Each bar gets 'end' = the time
    at which it is closed (last 1H bar start + 1h)."""
    shift = pd.Timedelta(hours=2) if metals else pd.Timedelta(0)
    t = df1h.index + shift
    if tf == "1h":
        key = t.floor("1h")
    elif tf == "4h":
        key = t.floor("4h")
    elif tf == "1d":
        key = t.floor("1D")
    elif tf == "1w":
        key = t.tz_localize(None).to_period("W-SUN").start_time.tz_localize("UTC")
    else:
        raise ValueError(tf)
    g = df1h.assign(_k=key, _t=df1h.index).groupby("_k", sort=True)
    out = pd.DataFrame({
        "open": g.open.first(), "high": g.high.max(), "low": g.low.min(),
        "close": g.close.last(), "start": g._t.first(), "end": g._t.last() + pd.Timedelta(hours=1)})
    out = out.set_index("start")
    return out


def atr(df, n=14):
    pc = df.close.shift(1)
    tr = np.maximum(df.high - df.low, np.maximum((df.high - pc).abs(), (df.low - pc).abs()))
    return tr.rolling(n, min_periods=n).mean().to_numpy()

# ----------------------------------------------------------------------------- pivots / storyline / events

@njit(cache=True)
def _close_pivots(c, d):
    """Returns arrays (idx, confirm_idx, type(+1 high/-1 low), price), alternating."""
    n = len(c)
    pidx = np.empty(n, np.int64); pcf = np.empty(n, np.int64)
    ptyp = np.empty(n, np.int64); ppx = np.empty(n)
    m = 0
    for p in range(d, n - d):
        ishi = True; islo = True
        for k in range(p - d, p + d + 1):
            if k == p:
                continue
            if c[k] >= c[p]:
                ishi = False
            if c[k] <= c[p]:
                islo = False
        typ = 1 if ishi else (-1 if islo else 0)
        if typ == 0:
            continue
        if m > 0 and ptyp[m - 1] == typ:
            # same type in a row: keep the more extreme one (confirmed now)
            if (typ == 1 and c[p] > ppx[m - 1]) or (typ == -1 and c[p] < ppx[m - 1]):
                pidx[m - 1] = p; pcf[m - 1] = p + d; ppx[m - 1] = c[p]
            continue
        pidx[m] = p; pcf[m] = p + d; ptyp[m] = typ; ppx[m] = c[p]; m += 1
    return pidx[:m], pcf[:m], ptyp[:m], ppx[:m]


@njit(cache=True)
def _storyline(c, pcf, ptyp, ppx):
    n = len(c)
    out = np.zeros(n, np.int64)
    sh = np.nan; sl = np.nan; trend = 0; q = 0
    for j in range(n):
        while q < len(pcf) and pcf[q] <= j:      # pivot confirmed at close of bar pcf[q]
            if ptyp[q] == 1:
                sh = ppx[q]
            else:
                sl = ppx[q]
            q += 1
        if not np.isnan(sh) and c[j] > sh:
            trend = 1
        elif not np.isnan(sl) and c[j] < sl:
            trend = -1
        out[j] = trend
    return out


def storyline(df, depth=2):
    c = df.close.to_numpy()
    _, pcf, ptyp, ppx = _close_pivots(c, depth)
    return _storyline(c, pcf, ptyp, ppx)


@njit(cache=True)
def _qm_events(c, pcf, ptyp, ppx):
    """QM levels created at the close of the bar that breaks structure."""
    n = len(c)
    ev_i = np.empty(n, np.int64); ev_px = np.empty(n); ev_k = np.empty(n, np.int64)
    m = 0; q = 0; last_used = -1
    for j in range(n):
        while q < len(pcf) and pcf[q] <= j:
            q += 1
        if q < 3:
            continue
        a, b, cc = q - 3, q - 2, q - 1
        if cc == last_used:
            continue
        # bullish: low L1, high H1, lower low L2 ; close > H1
        if ptyp[a] == -1 and ptyp[b] == 1 and ptyp[cc] == -1 and ppx[cc] < ppx[a] and c[j] > ppx[b]:
            ev_i[m] = j; ev_px[m] = ppx[a]; ev_k[m] = -1; m += 1; last_used = cc
        elif ptyp[a] == 1 and ptyp[b] == -1 and ptyp[cc] == 1 and ppx[cc] > ppx[a] and c[j] < ppx[b]:
            ev_i[m] = j; ev_px[m] = ppx[a]; ev_k[m] = 1; m += 1; last_used = cc
    return ev_i[:m], ev_px[:m], ev_k[:m]


def level_events(df, include_av=True, include_qm=True, av_mode="pivot", av_depth=3, qm_depth=2):
    """Level creation events on bars of df: returns DataFrame(avail, price, kind, src).
    kind +1 = resistance (price below it), -1 = support. src 0 = A/V, 1 = QM.
    av_mode "raw"  : literal 2-candle rule (bull->bear = A at close[i-1]; bear->bull = V).
                     Usable after candle i closes.
    av_mode "pivot": A = close-line peak higher than av_depth closes on each side, V = valley
                     (the 'obvious' line-chart peaks a human marks; depth 3 = DoN_JCT default).
                     Usable only after bar p+av_depth closes.
    avail = df.end of the confirming bar (the level can only be used after that)."""
    o = df.open.to_numpy(); c = df.close.to_numpy(); end = df.end.to_numpy()
    rows = []
    if include_av and av_mode == "raw":
        bull = c > o; bear = c < o
        a_idx = np.where(bull[:-1] & bear[1:])[0] + 1     # confirming bar i
        v_idx = np.where(bear[:-1] & bull[1:])[0] + 1
        rows.append(pd.DataFrame({"avail": end[a_idx], "price": c[a_idx - 1], "kind": 1, "src": 0}))
        rows.append(pd.DataFrame({"avail": end[v_idx], "price": c[v_idx - 1], "kind": -1, "src": 0}))
    elif include_av:
        pidx, pcf, ptyp, ppx = _raw_pivots(c, av_depth)
        rows.append(pd.DataFrame({"avail": end[pcf], "price": ppx, "kind": ptyp, "src": 0}))
    if include_qm:
        _, pcf, ptyp, ppx = _close_pivots(c, qm_depth)
        ei, epx, ek = _qm_events(c, pcf, ptyp, ppx)
        rows.append(pd.DataFrame({"avail": end[ei], "price": epx, "kind": ek, "src": 1}))
    ev = pd.concat(rows, ignore_index=True).sort_values("avail", kind="stable").reset_index(drop=True)
    return ev


@njit(cache=True)
def _raw_pivots(c, d):
    """All close-line peaks/valleys of depth d (not forced to alternate)."""
    n = len(c)
    pidx = np.empty(n, np.int64); pcf = np.empty(n, np.int64)
    ptyp = np.empty(n, np.int64); ppx = np.empty(n)
    m = 0
    for p in range(d, n - d):
        ishi = True; islo = True
        for k in range(p - d, p + d + 1):
            if k == p:
                continue
            if c[k] >= c[p]:
                ishi = False
            if c[k] <= c[p]:
                islo = False
        if ishi or islo:
            pidx[m] = p; pcf[m] = p + d; ptyp[m] = 1 if ishi else -1; ppx[m] = c[p]; m += 1
    return pidx[:m], pcf[:m], ptyp[:m], ppx[:m]


def map_events_to_bars(ev, bars):
    """First bar of `bars` whose START is >= the event's availability time."""
    starts = bars.index.to_numpy()
    idx = np.searchsorted(starts, ev.avail.to_numpy(), side="left")
    keep = idx < len(bars)
    return idx[keep].astype(np.int64), ev.price.to_numpy()[keep], ev.kind.to_numpy()[keep].astype(np.int64), ev.src.to_numpy()[keep].astype(np.int64)

# ----------------------------------------------------------------------------- level state machine

@njit(cache=True)
def run_levels(o, h, l, c, ev_idx, ev_px, ev_kind, ev_src, max_flips=1):
    """Walk bars; returns per-bar signals for src 0 and src 1 (+1 long, -1 short, 0 none),
    the touched level price, and nearest fresh resistance above / support below the close
    (for next-level TP), all evaluated at the CLOSE of bar j."""
    n = len(c); ne = len(ev_idx)
    cap = ne + 1
    px = np.empty(cap); kind = np.empty(cap, np.int64); src = np.empty(cap, np.int64)
    fresh = np.zeros(cap, np.bool_); alive = np.zeros(cap, np.bool_); flips = np.zeros(cap, np.int64)
    m = 0; e = 0
    sig0 = np.zeros(n, np.int64); sig1 = np.zeros(n, np.int64)
    lvl0 = np.full(n, np.nan); lvl1 = np.full(n, np.nan)
    nres = np.full(n, np.nan); nsup = np.full(n, np.nan)
    nalive = 0
    for j in range(n):
        while e < ne and ev_idx[e] <= j:            # level becomes usable at bar ev_idx
            px[m] = ev_px[e]; kind[m] = ev_kind[e]; src[m] = ev_src[e]
            fresh[m] = True; alive[m] = True; flips[m] = 0; m += 1; e += 1
        s0l = False; s0s = False; s1l = False; s1s = False
        best0l = np.nan; best0s = np.nan; best1l = np.nan; best1s = np.nan
        for k in range(m):
            if not alive[k]:
                continue
            L = px[k]
            if kind[k] == 1:                          # resistance, price expected below
                if c[j] > L:                          # body closes through -> flip (RBS)
                    if src[k] == 1 or flips[k] >= max_flips:
                        alive[k] = False
                    else:
                        kind[k] = -1; fresh[k] = True; flips[k] += 1
                elif h[j] >= L and (j == 0 or h[j - 1] < L):   # a RETEST: price left, came back, wick touch, close below
                    if fresh[k]:
                        if src[k] == 0:
                            s0s = True
                            if np.isnan(best0s) or L > best0s:
                                best0s = L
                        else:
                            s1s = True; best1s = L
                            alive[k] = False          # QML is one-shot
                    fresh[k] = False
            else:                                     # support, price expected above
                if c[j] < L:                          # body closes through -> flip (SBR)
                    if src[k] == 1 or flips[k] >= max_flips:
                        alive[k] = False
                    else:
                        kind[k] = 1; fresh[k] = True; flips[k] += 1
                elif l[j] <= L and (j == 0 or l[j - 1] > L):
                    if fresh[k]:
                        if src[k] == 0:
                            s0l = True
                            if np.isnan(best0l) or L < best0l:
                                best0l = L
                        else:
                            s1l = True; best1l = L
                            alive[k] = False
                    fresh[k] = False
        # nearest fresh opposite levels after this bar's updates
        nr = np.inf; ns = -np.inf
        for k in range(m):
            if alive[k] and fresh[k]:
                if kind[k] == 1 and px[k] > c[j] and px[k] < nr:
                    nr = px[k]
                if kind[k] == -1 and px[k] < c[j] and px[k] > ns:
                    ns = px[k]
        if nr < np.inf:
            nres[j] = nr
        if ns > -np.inf:
            nsup[j] = ns
        if s0l and not s0s:
            sig0[j] = 1; lvl0[j] = best0l
        elif s0s and not s0l:
            sig0[j] = -1; lvl0[j] = best0s
        if s1l and not s1s:
            sig1[j] = 1; lvl1[j] = best1l
        elif s1s and not s1l:
            sig1[j] = -1; lvl1[j] = best1s
        # compact dead levels occasionally (QM only die)
    return sig0, sig1, lvl0, lvl1, nres, nsup

# ----------------------------------------------------------------------------- trade simulation

@njit(cache=True)
def _exit(o, h, l, c, k0, d, E, S, T):
    """Walk from bar k0 (entry bar, entry at its open E). SL checked first each bar.
    Returns (exit_idx, exit_px, hit) hit=+1 TP, -1 SL, 0 end of data."""
    n = len(c)
    for k in range(k0, n):
        if d == 1:
            if l[k] <= S:
                return k, min(S, o[k]) if k > k0 else S, -1
            if h[k] >= T:
                return k, T, 1
        else:
            if h[k] >= S:
                return k, max(S, o[k]) if k > k0 else S, -1
            if l[k] <= T:
                return k, T, 1
    return n - 1, c[n - 1], 0


@njit(cache=True)
def simulate(o, h, l, c, a, sig, nres, nsup, j_lo, j_hi, buf, tp_mode, tp_r, min_rr,
             cost_abs, cost_pct, carry, bar_hours, one_at_a_time):
    """Simulate signals at bars j in [j_lo, j_hi). Entry open[j+1].
    tp_mode 0 = fixed tp_r * R ; 1 = nearest fresh opposite level (skip if < min_rr R).
    Returns per-trade arrays: sig_j, entry_j, exit_j, dir, E, S, T, gross_R, cost_R, risk_atr, tgt_R."""
    n = len(c)
    out = np.zeros((j_hi - j_lo, 11))
    m = 0; busy_until = -1
    for j in range(j_lo, min(j_hi, n - 1)):
        d = sig[j]
        if d == 0 or np.isnan(a[j]):
            continue
        if one_at_a_time and j < busy_until:
            continue
        E = o[j + 1]
        if d == 1:
            S = l[j] - buf * a[j]
            risk = E - S
        else:
            S = h[j] + buf * a[j]
            risk = S - E
        if risk <= 0:
            continue
        if tp_mode == 0:
            T = E + d * tp_r * risk
        else:
            T = nres[j] if d == 1 else nsup[j]
            if np.isnan(T):
                continue
            if d * (T - E) < min_rr * risk:
                continue
        k, X, hit = _exit(o, h, l, c, j + 1, d, E, S, T)
        gross = d * (X - E) / risk
        cost = (cost_abs + cost_pct * E * 2.0) / risk + carry * (k - j) * bar_hours / 8760.0 * E / risk
        out[m, 0] = j; out[m, 1] = j + 1; out[m, 2] = k; out[m, 3] = d
        out[m, 4] = E; out[m, 5] = S; out[m, 6] = T; out[m, 7] = gross; out[m, 8] = cost
        out[m, 9] = risk / a[j]; out[m, 10] = d * (T - E) / risk
        m += 1
        busy_until = k + 1      # can't take a new signal until the bar after exit
    return out[:m]


@njit(cache=True)
def random_baseline(o, h, l, c, a, story, j_lo, j_hi, ntr, risk_atr, tgt_r, use_story,
                    cost_abs, cost_pct, carry, bar_hours, reps, seed):
    """Random-entry baseline with the same SL/TP geometry: random signal bars in the same
    window, SL distance drawn from the strategy's own risk (in ATR), target R drawn from
    the strategy's own targets. Direction = coin flip, or the HTF storyline if use_story.
    Returns (mean net R per rep, mean gross R per rep)."""
    np.random.seed(seed)
    res = np.full(reps, np.nan); resg = np.full(reps, np.nan)
    hi = min(j_hi, len(c) - 1)
    for r in range(reps):
        tot = 0.0; totg = 0.0; cnt = 0; tries = 0
        while cnt < ntr and tries < ntr * 50:
            tries += 1
            j = np.random.randint(j_lo, hi)
            if np.isnan(a[j]):
                continue
            if use_story:
                d = story[j]
                if d == 0:
                    continue
            else:
                d = 1 if np.random.random() < 0.5 else -1
            q = np.random.randint(0, len(risk_atr))
            risk = risk_atr[q] * a[j]
            if risk <= 0:
                continue
            E = o[j + 1]
            S = E - d * risk
            T = E + d * tgt_r[q] * risk
            k, X, hit = _exit(o, h, l, c, j + 1, d, E, S, T)
            totg += d * (X - E) / risk
            tot += d * (X - E) / risk - (cost_abs + cost_pct * E * 2.0) / risk - carry * (k - j) * bar_hours / 8760.0 * E / risk
            cnt += 1
        if cnt > 0:
            res[r] = tot / cnt; resg[r] = totg / cnt
    return res, resg
