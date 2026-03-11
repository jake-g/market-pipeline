# ORCL Q3 Earnings Trade Analysis

## Executive Summary
> Oracle (ORCL) has pivoted aggressively from a legacy database software company to a massive Tier-1 Cloud Infrastructure provider. This report analyzes the recent earnings print and provides predictive scenarios for near-term price action.

## Intraday Ground Truth & Historical Context
Before looking forward, here is the immediate post-earnings price action:

![ORCL Intraday Trajectory](./plots/orcl_intraday_ground_truth.png)

## Predictive Scenario Bounds (48H)
Based on the technical data and historical fades, we project three viable paths for the next 48 hours:

![ORCL Predictive Trajectory](./plots/orcl_trajectory_prediction.png)

*   **Scenario 1: AI Acceleration** - Institutional buyers overwhelm normal fade patterns due to high OCI growth.
*   **Scenario 2: Structural Fade** - The stock follows historical norms, fading the initial gap over 2-3 days.
*   **Scenario 3: Siphon Rotation** - A broader market rejection pulls capital away from the extended gap.

## Short-Term Trading Decision Tree
For a portfolio currently holding 0 ORCL shares aiming for a short-term swing:

![ORCL Decision Tree](./plots/orcl_decision_tree.png)

### Historical Earnings Reactions
| Earnings_Date             | Surprise_Pct   | Open_Change_Pct   | High_Change_Pct   | Close_Change_Pct   |
|:--------------------------|:---------------|:------------------|:------------------|:-------------------|
| 2023-03-09                | +1.44%         | +0.73%            | +1.73%            | -3.22%             |
| 2023-06-12                | +5.56%         | +9.35%            | +9.94%            | +0.21%             |
| 2023-09-11                | +3.46%         | -9.00%            | -8.01%            | -13.49%            |
| 2023-12-11                | +0.95%         | -8.56%            | -6.56%            | -12.44%            |
| 2024-03-11                | +2.47%         | +12.95%           | +15.74%           | +11.75%            |
| 2024-06-11                | -1.14%         | +10.66%           | +15.81%           | +13.32%            |
| 2024-09-09                | +4.29%         | +11.89%           | +16.45%           | +11.43%            |
| 2024-12-09                | -0.77%         | -7.77%            | -5.47%            | -6.67%             |
| 2025-03-10                | -1.35%         | -2.63%            | -1.03%            | -3.10%             |
| 2025-06-11                | +3.37%         | +8.40%            | +15.55%           | +13.31%            |
| 2025-09-09                | -0.62%         | +32.74%           | +43.77%           | +35.95%            |
| 2025-12-10 (Latest Print) | +38.04%        | -14.30%           | -9.19%            | -10.83%            |

*   **Historical Average Gap Up (Open):** `+5.34%`
*   **Historical Average Intraday Peak:** `+8.90%`
*   **Historical Average Close:** `+4.28%`

#### The 'Fade' Pattern
Historically, ORCL gaps up but fades through the week. The chart below illustrates the T1 Close relative to the Open/High:

![ORCL Fade Pattern](./plots/orcl_fade_pattern.png)

#### EPS Surprise vs. Close
The scatter plot below highlights how the market reacts to the magnitude of the EPS surprise:

![ORCL Surprise Scatter](./plots/orcl_surprise_scatter.png)

### Implied Volatility (IV) Crush Metrics
*The 'Gap Trap': Tracking options premium decay from the Intraday Peak (FOMO) to the Final Close.*

| Earnings Date   | Intraday Peak (High)   | T+1 Final Close   | Premium Decay (Crush)   |
|:----------------|:-----------------------|:------------------|:------------------------|
| 2023-03-09      | +1.73%                 | -3.22%            | -4.95%                  |
| 2023-06-12      | +9.94%                 | +0.21%            | -9.73%                  |
| 2023-09-11      | -8.01%                 | -13.49%           | -5.48%                  |
| 2023-12-11      | -6.56%                 | -12.44%           | -5.88%                  |
| 2024-03-11      | +15.74%                | +11.75%           | -3.99%                  |
| 2024-06-11      | +15.81%                | +13.32%           | -2.49%                  |
| 2024-09-09      | +16.45%                | +11.43%           | -5.02%                  |
| 2024-12-09      | -5.47%                 | -6.67%            | -1.21%                  |
| 2025-03-10      | -1.03%                 | -3.10%            | -2.07%                  |
| 2025-06-11      | +15.55%                | +13.31%           | -2.24%                  |
| 2025-09-09      | +43.77%                | +35.95%           | -7.83%                  |
| 2025-12-10      | -9.19%                 | -10.83%           | -1.65%                  |

*   **Average Premium Decay per Quarter:** `-4.38%`

![ORCL IV Crush](./plots/orcl_iv_crush.png)

## Recent Industry News Context
> *Aggregated context to provide NotebookLM with the overarching industry narrative*

- **ORCL (03/10)**: [Oracle pops as Q3 results, guidance top estimates; updates on capital funding plans (ORCL:NYSE) - Seeking Alpha](https://news.google.com/rss/articles/CBMiuwFBVV95cUxPbFFkYUphdS1iZGJxZnFrZXphR05kQmVKZ3lxR1pXVVF2YWV5Y2VoYXFOVnNycWlXblpEdkc5ZDd2ZndadWlpMVZ1RVJINWRWbENLQndmRTYtQUliU1lRYmlBQUt2YkJxa2tGa0xtMDBIazhYUVN5SmY1eWVWQ3pVVmVQWWtSeUNMY3RncHZlVDFINjdsM0ZjdWtlMkNfQjNUMUJIRGNqelk2LTNvQmgtdXQzYzBLMWs1blhj?oc=5)
- **ORCL (03/10)**: [Oracle Earnings Prediction Market Preview: What Will Larry Ellison Say? - Benzinga](https://news.google.com/rss/articles/CBMi0gFBVV95cUxNYlFEWTItZFRmbTZhcDlxdkhtWFpSZjZDSEZHOHhXbWlYR1BJWExzN2JnT3I2WjdKQ2RjQlRnZ3dFenpBeUREemozbGRwYVZQcjBVeHk5OEFkWnZJc09VdUc3NnBtSVRjR0EyVEF4SjdxOTNYZHg1SE4tdWtCNFYzQjFLVHNzaUFrTHZYdWE5YjNjcjdUTFJHWlpqUzYxMFFDckdlc2MwaXY2Q0hSOFF1QUFtLVBzTENoUmtoTXdlZXBVXzZLaWl5dFlyM1VVRl9kZHc?oc=5)
- **AMZN (03/10)**: [Amazon’s Massive Bond Sale Draws $126 Billion in Orders, One of the Largest Ever - TipRanks](https://news.google.com/rss/articles/CBMiqwFBVV95cUxNZjRQaDNxaWpweDVrNkU5cEV6Si1PTzUtLTlydWdOTFJXb3dCa2xBcUNEdkM2SzAtM1hQQTAyeFN5bndRS3V6eHJYWHJicWViSm04Ul9ZdEpsU3hfbEJVQVRQQ0syUXZnZkxaWTZwT3ZyV09mQ3IybzJrSm85OWlOLXdTSUE2Y1l0cUlWODB6eEZoVmtfREREWmtabzNraXNGYnJSTHB1VFF5bVE?oc=5)
- **AMZN (03/10)**: [Amazon’s Record Bond Sale Tests AI Ambitions And Balance Sheet Choices - simplywall.st](https://news.google.com/rss/articles/CBMixAFBVV95cUxQVEVzeU1meXBYVFVNZ0dlM0ZWX3ZOZFhGY2VudUlqTzRnb0VhRndoSWM2b3dxcmZYMXhFOWxmRVZtU0VxWWtvTm91QnZzanlFa3dkYTJLMURYZVBEcW14RXhYWDlDSlVmd3d5RXVxd21Fd05IUER3TEI0blZXWVpraTIweURtWnVmM2dxcEFiS3pEdzkzR3I2TTRHNGNOOGpqWHBhUVNWLUpEem1Cd0JZNGl2WEhsMDZXUml3aUhEeGZTLW1m0gHKAUFVX3lxTE9TTHBuTkZTWmVoUl93ZGRsQU5GN3B6a2VkcjBCQVFjVmRYSWxiNGtRMHl0R1k5N0d5OXVqYS10d3lMdjdmb05Fc21WMThISkplbXB1cE9FSE0xVFprZ2dHNUF5UGtqeDVubXVlX1JEajVmT3EtVUJCd2REa09ENFJJOExrZUdyemVtX0FtQTdOWk9qZENqV3k1R0MzM01FeW4wQTdrclF1VFlISlNCUlNDSFVna0VEYndrNXFsYmVkX1ZtZWl0a2o4ZkE?oc=5)
- **AMZN (03/10)**: [OpenAI Gave Amazing News to Amazon Shareholders - The Motley Fool](https://news.google.com/rss/articles/CBMilAFBVV95cUxPblo4UDNKbE84N2FMbHRHYnpvX1daendLaFF4NTJVa25tNVBMYnlyZ0NFemJtQ0M2N0ttcXM0emtGYUZsYnNMSjRuWlR1bGRMSzRaaTIwVFJmUEU2OEZpT2thTmd4M2M0emxOc2gtTTNQODE1SmpneFhwQVJWLTNKSlphN2hiMGphaG14dEdnQmo0b1VG?oc=5)
- **AMZN (03/10)**: [Amazon Looks to Raise at Least $37 Billion Through Bond Sale - Bloomberg](https://news.google.com/rss/articles/CBMipgFBVV95cUxPb0kwUXhXN1hJUUk1MThXRzZ3bzhPRWxsQ1VrRllNb0lreHJTeldmT3QyRmNyLW9TM1dhZm8wR3pXVVdyU2J0VloxNXh2Q2NGMlJ2SGVBaXhiVVExcjUtS0Z3TkVXUWc5TVVNbVZNQmR1eHRMTVlmMl95TnBUZzMyWmJwSzVsVUhWQ1FwTU81RXRVNWM2V3VTN2llUk5KZjdyT0VIb2xn?oc=5)
- **AMZN (03/10)**: [Oracle Stock Jumps After Earnings Beat. AI Powers Stronger-Than-Expected Cloud Growth.](https://finance.yahoo.com/m/c807dae4-6fa8-3d07-a982-32e3af39e313/oracle-stock-jumps-after.html?.tsrc=rss) - *Oracle stock jumped late Tuesday after the enterprise and cloud-computing giant company reported fiscal Q3 results.*
- **AMZN (03/10)**: [An Investor Just Bought $6 Million of This Stock That's Up 272% in a Year. Here's Whether It Still Has Room to Run](https://www.fool.com/coverage/filings/2026/03/10/an-investor-just-bought-usd6-million-of-this-stock-that-s-up-272-in-a-year-here-s-whether-it-still-has-room-to-run/?.tsrc=rss) - *This communications infrastructure firm serves global network operators and enterprises with integrated hardware and software solutions.*
- **AMZN (03/10)**: [Marvell Technology Shares Jump on Strong AI Growth. Is It Too Late to Buy the Stock?](https://www.fool.com/investing/2026/03/10/marvell-technology-strong-ai-growth-buy-stock/?.tsrc=rss) - *The stock has been on a roller-coaster ride the past year.*
- **AMZN (03/10)**: [Amazon Stock (AMZN) Flat on Turn to Bond Market to Raise Up to $42B - TipRanks](https://news.google.com/rss/articles/CBMimgFBVV95cUxPS3d6bDVvelQzLXM2UHNfVllKQ0lZbVAxZ1RNSGttaVdxSXpwX2I0cFAwRWt1dVd4X2xtQWh1c0hXYlNJZHBqQWtpblV4ZWt4SjdrVVZmZjBFZk40dk1xNGlLLTNydFFtSTVROTRjaTNYRF91aVB0aHU5cmRkVDd5SlZPVWhxN3NLbnpqcVlyUUFCT2lOOTRZLXFn?oc=5)
- **AMZN (03/10)**: [This Latin American e-commerce giant is beating Amazon - thestreet.com](https://news.google.com/rss/articles/CBMiogFBVV95cUxPUnBhSTM0dVZxQWJIT1VjWG1kSnR2YUpob21pYkVvTlFaMGx0Mk1HNTdQdDBXZWV2Z3g1Y1FnTDZwcmlXVTVicU5Ndk1CaUhMbVplUzFfTllUQnU2S0t6Yk05dXdEWkowbVFWRVpQWTRoa1lKenBmXy1Hd1RDcnp2c2ZLMzhrQ2xUeUprc3VlX1pFTHN5OVU4bG53Um5iVmppdUE?oc=5)
- **AMZN (03/10)**: [Stock Movers: Oracle, Amazon, Goeasy - Bloomberg](https://news.google.com/rss/articles/CBMikwFBVV95cUxPZjFKaFB3SkVua3dWbG5HcmZSMXVaajMtTE93OEo0S1NQR2hXdnFxVjUxaURfSVpVSml6ODVnb0wzMkxPSDBqLWtqdVI3Y3diSVFPSTlpaHhTVkV0RmdXQ3dYcWRoWW5XVHhQaVdsa3V6elVtd3RMSVF6b0Z5WWxRZHliZkIwdGtJTTFfRWFIVDlLWU0?oc=5)
- **AMZN (03/10)**: [Musk Says 'Proceed With Caution' As Amazon's AI Bites Back - Amazon.com (NASDAQ:AMZN) - Benzinga](https://news.google.com/rss/articles/CBMioAFBVV95cUxPeUZfRDdrYjU0WXlIMm9QOHB1cFFSZEFlSEliNFM1UTVvZVBJTmZXWkhFaC1iVmlDMGMwOGJCMUNhYnRrX1JQR3RyajYxeTVUY3B4d2x6eGNyYnJHS3FBcHlxSVlqNFZ1M2xzTlFDZzJmMEp3Y1dDUkd4c0dvSmt6TVlqRk5ONVhWMEZJbjBWSkphMHpKMWdEbDJYV2dxYnct?oc=5)
- **AMZN (03/10)**: [Mom removes Amazon Alexa after device asks 4-year-old about her clothing - FOX19 | Cincinnati](https://news.google.com/rss/articles/CBMisgFBVV95cUxPc2JFazNYc2xvNXMxdnJxa0syQVVZZXlMRzFCUlE1MmY5WG9IWFNGbVdwelQ4RnhfSWEtb09jQkZOX1I4RDhFaFhNLXZENjZxdW8yRzBlRVI1VzFSX1FINkNhQlN3Z0RuWTlaUG1SM191S2ZYRVBPS2RWbjZ0QUNPaWlnY19iQTFLRmFteGNyMzY3RTdCTzJnaGQ0RVI4MFFmbXJMQ1ZtZUVIdlExR0Q5QllR0gHGAUFVX3lxTFBMYXlfMW8ySGFPZWdweFdJMjhqLVVQcnFnSExlTmhJMERqQ0JyYnNJX2ZreUJPd1A1NEMyUGk3SDNwNV9JODVkdnpkRFZRdE96YThhRmRCVHdiU0JfcmdZVmpnZEpOVXJvOGM0d3pkWkdiS3FCNTFhQWQzaWpzN2tBeVpya2pOSkVFcG5ZMmVrUlpQSzd6U3lIZ1JaYlJ4Q2l6XzJwYVJIUk1yMWhVRFJTdHVJM0hWaDYtd0RIbVhHUzdhcWpPUQ?oc=5)
- **AMZN (03/10)**: [Microsoft Stock Holds Key Level Amid Volatility; Is Microsoft A Buy Now?](https://finance.yahoo.com/m/642550a9-8bff-3dee-9bca-bcc9f001fddc/microsoft-stock-holds-key.html?.tsrc=rss) - *Microsoft stock ended lower but held a key level Tuesday amid volatility stemming from the U.S.-Iran war.  Is Microsoft stock a buy or sell now?  S...*\n\n


---

# AI Tactical Summary
> **[View Primary Active Reports Archive directly in NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**

Portfolio health is volatile, concentrated in **AI infrastructure** [1, 2]. Key metrics reveal aggressive debt-loading for scaling (AMZN) and consistent "gap trap" patterns in cloud providers (ORCL) [2, 3]. Broad market geopolitical tension is currently testing technical support levels for core mega-cap holdings [2].

**Overextended Names:**
1. **Communications Infrastructure Firm**: Up 272% annually; extreme profit-taking candidate [2].
2. **Marvell (MRVL)**: Recent AI-driven jump following a high-volatility "roller-coaster" year [2].
3. **Oracle (ORCL)**: Significant intraday "Fade Pattern" risk; historically loses 4.38% premium post-earnings [4, 5].

**Value/Long-Term Plays:**
1. **Amazon (AMZN)**: Flat pricing despite $126B bond demand; long-term AI infrastructure play [2].
2. **Microsoft (MSFT)**: Maintains key technical levels despite U.S.-Iran war volatility [2].
3. **Oracle (ORCL)**: Tier-1 Cloud pivot provides long-term value despite immediate post-earnings "Scenario 2" fade risk [1, 3].

**Weekly Trade Advice:**
*   **ORCL**: **SELL/WAIT**. Historical data predicts a structural fade over 48 hours [1, 3].
*   **Communications Stock**: **SELL**. Realize gains from 272% run [2].
*   **AMZN**: **HOLD**. Record bond sale orders indicate high institutional demand [2].
*   **MSFT**: **HOLD**. Monitor support levels amid macro volatility [2].

## References
1. [1] ORCL Q3 Earnings Trade Analysis: Executive Summary
2. [3] ORCL Q3 Earnings Trade Analysis: Historical Earnings Reactions
3. [4] ORCL Q3 Earnings Trade Analysis: The 'Fade' Pattern
4. [5] ORCL Q3 Earnings Trade Analysis: Implied Volatility (IV) Crush Metrics
5. [2] Recent Industry News Context: Aggregated news snippets (Seeking Alpha, Bloomberg, etc.)
