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
