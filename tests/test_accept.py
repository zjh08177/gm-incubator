from gm import accept


def test_spearman_perfect_negative():
    xs = [1, 2, 3, 4, 5]
    ys = [5, 4, 3, 2, 1]
    assert abs(accept.spearman(xs, ys) + 1.0) < 1e-9


def test_correlate_passes_when_loss_tracks_accuracy(conn):
    # accuracy high -> our avg loss low, and vice-versa, for 25 games
    for i in range(25):
        acc = 50 + i * 2                     # 50..98
        conn.execute("INSERT INTO games(uuid,color,accuracy_self,result,time_class) "
                     "VALUES(?,?,?,?,?)", (f"g{i}", "white", float(acc), "loss", "bullet"))
        loss = (100 - acc) / 100.0           # inverse of accuracy
        conn.execute("""INSERT INTO moves(game_uuid,ply,san,fen_before,eval_best_cp,
            best_move,eval_played_cp,winprob_delta,clock_ms,phase,clock_bucket,
            error_type,severity,is_mine) VALUES(?,?, 'x','f',0,'a1a1',0,?,1000,
            'middlegame','had_time',NULL,NULL,1)""", (f"g{i}", 1, loss))
    conn.commit()
    res = accept.correlate(conn)
    assert res["n"] == 25
    assert res["rho"] < -0.6
    assert abs(res["shuffled_rho"]) < 0.3    # negative control
    assert res["pass"] is True
