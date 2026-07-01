import io

import chess
import chess.pgn

from gm.analysis import classify, clock as clock_mod, phase as phase_mod, winprob


def analyze_game(pgn: str, color: str, analyzer, depth: int) -> list[dict]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return []
    tc = game.headers.get("TimeControl", "")
    my_turn = chess.WHITE if color == "white" else chess.BLACK

    # Pass 1: walk positions, collect per-move facts.
    steps = []
    board = game.board()
    node = game
    ply = 0
    while node.variations:
        nxt = node.variations[0]
        played = nxt.move
        ply += 1
        eval_best, best_uci = analyzer.analyse(board)
        clk = nxt.clock()
        steps.append({
            "ply": ply, "san": board.san(played), "fen_before": board.fen(),
            "played_uci": played.uci(), "eval_best_cp": eval_best, "best_uci": best_uci,
            "clock_ms": int(clk * 1000) if clk is not None else None,
            "is_mine": 1 if board.turn == my_turn else 0,
            "phase": phase_mod.game_phase(board, ply),
        })
        board.push(played)
        node = nxt

    # eval_played for ply i = -eval_best of the next position (mover flips).
    rows = []
    for i, s in enumerate(steps):
        nxt_best = steps[i + 1]["eval_best_cp"] if i + 1 < len(steps) else -s["eval_best_cp"]
        eval_played = -nxt_best
        delta = winprob.loss(s["eval_best_cp"], eval_played)
        sev = winprob.severity(delta) if s["is_mine"] else None
        cat = None
        if s["is_mine"] and sev:
            b = chess.Board(s["fen_before"])
            cat = classify.classify(b, s["played_uci"], s["best_uci"],
                                    s["eval_best_cp"], eval_played, sev, s["phase"])
        rows.append({
            "ply": s["ply"], "san": s["san"], "fen_before": s["fen_before"],
            "eval_best_cp": s["eval_best_cp"], "best_move": s["best_uci"],
            "eval_played_cp": eval_played, "winprob_delta": delta,
            "clock_ms": s["clock_ms"], "phase": s["phase"],
            "clock_bucket": clock_mod.bucket(s["clock_ms"], tc),
            "error_type": cat, "severity": sev, "is_mine": s["is_mine"],
        })
    return rows
