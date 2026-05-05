import json


def check_disconfirmation(conn, current_signals_fn):
    results = []
    rows = conn.execute(
        "SELECT * FROM judgments WHERE status='active' AND signals IS NOT NULL"
    ).fetchall()

    current = current_signals_fn()

    for row in rows:
        try:
            orig = json.loads(row["signals"])
        except (json.JSONDecodeError, TypeError):
            continue

        divergences = []
        for key, old_val in orig.items():
            new_val = current.get(key)
            if new_val is None:
                continue
            diff = abs(new_val - old_val)
            if diff > 1.0:
                divergences.append({
                    "signal": key,
                    "old": old_val,
                    "current": new_val,
                    "change": round(new_val - old_val, 2),
                })

        if divergences:
            summary = f"信号变化: {', '.join(d['signal'] for d in divergences)}"
            results.append({
                "id": row["id"],
                "stage": row["stage"],
                "timestamp": row["timestamp"],
                "divergences": divergences,
                "summary": summary,
            })

    return results
