import json
import csv
import re
from pathlib import Path
from typing import Dict, Any, Iterable


INPUT = Path("feeds.jsonl")
OUT_DIR = Path("feeds_out")


def iter_records() -> Iterable[Dict[str, Any]]:
    if not INPUT.exists():
        return []
    with INPUT.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def parse_jsonp_or_json(text: str) -> Any:
    text = text.strip()
    # Try plain JSON first
    try:
        return json.loads(text)
    except Exception:
        pass
    # JSONP like: callback({...})
    m = re.search(r"^[\w$]+\((.*)\)\s*;?\s*$", text, flags=re.S)
    if m:
        inner = m.group(1)
        return json.loads(inner)
    # Fallback: truncate trailing commas or invalid endings
    text2 = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text2)


def ensure_out():
    OUT_DIR.mkdir(exist_ok=True)


def write_csv(path: Path, header: Iterable[str], rows: Iterable[Iterable[Any]]):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(header))
        for r in rows:
            w.writerow(list(r))


def normalize() -> None:
    ensure_out()
    standings_rows = []
    results_rows = []
    odds_rows = []
    h2h_rows = []

    for rec in iter_records():
        url = rec.get("url", "")
        body = rec.get("body", "")
        if not body:
            continue
        try:
            data = parse_jsonp_or_json(body)
        except Exception:
            continue

        # Normalize Gismo envelope
        docs = data.get("doc") if isinstance(data, dict) else None
        if isinstance(docs, list) and docs and isinstance(docs[0], dict):
            payload = docs[0].get("data")
        else:
            payload = data

        # Standings
        if "vfl_tournament_livetablebyseasonandround" in url:
            if not payload or not isinstance(payload, dict):
                continue
            season = payload.get("seasonid")
            currentround = payload.get("currentround")
            for row in payload.get("tablerows", []) or []:
                team = row.get("team", {})
                standings_rows.append([
                    season,
                    currentround,
                    team.get("uid"),
                    team.get("name"),
                    row.get("pos"),
                    row.get("total"),
                    row.get("winTotal"),
                    row.get("drawTotal"),
                    row.get("lossTotal"),
                    row.get("goalsForTotal"),
                    row.get("goalsAgainstTotal"),
                    row.get("pointsTotal"),
                ])

        # Full event feed (results per match)
        elif "vfl_event_fullfeed" in url:
            if not payload or not isinstance(payload, dict):
                continue
            sports = payload
            for rc in sports.values():
                tmap = rc.get("tournaments") if isinstance(rc, dict) else None
                if not isinstance(tmap, dict):
                    continue
                for tdata in tmap.values():
                    matches = tdata.get("matches", {})
                    for match in matches.values():
                        mid = match.get("_id")
                        rd = match.get("round")
                        res = match.get("result", {})
                        teams = match.get("teams", {})
                        home = teams.get("home", {}).get("name")
                        away = teams.get("away", {}).get("name")
                        home_uid = teams.get("home", {}).get("uid")
                        away_uid = teams.get("away", {}).get("uid")
                        p1 = match.get("periods", {}).get("p1", {})
                        ft = match.get("periods", {}).get("ft", {})
                        results_rows.append([
                            mid, rd, home_uid, home, away_uid, away,
                            res.get("home"), res.get("away"),
                            p1.get("home"), p1.get("away"),
                            ft.get("home"), ft.get("away"),
                        ])

        # Match odds feed includes live score snapshot too
        elif "/match_odds2/" in url:
            if not payload or not isinstance(payload, dict):
                continue
            mid = payload.get("_id")
            season = payload.get("_seasonid")
            round_id = payload.get("round")
            teams = payload.get("teams", {})
            res = payload.get("result", {})
            odds = payload.get("odds", []) or []
            home = teams.get("home", {}).get("name")
            away = teams.get("away", {}).get("name")
            for o in odds:
                odds_rows.append([
                    mid, season, round_id, home, away,
                    o.get("fieldname"), o.get("value"), o.get("status"),
                ])
            # also emit to results if present
            if res:
                results_rows.append([
                    mid, round_id, teams.get("home", {}).get("uid"), home,
                    teams.get("away", {}).get("uid"), away,
                    res.get("home"), res.get("away"), None, None, None, None,
                ])

        # H2H recent
        elif "stats_uniquetournament_team_versusrecent" in url:
            if not payload or not isinstance(payload, dict):
                continue
            for m in payload.get("matches", []) or []:
                t = m.get("teams", {})
                res = m.get("result", {})
                p1 = m.get("periods", {}).get("p1", {})
                ft = m.get("periods", {}).get("ft", {})
                h2h_rows.append([
                    m.get("_id"), m.get("round"),
                    t.get("home", {}).get("uid"), t.get("home", {}).get("name"),
                    t.get("away", {}).get("uid"), t.get("away", {}).get("name"),
                    res.get("home"), res.get("away"),
                    p1.get("home"), p1.get("away"),
                    ft.get("home"), ft.get("away"),
                ])

        # Last X matches per team
        elif "stats_uniquetournament_team_lastx" in url:
            if not payload or not isinstance(payload, dict):
                continue
            team = payload.get("team", {})
            for m in payload.get("matches", []) or []:
                t = m.get("teams", {})
                res = m.get("result", {})
                p1 = m.get("periods", {}).get("p1", {})
                ft = m.get("periods", {}).get("ft", {})
                h2h_rows.append([
                    m.get("_id"), m.get("round"),
                    t.get("home", {}).get("uid"), t.get("home", {}).get("name"),
                    t.get("away", {}).get("uid"), t.get("away", {}).get("name"),
                    res.get("home"), res.get("away"),
                    p1.get("home"), p1.get("away"),
                    ft.get("home"), ft.get("away"),
                ])

    # Write CSVs
    write_csv(OUT_DIR / "standings.csv",
              ["season","round","team_uid","team","pos","played","win","draw","loss","gf","ga","pts"],
              standings_rows)
    write_csv(OUT_DIR / "results.csv",
              ["match_id","round","home_uid","home","away_uid","away","res_home","res_away","p1_home","p1_away","ft_home","ft_away"],
              results_rows)
    write_csv(OUT_DIR / "odds.csv",
              ["match_id","season","round","home","away","market","value","status"],
              odds_rows)
    write_csv(OUT_DIR / "h2h.csv",
              ["match_id","round","home_uid","home","away_uid","away","res_home","res_away","p1_home","p1_away","ft_home","ft_away"],
              h2h_rows)


if __name__ == "__main__":
    normalize()

