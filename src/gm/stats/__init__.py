def tc_filter(time_class, moves=False):
    """SQL fragment + args to scope a query to one `time_class` (None → all classes).

    moves=True scopes a query on the `moves` table through its parent game;
    otherwise scopes a query on the `games` table directly. The fragment always
    starts with a leading ' AND ...', so append it after an existing WHERE clause."""
    if not time_class:
        return "", []
    if moves:
        return " AND game_uuid IN (SELECT uuid FROM games WHERE time_class=?)", [time_class]
    return " AND time_class=?", [time_class]
