import json
import uuid
from datetime import datetime


def record_judgment(conn, type, stage, confidence, prediction,
                    verification_window, context=None, key_question=None,
                    signals=None):
    jid = f"JUDG-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO judgments
           (id, type, timestamp, stage, signals, confidence,
            key_question, prediction, verification_window, context,
            actual_outcome, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'active')""",
        (jid, type, now, stage,
         json.dumps(signals) if signals else None,
         confidence, key_question, prediction,
         verification_window, context),
    )
    conn.commit()
    return jid


def list_judgments(conn, status=None, type=None, last_n=None):
    clauses = []
    params = []
    if status:
        clauses.append("status=?")
        params.append(status)
    if type:
        clauses.append("type=?")
        params.append(type)
    where = " AND ".join(clauses) if clauses else "1=1"
    query = f"SELECT * FROM judgments WHERE {where} ORDER BY timestamp DESC"
    if last_n:
        query += f" LIMIT {last_n}"
    return conn.execute(query, params).fetchall()


def update_judgment(conn, jid, actual_outcome=None, status=None):
    if actual_outcome:
        conn.execute("UPDATE judgments SET actual_outcome=? WHERE id=?",
                     (actual_outcome, jid))
    if status:
        conn.execute("UPDATE judgments SET status=? WHERE id=?",
                     (status, jid))
    conn.commit()
