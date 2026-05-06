import pandas as pd


def calc_beta(conn, code, benchmark="000300.SH", periods=252):
    stock = pd.read_sql_query(
        "SELECT date, close FROM stock_prices WHERE code=? ORDER BY date",
        conn, params=(code,)
    )
    bench = pd.read_sql_query(
        "SELECT date, close FROM stock_prices WHERE code=? ORDER BY date",
        conn, params=(benchmark,)
    )
    if len(stock) < 2 or len(bench) < 2:
        return None

    merged = stock.merge(bench, on="date", suffixes=("_stock", "_bench"))
    if len(merged) < 2:
        return None

    returns = merged["close_stock"].pct_change().dropna()
    bench_returns = merged["close_bench"].pct_change().dropna()

    if len(returns) < 2 or len(bench_returns) < 2:
        return None

    cov = returns.cov(bench_returns)
    var = bench_returns.var()
    if var == 0:
        return None

    return round(cov / var, 4)
