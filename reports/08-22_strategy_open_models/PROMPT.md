# Strategy Report: Global Equities Correlated with Open AI Models (August 22, 2026)

## Objective
Execute an institutional-grade, data-driven quantitative analysis identifying US-available global equities directly correlated with the rise, proliferation, and execution of **Open AI Models** (e.g., Meta Llama 4, DeepSeek V3/R1, Alibaba Qwen 2.5). The analysis applies an **Exponentially Weighted Moving Correlation (EWMA, $\lambda=0.94$)** to weight recent post-DeepSeek and inference-era price action, models valuation arbitrage between Western pure-plays and Chinese open-model leaders, and projects structural capital expenditures and power grid bottlenecks through 2028.

## Target Audience
Macro & Quantitative Strategy Team, Operations Managers, and Institutional Asset Allocators managing multi-asset tech allocations across high-beta semiconductor design, custom ASICs, optical networking, baseload nuclear power, datacenter thermal cooling, and international open-weight tech champions.

## Core Thematic Pillars
1. **The Algorithmic Inflection & Jevons Paradox:**
   - How open-weight reasoning models (DeepSeek, Qwen, Llama) collapsed token input/output costs by >90%, triggering exponential inference query volume.
   - The shift from pure model training capex to custom ASIC and token-execution efficiency.
2. **China & International AI Champions (US-Available ADRs):**
   - **BABA** (Alibaba / Qwen 2.5), **BIDU** (Baidu / Ernie / Kunlun), **TCEHY** (Tencent / Hunyuan), **GDS** (Asian Hyperscale Data Centers), **KWEB**.
   - Analysis of structural valuation discounts (9x–14x forward P/E) vs Western peers.
3. **Custom Silicon, Foundry & Optical Interconnects:**
   - **NVDA**, **AMD**, **TSM**, **AVGO**, **MRVL**, **ARM**, **MU**, **ASML**, **ALAB**, **COHR**, **LITE**, **CDNS**, **SNPS**.
   - Broadcom/Marvell custom ASIC dominance (Meta MTIA, Google TPU, Amazon Trainium2) and Astera Labs/Coherent optical connectivity.
4. **Baseload Nuclear Power, Natural Gas & Grid Bottlenecks:**
   - **VST**, **CEG**, **GEV**, **PWR**, **ETN**, **NEE**, **CCJ**, **TLN**, **OKLO**, **SMR**.
   - Hyperscaler 20-year nuclear PPAs and substation interconnection queues exceeding 3–5 years.
5. **Datacenter Liquid Cooling & Neo-Clouds:**
   - **VRT**, **MOD**, **ANET**, **EQIX**, **CORZ**, **APLD**, **IREN**.
   - 100kW+ rack thermal density transition to direct-to-chip liquid cooling.
6. **Enterprise RAG & Data Moats:**
   - **PLTR**, **RDDT**, **SNOW**, **MDB**.

## Quantitative Workflow
- **Data Ingestion:** Fetch and align daily Close price series from `market_data/tickers/` (2018–2026) and fundamental balance sheet filings.
- **Statistical Model:** Calculate EWMA correlation matrix ($\lambda=0.94$) and synthetic Open Model Factor beta.
- **Momentum & Extension Screening:** Compute 14-day RSI, 200-day moving average distance, 20-day volatility, and 1-year Sharpe ratios.
- **Projections (2026–2028):** Project hyperscaler capex breakdown ($B) and AI datacenter electricity demand (TWh).
- **Decision Architecture:** Path-dependent allocation tree covering token commoditization, gridlock delays, and export control shocks.
