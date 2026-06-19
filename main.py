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

from data import SYMBOL_MAP, fetch_ohlc
from indicators import add_indicators
from notify import send_signal
from strategy import decide, levels

SYMBOLS = ["BTC", "ETH", "USDJPY", "XAU"]
STATE_FILE = Path("state.json")
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


def format_block(key: str, signal: str, confidence: int, reasons: list[str], last) -> str:
    price = last.close
    tp, sl = levels(signal, price, last.atr)
    head = f"{EMOJI[signal]} {SYMBOL_MAP[key]} — {signal} · มั่นใจ {confidence}%"
    body = f"{conf_bar(confidence)}\nราคา {price:,.2f}\n{' · '.join(reasons)}"
    if tp is not None:
        body += f"\n🎯 TP {tp:,.2f} · 🛑 SL {sl:,.2f}"
    return f"{head}\n{body}"


def main() -> None:
    state = load_state()
    new_state: dict = {}
    blocks: list[str] = []
    changed = False

    for key in SYMBOLS:
        try:
            df = add_indicators(fetch_ohlc(key))
            signal, confidence, reasons, last = decide(df)
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"⚠️ {SYMBOL_MAP[key]}: ดึงข้อมูลไม่สำเร็จ ({exc})")
            continue

        new_state[key] = signal
        if state.get(key) != signal:
            changed = True
        blocks.append(format_block(key, signal, confidence, reasons, last))

    message = (
        "📊 สัญญาณเทรด (TF 1H)\n"
        f"🕐 {th_now()} (เวลาไทย)\n\n"
        + "\n\n".join(blocks)
        + "\n\n— อิงอินดิเคเตอร์ทางเทคนิค ไม่ใช่คำแนะนำการลงทุน —"
    )

    if changed or ALWAYS_SEND:
        send_signal(message)
    else:
        print("[main] สัญญาณไม่เปลี่ยน ข้ามการส่ง LINE\n")
        print(message)

    save_state(new_state)


if __name__ == "__main__":
    main()
