"""Hand-screen of paper 02's corpus (rules applied after reading samples of the titles; every removal and reason is logged).
Writes data/clean/handscreen_exclusions.json, then `python kit/handscreen.py <dir> apply` merges it into config.json manual_exclude."""
import pandas as pd, re, json, os
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
m = pd.read_csv(os.path.join(B, "data/clean/master.csv"), encoding="utf-8-sig", keep_default_na=False)
FIN = re.compile(r"\b(stock|stocks|equit\w*|financ\w*|trad(?:er|ers|ing|e|es)|invest\w*|market|markets|currenc\w*|exchange rates?|portfolio|assets?|prices?|returns?|funds?|bitcoin|crypto\w*|forex|futures|commodit\w*|gold|hedge|bank\w*|securit\w*|sharpe|alpha|bonds?)\b", re.I)
TA = re.compile(r"(technical|moving average|candlestick|backtest|trading|overfit|snooping|reality check|multiple testing|false discover|sharpe|support and resistance|resistance level|support level|round number|smart money|order block)", re.I)
OKF = {"Economics, Econometrics and Finance", "Business, Management and Accounting"}
SOFT = {"Decision Sciences", "Computer Science", "Mathematics", "Physics and Astronomy"}
PROTECT_IDS = {'W2135606128', 'W3123939061', 'W2110065044'}  # White 2000 reality check; Romano-Wolf 2005; Benjamini-Hochberg 1995 (general-statistics classics that the finance snooping literature builds on)
PROTECT = re.compile(r"(technical analysis|technical trading|technical analyses|trading rules?|moving average convergence|\bMACD\b|foreign exchange|exchange dealers|data snooping|trading strateg|stock trading)", re.I)
ex = {}
for r in m.itertuples():
    t, txt = r.title, r.title + " . " + r.abstract
    why = None
    if r.oa_id in PROTECT_IDS or PROTECT.search(t):
        continue
    if r.field not in OKF and not FIN.search(txt): why = "off-topic: non-finance field (%s) and no finance term in title or abstract" % r.field
    elif re.search(r"\bICT\b|information and communication technolog", t) and not re.search(r"trad|stock|forex|smart money|inner circle|market|price", t, re.I): why = "off-topic: ICT = information and communication technology (acronym clash with 'ICT' trading method)"
    elif r.field not in OKF | SOFT and not FIN.search(t): why = "off-topic: non-finance field (%s), no finance term in title" % r.field
    elif r.field in SOFT and not FIN.search(t) and not TA.search(t): why = "off-topic: general data mining / anomaly detection / statistics, no finance or trading-rule term in title"
    elif re.search(r"dairy|price support levels|farm legislation|cannabis|tourism|cockroach|insecticide|acaricide|resistan\w+ (to|in) (pest|insect|drug)", t, re.I): why = "off-topic: agriculture / pests / tourism"
    if why: ex[r.oa_id] = why
json.dump(ex, open(os.path.join(B, "data/clean/handscreen_exclusions.json"), "w", encoding="utf-8"), indent=1)
print(len(ex), "of", len(m)); print(pd.Series(list(ex.values())).str[:60].value_counts().head(8))
