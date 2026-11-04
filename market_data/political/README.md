# 🗳️ Political Sentiment Dataset (`political_odds.tsv`, `political_events.tsv`)

## Overview
Daily "political sentiment" for the market pipeline: prediction-market odds for
key elections / policy events, a presidential approval poll average, and a
small key-events calendar. Maintained by `political_fetcher.py`
(`make political-fetch`). All sources are free and keyless.

## Sources
| Source | Endpoint | Used for |
| :--- | :--- | :--- |
| Polymarket Gamma | `https://gamma-api.polymarket.com/events?slug=…` (fallback `/public-search?q=…`) | Resolve `config.POLITICAL_MARKETS`, current `outcomePrices`, volume, token ids |
| Polymarket CLOB | `https://clob.polymarket.com/prices-history?market=<clobTokenId>&interval=max&fidelity=1440` | Daily price history (`--backfill`) |
| VoteHub | `https://api.votehub.com/polls?poll_type=approval&subject=Trump` | Approval polls → 14-day rolling average |
| `config.POLITICAL_EVENTS` | hand-maintained | Key-events calendar |

## `political_odds.tsv` (long format; unique on `Date, Key, Outcome`)
| Column | Description |
| :--- | :--- |
| `Date` | `YYYY-MM-DD` (local day of the last Polymarket print; poll end-date for approval) |
| `Key` | Config key (e.g. `house_2026`, `senate_2026`, `approval_trump`) |
| `Category` | `elections`, `elections_2028`, `approval`, `fed`, `fiscal`, `economy`, `trade`, `geopolitics`, `domestic`, `markets`, `foreign_elections` |
| `Question` | Event title (Polymarket) or approval series description |
| `Outcome` | Sub-market label (e.g. `Democratic Party`, `25 bps increase`, candidate name), `Yes` for binary markets, `Approve`/`Disapprove` for polls |
| `Prob` | Probability 0–1 (Polymarket Yes price) or poll share 0–1 |
| `Volume_USD` | Polymarket sub-market lifetime volume (current value, repeated across history rows); poll count for approval rows |
| `Source` | `polymarket` or `votehub` |
| `Market_Id` | Gamma market id, or `votehub:approval:Trump` |

Notes:
* Multi-outcome events (e.g. 2028 nominees) keep only the top 6 outcomes by
  current probability; resolved sub-markets (`closed=true`) are skipped.
* Approval is a plain mean of all pollsters' Approve/Disapprove over a 14-day
  trailing window (no house-effect or quality weighting). VoteHub's feed lags
  by several weeks; the Polymarket `approval_low_2026` market is the
  forward-looking complement.
* Slugs in `config.POLITICAL_MARKETS` are pinned. Entries containing spaces
  fall back to Gamma free-text search (highest-volume open event) and log the
  resolved slug — verify before trusting a new entry. Dated markets
  (e.g. `fed-decision-in-december-…`, `october-inflation-us-annual`) must be
  rolled forward by hand when they resolve.

## `political_events.tsv`
`Date, Event, Category, Notes` — key dates through the 2028 US presidential
cycle: midterms/primaries/conventions, FOMC/ECB/BoE/BoJ decisions, CPI,
funding and debt-ceiling deadlines, and major foreign events (China NPC and
Party Congress, PLA centenary, France 2027, Taiwan 2028, UK/India/Mexico
elections, USMCA review, G7/G20). `approx`/`TBD` in `Notes` means not yet
officially scheduled. Edit `config.POLITICAL_EVENTS` to maintain.

## Running
```
python political_fetcher.py                      # daily incremental
python political_fetcher.py --backfill --days 120  # daily history via CLOB
```
Responses are cached with joblib under `.cache/political` for
`config.CACHE_EXPIRY_POLITICAL` seconds. Merging is idempotent.
