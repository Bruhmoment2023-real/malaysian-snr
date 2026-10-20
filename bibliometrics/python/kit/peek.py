"""Hand-screening helper: print corpus titles (random sample / all / by sub-literature). Usage: python peek.py <dir> <stage1|final> [n] [sublit-substring] [seed]"""
import sys, os, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
B, stage = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
sub = sys.argv[4] if len(sys.argv) > 4 else ""
seed = int(sys.argv[5]) if len(sys.argv) > 5 else 1
ws = C.jsonl_gz_read(os.path.join(B, "data", "clean", "corpus_stage1.jsonl.gz" if stage == "stage1" else "corpus_final.jsonl.gz"))
print(len(ws), "records;", collections.Counter(w["_sublits"][0] for w in ws).most_common(), collections.Counter(w.get("type") for w in ws).most_common(8),
      "no-abstract:", sum(1 for w in ws if not w.get("abstract_inverted_index")), "refs>0:", sum(1 for w in ws if w.get("referenced_works")),
      "total refs:", sum(len(w.get("referenced_works") or []) for w in ws))
ws = [w for w in ws if sub in w["_sublits"][0]]
random.seed(seed)
sel = ws if n >= len(ws) else random.sample(ws, n)
for w in sorted(sel, key=lambda w: -(w.get("cited_by_count") or 0)):
    src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    print(f"{C.wid(w['id'])}|{w.get('publication_year')}|{w.get('cited_by_count')}|{w['_sublits'][0][:1]}|{w['_origin'][:6]}|{(w.get('title') or '')[:110]}|{src[:30]}")
