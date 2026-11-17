"""Re-fetch the public teaching-source pages cited in the paper (one GET each, generic client name, 2 s spacing) and test whether the rule wording the paper relies on is on the page."""
import re, time, hashlib, requests, pandas as pd
UA = {"User-Agent": "academic-research-client/1.0"}
S = [("Vesath MQL5 76993", "https://www.mql5.com/en/code/76993", ["fresh", "close", "resistance"]),
     ("trading-guide TradingView", "https://www.tradingview.com/script/20NljIPT-Malaysian-SnR-Levels/", ["fresh", "A-level|A level|Resistance", "close"]),
     ("DoN_JCT TradingView", "https://www.tradingview.com/script/iWgxW7bW/", ["decision|fresh|level"]),
     ("zacdivan Storyline TradingView", "https://www.tradingview.com/script/zHJLrkfS-Malaysian-SnR-Storyline/", ["storyline"]),
     ("Jithuze Fresh Levels TradingView", "https://www.tradingview.com/script/jYg6YsfN-MSNR-Jithuze-Fresh-Levels/", ["fresh"]),
     ("Crow Investing guide", "https://crowinvesting.com/guides/msnr-trading-explained/", ["fresh", "storyline|story line", "1:2|minimum"]),
     ("SlideShare Malaysian SNR (adamchiu4)", "https://www.slideshare.net/slideshow/8041707456492093639302-malaysian-snr-pdf/279734960", ["liquidity|snr"]),
     ("Scribd Malaysian SNR Strategy", "https://www.scribd.com/presentation/890088095/Malaysian-Snr-Strategy", ["storyline|snr"]),
     ("Scribd KororFX document", "https://www.scribd.com/document/826847580/malaysian-snr-full-document-by-KororFX", ["snr"]),
     ("TikTok @toby.fx1", "https://www.tiktok.com/@toby.fx1/video/7608116772859890962", ["snr|quasimodo"]),
     ("ForexIMF blog", "https://www.foreximf.com/blog/trading/malaysian-snr-trading-benarkah-strategi-ini-bisa-bikin-cuan-gila-gilaan-kupas-tuntas-fakta-mitosnya", ["snr"]),
     ("Chung & Bellotti arXiv", "https://arxiv.org/abs/2101.07410", ["support"])]
rows = []
for name, url, kws in S:
    try:
        r = requests.get(url, headers=UA, timeout=30); txt = re.sub(r"<[^>]+>", " ", r.text).lower(); code = r.status_code
        hits = {k: bool(re.search(k.lower(), txt)) for k in kws}; h = hashlib.sha256(r.content).hexdigest()[:16]
    except Exception as e:
        code, hits, h = f"error: {type(e).__name__}", {}, ""
    rows.append(dict(source=name, url=url, http=code, keywords_found="; ".join(f"{k}={v}" for k, v in hits.items()), sha256_16=h, checked="2026-11-17"))
    print(name, code, hits, flush=True); time.sleep(2)
pd.DataFrame(rows).to_csv(r"D:/Research-Publishing/02-malaysian-snr/rework-v3/results/sources_verification_2026-11-17.csv", index=False)
