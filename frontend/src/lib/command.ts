import type { FuncCode } from "../types.ts";

export const TICKER_FUNCS = ["DES", "GP", "FA", "N", "FIL"] as const;
export const GLOBAL_FUNCS = ["WEI", "ECO", "BRIEF"] as const;
export const ALL_FUNCS = [...TICKER_FUNCS, ...GLOBAL_FUNCS] as const;

export interface ParsedCommand {
  func: FuncCode | "BRIEF";
  symbol: string | null;
}

export function parseCommand(input: string): ParsedCommand | { error: string } {
  const raw = input.trim();
  if (!raw) return { error: "Enter a ticker or command. Try AAPL or AAPL US <DES>." };
  const upper = raw.toUpperCase();
  let func: string | null = null;
  let rest = upper;
  const bracket = upper.match(/<([A-Z]+)>/);
  if (bracket) {
    func = bracket[1];
    rest = upper.replace(bracket[0], " ").replace(/\s+/g, " ").trim();
  } else {
    const parts = upper.split(/\s+/);
    const last = parts[parts.length - 1];
    if ((ALL_FUNCS as readonly string[]).includes(last)) {
      func = last;
      rest = parts.slice(0, -1).join(" ");
    }
  }
  if (!func) {
    return { func: "DES", symbol: rest };
  }
  if (!(ALL_FUNCS as readonly string[]).includes(func)) {
    return { error: "Unknown function. Use DES, GP, FA, N, FIL, WEI, ECO, or BRIEF." };
  }
  if (!rest) {
    if ((GLOBAL_FUNCS as readonly string[]).includes(func) || func === "N") {
      return { func: func as ParsedCommand["func"], symbol: null };
    }
    return { error: `<${func}> needs a ticker. Example: AAPL or AAPL US <${func}>.` };
  }
  return { func: func as ParsedCommand["func"], symbol: rest };
}

export const EXAMPLES = [
  "AAPL US <DES>",
  "AAPL US <GP>",
  "AAPL US <FA>",
  "AAPL US <N>",
  "AAPL US <FIL>",
  "NVDA US <GP>",
  "0700 HK <DES>",
  "MSFT US <FA>",
  "<WEI>",
  "<ECO>",
  "<BRIEF>",
];

export const FUNC_HINT: Record<string, string> = {
  DES: "Company tear sheet",
  GP: "Price & volume chart",
  FA: "Financial statements",
  N: "News wire",
  FIL: "SEC filings",
  WEI: "World indices & macro",
  ECO: "Economic calendar",
  BRIEF: "Morning note",
};
