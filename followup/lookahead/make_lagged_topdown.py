"""Builds code_copy/topdown_lag.py from code_copy/topdown.py by 6 exact string replacements inside gen_setups (so the diff is auditable).
The lagged variant is used ONLY for limit-entry (conf == 'limit') configurations. It makes every quantity that a resting limit order could not have known
before the touch bar j opened be read as of the close of bar j-1 instead of bar j:
  * liquidity count (swing points known and not yet swept as of j-1; a swing first confirmed at j, or swept by bar j itself, is treated as j-1 would see it)
  * the T3 ATR that sizes the stop (atr3_at[j-1]).
Everything else (levels, touch detection, fill rule, stop-first rule, exits, costs) is unchanged."""
from pathlib import Path
CC = Path(r"D:/Research-Publishing/02-malaysian-snr/followup/lookahead/code_copy")
t = (CC / "topdown.py").read_text(encoding="utf-8")
rep = [
 ("    ph = np.nan; pl = np.nan          # last confirmed T4 swing high/low (depth 2)\n",
  "    ph = np.nan; pl = np.nan          # last confirmed T4 swing high/low (depth 2)\n    sadd = np.zeros(ns + 1, np.int64); skill = np.full(ns + 1, n + 5, np.int64)   # LAG VARIANT: bar a swing became known / was swept\n"),
 ("            spx[sm] = sw_px[se]; sty[sm] = sw_ty[se]; salive[sm] = True; sm += 1; se += 1\n",
  "            spx[sm] = sw_px[se]; sty[sm] = sw_ty[se]; salive[sm] = True; sadd[sm] = j; skill[sm] = n + 5; sm += 1; se += 1\n"),
 ("                if sty[k] == 1 and h[j] > spx[k]:\n                    salive[k] = False\n                elif sty[k] == -1 and l[j] < spx[k]:\n                    salive[k] = False\n",
  "                if sty[k] == 1 and h[j] > spx[k]:\n                    salive[k] = False; skill[k] = j\n                elif sty[k] == -1 and l[j] < spx[k]:\n                    salive[k] = False; skill[k] = j\n"),
 ("        a3 = atr3_at[j]\n",
  "        a3 = atr3_at[j]\n        a3p = atr3_at[j - 1] if j > 0 else np.nan     # LAG VARIANT: ATR as of the previous bar\n"),
 ("            out[r, 0] = d; out[r, 1] = L; out[r, 2] = j; out[r, 9] = a3;",
  "            out[r, 0] = d; out[r, 1] = L; out[r, 2] = j; out[r, 9] = a3p;"),
 ("            liq = 0\n            if not np.isnan(a3):\n                for q in range(sm):\n                    if salive[q] and sty[q] == -d:\n                        if d == 1 and spx[q] >= L - a3 and spx[q] <= L + 0.25 * a3:\n                            liq += 1\n                        if d == -1 and spx[q] <= L + a3 and spx[q] >= L - 0.25 * a3:\n                            liq += 1\n",
  "            liq = 0\n            if not np.isnan(a3p):\n                for q in range(sm):\n                    if sadd[q] < j and skill[q] >= j and sty[q] == -d:\n                        if d == 1 and spx[q] >= L - a3p and spx[q] <= L + 0.25 * a3p:\n                            liq += 1\n                        if d == -1 and spx[q] <= L + a3p and spx[q] >= L - 0.25 * a3p:\n                            liq += 1\n"),
 ("                    if salive[k] and (np.isnan(a3) or abs(spx[k] - C) < prune_atr * a3):\n                        spx[w] = spx[k]; sty[w] = sty[k]; salive[w] = True; w += 1\n",
  "                    if salive[k] and (np.isnan(a3) or abs(spx[k] - C) < prune_atr * a3):\n                        spx[w] = spx[k]; sty[w] = sty[k]; salive[w] = True; sadd[w] = sadd[k]; skill[w] = skill[k]; w += 1\n"),
]
for old, new in rep:
    assert t.count(old) == 1, old[:60]
    t = t.replace(old, new)
(CC / "topdown_lag.py").write_text(t, encoding="utf-8")
import difflib
d = "".join(difflib.unified_diff((CC / "topdown.py").read_text(encoding="utf-8").splitlines(1), t.splitlines(1), "topdown.py", "topdown_lag.py", n=0))
(CC.parent / "topdown_lag.diff").write_text(d, encoding="utf-8"); print(d)
