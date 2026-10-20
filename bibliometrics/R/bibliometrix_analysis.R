# Bibliometrix analysis for one paper's literature corpus.
# Usage (PowerShell):
#   $env:R_LIBS_USER='D:\Research-Publishing\_tools\R-lib;C:\Users\seans\AppData\Local\R\win-library\4.5'
#   & "C:\Program Files\R\R-4.5.3\bin\Rscript.exe" bibliometrix_analysis.R <bibliometrics_dir>
# Input : <dir>/data/clean/bibliometrix_input.csv (built by python/pipeline.py from OpenAlex records)
# Output: <dir>/figures/R_*.png|svg|html, <dir>/tables/R_*.csv, <dir>/vosviewer/*, <dir>/data/clean/*.rds
suppressPackageStartupMessages({
  library(bibliometrix); library(ggplot2); library(dplyr); library(tidyr); library(igraph)
  library(ggrepel); library(jsonlite); library(Matrix)
})
args <- commandArgs(TRUE)
B <- normalizePath(args[1], winslash = "/")
if (!dir.exists("D:/")) stop("D: is missing")
FIG <- file.path(B, "figures"); TAB <- file.path(B, "tables"); VOS <- file.path(B, "vosviewer")
for (d in c(FIG, TAB, VOS)) dir.create(d, showWarnings = FALSE, recursive = TRUE)
cfg <- fromJSON(file.path(B, "config.json"), simplifyVector = FALSE)
PAPER <- cfg$paper_id
set.seed(42)

M <- read.csv(file.path(B, "data/clean/bibliometrix_input.csv"), stringsAsFactors = FALSE, encoding = "UTF-8", na.strings = "NA_never")
for (cc in names(M)) if (is.character(M[[cc]])) M[[cc]][is.na(M[[cc]])] <- ""
M$TC <- as.numeric(M$TC); M$PY <- as.numeric(M$PY); M$LCS <- as.numeric(M$LCS)
M <- M[!is.na(M$PY), ]
rownames(M) <- M$SR
class(M) <- c("bibliometrixDB", "data.frame")
# ---- optional Scopus / Web of Science exports dropped by Sean or a mentor (none on this machine at build time)
drop <- file.path(B, "scopus-drop"); dir.create(drop, showWarnings = FALSE)
dropfiles <- list.files(drop, pattern = "\\.(csv|bib|txt)$", full.names = TRUE, ignore.case = TRUE)
drop_status <- data.frame(item = "scopus-drop", status = "EMPTY - no Scopus/WoS export to merge; corpus is OpenAlex-only", files = 0, records_added = 0)
if (length(dropfiles) > 0) {
  drop_status <- tryCatch({
    parts <- lapply(dropfiles, function(f) {
      ext <- tolower(tools::file_ext(f)); head3 <- paste(readLines(f, n = 5, warn = FALSE), collapse = " ")
      src <- if (ext == "csv" || grepl("scopus", head3, ignore.case = TRUE)) "scopus" else "wos"
      convert2df(f, dbsource = src, format = c(csv = "csv", bib = "bibtex", txt = "plaintext")[[ext]])
    })
    ext_all <- if (length(parts) > 1) Reduce(function(a, b) mergeDbSources(a, b, remove.duplicated = TRUE), parts) else parts[[1]]
    n0 <- nrow(M)
    keep_new <- ext_all[!(toupper(ext_all$DI) %in% M$DI[M$DI != ""]) & !(toupper(ext_all$TI) %in% M$TI), ]
    for (cc in setdiff(names(M), names(keep_new))) keep_new[[cc]] <- if (is.numeric(M[[cc]])) 0 else ""
    keep_new$SUBLIT <- "scopus_wos_import"; keep_new$DB <- "ISI"
    M <- rbind(as.data.frame(M), keep_new[, names(M)])
    M$SR <- make.unique(M$SR, sep = "-"); rownames(M) <- M$SR; class(M) <- c("bibliometrixDB", "data.frame")
    data.frame(item = "scopus-drop", status = "merged (records are NOT rule-screened; check them)", files = length(dropfiles), records_added = nrow(M) - n0)
  }, error = function(e) data.frame(item = "scopus-drop", status = paste("FAILED to merge:", conditionMessage(e)), files = length(dropfiles), records_added = 0))
}
dir.create(file.path(B, "tables"), showWarnings = FALSE)
write.csv(drop_status, file.path(B, "tables", "R_scopus_drop_status.csv"), row.names = FALSE)
cat("scopus-drop:", drop_status$status, "\n")
saveRDS(M, file.path(B, "data/clean/bibliometrix_M.rds"))
master <- read.csv(file.path(B, "data/clean/master.csv"), stringsAsFactors = FALSE, encoding = "UTF-8", fileEncoding = "UTF-8-BOM")
saveRDS(master, file.path(B, "data/clean/master.rds"))
N <- nrow(M); SMALL <- N < 50
THIS_YEAR <- as.numeric(format(Sys.Date(), "%Y"))
sub_labels <- sapply(cfg$sublits, function(s) s$label)
cat("Corpus:", N, "documents\n")

# ---------------------------------------------------------------- helpers
CAPS <- list(); LOG <- list()
cap <- function(file, title, what, how, caution) {
  CAPS[[length(CAPS) + 1]] <<- list(file = file, title = title, what = what, how = how, caution = caution, tool = "R / bibliometrix")
}
run <- function(name, expr) {
  t0 <- Sys.time()
  r <- tryCatch({ force(expr); "ok" }, error = function(e) paste("FAILED:", conditionMessage(e)))
  while (!is.null(dev.list())) dev.off()
  LOG[[length(LOG) + 1]] <<- data.frame(analysis = name, status = r, seconds = round(as.numeric(difftime(Sys.time(), t0, units = "secs")), 1))
  cat(sprintf("[%s] %s\n", name, r))
}
skip <- function(name, why) { LOG[[length(LOG) + 1]] <<- data.frame(analysis = name, status = paste("SKIPPED:", why), seconds = 0); cat(sprintf("[%s] SKIPPED: %s\n", name, why)) }
savep <- function(p, name, w = 10, h = 6.5) {
  ggsave(file.path(FIG, paste0(name, ".png")), p, width = w, height = h, dpi = 220, bg = "white")
  try(ggsave(file.path(FIG, paste0(name, ".svg")), p, width = w, height = h, bg = "white"), silent = TRUE)
}
wcsv <- function(x, name) write.csv(x, file.path(TAB, paste0(name, ".csv")), row.names = FALSE, fileEncoding = "UTF-8")
th <- theme_minimal(base_size = 12) + theme(plot.title = element_text(face = "bold"), plot.title.position = "plot", legend.position = "bottom")
`%||%` <- function(a, b) if (is.null(a)) b else a
SRC <- sprintf("Corpus: %d records (OpenAlex metadata). Paper %s.", N, PAPER)
splitc <- function(x) { v <- trimws(unlist(strsplit(x, ";"))); v[v != ""] }
shorten <- function(x, n = 55) ifelse(nchar(x) > n, paste0(substr(x, 1, n - 1), "\u2026"), x)
vos_export <- function(NetMatrix, name, n = 200, wlab = "Occurrences") {
  d <- Matrix::diag(NetMatrix); ord <- order(d, decreasing = TRUE)[seq_len(min(n, length(d)))]
  A <- as.matrix(NetMatrix[ord, ord]); labs <- rownames(A); diag(A) <- 0
  map <- data.frame(id = seq_along(labs), label = labs, w = d[ord]); names(map)[3] <- paste0("weight<", wlab, ">")
  write.table(map, file.path(VOS, paste0(name, "_map.txt")), sep = "\t", row.names = FALSE, quote = FALSE)
  idx <- which(A > 0 & upper.tri(A), arr.ind = TRUE)
  net <- data.frame(i = idx[, 1], j = idx[, 2], s = A[idx])
  write.table(net, file.path(VOS, paste0(name, "_network.txt")), sep = "\t", row.names = FALSE, col.names = FALSE, quote = FALSE)
  invisible(nrow(net))
}
netfig <- function(NetMatrix, name, title, n = 50, normalize = "association", type = "fruchterman", sub = "", labelsize = 0.75, ...) {
  png(file.path(FIG, paste0(name, ".png")), width = 2800, height = 2400, res = 220)
  par(mar = c(4, 1, 3, 1))
  net <- networkPlot(NetMatrix, normalize = normalize, n = n, Title = title, type = type, size = 5, size.cex = TRUE, labelsize = labelsize,
                     label.cex = TRUE, cluster = "louvain", remove.isolates = TRUE, remove.multiple = FALSE, edgesize = 3, alpha = 0.7,
                     halo = FALSE, curved = FALSE, verbose = TRUE, ...)
  cr <- net$cluster_res
  if (!is.null(cr) && nrow(cr) > 0) {
    g <- net$graph
    top <- cr %>% group_by(cluster) %>% slice_max(order_by = pagerank_centrality, n = 1, with_ties = FALSE) %>% ungroup()
    cols <- sapply(top$vertex, function(v) { i <- which(tolower(V(g)$name) == tolower(v))[1]; if (is.na(i)) "grey50" else adjustcolor(V(g)$color[i], alpha.f = 1) })
    legend("bottomleft", legend = paste0("Cluster ", top$cluster, ": ", shorten(top$vertex, 38)), fill = cols, cex = 0.7, bty = "n", title = "Louvain clusters (most central node)")
    wcsv(cr, paste0(name, "_clusters"))
  }
  mtext(sub, side = 1, line = 2.5, cex = 0.75)
  dev.off()
  invisible(net)
}

# ---------------------------------------------------------------- 1. main information
run("main_information", {
  yrs <- range(M$PY)
  n_au <- length(unique(splitc(M$AU)))
  single <- sum(!grepl(";", M$AU))
  cy <- sapply(strsplit(M$AU_CO, ";"), function(v) length(unique(v[v != ""])))
  ann <- as.data.frame(table(PY = M$PY), stringsAsFactors = FALSE); ann$PY <- as.numeric(ann$PY)
  full <- ann[ann$PY < THIS_YEAR, ]
  cagr <- if (nrow(full) > 1) ((full$Freq[nrow(full)] / full$Freq[1])^(1 / (full$PY[nrow(full)] - full$PY[1])) - 1) * 100 else NA
  mi <- data.frame(item = c("Timespan", "Documents", "Sources (journals, books, repositories)", "Annual growth rate % (first to last complete year)",
                            "Document average age (years)", "Average citations per document", "Median citations per document", "Cited references (resolved, distinct)",
                            "OpenAlex keywords (distinct)", "Concepts/topics (distinct)", "Authors", "Single-authored documents", "Co-authors per document",
                            "International co-authorship % (docs with >1 country, of docs with country data)", "Documents with country data", "Documents with abstract",
                            "Documents with DOI", "Documents with a reference list"),
                   value = c(paste(yrs, collapse = " - "), N, length(unique(M$SO)), round(cagr, 2), round(mean(THIS_YEAR - M$PY), 2), round(mean(M$TC), 2), median(M$TC),
                             length(unique(splitc(M$CR))), length(unique(splitc(M$DE))), length(unique(splitc(M$ID))), n_au, single,
                             round(mean(lengths(strsplit(M$AU, ";"))), 2), round(100 * sum(cy > 1) / max(1, sum(cy > 0)), 1), sum(cy > 0), sum(M$AB != ""), sum(M$DI != ""), sum(M$CR != "")))
  wcsv(mi, "R_main_information")
  dt <- as.data.frame(sort(table(M$DT), decreasing = TRUE)); names(dt) <- c("document_type", "n"); wcsv(dt, "R_document_types")
  sl <- as.data.frame(sort(table(M$SUBLIT), decreasing = TRUE)); names(sl) <- c("sub_literature", "n"); wcsv(sl, "R_sub_literature_counts")
})
run("biblioAnalysis_summary", {
  res <- biblioAnalysis(M, sep = ";")
  S <- summary(res, k = 25, pause = FALSE, verbose = FALSE)
  for (nm in c("MainInformationDF", "MostProdAuthors", "MostCitedPapers", "MostProdCountries", "TCperCountries", "MostRelSources", "MostRelKeywords")) {
    if (!is.null(S[[nm]])) wcsv(S[[nm]], paste0("R_bibliometrix_summary_", nm))
  }
})

# ---------------------------------------------------------------- 2. annual production, growth, citations per year
run("annual_production", {
  ann <- M %>% as.data.frame() %>% count(PY, SUBLIT)
  tot <- ann %>% group_by(PY) %>% summarise(n = sum(n))
  tot$growth_pct <- round(100 * (tot$n / lag(tot$n) - 1), 1)
  wcsv(tot, "R_annual_production")
  ann$SUBLIT <- factor(ann$SUBLIT, levels = names(sub_labels), labels = sub_labels[names(sub_labels)])
  p <- ggplot(ann, aes(PY, n, fill = SUBLIT)) + geom_col() + scale_fill_brewer(palette = "Set2", na.value = "grey60") +
    labs(title = "Annual scientific production, by sub-literature", subtitle = SRC, x = "Publication year", y = "Documents in corpus", fill = NULL,
         caption = paste0(THIS_YEAR, " is incomplete.")) + th + guides(fill = guide_legend(ncol = 2))
  savep(p, "R_01_annual_production")
  cap("R_01_annual_production.png", "Annual scientific production", "Number of corpus documents per publication year, stacked by the sub-literature each record was assigned to.",
      "Counts of PY in the screened corpus; sub-literature = first inclusion rule matched (see search-protocol.md).",
      "Growth partly reflects database growth and the search design (recent records are better indexed); the last year is incomplete.")
})
run("average_citations_per_year", {
  cy <- M %>% as.data.frame() %>% group_by(PY) %>% summarise(N = n(), MeanTCperArt = mean(TC), CitableYears = THIS_YEAR - first(PY) + 1) %>%
    mutate(MeanTCperYear = MeanTCperArt / CitableYears)
  wcsv(cy, "R_average_citations_per_year")
  p <- ggplot(cy, aes(PY, MeanTCperYear)) + geom_line(colour = "#1b6ca8", linewidth = 0.9) + geom_point(aes(size = N), colour = "#1b6ca8", alpha = 0.7) +
    labs(title = "Average citations per year, by publication year", subtitle = SRC, x = "Publication year", y = "Mean citations per document per year since publication",
         size = "Documents published that year") + th
  savep(p, "R_02_average_citations_per_year")
  cap("R_02_average_citations_per_year.png", "Average citations per year", "Mean OpenAlex citation count of documents published in each year, divided by the years since publication.",
      "TC = OpenAlex cited_by_count at the pull date; citable years = current year - PY + 1.",
      "Years with few documents (small points) are dominated by one or two highly cited papers; do not read them as trends.")
})

# ---------------------------------------------------------------- 3. sources
run("sources", {
  so <- M %>% as.data.frame() %>% group_by(SO) %>% summarise(documents = n(), total_citations = sum(TC), local_citations = sum(LCS), first_year = min(PY)) %>% arrange(desc(documents))
  wcsv(so, "R_most_relevant_sources")
  top <- head(so[!so$SO %in% c("NO SOURCE RECORDED"), ], 20)
  p <- ggplot(top, aes(documents, reorder(shorten(SO), documents))) + geom_col(fill = "#2a9d8f") + geom_text(aes(label = documents), hjust = -0.2, size = 3.3) +
    labs(title = "Most relevant sources", subtitle = SRC, x = "Documents in corpus", y = NULL) + th + scale_x_continuous(expand = expansion(mult = c(0, 0.08)))
  savep(p, "R_03_most_relevant_sources", 10, 7)
  cap("R_03_most_relevant_sources.png", "Most relevant sources", "The 20 journals, book series or repositories contributing most documents to the corpus.",
      "Counts of the OpenAlex primary-location source. Records with no source recorded are listed in the table but left out of the plot.",
      "Preprint servers (arXiv, SSRN, NBER) rank high because working papers are counted as documents; this is not a journal-quality ranking.")
})
run("bradford", {
  br <- bradford(M)
  wcsv(br$table, "R_bradford_law")
  savep(br$graph + labs(title = "Bradford's law: core sources", subtitle = SRC) + th + theme(axis.text.x = element_text(angle = 60, hjust = 1, size = 6)), "R_04_bradford_law", 11, 6.5)
  cap("R_04_bradford_law.png", "Bradford's law", "Sources ranked by number of documents (log rank); the shaded zone is Bradford zone 1, the small core of sources that carries about a third of the documents.",
      "bibliometrix::bradford() on the source field (SO).", "With a multi-disciplinary corpus the 'core' is partly an artefact of which sub-literature has the most records.")
})
run("source_dynamics", {
  sg <- sourceGrowth(M, top = 6, cdf = TRUE)
  wcsv(sg, "R_source_dynamics_cumulative")
  lg <- pivot_longer(sg, -Year, names_to = "source", values_to = "cum")
  p <- ggplot(lg, aes(Year, cum, colour = shorten(source, 45))) + geom_line(linewidth = 0.9) + scale_colour_brewer(palette = "Dark2") +
    labs(title = "Source dynamics: cumulative documents in the six largest sources", subtitle = SRC, x = "Year", y = "Cumulative documents", colour = NULL) + th + guides(colour = guide_legend(ncol = 2))
  savep(p, "R_05_source_dynamics")
  cap("R_05_source_dynamics.png", "Source dynamics", "Cumulative number of corpus documents over time in the six most frequent sources.", "bibliometrix::sourceGrowth(top = 6, cdf = TRUE).",
      "Small absolute numbers: a difference of two or three papers changes the ordering.")
})

# ---------------------------------------------------------------- 4. authors
run("authors", {
  al <- strsplit(M$AU, ";")
  au <- data.frame(AU = trimws(unlist(al)), TC = rep(M$TC, lengths(al)), LCS = rep(M$LCS, lengths(al)), frac = rep(1 / lengths(al), lengths(al)), PY = rep(M$PY, lengths(al)))
  au <- au[au$AU != "" & au$AU != "ANONYMOUS", ]
  at <- au %>% group_by(AU) %>% summarise(documents = n(), fractionalised = round(sum(frac), 2), total_citations = sum(TC), local_citations = sum(LCS), first_year = min(PY), last_year = max(PY)) %>% arrange(desc(documents), desc(total_citations))
  wcsv(at, "R_authors")
  t1 <- head(at, 20)
  p1 <- ggplot(t1, aes(documents, reorder(AU, documents))) + geom_col(fill = "#e76f51") + geom_text(aes(label = documents), hjust = -0.3, size = 3.3) +
    labs(title = "Most productive authors", subtitle = SRC, x = "Documents in corpus", y = NULL) + th
  savep(p1, "R_06_most_productive_authors", 9, 6.5)
  t2 <- head(at[order(-at$total_citations), ], 20)
  p2 <- ggplot(t2, aes(total_citations, reorder(AU, total_citations))) + geom_col(fill = "#264653") + geom_text(aes(label = total_citations), hjust = -0.15, size = 3.2) +
    labs(title = "Most cited authors (sum of citations to their corpus documents)", subtitle = SRC, x = "Total citations (OpenAlex)", y = NULL) + th + scale_x_continuous(expand = expansion(mult = c(0, 0.1)))
  savep(p2, "R_07_most_cited_authors", 9, 6.5)
  cap("R_06_most_productive_authors.png", "Most productive authors", "Authors with the most documents in the corpus (whole counting).", "Author names from OpenAlex authorships, reduced to SURNAME + initials.",
      "Name disambiguation is imperfect: common surnames with the same initials can be merged, and one person can be split across spellings.")
  cap("R_07_most_cited_authors.png", "Most cited authors", "Authors ranked by the total OpenAlex citations received by their documents in this corpus.", "Sum of TC over each author's corpus documents (full credit to every co-author).",
      "A single famous paper puts all of its co-authors at the top; this is citation to corpus papers only, not career citations.")
})
run("lotka", {
  L <- lotka(M)
  ap <- L$AuthorProd; names(ap) <- c("documents_written", "n_authors", "share_of_authors")
  ap$theoretical_share <- 10^(log10(L$C) - 2 * log10(ap$documents_written))
  wcsv(ap, "R_lotka_law")
  wcsv(data.frame(beta = L$Beta, C = L$C, R2 = L$R2, p_value_KS = L$p.value), "R_lotka_fit")
  lg <- pivot_longer(ap, c(share_of_authors, theoretical_share), names_to = "series", values_to = "share")
  p <- ggplot(lg, aes(documents_written, share, colour = series, linetype = series)) + geom_line(linewidth = 0.9) + geom_point() +
    scale_colour_manual(values = c("#d62828", "grey40"), labels = c("Observed", "Lotka (beta = 2)")) + scale_linetype_manual(values = c(1, 2), labels = c("Observed", "Lotka (beta = 2)")) +
    labs(title = sprintf("Lotka's law of author productivity (fitted beta = %.2f, R2 = %.2f)", L$Beta, L$R2), subtitle = SRC, x = "Documents written", y = "Share of authors", colour = NULL, linetype = NULL) + th
  savep(p, "R_08_lotka_law", 8, 5.5)
  cap("R_08_lotka_law.png", "Lotka's law", "Share of authors who wrote 1, 2, 3 ... corpus documents, against the theoretical inverse-square distribution.", "bibliometrix::lotka().",
      "A topical corpus truncates each author's output, so nearly everyone appears once; this describes the corpus, not the authors' careers.")
})
run("author_production_over_time", {
  ap <- authorProdOverTime(M, k = 12, graph = FALSE)
  wcsv(ap$dfAU, "R_author_production_over_time")
  savep(ap$graph + labs(title = "Authors' production over time (top 12 authors)", subtitle = SRC) + th, "R_09_author_production_over_time", 10, 6.5)
  cap("R_09_author_production_over_time.png", "Author production over time", "For the 12 most productive authors: when their corpus documents appeared (point size = number of documents, shade = citations per year).",
      "bibliometrix::authorProdOverTime(k = 12).", "Shows only documents that passed this corpus's inclusion rules.")
})

# ---------------------------------------------------------------- 5. affiliations and countries
run("affiliations", {
  af <- as.data.frame(sort(table(splitc(M$AU_UN)), decreasing = TRUE), stringsAsFactors = FALSE); names(af) <- c("affiliation", "documents")
  wcsv(af, "R_most_relevant_affiliations")
  p <- ggplot(head(af, 20), aes(documents, reorder(shorten(affiliation, 50), documents))) + geom_col(fill = "#6d597a") + geom_text(aes(label = documents), hjust = -0.3, size = 3.3) +
    labs(title = "Most relevant affiliations", subtitle = SRC, x = "Documents with at least one author from the institution", y = NULL) + th
  savep(p, "R_10_most_relevant_affiliations", 10, 6.5)
  cap("R_10_most_relevant_affiliations.png", "Most relevant affiliations", "Institutions appearing on the most corpus documents.", "OpenAlex institution of each authorship; one count per document per institution.",
      "OpenAlex affiliation data are missing for many older, book and Indian-journal records, so institutions from well-indexed countries are over-represented.")
})
run("countries", {
  cl <- lapply(strsplit(M$AU_CO, ";"), function(v) unique(v[v != ""]))
  co <- data.frame(country = unlist(cl), TC = rep(M$TC, lengths(cl)))
  ct <- co %>% group_by(country) %>% summarise(documents = n(), total_citations = sum(TC), mean_citations = round(mean(TC), 1)) %>% arrange(desc(documents))
  mcp <- lengths(cl) > 1
  cc <- data.frame(country = M$AU1_CO, mcp = mcp)[M$AU1_CO != "", ]
  ca <- cc %>% group_by(country) %>% summarise(corresponding_docs = n(), SCP = sum(!mcp), MCP = sum(mcp)) %>% mutate(MCP_ratio = round(MCP / corresponding_docs, 2)) %>% arrange(desc(corresponding_docs))
  ct <- left_join(ct, ca, by = "country")
  wcsv(ct, "R_countries")
  p <- ggplot(head(ct, 20), aes(documents, reorder(country, documents))) + geom_col(fill = "#457b9d") + geom_text(aes(label = documents), hjust = -0.3, size = 3.3) +
    labs(title = "Most relevant countries (documents with at least one author there)", subtitle = paste0(SRC, " Country data available for ", sum(lengths(cl) > 0), " records."), x = "Documents", y = NULL) + th
  savep(p, "R_11_most_relevant_countries", 9, 6.5)
  lg <- head(ca, 20) %>% pivot_longer(c(SCP, MCP), names_to = "type", values_to = "n")
  p2 <- ggplot(lg, aes(n, reorder(country, corresponding_docs), fill = type)) + geom_col() +
    scale_fill_manual(values = c(MCP = "#e63946", SCP = "#a8dadc"), labels = c(MCP = "Multi-country publication", SCP = "Single-country publication")) +
    labs(title = "Corresponding author's country", subtitle = SRC, x = "Documents", y = NULL, fill = NULL) + th
  savep(p2, "R_12_corresponding_author_countries", 9, 6.5)
  cap("R_11_most_relevant_countries.png", "Most relevant countries", "Countries of author institutions, counted once per document.", "OpenAlex authorship country codes.",
      "Counts where the authors work, not which country a study is about; records without affiliation data are excluded.")
  cap("R_12_corresponding_author_countries.png", "Corresponding author's country", "Documents by country of the corresponding (else first) author, split into single-country and multi-country papers.",
      "OpenAlex is_corresponding flag, falling back to the first author; MCP = authors from more than one country.", "The corresponding-author flag is missing for many records, in which case the first author is used.")
  # world collaboration map
  wm <- map_data("world")
  fix <- c("USA" = "USA", "UNITED KINGDOM" = "UK", "KOREA" = "South Korea", "RUSSIA" = "Russia", "IRAN" = "Iran", "TAIWAN" = "Taiwan", "VIETNAM" = "Vietnam",
           "CZECH REPUBLIC" = "Czech Republic", "TANZANIA" = "Tanzania", "TURKEY" = "Turkey", "HONG KONG" = "China", "IVORY COAST" = "Ivory Coast",
           "DR CONGO" = "Democratic Republic of the Congo", "NORTH MACEDONIA" = "North Macedonia", "TURKIYE" = "Turkey", "VIET NAM" = "Vietnam", "RUSSIAN FEDERATION" = "Russia")
  regs <- unique(wm$region); up <- setNames(regs, toupper(regs))
  tomap <- function(x) ifelse(x %in% names(fix), fix[x], ifelse(x %in% names(up), up[x], NA))
  ct$region <- tomap(ct$country)
  agg <- ct %>% filter(!is.na(region)) %>% group_by(region) %>% summarise(documents = sum(documents))
  wm2 <- left_join(wm, agg, by = "region")
  cen <- wm %>% group_by(region) %>% summarise(long = mean(range(long)), lat = mean(range(lat)))
  cen$long[cen$region == "USA"] <- -98; cen$lat[cen$region == "USA"] <- 39; cen$long[cen$region == "Russia"] <- 60; cen$lat[cen$region == "Russia"] <- 58
  cen$long[cen$region == "Canada"] <- -105; cen$lat[cen$region == "Canada"] <- 57; cen$long[cen$region == "France"] <- 2.5; cen$lat[cen$region == "France"] <- 46.5
  cen$long[cen$region == "Norway"] <- 9; cen$lat[cen$region == "Norway"] <- 61; cen$long[cen$region == "UK"] <- -1.5; cen$lat[cen$region == "UK"] <- 53
  pr <- do.call(rbind, lapply(cl[lengths(cl) > 1], function(v) { v <- sort(unique(na.omit(tomap(v)))); if (length(v) < 2) return(NULL); t(combn(v, 2)) }))
  p3 <- ggplot() + geom_polygon(data = wm2, aes(long, lat, group = group, fill = documents), colour = "white", linewidth = 0.1) +
    scale_fill_gradient(low = "#cfe8f3", high = "#08306b", na.value = "grey92", trans = "log10", name = "Documents (log scale)")
  if (!is.null(pr) && nrow(pr) > 0) {
    ed <- as.data.frame(pr, stringsAsFactors = FALSE) %>% count(V1, V2, name = "w") %>% left_join(cen, by = c("V1" = "region")) %>% left_join(cen, by = c("V2" = "region"), suffix = c("1", "2"))
    wcsv(ed[, c("V1", "V2", "w")], "R_country_collaboration_links")
    p3 <- p3 + geom_curve(data = ed, aes(x = long1, y = lat1, xend = long2, yend = lat2, linewidth = w), colour = "#d62828", alpha = 0.45, curvature = 0.2) +
      scale_linewidth(range = c(0.25, 2), name = "Co-authored documents")
  }
  p3 <- p3 + coord_quickmap(ylim = c(-55, 80)) + labs(title = "Country scientific production and collaboration map", subtitle = SRC, x = "Longitude", y = "Latitude") + th +
    theme(panel.grid = element_blank(), axis.text = element_text(size = 7))
  savep(p3, "R_13_country_collaboration_map", 12, 6.5)
  cap("R_13_country_collaboration_map.png", "Country production and collaboration map", "Shading = documents with an author in the country (log scale); red arcs = pairs of countries that co-authored, thicker = more joint documents.",
      "Author countries from OpenAlex, joined to the 'maps' world polygons; arcs join country bounding-box centres.", "Grey means no author affiliation recorded, not no research; affiliation coverage is weakest for India-published and legal sources.")
})

# ---------------------------------------------------------------- 6. most cited documents and references
run("most_cited_documents", {
  d <- as.data.frame(M)[, c("SR", "TI", "PY", "SO", "DI", "TC", "LCS", "SUBLIT")]
  d$TC_per_year <- round(d$TC / (THIS_YEAR - d$PY + 1), 2)
  wcsv(d[order(-d$TC), ], "R_most_global_cited_documents")
  wcsv(d[order(-d$LCS, -d$TC), ], "R_most_local_cited_documents")
  g <- head(d[order(-d$TC), ], 20)
  p <- ggplot(g, aes(TC, reorder(shorten(SR, 60), TC))) + geom_col(fill = "#1d3557") + geom_text(aes(label = TC), hjust = -0.15, size = 3.2) +
    labs(title = "Most globally cited documents", subtitle = SRC, x = "Citations from all of OpenAlex", y = NULL) + th + scale_x_continuous(expand = expansion(mult = c(0, 0.1)))
  savep(p, "R_14_most_global_cited_documents", 10, 6.5)
  l <- head(d[order(-d$LCS, -d$TC), ], 20); l <- l[l$LCS > 0, ]
  if (nrow(l) > 0) {
    p2 <- ggplot(l, aes(LCS, reorder(shorten(SR, 60), LCS))) + geom_col(fill = "#c1121f") + geom_text(aes(label = LCS), hjust = -0.3, size = 3.2) +
      labs(title = "Most locally cited documents (cited by other documents in this corpus)", subtitle = SRC, x = "Local citations", y = NULL) + th + scale_x_continuous(expand = expansion(mult = c(0, 0.1)))
    savep(p2, "R_15_most_local_cited_documents", 10, 6.5)
  }
  cap("R_14_most_global_cited_documents.png", "Most globally cited documents", "Corpus documents with the highest total citation counts in OpenAlex.", "OpenAlex cited_by_count at the pull date.",
      "Global citations reward age and breadth: a highly cited paper may be cited mostly for reasons unrelated to this topic.")
  cap("R_15_most_local_cited_documents.png", "Most locally cited documents", "Corpus documents cited most often by other corpus documents - the papers this literature itself treats as central.",
      "Exact matching of OpenAlex referenced_works ids between corpus records (not string matching).", "Only as complete as OpenAlex reference lists: books, working papers and many Indian and legal journals have no machine-readable references.")
  cr <- read.csv(file.path(B, "data/clean/cited_references.csv"), stringsAsFactors = FALSE, encoding = "UTF-8", fileEncoding = "UTF-8-BOM")
  wcsv(head(cr, 100), "R_most_local_cited_references")
  r <- head(cr, 25); r$lab <- shorten(paste0(sub(" .*", "", sub(".* ", "", r$first_author)), " (", r$year, ") ", r$title), 70)
  r$lab <- make.unique(r$lab)
  p3 <- ggplot(r, aes(local_citations, reorder(lab, local_citations), fill = factor(in_corpus))) + geom_col() +
    scale_fill_manual(values = c("0" = "#8d99ae", "1" = "#ef233c"), labels = c("0" = "Outside corpus", "1" = "In corpus"), name = NULL) +
    labs(title = "Most locally cited references", subtitle = SRC, x = "Corpus documents citing the reference", y = NULL) + th
  savep(p3, "R_16_most_local_cited_references", 11, 7)
  cap("R_16_most_local_cited_references.png", "Most locally cited references", "The 25 works cited by the largest number of corpus documents, whether or not they are themselves in the corpus.",
      "Counts over OpenAlex referenced_works of all corpus records, resolved to metadata by single-record lookups.", "Grey bars are intellectual foundations outside the search rules (methods papers, classics); they are context, not part of the topical corpus.")
})
run("rpys", {
  cr <- splitc(M$CR)
  yr <- suppressWarnings(as.numeric(trimws(sapply(strsplit(cr, ","), function(v) if (length(v) >= 2) v[2] else NA))))
  yr <- yr[!is.na(yr) & yr >= 1900 & yr <= THIS_YEAR]
  tb <- as.data.frame(table(Year = yr), stringsAsFactors = FALSE); tb$Year <- as.numeric(tb$Year)
  tb <- merge(data.frame(Year = min(tb$Year):max(tb$Year)), tb, all.x = TRUE); tb$Freq[is.na(tb$Freq)] <- 0
  med <- sapply(seq_len(nrow(tb)), function(i) median(tb$Freq[max(1, i - 2):min(nrow(tb), i + 2)]))
  tb$deviation_from_5yr_median <- tb$Freq - med
  names(tb)[2] <- "cited_references"
  wcsv(tb, "R_rpys")
  k <- max(tb$cited_references) / max(1, max(abs(tb$deviation_from_5yr_median)))
  pk <- tb[order(-tb$deviation_from_5yr_median), ][1:6, ]
  p <- ggplot(tb, aes(Year)) + geom_line(aes(y = cited_references, colour = "Cited references per year"), linewidth = 0.9) +
    geom_line(aes(y = deviation_from_5yr_median * k, colour = "Deviation from 5-year median (rescaled)"), linewidth = 0.7) +
    geom_text_repel(data = pk, aes(y = cited_references, label = Year), size = 3.2) +
    scale_colour_manual(values = c("black", "#d62828"), name = NULL) +
    labs(title = "Reference publication year spectroscopy (RPYS)", subtitle = SRC, x = "Publication year of the cited reference", y = "Number of cited references") + th
  savep(p, "R_17_rpys", 10, 6)
  cap("R_17_rpys.png", "Reference publication year spectroscopy", "How many of the corpus's cited references were published in each year; peaks in the red line mark years with unusually influential older works.",
      "Publication years of all resolved cited references (one count per citing document); deviation from a centred 5-year median, as in bibliometrix::rpys().",
      "Covers only references OpenAlex could link to a work record; pre-1950 and non-journal references are under-counted, so absent early peaks are not evidence of absence.")
  try({ rp <- rpys(M, sep = ";", graph = FALSE); wcsv(rp$rpysTable, "R_rpys_bibliometrix") }, silent = TRUE)
})

# ---------------------------------------------------------------- 7. keywords
STOPKW <- toupper(unlist(cfg$keyword_stoplist %||% list()))
run("keywords", {
  kw <- splitc(M$DE); kw <- kw[!kw %in% STOPKW]
  kt <- as.data.frame(sort(table(kw), decreasing = TRUE), stringsAsFactors = FALSE); names(kt) <- c("keyword", "occurrences")
  wcsv(kt, "R_keywords")
  p <- ggplot(head(kt, 30), aes(occurrences, reorder(tolower(keyword), occurrences))) + geom_col(fill = "#588157") + geom_text(aes(label = occurrences), hjust = -0.2, size = 3) +
    labs(title = "Most frequent keywords", subtitle = paste(SRC, "Keywords are those assigned by OpenAlex, not author keywords."), x = "Documents", y = NULL) + th
  savep(p, "R_18_most_frequent_keywords", 9, 7.5)
  png(file.path(FIG, "R_19_wordcloud.png"), width = 2200, height = 1900, res = 220); par(mar = c(1, 1, 3, 1))
  wc <- head(kt, 120)
  wordcloud::wordcloud(tolower(wc$keyword), wc$occurrences, scale = c(3.2, 0.45), random.order = FALSE, rot.per = 0.1, colors = RColorBrewer::brewer.pal(8, "Dark2"), min.freq = 1)
  title(main = "Keyword word cloud (size = number of documents)", sub = SRC, cex.sub = 0.7); dev.off()
  tm <- head(kt, 50)
  p2 <- ggplot(tm, aes(area = occurrences, fill = occurrences, label = paste0(tolower(keyword), "\n", occurrences))) + treemapify::geom_treemap(colour = "white") +
    treemapify::geom_treemap_text(colour = "white", place = "centre", reflow = TRUE, min.size = 5) + scale_fill_viridis_c(option = "D", end = 0.85, name = "Documents") +
    labs(title = "Keyword treemap (top 50 keywords)", subtitle = SRC) + th
  savep(p2, "R_20_keyword_treemap", 11, 7)
  kc <- "Keywords are OpenAlex's algorithmically assigned keywords (OpenAlex does not carry author keywords); they reflect OpenAlex's vocabulary as much as the authors' own wording."
  cap("R_18_most_frequent_keywords.png", "Most frequent keywords", "The 30 keywords attached to the most corpus documents.", "OpenAlex 'keywords' field (DE); frequency = number of documents.", kc)
  cap("R_19_wordcloud.png", "Keyword word cloud", "The 120 most frequent keywords, sized by number of documents.", "wordcloud::wordcloud on OpenAlex keywords.", "Word clouds exaggerate long words and hide relationships; use the frequency table for any number. " %>% paste0(kc))
  cap("R_20_keyword_treemap.png", "Keyword treemap", "Share of the 50 most frequent keywords; tile area is proportional to the number of documents.", "treemapify on OpenAlex keywords.", kc)
})
run("trend_topics", {
  ft <- fieldByYear(M, field = "DE", min.freq = max(3, round(N / 150)), n.items = 4, remove.terms = if (length(STOPKW)) STOPKW else NULL, graph = FALSE)
  wcsv(ft$df_graph, "R_trend_topics")
  savep(ft$graph + labs(title = "Trend topics (keywords by median year of use)", subtitle = SRC) + th, "R_21_trend_topics", 10, 8)
  cap("R_21_trend_topics.png", "Trend topics", "Each keyword is placed at the median publication year of the documents using it (bar = first to third quartile; point size = frequency).",
      "bibliometrix::fieldByYear(field = 'DE', n.items = 4 per year).", "A late median year can simply mean OpenAlex started assigning that keyword recently; it is not proof that the idea is new.")
})

# ---------------------------------------------------------------- structural analyses (need a corpus of roughly 50+)
if (SMALL) {
  for (nm in c("cooccurrence_network", "thematic_map", "thematic_evolution", "cocitation_references", "cocitation_sources", "bibliographic_coupling", "historiograph",
               "collaboration_networks", "three_field_plot")) skip(nm, sprintf("corpus has only %d documents (< 50); network/thematic methods would not be meaningful", N))
} else {
  run("cooccurrence_network", {
    NM <- biblioNetwork(M, analysis = "co-occurrences", network = "author_keywords", sep = ";", remove.terms = if (length(STOPKW)) STOPKW else NULL)
    vos_export(NM, "keyword_cooccurrence", 250, "Occurrences")
    netfig(NM, "R_22_keyword_cooccurrence_network", "Keyword co-occurrence network (top 50 keywords)", n = 50,
           sub = "Node size = documents using the keyword; edge = co-occurrence in the same document (association strength); colour = Louvain cluster.")
    cap("R_22_keyword_cooccurrence_network.png", "Keyword co-occurrence network", "Which keywords are attached to the same documents: clusters approximate the sub-topics of the literature.",
        "bibliometrix::biblioNetwork(co-occurrences, OpenAlex keywords), top 50 keywords, association-strength normalisation, Louvain clustering, Fruchterman-Reingold layout.",
        "Layout distances are not a metric and change with the random seed; clusters depend on the 50-keyword cut-off.")
  })
  run("thematic_map", {
    tm <- thematicMap(M, field = "DE", n = 250, minfreq = max(3, round(N * 5 / 1000)), size = 0.6, n.labels = 3, repel = TRUE, remove.terms = if (length(STOPKW)) STOPKW else NULL)
    wcsv(tm$clusters, "R_thematic_map_clusters"); wcsv(tm$words, "R_thematic_map_words")
    savep(tm$map + labs(title = "Thematic map (Callon centrality vs density)", subtitle = paste(SRC, "Upper right = motor themes; upper left = niche; lower right = basic; lower left = emerging or declining.")) +
            theme(plot.title = element_text(face = "bold")), "R_23_thematic_map", 11, 8)
    cap("R_23_thematic_map.png", "Thematic map", "Keyword clusters placed by centrality (links to other clusters: how important the theme is to the field) and density (internal links: how developed it is). Quadrants: motor (upper right), niche (upper left), basic (lower right), emerging or declining (lower left).",
        "bibliometrix::thematicMap(field = 'DE', n = 250, Louvain); bubble size = keyword occurrences in the cluster.",
        "Quadrant positions are relative ranks within this corpus only and shift with minfreq; a 'niche' theme here may be a large field elsewhere.")
  })
  run("thematic_evolution", {
    qs <- as.numeric(quantile(M$PY, c(1 / 3, 2 / 3))); cuts <- unique(floor(qs)); cuts <- cuts[cuts > min(M$PY) & cuts < max(M$PY)]
    if (length(cuts) < 1) stop("not enough spread in publication years for time slices")
    te <- thematicEvolution(M, field = "DE", years = cuts, n = 250, minFreq = max(2, round(N * 5 / 1000)), size = 0.6, n.labels = 2, repel = TRUE, remove.terms = if (length(STOPKW)) STOPKW else NULL)
    wcsv(te$Nodes, "R_thematic_evolution_nodes"); wcsv(te$Edges, "R_thematic_evolution_edges")
    w <- plotThematicEvolution(te$Nodes, te$Edges)
    htmlwidgets::saveWidget(w, file.path(FIG, "R_24_thematic_evolution.html"), selfcontained = FALSE, libdir = "html_libs", title = "Thematic evolution")
    for (i in seq_along(te$TM)) savep(te$TM[[i]]$map + labs(title = paste0("Thematic map, time slice ", i, " of ", length(te$TM)), subtitle = paste(SRC, "Slice boundaries (last year of each slice):", paste(cuts, collapse = ", "))),
                                      sprintf("R_24_thematic_evolution_slice%d", i), 10, 7.5)
    cap("R_24_thematic_evolution.html", "Thematic evolution (interactive Sankey)", paste0("How keyword clusters in one period flow into clusters of the next. Time slices cut after: ", paste(cuts, collapse = ", "), ". PNG maps of each slice are saved alongside."),
        "bibliometrix::thematicEvolution(field = 'DE', n = 250) with tercile cut points; flows weighted by the inclusion index.",
        "Cut years were chosen mechanically (terciles of publication years); moving them changes the flows, and early slices have few documents.")
  })
  run("cocitation_references", {
    NM <- biblioNetwork(M, analysis = "co-citation", network = "references", sep = ";")
    vos_export(NM, "cocitation_references", 250, "Citations")
    netfig(NM, "R_25_cocitation_references", "Co-citation network of cited references (top 50)", n = 50, normalize = NULL,
           sub = "Node = cited work (first author, year, source); edge = cited together by the same corpus document; colour = Louvain cluster.")
    cap("R_25_cocitation_references.png", "Co-citation network of references", "Cited works that corpus documents cite together: clusters are the intellectual bases the literature draws on.",
        "bibliometrix::biblioNetwork(co-citation, references) on WoS-style reference strings built from OpenAlex referenced_works; top 50 references, Louvain clusters.",
        "Reflects only records with machine-readable reference lists; economics and information-science journals dominate because they are best indexed.")
  })
  run("cocitation_sources", {
    # fast version of metaTagExtraction(CR_SO) + biblioNetwork(co-citation, sources): source = 3rd comma field of each WoS-style reference string
    src_list <- lapply(strsplit(M$CR, ";", fixed = TRUE), function(v) { v <- trimws(v); v <- v[v != ""]
      s <- trimws(vapply(strsplit(v, ",", fixed = TRUE), function(z) if (length(z) >= 3) z[3] else "", "")); unique(s[s != "" & !grepl("^(V|P)[0-9]|^DOI", s)]) })
    all_src <- sort(unique(unlist(src_list)))
    A <- Matrix::sparseMatrix(i = rep(seq_along(src_list), lengths(src_list)), j = match(unlist(src_list), all_src), x = 1, dims = c(length(src_list), length(all_src)), dimnames = list(NULL, all_src))
    NM <- Matrix::crossprod(A)
    vos_export(NM, "cocitation_sources", 250, "Citations")
    netfig(NM, "R_26_cocitation_sources", "Co-citation network of cited sources (top 40)", n = 40, normalize = NULL,
           sub = "Node = journal or other source of the cited references; edge = cited together in the same corpus document.")
    cap("R_26_cocitation_sources.png", "Co-citation network of sources", "Journals that are cited together, showing which disciplines the literature combines.",
        "bibliometrix::metaTagExtraction(CR_SO) then biblioNetwork(co-citation, sources); top 40 sources.", "Generic labels such as BOOK or PREPRINT are pooled categories, not single outlets.")
  })
  run("bibliographic_coupling", {
    NM <- biblioNetwork(M, analysis = "coupling", network = "references", sep = ";")
    vos_export(NM, "bibliographic_coupling_documents", 250, "References")
    netfig(NM, "R_27_bibliographic_coupling", "Bibliographic coupling of documents (top 60 by reference count)", n = 60, normalize = "salton", labelsize = 0.6,
           sub = "Node = corpus document; edge = shared references (Salton-normalised); colour = Louvain cluster.")
    cap("R_27_bibliographic_coupling.png", "Bibliographic coupling", "Corpus documents linked when they cite the same references: groups of papers working from the same prior literature.",
        "bibliometrix::biblioNetwork(coupling, references); the 60 documents with the longest reference lists; Salton normalisation; Louvain clusters.",
        "Selecting by reference-list length favours reviews and long articles; documents with no indexed references cannot appear.")
  })
  run("historiograph", {
    Mh <- M; Mh$CR[Mh$CR == ""] <- "NO REFERENCE LIST, 0, NONE"   # histNetwork fails on documents with an empty reference field
    hr <- histNetwork(Mh, min.citations = 1, sep = ";", verbose = FALSE)
    hp <- histPlot(hr, n = 25, size = 4, labelsize = 3, verbose = FALSE)
    savep(hp$g + labs(title = "Historiograph: direct citation network of the 25 most locally cited documents", subtitle = SRC), "R_28_historiograph", 13, 8)
    wcsv(hr$histData, "R_historiograph_data")
    cap("R_28_historiograph.png", "Historiograph (direct citation network)", "Chronological map of who cites whom among the 25 most locally cited corpus documents; arrows run from the cited to the citing paper along the time axis.",
        "bibliometrix::histNetwork(min.citations = 1) and histPlot(n = 25). A Python version built from exact OpenAlex ids is in py_citation_network.html and py_main_path.png.",
        "bibliometrix matches citations by DOI/label strings, so a few links can be missed; compare with the exact-id Python network.")
  })
  run("collaboration_authors", {
    NM <- biblioNetwork(M, analysis = "collaboration", network = "authors", sep = ";")
    vos_export(NM, "coauthorship_authors", 300, "Documents")
    netfig(NM, "R_29_collaboration_authors", "Author collaboration network (top 50 authors)", n = 50,
           sub = "Node size = documents; edge = co-authorship; colour = Louvain cluster. Isolated authors are removed.")
    cap("R_29_collaboration_authors.png", "Author collaboration network", "Co-authorship among the 50 most productive authors.", "bibliometrix::biblioNetwork(collaboration, authors); association normalisation; Louvain clusters; isolates removed.",
        "Most authors appear once in a topical corpus, so this shows a few teams, not the field's whole social structure.")
  })
  run("collaboration_institutions", {
    Mu <- M[M$AU_UN != "", ]
    NM <- biblioNetwork(Mu, analysis = "collaboration", network = "universities", sep = ";")
    vos_export(NM, "coauthorship_institutions", 300, "Documents")
    netfig(NM, "R_30_collaboration_institutions", "Institution collaboration network (top 40 institutions)", n = 40,
           sub = "Node size = documents; edge = co-authored documents between institutions; colour = Louvain cluster.")
    cap("R_30_collaboration_institutions.png", "Institution collaboration network", "Which institutions co-author within the corpus.", "bibliometrix::biblioNetwork(collaboration, universities) on OpenAlex institutions.",
        "Limited to records with affiliation data; multi-campus systems may appear as separate nodes.")
  })
  run("collaboration_countries", {
    Mc <- M[M$AU_CO != "", ]
    NM <- biblioNetwork(Mc, analysis = "collaboration", network = "countries", sep = ";")
    vos_export(NM, "coauthorship_countries", 100, "Documents")
    netfig(NM, "R_31_collaboration_countries", "Country collaboration network", n = 30,
           sub = "Node size = documents; edge = internationally co-authored documents; colour = Louvain cluster.")
    cap("R_31_collaboration_countries.png", "Country collaboration network", "International co-authorship links between the 30 most productive countries.", "bibliometrix::biblioNetwork(collaboration, countries).",
        "Based on author addresses only; says nothing about which countries are studied.")
  })
  run("three_field_plot", {
    w <- threeFieldsPlot(M, fields = c("AU_CO", "DE", "SO"), n = c(12, 15, 12))
    htmlwidgets::saveWidget(w, file.path(FIG, "R_32_three_field_plot_country_keyword_source.html"), selfcontained = FALSE, libdir = "html_libs", title = "Three-field plot")
    w2 <- threeFieldsPlot(M, fields = c("CR", "AU", "DE"), n = c(12, 12, 12))
    htmlwidgets::saveWidget(w2, file.path(FIG, "R_32_three_field_plot_reference_author_keyword.html"), selfcontained = FALSE, libdir = "html_libs", title = "Three-field plot")
    cap("R_32_three_field_plot_country_keyword_source.html", "Three-field plot: country - keyword - source", "Interactive Sankey linking author countries (left), keywords (middle) and sources (right). Saved as HTML because plotly cannot be rendered to PNG headlessly on this machine.",
        "bibliometrix::threeFieldsPlot(fields = AU_CO, DE, SO; top 12/15/12).", "Only the top items of each field are shown; flows are counts of co-appearance, not causal links.")
    cap("R_32_three_field_plot_reference_author_keyword.html", "Three-field plot: cited reference - author - keyword", "Interactive Sankey linking the most cited references (left), the most productive authors (middle) and keywords (right).",
        "bibliometrix::threeFieldsPlot(fields = CR, AU, DE; top 12 each).", "Top-12 cut-offs hide most of the corpus; use it to spot schools of thought, not to count.")
  })
}

write_json(CAPS, file.path(FIG, "_captions_R.json"), auto_unbox = TRUE, pretty = TRUE)
wcsv(do.call(rbind, LOG), "R_analysis_log")
cat("R analysis finished:", sum(sapply(LOG, function(x) x$status == "ok")), "ok of", length(LOG), "\n")
