export function sma(values: number[], period: number): Array<number | null> {
  const out: Array<number | null> = [];
  let sum = 0;
  for (let index = 0; index < values.length; index += 1) {
    sum += values[index] ?? 0;
    if (index >= period) sum -= values[index - period] ?? 0;
    out.push(index >= period - 1 ? sum / period : null);
  }
  return out;
}

export function ema(values: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const out: number[] = [];
  let previous = values[0] ?? 0;
  for (let index = 0; index < values.length; index += 1) {
    const value = values[index] ?? previous;
    previous = index === 0 ? value : value * k + previous * (1 - k);
    out.push(previous);
  }
  return out;
}

export function rsi(values: number[], period = 14): Array<number | null> {
  const out: Array<number | null> = new Array(values.length).fill(null);
  if (values.length <= period) return out;
  let gain = 0;
  let loss = 0;
  for (let index = 1; index <= period; index += 1) {
    const diff = (values[index] ?? 0) - (values[index - 1] ?? 0);
    if (diff >= 0) gain += diff;
    else loss -= diff;
  }
  let avgGain = gain / period;
  let avgLoss = loss / period;
  const first = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  out[period] = first;
  for (let index = period + 1; index < values.length; index += 1) {
    const diff = (values[index] ?? 0) - (values[index - 1] ?? 0);
    const up = diff > 0 ? diff : 0;
    const down = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + up) / period;
    avgLoss = (avgLoss * (period - 1) + down) / period;
    out[index] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

export function macd(values: number[]): { macd: number[]; signal: number[]; hist: number[] } {
  const fast = ema(values, 12);
  const slow = ema(values, 26);
  const line = fast.map((value, index) => value - (slow[index] ?? value));
  const signal = ema(line, 9);
  const hist = line.map((value, index) => value - (signal[index] ?? 0));
  return { macd: line, signal, hist };
}
