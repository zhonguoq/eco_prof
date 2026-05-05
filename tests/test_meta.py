def test_record_judgment_writes_to_db():
    from lab.engine.meta.judgment import record_judgment
    from lab.engine.db import get_db

    conn = get_db("meta")
    jid = record_judgment(conn, type="macro", stage="顶部",
                          confidence="medium",
                          prediction="未来 12 个月内不会衰退",
                          verification_window="12m")

    assert jid is not None
    row = conn.execute("SELECT * FROM judgments WHERE id=?", (jid,)).fetchone()
    assert row["type"] == "macro"
    assert row["stage"] == "顶部"
    assert row["confidence"] == "medium"
    assert row["status"] == "active"

def test_list_and_update_judgment():
    from lab.engine.meta.judgment import record_judgment, list_judgments, update_judgment
    from lab.engine.db import get_db

    conn = get_db("meta")
    jid = record_judgment(conn, type="macro", stage="顶部",
                          confidence="low", prediction="test",
                          verification_window="1m")

    results = list_judgments(conn, status="active")
    assert len(results) >= 1
    assert results[0]["id"] == jid

    update_judgment(conn, jid, actual_outcome="正确", status="confirmed")
    row = conn.execute("SELECT * FROM judgments WHERE id=?", (jid,)).fetchone()
    assert row["actual_outcome"] == "正确"
    assert row["status"] == "confirmed"

def test_check_disconfirmation_detects_divergence():
    from lab.engine.meta.judgment import record_judgment
    from lab.engine.meta.disconfirmation import check_disconfirmation
    from lab.engine.db import get_db

    conn = get_db("meta")
    old_signals = {"T10Y2Y": -0.15, "CPI_YOY": 3.2, "UNRATE": 4.0}
    jid = record_judgment(conn, type="macro", stage="顶部",
                          confidence="medium", prediction="将衰退",
                          verification_window="12m", signals=old_signals)

    def current_signals():
        return {"T10Y2Y": 0.35, "CPI_YOY": 1.5, "UNRATE": 5.5}

    results = check_disconfirmation(conn, current_signals)
    assert any(r["id"] == jid for r in results)
    r = next(r for r in results if r["id"] == jid)
    assert len(r["divergences"]) > 0
    assert r["summary"]
