def cagr(values):
    if not values or len(values) < 2:
        return None
    n = len(values)
    first, last = values[0], values[-1]
    if first <= 0 or last <= 0:
        return None
    return round((last / first) ** (1.0 / (n - 1)) - 1, 6)


def linear_trend(values):
    if not values or len(values) < 2:
        return None
    n = len(values)
    xs = list(range(n))
    sum_x = sum(xs)
    sum_y = sum(values)
    sum_xy = sum(x * v for x, v in zip(xs, values))
    sum_xx = sum(x * x for x in xs)
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return None
    slope = (n * sum_xy - sum_x * sum_y) / denom
    mean_y = sum_y / n
    if mean_y == 0:
        return None
    return round(slope / mean_y, 6)
