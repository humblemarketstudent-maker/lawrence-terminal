"""Ticker normalization, peer maps, and the local symbol catalog."""

from __future__ import annotations

import re

DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "GOOG", "NVDA", "AMZN", "SPCX", "2222.SR", "2330.TW", "AVGO", "META", "TSLA", "BRK-B",
    "LLY", "ANT", "WMT", "005930.KS", "JPM", "V", "AMD", "MU", "XOM", "JNJ", "000660.KS", "MA", "ABBV",
    "ASML.AS", "601939.SS", "COST", "KO", "CVX", "601288.SS", "PG", "0700.HK", "RO.SW", "CSCO", "601988.SS",
    "1398.HK", "688825.SS", "PLTR", "HD", "MRK", "BAC", "GE", "ORCL", "UNH", "NOVN.SW", "PM", "PANW", "HSBA.L",
    "AZN.L", "INTC", "600519.SS", "SHEL.L", "NESN.SW", "MS", "RTX", "OR.PA", "RY.TO", "TMO", "7203.T", "TXN",
    "AMAT", "WFC", "AMGN", "0857.HK", "CRWD", "CAT", "NFLX", "SAP.DE", "LIN", "LRCX", "GS", "0941.HK", "8306.T",
    "SIE.DE", "IBM", "ANET", "GILD", "MC.PA", "9988.HK", "AXP", "DIS", "RELIANCE.NS", "ITX.MC", "MCD", "VZ",
    "PEP", "TTE.PA", "CBA.AX", "ALV.DE", "GEV", "TD.TO", "C", "ABT", "BHP.AX", "DELL", "WELL", "TMUS", "NEE",
    "APH", "NOVO-B.CO", "UNP", "3968.HK", "BLK", "2454.TW", "ADI", "601088.SS", "IBE.MC", "KLAC", "AIR.PA",
    "DE", "SAN.MC", "ARM", "COP", "QCOM", "SHOP.TO", "9983.T", "6758.T", "ABI.BR", "300750.SZ", "PFE", "SCHW",
    "DHR", "TJX", "T", "CRM", "601318.SS", "6098.T", "601628.SS", "SU.PA", "BHARTIARTL.NS", "D05.SI", "CB",
    "HDFCBANK.NS", "RMS.PA", "ABBN.SW", "8316.T", "DTE.DE", "ISRG", "ULVR.L", "RR.L", "PGR", "UBSG.SW",
    "6501.T", "SAF.PA", "AI.PA", "BBVA.MC", "0883.HK", "ACN", "LMT", "VRTX", "UBER", "UCG.MI", "MDT", "SPGI",
    "ICICIBANK.NS", "MO", "BATS.L", "LOW", "BA", "MCK", "INVE-B.ST", "IBKR", "ETN", "RIO.L", "BMY", "PDD",
    "ADP", "SPOT", "8035.T", "CFR.SW", "SYK", "601328.SS", "SBUX", "PLD", "SBIN.NS", "APP", "600900.SS", "SCCO",
    "ZURN.SW", "ISP.MI", "SAN.PA", "8058.T", "BP.L", "8411.T", "6857.T", "CME", "MRVL", "PH", "BMO.TO",
    "601138.SS", "9984.T", "SO", "BNP.PA", "BKNG", "ENR.F", "COF", "000333.SZ", "6861.T", "600028.SS",
    "002594.SZ", "STX", "MAR", "601658.SS", "CVS", "ENEL.MI", "BNS.TO", "ENB.TO", "8766.T", "DUK", "CS.PA",
    "ABNB", "MPC", "HCA", "NET", "NEM", "MRSH", "PETR4.SA", "WDC", "1120.SR", "8001.T", "GSK.L", "1299.HK",
    "EQIX", "WM", "REGN", "601899.SS", "BNY", "ICE", "PSX", "CM.TO", "VLO", "EQNR.OL", "TCS.NS", "GD", "MMM",
    "FTNT", "NOW", "O39.SI", "CSX", "CNQ.TO", "UPS", "SNDK", "SNOW", "1810.HK", "2317.TW", "CMCSA", "EL.PA",
    "BX", "CTAS", "USB", "CABK.MC", "WAT", "MSI", "688256.SS", "MNST", "AMT", "ELV", "9432.T", "ADBE",
    "INGA.AS", "PNC", "TT", "PWR", "BN.TO", "MDLZ", "CEG", "HWM", "EMR", "ECL", "CDI.PA", "SHW", "GLW", "NG.L",
    "WBC.AX", "TRV", "MCO", "WMB", "MUV2.DE", "601998.SS", "8031.T", "RCL", "HLT", "GMEXICOB.MX", "KKR", "MRNA",
    "CL", "BAM.TO", "JCI", "CP.TO", "ITW", "WBD", "EPD", "CDNS", "EOG", "BAJFINANCE.NS", "AEM.TO", "ANZ.AX",
    "ATCO-B.ST", "SNPS", "NOC", "ENI.MI", "RSG", "TGT", "AMXB.MX", "ORLY", "ITUB4.SA", "NAB.AX", "2308.TW",
    "4519.T", "9434.T", "SU.TO", "285A.T", "CNR.TO", "SPG", "INTU", "AJG", "G.MI", "CI", "FDX", "LLOY.L", "AON",
    "VIC.VN", "CVNA", "300308.SZ", "2359.HK", "4502.T", "MRK.DE", "RACE.MI", "NSC", "DHL.DE", "BA.L", "PRX.AS",
    "BARC.L", "GLEN.L", "MELI", "ROST", "AEP", "SLB", "ENGI.PA", "REL.L", "MFC.TO", "KMI", "HON", "DG.PA",
    "DASH", "GM", "7182.T", "9433.T", "APD", "ALL", "402340.KS", "FCX", "APO", "KMB", "9633.HK", "IFX.DE",
    "TRP.TO", "COR", "ET", "7974.T", "VRT", "601166.SS", "9999.HK", "DELTA.BK", "CSL.AX", "GWW", "CAH",
    "VOLV-A.ST", "LT.NS", "3711.TW", "DB1.DE", "AFL", "DLR", "2388.HK", "TDG", "BSX", "PSA", "LSEG.L",
    "NDA-FI.HE", "EMIRATESNBD.AE", "URI", "LNG", "MET", "4063.T", "TRGP", "NWG.L", "002371.SZ", "DBK.DE",
    "NXPI", "600030.SS", "UCB.VI", "ARGX.BR", "2914.T", "CRH", "EW", "D", "1180.SR", "FAST", "BDX", "WES.AX",
    "BAYN.DE", "7011.T", "TEL", "L.TO", "NDAQ", "CPG.L", "DDOG", "MQG.AX", "MPLX", "GWO.TO", "6503.T",
    "1211.SR", "HOOD", "0388.HK", "MPWR", "KOTAKBANK.NS", "CMI", "O", "DGE.L", "IMO.TO", "TFC", "NU", "7010.SR",
    "2881.TW", "HPE", "STAN.L", "LONN.SW", "NUE", "OXY", "PCAR", "600000.SS", "6981.T", "EOAN.DE", "IDXX",
    "OKE", "SHL.DE", "0981.HK", "NA.TO", "SREN.SW", "DAL", "AZO", "ATD.TO", "002475.SZ", "HINDUNILVR.NS",
    "0728.HK", "CTVA", "GRMN", "ABX.TO", "Z74.SI", "AME", "ADSK", "CCEP.L", "373220.KS", "XEL", "3690.HK",
    "ACA.PA", "GALD.SW", "0019.HK", "EBAY", "HEIA.AS", "HO.PA", "^302000-USD-STRD", "^899903-USD-STRD",
    "^899800-USD-STRD", "^SPASIA50", "^DJAT", "^N225", "^AXJO", "^AORD", "^AXKO", "^NZ50", "000001.SS",
    "399001.SZ", "000300.SS", "399006.SZ", "000688.SS", "000905.SS", "^HSCE", "^HSI", "HSTECH.HK", "^KS11",
    "^KQ11", "^KS200", "^TWII", "^STI", "^JKSE", "^SET.BK", "^KLSE", "PSEI.PS", "^VNINDEX.VN", "ASEAN40.FGI",
    "^NSEI", "^BSESN", "^CRSLDX"
]

WEI_SYMBOLS = [
    ("^GSPC", "S&P 500", "equity"),
    ("^IXIC", "Nasdaq Composite", "equity"),
    ("^DJI", "Dow Jones", "equity"),
    ("^HSI", "Hang Seng", "equity"),
    ("^N225", "Nikkei 225", "equity"),
    ("^FTSE", "FTSE 100", "equity"),
    ("^GDAXI", "DAX", "equity"),
    ("DX-Y.NYB", "US Dollar Index", "fx"),
    ("CL=F", "WTI Crude", "commodity"),
    ("GC=F", "Gold", "commodity"),
    ("BTC-USD", "Bitcoin", "crypto"),
]

RATE_SYMBOLS = {"^TNX", "^FVX", "^TYX", "^IRX"}

PEER_MAP: dict[str, list[str]] = {
    "AAPL": ["MSFT", "GOOGL", "AMZN", "META", "AVGO"],
    "MSFT": ["AAPL", "GOOGL", "AMZN", "ORCL", "CRM"],
    "NVDA": ["AMD", "AVGO", "TSM", "QCOM", "ARM"],
    "GOOGL": ["META", "AMZN", "MSFT", "AAPL", "CRM"],
    "AMZN": ["MSFT", "GOOGL", "META", "BABA", "AAPL"],
    "META": ["GOOGL", "AMZN", "SNAP", "AAPL", "MSFT"],
    "AMD": ["NVDA", "AVGO", "INTC", "QCOM", "TSM"],
    "AVGO": ["NVDA", "AMD", "TSM", "QCOM", "AMAT"],
    "0700.HK": ["9988.HK", "BABA", "3690.HK", "1810.HK", "JD"],
    "9988.HK": ["0700.HK", "BABA", "JD", "3690.HK", "9618.HK"],
    "SPY": ["QQQ", "DIA", "IWM", "EFA", "VTI"],
    "QQQ": ["SPY", "QQQM", "XLK", "SMH", "IWM"],
}

CATALOG: list[dict[str, str]] = [
    {"symbol": "AAPL", "name": "Apple Inc.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "AMD", "name": "Advanced Micro Devices", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "AVGO", "name": "Broadcom Inc.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "TSM", "name": "Taiwan Semiconductor", "assetClass": "equity", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "ORCL", "name": "Oracle Corp.", "assetClass": "equity", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "CRM", "name": "Salesforce Inc.", "assetClass": "equity", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "assetClass": "equity", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "JPM", "name": "JPMorgan Chase", "assetClass": "equity", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "XOM", "name": "Exxon Mobil", "assetClass": "equity", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "BABA", "name": "Alibaba Group", "assetClass": "equity", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "0700.HK", "name": "Tencent Holdings", "assetClass": "equity", "exchange": "HKEX", "currency": "HKD"},
    {"symbol": "9988.HK", "name": "Alibaba Group HK", "assetClass": "equity", "exchange": "HKEX", "currency": "HKD"},
    {"symbol": "3690.HK", "name": "Meituan", "assetClass": "equity", "exchange": "HKEX", "currency": "HKD"},
    {"symbol": "1810.HK", "name": "Xiaomi", "assetClass": "equity", "exchange": "HKEX", "currency": "HKD"},
    {"symbol": "ASML.AS", "name": "ASML Holding", "assetClass": "equity", "exchange": "EURONEXT", "currency": "EUR"},
    {"symbol": "SAP.DE", "name": "SAP SE", "assetClass": "equity", "exchange": "XETRA", "currency": "EUR"},
    {"symbol": "MC.PA", "name": "LVMH", "assetClass": "equity", "exchange": "EURONEXT", "currency": "EUR"},
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "assetClass": "etf", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "assetClass": "etf", "exchange": "NASDAQ", "currency": "USD"},
    {"symbol": "DIA", "name": "SPDR Dow Jones ETF", "assetClass": "etf", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "IWM", "name": "iShares Russell 2000", "assetClass": "etf", "exchange": "NYSE", "currency": "USD"},
    {"symbol": "^GSPC", "name": "S&P 500", "assetClass": "index", "exchange": "INDEX", "currency": "USD"},
    {"symbol": "^IXIC", "name": "Nasdaq Composite", "assetClass": "index", "exchange": "INDEX", "currency": "USD"},
    {"symbol": "^DJI", "name": "Dow Jones Industrial", "assetClass": "index", "exchange": "INDEX", "currency": "USD"},
    {"symbol": "^HSI", "name": "Hang Seng", "assetClass": "index", "exchange": "INDEX", "currency": "HKD"},
    {"symbol": "^N225", "name": "Nikkei 225", "assetClass": "index", "exchange": "INDEX", "currency": "JPY"},
    {"symbol": "^FTSE", "name": "FTSE 100", "assetClass": "index", "exchange": "INDEX", "currency": "GBP"},
    {"symbol": "^GDAXI", "name": "DAX", "assetClass": "index", "exchange": "INDEX", "currency": "EUR"},
    {"symbol": "^TNX", "name": "US 10Y Yield", "assetClass": "rate", "exchange": "INDEX", "currency": "USD"},
    {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "assetClass": "fx", "exchange": "INDEX", "currency": "USD"},
    {"symbol": "USDHKD=X", "name": "USD / HKD", "assetClass": "fx", "exchange": "FX", "currency": "HKD"},
    {"symbol": "EURUSD=X", "name": "EUR / USD", "assetClass": "fx", "exchange": "FX", "currency": "USD"},
    {"symbol": "GC=F", "name": "Gold", "assetClass": "commodity", "exchange": "COMEX", "currency": "USD"},
    {"symbol": "CL=F", "name": "WTI Crude", "assetClass": "commodity", "exchange": "NYMEX", "currency": "USD"},
    {"symbol": "BTC-USD", "name": "Bitcoin", "assetClass": "crypto", "exchange": "CRYPTO", "currency": "USD"},
]

_BY_SYMBOL = {row["symbol"]: row for row in CATALOG}

_EXCHANGE_SUFFIX = {
    "HK": ".HK",
    "LN": ".L",
    "NA": ".AS",
    "GR": ".DE",
    "GY": ".DE",
    "FP": ".PA",
    "JP": ".T",
    "US": "",
    "UW": "",
    "UN": "",
    "UA": "",
    "UQ": "",
}


def normalize_symbol(raw: str | None) -> str:
    if not raw:
        return ""
    text = raw.strip().upper()
    text = text.replace(" EQUITY", "").replace(" INDEX", "").replace(" CURNCY", "").replace(" COMDTY", "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    parts = text.split(" ")
    if len(parts) == 2 and parts[1] in _EXCHANGE_SUFFIX:
        base, exch = parts
        suffix = _EXCHANGE_SUFFIX[exch]
        if exch == "HK" and base.replace(".", "").isdigit():
            return base.split(".")[0].zfill(4) + ".HK"
        return base + suffix
    if re.fullmatch(r"\d{1,5}", text):
        return text.zfill(4) + ".HK"
    return text


def catalog_row(symbol: str) -> dict[str, str] | None:
    return _BY_SYMBOL.get(symbol)


def classify(symbol: str, quote_type: str | None = None) -> str:
    row = catalog_row(symbol)
    if row:
        return row["assetClass"]
    if symbol in RATE_SYMBOLS:
        return "rate"
    if symbol.startswith("^"):
        return "index"
    if symbol.endswith("-USD"):
        return "crypto"
    if symbol.endswith("=X") or symbol in {"DX-Y.NYB"}:
        return "fx"
    if symbol.endswith("=F"):
        return "commodity"
    if quote_type and quote_type.upper() in {"ETF", "MUTUALFUND"}:
        return "etf"
    return "equity"


def currency_for(symbol: str, hinted: str | None = None) -> str:
    if symbol in RATE_SYMBOLS:
        return "USD"
    row = catalog_row(symbol)
    if row:
        return row["currency"]
    if hinted and hinted not in {"", "None"}:
        return hinted
    if symbol.endswith(".HK"):
        return "HKD"
    if symbol.endswith(".T"):
        return "JPY"
    if symbol.endswith(".L"):
        return "GBP"
    if symbol.endswith((".DE", ".PA", ".AS")):
        return "EUR"
    return "USD"


def name_for(symbol: str, hinted: str | None = None) -> str:
    row = catalog_row(symbol)
    if row:
        return row["name"]
    if hinted and hinted not in {"", "None"}:
        return hinted
    return symbol


def exchange_for(symbol: str, hinted: str | None = None) -> str:
    if hinted and hinted not in {"", "None"}:
        return hinted
    row = catalog_row(symbol)
    return row["exchange"] if row else ""


def bloomberg_label(symbol: str) -> str:
    asset = classify(symbol)
    if symbol.endswith(".HK"):
        core = symbol[:-3].lstrip("0") or "0"
        return f"{core} HK"
    if symbol.endswith(".L"):
        return f"{symbol[:-2]} LN"
    if symbol.endswith(".AS"):
        return f"{symbol[:-3]} NA"
    if symbol.endswith(".DE"):
        return f"{symbol[:-3]} GR"
    if symbol.endswith(".PA"):
        return f"{symbol[:-3]} FP"
    if symbol.endswith(".T"):
        return f"{symbol[:-2]} JP"
    if symbol.startswith("^"):
        return f"{symbol[1:]} Index"
    if symbol.endswith("=X"):
        return f"{symbol[:-2]} Curncy"
    if symbol.endswith("=F"):
        return f"{symbol[:-2]} Comdty"
    if symbol.endswith("-USD"):
        return f"{symbol[:-4]} Curncy"
    if asset == "index":
        return f"{symbol} Index"
    return f"{symbol} US"


def peers_for(symbol: str) -> list[str]:
    mapped = PEER_MAP.get(symbol)
    if mapped:
        return [item for item in mapped if item != symbol]
    asset = classify(symbol)
    if asset == "equity":
        return [item for item in ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"] if item != symbol]
    if asset == "etf":
        return [item for item in ["SPY", "QQQ", "IWM", "DIA", "EFA"] if item != symbol]
    return []


def search_catalog(query: str, limit: int = 12) -> list[dict[str, str]]:
    needle = query.strip().upper()
    if not needle:
        return CATALOG[:limit]
    normalized = normalize_symbol(needle)
    hits: list[dict[str, str]] = []
    for row in CATALOG:
        blob = f"{row['symbol']} {row['name']} {bloomberg_label(row['symbol'])}".upper()
        if needle in blob or normalized == row["symbol"] or needle in bloomberg_label(row["symbol"]).upper():
            hits.append(row)
    if not hits and normalized:
        asset = classify(normalized)
        hits.append(
            {
                "symbol": normalized,
                "name": name_for(normalized),
                "assetClass": asset,
                "exchange": exchange_for(normalized),
                "currency": currency_for(normalized),
            }
        )
    return hits[:limit]


NAME_TO_TICKER = {
    "apple": "AAPL",
    "iphone": "AAPL",
    "nvidia": "NVDA",
    "microsoft": "MSFT",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "broadcom": "AVGO",
    "amd": "AMD",
    "tencent": "0700.HK",
    "alibaba": "9988.HK",
    "meituan": "3690.HK",
    "xiaomi": "1810.HK",
    "asml": "ASML.AS",
    "bitcoin": "BTC-USD",
    "gold": "GC=F",
    "crude": "CL=F",
    "wti": "CL=F",
    "hang seng": "^HSI",
    "nikkei": "^N225",
    "nasdaq": "^IXIC",
    "s&p": "^GSPC",
    "dow": "^DJI",
    "ftse": "^FTSE",
    "dax": "^GDAXI",
    "treasury": "^TNX",
    "fed ": "MACRO",
    "fomc": "MACRO",
}
