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
    # AI & Tech
    "AI", "Artificial Intelligence", "Compute Power", "Data Center", "GPU",
    "Generative AI", "AI Regulation", "Technology", "Big Tech", "Sovereign AI",
    "Hyperscalers",

    # Energy, Grid & Commodities
    "Energy", "Oil", "OPEC", "Nuclear Energy", "Uranium", "Natural Gas",
    "Power Grid", "Renewable Energy", "Commodities", "Electricity Demand",
    "Small Modular Reactors", "Copper Demand",

    # Supply Chain, Chips & Shipping
    "Supply Chain", "Shipping", "Logistics", "Freight", "Container Rates",
    "Semiconductor Fabs", "Chip Shortage", "EDA Software", "Advanced Packaging",

    # Macro, Finance & Geopolitics
    "Inflation", "Federal Reserve", "Interest Rates", "Recession", "GDP",
    "Geopolitics", "War", "China", "Taiwan", "OPEC+", "Sanctions",
    "Tariffs", "Trade War", "US Economy", "Global Markets", "Bitcoin ETF",
    "GLP-1 Weight Loss"
]

# Sectors & Tickers
SECTORS = {
    "Macro Indices": [  # Major Indices and Volatility measures
        "^GSPC", "^IXIC", "GC=F", "CL=F", "^TNX", "^VIX", "^DJI", "^RUT", "SPY", "VIXY"
    ],
    "Chips & Semi": [
        "NVDA", "AMD", "INTC", "TSM", "ASML", "MU", "MPWR", "AVGO", "SMH",
        "LRCX", "AMAT", "ENTG", "WDC", "NVT", "COHR", "ARM", "QCOM", "TXN",
        "ON", "ADI", "KLAC", "CDNS", "SNPS", "APH", "SOXQ"
    ],
    "AI & Big Tech": [
        "GOOG", "PLTR", "MSFT", "META", "AAPL", "ORCL", "IBM", "AMZN", "SNOW",
        "CRM", "ADBE", "CSCO", "NOW", "RDDT", "IONQ", "PANW", "CRWD", "NET",
        "DELL", "HPE", "SMCI", "TTD", "VGT"
    ],
    "Auto & Robot": [
        "TSLA", "TM", "F", "ACHR", "JOBY", "RIVN", "UBER"
    ],
    "Energy & Power Grid": [
        "XOM", "CVX", "CCJ", "NEE", "XLE", "FSLR", "SHEL", "TTE", "BP", "COP",
        "EOG", "SLB", "HAL", "URA", "D", "ES", "VST", "CEG", "CNP", "SO",
        "GE", "GEV", "ETN", "PWR", "LIN", "WM", "VDE", "FENY", "VPU", "FUTY", "NLR"
    ],
    "Aerospace & Defense":
    ["LMT", "RTX", "ITA", "NOC", "GD", "BA", "TDG", "HII", "AXON", "LDOS"],
    "Crypto & Minerals": [
        "COIN", "MARA", "RIOT", "MSTR", "CLSK", "NEM", "GOLD", "PAAS", "FCX",
        "SCCO", "VALE", "RIO", "BHP", "BMNR", "BITF", "HUT", "CAT", "IBIT", "GLDM"
    ],
    "Data Center & Infra": [
        "EQIX", "DLR", "AMT", "CCI", "VRT", "ANET", "IRM", "BX", "SCHH"
    ],
    "Shipping & Logistics": [
        "ZIM", "FDX", "UPS", "MATX", "GSL", "DAC", "SBLK", "BDRY", "AMKBY",
        "PAVE", "CNI", "CP"
    ],
    "Bio & MedTech": [
        "NVO", "LLY", "ISRG", "VRTX", "REGN", "SYK", "VHT"
    ],
    "Consumer & Finance": [
        "CMG", "WMT", "COST", "DE", "BLK", "V", "MA", "JPM", "VDC"
    ],
    "Broad Market & Intl ETFs": [
        "VOO", "VTI", "VTSAX", "SCHG", "VUG", "VIGAX", "SCHV", "VTV",
        "SCHD", "VEA", "VWO"
    ],
    "Fixed Income & Preferred": [
        "PFFD", "PFXF", "FAGOX", "FASPX"
    ]
}
# yapf: enable

# Cache
CACHE_DIR = ".cache"
CACHE_EXPIRY_PRICES = 3600  # 1 hour
CACHE_EXPIRY_NEWS = 14400  # 4 hours
CACHE_EXPIRY_FUNDAMENTALS = 86400  # 24 hours
CACHE_EXPIRY_INSIDER = 43200  # 12 hours
CACHE_EXPIRY_MACRO = 86400 * 2  # 48 hours
