def dcf_value(fcf_list, growth_rate=0.10, growth_years=5,
              terminal_growth=0.03, discount_rate=0.08):
    last = fcf_list[-1] if fcf_list else 0
    pv_total = 0.0

    for y in range(1, growth_years + 1):
        fcf = last * (1 + growth_rate) ** y
        pv_total += fcf / (1 + discount_rate) ** y

    terminal = last * (1 + growth_rate) ** growth_years
    terminal *= (1 + terminal_growth) / (discount_rate - terminal_growth)
    pv_total += terminal / (1 + discount_rate) ** growth_years

    return round(pv_total, 2)


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
