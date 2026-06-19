"""ทดสอบว่า Confidence score ทำนายผลได้จริงไหม.

แยกผล backtest ตามช่วง confidence + ดูว่า "ถ้ากรองเทรดเฉพาะ confidence >= X" ดีขึ้นไหม
ถ้า confidence มีความหมาย -> ช่วงสูงควร win rate/PF ดีกว่าช่วงต่ำ
"""
from __future__ import annotations

import os

from data import SYMBOL_MAP, SYMBOLS_DEFAULT, fetch_ohlc
from indicators import add_indicators
from strategy import evaluate, levels

WARMUP = 210
FEE = 0.0005


def trades_with_conf(key: str):
    """คืนลิสต์ (return, entry_confidence) ต่อเทรด."""
    df = add_indicators(fetch_ohlc(key, outputsize=5000))
    out = []
    pos = None
    for i in range(WARMUP, len(df)):
        row = df.iloc[i]
        signal, conf, *_ = evaluate(row)
        if pos is None:
            if signal in ("LONG", "SHORT"):
                tp, sl = levels(signal, float(row.close), float(row.atr))
                pos = {"side": signal, "entry": float(row.close), "tp": tp, "sl": sl, "conf": conf}
            continue

        exit_price = None
        hi, lo, close = float(row.high), float(row.low), float(row.close)
        if pos["side"] == "LONG":
            if lo <= pos["sl"]:
                exit_price = pos["sl"]
            elif hi >= pos["tp"]:
                exit_price = pos["tp"]
        else:
            if hi >= pos["sl"]:
                exit_price = pos["sl"]
            elif lo <= pos["tp"]:
                exit_price = pos["tp"]
        if exit_price is None and signal != pos["side"]:
            exit_price = close

        if exit_price is not None:
            if pos["side"] == "LONG":
                ret = (exit_price - pos["entry"]) / pos["entry"]
            else:
                ret = (pos["entry"] - exit_price) / pos["entry"]
            out.append((ret - 2 * FEE, pos["conf"]))
            pos = None
    return out


def summarize(trades):
    n = len(trades)
    if n == 0:
        return None
    rets = [t[0] for t in trades]
    wins = [r for r in rets if r > 0]
    gw = sum(wins)
    gl = -sum(r for r in rets if r <= 0)
    eq = 1.0
    for r in rets:
        eq *= 1 + r
    return {
        "n": n,
        "win": len(wins) / n * 100,
        "total": (eq - 1) * 100,
        "avg": sum(rets) / n * 100,
        "pf": gw / gl if gl > 0 else float("inf"),
    }


def main() -> None:
    all_t = []
    for key in SYMBOLS_DEFAULT:
        try:
            all_t.extend(trades_with_conf(key))
        except Exception as exc:  # noqa: BLE001
            print(f"{SYMBOL_MAP[key]}: error {exc}")

    print("=== แยกผลตามช่วง Confidence (ถ้า confidence มีความหมาย ช่วงสูงควรดีกว่า) ===")
    print(f"{'ช่วง conf':<12}{'เทรด':>6}{'Winrate':>9}{'เฉลี่ย/เทรด':>13}{'PF':>7}")
    print("-" * 47)
    for lo, hi in [(0, 50), (50, 60), (60, 70), (70, 80), (80, 101)]:
        s = summarize([t for t in all_t if lo <= t[1] < hi])
        label = f"{lo}-{hi - 1}%"
        if s:
            print(f"{label:<12}{s['n']:>6}{s['win']:>8.1f}%{s['avg']:>12.2f}%{s['pf']:>7.2f}")
        else:
            print(f"{label:<12}{'0':>6}")

    print("\n=== ถ้าเทรดเฉพาะ Confidence >= X ===")
    print(f"{'เกณฑ์':<12}{'เทรด':>6}{'Winrate':>9}{'กำไรรวม':>10}{'PF':>7}")
    print("-" * 45)
    for x in [0, 50, 60, 70, 80]:
        s = summarize([t for t in all_t if t[1] >= x])
        if s:
            print(f"{'>= ' + str(x) + '%':<12}{s['n']:>6}{s['win']:>8.1f}%{s['total']:>9.1f}%{s['pf']:>7.2f}")
        else:
            print(f"{'>= ' + str(x) + '%':<12}{'0':>6}")


if __name__ == "__main__":
    main()
