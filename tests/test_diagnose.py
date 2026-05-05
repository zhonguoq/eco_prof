def test_read_signals_returns_latest_values():
    from lab.engine.macro.diagnose import read_signals
    from lab.engine.db import get_db

    conn = get_db("macro")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('FEDFUNDS', '2026-01-01', 4.5)")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('FEDFUNDS', '2026-06-01', 4.25)")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('T10Y2Y', '2026-06-01', -0.15)")
    conn.commit()

    signals = read_signals(conn)
    assert signals["FEDFUNDS"] == 4.25
    assert signals["T10Y2Y"] == -0.15

def test_classify_stage_yield_curve_inverted():
    from lab.engine.macro.diagnose import classify_stage

    signals = {"T10Y2Y": -0.15, "FEDFUNDS": 5.0, "CPI_YOY": 3.5, "UNRATE": 4.0}
    stage = classify_stage(signals)
    assert stage["id"] == 3
    assert stage["name"] == "顶部"

def test_classify_stage_bubble():
    from lab.engine.macro.diagnose import classify_stage
    signals = {"T10Y2Y": 0.15, "FEDFUNDS": 5.5, "CPI_YOY": 4.2, "UMCSENT": 90.0, "UNRATE": 3.5}
    stage = classify_stage(signals)
    assert stage["id"] == 2

def test_classify_stage_early():
    from lab.engine.macro.diagnose import classify_stage
    signals = {"T10Y2Y": 2.5, "FEDFUNDS": 2.0, "CPI_YOY": 2.5, "UNRATE": 5.0}
    stage = classify_stage(signals)
    assert stage["id"] == 1

def test_classify_stage_unclear_no_data():
    from lab.engine.macro.diagnose import classify_stage
    stage = classify_stage({})
    assert stage["id"] == 0

def test_diagnose_returns_full_output():
    from lab.engine.macro.diagnose import diagnose
    from lab.engine.db import get_db

    conn = get_db("macro")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('T10Y2Y', '2026-06-01', -0.15)")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('FEDFUNDS', '2026-06-01', 4.5)")
    conn.execute("INSERT OR REPLACE INTO series VALUES ('UNRATE', '2026-06-01', 4.5)")
    conn.commit()

    result = diagnose(conn)
    assert "date" in result
    assert "stage" in result
    assert "signals" in result
    assert "confidence" in result
    assert result["stage"]["id"] == 3

def test_load_rules_returns_config():
    from lab.engine.macro.diagnose import load_rules

    rules = load_rules()
    assert "stages" in rules
    assert "signals" in rules
    assert len(rules["stages"]) == 7
