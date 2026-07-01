import json
from pathlib import Path

from gm import chesscom

FIX = Path(__file__).parent / "fixtures" / "month_sample.json"


def test_normalize_white_win():
    raw = json.loads(FIX.read_text())["games"][0]
    g = chesscom.normalize(raw, "eric")
    assert g["uuid"] == "g1"
    assert g["color"] == "white"
    assert g["result"] == "win"
    assert g["my_rating"] == 1450 and g["opp_rating"] == 1440
    assert g["accuracy_self"] == 83.1
    assert g["opening_name"] == "Italian Game"
    assert g["time_class"] == "bullet"


def test_normalize_black_loss():
    raw = json.loads(FIX.read_text())["games"][1]
    g = chesscom.normalize(raw, "eric")
    assert g["color"] == "black"
    assert g["result"] == "loss"
    assert g["accuracy_self"] == 55.5


def test_username_match_is_case_insensitive():
    raw = json.loads(FIX.read_text())["games"][0]
    g = chesscom.normalize(raw, "ERIC")
    assert g["color"] == "white"


def _pgn(url):
    return f'[ECO "C45"]\n[ECOUrl "{url}"]\n\n1. e4 e5 *'


def test_opening_from_ecourl_deslugs_and_strips_moves():
    p = _pgn("https://www.chess.com/openings/Scotch-Game-4...Nf6-5.Nxc6")
    assert chesscom._opening_from_pgn(p) == "Scotch Game"


def test_opening_restores_known_compounds_and_possessives():
    assert chesscom._opening_from_pgn(
        _pgn("https://www.chess.com/openings/Sicilian-Defense-Smith-Morra-Gambit-Accepted-4.Nxc3")
    ) == "Sicilian Defense Smith-Morra Gambit Accepted"
    assert chesscom._opening_from_pgn(
        _pgn("https://www.chess.com/openings/Kings-Gambit-Declined-Queens-Knight-Defense")
    ) == "King's Gambit Declined Queen's Knight Defense"
    assert chesscom._opening_from_pgn(
        _pgn("https://www.chess.com/openings/Queens-Pawn-Opening-Blackmar-Diemer-Gambit")
    ) == "Queen's Pawn Opening Blackmar-Diemer Gambit"


def test_opening_cleans_duplicated_slug_word_and_possessives():
    assert chesscom._opening_from_pgn(
        _pgn("https://www.chess.com/openings/Queens-Pawn-Opening-Blackmar-Blackmar-Diemer-Gambit")
    ) == "Queen's Pawn Opening Blackmar-Diemer Gambit"
    assert chesscom._opening_from_pgn(
        _pgn("https://www.chess.com/openings/Bishops-Opening")) == "Bishop's Opening"
    assert chesscom._opening_from_pgn(
        _pgn("https://www.chess.com/openings/Van-t-Kruijs-Opening")) == "Van't Kruijs Opening"


def test_opening_none_without_ecourl():
    assert chesscom._opening_from_pgn('[ECO "C45"]\n\n1. e4 *') is None


def test_normalize_prefers_ecourl_over_opening_tag():
    raw = json.loads(FIX.read_text())["games"][0]
    raw = dict(raw)
    raw["pgn"] = ('[ECO "C50"]\n[Opening "Italian Game"]\n'
                  '[ECOUrl "https://www.chess.com/openings/Italian-Game-Two-Knights-Defense"]\n\n1. e4 *')
    g = chesscom.normalize(raw, "eric")
    assert g["opening_name"] == "Italian Game Two Knights Defense"
