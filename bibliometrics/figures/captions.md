# Figure captions - 02-malaysian-snr

Corpus: 1360 records (OpenAlex metadata). Paper 02-malaysian-snr. Every PNG is 220 dpi; SVG copies exist for the ggplot/matplotlib charts; HTML files are interactive and open offline.
Each entry: what it shows / data and settings / one caution about over-reading it.

## py_01_prisma_flow.png
**PRISMA-style flow diagram** (Python)

- **Shows:** How many records each step of the search, de-duplication, screening and snowballing kept or removed.
- **Data and settings:** Counts logged by python/pipeline.py (tables/prisma_counts.csv); blue = kept, red = removed.
- **Caution:** Screening was rule-based (regular expressions on title and abstract) plus one hand pass by an AI agent over titles; it is not a double-blind human screen, so treat the corpus as a map, not a systematic review.

## py_02_year_by_subliterature.png
**Publications by year and sub-literature** (Python)

- **Shows:** Top: stacked count of corpus documents per year by sub-literature. Bottom: each sub-literature's share of that year's documents.
- **Data and settings:** master.csv; sub-literature = first inclusion rule matched. matplotlib.
- **Caution:** The mix depends on how many queries each sub-literature had and on the per-query caps; the latest year is incomplete.

## py_03_timeline_key_papers.png
**Timeline of key papers** (Python)

- **Shows:** The 28 corpus documents most cited by other corpus documents, in order of publication, coloured by sub-literature.
- **Data and settings:** Local citations from exact OpenAlex reference matching (citation_edges.csv); ties broken by global citations.
- **Caution:** Recent papers have had little time to be cited, so the list under-represents work from the last two or three years - which for fast-moving topics is where the key papers are.

## py_04_citation_network.html
**Direct citation network (interactive)** (Python)

- **Shows:** The same network as the PNG, interactive: hover a node for title, authors, source, citation counts and DOI.
- **Data and settings:** pyvis / vis.js, self-contained HTML (opens offline in any browser); Barnes-Hut physics layout.
- **Caution:** The layout is a physics simulation and differs on every load; only the links are data.

## py_04_citation_network.png
**Direct citation network (static)** (Python)

- **Shows:** Corpus documents (nodes) joined when one cites the other, coloured by sub-literature; shows whether the sub-literatures cite each other or sit apart.
- **Data and settings:** Exact matches between OpenAlex referenced_works and corpus ids; up to 350 most connected documents; networkx spring layout, seed 7.
- **Caution:** Missing links are common for books, working papers and journals without deposited reference lists - an isolated node may be un-indexed rather than uncited.

## py_05_citation_flows_between_subliteratures.png
**Citation flows between sub-literatures** (Python)

- **Shows:** Number of within-corpus citation links from documents of one sub-literature (rows) to another (columns). A strong diagonal with weak off-diagonal cells means the sub-literatures are separate conversations.
- **Data and settings:** citation_edges.csv cross-tabulated by the sub-literature of citing and cited document.
- **Caution:** Cell sizes also reflect how many documents each sub-literature has and how well its sources deposit reference lists; compare proportions, not raw counts.

## py_06_main_path.png
**Main path / key-route view** (Python)

- **Shows:** The chain of papers that the largest number of citation paths run through - a summary of the field's main line of development.
- **Data and settings:** Search path count (SPC) on the acyclic within-corpus citation network (links against time order removed); key-route search from the 8 highest-SPC links, extended greedily backward and forward (Liu & Lu key-route approach). networkx.
- **Caution:** The main path follows the best-connected thread, which is the best-indexed sub-literature; a missing topic may only mean its papers do not cite each other in indexed sources.

## py_07_cocitation_references.png
**Co-citation network of references (Python)** (Python)

- **Shows:** Works that corpus documents cite together, grouped into Louvain clusters - the intellectual bases of the literature, with readable author-year labels.
- **Data and settings:** Co-citation counts over OpenAlex referenced_works of all corpus records; 150 most cited references clustered (networkx Louvain, seed 3), 70 drawn; spring layout, seed 11. Cluster membership: tables/py_cocitation_clusters.csv.
- **Caution:** Cluster boundaries move with the resolution parameter and the 150-reference cut-off; read the clusters as rough schools, not fixed categories.

## py_08_author_country_map.html
**Author-country map (interactive)** (Python)

- **Shows:** Choropleth of the number of corpus documents with at least one author affiliated in each country.
- **Data and settings:** OpenAlex authorship country codes; plotly choropleth, self-contained HTML.
- **Caution:** Shows where authors are employed, not which countries are studied; records without affiliations (many Indian-journal and legal records) are not on the map.

## py_09_places_named_in_text.png
**Geography of study settings** (Python)

- **Shows:** How many corpus documents name each country in the title or abstract - a rough proxy for where the evidence comes from.
- **Data and settings:** Case-insensitive name matching (with a few aliases such as 'American', 'British') on title + abstract in master.csv.
- **Caution:** A name in an abstract is not the same as a study setting (it can be a comparison or an author address), and India is partly a search term here, so its bar is inflated by design.

## py_10_database_overlap.png
**Database overlap** (Python)

- **Shows:** Left: how many final-corpus records each discovery source retrieved. Right: the most common combinations of sources per record.
- **Data and settings:** 'found_in' field of master.csv (which searches returned the record before OpenAlex enrichment).
- **Caution:** Low overlap is expected: each database was queried with different syntax and per-query caps, so this is not a measure of database quality.

## py_heatmap_methods_by_data.png
**Methods against markets: how the technical-analysis and snooping literature is spread (coded from title + abstract)** (Python)

- **Shows:** Number of corpus documents whose title or abstract mentions both the row term (method/topic) and the column term (market/data).
- **Data and settings:** Corpus: 1360 records (OpenAlex metadata). Paper 02-malaysian-snr. Coding by the regular expressions in config.json -> heatmap (title + abstract; 899 of 1360 documents have an abstract; the rest are coded on the title only). Cells are not exclusive. Counts in tables/py_heatmap_counts.csv.
- **Caution:** Mention is not design: a paper that names 'stock' once in its motivation counts the same as one that tests only stocks, and only title and abstract are read. Cells are not exclusive.

## R_01_annual_production.png
**Annual scientific production** (R / bibliometrix)

- **Shows:** Number of corpus documents per publication year, stacked by the sub-literature each record was assigned to.
- **Data and settings:** Counts of PY in the screened corpus; sub-literature = first inclusion rule matched (see search-protocol.md).
- **Caution:** Growth partly reflects database growth and the search design (recent records are better indexed); the last year is incomplete.

## R_02_average_citations_per_year.png
**Average citations per year** (R / bibliometrix)

- **Shows:** Mean OpenAlex citation count of documents published in each year, divided by the years since publication.
- **Data and settings:** TC = OpenAlex cited_by_count at the pull date; citable years = current year - PY + 1.
- **Caution:** Years with few documents (small points) are dominated by one or two highly cited papers; do not read them as trends.

## R_03_most_relevant_sources.png
**Most relevant sources** (R / bibliometrix)

- **Shows:** The 20 journals, book series or repositories contributing most documents to the corpus.
- **Data and settings:** Counts of the OpenAlex primary-location source. Records with no source recorded are listed in the table but left out of the plot.
- **Caution:** Preprint servers (arXiv, SSRN, NBER) rank high because working papers are counted as documents; this is not a journal-quality ranking.

## R_04_bradford_law.png
**Bradford's law** (R / bibliometrix)

- **Shows:** Sources ranked by number of documents (log rank); the shaded zone is Bradford zone 1, the small core of sources that carries about a third of the documents.
- **Data and settings:** bibliometrix::bradford() on the source field (SO).
- **Caution:** With a multi-disciplinary corpus the 'core' is partly an artefact of which sub-literature has the most records.

## R_05_source_dynamics.png
**Source dynamics** (R / bibliometrix)

- **Shows:** Cumulative number of corpus documents over time in the six most frequent sources.
- **Data and settings:** bibliometrix::sourceGrowth(top = 6, cdf = TRUE).
- **Caution:** Small absolute numbers: a difference of two or three papers changes the ordering.

## R_06_most_productive_authors.png
**Most productive authors** (R / bibliometrix)

- **Shows:** Authors with the most documents in the corpus (whole counting).
- **Data and settings:** Author names from OpenAlex authorships, reduced to SURNAME + initials.
- **Caution:** Name disambiguation is imperfect: common surnames with the same initials can be merged, and one person can be split across spellings.

## R_07_most_cited_authors.png
**Most cited authors** (R / bibliometrix)

- **Shows:** Authors ranked by the total OpenAlex citations received by their documents in this corpus.
- **Data and settings:** Sum of TC over each author's corpus documents (full credit to every co-author).
- **Caution:** A single famous paper puts all of its co-authors at the top; this is citation to corpus papers only, not career citations.

## R_08_lotka_law.png
**Lotka's law** (R / bibliometrix)

- **Shows:** Share of authors who wrote 1, 2, 3 ... corpus documents, against the theoretical inverse-square distribution.
- **Data and settings:** bibliometrix::lotka().
- **Caution:** A topical corpus truncates each author's output, so nearly everyone appears once; this describes the corpus, not the authors' careers.

## R_09_author_production_over_time.png
**Author production over time** (R / bibliometrix)

- **Shows:** For the 12 most productive authors: when their corpus documents appeared (point size = number of documents, shade = citations per year).
- **Data and settings:** bibliometrix::authorProdOverTime(k = 12).
- **Caution:** Shows only documents that passed this corpus's inclusion rules.

## R_10_most_relevant_affiliations.png
**Most relevant affiliations** (R / bibliometrix)

- **Shows:** Institutions appearing on the most corpus documents.
- **Data and settings:** OpenAlex institution of each authorship; one count per document per institution.
- **Caution:** OpenAlex affiliation data are missing for many older, book and Indian-journal records, so institutions from well-indexed countries are over-represented.

## R_11_most_relevant_countries.png
**Most relevant countries** (R / bibliometrix)

- **Shows:** Countries of author institutions, counted once per document.
- **Data and settings:** OpenAlex authorship country codes.
- **Caution:** Counts where the authors work, not which country a study is about; records without affiliation data are excluded.

## R_12_corresponding_author_countries.png
**Corresponding author's country** (R / bibliometrix)

- **Shows:** Documents by country of the corresponding (else first) author, split into single-country and multi-country papers.
- **Data and settings:** OpenAlex is_corresponding flag, falling back to the first author; MCP = authors from more than one country.
- **Caution:** The corresponding-author flag is missing for many records, in which case the first author is used.

## R_13_country_collaboration_map.png
**Country production and collaboration map** (R / bibliometrix)

- **Shows:** Shading = documents with an author in the country (log scale); red arcs = pairs of countries that co-authored, thicker = more joint documents.
- **Data and settings:** Author countries from OpenAlex, joined to the 'maps' world polygons; arcs join country bounding-box centres.
- **Caution:** Grey means no author affiliation recorded, not no research; affiliation coverage is weakest for India-published and legal sources.

## R_14_most_global_cited_documents.png
**Most globally cited documents** (R / bibliometrix)

- **Shows:** Corpus documents with the highest total citation counts in OpenAlex.
- **Data and settings:** OpenAlex cited_by_count at the pull date.
- **Caution:** Global citations reward age and breadth: a highly cited paper may be cited mostly for reasons unrelated to this topic.

## R_15_most_local_cited_documents.png
**Most locally cited documents** (R / bibliometrix)

- **Shows:** Corpus documents cited most often by other corpus documents - the papers this literature itself treats as central.
- **Data and settings:** Exact matching of OpenAlex referenced_works ids between corpus records (not string matching).
- **Caution:** Only as complete as OpenAlex reference lists: books, working papers and many Indian and legal journals have no machine-readable references.

## R_16_most_local_cited_references.png
**Most locally cited references** (R / bibliometrix)

- **Shows:** The 25 works cited by the largest number of corpus documents, whether or not they are themselves in the corpus.
- **Data and settings:** Counts over OpenAlex referenced_works of all corpus records, resolved to metadata by single-record lookups.
- **Caution:** Grey bars are intellectual foundations outside the search rules (methods papers, classics); they are context, not part of the topical corpus.

## R_17_rpys.png
**Reference publication year spectroscopy** (R / bibliometrix)

- **Shows:** How many of the corpus's cited references were published in each year; peaks in the red line mark years with unusually influential older works.
- **Data and settings:** Publication years of all resolved cited references (one count per citing document); deviation from a centred 5-year median, as in bibliometrix::rpys().
- **Caution:** Covers only references OpenAlex could link to a work record; pre-1950 and non-journal references are under-counted, so absent early peaks are not evidence of absence.

## R_18_most_frequent_keywords.png
**Most frequent keywords** (R / bibliometrix)

- **Shows:** The 30 keywords attached to the most corpus documents.
- **Data and settings:** OpenAlex 'keywords' field (DE); frequency = number of documents.
- **Caution:** Keywords are OpenAlex's algorithmically assigned keywords (OpenAlex does not carry author keywords); they reflect OpenAlex's vocabulary as much as the authors' own wording.

## R_19_wordcloud.png
**Keyword word cloud** (R / bibliometrix)

- **Shows:** The 120 most frequent keywords, sized by number of documents.
- **Data and settings:** wordcloud::wordcloud on OpenAlex keywords.
- **Caution:** Word clouds exaggerate long words and hide relationships; use the frequency table for any number. Keywords are OpenAlex's algorithmically assigned keywords (OpenAlex does not carry author keywords); they reflect OpenAlex's vocabulary as much as the authors' own wording.

## R_20_keyword_treemap.png
**Keyword treemap** (R / bibliometrix)

- **Shows:** Share of the 50 most frequent keywords; tile area is proportional to the number of documents.
- **Data and settings:** treemapify on OpenAlex keywords.
- **Caution:** Keywords are OpenAlex's algorithmically assigned keywords (OpenAlex does not carry author keywords); they reflect OpenAlex's vocabulary as much as the authors' own wording.

## R_21_trend_topics.png
**Trend topics** (R / bibliometrix)

- **Shows:** Each keyword is placed at the median publication year of the documents using it (bar = first to third quartile; point size = frequency).
- **Data and settings:** bibliometrix::fieldByYear(field = 'DE', n.items = 4 per year).
- **Caution:** A late median year can simply mean OpenAlex started assigning that keyword recently; it is not proof that the idea is new.

## R_22_keyword_cooccurrence_network.png
**Keyword co-occurrence network** (R / bibliometrix)

- **Shows:** Which keywords are attached to the same documents: clusters approximate the sub-topics of the literature.
- **Data and settings:** bibliometrix::biblioNetwork(co-occurrences, OpenAlex keywords), top 50 keywords, association-strength normalisation, Louvain clustering, Fruchterman-Reingold layout.
- **Caution:** Layout distances are not a metric and change with the random seed; clusters depend on the 50-keyword cut-off.

## R_23_thematic_map.png
**Thematic map** (R / bibliometrix)

- **Shows:** Keyword clusters placed by centrality (links to other clusters: how important the theme is to the field) and density (internal links: how developed it is). Quadrants: motor (upper right), niche (upper left), basic (lower right), emerging or declining (lower left).
- **Data and settings:** bibliometrix::thematicMap(field = 'DE', n = 250, Louvain); bubble size = keyword occurrences in the cluster.
- **Caution:** Quadrant positions are relative ranks within this corpus only and shift with minfreq; a 'niche' theme here may be a large field elsewhere.

## R_24_thematic_evolution.html
**Thematic evolution (interactive Sankey)** (R / bibliometrix)

- **Shows:** How keyword clusters in one period flow into clusters of the next. Time slices cut after: 2011, 2019. PNG maps of each slice are saved alongside.
- **Data and settings:** bibliometrix::thematicEvolution(field = 'DE', n = 250) with tercile cut points; flows weighted by the inclusion index.
- **Caution:** Cut years were chosen mechanically (terciles of publication years); moving them changes the flows, and early slices have few documents.

## R_25_cocitation_references.png
**Co-citation network of references** (R / bibliometrix)

- **Shows:** Cited works that corpus documents cite together: clusters are the intellectual bases the literature draws on.
- **Data and settings:** bibliometrix::biblioNetwork(co-citation, references) on WoS-style reference strings built from OpenAlex referenced_works; top 50 references, Louvain clusters.
- **Caution:** Reflects only records with machine-readable reference lists; economics and information-science journals dominate because they are best indexed.

## R_26_cocitation_sources.png
**Co-citation network of sources** (R / bibliometrix)

- **Shows:** Journals that are cited together, showing which disciplines the literature combines.
- **Data and settings:** bibliometrix::metaTagExtraction(CR_SO) then biblioNetwork(co-citation, sources); top 40 sources.
- **Caution:** Generic labels such as BOOK or PREPRINT are pooled categories, not single outlets.

## R_27_bibliographic_coupling.png
**Bibliographic coupling** (R / bibliometrix)

- **Shows:** Corpus documents linked when they cite the same references: groups of papers working from the same prior literature.
- **Data and settings:** bibliometrix::biblioNetwork(coupling, references); the 60 documents with the longest reference lists; Salton normalisation; Louvain clusters.
- **Caution:** Selecting by reference-list length favours reviews and long articles; documents with no indexed references cannot appear.

## R_28_historiograph.png
**Historiograph (direct citation network)** (R / bibliometrix)

- **Shows:** Chronological map of who cites whom among the 25 most locally cited corpus documents; arrows run from the cited to the citing paper along the time axis.
- **Data and settings:** bibliometrix::histNetwork(min.citations = 1) and histPlot(n = 25). A Python version built from exact OpenAlex ids is in py_citation_network.html and py_main_path.png.
- **Caution:** bibliometrix matches citations by DOI/label strings, so a few links can be missed; compare with the exact-id Python network.

## R_29_collaboration_authors.png
**Author collaboration network** (R / bibliometrix)

- **Shows:** Co-authorship among the 50 most productive authors.
- **Data and settings:** bibliometrix::biblioNetwork(collaboration, authors); association normalisation; Louvain clusters; isolates removed.
- **Caution:** Most authors appear once in a topical corpus, so this shows a few teams, not the field's whole social structure.

## R_30_collaboration_institutions.png
**Institution collaboration network** (R / bibliometrix)

- **Shows:** Which institutions co-author within the corpus.
- **Data and settings:** bibliometrix::biblioNetwork(collaboration, universities) on OpenAlex institutions.
- **Caution:** Limited to records with affiliation data; multi-campus systems may appear as separate nodes.

## R_31_collaboration_countries.png
**Country collaboration network** (R / bibliometrix)

- **Shows:** International co-authorship links between the 30 most productive countries.
- **Data and settings:** bibliometrix::biblioNetwork(collaboration, countries).
- **Caution:** Based on author addresses only; says nothing about which countries are studied.

## R_32_three_field_plot_country_keyword_source.html
**Three-field plot: country - keyword - source** (R / bibliometrix)

- **Shows:** Interactive Sankey linking author countries (left), keywords (middle) and sources (right). Saved as HTML because plotly cannot be rendered to PNG headlessly on this machine.
- **Data and settings:** bibliometrix::threeFieldsPlot(fields = AU_CO, DE, SO; top 12/15/12).
- **Caution:** Only the top items of each field are shown; flows are counts of co-appearance, not causal links.

## R_32_three_field_plot_reference_author_keyword.html
**Three-field plot: cited reference - author - keyword** (R / bibliometrix)

- **Shows:** Interactive Sankey linking the most cited references (left), the most productive authors (middle) and keywords (right).
- **Data and settings:** bibliometrix::threeFieldsPlot(fields = CR, AU, DE; top 12 each).
- **Caution:** Top-12 cut-offs hide most of the corpus; use it to spot schools of thought, not to count.


## py_burst_keywords.png
**Keyword burst timeline (Kleinberg)** (Python)

- **Shows:** Keywords whose share of the corpus rose sharply in an interval of years, ordered by start year.
- **Data and settings:** OpenAlex keywords of the 1360 corpus records; 3105 distinct keywords, 302 with at least 6 documents analysed; two-state automaton, s = 2, gamma = 1, years before 1990 pooled in 5-year bins; table in tables/py_burst_keywords.csv (36 bursts).
- **Caution:** Keywords are machine-assigned by OpenAlex and a corpus built from search terms over-represents those terms; bursts also reflect the growth of OpenAlex coverage and the sparsity of early years, and say nothing about causes.
