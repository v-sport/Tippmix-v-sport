#!/usr/bin/env python3
"""
Lekéri az aktuális competition (szezon) azonosítóját és a meccsekből kigyűjti a fordulókat.
Kimenet: emberi olvasható és opcionálisan JSON (stdout).
Futtatás: python -m scraper.get_season_round
"""
import sys
import json
from scraper.poller import VfPoller

def normalize_round(r):
    # próbáljuk számként kezelni, ha lehetséges
    try:
        return int(r)
    except Exception:
        return r

def main():
    p = VfPoller()
    timings, server_ts = p.fetch_timings()
    if not timings:
        print("timings fetch failed (no data). Ellenőrizd az internetkapcsolatot és a VF_BASE elérhetőségét.", file=sys.stderr)
        return 2

    competition = timings.get("competition") or {}
    comp_id = p.extract_competition_id(timings)
    if comp_id is None:
        print("competition_id nem található a timings-ben.", file=sys.stderr)
        return 3

    matches = p.fetch_matches(comp_id)
    if not matches:
        print(f"matches fetch failed (no data for competition_id={comp_id}).", file=sys.stderr)
        return 4

    rounds = set()
    examples = []
    for ch in matches.get("channels", []):
        for m in ch.get("matches", []):
            r = m.get("round") or m.get("matchday")
            if r is None:
                vm = m.get("vmatch_group", {}) or {}
                r = vm.get("round") or vm.get("matchday")
            if r is None:
                r = f"Unknown(match_id={m.get('id')})"
            rounds.add(str(r))
            if len(examples) < 5:
                vm = m.get("vmatch_group", {}) or {}
                home = vm.get("home_team") or m.get("home_team") or m.get("home") or ""
                away = vm.get("away_team") or m.get("away_team") or m.get("away") or ""
                start = m.get("start_datetime") or m.get("start") or ""
                examples.append({
                    "id": m.get("id"),
                    "round": str(r),
                    "home": home,
                    "away": away,
                    "start": start
                })

    # rendezés: ha számok, számrend; egyébként lexikografikusan
    def sort_key(x):
        try:
            return (0, int(x))
        except Exception:
            return (1, x)

    rounds_list = sorted(list(rounds), key=sort_key)

    out = {
        "competition": {
            "id": competition.get("id"),
            "name": competition.get("name")
        },
        "competition_id_used": comp_id,
        "rounds": rounds_list,
        "examples": examples
    }

    # Emberi kimenet
    print(f"Competition: {out['competition']['id']} - {out['competition']['name']}")
    print(f"Competition_id used: {out['competition_id_used']}")
    print(f"Found rounds ({len(out['rounds'])}):")
    for r in out["rounds"]:
        print(" -", r)
    print("\nExamples (max 5):")
    for e in out["examples"]:
        print(f"  id={e['id']} round={e['round']} {e['home']} vs {e['away']} start={e['start']}")

    # JSON duplicát kinyomtatása opcionálisan (ha kell más tool-nak)
    print("\n# JSON output")
    print(json.dumps(out, ensure_ascii=False, indent=2))

    return 0

if __name__ == "__main__":
    sys.exit(main())