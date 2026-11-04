import datetime
import os

from dotenv import load_dotenv

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")
MARKET_DATA_DIR = DATA_DIR
TICKERS_DIR = os.path.join(DATA_DIR, "tickers")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")

# API Keys (prefer loading from .env)
load_dotenv()  # Load secrets from personal .env file
FRED_API_KEY = os.environ.get("FRED_API_KEY")
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY")
# Support for multiple keys (comma-separated) for rotation
ALPHA_VANTAGE_KEYS = []
if ALPHA_VANTAGE_KEY:
  ALPHA_VANTAGE_KEYS = [k.strip() for k in ALPHA_VANTAGE_KEY.split(",")]

# Shipping & Logistics APIs
AISSTREAM_API_KEY = os.environ.get("AISSTREAM_API_KEY")

# Switch for Alpha Vantage
ENABLE_ALPHA_VANTAGE = True

ALIAS = os.environ.get("ALIAS", "Mr. Stonk")
HTTP_USER_AGENT = os.environ.get("HTTP_USER_AGENT", f"{ALIAS} stonk@market.com")

DEFAULT_START_DATE = "2018-01-01"
DEFAULT_END_DATE = datetime.date.today().strftime("%Y-%m-%d")
DEFAULT_NEWS_DAYS = 360  # Google News supports ~140 days; safely capturing 4 months
DEFAULT_NEWS_LIMIT = 100  # Increased to capture earnings, politics, and niche analysis
FUZZY_DEDUPE_THRESHOLD = 0.8  # Threshold for dropping similar news headlines

# Expanded News Topics
# These topics are used to fetch general market news not specific to a single ticker.
# yapf: disable
NEWS_TOPICS = [
    # AI, Compute & Mega-IPOs
    "AI", "Compute Power", "Data Center", "GPU", "Generative AI",
    "AI Regulation", "Technology", "Big Tech", "Sovereign AI", "Hyperscalers",
    "Circular Deals", "AI Agents", "Custom Silicon", "Cybersecurity",
    "Quantum Computing", "Physical AI", "Inference Infrastructure", "Edge AI",
    "High Bandwidth Memory", "HBM Shortage", "Silicon Photonics",
    "Optical Interconnects", "Liquid Cooling", "AI Data Licensing",
    "AI CapEx ROI", "AI Debt Financing", "Neocloud", "AI Bubble",
    "Anthropic IPO", "OpenAI IPO", "AI IPO", "SpaceX IPO", "Robotaxi",
    "Humanoid Robots", "Rack-Scale AI", "Agentic Commerce",

    # Energy, Grid & Commodities
    "Energy", "Oil", "OPEC+", "Nuclear Energy", "Uranium", "Natural Gas",
    "Power Grid", "Renewable Energy", "Commodities", "Electricity Demand",
    "AI Energy Demand", "Data Center Power", "Small Modular Reactors",
    "Nuclear PPAs", "Gas Turbines", "Grid Transformers", "Copper Demand",
    "Battery Storage", "Grid Modernization", "Power Grid Constraints",
    "Geothermal Energy", "Water Security", "Lithium", "Rare Earths",
    "Data Center Electricity Prices", "Gold Price", "Silver Price",

    # Supply Chain, Chips, Space & Shipping
    "Supply Chain", "Shipping", "Logistics", "Freight", "Container Rates",
    "Semiconductor Fabs", "Chip Shortage", "Memory Shortage", "EDA Software",
    "Advanced Packaging", "CoWoS Packaging", "Foundry Business",
    "Glass Substrates", "Chip Export Controls", "Chinese Semiconductors",
    "Nearshoring", "Commercial Space", "Satellite Direct-to-Cell",
    "Memory Supercycle", "Semiconductor Tariffs", "Port Congestion",
    "Tanker Rates",

    # Countries & Regions
    "Iran", "Russia", "Ukraine", "Venezuela", "Pakistan", "China", "Taiwan",
    "United States", "India", "Middle East", "Mexico", "Israel", "Canada",
    "Japan", "Europe", "South Korea", "Saudi Arabia", "Cuba", "Greenland",

    # Macro, Bond Yields, Elections & Geopolitics
    "Inflation", "Inflation Expectations", "Stagflation", "Federal Reserve",
    "Fed Rate Hike", "Fed Chair", "Interest Rates", "Treasury Yields",
    "Bond Vigilantes", "Credit Spreads", "Private Credit", "Recession",
    "GDP", "US Economy", "US Debt", "Government Shutdown", "Debt Ceiling",
    "US Midterm Elections", "Midterm Results", "Democratic Congress",
    "2028 Presidential Election", "Geopolitics", "War", "Sanctions",
    "Tariffs", "Trade War", "Tariff Supreme Court", "US China Trade Deal",
    "Global Markets", "Bitcoin ETF", "Crypto Regulation", "Tokenization",
    "Stablecoins", "Prediction Markets", "GLP-1 Weight Loss",
    "Drug Pricing", "De-dollarization", "Commercial Real Estate", "Drones",
    "Autonomous Drones", "Defense Tech", "Hormuz", "Taiwan Strait",
    "Russia Ukraine Ceasefire", "France Election 2027", "SaaS Valuation Reset",
    "Antitrust Big Tech", "Consumer Sentiment", "Labor Market", "Housing Market"
]
# yapf: enable

# Sectors & Tickers
SECTORS = {
    "Macro Indices": [  #  Major Indices and Volatility measures
        "^GSPC", "^IXIC", "GC=F", "CL=F", "^TNX", "^VIX", "^DJI", "^RUT", "SPY",
        "VIXY", "QQQ", "DIA", "IWM", "TLT", "AIPO"
    ],
    "Chips & Semi": [
        "NVDA", "AMD", "INTC", "TSM", "ASML", "MU", "MPWR", "AVGO", "SMH",
        "LRCX", "AMAT", "ENTG", "WDC", "NVT", "COHR", "ARM", "QCOM", "TXN",
        "ON", "ADI", "KLAC", "CDNS", "SNPS", "APH", "SOXQ", "MRVL", "SWKS",
        "STM", "TTDKY", "TTMI", "SOXX", "XSD", "SMHX", "MUZ", "ALAB", "LITE",
        "FN", "DRAM", "QTUM", "CLS", "EUV"
    ],
    "AI & Big Tech": [
        "GOOG", "PLTR", "MSFT", "META", "AAPL", "ORCL", "IBM", "AMZN", "SNOW",
        "CRM", "ADBE", "CSCO", "NOW", "RDDT", "IONQ", "PANW", "CRWD", "NET",
        "DELL", "HPE", "SMCI", "TTD", "VGT", "APP", "MNDY", "DDOG", "FTNT",
        "ZS", "NBIS", "CRWV", "MDB", "CHAT"
    ],
    "China & Intl AI": [
        "BABA", "BIDU", "TCEHY", "PDD", "JD", "GDS", "VNET", "KWEB", "FXI"
    ],
    "Auto & Robot": [
        "TSLA", "TM", "F", "ACHR", "JOBY", "RIVN", "UBER", "SYM", "PATH",
        "ASTS", "LUNR"
    ],
    "Energy & Power Grid": [
        "XOM", "CVX", "CCJ", "NEE", "XLE", "FSLR", "SHEL", "TTE", "BP", "COP",
        "EOG", "SLB", "HAL", "URA", "D", "ES", "VST", "CEG", "CNP", "SO", "GE",
        "GEV", "ETN", "PWR", "LIN", "WM", "VDE", "FENY", "VPU", "FUTY", "NLR",
        "ENPH", "FLNC", "KULR", "NXT", "TLN", "OKLO", "SMR", "URNM"
    ],
    "Aerospace & Defense": [
        "LMT", "RTX", "ITA", "NOC", "GD", "BA", "TDG", "HII", "AXON", "LDOS",
        "KTOS", "AVAV", "ESLT", "VSAT", "RKLB", "SPCX", "NASA"
    ],
    "Crypto & Minerals": [
        "BTC-USD", "ETH-USD", "COIN", "MARA", "RIOT", "MSTR", "CLSK", "NEM",
        "GOLD", "PAAS", "FCX", "SCCO", "VALE", "RIO", "BHP", "BMNR", "HUT",
        "CAT", "IBIT", "GLDM", "SOL-USD", "ALB", "SQM", "CF", "MEOH", "COPX",
        "LIT"
    ],
    "Data Center & Infra": [
        "EQIX", "DLR", "AMT", "CCI", "VRT", "ANET", "IRM", "BX", "SCHH", "MOD",
        "CORZ", "IREN", "WULF", "GLW", "APLD", "CIFR"
    ],
    "Shipping & Logistics": [
        "ZIM", "FDX", "UPS", "MATX", "GSL", "DAC", "SBLK", "BDRY", "AMKBY",
        "PAVE", "CNI", "CP", "EXPD", "CHRW", "STNG", "FRO"
    ],
    "Bio & MedTech": [
        "NVO", "LLY", "ISRG", "VRTX", "REGN", "SYK", "VHT", "AMGN", "ABBV",
        "PFE", "MRK", "JNJ", "BSX", "MDT", "TMO", "MRNA", "PPH", "OZEM"
    ],
    "Water & Desalination": ["AWK", "XYL", "CWCO", "AWX", "DD", "FIW"],
    "Consumer & Finance": [
        "CMG", "WMT", "COST", "DE", "BLK", "V", "MA", "JPM", "VDC", "HD", "LOW",
        "PG", "KO", "GS", "MS", "BAC", "O", "PLD", "DIS", "HOOD"
    ],
    "Broad Market & Intl ETFs": [
        "VOO", "VTI", "VTSAX", "SCHG", "VUG", "VIGAX", "SCHV", "VTV", "SCHD",
        "VEA", "VWO", "EFA", "EEM", "URTH", "CIBR", "VIG", "VIS", "VYM", "VAW",
        "VXUS", "EWY", "SCHB"
    ],
    "Mutual Funds": ["VMFXX", "VFTAX", "VIGIX", "VIIIX", "VEMRX", "VTIFX"],
    "Fixed Income & Preferred": [
        "PFFD", "PFXF", "FAGOX", "FASPX", "VBIL", "VUSB"
    ],
    "Bonds & Rates": [
        # Wealthfront Automated Bond Portfolio holdings
        "FLRN",
        "FLTR",
        "GBIL",
        "HYLB",
        "SCHO",
        "SHV",
        "SHY",
        "SHYG",
        "SJNK",
        "USHY",
        "VCSH",
        "VGLT",
        # Benchmarks by duration / credit bucket (401k proxies: BND, BNDX)
        "SGOV",
        "VGSH",
        "VGIT",
        "IEF",
        "BND",
        "BNDX",
        "LQD",
        "HYG",
        "TIP"
    ],
    "Thematic ETFs": [
        # Gaps in the sector-ETF matrix: grid, defense, robotics, software,
        # space (longer history than NASA), data-center REITs, biotech,
        # clean energy, silver
        "GRID",
        "SHLD",
        "BOTZ",
        "IGV",
        "UFO",
        "SRVR",
        "XBI",
        "ICLN",
        "SLV"
    ]
}
# yapf: enable

# Treated as cash in household asset-class roll-ups.
CASH_LIKE_TICKERS = ("CASH", "VMFXX", "SGOV", "VBIL", "SHV", "GBIL", "VUSB",
                     "SPAXX", "SWVXX")

# Political sentiment (political_fetcher.py). Each entry resolves a Polymarket
# Gamma *event* by slug; if `slug_or_query` contains spaces it is treated as a
# free-text search instead. Keep this list small and easy to edit.
# yapf: disable
POLITICAL_MARKETS = [
    {"key": "house_2026", "category": "elections",
     "slug_or_query": "which-party-will-win-the-house-in-2026"},
    {"key": "senate_2026", "category": "elections",
     "slug_or_query": "which-party-will-win-the-senate-in-2026"},
    {"key": "approval_low_2026", "category": "approval",
     "slug_or_query": "how-low-will-trumps-approval-rating-go-in-2026"},
    {"key": "fed_decision_dec_2026", "category": "fed",
     "slug_or_query": "fed-decision-in-december-20260729232808632"},
    {"key": "fed_rate_end_2026", "category": "fed",
     "slug_or_query": "what-will-the-fed-rate-be-at-the-end-of-2026"},
    {"key": "powell_out", "category": "fed",
     "slug_or_query": "jerome-powell-out-from-fed-board-by"},
    {"key": "gov_shutdown", "category": "fiscal",
     "slug_or_query": "government-shutdown-by"},
    {"key": "us_recession_2026", "category": "economy",
     "slug_or_query": "us-recession-by-end-of-2026"},
    {"key": "china_tariff_2026", "category": "trade",
     "slug_or_query": "us-tariff-rate-on-china-on-december-31-2026"},
    {"key": "us_invade_iran", "category": "geopolitics",
     "slug_or_query": "will-the-us-invade-iran-before-2027"},
    {"key": "trump_impeached_2026", "category": "domestic",
     "slug_or_query": "will-trump-be-impeached-by-december-31-2026"},
    {"key": "dem_nominee_2028", "category": "elections_2028",
     "slug_or_query": "democratic-presidential-nominee-2028"},
    {"key": "gop_nominee_2028", "category": "elections_2028",
     "slug_or_query": "republican-presidential-nominee-2028"},
    {"key": "pres_winner_2028", "category": "elections_2028",
     "slug_or_query": "presidential-election-winner-2028"},
    # --- Geopolitics (slugs pinned; search fallback only if a slug 404s) ---
    {"key": "china_taiwan_invasion", "category": "geopolitics",
     "slug_or_query": "will-china-invade-taiwan-before-2027"},
    {"key": "china_taiwan_blockade", "category": "geopolitics",
     "slug_or_query": "will-china-blockade-taiwan-by-in-2026"},
    {"key": "us_china_military_clash", "category": "geopolitics",
     "slug_or_query": "us-x-china-military-clash-before-2027"},
    {"key": "russia_ukraine_ceasefire", "category": "geopolitics",
     "slug_or_query": "russia-x-ukraine-ceasefire-agreement-by"},
    {"key": "iran_nuclear_deal", "category": "geopolitics",
     "slug_or_query": "us-iran-final-nuclear-deal-by-20260621201254412"},
    {"key": "hormuz_traffic_normal", "category": "geopolitics",
     "slug_or_query": "strait-of-hormuz-traffic-returns-to-normal-by-december-31"},
    {"key": "bab_el_mandeb_closed", "category": "geopolitics",
     "slug_or_query": "bab-el-mandeb-strait-effectively-closed-by"},
    {"key": "venezuela_leader_2026", "category": "geopolitics",
     "slug_or_query": "venezuela-leader-end-of-2026"},
    {"key": "us_strike_cuba", "category": "geopolitics",
     "slug_or_query": "us-strike-on-cuba-by"},
    {"key": "xi_out", "category": "geopolitics",
     "slug_or_query": "xi-jinping-out-before-2027"},
    {"key": "putin_out", "category": "geopolitics",
     "slug_or_query": "putin-out-before-2027"},
    # --- Macro & market tails ---
    {"key": "us_inflation_oct_2026", "category": "economy",
     "slug_or_query": "october-inflation-us-annual"},
    {"key": "us_default_2027", "category": "fiscal",
     "slug_or_query": "us-defaults-on-debt-by-2027"},
    {"key": "fed_rate_end_2027", "category": "fed",
     "slug_or_query": "what-will-the-fed-rate-be-at-the-end-of-2027"},
    {"key": "largest_company_2026", "category": "markets",
     "slug_or_query": "largest-company-end-of-december-2026"},
    {"key": "ai_bubble_burst", "category": "markets",
     "slug_or_query": "ai-bubble-burst-by"},
    {"key": "largest_ipo_2026", "category": "markets",
     "slug_or_query": "largest-ipo-by-market-cap-in-2026-287"},
    {"key": "anthropic_ipo", "category": "markets",
     "slug_or_query": "anthropic-ipo-by"},
    # --- Foreign politics ---
    {"key": "france_pres_2027", "category": "foreign_elections",
     "slug_or_query": "next-french-presidential-election"},
    {"key": "leader_out_2026", "category": "foreign_elections",
     "slug_or_query": "next-leader-out-of-power-before-2027-no-starmer-or-petro-"
                      "20260630194619406"},
    {"key": "japan_pm_out", "category": "foreign_elections",
     "slug_or_query": "sanae-takaichi-out-as-prime-minister-of-japan-in-2026"},
    {"key": "modi_out", "category": "foreign_elections",
     "slug_or_query": "modi-out-before-2027"},
    {"key": "taiwan_local_2026", "category": "foreign_elections",
     "slug_or_query": "2026-taiwanese-local-elections-party-winner"},
    # --- Rates / macro (high-volume) ---
    {"key": "fed_cuts_2026", "category": "fed",
     "slug_or_query": "how-many-fed-rate-cuts-in-2026"},
    {"key": "fed_emergency_cut", "category": "fed",
     "slug_or_query": "fed-emergency-rate-cut-before-2027"},
    {"key": "us10y_high_2026", "category": "rates",
     "slug_or_query": "how-high-will-10-year-treasury-yield-go-before-2027"},
    {"key": "us5y_low_2026", "category": "rates",
     "slug_or_query": "how-low-will-5-year-treasury-yield-get-before-2027"},
    {"key": "wti_nov_2026", "category": "energy",
     "slug_or_query": "what-price-will-wti-hit-in-november-2026"},
    {"key": "china_gdp_2026", "category": "economy",
     "slug_or_query": "china-annual-gdp-growth-2026"},
    {"key": "ez_inflation_2026", "category": "economy",
     "slug_or_query": "eurozone-2026-annual-inflation"},
    # --- Markets / crypto / IPO wave ---
    {"key": "btc_ath_by", "category": "markets",
     "slug_or_query": "bitcoin-all-time-high-by"},
    {"key": "eth_price_2026", "category": "markets",
     "slug_or_query": "what-price-will-ethereum-hit-before-2027"},
    {"key": "btc_gold_spx_2026", "category": "markets",
     "slug_or_query": "bitcoin-vs-gold-vs-sp-500-in-2026"},
    {"key": "openai_ipo", "category": "markets",
     "slug_or_query": "openai-ipo-by"},
    {"key": "ipos_2026", "category": "markets",
     "slug_or_query": "ipos-before-2027"},
    {"key": "trade_deals_2026", "category": "trade",
     "slug_or_query":
         "which-countries-will-trump-make-new-trade-deals-with-before-2027-921"},
    {"key": "bills_law_2026", "category": "domestic",
     "slug_or_query": "which-bills-will-become-law-in-2026"},
    {"key": "trump_meetings_2026", "category": "geopolitics",
     "slug_or_query": "who-will-trump-meet-with-in-2026"},
    # --- Geopolitical tails (high-volume) ---
    {"key": "china_taiwan_invasion_2027", "category": "geopolitics",
     "slug_or_query": "will-china-invade-taiwan-by-december-31-2027"},
    {"key": "china_taiwan_clash", "category": "geopolitics",
     "slug_or_query": "china-x-taiwan-military-clash-before-2027"},
    {"key": "china_japan_clash", "category": "geopolitics",
     "slug_or_query": "china-x-japan-military-clash-before-2027"},
    {"key": "greenland_acquire", "category": "geopolitics",
     "slug_or_query": "will-trump-acquire-greenland-before-2027"},
    {"key": "iran_regime_fall_2026", "category": "geopolitics",
     "slug_or_query": "will-the-iranian-regime-fall-by-the-end-of-2026"},
    {"key": "israel_strike_countries_2026", "category": "geopolitics",
     "slug_or_query": "how-many-different-countries-will-israel-strike-in-2026"},
    {"key": "ukraine_nato", "category": "geopolitics",
     "slug_or_query": "ukraine-joins-nato-before-2027"},
    {"key": "us_russia_nuclear_deal", "category": "geopolitics",
     "slug_or_query": "us-x-russia-nuclear-deal-by-december-31"},
    {"key": "india_pakistan_strike", "category": "geopolitics",
     "slug_or_query": "india-strike-on-pakistan-by"},
    {"key": "nk_invade_sk", "category": "geopolitics",
     "slug_or_query": "will-north-korea-invade-south-korea-before-2027"},
    {"key": "kim_out", "category": "geopolitics",
     "slug_or_query": "kim-jong-un-out-as-supreme-leader-of-north-korea-before-2027"},
]

# Hand-maintained key events (Date, Event, Category, Notes). Extends through
# the 2028 US presidential cycle and includes major foreign political and
# central-bank dates. "approx"/"TBD" = not yet officially scheduled; verify.
POLITICAL_EVENTS = [
    # ---- 2026 ----
    ("2026-11-03", "US midterm elections", "elections", "House + 35 Senate"),
    ("2026-11-10", "US-China trade truce 1-yr expiry (Busan deal)", "trade",
     "approx; renewal or tariff snap-back"),
    ("2026-11-12", "CPI release (Oct)", "data", "approx; verify bls.gov"),
    ("2026-11-28", "Taiwan local (9-in-1) elections", "foreign", "KMT vs DPP"),
    ("2026-11-30", "OPEC+ ministerial meeting", "energy", "approx"),
    ("2026-12-09", "FOMC decision", "fed", "Dec 8-9 meeting + SEP"),
    ("2026-12-10", "CPI release (Nov)", "data", "approx; verify bls.gov"),
    ("2026-12-10", "ECB decision", "cb", "approx"),
    ("2026-12-14", "G20 summit (Miami, US presidency)", "summit", "Dec 14-15"),
    ("2026-12-17", "BoE decision", "cb", "approx"),
    ("2026-12-18", "BoJ decision", "cb", "Dec 17-18"),
    ("2026-12-15", "China Central Economic Work Conference", "foreign",
     "approx; sets 2027 growth target tone"),
    # ---- 2027 ----
    ("2027-01-01", "Brazil presidential inauguration", "foreign", ""),
    ("2027-01-03", "120th Congress convenes", "congress", "Speaker vote"),
    ("2027-01-13", "CPI release (Dec)", "data", "approx; verify bls.gov"),
    ("2027-01-18", "World Economic Forum (Davos)", "summit", "approx"),
    ("2027-01-27", "FOMC decision", "fed", "Jan 26-27 meeting"),
    ("2027-02-01", "India Union Budget", "foreign", ""),
    ("2027-02-01", "State of the Union", "domestic", "date TBD"),
    ("2027-02-15", "India Uttar Pradesh state election", "foreign",
     "approx Feb-Mar; biggest state, Modi bellwether"),
    ("2027-03-05", "China NPC annual session", "foreign",
     "growth target, fiscal stance, defense budget"),
    ("2027-03-17", "FOMC decision", "fed", "Mar 16-17 meeting + SEP"),
    ("2027-04-11", "France presidential election R1", "foreign",
     "approx; R2 ~Apr 25; Le Pen/Bardella vs field"),
    ("2027-04-25", "France presidential election R2", "foreign", "approx"),
    ("2027-04-28", "FOMC decision", "fed", "Apr 27-28 meeting"),
    ("2027-05-06", "UK local elections", "foreign", "Reform UK test"),
    ("2027-06-06", "Mexico midterm elections", "foreign", "Sheinbaum test"),
    ("2027-06-13", "France legislative elections", "foreign", "approx"),
    ("2027-06-14", "G7 summit (Evian, France)", "summit", "Jun 14-16"),
    ("2027-06-16", "FOMC decision", "fed", "Jun 15-16 meeting + SEP"),
    ("2027-06-30", "US Supreme Court term ends", "domestic", "major rulings"),
    ("2027-07-01", "USMCA annual review", "trade",
     "if 16-yr extension not agreed in 2026"),
    ("2027-07-28", "FOMC decision", "fed", "approx"),
    ("2027-08-01", "PLA centenary", "foreign",
     "US-intel Taiwan readiness date"),
    ("2027-08-02", "EU AI Act high-risk obligations apply", "foreign", ""),
    ("2027-08-26", "Jackson Hole symposium", "fed", "approx"),
    ("2027-09-22", "FOMC decision", "fed", "approx"),
    ("2027-09-30", "FY2027 funding deadline", "fiscal", "shutdown risk"),
    ("2027-09-30", "Japan LDP presidential election", "foreign",
     "approx Sep; PM Takaichi term"),
    ("2027-10-15", "China 21st Party Congress", "foreign",
     "approx Oct-Nov; Xi 4th term, Politburo reshuffle"),
    ("2027-10-31", "ECB: Lagarde term ends", "cb", "successor decision"),
    ("2027-11-02", "US off-year elections (KY/LA/MS governors)", "elections",
     ""),
    ("2027-11-03", "FOMC decision", "fed", "approx"),
    ("2027-12-15", "FOMC decision", "fed", "approx"),
    ("2027-12-31", "US debt-ceiling X-date window opens", "fiscal",
     "approx; $5T raise (Jul 2025) projected to bind 2027-28"),
    # ---- 2028 ----
    ("2028-01-13", "Taiwan presidential election", "foreign",
     "approx Jan; cross-strait risk peak"),
    ("2028-01-31", "Powell Fed Board term ends", "fed", ""),
    ("2028-02-01", "First US presidential caucuses/primaries", "elections",
     "approx; IA/NH/SC/NV order TBD"),
    ("2028-03-07", "Super Tuesday", "elections", "approx"),
    ("2028-04-08", "BoJ: Ueda term ends", "cb", ""),
    ("2028-07-17", "Republican National Convention", "elections",
     "approx mid-Jul"),
    ("2028-08-14", "Democratic National Convention", "elections",
     "approx mid-Aug"),
    ("2028-09-30", "FY2028 funding deadline", "fiscal", "pre-election"),
    ("2028-10-31", "Japan House of Representatives term ends", "foreign",
     "general election by this date"),
    ("2028-11-07", "US presidential election", "elections",
     "also House + 33 Senate + 11 governors"),
    ("2029-01-20", "US presidential inauguration", "elections", ""),
]
# yapf: enable

# Cache Directory
CACHE_DIR = ".cache"

# Price and portfolio data
CACHE_EXPIRY_PRICES = 3600  # 1 hour
CACHE_YAHOO_PORTFOLIO_HOURS = 1  # 1 hour

# News RSS feeds
CACHE_EXPIRY_NEWS = 14400  # 4 hours
CACHE_EXPIRY_AV_NEWS = 86400 * 14  # 14 days

# Daily/weekly datasets (Yahoo, AIS, SEC, FRED)
CACHE_EXPIRY_FUNDAMENTALS = 86400  # 24 hours
CACHE_EXPIRY_SHIPPING = 86400  # 24 hours
CACHE_EXPIRY_INSIDER = 86400 * 2  # 48 hours
CACHE_EXPIRY_MACRO = 86400 * 2  # 48 hours
CACHE_EXPIRY_POLITICAL = 3600 * 6  # 6 hours (prediction markets move fast)

# Slow-changing corporate filings (30 days to avoid AlphaVantage rate limits)
CACHE_EXPIRY_AV_OVERVIEW = 2592000  # 30 days
CACHE_EXPIRY_AV_FINANCIALS = 2592000  # 30 days

# Long-term archives
CACHE_EXPIRY_HISTORICAL_NEWS = 31536000 * 4  # 4 years

# Max age before triggering pipeline failures
MAX_PORTFOLIO_AGE_DAYS = 3
