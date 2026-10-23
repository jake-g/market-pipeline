# Macroeconomic Regime Report

*Generated 2026-10-22. All statistics are computed on
native FRED observations (not the forward-filled daily grid); Δ columns are
percentage changes for levels and percentage-point (pp) changes for rates,
spreads and ratios.*

## Regime Read
**Late-cycle (hot rates).** Growth expansion (CFNAI -0.04), inflation re-accelerating (CPI 3.7% YoY, +0.3pp in 3M); 10Y 5.13% (+0.50pp 3M), curve 10s2s +0.32, real fed funds +0.03%; HY spread 3.27% (+58bp 3M), WTI $108 (+28% 3M); unemployment 4.2%, UMich sentiment 52.

## Alerts
- ⚠️ **FREIGHT_PPI** at 534.80 is +2.8σ from its 5-year mean (98th percentile).
- ⚠️ **TRUCK_PPI** at 219.38 is +2.4σ from its 5-year mean (98th percentile).
- ⚠️ **WTI_CRUDE** at 107.89 is +2.1σ from its 5-year mean (95th percentile).
- ⚠️ **ELECTRIC_POWER_INDEX** at 123.52 is +3.0σ from its 5-year mean (98th percentile).
- 🚨 **RD_INVESTMENT**: latest move +23.42 is 2.8σ of its 5Y move distribution (now 950.52, 2026-04-01).
- 🚨 **HOUSEHOLD_NET_WORTH**: latest move +12803400.00 is 3.0σ of its 5Y move distribution (now 195,870,496.00, 2026-04-01).
- ⚠️ **HOUSEHOLD_NET_WORTH** at 195,870,496.00 is +2.1σ from its 5-year mean (94th percentile).
- 🚨 **GDP**: latest move +656.76 is 5.7σ of its 5Y move distribution (now 32,563.03, 2026-04-01).

## Most Extreme vs 5-Year History
| Indicator              |         Latest |   5Y Z |   pct | Δ3M     | 3M   |
|------------------------|----------------|--------|-------|---------|------|
| ELECTRIC_POWER_INDEX   |   123.52       |    3   |    98 | +7.0%   | ↑    |
| FREIGHT_PPI            |   534.8        |    2.8 |    98 | +6.0%   | ↑    |
| TRUCK_PPI              |   219.38       |    2.4 |    98 | +10.8%  | ↑    |
| HOUSEHOLD_NET_WORTH    |     1.9587e+08 |    2.1 |    94 | +7.0%   | ↑    |
| WTI_CRUDE              |   107.89       |    2.1 |    95 | +27.9%  | ↑    |
| RD_INVESTMENT          |   950.52       |    2   |    94 | +2.5%   | ↑    |
| GDP                    | 32563          |    1.7 |    94 | +2.1%   | ↑    |
| KANSAS_CITY_FIN_STRESS |    -0.99       |   -1.5 |     0 | -0.22pp | ↓    |

## Regime Dashboard (5-Year)
![Regime 5Y](rendered/macro_regime_5yr.png)

## Regime Dashboard (1-Year)
![Regime 1Y](rendered/macro_regime_1yr.png)

*How to read*: top-left shows the policy rate against the curve with 10s2s
inversions shaded; top-right compares headline/food inflation with the real
policy rate (positive = restrictive); bottom-left is credit stress; bottom
right rebases commodities and the dollar to 100 at the window start.

## Correlation of Monthly Changes (5-Year)
### Move together (top +)
- **US10Y** & **USD_INDEX**: `+0.61`
- **CPI_YOY** & **WTI_CRUDE**: `+0.43`
- **CHICAGO_FED_ACTIVITY** & **TECH_PULSE**: `+0.42`
- **HY_SPREAD** & **ST_LOUIS_FIN_STRESS**: `+0.36`
- **UNRATE** & **USD_INDEX**: `+0.30`

### Move opposite (top −)
- **HY_SPREAD** & **US_POLICY_UNCERTAINTY**: `-0.34`
- **HY_SPREAD** & **TECH_PULSE**: `-0.33`
- **YC_10Y_2Y** & **FEDFUNDS**: `-0.33`
- **YC_10Y_2Y** & **TECH_PULSE**: `-0.30`
- **COPPER_PRICE** & **USD_INDEX**: `-0.28`

![Correlation Matrix](rendered/macro_correlation.png)

## Indicator Dashboard

### Rates & Curve
| Indicator     |   Latest | Δ1M     | Δ3M     | Δ1Y     |   5Y Z |   5Y pct | 3M   | As of      |
|---------------|----------|---------|---------|---------|--------|----------|------|------------|
| FEDFUNDS      |     3.75 | +0.12pp | +0.12pp | -0.47pp |    0.1 |       37 | ↑    | 2026-09-01 |
| US02Y         |     4.81 | +0.05pp | +0.55pp | +1.36pp |    0.9 |       88 | ↑    | 2026-10-21 |
| US10Y         |     5.13 | +0.17pp | +0.50pp | +1.15pp |    1.5 |       99 | ↑    | 2026-10-21 |
| US30Y         |     5.42 | +0.08pp | +0.31pp | +0.84pp |    1.4 |       99 | →    | 2026-10-20 |
| YC_10Y_2Y     |     0.32 | +0.12pp | -0.05pp | -0.21pp |    0.6 |       61 | ↓    | 2026-10-21 |
| YC_30Y_10Y    |     0.29 | -0.04pp | -0.21pp | -0.28pp |   -0   |       55 | ↓    | 2026-10-21 |
| REAL_FEDFUNDS |     0.03 | -0.24pp | -0.13pp | -1.16pp |    0.2 |       34 | ↓    | 2026-09-01 |

### Inflation & Growth
| Indicator            |   Latest | Δ1M     | Δ3M     | Δ1Y     |   5Y Z |   5Y pct | 3M   | As of      |
|----------------------|----------|---------|---------|---------|--------|----------|------|------------|
| CPI_YOY              |     3.72 | +0.36pp | +0.25pp | +0.69pp |   -0.3 |       60 | ↑    | 2026-09-01 |
| FOOD_CPI_YOY         |     2.48 | -0.19pp | -0.53pp | -0.63pp |   -0.8 |       17 | ↓    | 2026-09-01 |
| GDP                  | 32563    | +2.1%   | +2.1%   | +6.3%   |    1.7 |       94 | ↑    | 2026-04-01 |
| REAL_GDP             | 24408    | +0.6%   | +0.6%   | +2.2%   |    1.5 |       94 | ↑    | 2026-04-01 |
| CHICAGO_FED_ACTIVITY |    -0.04 | -0.12pp | +0.06pp | +0.32pp |    0.2 |       55 | ↑    | 2026-08-01 |
| RECESSION_PROB       |     0.62 | +0.38pp | +0.50pp | -0.24pp |    0.6 |       81 | ↑    | 2026-08-01 |
| M2_YOY               |     5.66 | +0.25pp | +0.27pp | +1.41pp |    0.7 |       84 | ↑    | 2026-08-01 |
| M2_VELOCITY          |     1.42 | +0.2%   | +0.2%   | +1.1%   |    0.9 |       94 | ↑    | 2026-04-01 |

### Labor & Consumer
| Indicator               |         Latest | Δ1M     | Δ3M     | Δ1Y     |   5Y Z |   5Y pct | 3M   | As of      |
|-------------------------|----------------|---------|---------|---------|--------|----------|------|------------|
| UNRATE                  |     4.2        | +0.10pp | +0.00pp | -0.20pp |    0.8 |       68 | →    | 2026-09-01 |
| UMICH_SENTIMENT         |    51.7        | -6.3%   | +15.4%  | -11.2%  |   -1.3 |       11 | ↑    | 2026-08-01 |
| SAVINGS_RATE            |     4.1        | -0.50pp | -0.30pp | -1.10pp |   -1   |       15 | ↓    | 2026-08-01 |
| DISPOSABLE_INCOME       | 18410.5        | -0.0%   | +0.6%   | +1.3%   |    1.2 |       97 | ↑    | 2026-08-01 |
| CREDIT_CARD_DELINQUENCY |     2.62       | -0.02pp | -0.02pp | -0.13pp |    0.5 |       39 | ↓    | 2026-04-01 |
| HOUSING_STARTS          |  1221          | -5.2%   | -15.1%  | -7.4%   |   -1.5 |        2 | ↓    | 2026-09-01 |
| HOUSEHOLD_NET_WORTH     |     1.9587e+08 | +7.0%   | +7.0%   | +11.8%  |    2.1 |       94 | ↑    | 2026-04-01 |

### Credit & Stress
| Indicator              |      Latest | Δ1M     | Δ3M     | Δ1Y     |   5Y Z |   5Y pct | 3M   | As of      |
|------------------------|-------------|---------|---------|---------|--------|----------|------|------------|
| HY_SPREAD              |  3.27       | +0.61pp | +0.58pp | +0.30pp |    0.5 |       77 | ↑    | 2026-10-21 |
| BAA_SPREAD             |  1.44       | +0.04pp | -0.17pp | -0.24pp |   -1.4 |        4 | ↓    | 2026-10-20 |
| AAA_SPREAD             |  0.97       | -0.02pp | -0.20pp | -0.11pp |   -0.2 |       40 | ↓    | 2026-10-21 |
| CORP_SPREAD            |  0.88       | +0.11pp | +0.10pp | +0.09pp |   -0.1 |       54 | ↑    | 2026-10-21 |
| ST_LOUIS_FIN_STRESS    | -0.63       | +0.22pp | +0.25pp | -0.15pp |   -0.4 |       40 | ↑    | 2026-10-16 |
| KANSAS_CITY_FIN_STRESS | -0.99       | -0.04pp | -0.22pp | -0.15pp |   -1.5 |        0 | ↓    | 2026-09-01 |
| FED_ASSETS             |  6.7536e+06 | +0.1%   | +0.2%   | +2.4%   |   -1   |       31 | →    | 2026-10-21 |

### Commodities & FX
| Indicator   |   Latest | Δ1M   | Δ3M    | Δ1Y    |   5Y Z |   5Y pct | 3M   | As of      |
|-------------|----------|-------|--------|--------|--------|----------|------|------------|
| WTI_CRUDE   |   107.89 | +6.4% | +27.9% | +84.9% |    2.1 |       95 | ↑    | 2026-10-20 |
| USD_INDEX   |   121.4  | +2.1% | +0.9%  | +0.6%  |    0.1 |       62 | →    | 2026-10-16 |
| USD_CNY     |     6.69 | -0.3% | -1.3%  | -6.1%  |   -1.1 |       12 | →    | 2026-10-16 |
| USD_EUR     |     1.12 | -2.7% | -1.9%  | -3.7%  |    0.5 |       64 | →    | 2026-10-16 |
| USD_JPY     |   158    | +1.9% | -2.7%  | +4.8%  |    1.1 |       88 | →    | 2026-10-16 |

### Policy & Trade
| Indicator                 |   Latest | Δ1M   | Δ3M    | Δ1Y    |   5Y Z |   5Y pct | 3M   | As of      |
|---------------------------|----------|-------|--------|--------|--------|----------|------|------------|
| US_POLICY_UNCERTAINTY     |   168.22 | -5.0% | -53.6% | -39.8% |   -0.3 |       51 | →    | 2026-10-21 |
| EUROPE_POLICY_UNCERTAINTY |   358.52 | +2.2% | -9.4%  | -23.9% |   -0.1 |       54 | ↓    | 2026-09-01 |
| TARIFFS                   |   306.4  | -6.1% | -6.1%  | +13.2% |    1.4 |       78 | ↓    | 2026-04-01 |
| CHINA_IMPORTS             | 27133.8  | +0.2% | +15.4% | +6.9%  |   -0.8 |       28 | ↑    | 2026-08-01 |
| TECH_PULSE                |    95.19 | -0.6% | -1.2%  | +1.7%  |    0.6 |       64 | ↓    | 2026-09-01 |
| RD_INVESTMENT             |   950.52 | +2.5% | +2.5%  | +12.2% |    2   |       94 | ↑    | 2026-04-01 |

### Logistics & Power
| Indicator            |    Latest | Δ1M   | Δ3M    | Δ1Y    |   5Y Z |   5Y pct | 3M   | As of      |
|----------------------|-----------|-------|--------|--------|--------|----------|------|------------|
| FREIGHT_PPI          |    534.8  | +0.4% | +6.0%  | +36.8% |    2.8 |       98 | ↑    | 2026-09-01 |
| TRUCK_PPI            |    219.38 | +4.6% | +10.8% | +17.9% |    2.4 |       98 | ↑    | 2026-09-01 |
| AIR_PPI              |    181.85 | -1.9% | -10.0% | +5.8%  |    0.7 |       80 | ↓    | 2026-09-01 |
| WAREHOUSE_PPI        |    166.87 | +0.7% | -0.4%  | +4.4%  |    0.9 |       80 | ↓    | 2026-09-01 |
| ELECTRIC_POWER_INDEX |    123.52 | +3.7% | +7.0%  | +10.8% |    3   |       98 | ↑    | 2026-09-01 |
| MFG_CONST            | 170701    | +0.2% | -1.7%  | -19.2% |   -0.4 |       26 | ↓    | 2026-08-01 |

<details><summary>Structural (slow)</summary>

| Indicator       |    Latest | Δ1M     | Δ3M     | Δ1Y     | 5Y Z   | 5Y pct   | 3M   | As of      |
|-----------------|-----------|---------|---------|---------|--------|----------|------|------------|
| US_POPULATION   | 343150    | +0.0%   | +0.1%   | +0.2%   | +1.3   | 98       | →    | 2026-10-01 |
| US_BIRTH_RATE   |     10.6  | -0.10pp | -0.10pp | -0.10pp | —      | —        | ↓    | 2024-01-01 |
| LIFE_EXPECTANCY |     78.89 | +0.6%   | +0.6%   | +0.6%   | —      | —        | ↑    | 2024-01-01 |

</details>
