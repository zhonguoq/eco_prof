from fredapi import Fred

FRED_SERIES = [
    "T10Y2Y", "DGS2", "DGS10",
    "CPIAUCSL",
    "UNRATE",
    "UMCSENT",
    "GDPC1", "FEDFUNDS",
    "TCMDO", "GFDEGDQ188S", "DTWEXBGS",
]


def fetch_one(series_id, conn, api_key, fred=None):
    fred = fred or Fred(api_key=api_key)
    data = fred.get_series(series_id)
    rows = 0
    for date, value in data.items():
        date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
        conn.execute(
            "INSERT OR REPLACE INTO series (series_id, date, value) VALUES (?, ?, ?)",
            (series_id, date_str, float(value)),
        )
        rows += 1
    conn.commit()
    return rows


def get_latest_date(conn, series_id):
    row = conn.execute(
        "SELECT MAX(date) AS d FROM series WHERE series_id=?", (series_id,)
    ).fetchone()
    return row["d"] if row and row["d"] else None


def fetch_all(conn, api_key, fred=None):
    fred = fred or Fred(api_key=api_key)
    result = {}
    for series_id in FRED_SERIES:
        result[series_id] = fetch_one(series_id, conn, api_key, fred=fred)
    return result
