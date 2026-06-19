"""ดึงพาดหัวข่าวรายสินทรัพย์จาก Google News RSS — ฟรี ไม่ต้องมี API key."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

# คำค้นข่าวต่อสินทรัพย์
NEWS_QUERIES = {
    "BTC": "bitcoin price",
    "ETH": "ethereum price",
    "USDJPY": "USD JPY yen dollar forex",
    "XAU": "gold price XAU",
}


def fetch_headlines(symbol_key: str, limit: int = 8) -> list[str]:
    """คืนพาดหัวข่าวล่าสุด (เรียงใหม่->เก่า) ของสินทรัพย์นั้น."""
    query = NEWS_QUERIES.get(symbol_key, symbol_key)
    url = (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(resp.content)
    titles = [item.findtext("title") or "" for item in root.iter("item")]
    return [t for t in titles if t][:limit]
