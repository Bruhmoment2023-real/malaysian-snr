"""Faithful top-down MSNR (ladder T1/T2/T3/T4), causal by construction.

T1 storyline TF, T2 roadblock TF, T3 point-of-interest (POI) TF, T4 entry TF.
1. Levels on each TF from closes (A = close-line peak, V = valley; pivot depth d) + optional gap levels
   (two same-colour candles, open[i] != close[i-1]; level = close[i-1]). One role flip, then dead.
2. Top-down storyline: a T1 fresh level is rejected (wick touch, T1 close back) -> pending; a T2 break of
   structure (T2 close beyond the last confirmed T2 swing) in that direction within W2 T2 bars activates the
   storyline. It ends when price reaches the nearest opposing fresh T1 level that existed at activation
   (storyline end) or when a T2 close goes beyond the T1 rejection wick (invalidation), or a new opposite one starts.
3. POI: a FRESH T3 level touched by a T4 wick (support for longs, resistance for shorts). The touch makes the
   level unfresh. A zone then stays open up to K T4 bars, closed early if a T4 close goes beyond the level by
   0.25*ATR(T3).
4. Confirmations inside the zone on T4: 'rej' = touch bar itself closed back on the level's side,
   'eng' = engulfing candle, 'bos' = T4 close beyond the last confirmed T4 swing (pivot depth 2).
   The first time each happens is recorded with the zone extreme (lowest low / highest high since touch).
5. Recorded per setup: storyline (top-down, simple pivot), storyline-end target, nearest opposing fresh T2
   level (roadblock), liquidity (# unswept T3 swing points within [L-1 ATR3, L+0.25 ATR3] beyond/near the
   level), misses (# T3 bars since level creation that came within 0.5 ATR3 without touching), level age.
Entry/stop/target choices are applied later (sim_setups) so every piece can be switched on/off.
"""
import numpy as np
from numba import njit


# ------------------------------------------------------------------ helpers on a single TF
@njit(cache=True)
def wick_swings(h, l, d):
    """Last confirmed swing high / low (wick pivots depth d) known at the close of each bar."""
    n = len(h); sh = np.full(n, np.nan); sl = np.full(n, np.nan)
    ch = np.nan; cl = np.nan
    for j in range(n):
        p = j - d
        if p >= d:
            ih = True; il = True
            for k in range(p - d, p + d + 1):
                if k == p:
                    continue
                if h[k] >= h[p]:
                    ih = False
                if l[k] <= l[p]:
                    il = False
            if ih:
                ch = h[p]
            if il:
                cl = l[p]
        sh[j] = ch; sl[j] = cl
    return sh, sl


@njit(cache=True)
def swing_events(h, l, d):
    """All wick swing points with the bar index at which they are confirmed (p+d). type +1 high, -1 low."""
    n = len(h); cf = np.empty(n, np.int64); px = np.empty(n); ty = np.empty(n, np.int64); m = 0
    for p in range(d, n - d):
        ih = True; il = True
        for k in range(p - d, p + d + 1):
            if k == p:
                continue
            if h[k] >= h[p]:
                ih = False
            if l[k] <= l[p]:
                il = False
        if ih:
            cf[m] = p + d; px[m] = h[p]; ty[m] = 1; m += 1
        if il:
            cf[m] = p + d; px[m] = l[p]; ty[m] = -1; m += 1
    return cf[:m], px[:m], ty[:m]


@njit(cache=True)
def topdown_story(n2, t1_close_at2, t1_sig_at2, t1_ext_at2, t1_tgt_at2, h2, l2, c2, sh2, sl2, W2):
    """Storyline state evaluated at each T2 bar close. Inputs mapped to T2 index (nan / 0 if no T1 close
    at that T2 bar). Returns story dir, invalidation level, end target per T2 bar."""
    st = np.zeros(n2, np.int64); tg = np.full(n2, np.nan)
    cur = 0; inv = np.nan; tgt = np.nan
    pend = 0; pend_inv = np.nan; pend_tgt = np.nan; pend_left = 0
    for j in range(n2):
        if t1_sig_at2[j] != 0:
            pend = t1_sig_at2[j]; pend_inv = t1_ext_at2[j]; pend_tgt = t1_tgt_at2[j]; pend_left = W2
        if pend != 0:
            psh = sh2[j - 1] if j > 0 else np.nan
            psl = sl2[j - 1] if j > 0 else np.nan
            if pend == 1 and not np.isnan(psh) and c2[j] > psh:
                cur = 1; inv = pend_inv; tgt = pend_tgt; pend = 0
            elif pend == -1 and not np.isnan(psl) and c2[j] < psl:
                cur = -1; inv = pend_inv; tgt = pend_tgt; pend = 0
            else:
                pend_left -= 1
                if pend_left <= 0:
                    pend = 0
        if cur == 1:
            if (not np.isnan(tgt) and h2[j] >= tgt) or c2[j] < inv:
                cur = 0
        elif cur == -1:
            if (not np.isnan(tgt) and l2[j] <= tgt) or c2[j] > inv:
                cur = 0
        st[j] = cur; tg[j] = tgt if cur != 0 else np.nan
    return st, tg


# ------------------------------------------------------------------ POI setups on T4
@njit(cache=True)
def gen_setups(o, h, l, c, atr4, atr3_at, t3c_at, t3h_at, t3l_at,
               ev_j, ev_px, ev_kind, sw_j, sw_px, sw_ty, K, prune_atr):
    """Returns setups array (rows) with columns:
    0 dir, 1 L, 2 j_touch, 3 j_rej, 4 ext_rej, 5 j_eng, 6 ext_eng, 7 j_bos, 8 ext_bos, 9 atr3, 10 liq, 11 miss, 12 age_bars"""
    n = len(c); ne = len(ev_j); ns = len(sw_j)
    cap = ne + 1
    px = np.empty(cap); kind = np.empty(cap, np.int64); fresh = np.zeros(cap, np.bool_)
    alive = np.zeros(cap, np.bool_); flips = np.zeros(cap, np.int64); miss = np.zeros(cap, np.int64); born = np.zeros(cap, np.int64)
    m = 0; e = 0
    spx = np.empty(ns + 1); sty = np.empty(ns + 1, np.int64); salive = np.zeros(ns + 1, np.bool_); sm = 0; se = 0
    out = np.full((3 * cap + 10, 13), np.nan); no = 0
    # active zones
    zc = 512
    z_row = np.full(zc, -1, np.int64); z_dir = np.zeros(zc, np.int64); z_L = np.zeros(zc); z_start = np.zeros(zc, np.int64)
    z_ext = np.zeros(zc); z_on = np.zeros(zc, np.bool_)
    ph = np.nan; pl = np.nan          # last confirmed T4 swing high/low (depth 2)
    for j in range(n):
        while e < ne and ev_j[e] <= j:
            px[m] = ev_px[e]; kind[m] = ev_kind[e]; fresh[m] = True; alive[m] = True; flips[m] = 0; miss[m] = 0; born[m] = j
            m += 1; e += 1
        while se < ns and sw_j[se] <= j:
            spx[sm] = sw_px[se]; sty[sm] = sw_ty[se]; salive[sm] = True; sm += 1; se += 1
        # sweep liquidity (swing highs taken by a higher high, lows by a lower low)
        for k in range(sm):
            if salive[k]:
                if sty[k] == 1 and h[j] > spx[k]:
                    salive[k] = False
                elif sty[k] == -1 and l[j] < spx[k]:
                    salive[k] = False
        a3 = atr3_at[j]
        # ---- update open zones with this bar (extreme, confirmations, invalidation)
        if j >= 2:
            p = j - 2
            if p >= 2 and h[p] > h[p - 1] and h[p] > h[p - 2] and h[p] > h[p + 1] and h[p] > h[p + 2]:
                ph = h[p]
            if p >= 2 and l[p] < l[p - 1] and l[p] < l[p - 2] and l[p] < l[p + 1] and l[p] < l[p + 2]:
                pl = l[p]
        eng_l = j > 0 and c[j] > o[j] and c[j - 1] < o[j - 1] and c[j] >= o[j - 1] and o[j] <= c[j - 1]
        eng_s = j > 0 and c[j] < o[j] and c[j - 1] > o[j - 1] and c[j] <= o[j - 1] and o[j] >= c[j - 1]
        for z in range(zc):
            if not z_on[z]:
                continue
            r = z_row[z]; d = z_dir[z]; L = z_L[z]
            if j > z_start[z]:
                if d == 1:
                    z_ext[z] = min(z_ext[z], l[j])
                else:
                    z_ext[z] = max(z_ext[z], h[j])
                if np.isnan(out[r, 5]) and ((d == 1 and eng_l) or (d == -1 and eng_s)):
                    out[r, 5] = j; out[r, 6] = z_ext[z]
                if np.isnan(out[r, 7]) and ((d == 1 and not np.isnan(ph) and c[j] > ph and c[j - 1] <= ph) or
                                            (d == -1 and not np.isnan(pl) and c[j] < pl and c[j - 1] >= pl)):
                    out[r, 7] = j; out[r, 8] = z_ext[z]
            dead = (j - z_start[z] >= K) or (not np.isnan(a3) and ((d == 1 and c[j] < L - 0.25 * a3) or (d == -1 and c[j] > L + 0.25 * a3)))
            if dead or (not np.isnan(out[r, 5]) and not np.isnan(out[r, 7])):
                z_on[z] = False
        # ---- touches of fresh T3 levels -> new zones
        for k in range(m):
            if not (alive[k] and fresh[k]):
                continue
            L = px[k]
            if kind[k] == -1 and l[j] <= L:
                d = 1
            elif kind[k] == 1 and h[j] >= L:
                d = -1
            else:
                continue
            fresh[k] = False
            r = no; no += 1
            out[r, 0] = d; out[r, 1] = L; out[r, 2] = j; out[r, 9] = a3; out[r, 11] = miss[k]; out[r, 12] = j - born[k]
            if (d == 1 and c[j] >= L) or (d == -1 and c[j] <= L):
                out[r, 3] = j; out[r, 4] = l[j] if d == 1 else h[j]
            if (d == 1 and eng_l) or (d == -1 and eng_s):
                out[r, 5] = j; out[r, 6] = l[j] if d == 1 else h[j]
            if (d == 1 and not np.isnan(ph) and c[j] > ph and j > 0 and c[j - 1] <= ph) or \
               (d == -1 and not np.isnan(pl) and c[j] < pl and j > 0 and c[j - 1] >= pl):
                out[r, 7] = j; out[r, 8] = l[j] if d == 1 else h[j]
            liq = 0
            if not np.isnan(a3):
                for q in range(sm):
                    if salive[q] and sty[q] == -d:
                        if d == 1 and spx[q] >= L - a3 and spx[q] <= L + 0.25 * a3:
                            liq += 1
                        if d == -1 and spx[q] <= L + a3 and spx[q] >= L - 0.25 * a3:
                            liq += 1
            out[r, 10] = liq
            for z in range(zc):
                if not z_on[z]:
                    z_on[z] = True; z_row[z] = r; z_dir[z] = d; z_L[z] = L; z_start[z] = j
                    z_ext[z] = l[j] if d == 1 else h[j]
                    break
        # ---- T3 close: body breaks (flip once, then dead), misses, pruning
        if not np.isnan(t3c_at[j]):
            C = t3c_at[j]; H = t3h_at[j]; Lo = t3l_at[j]
            for k in range(m):
                if not alive[k]:
                    continue
                L = px[k]
                if not np.isnan(a3) and abs(C - L) > prune_atr * a3:
                    alive[k] = False; continue
                if kind[k] == 1:
                    if C > L:
                        if flips[k] >= 1:
                            alive[k] = False
                        else:
                            kind[k] = -1; fresh[k] = True; flips[k] += 1
                    elif fresh[k] and not np.isnan(a3) and H < L and H >= L - 0.5 * a3:
                        miss[k] += 1
                else:
                    if C < L:
                        if flips[k] >= 1:
                            alive[k] = False
                        else:
                            kind[k] = 1; fresh[k] = True; flips[k] += 1
                    elif fresh[k] and not np.isnan(a3) and Lo > L and Lo <= L + 0.5 * a3:
                        miss[k] += 1
            # compact dead levels / swept swings
            if m > 4000:
                w = 0
                for k in range(m):
                    if alive[k]:
                        px[w] = px[k]; kind[w] = kind[k]; fresh[w] = fresh[k]; alive[w] = True
                        flips[w] = flips[k]; miss[w] = miss[k]; born[w] = born[k]; w += 1
                m = w
            if sm > 4000:
                w = 0
                for k in range(sm):
                    if salive[k] and (np.isnan(a3) or abs(spx[k] - C) < prune_atr * a3):
                        spx[w] = spx[k]; sty[w] = sty[k]; salive[w] = True; w += 1
                sm = w
    return out[:no]


# ------------------------------------------------------------------ simulation of chosen setups
@njit(cache=True)
def sim_setups(o, h, l, c, atr4, S, keep, conf, stop_mode, tgt_mode, tgt_r, story_tgt, rb_lvl, rb_on,
               eabs, epct, tabs, tpct, sabs, spct, carry, bar_h, buf, limit_eps):
    """conf: 0 rej, 1 eng, 2 bos, 3 either(eng/bos earliest), 4 limit at level (touch fill).
    stop_mode: 0 zone (beyond level & zone extreme + buf*ATR3), 1 LTF wick (+buf*ATR4).
    tgt_mode: 0 fixed tgt_r R, 1 storyline end (>= tgt_r R else skip), 2 roadblock T2 (>= tgt_r R else skip).
    rb_on: skip if an opposing fresh T2 level lies closer than tgt_r R (roadblock in the way).
    Returns trades: sig_j, entry_j, exit_j, dir, E, S, R, grossR, costR, risk_atr4, tgtR, kind, setup_row"""
    n = len(c); ns = S.shape[0]
    ent = np.full(ns, -1, np.int64); cj = np.full(ns, -1, np.int64); ext = np.full(ns, np.nan)
    for i in range(ns):
        if not keep[i]:
            continue
        if conf == 0:
            if not np.isnan(S[i, 3]):
                cj[i] = int(S[i, 3]); ext[i] = S[i, 4]
        elif conf == 1:
            if not np.isnan(S[i, 5]):
                cj[i] = int(S[i, 5]); ext[i] = S[i, 6]
        elif conf == 2:
            if not np.isnan(S[i, 7]):
                cj[i] = int(S[i, 7]); ext[i] = S[i, 8]
        elif conf == 3:
            a = S[i, 5]; b = S[i, 7]
            if not np.isnan(a) and (np.isnan(b) or a <= b):
                cj[i] = int(a); ext[i] = S[i, 6]
            elif not np.isnan(b):
                cj[i] = int(b); ext[i] = S[i, 8]
        else:
            cj[i] = int(S[i, 2]); ext[i] = S[i, 1]
        if cj[i] >= 0:
            ent[i] = cj[i] if conf == 4 else cj[i] + 1
    order = np.argsort(ent)
    out = np.zeros((ns, 13)); m = 0; busy = -1
    for q in range(ns):
        i = order[q]
        if ent[i] < 0 or ent[i] >= n - 1 or ent[i] <= busy:
            continue
        d = int(S[i, 0]); L = S[i, 1]; a3 = S[i, 9]; j = cj[i]; k0 = ent[i]
        if np.isnan(a3) or np.isnan(atr4[j]):
            continue
        if conf == 4:
            if d == 1:
                if not (l[j] <= L - limit_eps * atr4[j]):
                    continue
                E = min(L, o[j])
            else:
                if not (h[j] >= L + limit_eps * atr4[j]):
                    continue
                E = max(L, o[j])
            Sx = L - d * 0.5 * a3
        else:
            E = o[k0]
            if stop_mode == 0:
                Sx = (min(L, ext[i]) - buf * a3) if d == 1 else (max(L, ext[i]) + buf * a3)
            else:
                Sx = (l[j] - buf * atr4[j]) if d == 1 else (h[j] + buf * atr4[j])
        R = d * (E - Sx)
        if R <= 0 or R < 0.0005 * E:
            continue
        if tgt_mode == 0:
            T = E + d * tgt_r * R
        elif tgt_mode == 1:
            T = story_tgt[i]
            if np.isnan(T) or d * (T - E) < tgt_r * R:
                continue
        else:
            T = rb_lvl[i]
            if np.isnan(T) or d * (T - E) < tgt_r * R:
                continue
        if rb_on and not np.isnan(rb_lvl[i]) and d * (rb_lvl[i] - E) < tgt_r * R and d * (rb_lvl[i] - E) > 0:
            continue
        # walk exits (stop first). For limit fills, only the stop can trigger in the fill bar.
        kx = -1; X = 0.0; kind = 0
        start = k0
        if conf == 4:
            if (d == 1 and l[k0] <= Sx) or (d == -1 and h[k0] >= Sx):
                kx = k0; X = Sx
            start = k0 + 1
        if kx < 0:
            for k in range(start, n):
                if (d == 1 and l[k] <= Sx) or (d == -1 and h[k] >= Sx):
                    X = (min(Sx, o[k]) if d == 1 else max(Sx, o[k])) if k > k0 else Sx
                    kx = k; break
                if (d == 1 and h[k] >= T) or (d == -1 and l[k] <= T):
                    X = T; kx = k; kind = 1; break
            if kx < 0:
                kx = n - 1; X = c[n - 1]
        g = d * (X - E) / R
        ea = eabs; ep = epct
        cost = ea + ep * E + ((tabs + tpct * X) if kind == 1 else (sabs + spct * X))
        cost = cost / R + carry * (kx - k0 + 1) * bar_h / 8760.0 * E / R
        out[m, 0] = j; out[m, 1] = k0; out[m, 2] = kx; out[m, 3] = d; out[m, 4] = E; out[m, 5] = Sx; out[m, 6] = R
        out[m, 7] = g; out[m, 8] = cost; out[m, 9] = R / atr4[j]; out[m, 10] = d * (T - E) / R; out[m, 11] = kind; out[m, 12] = i
        m += 1; busy = kx
    return out[:m]
