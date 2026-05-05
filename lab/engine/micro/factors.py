import statistics


def _zscore(values):
    mu = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 1
    return [(v - mu) / sd for v in values]


def compute_scores(stocks, factors, weights=None):
    if not stocks:
        return []

    if weights is None:
        weights = {f: 1.0 / len(factors) for f in factors}

    scored = {s["code"]: 0.0 for s in stocks}

    for factor in factors:
        vals = [s.get(factor, 0) or 0 for s in stocks]
        zs = _zscore(vals)
        for i, s in enumerate(stocks):
            scored[s["code"]] += zs[i] * weights.get(factor, 0)

    result = sorted(
        [{"code": s["code"], "score": round(scored[s["code"]], 3)} for s in stocks],
        key=lambda x: x["score"],
        reverse=True,
    )
    for i, r in enumerate(result):
        r["rank"] = i + 1

    return result
