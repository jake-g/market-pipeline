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
| GSL      | GSL    | 0%                     | 0%                   | $387.16        | +89.56%                           |  82.8 | +33.42%         |   1.13 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| MATX     | MATX   | 0%                     | 0%                   | $872.23        | +80.67%                           |  61.6 | +44.87%         |   5.95 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| ES       | ES     | 0%                     | 0%                   | $291.17        | +74.22%                           |  80.6 | +12.45%         |   1.65 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| DAC      | DAC    | 0%                     | 0%                   | $399.23        | +70.80%                           |  87.8 | +26.13%         |   3.66 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| DELL     | DELL   | 0%                     | 0%                   | $409.31        | +70.33%                           |  56.6 | -4.95%          |   0.1  | Death      | Value Hold (Years) | Mean Reversion to Fair Value |
| REGN     | REGN   | 0%                     | 0%                   | $2533.91       | +69.58%                           |  51.5 | +21.37%         |   5.54 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| D        | D      | 0%                     | 0%                   | $194.32        | +67.40%                           |  54.1 | +7.93%          |   0.99 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| LDOS     | LDOS   | 0%                     | 0%                   | $536.46        | +67.22%                           |  43.8 | -0.61%          |  -4.58 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| IBM      | IBM    | 0%                     | 0%                   | $723.14        | +66.53%                           |  29.7 | -12.65%         | -15.96 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| FDX      | FDX    | 0%                     | 0%                   | $1030.48       | +62.38%                           |  72.8 | +49.95%         |  18.56 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| SMCI     | SMCI   | 0%                     | 0%                   | $84.10         | +61.62%                           |  54.2 | -22.52%         |   0.18 | Death      | Value Hold (Years) | Mean Reversion to Fair Value |
| MSFT     | MSFT   | 0%                     | 0%                   | $1021.32       | +60.67%                           |  56.3 | -17.01%         | -15.25 | Death      | Value Hold (Years) | Mean Reversion to Fair Value |
| PAAS     | PAAS   | 0%                     | 0%                   | $171.39        | +60.61%                           |  74   | +71.85%         |   2.46 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| ADBE     | ADBE   | 0%                     | 0%                   | $648           | +60.21%                           |  40.4 | -25.36%         | -13.3  | Death      | Value Hold (Years) | Mean Reversion to Fair Value |
| NOC      | NOC    | 0%                     | 0%                   | $1776.80       | +59.99%                           |  55.4 | +23.98%         |  18.99 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| CRM      | CRM    | 0%                     | 0%                   | $496.96        | +59.86%                           |  58.2 | -19.27%         | -10.41 | Death      | Value Hold (Years) | Mean Reversion to Fair Value |
| WDC      | WDC    | 0%                     | 0%                   | $654.33        | +56.86%                           |  57.6 | +114.39%        |  13.91 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| ORCL     | ORCL   | 0%                     | 0%                   | $344.69        | +56.39%                           |  60.9 | -31.64%         |  -8.22 | Death      | Value Hold (Years) | Mean Reversion to Fair Value |
| HII      | HII    | 0%                     | 0%                   | $996.47        | +55.54%                           |  76.8 | +47.58%         |  12.94 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| CSCO     | CSCO   | 0%                     | 0%                   | $174.57        | +55.26%                           |  41.2 | +10.30%         |   0.09 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| NEE      | NEE    | 0%                     | 0%                   | $203.24        | +54.74%                           |  59.1 | +17.96%         |   2.37 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| GOOG     | GOOG   | 0%                     | 0%                   | $675.36        | +54.52%                           |  28.4 | +23.16%         |  -4.56 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| LMT      | LMT    | 0%                     | 0%                   | $1357.08       | +52.72%                           |  63.6 | +31.33%         |  22.74 | Golden     | Value Hold (Years) | Mean Reversion to Fair Value |
| BX       | BX     | 0%                     | 0%                   | $245.93        | +52.04%                           |  40.6 | -22.26%         |  -7.53 | Death      | Value Hold (Years) | Mean Reversion to Fair Value |
| MA       | MA     | 0%                     | 0%                   | $1062.73       | +51.56%                           |  34   | -8.25%          | -10.35 | Death      | Value Hold (Years) | Mean Reversion to Fair Value |

---
*Generated algorithmically by `intrinsic_value_report.py`.*
