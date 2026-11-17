PY=/c/Users/seans/AppData/Local/Programs/Python/Python313/python.exe
R=D:/Research-Publishing/02-malaysian-snr/rework-v3
cd $R
$PY -I code/duka_spreads.py > logs/spreads.log 2>&1
$PY -I code/analysis.py new > logs/analysis_final.log 2>&1
$PY -I code/year_by_class.py > logs/year_by_class.log 2>&1
$PY -I code/repro_check.py > logs/repro.log 2>&1
$PY -I code/figures.py > logs/figs.log 2>&1
$PY -I code/build_v17.py > logs/build.log 2>&1
$PY -I code/make_changes.py >> logs/build.log 2>&1
echo FINALDONE > logs/final.done
