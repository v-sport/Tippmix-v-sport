import json
import os
import re
import time
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


HEADERS = {"User-Agent": "Mozilla/5.0"}
VF_BASE = "https://vfscigaming.aitcloud.de"


def http_get(url: str, timeout: int = 15) -> tuple[int, bytes]:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as r:
        return r.getcode(), r.read()


def save_json(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def extract_competition_id(timings_text: str) -> Optional[str]:
    m = re.search(r'"competition_id":(\d+)', timings_text)
    return m.group(1) if m else None


def poll_vf_timings(output_path: str) -> Optional[str]:
    code, data = http_get(f"{VF_BASE}/vflmshop/timeline/get-timings/get-timings.json")
    if code != 200:
        raise RuntimeError(f"timings http {code}")
    txt = data.decode("utf-8", "ignore")
    try:
        payload = json.loads(txt)
    except json.JSONDecodeError:
        payload = {"raw": txt}
    save_json(output_path, payload)
    return extract_competition_id(txt)


def poll_vf_matches(comp_id: str, output_path: str) -> None:
    code, data = http_get(f"{VF_BASE}/vflmshop/timeline/get-matches/get-matches.json?competition_id={comp_id}")
    if code != 200:
        raise RuntimeError(f"matches http {code}")
    txt = data.decode("utf-8", "ignore")
    try:
        payload = json.loads(txt)
    except json.JSONDecodeError:
        payload = {"raw": txt}
    save_json(output_path, payload)


def run_loop(data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    timings_file = os.path.join(data_dir, "timings.json")
    matches_file = os.path.join(data_dir, "matches.json")

    last_comp = None
    last_matches_ts = 0.0

    while True:
        try:
            comp = poll_vf_timings(timings_file)
            now = time.time()
            fetch_matches = False
            if comp and comp != last_comp:
                fetch_matches = True
                last_comp = comp
            elif now - last_matches_ts > 60:
                fetch_matches = True
            if fetch_matches and last_comp:
                poll_vf_matches(last_comp, matches_file)
                last_matches_ts = now
            print(f"[loop] timings ok, comp={last_comp} matches_refreshed={fetch_matches}")
        except (HTTPError, URLError) as e:
            print("[loop] HTTP error:", e)
        except Exception as e:
            print("[loop] error:", e)
        time.sleep(2)

