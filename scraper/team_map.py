import json
import re
from typing import Dict


def load_team_map_from_target_html(path: str = "target.html") -> Dict[int, str]:
    """Parse teamIds and translatedTeamList from target.html and return id->name map.

    Preference order:
      1) translatedTeamList.long if present
      2) fallback to placeholder name like "Team <id>"
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Extract the translatedTeamList JSON object
    # Pattern around: srvg.translation.translatedTeamList  = { ... };
    m = re.search(r"translatedTeamList\s*=\s*(\{.*?\});", text, flags=re.S)
    translated: Dict[str, dict] = {}
    if m:
        blob = m.group(1)
        try:
            translated = json.loads(blob)
        except Exception:
            # Try to loosen JSON (allow unescaped unicode already okay, keys are quoted)
            translated = json.loads(blob)

    # Map id->long name if available
    id_to_name: Dict[int, str] = {}
    for string_id, obj in translated.items():
        try:
            tid = int(obj.get("id") or 0)
        except Exception:
            continue
        name = None
        tr = obj.get("translation") or {}
        if isinstance(tr, dict):
            name = tr.get("long") or tr.get("short")
        if not name:
            name = obj.get("long") or obj.get("short")
        if not name:
            name = f"Team {tid}"
        id_to_name[tid] = name

    # There is also srvg.customization.teamIds mapping VF club_id -> team id, but
    # for readable naming from matches payload we use the long names from translatedTeamList
    return id_to_name

