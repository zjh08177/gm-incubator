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


# Chess.com's ECOUrl slug carries the human opening name and reflects the full
# move sequence (their classifier walks many plies), unlike the coarse ECO code.
_COMPOUND_FIXUPS = [
    ("Smith Morra", "Smith-Morra"),
    ("Blackmar Diemer", "Blackmar-Diemer"),
    ("Caro Kann", "Caro-Kann"),
    ("Nimzowitsch Larsen", "Nimzowitsch-Larsen"),
    ("Bogo Indian", "Bogo-Indian"),
]
_POSSESSIVE = ("King", "Queen", "Bishop", "Owen")     # always possessive in opening names


def _deslug(slug: str) -> str | None:
    kept = []
    for tok in slug.split("-"):
        if tok[:1].isdigit():                 # move-notation onset (4.Nxc3 / 4...Nf6 / 1)
            break
        kept.append(tok)
    name = re.sub(r"\s+(?:with|and|the)\s*$", "", " ".join(kept), flags=re.I).strip()
    name = re.sub(r"\b(\w+) \1\b", r"\1", name)        # drop slug-duplicated word (Blackmar Blackmar)
    for a, b in _COMPOUND_FIXUPS:
        name = name.replace(a, b)
    for w in _POSSESSIVE:
        name = re.sub(rf"\b{w}s\b", f"{w}'s", name)
    return name.replace("Van t ", "Van't ") or None


def _opening_from_pgn(pgn: str) -> str | None:
    m = re.search(r'/openings/([^"?#\s]+)', pgn or "")
    return _deslug(m.group(1)) if m else None


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
        "opening_name": _opening_from_pgn(raw.get("pgn", "")) or _tag(raw.get("pgn", ""), "Opening"),
        "accuracy_self": acc.get(mine),
        "pgn": raw.get("pgn"),
    }
