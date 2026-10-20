"""Hand-screening support.
  python handscreen.py <dir> dump    -> data/clean/handscreen_titles.tsv (id, year, cites, origin, sub-literature, source, title)
  python handscreen.py <dir> apply   -> merges data/clean/handscreen_exclusions.json ({oa_id: reason}) into config.json manual_exclude
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
B, mode = os.path.abspath(sys.argv[1]), sys.argv[2]
if mode == "dump":
    ws = C.jsonl_gz_read(os.path.join(B, "data", "clean", "corpus_final.jsonl.gz"))
    ws.sort(key=lambda w: (w["_sublits"][0], -(w.get("cited_by_count") or 0)))
    with open(os.path.join(B, "data", "clean", "handscreen_titles.tsv"), "w", encoding="utf-8") as f:
        f.write("oa_id\tyear\tcites\torigin\tsublit\tsource\ttitle\n")
        for w in ws:
            src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
            f.write(f"{C.wid(w['id'])}\t{w.get('publication_year')}\t{w.get('cited_by_count')}\t{w['_origin']}\t{w['_sublits'][0]}\t{src[:40]}\t{(w.get('title') or '').replace(chr(9), ' ')[:160]}\n")
    print(len(ws), "titles dumped")
else:
    ex = C.jload(os.path.join(B, "data", "clean", "handscreen_exclusions.json"), {})
    cfg = C.jload(os.path.join(B, "config.json"))
    ids = {C.wid(w["id"]) for w in C.jsonl_gz_read(os.path.join(B, "data", "clean", "corpus_final.jsonl.gz"))}
    ok = {k: str(v) for k, v in ex.items() if k in ids}
    cfg.setdefault("manual_exclude", {}).update(ok)
    C.jdump(cfg, os.path.join(B, "config.json"), indent=2)
    print(f"{len(ok)} exclusions applied ({len(ex) - len(ok)} ids not in corpus ignored); manual_exclude now {len(cfg['manual_exclude'])}")
