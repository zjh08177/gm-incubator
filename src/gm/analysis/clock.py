def base_seconds(tc: str) -> int:
    if not tc:
        return 0
    return int(str(tc).split("+")[0])


def bucket(clock_ms: int | None, tc: str) -> str:
    if clock_ms is None:
        return "had_time"
    thresh = max(5.0, 0.10 * base_seconds(tc))
    return "low_clock" if clock_ms / 1000.0 < thresh else "had_time"
