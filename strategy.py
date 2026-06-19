"""ตรรกะตัดสินสัญญาณ + Confidence score.

อิงเทคนิคที่ระบบเทรดเชิงปริมาณใช้กันจริง:
- Multi-indicator confluence แบบ "ถ่วงน้ำหนัก" (ไม่ใช่นับ ±1 เท่ากันหมด)
- ADX เป็น regime filter: ADX < 20 = ไซด์เวย์ -> เลี่ยงเทรด (NEUTRAL)
- Confidence = (ความเห็นพ้องของอินดิเคเตอร์) x (ความแรงของเทรนด์จาก ADX)

Confidence แปลงเป็น 0-100% เพื่อบอกว่าสัญญาณ "น่าเชื่อ" แค่ไหน
"""
from __future__ import annotations

import pandas as pd

# น้ำหนักของแต่ละปัจจัย (รวม = 9.0) — ปัจจัยเทรนด์ได้น้ำหนักมากสุด
WEIGHTS = {
    "ema_fast_slow": 2.0,  # เทรนด์ระยะสั้น/กลาง
    "ema_htf": 2.0,        # เทรนด์ใหญ่ (EMA50 vs EMA200) = multi-timeframe
    "macd_zero": 1.5,      # โซน MACD (เหนือ/ใต้ศูนย์)
    "macd_hist": 1.0,      # โมเมนตัม
    "rsi": 1.0,            # แรงซื้อ/ขาย
    "di": 1.5,             # ทิศทางจาก +DI/-DI
}
TOTAL_W = sum(WEIGHTS.values())

ADX_RANGING = 20   # ต่ำกว่านี้ = ไซด์เวย์ ไม่เทรดตามเทรนด์
AGREE_MIN = 0.34   # ต้องเห็นพ้องอย่างน้อย ~1/3 ของน้ำหนักรวม จึงจะออกสัญญาณ


def _adx_label(adx: float) -> str:
    if adx < ADX_RANGING:
        return "ไซด์เวย์"
    if adx < 25:
        return "เริ่มมีเทรนด์"
    if adx < 50:
        return "เทรนด์แข็ง"
    return "แรงมาก ระวังกลับตัว"


def evaluate(row):
    """ตัดสินจากข้อมูลแถวเดียว — ใช้ทั้ง live และ backtest (causal ไม่มี lookahead).

    คืน (signal, confidence, direction, adx, votes).
    """
    votes = {
        "ema_fast_slow": 1 if row.ema_fast > row.ema_slow else -1,
        "ema_htf": 1 if row.ema_slow > row.ema200 else -1,
        "macd_zero": 1 if row.macd > 0 else -1,
        "macd_hist": 1 if row.macd_hist > 0 else -1,
        "di": 1 if row.plus_di > row.minus_di else -1,
        "rsi": 1 if row.rsi >= 55 else (-1 if row.rsi <= 45 else 0),
    }

    net = sum(votes[k] * WEIGHTS[k] for k in votes)
    agreement = abs(net) / TOTAL_W          # 0..1 อินดิเคเตอร์เห็นพ้องกันแค่ไหน
    adx = float(row.adx)
    trend_factor = min(adx, 40.0) / 40.0    # 0..1 เทรนด์แข็งแค่ไหน (ADX 40+ = เต็ม)

    direction = 1 if net > 0 else -1
    confidence = round(100 * agreement * trend_factor)

    # ADX ต่ำ = ไซด์เวย์ หรือ อินดิเคเตอร์ไม่เห็นพ้องพอ -> ไม่ออกสัญญาณ
    if adx < ADX_RANGING or agreement < AGREE_MIN:
        signal = "NEUTRAL"
    else:
        signal = "LONG" if direction > 0 else "SHORT"

    return signal, confidence, direction, adx, votes


def decide(df: pd.DataFrame):
    """คืน (signal, confidence, reasons, last_row)."""
    last = df.iloc[-1]
    signal, confidence, direction, adx, votes = evaluate(last)
    reasons = _build_reasons(last, votes, direction, adx, signal)
    return signal, confidence, reasons, last


def _build_reasons(last, votes, direction, adx, signal) -> list[str]:
    r: list[str] = []
    r.append("เทรนด์ขาขึ้น" if votes["ema_fast_slow"] > 0 else "เทรนด์ขาลง")

    if signal != "NEUTRAL":
        # เทรนด์ใหญ่หนุนทางเดียวกับสัญญาณไหม
        if votes["ema_htf"] == direction:
            r.append("เทรนด์ใหญ่หนุน")
        else:
            r.append("สวนเทรนด์ใหญ่")

    r.append(f"ADX {adx:.0f} {_adx_label(adx)}")
    r.append(f"RSI {last.rsi:.0f}")
    return r


def levels(signal: str, price: float, atr: float):
    """คืน (take_profit, stop_loss) จาก ATR. คืน (None, None) ถ้า NEUTRAL."""
    if signal == "LONG":
        return price + 2.5 * atr, price - 1.5 * atr
    if signal == "SHORT":
        return price - 2.5 * atr, price + 1.5 * atr
    return None, None
