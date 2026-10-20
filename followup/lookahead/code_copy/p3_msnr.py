"""Phase-3 faithful top-down MSNR study. Usage:
  python p3_msnr.py A [workers] [cells]   # pre-holdout only (holdout data never loaded)
  python p3_msnr.py B [workers]           # final holdout (last 365 days), frozen candidates only
Checkpoints: results/A3/<cell>.* and results/B3/<cell>.* (cells already done are skipped)."""
import sys, os, json, time, itertools, math, zlib
from pathlib import Path
import numpy as np, pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead/code_copy")
import p3common as C
import msnr, engine2 as E2, indicators as IND, topdown as TD
from p2_phaseA import rc_spa, dsr

RES = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead/scratch/p3"); A3 = RES / "A3"; B3 = RES / "B3"
NF = 5; HOLD = pd.Timedelta(days=365)
STORY = {"td": 0, "simple": 1, "none": 2}
CONF = {"rej": 0, "eng": 1, "bos": 2, "either": 3, "limit": 4}
TGT = [("2R", 0, 2.0), ("3R", 0, 3.0), ("4R", 0, 4.0), ("storyEnd", 1, 2.0), ("roadblock", 2, 2.0)]
EXTRA_F = ["sweep", "macd_turn", "atrpct_hi", "ema200", "vwap_trend"]
CANON = dict(depth=3, gaps=0, story="td", conf="either", stop="zone", tgt="3R", rb=1, liq=0, miss=0, sess=0, xf="")


def cname(c):
    return "|".join(f"{k}={c[k]}" for k in ("depth", "gaps", "story", "conf", "stop", "tgt", "rb", "liq", "miss", "sess", "xf"))


def asof(src_end, dst_end, vals):
    idx = np.searchsorted(src_end, dst_end, side="right") - 1
    v = np.asarray(vals)
    out = np.where(idx >= 0, v[np.clip(idx, 0, None)], np.nan if v.dtype.kind == "f" else 0)
    return out


def exact_at(src_end, dst_end, vals):
    """value of src bar whose end == dst bar end, NaN otherwise."""
    pos = np.searchsorted(src_end, dst_end, side="left")
    ok = (pos < len(src_end)) & (src_end[np.clip(pos, 0, len(src_end) - 1)] == dst_end)
    out = np.full(len(dst_end), np.nan)
    out[ok] = np.asarray(vals, float)[pos[ok]]
    return out


def gap_events(b):
    o, c = b.open.to_numpy(), b.close.to_numpy(); end = b.end.to_numpy()
    bull = c > o; bear = c < o
    i = np.arange(1, len(c))
    up = bull[1:] & bull[:-1] & (o[1:] > c[:-1]); dn = bear[1:] & bear[:-1] & (o[1:] < c[:-1])
    rows = [pd.DataFrame({"avail": end[i[up]], "price": c[:-1][up], "kind": -1, "src": 0}),
            pd.DataFrame({"avail": end[i[dn]], "price": c[:-1][dn], "kind": 1, "src": 0})]
    return pd.concat(rows, ignore_index=True)


class Cell3:
    def __init__(self, asset, ladder, phase):
        self.asset, self.ladder = asset, ladder
        spec = C.ASSETS[asset]; self.cost = spec["cost"]; self.gapsok = spec["gaps"]
        base = C.load_base(asset)
        self.hold_start = base.index[-1] - HOLD
        if phase == "A":
            base = base[base.index < self.hold_start]
        T1, T2, T3, T4 = C.LADDERS[ladder]
        sh = spec["shift_h"]
        b1, b2, b3, b4 = (C.bars(base, t, sh) for t in (T1, T2, T3, T4))
        del base
        self.b4 = b4; self.bar_h = C.TF_MIN[T4] / 60.0
        o, h, l, c = (b4[k].to_numpy() for k in ("open", "high", "low", "close"))
        self.o, self.h, self.l, self.c = o, h, l, c
        self.a4 = msnr.atr(b4); self.n = len(b4)
        e1, e2, e3, e4 = (x.end.to_numpy() for x in (b1, b2, b3, b4))
        # ---- T1 rejections -> T2 storyline
        o1, h1, l1, c1 = (b1[k].to_numpy() for k in ("open", "high", "low", "close"))
        ev1 = msnr.map_events_to_bars(msnr.level_events(b1, include_qm=False), b1)
        s1, _, _, _, nr1, ns1 = msnr.run_levels(o1, h1, l1, c1, *ev1, 1)
        ext1 = np.where(s1 == 1, l1, np.where(s1 == -1, h1, np.nan)); tg1 = np.where(s1 == 1, nr1, np.where(s1 == -1, ns1, np.nan))
        h2, l2, c2 = b2.high.to_numpy(), b2.low.to_numpy(), b2.close.to_numpy()
        sig_at2 = np.nan_to_num(exact_at(e1, e2, s1)).astype(np.int64)
        ext_at2 = exact_at(e1, e2, ext1); tg_at2 = exact_at(e1, e2, tg1)
        sh2, sl2 = TD.wick_swings(h2, l2, 2)
        W2 = int(2 * C.TF_MIN[T1] / C.TF_MIN[T2])
        st2, stg2 = TD.topdown_story(len(b2), exact_at(e1, e2, c1), sig_at2, ext_at2, tg_at2, h2, l2, c2, sh2, sl2, W2)
        self.story_td = asof(e2, e4, st2).astype(np.int64); self.story_tgt = asof(e2, e4, stg2)
        self.story_simple = asof(e1, e4, msnr.storyline(b1)).astype(np.int64)
        # ---- T2 roadblocks (nearest fresh opposing T2 level)
        o2 = b2.open.to_numpy()
        ev2 = msnr.map_events_to_bars(msnr.level_events(b2, include_qm=False), b2)
        _, _, _, _, nr2, ns2 = msnr.run_levels(o2, h2, l2, c2, *ev2, 1)
        self.rb_res = asof(e2, e4, nr2); self.rb_sup = asof(e2, e4, ns2)
        # ---- T3 info at T4 resolution
        a3 = msnr.atr(b3)
        self.atr3_at = asof(e3, e4, a3)
        self.t3c = exact_at(e3, e4, b3.close.to_numpy()); self.t3h = exact_at(e3, e4, b3.high.to_numpy()); self.t3l = exact_at(e3, e4, b3.low.to_numpy())
        cf, spx, sty = TD.swing_events(b3.high.to_numpy(), b3.low.to_numpy(), 2)
        sev = pd.DataFrame({"avail": e3[cf], "price": spx, "kind": sty, "src": 0})
        sj, sp, sk, _ = msnr.map_events_to_bars(sev, b4)
        self.sw = (sj, sp, sk)
        self.K = int(3 * C.TF_MIN[T3] / C.TF_MIN[T4])
        self.b3 = b3
        # ---- indicators on T4 (phase-2 code) for extra confluences
        F, _, _, _ = IND.build(b4, asset, asset.endswith("USDT"), {})
        self.XF = {k: F[k] for k in EXTRA_F if k in F}
        hr = b4.end.dt.hour.to_numpy(); self.sess = ((hr >= 7) & (hr <= 11)) | ((hr >= 12) & (hr <= 17))
        self.setups = {}
        self.edges = np.linspace(260, self.n, NF + 1).astype(int)
        self.days = ((b4.end - b4.end.iloc[0]).dt.total_seconds() // 86400).astype(int).to_numpy()

    def get_setups(self, depth, gaps):
        key = (depth, gaps)
        if key not in self.setups:
            ev = msnr.level_events(self.b3, include_qm=False, av_depth=depth)
            if gaps:
                ev = pd.concat([ev, gap_events(self.b3)], ignore_index=True).sort_values("avail", kind="stable")
            ej, ep, ek, _ = msnr.map_events_to_bars(ev, self.b4)
            S = TD.gen_setups(self.o, self.h, self.l, self.c, self.a4, self.atr3_at, self.t3c, self.t3h, self.t3l,
                              ej, ep, ek, *self.sw, self.K, 50.0)
            jt = S[:, 2].astype(int) if len(S) else np.zeros(0, int)
            d = S[:, 0] if len(S) else np.zeros(0)
            feats = dict(td=self.story_td[jt], simple=self.story_simple[jt], tgt=self.story_tgt[jt],
                         rb=np.where(d == 1, self.rb_res[jt], self.rb_sup[jt]))
            self.setups[key] = (S, feats)
        return self.setups[key]

    def conf_j(self, S, conf):
        if conf == "rej":
            return S[:, 3]
        if conf == "eng":
            return S[:, 5]
        if conf == "bos":
            return S[:, 7]
        if conf == "either":
            return np.fmin(S[:, 5], S[:, 7])
        return S[:, 2]

    def trades(self, cf, j_lo=None, j_hi=None):
        S, f = self.get_setups(cf["depth"], cf["gaps"])
        if len(S) == 0:
            return np.zeros((0, 13))
        d = S[:, 0]
        keep = np.ones(len(S), bool)
        if cf["story"] != "none":
            keep &= f[cf["story"]] == d
        if cf["liq"]:
            keep &= S[:, 10] >= 1
        if cf["miss"]:
            keep &= S[:, 11] >= 1
        cj = self.conf_j(S, cf["conf"])
        okc = ~np.isnan(cj); cji = np.where(okc, cj, 0).astype(int)
        if cf["sess"]:
            keep &= okc & self.sess[cji]
        if cf["xf"]:
            L, Sx = self.XF[cf["xf"]]
            keep &= okc & np.where(d == 1, np.asarray(L)[cji], np.asarray(Sx)[cji])
        lo = 260 if j_lo is None else j_lo; hi = self.n if j_hi is None else j_hi
        keep &= okc & (cj >= lo) & (cj < hi)
        tname, tm, tr_ = dict((t[0], t) for t in TGT)[cf["tgt"]]
        cs = self.cost; lim = cf["conf"] == "limit"
        return TD.sim_setups(self.o, self.h, self.l, self.c, self.a4, S, keep, CONF[cf["conf"]], 0 if cf["stop"] == "zone" else 1,
                             tm, tr_, f["tgt"], f["rb"], bool(cf["rb"]),
                             cs["l_eabs"] if lim else cs["m_eabs"], cs["l_epct"] if lim else cs["m_epct"], cs["tabs"], cs["tpct"],
                             cs["sabs"], cs["spct"], cs["carry"], self.bar_h, 0.1, 0.05)

    def random(self, cf, tr, lo, hi, reps=200, seed=1):
        if len(tr) < 5:
            return np.array([np.nan]), np.array([np.nan])
        if len(tr) > 3000:
            reps = 60
        dirs = {"td": self.story_td, "simple": self.story_simple}.get(cf["story"])
        use = 0 if dirs is None else 1
        dirs = np.zeros(self.n, np.int64) if dirs is None else dirs.astype(np.int64)
        cs = self.cost; lim = cf["conf"] == "limit"
        return E2.random_baseline2(self.o, self.h, self.l, self.c, self.a4, dirs, use, lo, hi, len(tr), tr[:, 9].copy(), tr[:, 10].copy(),
                                   0, 2.0, 0.0, cs["l_eabs"] if lim else cs["m_eabs"], cs["l_epct"] if lim else cs["m_epct"],
                                   cs["tabs"], cs["tpct"], cs["sabs"], cs["spct"], cs["carry"], self.bar_h, reps, seed)


def all_configs(gapsok):
    out = []
    for depth in (3, 2):
        for gaps in ((0, 1) if gapsok else (0,)):
            for story, conf, tgt, rb, liq, miss, sess in itertools.product(STORY, CONF, [t[0] for t in TGT], (0, 1), (0, 1), (0, 1), (0, 1)):
                for stop in (("zone", "ltf") if conf != "limit" else ("lvl",)):
                    out.append(dict(depth=depth, gaps=gaps, story=story, conf=conf, stop=stop, tgt=tgt, rb=rb, liq=liq, miss=miss, sess=sess, xf=""))
            for xf, story, conf, tgt in itertools.product(EXTRA_F, STORY, ("either", "eng", "bos"), ("2R", "3R")):
                out.append(dict(depth=depth, gaps=gaps, story=story, conf=conf, stop="zone", tgt=tgt, rb=1, liq=0, miss=0, sess=0, xf=xf))
    return out


def stats_row(tr, cell, e):
    net = tr[:, 7] - tr[:, 8] if len(tr) else np.zeros(0)
    fold = np.clip(np.searchsorted(e, tr[:, 1], side="right") - 1, 0, NF - 1) if len(tr) else np.zeros(0, int)
    r = {}
    for k in range(NF):
        mk = fold == k; r[f"n{k}"] = int(mk.sum()); r[f"s{k}"] = float(net[mk].sum())
    wf = fold >= 1; x = net[wf]
    r["wf_n"] = int(len(x)); r["wf_netR"] = float(x.mean()) if len(x) else np.nan
    r["wf_grossR"] = float(tr[wf, 7].mean()) if len(x) else np.nan
    w, lo = x[x > 0].sum(), -x[x < 0].sum(); r["wf_PF"] = float(w / lo) if lo > 0 else np.nan
    r["wf_win"] = float((x > 0).mean()) if len(x) else np.nan
    from p2common import tstat_p
    t, p = tstat_p(x); r["wf_t"] = t; r["wf_p"] = p
    if len(x) > 2 and x.std() > 0:
        r["sr_trade"] = float(x.mean() / x.std(ddof=1)); r["skew"] = float(pd.Series(x).skew()); r["kurt"] = float(pd.Series(x).kurt() + 3)
    else:
        r["sr_trade"] = np.nan; r["skew"] = 0.0; r["kurt"] = 3.0
    return r, net, wf, fold


def eq_stats(tr, cell):
    from p2common import equity_stats
    class _B: pass
    b = _B(); b.bars = cell.b4
    return equity_stats(tr, b)


def run_A(asset, ladder):
    tag = f"{asset}_{ladder}"
    if (A3 / f"{tag}.csv").exists():
        return tag, "cached"
    t0 = time.time()
    cell = Cell3(asset, ladder, "A"); e = cell.edges; wf_lo = e[1]
    d0 = cell.days[wf_lo]; D = int(cell.days[-1] - d0 + 1)
    cfgs = all_configs(cell.gapsok)
    if not asset.endswith("USDT"):
        cfgs = [c for c in cfgs if c["xf"] != "vwap_trend"]
    recs, daily = [], []
    for cf in cfgs:
        tr = cell.trades(cf)
        r, net, wf, fold = stats_row(tr, cell, e)
        r.update(asset=asset, ladder=ladder, name=cname(cf), **{k: cf[k] for k in cf})
        dv = np.zeros(D, np.float32)
        if wf.any():
            np.add.at(dv, cell.days[tr[wf, 2].astype(int)] - d0, net[wf].astype(np.float32))
        recs.append(r); daily.append(dv)
    R = pd.DataFrame(recs); X = np.vstack(daily)
    p_rc, p_spa = rc_spa(X[R.wf_n.to_numpy() > 0]); R["cell_p_RC"] = p_rc; R["cell_p_SPA"] = p_spa
    V = np.nanvar(R.loc[R.wf_n >= 30, "sr_trade"].to_numpy()) if (R.wf_n >= 30).sum() > 2 else np.nan
    R["DSR"] = [dsr(a, n, s, k, len(R), V) for a, n, s, k in zip(R["sr_trade"], R["wf_n"], R["skew"], R["kurt"])]
    # walk-forward selection groups
    nk = R[[f"n{k}" for k in range(NF)]].to_numpy(); sk = R[[f"s{k}" for k in range(NF)]].to_numpy()
    canon = cname(dict(CANON))
    groups = {"a_canonical_fixed": (R.name == canon).to_numpy(),
              "a_faithful_selected": (R.xf.fillna("") == "").to_numpy() & (R.story != "none").to_numpy(),
              "a_any_msnr_selected": (R.xf.fillna("") == "").to_numpy(),
              "b_msnr_plus_conf_selected": (R.xf.fillna("") != "").to_numpy()}
    sel = {}
    for g, gm in groups.items():
        tot_n = 0; tot_s = 0.0; picks = []; trs = []; rnd = []
        for k in range(1, NF):
            isn = nk[:, :k].sum(1); iss = sk[:, :k].sum(1)
            sc = np.where(gm & ((isn >= 30) | (g == "a_canonical_fixed")), iss / np.maximum(isn, 1), -np.inf)
            if not np.isfinite(sc.max()):
                picks.append(None); continue
            i = int(np.argmax(sc)); picks.append(R.name.iloc[i]); cf = cfgs[i]
            tr = cell.trades(cf, e[k], e[k + 1]); tot_n += len(tr); tot_s += float((tr[:, 7] - tr[:, 8]).sum()) if len(tr) else 0.0
            if len(tr): trs.append(tr)
            if len(tr) >= 5:
                rn, _ = cell.random(cf, tr, e[k], e[k + 1], 200, 100 + k); rnd.append((len(tr), rn))
        allt = np.vstack(trs) if trs else np.zeros((0, 13))
        if rnd:
            Lm = min(len(r_) for _, r_ in rnd); w = np.array([a for a, _ in rnd], float)
            comb = (np.vstack([r_[:Lm] for _, r_ in rnd]) * w[:, None]).sum(0) / w.sum()
            p_r = (np.sum(comb >= tot_s / max(tot_n, 1)) + 1) / (np.sum(~np.isnan(comb)) + 1); rmean = float(np.nanmean(comb))
        else:
            p_r, rmean = np.nan, np.nan
        isn = nk.sum(1); iss = sk.sum(1)
        fs = np.where(gm & ((isn >= 30) | (g == "a_canonical_fixed")), iss / np.maximum(isn, 1), -np.inf)
        final = R.name.iloc[int(np.argmax(fs))] if np.isfinite(fs.max()) else None
        cg, md, shp = eq_stats(allt, cell) if len(allt) else (np.nan,) * 3
        sel[g] = dict(asset=asset, ladder=ladder, group=g, picks=" ; ".join(map(str, picks)), wf_n=tot_n,
                      wf_netR=tot_s / tot_n if tot_n else np.nan, rand_netR=rmean, p_vs_random=p_r,
                      CAGR=cg, MaxDD=md, Sharpe=shp, final_pick=final)
    # candidates: canonical, finals, top-15 WF (n>=30), plus ablations of canonical (one piece changed)
    cand = set(R.index[R.name == canon]) | set(R.index[R.name.isin([s["final_pick"] for s in sel.values()])])
    cand |= set(R[R.wf_n >= 30].sort_values("wf_netR", ascending=False).index[:15])
    abl = []
    for k, vals in (("story", STORY), ("conf", CONF), ("stop", ("zone", "ltf")), ("tgt", [t[0] for t in TGT]), ("rb", (0, 1)),
                    ("liq", (0, 1)), ("miss", (0, 1)), ("sess", (0, 1)), ("depth", (3, 2)), ("gaps", (0, 1))):
        for v in vals:
            c2 = dict(CANON); c2[k] = v
            if c2["conf"] == "limit":
                c2["stop"] = "lvl"
            abl.append(cname(c2))
    full = dict(CANON, liq=1, miss=1, sess=1); abl.append(cname(full))
    cand |= set(R.index[R.name.isin(abl)])
    R["candidate"] = False; R["ablation"] = R.name.isin(abl); R["full_faithful"] = R.name == cname(full)
    for col in ("rand_netR", "p_vs_random", "CAGR", "MaxDD", "Sharpe"):
        R[col] = np.nan
    for i in cand:
        cf = cfgs[i]; tr = cell.trades(cf, wf_lo, cell.n); R.loc[i, "candidate"] = True
        if len(tr) < 5:
            continue
        rn, _ = cell.random(cf, tr, wf_lo, cell.n, 200, 7 + i)
        R.loc[i, "rand_netR"] = np.nanmean(rn); R.loc[i, "p_vs_random"] = (np.sum(rn >= R.loc[i, "wf_netR"]) + 1) / (np.sum(~np.isnan(rn)) + 1)
        R.loc[i, ["CAGR", "MaxDD", "Sharpe"]] = eq_stats(tr, cell)
    c = cell.c; yrs = (cell.b4.end.iloc[-1] - cell.b4.index[wf_lo]).days / 365.25
    bh = dict(asset=asset, ladder=ladder, wf_start=str(cell.b4.index[wf_lo]), hold_start=str(cell.hold_start),
              BH_CAGR=(c[-1] / cell.o[wf_lo]) ** (1 / yrs) - 1, n_configs=len(R), secs=round(time.time() - t0))
    R.to_csv(A3 / f"{tag}.csv", index=False)
    json.dump({"sel": sel, "bh": bh, "cfgs": {cname(c_): c_ for c_ in [cfgs[i] for i in cand]}}, open(A3 / f"{tag}.json", "w"), default=float, indent=1)
    return tag, len(R), bh["secs"]


def run_B(asset, ladder):
    tag = f"{asset}_{ladder}"
    if (B3 / f"{tag}.csv").exists():
        return tag, "cached"
    meta = json.load(open(A3 / f"{tag}.json")); cfgs = meta["cfgs"]
    cell = Cell3(asset, ladder, "B")
    jH = int(np.searchsorted(cell.b4.index, cell.hold_start, side="left"))
    jW = int(np.searchsorted(cell.b4.index, pd.Timestamp(meta["bh"]["wf_start"]), side="left"))
    rows, curves = [], {}
    picks = {s["final_pick"] for s in meta["sel"].values() if s["final_pick"]}
    for nm, cf in cfgs.items():
        tr = cell.trades(cf, jH, cell.n)
        net = tr[:, 7] - tr[:, 8] if len(tr) else np.zeros(0)
        rn, _ = cell.random(cf, tr, jH, cell.n, 200, 999) if len(tr) >= 5 else (np.array([np.nan]),) * 2
        w, lo = net[net > 0].sum(), -net[net < 0].sum()
        cg, md, shp = eq_stats(tr, cell) if len(tr) else (np.nan,) * 3
        rows.append(dict(asset=asset, ladder=ladder, name=nm, hold_n=len(tr), hold_netR=net.mean() if len(tr) else np.nan,
                         hold_PF=w / lo if lo > 0 else np.nan, hold_CAGR=cg, hold_MaxDD=md, hold_rand_netR=np.nanmean(rn),
                         hold_p_vs_random=(np.sum(rn >= net.mean()) + 1) / (np.sum(~np.isnan(rn)) + 1) if len(tr) >= 5 else np.nan))
        if nm in picks or nm == cname(CANON):
            full = cell.trades(cf, jW, cell.n)
            if len(full):
                np.save(B3 / f"trades_{tag}_{zlib.crc32(nm.encode()) % 10**8}.npy", full)
                np.save(B3 / f"exits_{tag}_{zlib.crc32(nm.encode()) % 10**8}.npy", cell.b4.end.dt.tz_convert(None).to_numpy()[full[:, 2].astype(int)])
                ne = full[:, 7] - full[:, 8]
                curves[nm[:90]] = pd.Series(np.cumsum(ne), index=cell.b4.end.to_numpy()[full[:, 2].astype(int)])
        # regime splits (gold/silver/MCX): full history incl. holdout, labelled
        if not asset.endswith("USDT") and (nm in picks or nm == cname(CANON)):
            full = cell.trades(cf, 260, cell.n)
            t_ex = cell.b4.end.dt.tz_convert(None).to_numpy()[full[:, 1].astype(int)] if len(full) else np.array([], "datetime64[ns]")
            for lab, a_, b_ in (("2009-13", "2009", "2014"), ("2014-19", "2014", "2020"), ("2020+", "2020", "2100")):
                mk = (t_ex >= np.datetime64(a_ + "-01-01")) & (t_ex < np.datetime64(b_ + "-01-01")) if len(full) else np.zeros(0, bool)
                x = (full[mk, 7] - full[mk, 8]) if len(full) else np.zeros(0)
                rows[-1][f"regime_{lab}_n"] = int(mk.sum()); rows[-1][f"regime_{lab}_netR"] = float(x.mean()) if len(x) else np.nan
    c = cell.c[jH:]
    bh = dict(asset=asset, ladder=ladder, hold_start=str(cell.b4.index[jH]), hold_end=str(cell.b4.end.iloc[-1]),
              BH_hold_return=float(c[-1] / cell.o[jH] - 1))
    pd.DataFrame(rows).to_csv(B3 / f"{tag}.csv", index=False)
    json.dump(dict(bh=bh, picks=list(picks)), open(B3 / f"{tag}.json", "w"), default=float)
    if curves:
        pd.DataFrame({k: v.groupby(level=0).last() for k, v in curves.items()}).to_parquet(B3 / f"curves_{tag}.parquet")
    return tag, len(rows)


CELLS = [(a, l) for l in ("W-D-4H-1H", "D-4H-1H-15m", "4H-1H-15m-5m") for a in C.ASSETS]

if __name__ == "__main__":
    assert os.path.exists("D:/"), "D: offline"
    ph = sys.argv[1]; workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    (A3 if ph == "A" else B3).mkdir(parents=True, exist_ok=True)
    cells = CELLS
    if len(sys.argv) > 3:
        cells = [c for c in CELLS if f"{c[0]}_{c[1]}" in sys.argv[3].split(",")]
    fn = run_A if ph == "A" else run_B
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, a, l): (a, l) for a, l in cells}
        for f in as_completed(futs):
            try:
                print("done", f.result(), flush=True)
            except Exception:
                import traceback; print("FAILED", futs[f], traceback.format_exc(), flush=True)
