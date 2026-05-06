def dcf_value(fcf_list, growth_rate=0.10, growth_years=5,
              terminal_growth=0.03, discount_rate=0.08):
    if discount_rate <= terminal_growth:
        raise ValueError(
            f"discount_rate ({discount_rate}) must be > terminal_growth ({terminal_growth})"
        )
    last = fcf_list[-1] if fcf_list else 0
    pv_total = 0.0

    for y in range(1, growth_years + 1):
        fcf = last * (1 + growth_rate) ** y
        pv_total += fcf / (1 + discount_rate) ** y

    terminal = last * (1 + growth_rate) ** growth_years
    terminal *= (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_total += terminal / (1 + discount_rate) ** growth_years

    return round(pv_total, 2)


def batch_dcf(conn, code, growth_rate=0.10, growth_years=5,
              terminal_growth=0.03, discount_rate=0.08, years_back=5):
    rows = conn.execute(
        """SELECT fcf FROM financial_statements
           WHERE code = ? AND fcf IS NOT NULL
           AND report_date LIKE '%-12-31'
           ORDER BY report_date DESC
           LIMIT ?""",
        (code, years_back)
    ).fetchall()

    if not rows:
        return None

    fcf_list = [r["fcf"] for r in rows]
    fcf_list.reverse()
    return dcf_value(fcf_list, growth_rate, growth_years,
                     terminal_growth, discount_rate)


def equity_value(conn, code, ev):
    row = conn.execute(
        """SELECT cash, total_liabilities FROM financial_statements
           WHERE code = ? AND cash IS NOT NULL AND total_liabilities IS NOT NULL
           ORDER BY report_date DESC LIMIT 1""",
        (code,)
    ).fetchone()
    if not row:
        return ev
    net_debt = row["total_liabilities"] - row["cash"]
    return round(ev - net_debt, 2)


def sensitivity_matrix(fcf_list, growth_range=(0.05, 0.15, 3),
                       discount_range=(0.06, 0.10, 3),
                       growth_years=5, terminal_growth=0.03):
    matrix = {}
    g_lo, g_hi, g_steps = growth_range
    d_lo, d_hi, d_steps = discount_range
    for g in [g_lo + i * (g_hi - g_lo) / (g_steps - 1) for i in range(g_steps)]:
        row_key = f"g={g:.0%}"
        matrix[row_key] = {}
        for d in [d_lo + i * (d_hi - d_lo) / (d_steps - 1) for i in range(d_steps)]:
            matrix[row_key][f"r={d:.0%}"] = dcf_value(
                fcf_list, growth_rate=g, growth_years=growth_years,
                terminal_growth=terminal_growth, discount_rate=d,
            )
    return matrix
