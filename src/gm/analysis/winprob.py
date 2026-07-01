import math

MATE_CP = 100000
_K = 0.00368208  # lichess-derived logistic constant


def cp_to_winprob(cp: int) -> float:
    cp = max(-MATE_CP, min(MATE_CP, cp))
    return 1.0 / (1.0 + math.exp(-_K * cp))


def loss(best_cp: int, played_cp: int) -> float:
    return max(0.0, cp_to_winprob(best_cp) - cp_to_winprob(played_cp))


def severity(loss_val: float) -> str | None:
    if loss_val > 0.20:
        return "blunder"
    if loss_val > 0.10:
        return "mistake"
    if loss_val > 0.05:
        return "inaccuracy"
    return None
