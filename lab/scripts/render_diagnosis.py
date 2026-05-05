#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lab.chart_lib.macro_charts import yield_curve_chart, signal_dashboard, debt_gdp_chart
from lab.chart_lib.composite import compose


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else "diagnosis_report.html"

    charts = [
        yield_curve_chart(title="收益率曲线"),
        signal_dashboard(title="信号面板"),
        debt_gdp_chart(title="债务/GDP"),
    ]
    path = compose("宏观诊断报告", charts, filename=output)
    print(f"报告已生成: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
