"""อินดิเคเตอร์ทางเทคนิค คำนวณด้วย pandas.

ชุดอินดิเคเตอร์อิงเทคนิคที่ใช้กันในระบบเทรดเชิงปริมาณ (systematic/quant):
- EMA20/50/200  : เทรนด์ระยะสั้น/กลาง/ใหญ่ (multi-timeframe confluence)
- RSI(14)        : แรงซื้อ/ขาย
- MACD(12,26,9)  : ทิศทางหลัก + โมเมนตัม
- ADX/+DI/-DI(14): ความแรงของเทรนด์ (regime filter) + ทิศทาง
- ATR(14)        : ความผันผวน ใช้คำนวณ SL/TP
"""
from __future__ import annotations

import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close, high, low = df["close"], df["high"], df["low"]

    # เทรนด์: EMA สั้น/กลาง/ใหญ่
    df["ema_fast"] = close.ewm(span=20, adjust=False).mean()
    df["ema_slow"] = close.ewm(span=50, adjust=False).mean()
    df["ema200"] = close.ewm(span=200, adjust=False).mean()

    # RSI(14) แบบ Wilder
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + avg_gain / avg_loss))

    # MACD(12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # True Range (ใช้ร่วมกันระหว่าง ATR และ ADX)
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["atr"] = atr

    # ADX + Directional Movement (วัดความแรงและทิศทางของเทรนด์)
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))
    df["plus_di"] = plus_di
    df["minus_di"] = minus_di
    df["adx"] = dx.ewm(alpha=1 / 14, adjust=False).mean()

    return df
