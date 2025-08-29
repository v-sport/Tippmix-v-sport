import time
import json
from typing import Any, Dict, Optional, Tuple
import csv

import requests


HEADERS = {"User-Agent": "Mozilla/5.0"}
VF_BASE = "https://vfscigaming.aitcloud.de"


def _http_get(url: str, timeout: int = 15) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    data: Dict[str, Any]
    try:
        data = resp.json()
    except ValueError:
        # try rescue malformed content by decoding then json loads
        data = json.loads(resp.text) if resp.text else {}
    return resp.status_code, data, dict(resp.headers)


class VfPoller:
    def __init__(self, base_url: str = VF_BASE, jsonl_path: Optional[str] = None, csv_path: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.last_timings: Optional[Dict[str, Any]] = None
        self.last_matches: Optional[Dict[str, Any]] = None
        self.jsonl_path = jsonl_path
        self.csv_path = csv_path

    def timings_url(self) -> str:
        return f"{self.base_url}/vflmshop/timeline/get-timings/get-timings.json"

    def matches_url(self, competition_id: int) -> str:
        return f"{self.base_url}/vflmshop/timeline/get-matches/get-matches.json?competition_id={competition_id}"

    def fetch_timings(self) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        code, data, _headers = _http_get(self.timings_url())
        if code != 200:
            return None, None
        server_ts = None
        if isinstance(data, dict):
            server_ts = data.get("server_datetime")
        return data, server_ts

    def extract_competition_id(self, timings: Dict[str, Any]) -> Optional[int]:
        comp = timings.get("competition") or {}
        comp_id = comp.get("id")
        try:
            return int(comp_id) if comp_id is not None else None
        except (TypeError, ValueError):
            return None

    def fetch_matches(self, competition_id: int) -> Optional[Dict[str, Any]]:
        code, data, _headers = _http_get(self.matches_url(competition_id))
        if code != 200:
            return None
        return data

    def _next_poll_delay_ms(self, timings: Dict[str, Any], server_ts: Optional[int]) -> int:
        # Default delays tuned to be safe and not too chatty
        poll_min_ms = 1000
        poll_unknown_ms = 10000

        channels = timings.get("channels") or []
        next_end: Optional[int] = None
        for ch in channels:
            # timelineWorker uses channels[i].active_phase_end_datetime
            end_ts = ch.get("active_phase_end_datetime")
            if isinstance(end_ts, int):
                if next_end is None or end_ts < next_end:
                    next_end = end_ts

        if next_end is None:
            return poll_unknown_ms

        now_server = server_ts if isinstance(server_ts, int) else None
        if now_server is None:
            # fall back if server datetime not provided
            return poll_unknown_ms

        delta_ms = max((next_end - now_server) * 1000, poll_min_ms)
        return int(delta_ms)

    def run(self, once: bool = False) -> None:
        """Continuously poll the VF timings/matches endpoints and print updates.

        If once=True, fetch a single timings+matches snapshot and exit.
        """
        while True:
            timings, server_ts = self.fetch_timings()
            if not timings:
                print("[VF] timings: request failed")
                # back off a bit
                time.sleep(10)
                if once:
                    return
                continue

            comp_id = self.extract_competition_id(timings)
            if comp_id is None:
                print("[VF] timings: competition_id not found")
                delay_ms = self._next_poll_delay_ms(timings, server_ts)
                if once:
                    return
                time.sleep(delay_ms / 1000.0)
                continue

            matches = self.fetch_matches(comp_id)

            fresh_timings = timings != self.last_timings
            fresh_matches = matches is not None and matches != self.last_matches

            if fresh_timings:
                self.last_timings = timings
                channels = timings.get("channels") or []
                summary = []
                for ch in channels:
                    mid = ch.get("match_id")
                    next_mid = ch.get("next_match_id")
                    aend = ch.get("active_phase_end_datetime")
                    summary.append(f"ch:match={mid} next={next_mid} phase_end={aend}")
                print(f"[VF] timings update: server={server_ts} | " + "; ".join(summary))
                self._write_jsonl({
                    "type": "timings",
                    "server_datetime": server_ts,
                    "payload": timings,
                })
                self._write_csv_timings(server_ts, channels)

            if fresh_matches:
                self.last_matches = matches
                total = 0
                try:
                    for ch in matches.get("channels", []):
                        total += len(ch.get("matches", []))
                except Exception:
                    total = 0
                print(f"[VF] matches update: competition_id={comp_id} entries={total}")
                self._write_jsonl({
                    "type": "matches",
                    "competition_id": comp_id,
                    "payload": matches,
                })
                self._write_csv_matches(comp_id, matches)

            delay_ms = self._next_poll_delay_ms(timings, server_ts)
            if once:
                return
            time.sleep(delay_ms / 1000.0)

    def _write_jsonl(self, obj: Dict[str, Any]) -> None:
        if not self.jsonl_path:
            return
        try:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        except Exception:
            # best-effort logging only
            pass

    def _write_csv_timings(self, server_ts: Optional[int], channels: Any) -> None:
        if not self.csv_path:
            return
        try:
            is_new = False
            try:
                with open(self.csv_path, "r", encoding="utf-8"):
                    pass
            except FileNotFoundError:
                is_new = True
            with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(["type", "server_datetime", "channel_match_id", "channel_next_match_id", "active_phase_end"])
                for ch in channels:
                    writer.writerow([
                        "timings",
                        server_ts,
                        ch.get("match_id"),
                        ch.get("next_match_id"),
                        ch.get("active_phase_end_datetime"),
                    ])
        except Exception:
            pass

    def _write_csv_matches(self, competition_id: int, matches: Dict[str, Any]) -> None:
        if not self.csv_path:
            return
        try:
            is_new = False
            try:
                with open(self.csv_path, "r", encoding="utf-8"):
                    pass
            except FileNotFoundError:
                is_new = True
            with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(["type", "competition_id", "match_id", "chunk_id", "betstop", "start", "end", "home_club_id", "away_club_id"])
                for ch in matches.get("channels", []):
                    for m in ch.get("matches", []):
                        vm = m.get("vmatch_group", {})
                        writer.writerow([
                            "matches",
                            competition_id,
                            m.get("id"),
                            m.get("chunk_id"),
                            m.get("betstop_datetime"),
                            m.get("start_datetime"),
                            m.get("end_datetime"),
                            vm.get("home_club_id"),
                            vm.get("away_club_id"),
                        ])
        except Exception:
            pass


def main_once() -> None:
    VfPoller().run(once=True)


if __name__ == "__main__":
    main_once()

