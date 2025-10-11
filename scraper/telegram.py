import requests
from typing import Any, Dict, Optional, Union

TELEGRAM_API_BASE = "https://api.telegram.org"


def send_telegram_message(
    token: str,
    chat_id: Union[str, int],
    text: str,
    parse_mode: Optional[str] = None,
    disable_web_page_preview: bool = True,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Send a message via Telegram Bot API.

    Raises requests.HTTPError on non-2xx responses.
    Returns decoded JSON response from Telegram (dict with ok/result fields).
    """
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload: Dict[str, Any] = {
        "chat_id": str(chat_id),
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    data: Dict[str, Any] = response.json()
    if not isinstance(data, dict):
        raise ValueError("Unexpected Telegram API response type")
    return data
