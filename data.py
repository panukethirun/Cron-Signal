"""ดึงข้อมูลแท่งเทียน (OHLC) จาก Twelve Data — ฟรี รองรับทั้ง crypto และทองคำ.

สมัครคีย์ฟรีที่ https://twelvedata.com/  (Free plan: 800 req/วัน, 8 req/นาที)
"""
from __future__ import annotations

import os

import pandas as pd
import requests

TD_KEY = os.environ.get("TWELVEDATA_API_KEY", "")

# แมปชื่อย่อ -> สัญลักษณ์ของ Twelve Data
SYMBOL_MAP = {
    "BTC": "BTC/USD",
    "ETH": "ETH/USD",
    "USDJPY": "USD/JPY",  # คู่เงิน ดอลลาร์/เยน
    "XAU": "XAU/USD",     # ทองคำ
}


def fetch_ohlc(symbol_key: str, interval: str = "1h", outputsize: int = 300) -> pd.DataFrame:
    """คืน DataFrame คอลัมน์ time/open/high/low/close เรียงจากเก่า -> ใหม่."""
    if not TD_KEY:
        raise RuntimeError(
            "ยังไม่ได้ตั้งค่า TWELVEDATA_API_KEY (สมัครฟรีที่ twelvedata.com)"
        )

    sym = SYMBOL_MAP[symbol_key]
    resp = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": sym,
            "interval": interval,
            "outputsize": outputsize,
            "order": "ASC",          # เก่าสุดมาก่อน เพื่อคำนวณอินดิเคเตอร์
            "apikey": TD_KEY,
        },
        timeout=30,
    )
    data = resp.json()
    if "values" not in data:
        raise RuntimeError(f"Twelve Data error ({sym}): {data.get('message', data)}")

    df = pd.DataFrame(data["values"]).rename(columns={"datetime": "time"})
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    return df.reset_index(drop=True)
