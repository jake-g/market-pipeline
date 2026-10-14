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
    "Multimodal AI", "Reasoning Models", "High Bandwidth Memory",
    "HBM Shortage", "Silicon Photonics", "Optical Interconnects",
    "Liquid Cooling", "AI Data Licensing", "AI CapEx ROI",
    "Anthropic IPO", "OpenAI IPO", "AI IPO", "Databricks IPO",
    "Robotaxi", "Humanoid Robots",

    # Energy, Grid & Commodities
    "Energy", "Oil", "OPEC", "Nuclear Energy", "Uranium", "Natural Gas",
    "Power Grid", "Renewable Energy", "Commodities", "Electricity Demand",
    "AI Energy Demand", "Data Center Power", "Small Modular Reactors",
    "Nuclear PPAs", "Gas Turbines", "Grid Transformers", "Copper Demand",
    "Battery Storage", "Grid Modernization", "Power Grid Constraints",
    "Geothermal Energy", "Desalination", "Water Security", "Lithium",
    "Rare Earths",

    # Supply Chain, Chips, Space & Shipping
    "Supply Chain", "Shipping", "Logistics", "Freight", "Container Rates",
    "Semiconductor Fabs", "Chip Shortage", "Memory Shortage", "EDA Software",
    "Advanced Packaging", "CoWoS Packaging", "Foundry Business",
    "Glass Substrates", "Chip Export Controls", "Chinese Semiconductors",
    "Nearshoring", "SpaceX IPO", "Commercial Space", "Satellite Direct-to-Cell",

    # Countries & Regions
    "Iran", "Russia", "Ukraine", "Venezuela", "Pakistan", "China", "Taiwan",
    "United States", "India", "Middle East", "Mexico", "Israel", "Canada",

    # Macro, Bond Yields, Elections & Geopolitics
    "Inflation", "Inflation Expectations", "Stagflation", "Federal Reserve",
    "Interest Rates", "Treasury Yields", "Bond Vigilantes", "Credit Spreads",
    "Private Credit", "Recession", "GDP", "US Economy", "US Debt",
    "US Midterm Elections", "Geopolitics", "War", "OPEC+", "Sanctions",
    "Tariffs", "Trade War", "Global Markets", "Bitcoin ETF",
    "Crypto Regulation", "Tokenization", "GLP-1 Weight Loss",
    "De-dollarization", "Commercial Real Estate", "Drones",
    "Autonomous Drones", "Defense Tech", "Hormuz", "SaaS Valuation Reset"
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
        "FN", "DRAM", "QTUM"
    ],
    "AI & Big Tech": [
        "GOOG", "PLTR", "MSFT", "META", "AAPL", "ORCL", "IBM", "AMZN", "SNOW",
        "CRM", "ADBE", "CSCO", "NOW", "RDDT", "IONQ", "PANW", "CRWD", "NET",
        "DELL", "HPE", "SMCI", "TTD", "VGT", "APP", "MNDY", "DDOG", "FTNT",
        "ZS", "NBIS", "CRWV", "MDB"
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
