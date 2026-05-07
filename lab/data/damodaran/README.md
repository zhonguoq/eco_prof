# Damodaran 数据手动下载指南

每年 1 月更新一次。所有文件保存至本目录。

## 所需文件

| 文件名 | 内容 | 来源 URL |
|--------|------|----------|
| `ctryprem.csv` | ERP by country | https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.csv |
| `betas_us.csv` | US sector betas | https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls → 转 CSV |
| `betas_em.csv` | Emerging Markets betas | https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaemerg.xls → 转 CSV |
| `betas_china.csv` | China sector betas | https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaChina.xls → 转 CSV |
| `betas_japan.csv` | Japan sector betas | https://pages.stern.nyu.edu/~adamodar/pc/datasets/betaJapan.xls → 转 CSV |
| `taxrate.csv` | Tax rates by country | https://pages.stern.nyu.edu/~adamodar/pc/datasets/taxrate.csv |

## CSV 列格式

### ctryprem.csv
```
Country,Adj Default Spread,Equity Risk Premium,Country Risk Premium,Corporate Tax Rate,Moody's Rating,PRS Overall Risk Score
China,0.0046,0.0637,0.0187,0.25,...
```

### betas_*.csv
```
Industry Name,Number of Firms,Beta,D/E Ratio,Tax Rate,Unlevered Beta,Cash/Firm Value,Unlevered Beta corrected for cash,HiLo Risk,Standard deviation of equity,Standard deviation in operating income (last 10 years)
Beverage (Alcoholic),25,0.85,0.25,0.25,0.72,...
```

### taxrate.csv
```
Country,Tax Rate
China,0.25
United States,0.21
Hong Kong,0.165
```

## 更新步骤

1. 访问 https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/
2. 下载对应 XLS/CSV 文件
3. 若为 XLS，用 Excel/LibreOffice 另存为 CSV
4. 覆盖本目录同名文件
5. 提交 git commit（加 `[data] update damodaran YYYY`）
