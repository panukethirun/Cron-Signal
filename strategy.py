"""ตรรกะตัดสินสัญญาณ Long / Short / Neutral จากอินดิเคเตอร์.

ใช้ระบบให้คะแนนจาก 4 ปัจจัย:
  1) เทรนด์   : EMA20 vs EMA50
  2) โซน MACD : MACD line เหนือ/ใต้ศูนย์ (ยืนยันทิศทางหลัก)
  3) โมเมนตัม : MACD histogram (MACD vs signal line)
  4) แรงซื้อขาย: RSI(14)

  คะแนน >= +2  -> LONG
  คะแนน <= -2  -> SHORT
  อื่น ๆ        -> NEUTRAL

หมายเหตุ: แยก "โซน MACD" (line vs 0 = ทิศทางหลัก) ออกจาก "โมเมนตัม" (hist)
เพราะในเทรนด์ที่กำลังชะลอตัว hist อาจสวนทางชั่วคราว ไม่ควรใช้ตัดสินทิศทางลำพัง
"""
from __future__ import annotations

import pandas as pd


def decide(df: pd.DataFrame):
    """คืน (signal, score, reasons, last_row)."""
    last = df.iloc[-1]
    score = 0
    reasons: list[str] = []

    # 1) เทรนด์จาก EMA
    if last.ema_fast > last.ema_slow:
        score += 1
        reasons.append("EMA20>EMA50 ขาขึ้น")
    else:
        score -= 1
        reasons.append("EMA20<EMA50 ขาลง")

    # 2) ทิศทางหลักจากตำแหน่ง MACD line เทียบศูนย์
    if last.macd > 0:
        score += 1
        reasons.append("MACD เหนือ 0")
    else:
        score -= 1
        reasons.append("MACD ใต้ 0")

    # 3) โมเมนตัมจาก MACD histogram (MACD line vs signal)
    if last.macd_hist > 0:
        score += 1
        reasons.append("โมเมนตัมขึ้น")
    else:
        score -= 1
        reasons.append("โมเมนตัมลง")

    # 4) แรงซื้อ/ขายจาก RSI
    if last.rsi >= 55:
        score += 1
        reasons.append(f"RSI {last.rsi:.0f} แรง")
    elif last.rsi <= 45:
        score -= 1
        reasons.append(f"RSI {last.rsi:.0f} อ่อน")
    else:
        reasons.append(f"RSI {last.rsi:.0f} กลาง")

    if score >= 2:
        signal = "LONG"
    elif score <= -2:
        signal = "SHORT"
    else:
        signal = "NEUTRAL"

    return signal, score, reasons, last


def levels(signal: str, price: float, atr: float):
    """คืน (take_profit, stop_loss) จาก ATR. คืน (None, None) ถ้า NEUTRAL."""
    if signal == "LONG":
        return price + 2.5 * atr, price - 1.5 * atr
    if signal == "SHORT":
        return price - 2.5 * atr, price + 1.5 * atr
    return None, None
