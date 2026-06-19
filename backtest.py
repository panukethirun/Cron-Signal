"""Backtest กลยุทธ์กับข้อมูลย้อนหลัง 1H — วัดผลจริงว่าได้ดีแค่ไหน.

วิธีจำลอง (ตรงกับตรรกะ live ผ่าน strategy.evaluate):
- เข้า position เมื่อมีสัญญาณ LONG/SHORT (ที่ราคาปิดของแท่งนั้น)
- ออกเมื่อ: ราคาแตะ TP, แตะ SL (ดูจาก high/low ในแท่ง), หรือสัญญาณกลับ/หาย (ปิดที่ราคาปิด)
- ถ้าแท่งเดียวแตะทั้ง TP และ SL -> ถือว่าโดน SL ก่อน (อนุรักษ์นิยม)
- หักค่าธรรมเนียม+สลิป FEE ต่อข้าง

ข้อจำกัด: ไม่มี leverage, ถือทีละ 1 position ต่อสินทรัพย์, ไม่คิด funding/overnight,
ใช้ข้อมูลเท่าที่ Twelve Data free ให้ (≈ ไม่กี่เดือน–ปี). เป็นค่าประมาณ ไม่ใช่ผลเป๊ะ.
"""
from __future__ import annotations

import os

from data import SYMBOLS_DEFAULT, SYMBOL_MAP, fetch_ohlc
from indicators import add_indicators
from strategy import evaluate, levels

WARMUP = 210         # ข้ามแท่งแรก ๆ ให้ EMA200/ADX นิ่ง
FEE = 0.0005         # ค่าธรรมเนียม+สลิป ต่อข้าง (0.05%)


def backtest_symbol(key: str):
    df = add_indicators(fetch_ohlc(key, outputsize=5000))
    n = len(df)
    trades: list[float] = []
    pos = None

    for i in range(WARMUP, n):
        row = df.iloc[i]
        signal, _conf, _dir, _adx, _votes = evaluate(row)

        if pos is None:
            if signal in ("LONG", "SHORT"):
                tp, sl = levels(signal, float(row.close), float(row.atr))
                pos = {"side": signal, "entry": float(row.close), "tp": tp, "sl": sl}
            continue

        # อยู่ใน position -> เช็คทางออก
        exit_price = None
        hi, lo, close = float(row.high), float(row.low), float(row.close)
        if pos["side"] == "LONG":
            if lo <= pos["sl"]:
                exit_price = pos["sl"]
            elif hi >= pos["tp"]:
                exit_price = pos["tp"]
        else:  # SHORT
            if hi >= pos["sl"]:
                exit_price = pos["sl"]
            elif lo <= pos["tp"]:
                exit_price = pos["tp"]
        # สัญญาณกลับ/หาย -> ปิดที่ราคาปิด
        if exit_price is None and signal != pos["side"]:
            exit_price = close

        if exit_price is not None:
            if pos["side"] == "LONG":
                ret = (exit_price - pos["entry"]) / pos["entry"]
            else:
                ret = (pos["entry"] - exit_price) / pos["entry"]
            trades.append(ret - 2 * FEE)
            pos = None

    buy_hold = float(df.close.iloc[-1]) / float(df.close.iloc[WARMUP]) - 1
    return trades, n, buy_hold


def stats(trades: list[float]) -> dict:
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t <= 0]
    gross_w = sum(wins)
    gross_l = -sum(losses)

    equity, peak, mdd = 1.0, 1.0, 0.0
    for t in trades:
        equity *= 1 + t
        peak = max(peak, equity)
        mdd = max(mdd, (peak - equity) / peak)

    return {
        "n": n,
        "win_rate": len(wins) / n * 100,
        "total": (equity - 1) * 100,                # ผลตอบแทนทบต้นรวม %
        "avg": sum(trades) / n * 100,
        "avg_win": (gross_w / len(wins) * 100) if wins else 0,
        "avg_loss": (gross_l / len(losses) * 100) if losses else 0,
        "pf": (gross_w / gross_l) if gross_l > 0 else float("inf"),
        "mdd": mdd * 100,
    }


def main() -> None:
    all_trades: list[float] = []
    print(f"{'สินทรัพย์':<10}{'เทรด':>6}{'Winrate':>9}{'กำไรรวม':>10}{'PF':>7}{'MaxDD':>8}{'B&H':>9}")
    print("-" * 60)

    for key in SYMBOLS_DEFAULT:
        try:
            trades, n, bh = backtest_symbol(key)
        except Exception as exc:  # noqa: BLE001
            print(f"{SYMBOL_MAP[key]:<10} error: {exc}")
            continue
        s = stats(trades)
        all_trades.extend(trades)
        if s["n"] == 0:
            print(f"{SYMBOL_MAP[key]:<10}{'0':>6}  (ไม่มีสัญญาณในช่วงนี้, {n} แท่ง)")
            continue
        print(f"{SYMBOL_MAP[key]:<10}{s['n']:>6}{s['win_rate']:>8.1f}%"
              f"{s['total']:>9.1f}%{s['pf']:>7.2f}{s['mdd']:>7.1f}%{bh*100:>8.1f}%")

    print("-" * 60)
    o = stats(all_trades)
    if o.get("n"):
        print(f"{'รวมทุกตัว':<10}{o['n']:>6}{o['win_rate']:>8.1f}%"
              f"{o['total']:>9.1f}%{o['pf']:>7.2f}{o['mdd']:>7.1f}%")
        print(f"\nเฉลี่ยต่อเทรด {o['avg']:+.2f}% · กำไรเฉลี่ย {o['avg_win']:.2f}% · "
              f"ขาดทุนเฉลี่ย -{o['avg_loss']:.2f}%")
        print("PF = Profit Factor (>1 = กำไร), MaxDD = ขาดทุนสูงสุดจากจุดพีค, "
              "B&H = ซื้อถือเฉยๆ")


if __name__ == "__main__":
    main()
