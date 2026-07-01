import chess
import chess.engine

from gm import config
from gm.analysis.winprob import MATE_CP


class Analyzer:
    def __init__(self, depth: int = 12, path: str | None = None):
        self.depth = depth
        self.path = path or config.stockfish_path()
        if not self.path:
            raise RuntimeError("Stockfish not found; set STOCKFISH_PATH")
        self._engine = None

    def __enter__(self):
        self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self

    def __exit__(self, *exc):
        if self._engine:
            self._engine.quit()

    def analyse(self, board: chess.Board) -> tuple[int, str]:
        info = self._engine.analyse(board, chess.engine.Limit(depth=self.depth))
        score = info["score"].pov(board.turn)
        cp = score.score(mate_score=MATE_CP)
        best = info["pv"][0].uci() if info.get("pv") else ""
        return cp, best
