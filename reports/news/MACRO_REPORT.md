# Macroeconomic Indicators

## Overview
This report monitors 52 core macroeconomic indicators from the Federal Reserve Economic Data (FRED) system. Indicators are ranked by **5-Year Z-Score** to highlight the most statistically significant deviations in the current macroeconomic regime.

## Indicator Alerts
- *No severe macroeconomic anomalies or extreme jumps detected.*

## 1-Year Trends
![Timeline Plot 1Yr](rendered/macro_timeline_1yr.png)

## 5-Year Trends
![Timeline Plot 5Yr](rendered/macro_timeline_5yr.png)

## Correlation Matrix
### Top Positive Correlations
- **CPI** & **REAL_GDP**: `0.97`
- **REAL_GDP** & **DISPOSABLE_INCOME**: `0.97`
- **CPI** & **DISPOSABLE_INCOME**: `0.93`
- **US10Y** & **CPI**: `0.85`
- **FEDFUNDS** & **US10Y**: `0.82`

### Top Inverse Correlations
- **ST_LOUIS_FIN_STRESS** & **DISPOSABLE_INCOME**: `-0.52`
- **WTI_CRUDE** & **DISPOSABLE_INCOME**: `-0.51`
- **FEDFUNDS** & **WTI_CRUDE**: `-0.46`
- **FEDFUNDS** & **CHICAGO_FED_ACTIVITY**: `-0.43`
- **REAL_GDP** & **ST_LOUIS_FIN_STRESS**: `-0.43`


![Correlation Matrix](rendered/macro_correlation.png)

## Indicator Dashboard
| Indicator                 |           Latest | 1M Chg   | 1Y Chg   |   5Y Z-Score | Date       |
|---------------------------|------------------|----------|----------|--------------|------------|
| FREIGHT_PPI               |    518.62        | +0.00%   | +24.88%  |         2.46 | 2026-12-01 |
| M2_MONEY                  |  23342.8         | +0.00%   | +4.42%   |         2.41 | 2026-12-01 |
| COPPER_PRICE              |  13542.8         | +0.00%   | +14.86%  |         2.24 | 2026-12-01 |
| ELECTRIC_POWER_INDEX      |    118.75        | +0.00%   | +0.19%   |         1.97 | 2026-12-01 |
| HOUSEHOLD_NET_WORTH       |      1.9587e+08  | +0.00%   | +7.46%   |         1.91 | 2026-12-01 |
| RD_INVESTMENT             |    950.52        | +0.00%   | +5.67%   |         1.78 | 2026-12-01 |
| US10Y                     |      5.28        | +0.00%   | +29.10%  |         1.7  | 2026-12-01 |
| US30Y                     |      5.63        | +0.00%   | +18.78%  |         1.68 | 2026-12-01 |
| TRUCK_PPI                 |    207.64        | +0.00%   | +14.67%  |         1.57 | 2026-12-01 |
| CPI                       |    334.13        | +0.00%   | +2.48%   |         1.57 | 2026-12-01 |
| GDP                       |  32563           | +0.00%   | +3.50%   |         1.55 | 2026-12-01 |
| KANSAS_CITY_FIN_STRESS    |     -0.95        | +0.00%   | -34.25%  |        -1.44 | 2026-12-01 |
| REAL_GDP                  |  24408           | +0.00%   | +1.17%   |         1.44 | 2026-12-01 |
| TARIFFS                   |    306.4         | +0.00%   | -16.43%  |         1.38 | 2026-12-01 |
| FOOD_CPI                  |    350.42        | +0.00%   | +1.93%   |         1.38 | 2026-12-01 |
| US_POPULATION             | 343290           | +0.02%   | +0.24%   |         1.36 | 2026-12-01 |
| AIR_PPI                   |    187.37        | +0.00%   | +5.31%   |         1.34 | 2026-12-01 |
| SUGAR_PRICE               |     14.81        | +0.00%   | -0.82%   |        -1.3  | 2026-12-01 |
| BAA_SPREAD                |      1.47        | +0.00%   | -17.42%  |        -1.29 | 2026-12-01 |
| UMICH_SENTIMENT           |     51.7         | +0.00%   | -2.27%   |        -1.26 | 2026-12-01 |
| DISPOSABLE_INCOME         |  18410.5         | +0.00%   | +1.11%   |         1.23 | 2026-12-01 |
| WTI_CRUDE                 |     96.16        | +0.00%   | +61.69%  |         1.22 | 2026-12-01 |
| HOUSING_STARTS            |   1275           | +0.00%   | -7.47%   |        -1.11 | 2026-12-01 |
| WAREHOUSE_PPI             |    168.97        | +0.00%   | +2.48%   |         1.09 | 2026-12-01 |
| USD_JPY                   |    157.81        | +0.00%   | +1.63%   |         1.05 | 2026-12-01 |
| FED_ASSETS                |      6.74303e+06 | +0.00%   | +2.91%   |        -1    | 2026-12-01 |
| SAVINGS_RATE              |      4.1         | +0.00%   | -18.00%  |        -1    | 2026-12-01 |
| USD_CNY                   |      6.7         | +0.00%   | -5.20%   |        -0.98 | 2026-12-01 |
| ST_LOUIS_FIN_STRESS       |     -0.81        | +0.00%   | -112.03% |        -0.97 | 2026-12-01 |
| US02Y                     |      4.83        | +0.00%   | +36.44%  |         0.96 | 2026-12-01 |
| M2_VELOCITY               |      1.42        | +0.00%   | +0.50%   |         0.9  | 2026-12-01 |
| TECH_PULSE                |     96.05        | +0.00%   | +6.80%   |         0.83 | 2026-12-01 |
| CHINA_IMPORTS             |  27070.7         | +0.00%   | +28.26%  |        -0.81 | 2026-12-01 |
| UNRATE                    |      4.2         | +0.00%   | -4.55%   |         0.77 | 2026-12-01 |
| US_BIRTH_RATE             |     10.6         | +0.00%   | +0.00%   |        -0.72 | 2026-12-01 |
| LIFE_EXPECTANCY           |     78.89        | +0.00%   | +0.00%   |         0.71 | 2026-12-01 |
| RECESSION_PROB            |      0.62        | +0.00%   | +106.67% |         0.59 | 2026-12-01 |
| CREDIT_CARD_DELINQUENCY   |      2.62        | +0.00%   | -0.38%   |         0.51 | 2026-12-01 |
| USD_EUR                   |      1.13        | +0.00%   | -3.13%   |         0.5  | 2026-12-01 |
| NAT_GAS_PRICE             |      2.96        | +0.00%   | -33.13%  |        -0.47 | 2026-12-01 |
| CORN_PRICE                |    213.19        | +0.00%   | +3.84%   |        -0.46 | 2026-12-01 |
| US_POLICY_UNCERTAINTY     |    277.43        | +0.00%   | +7.58%   |         0.41 | 2026-12-01 |
| MFG_CONST                 | 170701           | +0.00%   | -6.10%   |        -0.37 | 2026-12-01 |
| GLOBAL_POLICY_UNCERTAINTY |    241.69        | +0.00%   | -27.29%  |        -0.36 | 2026-12-01 |
| CORP_SPREAD               |      0.85        | +0.00%   | +3.66%   |        -0.3  | 2026-12-01 |
| WHEAT_PRICE               |    228.74        | +0.00%   | +38.11%  |        -0.25 | 2026-12-01 |
| CHICAGO_FED_ACTIVITY      |     -0.04        | +0.00%   | +33.33%  |         0.13 | 2026-12-01 |
| USD_INDEX                 |    121.38        | +0.00%   | +0.33%   |         0.12 | 2026-12-01 |
| EUROPE_POLICY_UNCERTAINTY |    358.52        | +0.00%   | +1.48%   |        -0.08 | 2026-12-01 |
| FEDFUNDS                  |      3.75        | +0.00%   | +0.81%   |        -0.02 | 2026-12-01 |
| HY_SPREAD                 |      3.1         | +0.00%   | +5.44%   |        -0.01 | 2026-12-01 |
| AAA_SPREAD                |      1           | +0.00%   | -14.53%  |         0    | 2026-12-01 |
