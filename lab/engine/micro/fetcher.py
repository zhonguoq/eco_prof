import pandas as pd


import json


def _aksymbol(code):
    """Convert '000725.SZ' → 'SZ000725' for akshare API."""
    parts = code.split(".")
    return parts[1] + parts[0] if len(parts) == 2 else code


def fetch_financial_statements(code, conn, market="A",
                                mock_cash_flow=None, mock_balance=None):
    symbol = _aksymbol(code)
    cf_df = mock_cash_flow
    bs_df = mock_balance
    if mock_cash_flow is None and mock_balance is None:
        import akshare as ak
        cf_df = ak.stock_cash_flow_sheet_by_report_em(symbol=symbol)
        bs_df = ak.stock_balance_sheet_by_report_em(symbol=symbol)

    rows = 0
    dates = cf_df["REPORT_DATE"] if cf_df is not None else []
    for date_val in dates:
        date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)[:10]

        cf_row = cf_df[cf_df["REPORT_DATE"] == date_val]
        operating_cf = float(cf_row["NETCASH_OPERATE"].iloc[0])
        capex = float(cf_row["CONSTRUCT_LONG_ASSET"].iloc[0])
        # Some stocks report capex as negative; take absolute
        fcf = round(operating_cf - abs(capex), 2)

        cash = None
        total_liabilities = None
        raw_data = json.dumps({"operating_cf": operating_cf, "capex": capex}, ensure_ascii=False)
        if bs_df is not None:
            bs_row = bs_df[bs_df["REPORT_DATE"] == date_val]
            if not bs_row.empty:
                cash = float(bs_row["MONETARYFUNDS"].iloc[0])
                total_liabilities = float(bs_row["TOTAL_LIABILITIES"].iloc[0])
                raw_data = json.dumps({
                    "operating_cf": operating_cf, "capex": capex,
                    "cash": cash, "total_liabilities": total_liabilities,
                }, ensure_ascii=False)

        conn.execute(
            """INSERT OR REPLACE INTO financial_statements
               (code, report_date, fcf, operating_cf, capex, cash, total_liabilities, data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, date_str, fcf, operating_cf, abs(capex), cash, total_liabilities, raw_data),
        )
        rows += 1
    conn.commit()
    return rows


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
