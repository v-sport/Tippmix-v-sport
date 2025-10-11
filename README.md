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

# send a hello message to Telegram (uses env vars)
TELEGRAM_BOT_TOKEN=123:abc TELEGRAM_CHAT_ID=987654321 \
  python -m scraper.cli hello "Szia! Ez egy próba üzenet."
```

### Telegram setup

- Set environment variables before using `hello`:
  - `TELEGRAM_BOT_TOKEN`: your bot token from BotFather
  - `TELEGRAM_CHAT_ID`: numeric chat id (user/group/channel)
- Optional: pass a custom message after `hello`. If omitted, a default greeting is sent.
