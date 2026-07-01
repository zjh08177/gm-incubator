import chess

VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
       chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}


def _least_attacker(board, sq, color):
    attackers = board.attackers(color, sq)
    if not attackers:
        return None
    return min(attackers, key=lambda s: VAL[board.piece_type_at(s)])


def see_capture(board: chess.Board, move: chess.Move) -> int:
    """Static exchange evaluation of a capture, in pawns, from mover POV."""
    target = board.piece_type_at(move.to_square)
    if target is None:
        return 0
    gain = [VAL[target]]
    b = board.copy(stack=False)
    b.push(move)
    sq = move.to_square
    occupied_val = VAL[board.piece_type_at(move.from_square)]
    color = not board.turn  # side to recapture
    while True:
        frm = _least_attacker(b, sq, color)
        if frm is None:
            break
        gain.append(occupied_val - gain[-1])
        occupied_val = VAL[b.piece_type_at(frm)]
        b.remove_piece_at(sq)
        b.set_piece_at(sq, b.piece_at(frm))
        b.remove_piece_at(frm)
        color = not color
    for i in range(len(gain) - 2, -1, -1):
        gain[i] = -max(-gain[i], gain[i + 1])
    return gain[0]


def hanging_after(board_after: chess.Board) -> bool:
    """True if the side to move on board_after has a strictly winning capture."""
    for mv in board_after.legal_moves:
        if board_after.is_capture(mv) and see_capture(board_after, mv) > 0:
            return True
    return False
