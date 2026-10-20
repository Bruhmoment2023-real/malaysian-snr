"""Python figures, VOSviewer exports and caption file for one paper's literature map.

Usage: python figures.py <bibliometrics_dir>
Reads data/clean/{master.csv, citation_edges.csv, cited_references.csv, corpus_final.jsonl.gz}, tables/prisma_counts.csv
Writes figures/py_*.png|svg|html, vosviewer/py_*, tables/py_*.csv, figures/captions.md (merging figures/_captions_R.json)
"""
import itertools, json, math, os, re, subprocess, sys, textwrap
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

B = os.path.abspath(sys.argv[1])
if not os.path.exists("D:\\"):
    sys.exit("D: is missing")
FIG, TAB, VOS = [os.path.join(B, d) for d in ("figures", "tables", "vosviewer")]
for d in (FIG, TAB, VOS):
    os.makedirs(d, exist_ok=True)
cfg = C.jload(os.path.join(B, "config.json"))
M = pd.read_csv(os.path.join(B, "data", "clean", "master.csv"), encoding="utf-8-sig", keep_default_na=False)
for c in ["year", "cited_by_count", "local_citations", "n_refs", "relevance"]:
    M[c] = pd.to_numeric(M[c], errors="coerce").fillna(0)
M["year"] = M.year.astype(int)
E = pd.read_csv(os.path.join(B, "data", "clean", "citation_edges.csv"))
CR = pd.read_csv(os.path.join(B, "data", "clean", "cited_references.csv"), encoding="utf-8-sig", keep_default_na=False)
works = C.jsonl_gz_read(os.path.join(B, "data", "clean", "corpus_final.jsonl.gz"))
N = len(M)
SUB = {k: v["label"] for k, v in cfg["sublits"].items()}
SUB["seed"] = "Seed (named prior work, outside rules)"
PAL = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d"]
COL = {k: PAL[i % len(PAL)] for i, k in enumerate(SUB)}
SRC = f"Corpus: {N} records (OpenAlex metadata). Paper {cfg['paper_id']}."
CAPS = []
byid = M.set_index("oa_id")


def cap(file, title, what, how, caution, tool="Python"):
    CAPS.append(dict(file=file, title=title, what=what, how=how, caution=caution, tool=tool))


def save(fig, name, svg=True):
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=220, bbox_inches="tight", facecolor="white")
    if svg:
        fig.savefig(os.path.join(FIG, name + ".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def surname(a):
    a = (a or "").strip()
    return a.split()[-1] if a else "Anon."


def short_label(r, n=38):
    t = r.title if len(r.title) <= n else r.title[: n - 1] + "\u2026"
    return f"{surname(r.first_author)} ({r.year}) {t}"


def sub_legend(ax, keys=None, **kw):
    keys = keys or [k for k in SUB if k in set(M.sublit)]
    ax.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=COL[k], markersize=9, label=SUB[k]) for k in keys],
              title="Sub-literature", fontsize=8, title_fontsize=9, **kw)


# ---------------------------------------------------------------- 1 PRISMA flow
def fig_prisma():
    p1 = C.jload(os.path.join(B, "data", "clean", "prisma_search.json"), {})
    p2 = C.jload(os.path.join(B, "data", "clean", "prisma_snowball.json"), {})
    hs = pd.read_csv(os.path.join(TAB, "hand_screen_removed.csv")) if os.path.getsize(os.path.join(TAB, "hand_screen_removed.csv")) > 5 else pd.DataFrame()
    exr = p1.get("excluded_reasons", {})
    boxes = [
        ("Records identified by database searches\n" + ", ".join(f"{k}: {v}" for k, v in sorted(p1.get("by_db", {}).items())) + f"\n(total hits = {p1.get('records_identified')})", None),
        (f"Unique records after removing duplicates\nn = {p1.get('unique_records')}", f"Duplicates removed\nn = {p1.get('duplicates_removed_identifiers')}"),
        (f"Passed title pre-screen, looked up in OpenAlex\nn = {p1.get('sent_to_openalex')}", f"Off-topic at title pre-screen\nn = {p1.get('removed_title_prescreen')}"),
        (f"Included after full screen (title + abstract)\nn = {p1.get('included_after_search_screen')}",
         "Removed at full screen\n" + "\n".join(f"{k}: {v}" for k, v in sorted(exr.items(), key=lambda kv: -kv[1])) + f"\nduplicates (same work/title): {p1.get('duplicates_removed_openalex')}"),
        (f"Snowball (1 round, {p2.get('central_papers')} central papers): {p2.get('snowball_screened')} candidates screened\nadded n = {p2.get('snowball_included')} "
         f"(backward {p2.get('backward_included')}, forward {p2.get('forward_included')})",
         f"Snowball candidates not added\nn = {(p2.get('snowball_screened') or 0) - (p2.get('snowball_included') or 0)}"),
        (f"FINAL CORPUS\nn = {N}", f"Removed at hand-screening\nn = {len(hs)}"),
    ]
    fig, ax = plt.subplots(figsize=(11, 10))
    ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, len(boxes) * 2)
    for i, (main, side) in enumerate(boxes):
        y = (len(boxes) - i) * 2 - 1
        ax.add_patch(FancyBboxPatch((0.3, y - 0.62), 5.2, 1.24, boxstyle="round,pad=0.05", fc="#e8f1fa" if i < len(boxes) - 1 else "#cfe8cf", ec="#1d3557"))
        ax.text(2.9, y, "\n".join(textwrap.fill(l, 62) for l in main.split("\n")), ha="center", va="center", fontsize=8.5)
        if side:
            nl = side.count("\n") + 1
            h = max(1.0, 0.24 * nl + 0.3)
            ax.add_patch(FancyBboxPatch((6.2, y - h / 2), 3.6, h, boxstyle="round,pad=0.05", fc="#fdecea", ec="#9b2226"))
            ax.text(8.0, y, side, ha="center", va="center", fontsize=7.5)
            ax.annotate("", xy=(6.15, y), xytext=(5.55, y), arrowprops=dict(arrowstyle="->", color="#9b2226"))
        if i < len(boxes) - 1:
            ax.annotate("", xy=(2.9, y - 1.33), xytext=(2.9, y - 0.68), arrowprops=dict(arrowstyle="->", color="#1d3557"))
    ax.set_title(f"PRISMA-style flow of records - {cfg['paper_id']}\n(searches run {p1.get('date')})", fontweight="bold")
    save(fig, "py_01_prisma_flow")
    cap("py_01_prisma_flow.png", "PRISMA-style flow diagram", "How many records each step of the search, de-duplication, screening and snowballing kept or removed.",
        "Counts logged by python/pipeline.py (tables/prisma_counts.csv); blue = kept, red = removed.",
        "Screening was rule-based (regular expressions on title and abstract) plus one hand pass by an AI agent over titles; it is not a double-blind human screen, so treat the corpus as a map, not a systematic review.")


# ---------------------------------------------------------------- 2 year x sub-literature
def fig_year_sub():
    y0 = max(int(M.year.min()), int(M.year.quantile(0.02)))
    d = M[M.year >= y0].groupby(["year", "sublit"]).size().unstack(fill_value=0)
    d = d.reindex(range(y0, int(M.year.max()) + 1), fill_value=0)
    keys = [k for k in SUB if k in d.columns]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 8.5), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
    bot = np.zeros(len(d))
    for k in keys:
        a1.bar(d.index, d[k], bottom=bot, color=COL[k], label=SUB[k], width=0.85)
        bot += d[k].values
    a1.set_ylabel("Documents in corpus"); a1.legend(title="Sub-literature", fontsize=8, loc="upper left")
    a1.set_title(f"Publications by year and sub-literature\n{SRC} Years before {y0} omitted from the plot ({int((M.year < y0).sum())} records).", fontweight="bold", loc="left", fontsize=11)
    sh = d[keys].div(d[keys].sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
    a2.stackplot(sh.index, [sh[k] * 100 for k in keys], colors=[COL[k] for k in keys])
    a2.set_ylabel("Share of year's documents (%)"); a2.set_xlabel("Publication year"); a2.set_ylim(0, 100)
    for a in (a1, a2):
        a.grid(axis="y", alpha=0.3); a.spines[["top", "right"]].set_visible(False)
    save(fig, "py_02_year_by_subliterature")
    d.to_csv(os.path.join(TAB, "py_year_by_subliterature.csv"))
    cap("py_02_year_by_subliterature.png", "Publications by year and sub-literature", "Top: stacked count of corpus documents per year by sub-literature. Bottom: each sub-literature's share of that year's documents.",
        "master.csv; sub-literature = first inclusion rule matched. matplotlib.", "The mix depends on how many queries each sub-literature had and on the per-query caps; the latest year is incomplete.")


# ---------------------------------------------------------------- 3 timeline of key papers
def fig_timeline():
    d = M.sort_values(["local_citations", "cited_by_count"], ascending=False).head(28).sort_values("year").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(13, 9))
    for i, r in d.iterrows():
        y = len(d) - i
        ax.scatter(r.year, y, s=40 + 28 * r.local_citations, color=COL.get(r.sublit, "grey"), edgecolor="black", linewidth=0.5, zorder=3)
        ax.text(r.year + 0.4, y, f"{surname(r.first_author)}{' et al.' if r.n_authors > 1 else ''} ({r.year}) {r.title[:78]}{'…' if len(r.title) > 78 else ''}  [{int(r.local_citations)} local / {int(r.cited_by_count)} global]",
                va="center", fontsize=7.2)
    ax.set_yticks([]); ax.set_xlabel("Publication year"); ax.set_ylabel("Key papers, ordered by year (oldest at top)")
    ax.set_xlim(d.year.min() - 1, d.year.max() + (d.year.max() - d.year.min()) * 1.15 + 12)
    ax.grid(axis="x", alpha=0.3); ax.spines[["top", "right", "left"]].set_visible(False)
    sub_legend(ax, keys=[k for k in SUB if k in set(d.sublit)], loc="lower left")
    ax.set_title(f"Timeline of the field's key papers (28 most locally cited corpus documents)\n{SRC} Point size = citations received from other corpus documents.", fontweight="bold", loc="left", fontsize=11)
    save(fig, "py_03_timeline_key_papers")
    d[["oa_id", "doi", "first_author", "year", "title", "source", "sublit", "local_citations", "cited_by_count"]].to_csv(os.path.join(TAB, "py_key_papers_timeline.csv"), index=False, encoding="utf-8-sig")
    cap("py_03_timeline_key_papers.png", "Timeline of key papers", "The 28 corpus documents most cited by other corpus documents, in order of publication, coloured by sub-literature.",
        "Local citations from exact OpenAlex reference matching (citation_edges.csv); ties broken by global citations.",
        "Recent papers have had little time to be cited, so the list under-represents work from the last two or three years - which for fast-moving topics is where the key papers are.")


# ---------------------------------------------------------------- 4 direct citation network (interactive + static) and VOSviewer export
def build_graph():
    G = nx.DiGraph()
    for r in M.itertuples():
        G.add_node(r.oa_id, year=int(r.year), sublit=r.sublit)
    for a, b in E.itertuples(index=False):
        if a in G and b in G and a != b:
            G.add_edge(b, a)          # edge runs cited -> citing (direction of knowledge flow)
    return G


def fig_citation_network(G):
    deg = dict(G.degree())
    keep = [n for n, k in sorted(deg.items(), key=lambda kv: -kv[1]) if k > 0][:350]
    H = G.subgraph(keep).copy()
    iso = sum(1 for n in G if deg[n] == 0)
    # VOSviewer export of the full linked network
    ids = {n: i + 1 for i, n in enumerate([n for n in G if deg[n] > 0])}
    with open(os.path.join(VOS, "py_direct_citation_map.txt"), "w", encoding="utf-8") as f:
        f.write("id\tlabel\tdescription\turl\tcluster\tweight<Local citations>\tweight<Global citations>\tscore<Pub. year>\n")
        subs = list(SUB)
        for n, i in ids.items():
            r = byid.loc[n]
            f.write(f"{i}\t{surname(r.first_author).lower()} ({r.year})\t{r.title.replace(chr(9), ' ')}\t{'https://doi.org/' + r.doi if r.doi else 'https://openalex.org/' + n}\t"
                    f"{subs.index(r.sublit) + 1 if r.sublit in subs else len(subs)}\t{int(r.local_citations)}\t{int(r.cited_by_count)}\t{r.year}\n")
    with open(os.path.join(VOS, "py_direct_citation_network.txt"), "w", encoding="utf-8") as f:
        for u, v in G.edges():
            f.write(f"{ids[u]}\t{ids[v]}\t1\n")
    # static
    und = H.to_undirected()
    comp = max(nx.connected_components(und), key=len) if len(und) else set()
    pos = nx.spring_layout(und, k=1.6 / math.sqrt(max(1, len(und))), seed=7, iterations=120)
    fig, ax = plt.subplots(figsize=(13, 11))
    nx.draw_networkx_edges(und, pos, ax=ax, alpha=0.15, width=0.5, edge_color="#555555")
    sizes = [25 + 14 * byid.loc[n].local_citations for n in und]
    nx.draw_networkx_nodes(und, pos, ax=ax, node_size=sizes, node_color=[COL.get(byid.loc[n].sublit, "grey") for n in und], edgecolors="white", linewidths=0.4, alpha=0.9)
    top = sorted(und, key=lambda n: -byid.loc[n].local_citations)[:25]
    for n in top:
        r = byid.loc[n]
        ax.text(pos[n][0], pos[n][1], f"{surname(r.first_author)} {r.year}", fontsize=7, ha="center", va="bottom",
                bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.3))
    ax.axis("off"); sub_legend(ax, loc="lower left")
    ax.set_title(f"Direct citation network within the corpus\n{SRC} {len(und)} most connected documents shown; {G.number_of_edges()} citation links in total; "
                 f"{iso} documents have no link to another corpus document.\nNode size = local citations; 25 most cited labelled; layout: Fruchterman-Reingold (positions carry no scale).",
                 fontweight="bold", loc="left", fontsize=10)
    save(fig, "py_04_citation_network", svg=False)
    cap("py_04_citation_network.png", "Direct citation network (static)", "Corpus documents (nodes) joined when one cites the other, coloured by sub-literature; shows whether the sub-literatures cite each other or sit apart.",
        "Exact matches between OpenAlex referenced_works and corpus ids; up to 350 most connected documents; networkx spring layout, seed 7.",
        "Missing links are common for books, working papers and journals without deposited reference lists - an isolated node may be un-indexed rather than uncited.")
    try:
        from pyvis.network import Network
        net = Network(height="820px", width="100%", directed=True, bgcolor="#ffffff", cdn_resources="in_line", notebook=False)
        for n in H:
            r = byid.loc[n]
            net.add_node(n, label=f"{surname(r.first_author)} {r.year}", color=COL.get(r.sublit, "grey"), size=6 + 2.2 * math.sqrt(r.local_citations) * 3,
                         title=f"{r.title}<br>{r.authors[:120]}<br>{r.source} ({r.year})<br>Sub-literature: {SUB.get(r.sublit, r.sublit)}<br>Local citations: {int(r.local_citations)} | Global: {int(r.cited_by_count)}"
                               f"<br>{'https://doi.org/' + r.doi if r.doi else ''}")
        for u, v in H.edges():
            net.add_edge(u, v, color="#bbbbbb", width=0.5)
        net.set_options('{"physics":{"barnesHut":{"gravitationalConstant":-4000,"springLength":110},"stabilization":{"iterations":150}},"edges":{"arrows":{"to":{"enabled":true,"scaleFactor":0.35}},"smooth":false},"interaction":{"hover":true,"tooltipDelay":80}}')
        html = net.generate_html()
        leg = "".join(f'<span style="display:inline-block;width:12px;height:12px;background:{COL[k]};border-radius:6px;margin:0 4px 0 12px"></span>{SUB[k]}' for k in SUB if k in set(M.sublit))
        head = (f'<div style="font-family:Arial;padding:10px 14px"><h3 style="margin:0">Direct citation network - {cfg["paper_id"]}</h3>'
                f'<div style="font-size:13px;margin-top:4px">{SRC} {len(H)} most connected documents. Arrows run from the cited paper to the paper citing it. '
                f'Node size = citations from other corpus documents. Hover for details; drag to rearrange; scroll to zoom.</div><div style="font-size:13px;margin-top:6px"><b>Sub-literature:</b>{leg}</div></div>')
        html = html.replace("<body>", "<body>" + head, 1)
        with open(os.path.join(FIG, "py_04_citation_network.html"), "w", encoding="utf-8") as f:
            f.write(html)
        cap("py_04_citation_network.html", "Direct citation network (interactive)", "The same network as the PNG, interactive: hover a node for title, authors, source, citation counts and DOI.",
            "pyvis / vis.js, self-contained HTML (opens offline in any browser); Barnes-Hut physics layout.", "The layout is a physics simulation and differs on every load; only the links are data.")
    except Exception as e:
        print("pyvis failed:", e)
    # cross sub-literature citation flows
    keys = [k for k in SUB if k in set(M.sublit)]
    fl = pd.DataFrame(0, index=keys, columns=keys)
    for u, v in G.edges():          # u cited, v citing
        fl.loc[byid.loc[v].sublit, byid.loc[u].sublit] += 1
    fl.to_csv(os.path.join(TAB, "py_citation_flows_between_subliteratures.csv"))
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    im = ax.imshow(fl.values, cmap="Blues")
    lab = [textwrap.fill(SUB[k], 24) for k in keys]
    ax.set_xticks(range(len(keys))); ax.set_xticklabels(lab, rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(len(keys))); ax.set_yticklabels(lab, fontsize=8)
    for i in range(len(keys)):
        for j in range(len(keys)):
            ax.text(j, i, int(fl.values[i, j]), ha="center", va="center", color="white" if fl.values[i, j] > fl.values.max() * 0.5 else "black", fontsize=10)
    ax.set_xlabel("Sub-literature of the CITED document"); ax.set_ylabel("Sub-literature of the CITING document")
    fig.colorbar(im, ax=ax, label="Citation links within the corpus")
    ax.set_title(f"Do the sub-literatures cite each other?\n{SRC}", fontweight="bold", loc="left", fontsize=11)
    save(fig, "py_05_citation_flows_between_subliteratures")
    cap("py_05_citation_flows_between_subliteratures.png", "Citation flows between sub-literatures", "Number of within-corpus citation links from documents of one sub-literature (rows) to another (columns). A strong diagonal with weak off-diagonal cells means the sub-literatures are separate conversations.",
        "citation_edges.csv cross-tabulated by the sub-literature of citing and cited document.", "Cell sizes also reflect how many documents each sub-literature has and how well its sources deposit reference lists; compare proportions, not raw counts.")


# ---------------------------------------------------------------- 5 main path (search path count)
def fig_main_path(G):
    D = nx.DiGraph((u, v) for u, v in G.edges() if G.nodes[u]["year"] <= G.nodes[v]["year"])
    while not nx.is_directed_acyclic_graph(D):
        cyc = nx.find_cycle(D)
        D.remove_edge(*cyc[0][:2])
    if D.number_of_edges() < 8:
        print("main path: too few citation links"); return False
    order = list(nx.topological_sort(D))
    nm = {n: (1 if D.in_degree(n) == 0 else 0) for n in D}
    for n in order:
        if D.in_degree(n):
            nm[n] = sum(nm[p] for p in D.predecessors(n))
    npl = {n: (1 if D.out_degree(n) == 0 else 0) for n in D}
    for n in reversed(order):
        if D.out_degree(n):
            npl[n] = sum(npl[s] for s in D.successors(n))
    for u, v in D.edges():
        D[u][v]["spc"] = nm[u] * npl[v]
    # key-route search: start from the top-k SPC links, extend greedily both ways
    k = 8
    top = sorted(D.edges(data="spc"), key=lambda e: -e[2])[:k]
    path_edges = set()
    for u, v, _ in top:
        path_edges.add((u, v))
        a = u
        while D.in_degree(a):
            p = max(D.predecessors(a), key=lambda q: D[q][a]["spc"]); path_edges.add((p, a)); a = p
        b = v
        while D.out_degree(b):
            s = max(D.successors(b), key=lambda q: D[b][q]["spc"]); path_edges.add((b, s)); b = s
    P = nx.DiGraph(list(path_edges))
    rows = []
    for n in P:
        r = byid.loc[n]
        rows.append(dict(oa_id=n, year=r.year, first_author=r.first_author, title=r.title, source=r.source, doi=r.doi, sublit=r.sublit,
                         local_citations=int(r.local_citations), global_citations=int(r.cited_by_count)))
    pd.DataFrame(rows).sort_values("year").to_csv(os.path.join(TAB, "py_main_path_documents.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame([(u, v, D[u][v]["spc"]) for u, v in P.edges()], columns=["cited", "citing", "spc"]).to_csv(os.path.join(TAB, "py_main_path_links.csv"), index=False)
    # layout: x = year, y = spread within year
    ys = defaultdict(list)
    for n in sorted(P, key=lambda n: (G.nodes[n]["year"], -byid.loc[n].local_citations)):
        ys[G.nodes[n]["year"]].append(n)
    pos, slot = {}, 0
    for yv in sorted(ys):
        for j, n in enumerate(ys[yv]):
            pos[n] = (yv + 0.12 * j, slot); slot += 1
    fig, ax = plt.subplots(figsize=(14, max(7, 0.36 * len(P) + 2)))
    mx = max(D[u][v]["spc"] for u, v in P.edges())
    for u, v in P.edges():
        ax.annotate("", xy=pos[v], xytext=pos[u], arrowprops=dict(arrowstyle="->", color="#444", alpha=0.55, lw=0.5 + 2.5 * D[u][v]["spc"] / mx, connectionstyle="arc3,rad=0.12"))
    for n in P:
        r = byid.loc[n]
        ax.scatter(*pos[n], s=70 + 16 * r.local_citations, color=COL.get(r.sublit, "grey"), edgecolor="black", linewidth=0.5, zorder=3)
        ax.text(pos[n][0] + 0.35, pos[n][1], f"{surname(r.first_author)} ({r.year}) {r.title[:70]}{'…' if len(r.title) > 70 else ''}", fontsize=7, va="center")
    xs = [p[0] for p in pos.values()]
    ax.set_xlim(min(xs) - 1, max(xs) + (max(xs) - min(xs)) * 0.9 + 8)
    ax.set_yticks([]); ax.set_xlabel("Publication year"); ax.set_ylabel("Documents on the main path (ordered by year)")
    ax.spines[["top", "right", "left"]].set_visible(False); ax.grid(axis="x", alpha=0.3)
    sub_legend(ax, keys=[k for k in SUB if k in set(byid.loc[list(P)].sublit)], loc="upper left")
    ax.set_title(f"Main path (key-route, top {k} links by search path count) through the direct citation network\n{SRC} {len(P)} documents, {P.number_of_edges()} links. "
                 f"Arrow = cited \u2192 citing; arrow width = search path count (SPC).", fontweight="bold", loc="left", fontsize=10)
    save(fig, "py_06_main_path")
    cap("py_06_main_path.png", "Main path / key-route view", "The chain of papers that the largest number of citation paths run through - a summary of the field's main line of development.",
        f"Search path count (SPC) on the acyclic within-corpus citation network (links against time order removed); key-route search from the {k} highest-SPC links, extended greedily backward and forward (Liu & Lu key-route approach). networkx.",
        "The main path follows the best-connected thread, which is the best-indexed sub-literature; a missing topic may only mean its papers do not cite each other in indexed sources.")
    return True


# ---------------------------------------------------------------- 6 co-citation network of references (python) + VOSviewer export
def fig_cocitation():
    cnt = Counter()
    lists = []
    for w in works:
        rw = sorted(set(C.wid(r) for r in (w.get("referenced_works") or [])))
        if rw:
            lists.append(rw); cnt.update(rw)
    meta = CR.set_index("oa_id")
    topn = [r for r, c in cnt.most_common(400) if r in meta.index and c >= 2][:150]
    if len(topn) < 15:
        print("co-citation: too few shared references"); return False
    ts = set(topn)
    co = Counter()
    for rw in lists:
        s = [r for r in rw if r in ts]
        for a, b in itertools.combinations(s, 2):
            co[(a, b)] += 1
    Gc = nx.Graph()
    for r in topn:
        Gc.add_node(r)
    for (a, b), w_ in co.items():
        Gc.add_edge(a, b, weight=w_)
    comms = nx.community.louvain_communities(Gc, weight="weight", seed=3, resolution=1.0)
    cl = {n: i + 1 for i, c in enumerate(sorted(comms, key=len, reverse=True)) for n in c}
    ids = {n: i + 1 for i, n in enumerate(topn)}
    with open(os.path.join(VOS, "py_cocitation_references_map.txt"), "w", encoding="utf-8") as f:
        f.write("id\tlabel\tdescription\turl\tcluster\tweight<Citations in corpus>\tscore<Pub. year>\n")
        for n in topn:
            r = meta.loc[n]
            f.write(f"{ids[n]}\t{surname(str(r.first_author)).lower()} ({r.year})\t{str(r.title).replace(chr(9), ' ')}\t{'https://doi.org/' + r.doi if r.doi else 'https://openalex.org/' + n}\t{cl[n]}\t{cnt[n]}\t{r.year}\n")
    with open(os.path.join(VOS, "py_cocitation_references_network.txt"), "w", encoding="utf-8") as f:
        for (a, b), w_ in co.items():
            f.write(f"{ids[a]}\t{ids[b]}\t{w_}\n")
    show = topn[:70]
    H = Gc.subgraph(show).copy()
    H.remove_edges_from([(a, b) for a, b, w_ in H.edges(data="weight") if w_ < 2])
    pos = nx.spring_layout(H, weight="weight", k=2.2 / math.sqrt(len(H)), seed=11, iterations=200)
    fig, ax = plt.subplots(figsize=(14, 11))
    ew = [d["weight"] for _, _, d in H.edges(data=True)]
    nx.draw_networkx_edges(H, pos, ax=ax, width=[0.3 + 2.5 * w_ / max(ew) for w_ in ew] if ew else 1, alpha=0.25, edge_color="#444")
    cm = plt.get_cmap("tab10")
    nx.draw_networkx_nodes(H, pos, ax=ax, node_size=[40 + 22 * cnt[n] for n in H], node_color=[cm((cl[n] - 1) % 10) for n in H], edgecolors="white", linewidths=0.5, alpha=0.92)
    for n in H:
        r = meta.loc[n]
        ax.text(pos[n][0], pos[n][1], f"{surname(str(r.first_author))} {r.year}", fontsize=6.8, ha="center", va="center")
    hs = []
    for c in sorted(set(cl[n] for n in H)):
        mem = sorted([n for n in H if cl[n] == c], key=lambda n: -cnt[n])
        r = meta.loc[mem[0]]
        hs.append(Line2D([0], [0], marker="o", color="w", markerfacecolor=cm((c - 1) % 10), markersize=9,
                         label=f"Cluster {c} ({len(mem)}): e.g. {surname(str(r.first_author))} {r.year}, {str(r.title)[:48]}"))
    ax.legend(handles=hs, fontsize=7.5, loc="lower left", title="Louvain clusters (most cited member)", title_fontsize=8.5)
    ax.axis("off")
    ax.set_title(f"Co-citation network of cited references (70 most cited; links with 2+ co-citations)\n{SRC} Node size = number of corpus documents citing the work; "
                 f"edge width = times cited together.", fontweight="bold", loc="left", fontsize=10)
    save(fig, "py_07_cocitation_references", svg=False)
    pd.DataFrame([dict(oa_id=n, cluster=cl[n], citations_in_corpus=cnt[n], first_author=meta.loc[n].first_author, year=meta.loc[n].year, title=meta.loc[n].title,
                       source=meta.loc[n].source, doi=meta.loc[n].doi, in_corpus=meta.loc[n].in_corpus) for n in topn]).sort_values(["cluster", "citations_in_corpus"], ascending=[True, False]).to_csv(
        os.path.join(TAB, "py_cocitation_clusters.csv"), index=False, encoding="utf-8-sig")
    cap("py_07_cocitation_references.png", "Co-citation network of references (Python)", "Works that corpus documents cite together, grouped into Louvain clusters - the intellectual bases of the literature, with readable author-year labels.",
        "Co-citation counts over OpenAlex referenced_works of all corpus records; 150 most cited references clustered (networkx Louvain, seed 3), 70 drawn; spring layout, seed 11. Cluster membership: tables/py_cocitation_clusters.csv.",
        "Cluster boundaries move with the resolution parameter and the 150-reference cut-off; read the clusters as rough schools, not fixed categories.")
    return True


# ---------------------------------------------------------------- 7 geography
def fig_geography():
    import pycountry
    cc = Counter(c for s in M.countries for c in s.split("; ") if c)
    rows = []
    for a2, n in cc.items():
        c = pycountry.countries.get(alpha_2=a2)
        if c:
            rows.append(dict(iso3=c.alpha_3, country=c.name, documents=n))
    d = pd.DataFrame(rows)
    if len(d):
        import plotly.express as px
        f = px.choropleth(d, locations="iso3", color="documents", hover_name="country", color_continuous_scale="Blues",
                          title=f"Where the authors work: documents by author country<br><sup>{SRC} {int((M.countries != '').sum())} records have country data. Hover for counts.</sup>")
        f.update_layout(coloraxis_colorbar=dict(title="Documents"), margin=dict(l=10, r=10, t=70, b=10))
        f.write_html(os.path.join(FIG, "py_08_author_country_map.html"), include_plotlyjs=True)
        cap("py_08_author_country_map.html", "Author-country map (interactive)", "Choropleth of the number of corpus documents with at least one author affiliated in each country.",
            "OpenAlex authorship country codes; plotly choropleth, self-contained HTML.", "Shows where authors are employed, not which countries are studied; records without affiliations (many Indian-journal and legal records) are not on the map.")
    # study settings: countries (and Indian states) named in titles/abstracts
    names = {c.name: c.name for c in pycountry.countries}
    alias = {"United States": ["united states", "u.s.", "usa", "american"], "United Kingdom": ["united kingdom", "britain", "england", "british", "scotland", "wales", r"\buk\b"],
             "India": ["india", "indian"], "China": ["china", "chinese"], "Russian Federation": ["russia"], "Korea, Republic of": ["south korea", "korea"],
             "Viet Nam": ["vietnam"], "Iran, Islamic Republic of": ["iran"], "Tanzania, United Republic of": ["tanzania"], "Türkiye": ["turkey", "turkish"],
             "Italy": ["italy", "italian"], "Germany": ["germany", "german"], "France": ["france", "french"], "Brazil": ["brazil"], "Nigeria": ["nigeria"],
             "Indonesia": ["indonesia"], "Romania": ["romania"], "Sweden": ["sweden", "swedish"], "Netherlands": ["netherlands", "dutch"], "Singapore": ["singapore"],
             "Pakistan": ["pakistan"], "Japan": ["japan", "japanese"], "Mexico": ["mexico", "mexican"], "Spain": ["spain", "spanish"], "Australia": ["australia"],
             "Canada": ["canada", "canadian"], "South Africa": ["south africa"], "Kenya": ["kenya"], "Ghana": ["ghana"], "Bangladesh": ["bangladesh"]}
    pats = {}
    for nm in names:
        if "," in nm or len(nm) < 4 or nm in ("Georgia", "Jersey", "Guinea", "Niger", "Chad", "Oman", "Mali", "Togo"):
            continue
        pats[nm] = [r"\b" + re.escape(nm.lower()) + r"\b"]
    for nm, al in alias.items():
        pats[nm] = [a if a.startswith("\\") else r"\b" + re.escape(a) + r"\b" for a in al]
    txt = (M.title + " . " + M.abstract).str.lower()
    cm_ = {nm: int(txt.str.contains("|".join(p), regex=True).sum()) for nm, p in pats.items()}
    cd = pd.DataFrame([(k, v) for k, v in cm_.items() if v > 0], columns=["country_named", "documents"]).sort_values("documents", ascending=False)
    cd.to_csv(os.path.join(TAB, "py_countries_named_in_text.csv"), index=False, encoding="utf-8-sig")
    states = ["Karnataka", "Tamil Nadu", "Kerala", "Maharashtra", "Bihar", "Uttar Pradesh", "Andhra Pradesh", "Telangana", "Gujarat", "Rajasthan", "Madhya Pradesh", "West Bengal",
              "Odisha", "Punjab", "Haryana", "Delhi", "Assam", "Jharkhand", "Chhattisgarh", "Himachal Pradesh", "Uttarakhand", "Goa", "Jammu and Kashmir", "Manipur", "Tripura"]
    sd = pd.DataFrame([(s, int(txt.str.contains(r"\b" + s.lower() + r"\b", regex=True).sum())) for s in states], columns=["state_named", "documents"])
    sd = sd[sd.documents > 0].sort_values("documents", ascending=False)
    sd.to_csv(os.path.join(TAB, "py_indian_states_named_in_text.csv"), index=False, encoding="utf-8-sig")
    show_states = cfg.get("india_states") and len(sd) >= 3
    fig, axs = plt.subplots(1, 2 if show_states else 1, figsize=(14 if show_states else 9, 7))
    axs = np.atleast_1d(axs)
    t = cd.head(22).iloc[::-1]
    axs[0].barh(t.country_named, t.documents, color="#457b9d")
    for y, v in enumerate(t.documents):
        axs[0].text(v, y, f" {v}", va="center", fontsize=8)
    axs[0].set_xlabel("Documents naming the country in title or abstract"); axs[0].set_ylabel("Country named")
    axs[0].set_title("Countries named in titles/abstracts", fontsize=10, loc="left")
    if show_states:
        t2 = sd.iloc[::-1]
        axs[1].barh(t2.state_named, t2.documents, color="#e76f51")
        for y, v in enumerate(t2.documents):
            axs[1].text(v, y, f" {v}", va="center", fontsize=8)
        axs[1].set_xlabel("Documents naming the state in title or abstract"); axs[1].set_ylabel("Indian state named")
        axs[1].set_title("Indian states named in titles/abstracts", fontsize=10, loc="left")
    for a in axs:
        a.spines[["top", "right"]].set_visible(False); a.grid(axis="x", alpha=0.3)
    fig.suptitle(f"Geography of study settings: places named in titles and abstracts\n{SRC} {int((M.has_abstract.astype(int) == 1).sum())} records have an abstract.", fontweight="bold", x=0.02, ha="left", fontsize=11)
    save(fig, "py_09_places_named_in_text")
    cap("py_09_places_named_in_text.png", "Geography of study settings", "How many corpus documents name each country" + (" (left) and each Indian state (right)" if show_states else "") + " in the title or abstract - a rough proxy for where the evidence comes from.",
        "Case-insensitive name matching (with a few aliases such as 'American', 'British') on title + abstract in master.csv.",
        "A name in an abstract is not the same as a study setting (it can be a comparison or an author address), and India is partly a search term here, so its bar is inflated by design.")


# ---------------------------------------------------------------- 8 database overlap
def fig_db():
    fi = Counter(d for s in M.found_in for d in s.split("; ") if d)
    nm = {"crossref": "Crossref", "s2": "Semantic Scholar", "eric": "ERIC", "arxiv": "arXiv", "seed": "Seed list", "openalex_snowball": "Snowball (OpenAlex refs /\nOpenCitations)", "openalex": "OpenAlex search"}
    combos = Counter(M.found_in)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.5))
    k = sorted(fi, key=lambda x: -fi[x])
    a1.bar([nm.get(x, x) for x in k], [fi[x] for x in k], color="#2a9d8f")
    for i, x in enumerate(k):
        a1.text(i, fi[x], str(fi[x]), ha="center", va="bottom", fontsize=9)
    a1.set_ylabel("Corpus records retrieved by the source"); a1.set_xlabel("Discovery source"); a1.set_title("Records per discovery source (a record can have several)", fontsize=10, loc="left")
    a1.tick_params(axis="x", labelsize=8)
    tc = combos.most_common(8)[::-1]
    a2.barh([" + ".join(nm.get(x, x).replace("\n", " ") for x in c.split("; ")) for c, _ in tc], [v for _, v in tc], color="#8ab17d")
    for i, (_, v) in enumerate(tc):
        a2.text(v, i, f" {v}", va="center", fontsize=8)
    a2.set_xlabel("Corpus records"); a2.set_ylabel("Combination of sources"); a2.set_title("Most common source combinations", fontsize=10, loc="left"); a2.tick_params(axis="y", labelsize=7.5)
    for a in (a1, a2):
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"Which database found the corpus records?\n{SRC}", fontweight="bold", x=0.02, ha="left", fontsize=11)
    fig.tight_layout()
    save(fig, "py_10_database_overlap")
    cap("py_10_database_overlap.png", "Database overlap", "Left: how many final-corpus records each discovery source retrieved. Right: the most common combinations of sources per record.",
        "'found_in' field of master.csv (which searches returned the record before OpenAlex enrichment).",
        "Low overlap is expected: each database was queried with different syntax and per-query caps, so this is not a measure of database quality.")


# ---------------------------------------------------------------- 9 VOSviewer command line (layout + clustering only; it has no image export)
def vos_cli():
    exe = r"D:\Research-Publishing\_tools\VOSviewer\VOSviewer.exe"
    note = ""
    if not os.path.exists(exe):
        return "VOSviewer.exe not found in D:\\Research-Publishing\\_tools\\VOSviewer."
    done = []
    for stem, title in [("py_cocitation_references", "Co-citation of references"), ("keyword_cooccurrence", "Keyword co-occurrence"), ("coauthorship_authors", "Co-authorship (authors)")]:
        mp, nw = os.path.join(VOS, stem + "_map.txt"), os.path.join(VOS, stem + "_network.txt")
        out = os.path.join(VOS, stem + "_voslayout_map.txt")
        if not (os.path.exists(mp) and os.path.exists(nw)):
            continue
        try:
            subprocess.run([exe, "-map", mp, "-network", nw, "-run_layout", "-run_clustering", "-save_map", out], timeout=150, capture_output=True)
        except subprocess.TimeoutExpired:
            note += f"{stem}: VOSviewer command line timed out. "
        except Exception as e:
            note += f"{stem}: {e}. "
        if os.path.exists(out):
            try:
                d = pd.read_csv(out, sep="\t", encoding="utf-8-sig")
                wcol = [c for c in d.columns if c.startswith("weight<")][-1]
                fig, ax = plt.subplots(figsize=(13, 10))
                cm = plt.get_cmap("tab10")
                sc = d[wcol] / d[wcol].max()
                ax.scatter(d.x, d.y, s=30 + 900 * sc, c=[cm((int(c) - 1) % 10) for c in d.cluster], alpha=0.75, edgecolors="white", linewidths=0.5)
                for r in d.sort_values(wcol, ascending=False).head(60).itertuples():
                    ax.text(r.x, r.y, str(r.label)[:28], fontsize=6.5, ha="center", va="center")
                ax.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=cm((int(c) - 1) % 10), markersize=9, label=f"VOS cluster {int(c)} ({int((d.cluster == c).sum())} items)")
                                   for c in sorted(d.cluster.unique())[:10]], fontsize=8, loc="lower left", title="VOSviewer clustering")
                ax.set_xlabel("VOS layout x (arbitrary units)"); ax.set_ylabel("VOS layout y (arbitrary units)")
                ax.set_title(f"{title}: VOSviewer layout and clustering (computed headlessly), drawn with matplotlib\n{SRC} {len(d)} items; point size = {wcol[7:-1].lower()}; 60 largest labelled.",
                             fontweight="bold", loc="left", fontsize=10)
                ax.spines[["top", "right"]].set_visible(False)
                save(fig, f"py_11_vosviewer_{stem.replace('py_', '')}", svg=False)
                cap(f"py_11_vosviewer_{stem.replace('py_', '')}.png", f"{title} - VOSviewer layout", f"{title} map positioned and clustered by VOSviewer 1.6.20 itself (VOS mapping + VOS clustering), then drawn with matplotlib because the VOSviewer command line cannot export images.",
                    f"VOSviewer.exe -map/-network -run_layout -run_clustering -save_map on vosviewer/{stem}_map.txt and _network.txt; default VOSviewer parameters.",
                    "Closeness means relatedness only approximately (a 2-D projection); open the map and network files in the VOSviewer GUI to inspect links and change resolution.", tool="VOSviewer + Python")
                done.append(stem)
            except Exception as e:
                note += f"{stem}: could not draw VOS layout ({e}). "
    return f"VOSviewer command line produced layouts for: {', '.join(done) or 'none'}. {note}"


# ---------------------------------------------------------------- topic-specific chart: coded heat map (config "heatmap")
def fig_heatmap():
    hm = cfg.get("heatmap")
    if not hm:
        return False
    text = (M.title.astype(str) + " . " + M.abstract.astype(str))
    R = {k: re.compile(v, re.I) for k, v in hm["rows"].items()}
    Cc = {k: re.compile(v, re.I) for k, v in hm["cols"].items()}
    rhit = {k: text.apply(lambda t: bool(rx.search(t))) for k, rx in R.items()}
    chit = {k: text.apply(lambda t: bool(rx.search(t))) for k, rx in Cc.items()}
    mat = pd.DataFrame({c: {r: int((rhit[r] & chit[c]).sum()) for r in R} for c in Cc})
    mat["(any row term)"] = [int(rhit[r].sum()) for r in R]
    tot = pd.Series({c: int(chit[c].sum()) for c in Cc}); tot["(any row term)"] = N
    mat.loc["(any column term)"] = tot
    mat.to_csv(os.path.join(TAB, "py_heatmap_counts.csv"), encoding="utf-8-sig")
    body = mat.drop(index="(any column term)").drop(columns="(any row term)")
    body = body.loc[body.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(1.05 * len(Cc) + 5, 0.5 * len(R) + 3.2))
    im = ax.imshow(np.log1p(body.values), cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(body.columns))); ax.set_xticklabels([f"{c} (n={int(mat.loc['(any column term)', c])})" for c in body.columns], rotation=40, ha="right")
    ax.set_yticks(range(len(body.index))); ax.set_yticklabels([f"{r} (n={int(mat.loc[r, '(any row term)'])})" for r in body.index])
    for i in range(body.shape[0]):
        for j in range(body.shape[1]):
            v = int(body.values[i, j])
            ax.text(j, i, v if v else "·", ha="center", va="center", fontsize=8, color="white" if v > body.values.max() * 0.35 else "#222")
    ax.set_xlabel(hm.get("col_title", "Column")); ax.set_ylabel(hm.get("row_title", "Row"))
    ax.set_title(textwrap.fill(hm.get("title", "Coded heat map"), 90), fontweight="bold", fontsize=11)
    cb = fig.colorbar(im, ax=ax, shrink=0.7); cb.set_label("Documents (colour on log scale; number = count)")
    ticks = [t for t in [0, 1, 5, 20, 50, 100, 200, 400] if t <= body.values.max()]
    cb.set_ticks(np.log1p(ticks)); cb.set_ticklabels(ticks)
    fig.text(0.01, -0.2, SRC + " A document is counted in every cell whose row and column terms both occur in its title or abstract.", fontsize=7, color="grey")
    save(fig, "py_heatmap_methods_by_data")
    n_ab = int((M.abstract.astype(str) != "").sum())
    cap("py_heatmap_methods_by_data.png", hm.get("title", "Coded heat map"),
        "Number of corpus documents whose title or abstract mentions both the row term (method/topic) and the column term (market/data).",
        f"{SRC} Coding by the regular expressions in config.json -> heatmap (title + abstract; {n_ab} of {N} documents have an abstract; the rest are coded on the title only). Cells are not exclusive. Counts in tables/py_heatmap_counts.csv.",
        hm.get("caution", "Mention is not design."))


# ---------------------------------------------------------------- run
status = {}
for name, fn in [("prisma", fig_prisma), ("year_sub", fig_year_sub), ("timeline", fig_timeline), ("db", fig_db), ("geography", fig_geography), ("heatmap", fig_heatmap)]:
    try:
        fn(); status[name] = "ok"
    except Exception as e:
        status[name] = f"FAILED: {e!r}"
    print(name, status[name], flush=True)
G = build_graph()
small = N < 50
for name, fn in [("citation_network", lambda: fig_citation_network(G)), ("main_path", lambda: fig_main_path(G)), ("cocitation", fig_cocitation)]:
    if small:
        status[name] = f"SKIPPED: corpus has only {N} documents (< 50)"
    else:
        try:
            r = fn(); status[name] = "ok" if r is not False else "SKIPPED: too few citation links for a meaningful picture"
        except Exception as e:
            status[name] = f"FAILED: {e!r}"
    print(name, status[name], flush=True)
if "--no-vos" in sys.argv or small:
    status["vosviewer_cli"] = "not run"
else:
    try:
        status["vosviewer_cli"] = vos_cli()
    except Exception as e:
        status["vosviewer_cli"] = f"FAILED: {e!r}"
print("vosviewer:", status["vosviewer_cli"])
C.jdump(CAPS, os.path.join(FIG, "_captions_py.json"), indent=1)
C.jdump(status, os.path.join(TAB, "py_figure_log.json"), indent=1)

# ---------------------------------------------------------------- captions.md (R + Python)
allc = (C.jload(os.path.join(FIG, "_captions_R.json"), []) or []) + CAPS
allc = [c for c in allc if os.path.exists(os.path.join(FIG, c["file"]))]
allc.sort(key=lambda c: c["file"].lower())
with open(os.path.join(FIG, "captions.md"), "w", encoding="utf-8") as f:
    f.write(f"# Figure captions - {cfg['paper_id']}\n\n{SRC} Every PNG is 220 dpi; SVG copies exist for the ggplot/matplotlib charts; HTML files are interactive and open offline.\n"
            f"Each entry: what it shows / data and settings / one caution about over-reading it.\n\n")
    for c in allc:
        f.write(f"## {c['file']}\n**{c['title']}** ({c['tool']})\n\n- **Shows:** {c['what']}\n- **Data and settings:** {c['how']}\n- **Caution:** {c['caution']}\n\n")
print(f"captions.md written with {len(allc)} entries")
