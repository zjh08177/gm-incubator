import chess

from gm.analysis import see


def classify(board_before: chess.Board, played_uci: str, best_uci: str,
             eval_best_cp: int, eval_played_cp: int,
             severity: str | None, phase: str) -> str | None:
    if severity is None:
        return None

    # 1) Winning endgame that slipped.
    if phase == "endgame" and eval_best_cp >= 200 and (eval_best_cp - eval_played_cp) >= 150:
        return "endgame_conversion"

    # 2) Missed your own tactic: best move was a winning capture/mate you skipped.
    if best_uci:
        best = chess.Move.from_uci(best_uci)
        best_is_capture = board_before.is_capture(best)
        if (eval_best_cp >= 300 and eval_best_cp - eval_played_cp >= 150
                and (best_is_capture or eval_best_cp >= 900)):
            played = chess.Move.from_uci(played_uci)
            if not board_before.is_capture(played):
                return "missed_tactic"

    # 3) Dropped material: your move left a piece capturable for free.
    after = board_before.copy(stack=False)
    after.push(chess.Move.from_uci(played_uci))
    if see.hanging_after(after):
        return "dropped_material"

    # 4) Fallback: your move worsened the position tactically.
    return "allowed_tactic"
