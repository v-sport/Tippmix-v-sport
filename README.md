# Tippmix-v-sport
V-sport tipp adó bot telegramra és adat kaparás

## Scraper/poller

- VF endpoints (no Selenium):
  - timings: `/vflmshop/timeline/get-timings/get-timings.json`
  - matches: `/vflmshop/timeline/get-matches/get-matches.json?competition_id=...`

### Run

```
python -m scraper.cli                    # quick check endpoints + widgets loader
python -m scraper.cli poll               # start continuous poller
python -m scraper.cli poll-once          # fetch single snapshot and exit

# with sinks
python -m scraper.cli poll-once events.jsonl events.csv
python -m scraper.cli poll events.jsonl events.csv
```
