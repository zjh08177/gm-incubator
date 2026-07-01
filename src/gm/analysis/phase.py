import chess


def game_phase(board: chess.Board, ply: int) -> str:
    pieces = chess.popcount(board.occupied)  # includes both kings
    if pieces <= 10:
        return "endgame"
    if ply <= 20:  # first 10 full moves
        return "opening"
    return "middlegame"
