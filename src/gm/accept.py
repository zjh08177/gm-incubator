import random


def _rank(vals):
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def spearman(xs, ys) -> float:
    return _pearson(_rank(xs), _rank(ys))


def correlate(conn) -> dict:
    rows = conn.execute("""
        SELECT g.accuracy_self AS acc, AVG(m.winprob_delta) AS loss
        FROM games g JOIN moves m ON m.game_uuid=g.uuid AND m.is_mine=1
        WHERE g.accuracy_self IS NOT NULL
        GROUP BY g.uuid HAVING COUNT(m.ply) > 0""").fetchall()
    acc = [r["acc"] for r in rows]
    loss = [r["loss"] for r in rows]
    n = len(acc)
    if n < 2:
        return {"n": n, "rho": 0.0, "shuffled_rho": 0.0, "pass": False}
    rho = spearman(loss, acc)
    rng = random.Random(1234)                 # deterministic negative control
    shuffled = acc[:]
    rng.shuffle(shuffled)
    srho = spearman(loss, shuffled)
    return {"n": n, "rho": round(rho, 3), "shuffled_rho": round(srho, 3),
            "pass": bool(n >= 20 and rho < -0.6 and abs(srho) < 0.3)}
