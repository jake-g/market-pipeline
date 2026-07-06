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
NEWS_TOPICS =[
    # AI & Tech
    "AI", "Compute Power", "Data Center",
    "GPU", "Generative AI", "AI Regulation", "Technology", "Big Tech", "Sovereign AI",
    "Hyperscalers", "Circular Deals", "AI Agents", "Custom Silicon", "Cybersecurity",
    "Quantum Computing", "Physical AI", "Inference Infrastructure", "Edge AI",
    "Multimodal AI",

    # Energy, Grid & Commodities
    "Energy", "Oil", "OPEC", "Nuclear Energy", "Uranium", "Natural Gas",
    "Power Grid", "Renewable Energy", "Commodities", "Electricity Demand",
    "AI Energy Demand", "Small Modular Reactors", "Copper Demand",
    "Battery Storage", "Grid Modernization", "Desalination", "Water Security",
    "Lithium", "Rare Earths", "Power Grid Constraints",

    # Supply Chain, Chips & Shipping
    "Supply Chain", "Shipping", "Logistics", "Freight", "Container Rates",
    "Semiconductor Fabs", "Chip Shortage", "Memory Shortage", "EDA Software",
    "Advanced Packaging", "Taiwan-China Chip Geopolitics", "Foundry Business",
    "Nearshoring", "Friendshoring",

    # Countries & Regions
    "Iran", "Russia", "Ukraine", "Venezuela", "Pakistan", "China", "Taiwan",
    "United States", "India", "Middle East", "Mexico", "Israel", "Canada",

    # Macro, Finance & Geopolitics
    "Inflation", "Federal Reserve", "Interest Rates", "Recession", "GDP",
    "Geopolitics", "War", "OPEC+", "Sanctions", "Tariffs", "Trade War", "US Economy",
    "Global Markets", "Bitcoin ETF", "GLP-1 Weight Loss", "De-dollarization",
    "Commercial Real Estate", "US Debt", "Crypto Regulation", "Tokenization",
    "Drones",  "Attritable Mass", "Hormuz",
    "Geopolitical De-Risking", "Corporate Austerity", "SaaS Valuation Reset"
]

# Sectors & Tickers
SECTORS = {
    "Macro Indices": [ #  Major Indices and Volatility measures
        "^GSPC", "^IXIC", "GC=F", "CL=F", "^TNX", "^VIX", "^DJI", "^RUT",
        "SPY", "VIXY", "QQQ", "DIA", "IWM", "TLT", "AIPO"
    ],
    "Chips & Semi": [
        "NVDA", "AMD", "INTC", "TSM", "ASML", "MU", "MPWR", "AVGO", "SMH",
        "LRCX", "AMAT", "ENTG", "WDC", "NVT", "COHR", "ARM", "QCOM", "TXN",
        "ON", "ADI", "KLAC", "CDNS", "SNPS", "APH", "SOXQ", "MRVL", "SWKS",
        "STM", "TTDKY", "TTMI", "SOXX", "XSD", "SMHX", "MUZ"
    ],
    "AI & Big Tech": [
        "GOOG", "PLTR", "MSFT", "META", "AAPL", "ORCL", "IBM", "AMZN", "SNOW",
        "CRM", "ADBE", "CSCO", "NOW", "RDDT", "IONQ", "PANW", "CRWD", "NET",
        "DELL", "HPE", "SMCI", "TTD", "VGT", "APP", "MNDY", "DDOG", "FTNT", "ZS",
        "NBIS", "CRWV"
    ],
    "Auto & Robot": [
        "TSLA", "TM", "F", "ACHR", "JOBY", "RIVN", "UBER", "SYM", "PATH",
        "ASTS", "LUNR"
    ],
    "Energy & Power Grid": [
        "XOM", "CVX", "CCJ", "NEE", "XLE", "FSLR", "SHEL", "TTE", "BP", "COP",
        "EOG", "SLB", "HAL", "URA", "D", "ES", "VST", "CEG", "CNP", "SO",
        "GE", "GEV", "ETN", "PWR", "LIN", "WM", "VDE", "FENY", "VPU", "FUTY",
        "NLR", "ENPH", "FLNC", "KULR", "NXT"
    ],
    "Aerospace & Defense": [
        "LMT", "RTX", "ITA", "NOC", "GD", "BA", "TDG", "HII", "AXON", "LDOS", "KTOS", "AVAV", "ESLT", "VSAT", "RKLB", "SPCX"
    ],
    "Crypto & Minerals": [
        "BTC-USD", "ETH-USD", "COIN", "MARA", "RIOT", "MSTR", "CLSK", "NEM",
        "GOLD", "PAAS", "FCX", "SCCO", "VALE", "RIO", "BHP", "BMNR",
        "HUT", "CAT", "IBIT", "GLDM", "SOL-USD", "ALB", "SQM", "CF", "MEOH"
    ],
    "Data Center & Infra": [
        "EQIX", "DLR", "AMT", "CCI", "VRT", "ANET", "IRM", "BX", "SCHH",
        "MOD", "CORZ", "IREN", "WULF", "GLW"
    ],
    "Shipping & Logistics": [
        "ZIM", "FDX", "UPS", "MATX", "GSL", "DAC", "SBLK", "BDRY", "AMKBY",
        "PAVE", "CNI", "CP", "EXPD", "CHRW", "STNG", "FRO"
    ],
    "Bio & MedTech": [
        "NVO", "LLY", "ISRG", "VRTX", "REGN", "SYK", "VHT", "AMGN", "ABBV",
        "PFE", "MRK", "JNJ", "BSX", "MDT", "TMO", "MRNA", "PPH", "OZEM"
    ],
    "Water & Desalination": [
        "AWK", "XYL", "CWCO", "AWX", "DD",
    ],
    "Consumer & Finance": [
        "CMG", "WMT", "COST", "DE", "BLK", "V", "MA", "JPM", "VDC", "HD",
        "LOW", "PG", "KO", "GS", "MS", "BAC", "O", "PLD", "DIS"
    ],
    "Broad Market & Intl ETFs": [
        "VOO", "VTI", "VTSAX", "SCHG", "VUG", "VIGAX", "SCHV", "VTV",
        "SCHD", "VEA", "VWO", "EFA", "EEM", "URTH", "CIBR", "VIG", "VIS", "VYM",
        "VAW", "VXUS", "EWY"
    ],
    "Mutual Funds": [
        "VMFXX", "VFTAX", "VIGIX", "VIIIX", "VEMRX", "VTIFX"
    ],
    "Fixed Income & Preferred": [
        "PFFD", "PFXF", "FAGOX", "FASPX"
    ]
}
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

# Slow-changing corporate filings (30 days to avoid AlphaVantage rate limits)
CACHE_EXPIRY_AV_OVERVIEW = 2592000  # 30 days
CACHE_EXPIRY_AV_FINANCIALS = 2592000  # 30 days

# Long-term archives
CACHE_EXPIRY_HISTORICAL_NEWS = 31536000 * 4  # 4 years

# Max age before triggering pipeline failures
MAX_PORTFOLIO_AGE_DAYS = 3
