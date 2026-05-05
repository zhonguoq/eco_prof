def test_compute_factor_scores():
    from lab.engine.micro.factors import compute_scores

    stocks = [
        {"code": "A", "pe": 10, "roe": 0.20, "pb": 2.0},
        {"code": "B", "pe": 20, "roe": 0.10, "pb": 1.5},
        {"code": "C", "pe": 30, "roe": 0.05, "pb": 1.0},
    ]
    result = compute_scores(stocks, factors=["pe", "roe"])
    assert len(result) == 3
    assert result[0]["code"] in ("A", "B", "C")
    assert "score" in result[0]
    assert result[0]["score"] > result[2]["score"]

def test_compute_scores_with_weights():
    from lab.engine.micro.factors import compute_scores

    stocks = [
        {"code": "X", "pe": 15, "roe": 0.15},
        {"code": "Y", "pe": 25, "roe": 0.25},
    ]
    result = compute_scores(stocks, factors=["pe", "roe"], weights={"pe": 0.3, "roe": 0.7})
    assert len(result) == 2
