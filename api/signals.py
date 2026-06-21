"""Vercel serverless function — คำนวณสัญญาณสด + AI ตอนกด Refresh บน dashboard.

POST /api/signals -> คืน JSON หน้าตาเดียวกับ signals.json (คำนวณสดจากราคาล่าสุด)

self-contained โดยตั้งใจ (อินดิเคเตอร์ pure-python ใช้แค่ requests ไม่พึ่ง pandas)
เพื่อให้ deploy บน Vercel ง่ายและชัวร์. ตรรกะมิเรอร์มาจาก strategy.py/indicators.py
*** ถ้าแก้ตรรกะหลัก อย่าลืมแก้ไฟล์นี้ให้ตรงกันด้วย ***

ต้องตั้ง Environment Variables บน Vercel:
  TWELVEDATA_API_KEY (จำเป็น), DEEPSEEK_API_KEY (ไม่บังคับ — ใส่ถ้าอยากได้บรรทัด AI)
"""
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import json
import os
import xml.etree.ElementTree as ET

import requests

TD_KEY = os.environ.get("TWELVEDATA_API_KEY", "")
DS_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DS_BASE = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
DS_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")

# (key, ชื่อแสดง, คำค้นข่าว)
SYMBOLS = [
    ("BTC", "BTC/USD", "bitcoin price"),
    ("ETH", "ETH/USD", "ethereum price"),
    ("USDJPY", "USD/JPY", "USD JPY yen dollar forex"),
    ("XAU", "XAU/USD", "gold price XAU"),
]

WEIGHTS = {"ema_fast_slow": 2.0, "ema_htf": 2.0, "macd_zero": 1.5,
           "macd_hist": 1.0, "rsi": 1.0, "di": 1.5}
TOTAL_W = sum(WEIGHTS.values())
ADX_RANGING = 20
AGREE_MIN = 0.34
TH_MONTHS = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
             "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def _ema(vals, span):
    k = 2 / (span + 1)
    prev = vals[0]
    out = [prev]
    for v in vals[1:]:
        prev = v * k + prev * (1 - k)
        out.append(prev)
    return out


def _wilder(vals, n):
    a = 1 / n
    prev = vals[0]
    out = [prev]
    for v in vals[1:]:
        prev = v * a + prev * (1 - a)
        out.append(prev)
    return out


def fetch_ohlc(sym):
    r = requests.get("https://api.twelvedata.com/time_series", params={
        "symbol": sym, "interval": "1h", "outputsize": 300,
        "order": "ASC", "apikey": TD_KEY}, timeout=20)
    d = r.json()
    if "values" not in d:
        raise RuntimeError(d.get("message", "no data"))
    v = d["values"]
    return ([float(x["high"]) for x in v],
            [float(x["low"]) for x in v],
            [float(x["close"]) for x in v])


def indicators(h, l, c):
    n = len(c)
    ema20 = _ema(c, 20)[-1]
    ema50 = _ema(c, 50)[-1]
    ema200 = _ema(c, 200)[-1]

    deltas = [c[i] - c[i - 1] for i in range(1, n)]
    ag = _wilder([max(d, 0) for d in deltas], 14)[-1]
    al = _wilder([max(-d, 0) for d in deltas], 14)[-1]
    rsi = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)

    e12, e26 = _ema(c, 12), _ema(c, 26)
    macd = [e12[i] - e26[i] for i in range(n)]
    sig = _ema(macd, 9)
    macd_last = macd[-1]
    hist_last = macd[-1] - sig[-1]

    tr = [h[0] - l[0]]
    for i in range(1, n):
        tr.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    atr = _wilder(tr, 14)

    pdm, mdm = [0.0], [0.0]
    for i in range(1, n):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm.append(up if (up > dn and up > 0) else 0.0)
        mdm.append(dn if (dn > up and dn > 0) else 0.0)
    pdm_s, mdm_s = _wilder(pdm, 14), _wilder(mdm, 14)
    pdi = [100 * pdm_s[i] / atr[i] if atr[i] else 0 for i in range(n)]
    mdi = [100 * mdm_s[i] / atr[i] if atr[i] else 0 for i in range(n)]
    dx = []
    for i in range(n):
        s = pdi[i] + mdi[i]
        dx.append(100 * abs(pdi[i] - mdi[i]) / s if s else 0)
    adx = _wilder(dx, 14)[-1]

    return {"ema20": ema20, "ema50": ema50, "ema200": ema200, "rsi": rsi,
            "macd": macd_last, "hist": hist_last, "plus_di": pdi[-1],
            "minus_di": mdi[-1], "adx": adx, "atr": atr[-1], "close": c[-1]}


def adx_label(adx):
    if adx < ADX_RANGING:
        return "ไซด์เวย์"
    if adx < 25:
        return "เริ่มมีเทรนด์"
    if adx < 50:
        return "เทรนด์แข็ง"
    return "แรงมาก ระวังกลับตัว"


def evaluate(ind):
    votes = {
        "ema_fast_slow": 1 if ind["ema20"] > ind["ema50"] else -1,
        "ema_htf": 1 if ind["ema50"] > ind["ema200"] else -1,
        "macd_zero": 1 if ind["macd"] > 0 else -1,
        "macd_hist": 1 if ind["hist"] > 0 else -1,
        "di": 1 if ind["plus_di"] > ind["minus_di"] else -1,
        "rsi": 1 if ind["rsi"] >= 55 else (-1 if ind["rsi"] <= 45 else 0),
    }
    net = sum(votes[k] * WEIGHTS[k] for k in votes)
    agreement = abs(net) / TOTAL_W
    adx = ind["adx"]
    tf = min(adx, 40.0) / 40.0
    direction = 1 if net > 0 else -1
    confidence = round(100 * agreement * tf)
    if adx < ADX_RANGING or agreement < AGREE_MIN:
        signal = "NEUTRAL"
    else:
        signal = "LONG" if direction > 0 else "SHORT"

    reasons = ["เทรนด์ขาขึ้น" if votes["ema_fast_slow"] > 0 else "เทรนด์ขาลง"]
    if signal != "NEUTRAL":
        reasons.append("เทรนด์ใหญ่หนุน" if votes["ema_htf"] == direction else "สวนเทรนด์ใหญ่")
    reasons.append(f"ADX {adx:.0f} {adx_label(adx)}")
    reasons.append(f"RSI {ind['rsi']:.0f}")
    return signal, confidence, reasons


def levels(signal, price, atr):
    if signal == "LONG":
        return price + 2.5 * atr, price - 1.5 * atr
    if signal == "SHORT":
        return price - 2.5 * atr, price + 1.5 * atr
    return None, None


def headlines(query, limit=8):
    url = "https://news.google.com/rss/search?q=" + quote(query) + "&hl=en-US&gl=US&ceid=US:en"
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    root = ET.fromstring(r.content)
    return [it.findtext("title") or "" for it in root.iter("item") if it.findtext("title")][:limit]


def analyze_sentiment(news_by_asset):
    if not DS_KEY:
        return {}
    blocks = []
    for asset, hl in news_by_asset.items():
        joined = "\n".join(f"- {h}" for h in hl) or "- (no headlines)"
        blocks.append(f"### {asset}\n{joined}")
    schema = ('{"<asset>": {"score": <-1..1>, "label": "bullish|bearish|neutral", '
              '"reason": "<เหตุผลสั้น ภาษาไทย ไม่เกิน 12 คำ>"}}')
    user = ("วิเคราะห์ sentiment ราคาช่วงสั้น (1-4 ชั่วโมง) ของแต่ละสินทรัพย์จากพาดหัวข่าว\n"
            f"ตอบเป็น JSON object เดียว key=ชื่อสินทรัพย์ตรงตามที่ให้: {schema}\n\n"
            + "\n\n".join(blocks))
    try:
        r = requests.post(f"{DS_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {DS_KEY}", "Content-Type": "application/json"},
            json={"model": DS_MODEL, "messages": [
                {"role": "system", "content": "You are a financial news sentiment analyst. Output ONLY valid JSON. Be conservative; neutral if mixed/irrelevant."},
                {"role": "user", "content": user}],
                "response_format": {"type": "json_object"}, "temperature": 0.3, "stream": False},
            timeout=25)
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception:
        return {}


def compute():
    results, news = [], {}
    for key, sym, q in SYMBOLS:
        try:
            h, l, c = fetch_ohlc(sym)
            ind = indicators(h, l, c)
            signal, conf, reasons = evaluate(ind)
            results.append((sym, ind, signal, conf, reasons))
        except Exception as e:  # noqa: BLE001
            results.append((sym, None, str(e)))
        try:
            news[sym] = headlines(q)
        except Exception:  # noqa: BLE001
            news[sym] = []

    ai = analyze_sentiment(news)

    cards = []
    for item in results:
        sym = item[0]
        if item[1] is None:
            cards.append({"symbol": sym, "signal": "ERROR", "error": item[2]})
            continue
        _, ind, signal, conf, reasons = item
        tp, sl = levels(signal, ind["close"], ind["atr"])
        cards.append({
            "symbol": sym, "signal": signal, "confidence": conf,
            "price": round(ind["close"], 2),
            "tp": round(tp, 2) if tp is not None else None,
            "sl": round(sl, 2) if sl is not None else None,
            "rsi": round(ind["rsi"], 1), "adx": round(ind["adx"], 1),
            "reasons": reasons, "ai": ai.get(sym),
        })

    now = datetime.now(timezone.utc) + timedelta(hours=7)
    return {
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "updated_th": f"{now.day} {TH_MONTHS[now.month]} {now.year + 543}, {now:%H:%M} น.",
        "timeframe": "1H", "live": True, "signals": cards,
    }


class handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            if not TD_KEY:
                raise RuntimeError("ยังไม่ได้ตั้ง TWELVEDATA_API_KEY บน Vercel")
            self._send(200, compute())
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": str(e)})

    def do_GET(self):
        # GET ไม่คำนวณ (กัน bot/prefetch มายิงเปลือง API) — ใช้ POST เท่านั้น
        self._send(200, {"info": "POST to compute live signals"})
