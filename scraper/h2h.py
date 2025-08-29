import os
import re
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


HEADERS = {"User-Agent": "Mozilla/5.0"}
# Template from page config
H2H_TEMPLATE = (
    "https://s5.sir.sportradar.com/scigamingvirtuals/zh/1/season/%s/h2h/%s/%s"
)


def http_get(url: str, timeout: int = 15) -> tuple[int, bytes]:
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as r:
        return r.getcode(), r.read()


def fetch_h2h_html(season_id: str, team1: str, team2: str) -> str:
    url = H2H_TEMPLATE % (season_id, team1, team2)
    code, data = http_get(url)
    if code != 200:
        raise RuntimeError(f"H2H http {code}")
    return data.decode("utf-8", "ignore")


def extract_table_rows(html: str) -> list[str]:
    # crude extract of rows for quick persistence
    rows = re.findall(r"<tr[\s\S]*?</tr>", html, re.IGNORECASE)
    return rows


def save_text(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def run_sample(out_dir: str, season_id: str, team1: str, team2: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    html = fetch_h2h_html(season_id, team1, team2)
    save_text(os.path.join(out_dir, f"h2h_{team1}_{team2}.html"), html)
    rows = extract_table_rows(html)
    save_text(os.path.join(out_dir, f"h2h_{team1}_{team2}.rows.txt"), "\n".join(rows))

