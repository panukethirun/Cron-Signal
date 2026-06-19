"""ตัวรันหลัก: ดึงข้อมูล -> คำนวณสัญญาณ -> ส่ง LINE.

ค่าเริ่มต้นจะ "ส่งเฉพาะตอนสัญญาณเปลี่ยน" เพื่อประหยัดโควต้า LINE ฟรี
ตั้ง ALWAYS_SEND=true ถ้าต้องการให้ส่งทุกชั่วโมงไม่ว่าจะเปลี่ยนหรือไม่
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_sentiment import analyze_sentiment
from data import SYMBOL_MAP, fetch_ohlc
from indicators import add_indicators
from news import fetch_headlines
from notify import send_signal
from strategy import decide, levels

SYMBOLS = ["BTC", "ETH", "USDJPY", "XAU"]
STATE_FILE = Path("state.json")
SIGNALS_FILE = Path("signals.json")  # ข้อมูลสำหรับ dashboard บนเว็บ
ALWAYS_SEND = os.environ.get("ALWAYS_SEND", "false").lower() == "true"

EMOJI = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}
TH_MONTHS = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
             "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


def th_now() -> str:
    now = datetime.datetime.now(ZoneInfo("Asia/Bangkok"))
    return f"{now.day} {TH_MONTHS[now.month]} {now.year + 543}, {now:%H:%M} น."


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def conf_bar(pct: int) -> str:
    filled = max(0, min(5, round(pct / 20)))
    return "▰" * filled + "▱" * (5 - filled)


def ai_emoji(score: float) -> str:
    return "🟢" if score > 0.15 else "🔴" if score < -0.15 else "⚪"


def format_block(key: str, signal: str, confidence: int, reasons: list[str], last, ai=None) -> str:
    price = last.close
    tp, sl = levels(signal, price, last.atr)
    head = f"{EMOJI[signal]} {SYMBOL_MAP[key]} — {signal} · มั่นใจ {confidence}%"
    body = f"{conf_bar(confidence)}\nราคา {price:,.2f}\n{' · '.join(reasons)}"
    if tp is not None:
        body += f"\n🎯 TP {tp:,.2f} · 🛑 SL {sl:,.2f}"
    if ai:
        score = ai.get("score", 0)
        body += f"\n🤖 ข่าว: {ai_emoji(score)} {ai.get('label', '-')} ({score:+.1f}) {ai.get('reason', '')}"
    return f"{head}\n{body}"


def main() -> None:
    state = load_state()
    new_state: dict = {}
    changed = False

    # 1) คำนวณสัญญาณเทคนิคของทุกสินทรัพย์
    computed = []  # (key, signal, confidence, reasons, last) หรือ (key, None, error)
    for key in SYMBOLS:
        try:
            df = add_indicators(fetch_ohlc(key))
            signal, confidence, reasons, last = decide(df)
            computed.append((key, signal, confidence, reasons, last))
            new_state[key] = signal
            if state.get(key) != signal:
                changed = True
        except Exception as exc:  # noqa: BLE001
            computed.append((key, None, str(exc)))

    # 2) AI วิเคราะห์ sentiment จากข่าว (ข้ามได้ถ้าไม่มี DEEPSEEK_API_KEY)
    ai_by_asset = {}
    if os.environ.get("DEEPSEEK_API_KEY"):
        try:
            news = {SYMBOL_MAP[k]: fetch_headlines(k) for k in SYMBOLS}
            ai_by_asset = analyze_sentiment(news)
        except Exception as exc:  # noqa: BLE001
            print(f"[ai] ข้ามส่วน AI: {exc}")

    # 3) ประกอบข้อความ + การ์ดสำหรับ dashboard
    blocks: list[str] = []
    cards: list[dict] = []
    for item in computed:
        key = item[0]
        sym = SYMBOL_MAP[key]
        if item[1] is None:  # ดึงข้อมูลไม่สำเร็จ
            blocks.append(f"⚠️ {sym}: ดึงข้อมูลไม่สำเร็จ ({item[2]})")
            cards.append({"symbol": sym, "signal": "ERROR", "error": item[2]})
            continue

        _, signal, confidence, reasons, last = item
        ai = ai_by_asset.get(sym)
        blocks.append(format_block(key, signal, confidence, reasons, last, ai))
        tp, sl = levels(signal, float(last.close), float(last.atr))
        cards.append({
            "symbol": sym,
            "signal": signal,
            "confidence": confidence,
            "price": round(float(last.close), 2),
            "tp": round(tp, 2) if tp is not None else None,
            "sl": round(sl, 2) if sl is not None else None,
            "rsi": round(float(last.rsi), 1),
            "adx": round(float(last.adx), 1),
            "reasons": reasons,
            "ai": ai,
        })

    # 4) เขียนไฟล์ข้อมูลสำหรับ dashboard (เขียนทุกครั้ง แม้สัญญาณไม่เปลี่ยน)
    SIGNALS_FILE.write_text(json.dumps({
        "updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "updated_th": th_now(),
        "timeframe": "1H",
        "signals": cards,
    }, ensure_ascii=False, indent=2))

    # 5) ส่งแจ้งเตือน
    ai_legend = (
        "\n\n🤖 ข่าว = sentiment จาก AI (ช่วง −1 ถึง +1)\n"
        "− ข่าวโทนลบ (กดราคาลง) · + ข่าวโทนบวก (ดันราคาขึ้น) · ยิ่งใกล้ปลาย ยิ่งแรง"
    ) if ai_by_asset else ""
    message = (
        "📊 สัญญาณเทรด (TF 1H)\n"
        f"🕐 {th_now()} (เวลาไทย)\n\n"
        + "\n\n".join(blocks)
        + ai_legend
    )
    if changed or ALWAYS_SEND:
        send_signal(message)
    else:
        print("[main] สัญญาณไม่เปลี่ยน ข้ามการส่งแจ้งเตือน\n")
        print(message)

    save_state(new_state)


if __name__ == "__main__":
    main()
