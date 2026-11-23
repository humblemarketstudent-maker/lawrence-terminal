import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { api } from "../lib/api.ts";
import { parseCommand } from "../lib/command.ts";
import type {
  Brief,
  CompanyProfile,
  EcoBoard,
  Filing,
  FuncCode,
  History,
  LayoutMode,
  Meta,
  NewsItem,
  Providers,
  Quote,
  Statements,
  SymbolBundle,
  WeiBoard,
} from "../types.ts";

const DEFAULT_WATCHLIST = [
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
];
const STORAGE = "apex-terminal-v1";

interface Prefs {
  symbol: string;
  func: FuncCode;
  layout: LayoutMode;
  linked: boolean;
  timeframe: string;
  watchlist: string[];
}

function loadPrefs(): Prefs {
    const funcs: FuncCode[] = ["DES", "GP", "FA", "N", "FIL", "WEI", "ECO"];
    const base: Prefs = { symbol: "AAPL", func: "DES", layout: 3, linked: true, timeframe: "1Y", watchlist: DEFAULT_WATCHLIST };
    try {
      const raw = localStorage.getItem(STORAGE);
      if (!raw) return base;
      const parsed = JSON.parse(raw) as Partial<Prefs>;
      return {
        ...base,
        ...parsed,
        func: parsed.func && funcs.includes(parsed.func) ? parsed.func : "DES",
        watchlist: parsed.watchlist?.length ? parsed.watchlist : base.watchlist,
        layout: parsed.layout && [1, 2, 3, 4].includes(parsed.layout) ? parsed.layout : 3,
      };
  } catch {
    return base;
  }
}

interface TerminalValue {
  symbol: string;
  func: FuncCode;
  layout: LayoutMode;
  linked: boolean;
  timeframe: string;
  watchlist: string[];
  quotes: Record<string, Quote>;
  news: NewsItem[];
  symbolNews: NewsItem[];
  newsMeta: Meta | null;
  symbolNewsMeta: Meta | null;
  quoteMeta: Meta | null;
  wei: WeiBoard | null;
  weiMeta: Meta | null;
  eco: EcoBoard | null;
  ecoMeta: Meta | null;
  profile: CompanyProfile | null;
  profileMeta: Meta | null;
  statements: Statements | null;
  statementsMeta: Meta | null;
  history: History | null;
  historyMeta: Meta | null;
  filings: Filing[];
  filingsMeta: Meta | null;
  providers: Providers | null;
  loading: boolean;
  refreshing: boolean;
  banner: string | null;
  briefOpen: boolean;
  brief: Brief | null;
  briefLoading: boolean;
  activeNews: NewsItem | null;
  helpOpen: boolean;
  commandRef: RefObject<HTMLInputElement | null>;
  activeQuote: Quote | null;
  setFunc: (func: FuncCode) => void;
  setLayout: (layout: LayoutMode) => void;
  setLinked: (linked: boolean) => void;
  setTimeframe: (timeframe: string) => void;
  selectTicker: (symbol: string) => void;
  runCommand: (input: string) => string | null;
  addTicker: (raw: string) => Promise<void>;
  removeTicker: (symbol: string) => void;
  refresh: () => Promise<void>;
  openBrief: () => Promise<void>;
  setBriefOpen: (open: boolean) => void;
  setActiveNews: (item: NewsItem | null) => void;
  setHelpOpen: (open: boolean) => void;
  focusCommand: () => void;
}

const TerminalContext = createContext<TerminalValue | null>(null);

export function TerminalProvider({ children }: { children: ReactNode }) {
  const [prefs] = useState(loadPrefs);
  const [symbol, setSymbol] = useState(prefs.symbol);
  const [func, setFuncState] = useState<FuncCode>(prefs.func);
  const [layout, setLayoutState] = useState<LayoutMode>(prefs.layout);
  const [linked, setLinkedState] = useState(prefs.linked);
  const [timeframe, setTimeframeState] = useState(prefs.timeframe);
  const [watchlist, setWatchlist] = useState<string[]>(prefs.watchlist);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [news, setNews] = useState<NewsItem[]>([]);
  const [symbolNews, setSymbolNews] = useState<NewsItem[]>([]);
  const [newsMeta, setNewsMeta] = useState<Meta | null>(null);
  const [symbolNewsMeta, setSymbolNewsMeta] = useState<Meta | null>(null);
  const [quoteMeta, setQuoteMeta] = useState<Meta | null>(null);
  const [wei, setWei] = useState<WeiBoard | null>(null);
  const [weiMeta, setWeiMeta] = useState<Meta | null>(null);
  const [eco, setEco] = useState<EcoBoard | null>(null);
  const [ecoMeta, setEcoMeta] = useState<Meta | null>(null);
  const [profile, setProfile] = useState<CompanyProfile | null>(null);
  const [profileMeta, setProfileMeta] = useState<Meta | null>(null);
  const [statements, setStatements] = useState<Statements | null>(null);
  const [statementsMeta, setStatementsMeta] = useState<Meta | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [historyMeta, setHistoryMeta] = useState<Meta | null>(null);
  const [filings, setFilings] = useState<Filing[]>([]);
  const [filingsMeta, setFilingsMeta] = useState<Meta | null>(null);
  const [providers, setProviders] = useState<Providers | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [briefOpen, setBriefOpen] = useState(false);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [activeNews, setActiveNews] = useState<NewsItem | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const commandRef = useRef<HTMLInputElement>(null);
  const watchRef = useRef(watchlist);
  const symbolRef = useRef(symbol);
  const frameRef = useRef(timeframe);
  useEffect(() => {
    watchRef.current = watchlist;
    symbolRef.current = symbol;
    frameRef.current = timeframe;
  }, [watchlist, symbol, timeframe]);

  const mergeQuotes = useCallback((list: Quote[]) => {
    setQuotes((current) => {
      const next = { ...current };
      for (const quote of list) next[quote.symbol] = quote;
      return next;
    });
  }, []);

  const applyBundle = useCallback((bundle: SymbolBundle) => {
    setSymbol(bundle.symbol);
    setProfile(bundle.profile.data);
    setProfileMeta(bundle.profile.meta);
    setStatements(bundle.statements.data);
    setStatementsMeta(bundle.statements.meta);
    setHistory(bundle.history.data);
    setHistoryMeta(bundle.history.meta);
    setFilings(bundle.filings.data);
    setFilingsMeta(bundle.filings.meta);
    setSymbolNews(bundle.news.data);
    setSymbolNewsMeta(bundle.news.meta);
  }, []);

  const loadSymbol = useCallback(
    async (next: string, frame = frameRef.current) => {
      setLoading(true);
      try {
        const bundle = await api.symbol(next, frame);
        applyBundle(bundle);
        setBanner(null);
      } catch (error) {
        setBanner(error instanceof Error ? error.message : "Symbol load failed. Showing the last book.");
      } finally {
        setLoading(false);
      }
    },
    [applyBundle],
  );

  useEffect(() => {
    let cancelled = false;
    api
        .bootstrap(prefs.symbol, prefs.timeframe)
      .then((payload) => {
        if (cancelled) return;
        mergeQuotes(payload.quotes.data);
        setQuoteMeta(payload.quotes.meta);
        setNews(payload.news.data);
        setNewsMeta(payload.news.meta);
        setWei(payload.wei.data);
        setWeiMeta(payload.wei.meta);
        setEco(payload.eco.data);
        setEcoMeta(payload.eco.meta);
        setProviders(payload.providers);
        applyBundle(payload.bundle);
        setBanner(null);
      })
      .catch(() => {
        if (!cancelled) setBanner("Desk feed unreachable. Retry with R once the API is up.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [applyBundle, mergeQuotes]);

  useEffect(() => {
    const upgrade = () => {
      api
        .symbol(symbolRef.current, frameRef.current)
        .then((bundle) => applyBundle(bundle))
        .catch(() => undefined);
      api
        .wei()
        .then((section) => {
          setWei(section.data);
          setWeiMeta(section.meta);
        })
        .catch(() => undefined);
      api
        .eco()
        .then((section) => {
          setEco(section.data);
          setEcoMeta(section.meta);
        })
        .catch(() => undefined);
    };
    const timers = [4000, 14000].map((delay) => window.setTimeout(upgrade, delay));
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [applyBundle]);

  useEffect(() => {
    const pull = () => {
      api
        .quotes(watchRef.current)
        .then((section) => {
          mergeQuotes(section.data);
          setQuoteMeta(section.meta);
        })
        .catch(() => undefined);
    };
    const early = [2500, 7000].map((delay) => window.setTimeout(pull, delay));
    const timer = window.setInterval(pull, 20000);
    return () => {
      early.forEach((id) => window.clearTimeout(id));
      window.clearInterval(timer);
    };
  }, [mergeQuotes]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      api
        .news()
        .then((section) => {
          setNews(section.data);
          setNewsMeta(section.meta);
        })
        .catch(() => undefined);
    }, 60000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const prefsNext: Prefs = { symbol, func, layout, linked, timeframe, watchlist };
    localStorage.setItem(STORAGE, JSON.stringify(prefsNext));
  }, [symbol, func, layout, linked, timeframe, watchlist]);

  const setFunc = useCallback((next: FuncCode) => setFuncState(next), []);
  const setLayout = useCallback((next: LayoutMode) => setLayoutState(next), []);
  const setLinked = useCallback((next: boolean) => setLinkedState(next), []);

  const setTimeframe = useCallback(
    (next: string) => {
      setTimeframeState(next);
      void loadSymbol(symbolRef.current, next);
    },
    [loadSymbol],
  );

  const selectTicker = useCallback(
    (next: string) => {
      if (!linked) {
        setBanner("Panels are unlinked. Toggle LINK to push a ticker across the desk.");
        return;
      }
      setBanner(null);
      void loadSymbol(next);
    },
    [linked, loadSymbol],
  );

  const openBrief = useCallback(async () => {
    setBriefOpen(true);
    setBriefLoading(true);
    try {
      const note = await api.brief(watchRef.current);
      setBrief(note);
    } catch (error) {
      setBanner(error instanceof Error ? error.message : "Brief failed.");
    } finally {
      setBriefLoading(false);
    }
  }, []);

  const runCommand = useCallback(
    (input: string) => {
      const parsed = parseCommand(input);
      if ("error" in parsed) return parsed.error;
      if (parsed.func === "BRIEF") {
        void openBrief();
        return null;
      }
      setFuncState(parsed.func);
      if (parsed.symbol) void loadSymbol(parsed.symbol);
      return null;
    },
    [loadSymbol, openBrief],
  );

  const addTicker = useCallback(
    async (raw: string) => {
      const query = raw.trim();
      if (!query) return;
      try {
        const hits = await api.search(query);
        const next = hits[0]?.symbol ?? query.toUpperCase();
        setWatchlist((current) => (current.includes(next) ? current : [...current, next]));
        const section = await api.quotes([next]);
        mergeQuotes(section.data);
        if (linked) void loadSymbol(next);
      } catch (error) {
        setBanner(error instanceof Error ? error.message : "Could not add that ticker.");
      }
    },
    [linked, loadSymbol, mergeQuotes],
  );

  const removeTicker = useCallback((next: string) => {
    setWatchlist((current) => current.filter((item) => item !== next));
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await api.refresh(watchRef.current, "all", frameRef.current);
      const payload = await api.bootstrap(symbolRef.current, frameRef.current);
      mergeQuotes(payload.quotes.data);
      setQuoteMeta(payload.quotes.meta);
      setNews(payload.news.data);
      setNewsMeta(payload.news.meta);
      setWei(payload.wei.data);
      setWeiMeta(payload.wei.meta);
      setEco(payload.eco.data);
      setEcoMeta(payload.eco.meta);
      setProviders(payload.providers);
      applyBundle(payload.bundle);
      setBanner(null);
    } catch (error) {
      setBanner(error instanceof Error ? error.message : "Refresh failed. Showing the last book.");
    } finally {
      setRefreshing(false);
    }
  }, [applyBundle, mergeQuotes]);

  const focusCommand = useCallback(() => {
    commandRef.current?.focus();
    commandRef.current?.select();
  }, []);

  const activeQuote = quotes[symbol] ?? null;

  const value = useMemo<TerminalValue>(
    () => ({
      symbol,
      func,
      layout,
      linked,
      timeframe,
      watchlist,
      quotes,
      news,
      symbolNews,
      newsMeta,
      symbolNewsMeta,
      quoteMeta,
      wei,
      weiMeta,
      eco,
      ecoMeta,
      profile,
      profileMeta,
      statements,
      statementsMeta,
      history,
      historyMeta,
      filings,
      filingsMeta,
      providers,
      loading,
      refreshing,
      banner,
      briefOpen,
      brief,
      briefLoading,
      activeNews,
      helpOpen,
      commandRef,
      activeQuote,
      setFunc,
      setLayout,
      setLinked,
      setTimeframe,
      selectTicker,
      runCommand,
      addTicker,
      removeTicker,
      refresh,
      openBrief,
      setBriefOpen,
      setActiveNews,
      setHelpOpen,
      focusCommand,
    }),
    [
      symbol, func, layout, linked, timeframe, watchlist, quotes, news, symbolNews, newsMeta, symbolNewsMeta,
      quoteMeta, wei, weiMeta, eco, ecoMeta, profile, profileMeta, statements, statementsMeta, history, historyMeta,
      filings, filingsMeta, providers, loading, refreshing, banner, briefOpen, brief, briefLoading, activeNews,
      helpOpen, activeQuote, setFunc, setLayout, setLinked, setTimeframe, selectTicker, runCommand, addTicker,
      removeTicker, refresh, openBrief, focusCommand,
    ],
  );

  return <TerminalContext.Provider value={value}>{children}</TerminalContext.Provider>;
}

export function useTerminal() {
  const value = useContext(TerminalContext);
  if (!value) throw new Error("useTerminal must be used inside TerminalProvider");
  return value;
}
