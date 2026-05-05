import pandas as pd


def fetch_stock_data(code, conn, market="A", mock=None):
    if mock is not None:
        data = mock
    elif market == "A":
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code.replace(".SH", "").replace(".SZ", ""),
                                adjust="qfq")
        data = df.set_index("日期")
    else:
        import yfinance as yf
        ticker = yf.Ticker(code)
        data = ticker.history(period="max")

    rows = 0
    for date_idx, row in data.iterrows():
        date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, "strftime") else str(date_idx)
        conn.execute(
            """INSERT OR REPLACE INTO stock_prices
               (code, date, open, close, high, low, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (code, date_str,
             float(row.get("open", row.get("Open", 0))),
             float(row.get("close", row.get("Close", 0))),
             float(row.get("high", row.get("High", 0))),
             float(row.get("low", row.get("Low", 0))),
             float(row.get("volume", row.get("Volume", 0)))),
        )
        rows += 1
    conn.commit()
    return rows
