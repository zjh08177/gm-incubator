import chess

from gm.analysis import see

_MATE_GUARD = 50000  # eval_played below this = a forced mate against the mover


def classify(board_before: chess.Board, played_uci: str, best_uci: str,
             eval_best_cp: int, eval_played_cp: int,
             severity: str | None, phase: str) -> str | None:
    if severity is None:
        return None

    played = chess.Move.from_uci(played_uci)
    after = board_before.copy(stack=False)
    after.push(played)
    hangs = see.hanging_after(after)
    mated = eval_played_cp <= -_MATE_GUARD

    # 1) Winning endgame that slipped — but NOT via a hang or a walk-into-mate
    #    (those are more specific and handled below).
    if (phase == "endgame" and eval_best_cp >= 200
            and (eval_best_cp - eval_played_cp) >= 150
            and not hangs and not mated):
        return "endgame_conversion"

    # 2) Missed your own tactic: best move was a winning capture/mate you skipped.
    if best_uci:
        best = chess.Move.from_uci(best_uci)
        if (eval_best_cp >= 300 and eval_best_cp - eval_played_cp >= 150
                and (board_before.is_capture(best) or eval_best_cp >= 900)
                and not board_before.is_capture(played)):
            return "missed_tactic"

    # 3) Dropped material: your move left a piece capturable for free.
    if hangs:
        return "dropped_material"

    # 4) Fallback: your move worsened the position tactically (incl. allowing mate).
    return "allowed_tactic"
