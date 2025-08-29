import json
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .poller import VfPoller


HEADERS = {"User-Agent": "Mozilla/5.0"}
VF_BASE = "https://vfscigaming.aitcloud.de"
VSWIDGETS_LOADER = "https://vsw.live.vsports.cloud/ls/vswidgets/?/scigamingscigamingcdn/zh/page/vswidgets"


def http_get(url: str, timeout: int = 15) -> tuple[int, bytes]:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as r:
        return r.getcode(), r.read()


def test_vf_endpoints() -> bool:
    print("[VF] timings →", end=" ")
    try:
        code, data = http_get(f"{VF_BASE}/vflmshop/timeline/get-timings/get-timings.json")
        print(code, f"{len(data)} bytes")
        txt = data.decode("utf-8", "ignore")
        m = re.search(r'"competition_id":(\d+)', txt)
        if not m:
            print("[VF] competition_id not found in timings")
            return False
        comp_id = m.group(1)
        print("[VF] competition_id:", comp_id)
        print("[VF] matches →", end=" ")
        code2, data2 = http_get(f"{VF_BASE}/vflmshop/timeline/get-matches/get-matches.json?competition_id={comp_id}")
        print(code2, f"{len(data2)} bytes")
        return code == 200 and code2 == 200
    except (URLError, HTTPError) as e:
        print("ERROR:", e)
        return False


def test_vswidgets_loader() -> bool:
    print("[VSW] loader →", end=" ")
    try:
        code, data = http_get(VSWIDGETS_LOADER)
        print(code, f"{len(data)} bytes")
        return code == 200 and len(data) > 1000
    except (URLError, HTTPError) as e:
        print("ERROR:", e)
        return False


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {"poll", "poll-once"}:
        once = sys.argv[1] == "poll-once"
        jsonl_path = None
        csv_path = None
        # optional: python -m scraper.cli poll logs.jsonl logs.csv
        if len(sys.argv) > 2:
            jsonl_path = sys.argv[2]
        if len(sys.argv) > 3:
            csv_path = sys.argv[3]
        try:
            VfPoller(jsonl_path=jsonl_path, csv_path=csv_path).run(once=once)
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            print("[ERROR] poller:", e)
            return 2

    ok_vf = test_vf_endpoints()
    ok_vsw = test_vswidgets_loader()
    all_ok = ok_vf and ok_vsw
    print("[RESULT] Selenium required:", "NO" if all_ok else "UNKNOWN/REVIEW")
    print("Usage: python -m scraper.cli poll [events.jsonl] [events.csv] | poll-once [events.jsonl] [events.csv]")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

