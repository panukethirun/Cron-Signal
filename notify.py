"""ส่งข้อความแจ้งเตือน — รองรับหลายช่องทาง (Telegram / LINE).

ตั้งค่าช่องไหน ก็ส่งช่องนั้น (ตั้งหลายช่อง = ส่งทุกช่อง). ถ้าไม่ตั้งเลย = พิมพ์ออกจอ

- Telegram (แนะนำ ฟรีไม่จำกัด): TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
- LINE Messaging API:           LINE_CHANNEL_ACCESS_TOKEN (+ LINE_TO ถ้าจะ push)
"""
from __future__ import annotations

import os

import requests

TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_TO = os.environ.get("LINE_TO", "")


def send_telegram(text: str) -> None:
    resp = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    if resp.status_code == 200:
        print("[notify] ส่ง Telegram สำเร็จ")
    else:
        print(f"[notify] Telegram error {resp.status_code}: {resp.text}")


def send_line(text: str) -> None:
    if LINE_TO:
        url = "https://api.line.me/v2/bot/message/push"
        payload = {"to": LINE_TO, "messages": [{"type": "text", "text": text}]}
    else:
        url = "https://api.line.me/v2/bot/message/broadcast"
        payload = {"messages": [{"type": "text", "text": text}]}

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {LINE_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if resp.status_code == 200:
        print("[notify] ส่ง LINE สำเร็จ")
    else:
        print(f"[notify] LINE error {resp.status_code}: {resp.text}")


def send_signal(text: str) -> None:
    """ส่งไปทุกช่องทางที่ตั้งค่าไว้ (Telegram และ/หรือ LINE)."""
    sent = False
    if TG_TOKEN and TG_CHAT:
        send_telegram(text)
        sent = True
    # --- ปิดการส่ง LINE ชั่วคราว (เอาคอมเมนต์ออกถ้าจะกลับมาใช้) ---
    # if LINE_TOKEN:
    #     send_line(text)
    #     sent = True
    if not sent:
        print("[notify] ยังไม่ได้ตั้งช่องทางส่ง — แสดงข้อความแทน:\n")
        print(text)
