import json
from typing import Any, Dict, List, Optional, Tuple

import requests

from .team_map import load_team_map_from_target_html


HEADERS = {"User-Agent": "Mozilla/5.0"}
VF_BASE = "https://vfscigaming.aitcloud.de"


def http_get_json(url: str, timeout: int = 15) -> Dict[str, Any]:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_timings() -> Dict[str, Any]:
    return http_get_json(f"{VF_BASE}/vflmshop/timeline/get-timings/get-timings.json")


def fetch_matches(competition_id: int) -> Dict[str, Any]:
    return http_get_json(
        f"{VF_BASE}/vflmshop/timeline/get-matches/get-matches.json?competition_id={competition_id}"
    )


def index_matches_by_id(matches_payload: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    idx: Dict[int, Dict[str, Any]] = {}
    for ch in matches_payload.get("channels", []):
        for m in ch.get("matches", []):
            mid = m.get("id")
            if isinstance(mid, int):
                idx[mid] = m
    return idx


def hname(team_map: Dict[int, str], club_id: Optional[int]) -> str:
    if isinstance(club_id, int):
        return team_map.get(club_id, f"Team {club_id}")
    return ""


def main() -> None:
    team_map = load_team_map_from_target_html("target.html")

    t = fetch_timings()
    server_ts = int(t.get("server_datetime") or 0)
    comp = t.get("competition") or {}
    competition_id = int(comp.get("id") or 0)

    m = fetch_matches(competition_id)
    midx = index_matches_by_id(m)

    # Következő 8 meccs: csatornánként a next_match_id
    next_pairs: List[Tuple[int, int, int, str, str, int]] = []
    for ch in t.get("channels", []):
        ch_next = ch.get("next_match_id") or ch.get("match_id")
        if not isinstance(ch_next, int):
            continue
        mo = midx.get(ch_next)
        if not mo:
            continue
        vm = mo.get("vmatch_group", {})
        hid = vm.get("home_club_id")
        aid = vm.get("away_club_id")
        start_ts = int(mo.get("start_datetime") or 0)
        next_pairs.append((ch.get("id", -1), ch_next, start_ts, hname(team_map, hid), hname(team_map, aid), start_ts))

    # Előző 8 meccs: csatornánként a legutóbb befejezett (end_datetime < server_ts)
    prev_results: List[Tuple[int, int, int, str, str, int]] = []
    for ch in t.get("channels", []):
        last_mo = None
        last_end = -1
        for mo in m.get("channels", [])[ch.get("id", 0) - 1].get("matches", []):
            ed = int(mo.get("end_datetime") or 0)
            if ed < server_ts and ed > last_end:
                last_end = ed
                last_mo = mo
        if last_mo:
            vm = last_mo.get("vmatch_group", {})
            hid = vm.get("home_club_id")
            aid = vm.get("away_club_id")
            prev_results.append((ch.get("id", -1), last_mo.get("id"), last_end, hname(team_map, hid), hname(team_map, aid), last_end))

    print("=== Következő forduló 8 meccs (csatornánként) ===")
    for ch_id, mid, st, hn, an, _ in sorted(next_pairs, key=lambda x: x[0]):
        print(f"csatorna={ch_id} match_id={mid} kezdés={st} párosítás={hn} vs {an}")

    print("\n=== Előző forduló 8 meccs (csatornánként, lezártak) ===")
    for ch_id, mid, ed, hn, an, _ in sorted(prev_results, key=lambda x: x[0]):
        print(f"csatorna={ch_id} match_id={mid} vége={ed} párosítás={hn} vs {an} eredmény=(n/a)")

    # H2H és tabella: linkek (ha elérhetők)
    # Próbáljuk kinyerni season_id-t a timetable-ból (sr_table_id gyakran megfelel).
    season_id = None
    try:
        # get-timings struktúrából próbálunk sr_table_id-t keresni
        ch0 = t.get("channels", [])[0]
        # keresünk a matches listában a competitionstage.competition.sr_table_id-t
        for mo in m.get("channels", [])[0].get("matches", []):
            cs = (((mo.get("matchset") or {}).get("competitionstage") or {}).get("competition") or {})
            sid = cs.get("sr_table_id")
            if sid:
                season_id = int(sid)
                break
    except Exception:
        season_id = None

    if season_id:
        print(f"\nH2H példa link (nem garantáltan publikus): https://s5.sir.sportradar.com/scigamingvirtuals/zh/1/season/{season_id}/h2h/<team1>/<team2>")
        print(f"Tabella példa link: https://s5.sir.sportradar.com/scigamingvirtuals/zh/1/season/{season_id}/standings")
    else:
        print("\nH2H/Tabella: publikus linkhez szükséges season_id nem elérhető megbízhatóan a publikus JSON-ból.")


if __name__ == "__main__":
    main()

