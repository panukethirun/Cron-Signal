"""ส่งข้อความเข้า LINE ผ่าน Messaging API (ฟรี).

ตั้งค่า LINE_CHANNEL_ACCESS_TOKEN จาก LINE Developers Console
- ไม่ตั้ง LINE_TO  -> ใช้ broadcast (ส่งหาทุกคนที่เป็นเพื่อนกับ OA)
- ตั้ง LINE_TO     -> ใช้ push หา userId ที่ระบุ
"""
from __future__ import annotations

import os

import requests

LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_TO = os.environ.get("LINE_TO", "")


def send_line(text: str) -> None:
    if not LINE_TOKEN:
        print("[notify] ยังไม่ได้ตั้ง LINE token — แสดงข้อความแทน:\n")
        print(text)
        return

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
