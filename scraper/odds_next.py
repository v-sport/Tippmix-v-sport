import csv
import json
from typing import List, Tuple

import requests


H = {"User-Agent": "Mozilla/5.0"}
VF = "https://vfscigaming.aitcloud.de"
W = "https://vgls.live.vsports.cloud/vfl/feeds/?/scigamingscigamingcdn/zh/Europe:Berlin/gismo"


def get_timings() -> dict:
    return requests.get(f"{VF}/vflmshop/timeline/get-timings/get-timings.json", headers=H, timeout=15).json()


def get_matches(comp_id: int) -> dict:
    return requests.get(
        f"{VF}/vflmshop/timeline/get-matches/get-matches.json?competition_id={comp_id}", headers=H, timeout=15
    ).json()


def next_eight_match_ids(timings: dict, matches: dict) -> List[int]:
    idx = {}
    for ch in matches.get("channels", []) or []:
        for mo in ch.get("matches", []) or []:
            idx[mo.get("id")] = mo
    ids: List[int] = []
    for ch in timings.get("channels", []) or []:
        mid = ch.get("next_match_id") or ch.get("match_id")
        if not mid:
            continue
        if mid not in idx:
            continue
        if mid not in ids:
            ids.append(mid)
    return ids[:8]


def fetch_match_odds(mid: int) -> dict:
    url = f"{W}/match_odds2/{mid}"
    r = requests.get(url, headers=H, timeout=15)
    r.raise_for_status()
    j = r.json()
    docs = j.get("doc") if isinstance(j, dict) else None
    if not isinstance(docs, list) or not docs:
        return {}
    return docs[0].get("data") or {}


def extract_home_away_and_1x2(data: dict) -> Tuple[str, str, List[Tuple[str, str]]]:
    teams = data.get("teams", {})
    home = teams.get("home", {}).get("name")
    away = teams.get("away", {}).get("name")
    main = {}
    # Prefer main 1X2 market: _otid == 2 and _fid in {1,2,3}
    for o in data.get("odds", []) or []:
        if o.get("_otid") == 2 and (o.get("_fid") in {1, 2, 3}):
            m = o.get("fieldname")
            if m in {"1", "x", "2"}:
                main[m] = o.get("value")
    # Fallback: first seen 1/x/2 if main not present
    if not main:
        for o in data.get("odds", []) or []:
            m = o.get("fieldname")
            if m in {"1", "x", "2"} and m not in main:
                main[m] = o.get("value")
    odds = [(k, main.get(k)) for k in ["1", "x", "2"] if k in main]
    return home or "", away or "", odds


def main() -> int:
    t = get_timings()
    comp_id = (t.get("competition") or {}).get("id")
    m = get_matches(comp_id)
    ids = next_eight_match_ids(t, m)
    rows = []
    for mid in ids:
        data = fetch_match_odds(mid)
        home, away, ox = extract_home_away_and_1x2(data)
        row = {"match_id": mid, "home": home, "away": away}
        for k, v in ox:
            row[k] = v
        rows.append(row)

    # Print
    for r in rows:
        print(f"{r['match_id']}: {r['home']} vs {r['away']} | 1={r.get('1','-')} X={r.get('x','-')} 2={r.get('2','-')}")

    # Optional CSV
    import sys
    if len(sys.argv) > 1:
        out = sys.argv[1]
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["match_id", "home", "away", "1", "x", "2"])
            w.writeheader()
            for r in rows:
                w.writerow({
                    "match_id": r.get("match_id"),
                    "home": r.get("home"),
                    "away": r.get("away"),
                    "1": r.get("1", ""),
                    "x": r.get("x", ""),
                    "2": r.get("2", ""),
                })

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

