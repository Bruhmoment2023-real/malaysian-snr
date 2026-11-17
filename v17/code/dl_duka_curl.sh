# Dukascopy 1h BID/ASK monthly bi5, SAMPLE months only (June of each year 2010-2026) to calibrate real bid-ask spreads of XAUUSD/XAGUSD.
# curl, 8 s spacing, 90 s back-off; raw files stay local (not redistributed).
R=D:/Research-Publishing/02-malaysian-snr/rework-v3/data/duka_raw
for y in 2012 2016 2020 2024 2026 2014 2018 2022 2010 2011 2013 2015 2017 2019 2021 2023 2025; do for s in XAUUSD XAGUSD; do for side in BID ASK; do
  mm=05; f=$R/$s/${side}_${y}_${mm}.bi5; mkdir -p $R/$s
  [ -f $f ] && continue
  for try in 1 2 3 4 5 6 7 8; do
    sleep 8
    code=$(curl -s -m 45 -o $f.tmp -w "%{http_code}" -A "academic-research-client/1.0" "https://datafeed.dukascopy.com/datafeed/$s/$y/$mm/${side}_candles_hour_1.bi5")
    if [ "$code" = 200 ]; then mv $f.tmp $f; break; elif [ "$code" = 404 ]; then : > $f; rm -f $f.tmp; break; else rm -f $f.tmp; sleep 90; fi
  done
done; done; echo "done $y"; done
echo ALLDONE
