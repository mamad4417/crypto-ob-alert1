def detect_new_order_blocks(rows, sensitivity=28, ob_gap_bars=5):
    threshold = sensitivity / 100.0
    n = len(rows)
    if n < 17:
        return []

    pc = [None] * n
    for i in range(4, n):
        pc[i] = (rows[i]["open"] - rows[i-4]["open"]) / rows[i-4]["open"] * 100.0

    last_cross = None
    for i in range(5, n-1):
        bearish = pc[i-1] >= -threshold and pc[i] < -threshold
        bullish = pc[i-1] <= threshold and pc[i] > threshold
        if bearish or bullish:
            last_cross = i

    i = n - 1
    bearish = pc[i-1] >= -threshold and pc[i] < -threshold
    bullish = pc[i-1] <= threshold and pc[i] > threshold
    if not (bearish or bullish):
        return []

    if last_cross is not None and i - last_cross <= ob_gap_bars:
        return []

    result = []
    if bearish:
        for off in range(4, 16):
            x = rows[i-off]
            if x["close"] > x["open"]:
                result.append({"side":"BEARISH","high":x["high"],"low":x["low"],
                               "created_open_time":rows[i]["open_time"]})
                break
    if bullish:
        for off in range(4, 16):
            x = rows[i-off]
            if x["close"] < x["open"]:
                result.append({"side":"BULLISH","high":x["high"],"low":x["low"],
                               "created_open_time":rows[i]["open_time"]})
                break
    return result
