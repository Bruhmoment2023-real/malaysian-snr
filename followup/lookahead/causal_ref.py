"""Reference (online, strictly causal) versions of the close-pivot storyline, written for the follow-up look-ahead audit.
Shipped msnr._close_pivots keeps ONE list of alternating pivots; when a later pivot of the same type is more extreme it OVERWRITES the earlier entry
(pidx, pcf = p+d, price). The earlier pivot was already confirmed (and usable) at its own pcf, but in the shipped list it disappears until the later one is
confirmed, so the storyline at the bars in between uses information about a pivot that did not exist yet.  Here every accepted pivot is kept as its own
event at its own confirmation bar, which is what a live implementation would have."""
import numpy as np
from numba import njit


@njit(cache=True)
def close_pivot_events_causal(c, d):
    n = len(c)
    ecf = np.empty(n, np.int64); etyp = np.empty(n, np.int64); epx = np.empty(n)
    m = 0; last_typ = 0; last_px = np.nan
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
        if last_typ == typ:
            if (typ == 1 and c[p] > last_px) or (typ == -1 and c[p] < last_px):
                last_px = c[p]
                ecf[m] = p + d; etyp[m] = typ; epx[m] = c[p]; m += 1       # superseding pivot: a NEW event; the old one stays in force until now
            continue
        last_typ = typ; last_px = c[p]
        ecf[m] = p + d; etyp[m] = typ; epx[m] = c[p]; m += 1
    return ecf[:m], etyp[:m], epx[:m]


@njit(cache=True)
def storyline_from_events(c, ecf, etyp, epx):
    n = len(c); out = np.zeros(n, np.int64)
    sh = np.nan; sl = np.nan; trend = 0; q = 0
    for j in range(n):
        while q < len(ecf) and ecf[q] <= j:
            if etyp[q] == 1:
                sh = epx[q]
            else:
                sl = epx[q]
            q += 1
        if not np.isnan(sh) and c[j] > sh:
            trend = 1
        elif not np.isnan(sl) and c[j] < sl:
            trend = -1
        out[j] = trend
    return out


def storyline_causal(df, depth=2):
    c = df.close.to_numpy()
    return storyline_from_events(c, *close_pivot_events_causal(c, depth))
