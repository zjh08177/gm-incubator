import re
import time

import httpx

USER_AGENT = "gm-chess-coach/0.1 (contact: ericzjh08177@gmail.com)"


def _client(client=None):
    return client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30)


def _get_json(url, client, retries=4):
    c = _client(client)
    r = None
    for attempt in range(retries):
        r = c.get(url)
        if r.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def get_archives(username, client=None) -> list[str]:
    data = _get_json(f"https://api.chess.com/pub/player/{username}/games/archives", client)
    return data.get("archives", [])


def get_month(url, client=None) -> list[dict]:
    return _get_json(url, client).get("games", [])


def _result(chesscom_result: str) -> str:
    if chesscom_result == "win":
        return "win"
    if chesscom_result in {"agreed", "repetition", "stalemate", "insufficient",
                           "50move", "timevsinsufficient"}:
        return "draw"
    return "loss"


def _tag(pgn: str, name: str) -> str | None:
    m = re.search(rf'\[{name} "([^"]*)"\]', pgn or "")
    return m.group(1) if m else None


def normalize(raw: dict, username: str) -> dict:
    u = username.lower()
    mine, opp = ("white", "black") if raw["white"]["username"].lower() == u else ("black", "white")
    acc = raw.get("accuracies") or {}
    return {
        "uuid": raw["uuid"],
        "url": raw.get("url"),
        "end_time": raw.get("end_time"),
        "time_class": raw.get("time_class"),
        "time_control": raw.get("time_control"),
        "color": mine,
        "result": _result(raw[mine]["result"]),
        "my_rating": raw[mine].get("rating"),
        "opp_rating": raw[opp].get("rating"),
        "eco": _tag(raw.get("pgn", ""), "ECO"),
        "opening_name": _tag(raw.get("pgn", ""), "Opening"),
        "accuracy_self": acc.get(mine),
        "pgn": raw.get("pgn"),
    }
