"""Phase-2 engine: general exits, limit/maker entries at fresh levels, generalized random baseline.
All functions are causal: decisions at bar j use data <= bar j close (market entries fill at
open[j+1]); resting limit orders use only levels that existed before bar j and filters as of
bar j-1. Same-bar ambiguity: stop first; for limit fills a TP is never credited in the fill bar.

Exit modes (p1, p2 meaning):
  0 fixed target      : TP = p1 R
  1 next fresh level  : TP = nearest fresh opposite level (trade skipped if < p1 R away)
  2 breakeven         : TP = p1 R, stop -> entry after +p2 R is reached (active from next bar)
  3 ATR trail         : chandelier stop best_price - p1*ATR(signal), no TP (20R cap)
  4 partial           : 50% off at +1R, rest TP = p1 R, stop -> entry after the partial
  5 time stop         : TP = p1 R, else exit at close of bar entry+p2-1
"""
import numpy as np
from numba import njit

MIN_RISK_FRAC = 0.0005   # stops tighter than 5 bp of price are not tradable (flat-bar / zero-ATR artefacts)


@njit(cache=True)
def exit_general(o, h, l, c, k0, entry_bar, d, E, S, T, R, mode, p1, p2, atr0):
    """Returns (exit_idx, gross_R, exit_kind) exit_kind 1 = limit TP, 0 = stop/other."""
    n = len(c)
    stop = S
    if mode == 3:
        tgt = E + d * 20.0 * R
    else:
        tgt = T
    realized = 0.0; w = 1.0; part = False
    best = E
    for k in range(k0, n):
        # ---- stop first
        if (d == 1 and l[k] <= stop) or (d == -1 and h[k] >= stop):
            if k > entry_bar:
                px = min(stop, o[k]) if d == 1 else max(stop, o[k])
            else:
                px = stop
            return k, realized + w * d * (px - E) / R, 0
        # ---- partial at +1R
        if mode == 4 and not part:
            lvl1 = E + d * R
            if (d == 1 and h[k] >= lvl1) or (d == -1 and l[k] <= lvl1):
                realized += 0.5; w = 0.5; part = True
        # ---- target
        if (d == 1 and h[k] >= tgt) or (d == -1 and l[k] <= tgt):
            return k, realized + w * d * (tgt - E) / R, 1
        # ---- time stop
        if mode == 5 and (k - entry_bar + 1) >= p2:
            return k, realized + w * d * (c[k] - E) / R, 0
        # ---- end-of-bar updates (active from next bar)
        if mode == 2:
            trig = E + d * p2 * R
            if (d == 1 and h[k] >= trig) or (d == -1 and l[k] <= trig):
                stop = max(stop, E) if d == 1 else min(stop, E)
        elif mode == 4 and part:
            stop = max(stop, E) if d == 1 else min(stop, E)
        elif mode == 3:
            if d == 1:
                best = max(best, h[k]); stop = max(stop, best - p1 * atr0)
            else:
                best = min(best, l[k]); stop = min(stop, best + p1 * atr0)
    return n - 1, realized + w * d * (c[n - 1] - E) / R, 0


@njit(cache=True)
def _cost(E, X, kind, eabs, epct, tabs, tpct, sabs, spct):
    if kind == 1:
        return eabs + epct * E + tabs + tpct * X
    return eabs + epct * E + sabs + spct * X


@njit(cache=True)
def sim_market(o, h, l, c, a, sig, nres, nsup, j_lo, j_hi, buf, mode, p1, p2,
               eabs, epct, tabs, tpct, sabs, spct, carry, bar_hours):
    """Market entry at open[j+1] after a signal at bar j close. SL beyond bar-j wick + buf*ATR.
    cols: sig_j, entry_j, exit_j, dir, E, S, risk, grossR, costR, risk_atr, tgtR, exit_kind"""
    n = len(c)
    out = np.zeros((max(j_hi - j_lo, 1), 12)); m = 0; busy = -1
    for j in range(j_lo, min(j_hi, n - 1)):
        d = sig[j]
        if d == 0 or j < busy or np.isnan(a[j]):
            continue
        E = o[j + 1]
        S = l[j] - buf * a[j] if d == 1 else h[j] + buf * a[j]
        R = d * (E - S)
        if R <= 0 or R < MIN_RISK_FRAC * E:
            continue
        if mode == 1:
            T = nres[j] if d == 1 else nsup[j]
            if np.isnan(T) or d * (T - E) < p1 * R:
                continue
        else:
            T = E + d * p1 * R
        k, g, kind = exit_general(o, h, l, c, j + 1, j + 1, d, E, S, T, R, mode, p1, p2, a[j])
        X = E + d * g * R
        cost = _cost(E, X, kind, eabs, epct, tabs, tpct, sabs, spct) / R + carry * (k - j) * bar_hours / 8760.0 * E / R
        out[m, 0] = j; out[m, 1] = j + 1; out[m, 2] = k; out[m, 3] = d; out[m, 4] = E; out[m, 5] = S
        out[m, 6] = R; out[m, 7] = g; out[m, 8] = cost; out[m, 9] = R / a[j]; out[m, 10] = d * (T - E) / R
        out[m, 11] = kind
        m += 1; busy = k + 1
    return out[:m]


@njit(cache=True)
def run_levels_limit(o, h, l, c, a, ev_idx, ev_px, ev_kind, eps_atr, max_flips):
    """Resting limit orders at every FRESH level (sell at resistance, buy at support).
    Fill only if price trades THROUGH the level by eps_atr*ATR(prev bar) (missed-fill model;
    eps 0 = optimistic touch fill). Fill price = level, or the open if the bar gaps beyond it.
    Among several candidate levels the one nearest the open is assumed to fill first.
    State update (touch -> unfresh, body close through -> flip / die) is as in msnr.run_levels."""
    n = len(c); ne = len(ev_idx); cap = ne + 1
    px = np.empty(cap); kind = np.empty(cap, np.int64)
    fresh = np.zeros(cap, np.bool_); alive = np.zeros(cap, np.bool_); flips = np.zeros(cap, np.int64)
    m = 0; e = 0
    fdir = np.zeros(n, np.int64); fpx = np.full(n, np.nan); flvl = np.full(n, np.nan)
    nres = np.full(n, np.nan); nsup = np.full(n, np.nan)
    for j in range(n):
        while e < ne and ev_idx[e] <= j:
            px[m] = ev_px[e]; kind[m] = ev_kind[e]; fresh[m] = True; alive[m] = True; flips[m] = 0
            m += 1; e += 1
        # nearest fresh opposite levels known BEFORE this bar (for next-level TP of a fill now)
        nr = np.inf; ns = -np.inf
        eps = eps_atr * a[j - 1] if j > 0 and not np.isnan(a[j - 1]) else np.nan
        bestd = np.inf; bdir = 0; bpx = np.nan; blv = np.nan
        for k in range(m):
            if not (alive[k] and fresh[k]):
                continue
            L = px[k]
            if kind[k] == 1:
                if L > o[j] and L < nr:
                    nr = L
                if not np.isnan(eps) and h[j] >= L + eps:
                    dist = max(L - o[j], 0.0)
                    if dist < bestd:
                        bestd = dist; bdir = -1; bpx = max(L, o[j]); blv = L
            else:
                if L < o[j] and L > ns:
                    ns = L
                if not np.isnan(eps) and l[j] <= L - eps:
                    dist = max(o[j] - L, 0.0)
                    if dist < bestd:
                        bestd = dist; bdir = 1; bpx = min(L, o[j]); blv = L
        if nr < np.inf:
            nres[j] = nr
        if ns > -np.inf:
            nsup[j] = ns
        fdir[j] = bdir; fpx[j] = bpx; flvl[j] = blv
        # state updates
        for k in range(m):
            if not alive[k]:
                continue
            L = px[k]
            if kind[k] == 1:
                if c[j] > L:
                    if flips[k] >= max_flips:
                        alive[k] = False
                    else:
                        kind[k] = -1; fresh[k] = True; flips[k] += 1
                elif h[j] >= L:
                    fresh[k] = False
            else:
                if c[j] < L:
                    if flips[k] >= max_flips:
                        alive[k] = False
                    else:
                        kind[k] = 1; fresh[k] = True; flips[k] += 1
                elif l[j] <= L:
                    fresh[k] = False
    return fdir, fpx, flvl, nres, nsup


@njit(cache=True)
def sim_limit(o, h, l, c, a, fdir, fpx, flvl, nres, nsup, ok_long, ok_short, j_lo, j_hi, sl_atr,
              mode, p1, p2, eabs, epct, tabs, tpct, sabs, spct, carry, bar_hours):
    """Limit fill at bar j (price fpx). Filters ok_long/ok_short must be evaluated at j-1
    (caller passes shifted arrays). SL = level -/+ sl_atr*ATR(j-1). In the fill bar only the SL
    can trigger (conservative). Exits from bar j+1 via exit_general."""
    n = len(c)
    out = np.zeros((max(j_hi - j_lo, 1), 12)); m = 0; busy = -1
    for j in range(max(j_lo, 1), min(j_hi, n - 1)):
        d = fdir[j]
        if d == 0 or j < busy or np.isnan(a[j - 1]):
            continue
        if (d == 1 and not ok_long[j]) or (d == -1 and not ok_short[j]):
            continue
        E = fpx[j]; L = flvl[j]
        S = L - d * sl_atr * a[j - 1]
        R = d * (E - S)
        if R <= 0 or R < MIN_RISK_FRAC * E:
            continue
        if mode == 1:
            T = nres[j] if d == 1 else nsup[j]
            if np.isnan(T) or d * (T - E) < p1 * R:
                continue
        else:
            T = E + d * p1 * R
        if (d == 1 and l[j] <= S) or (d == -1 and h[j] >= S):
            k = j; g = -1.0; kind = 0
        else:
            k, g, kind = exit_general(o, h, l, c, j + 1, j, d, E, S, T, R, mode, p1, p2, a[j - 1])
        X = E + d * g * R
        cost = _cost(E, X, kind, eabs, epct, tabs, tpct, sabs, spct) / R + carry * (k - j + 1) * bar_hours / 8760.0 * E / R
        out[m, 0] = j; out[m, 1] = j; out[m, 2] = k; out[m, 3] = d; out[m, 4] = E; out[m, 5] = S
        out[m, 6] = R; out[m, 7] = g; out[m, 8] = cost; out[m, 9] = R / a[j - 1]; out[m, 10] = d * (T - E) / R
        out[m, 11] = kind
        m += 1; busy = k + 1
    return out[:m]


@njit(cache=True)
def random_baseline2(o, h, l, c, a, dir_arr, use_dir, j_lo, j_hi, ntr, risk_atr, tgt_r, mode, p1, p2,
                     eabs, epct, tabs, tpct, sabs, spct, carry, bar_hours, reps, seed):
    """Random entries (open of j+1) with the strategy's own risk (ATR units) and targets.
    use_dir: 0 coin flip on every bar; 1 direction = dir_arr[j] (0 = bar not allowed).
    Returns (net mean per rep, gross mean per rep)."""
    np.random.seed(seed)
    resn = np.full(reps, np.nan); resg = np.full(reps, np.nan)
    hi = min(j_hi, len(c) - 1)
    if hi - j_lo < 10 or ntr == 0:
        return resn, resg
    for r in range(reps):
        tn = 0.0; tg = 0.0; cnt = 0; tries = 0
        while cnt < ntr and tries < ntr * 200:
            tries += 1
            j = np.random.randint(j_lo, hi)
            if np.isnan(a[j]):
                continue
            if use_dir == 1:
                d = dir_arr[j]
                if d == 0:
                    continue
                if d == 2:
                    d = 1 if np.random.random() < 0.5 else -1
            else:
                d = 1 if np.random.random() < 0.5 else -1
            q = np.random.randint(0, len(risk_atr))
            R = risk_atr[q] * a[j]
            E = o[j + 1]
            if R <= 0 or R < MIN_RISK_FRAC * E:
                continue
            S = E - d * R
            tr = tgt_r[q] if mode != 3 else 20.0
            T = E + d * tr * R
            k, g, kind = exit_general(o, h, l, c, j + 1, j + 1, d, E, S, T, R, 0 if mode == 1 else mode, p1, p2, a[j])
            X = E + d * g * R
            cost = _cost(E, X, kind, eabs, epct, tabs, tpct, sabs, spct) / R + carry * (k - j) * bar_hours / 8760.0 * E / R
            tn += g - cost; tg += g; cnt += 1
        if cnt > 0:
            resn[r] = tn / cnt; resg[r] = tg / cnt
    return resn, resg
