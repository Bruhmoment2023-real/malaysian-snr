#!/bin/bash
# paper 02: master -> R -> figures (no VOSviewer CLI: it hung on a loaded laptop) 
cd /d/Research-Publishing/02-malaysian-snr/bibliometrics
PY=/d/Research-Publishing/_tools/biblio-venv/Scripts/python.exe
B="$(pwd -W)"
export R_LIBS_USER='D:\Research-Publishing\_tools\R-lib;C:\Users\seans\AppData\Local\R\win-library\4.5'
$PY python/kit/pipeline.py "$B" master > python/run_master2.log 2>&1
"/c/Program Files/R/R-4.5.3/bin/Rscript.exe" R/bibliometrix_analysis.R "$B" > R/run_kit.log 2>&1
$PY python/kit/figures.py "$B" --no-vos > python/run_figures.log 2>&1
echo CHAIN_DONE > python/chain.done
