# Algorithmic Value Strategy - Screener Output

## Executive Summary
> *Analyzed **126 equities** utilizing Benjamin Graham's revised Intrinsic Value formula, substituting contemporary bond yields and trailing EPS. Objective: Identify deep-value dislocations in the market where growth estimates have not kept pace with pricing reality.*

- **Highest Margin of Safety:** GSL (Trading at a 89.6% discount)

## Data Quality & Potential Issues
> **Pipeline Diagnostics:** Out of `126` tickers analyzed, there are some data gaps that may affect metric coverage:
> - Missing Intrinsic Value (Often lacking Forward EPS/Growth projection): **20** tickers
> - Missing EPS Surprise (Missing quarterly expectations): **0** tickers
> - Missing Current Price data: **0** tickers

## Execution Matrix
Based on raw pricing efficiency against terminal growth estimates, the following dynamic decision matrix dictates capital flow.

![Decision Tree](./plots/value_decision_tree.png)

---
## Analytical Output

### 📉 Dislocation Curve (Value vs Earnings Surprise)
The following scatter plot maps theoretical discount against actual corporate earnings execution. Equities in the **upper-right quadrant** represent the holy grail of value investing: severely undervalued companies that are consistently beating consensus earnings.

![Intrinsic Value Scatter Plot](./plots/intrinsic_value_scatter.png)

> [!CAUTION]
> **The Value Trap:** High-discount equities residing in the *lower-left* quadrant are actively missing earnings, suggesting their 'cheap' valuation is a direct function of collapsing forward guidance rather than market inefficiency.

### 🏆 Top Deep Value Targets
*Filtered for positive execution (Surprise > 0) and high margin of safety (Discount > 0).*

| Ticker   | Name   | Portfolio_Weight_Pct   | Unrealized_PnL_Pct   | Graham_Value   | Discount_to_Intrinsic_Value_Pct   |   RSI | Dist_to_200MA   |   MACD | MA_Cross   | Time_Horizon       | Exit_Strategy                |
|:---------|:-------|:-----------------------|:---------------------|:---------------|:----------------------------------|------:|:----------------|-------:|:-----------|:-------------------|:-----------------------------|
| GSL      | GSL    | 0%                     | 0%                   | $382.29        | +89.57%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| ES       | ES     | 0%                     | 0%                   | $290.53        | +74.21%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| DAC      | DAC    | 0%                     | 0%                   | $391.29        | +70.81%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| DELL     | DELL   | 0%                     | 0%                   | $415.43        | +70.28%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| REGN     | REGN   | 0%                     | 0%                   | $2577.41       | +69.57%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| D        | D      | 0%                     | 0%                   | $194.96        | +67.39%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| LDOS     | LDOS   | 0%                     | 0%                   | $517.87        | +67.19%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| IBM      | IBM    | 0%                     | 0%                   | $709.76        | +66.53%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| FDX      | FDX    | 0%                     | 0%                   | $1016.40       | +62.36%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| SMCI     | SMCI   | 0%                     | 0%                   | $87.29         | +61.51%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| MSFT     | MSFT   | 0%                     | 0%                   | $1018.77       | +60.68%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| PAAS     | PAAS   | 0%                     | 0%                   | $163.10        | +60.58%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| ADBE     | ADBE   | 0%                     | 0%                   | $648           | +60.21%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| NOC      | NOC    | 0%                     | 0%                   | $1761.67       | +60.06%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| CRM      | CRM    | 0%                     | 0%                   | $477.21        | +59.82%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| WDC      | WDC    | 0%                     | 0%                   | $674.08        | +56.84%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| ORCL     | ORCL   | 0%                     | 0%                   | $338.95        | +56.37%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| HII      | HII    | 0%                     | 0%                   | $981.18        | +55.61%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| CSCO     | CSCO   | 0%                     | 0%                   | $177.12        | +55.33%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| NEE      | NEE    | 0%                     | 0%                   | $210.25        | +54.76%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| GOOG     | GOOG   | 0%                     | 0%                   | $689.37        | +54.59%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| LMT      | LMT    | 0%                     | 0%                   | $1367.28       | +52.64%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| BX       | BX     | 0%                     | 0%                   | $245.93        | +51.93%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| MA       | MA     | 0%                     | 0%                   | $1053.17       | +51.63%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |
| V        | V      | 0%                     | 0%                   | $549.02        | +42.99%                           |     0 | 0%              |      0 | N/A        | Value Hold (Years) | Mean Reversion to Fair Value |

---
*Generated algorithmically by `intrinsic_value_report.py`.*
