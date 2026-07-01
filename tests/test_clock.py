from gm.analysis import clock


def test_base_seconds_variants():
    assert clock.base_seconds("60") == 60
    assert clock.base_seconds("60+0") == 60
    assert clock.base_seconds("180+2") == 180


def test_bucket_low_and_had_time():
    assert clock.bucket(3000, "60") == "low_clock"     # 3s left on a 60s game
    assert clock.bucket(45000, "60") == "had_time"     # 45s left
    assert clock.bucket(None, "60") == "had_time"      # unknown -> assume had time
