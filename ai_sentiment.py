"""วิเคราะห์ sentiment จากพาดหัวข่าวด้วย LLM (DeepSeek — หรือ OpenAI-compatible เจ้าอื่น).

ตั้งค่า DEEPSEEK_API_KEY (จาก https://platform.deepseek.com/ — ต้องเติมเงิน แต่ถูกมาก)
อยากใช้เจ้าฟรีแทน เปลี่ยน AI_BASE_URL + AI_MODEL ได้ (เช่น Groq/Gemini/OpenRouter):
  Groq    : AI_BASE_URL=https://api.groq.com/openai/v1   AI_MODEL=llama-3.3-70b-versatile
  Gemini  : AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai  AI_MODEL=gemini-2.0-flash
"""
from __future__ import annotations

import json
import os

import requests

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
MODEL = os.environ.get("AI_MODEL", "deepseek-chat")

SYSTEM = (
    "You are a professional financial-markets news sentiment analyst. "
    "For each asset, read the recent headlines, reason about what they imply for "
    "the next 1-4 hours of price action, then output ONLY valid JSON. "
    "Be conservative: if headlines are mixed, old, or irrelevant, return neutral "
    "(score near 0). Do not invent news."
)


def analyze_sentiment(news_by_asset: dict) -> dict:
    """คืน {asset: {"score": float(-1..1), "label": str, "reason": str}}.

    คืน {} ถ้าไม่มี API key หรือเรียกไม่สำเร็จ (ระบบจะทำงานต่อได้โดยข้ามส่วน AI).
    """
    if not API_KEY:
        return {}

    blocks = []
    for asset, headlines in news_by_asset.items():
        joined = "\n".join(f"- {h}" for h in headlines) or "- (no headlines)"
        blocks.append(f"### {asset}\n{joined}")

    schema = (
        '{"<asset>": {"score": <number from -1 to 1>, '
        '"label": "bullish|bearish|neutral", '
        '"reason": "<เหตุผลสั้น ภาษาไทย ไม่เกิน 12 คำ>"}}'
    )
    user = (
        "วิเคราะห์ sentiment ราคาช่วงสั้น (1-4 ชั่วโมงข้างหน้า) ของแต่ละสินทรัพย์ "
        "จากพาดหัวข่าวด้านล่าง\n"
        f"ตอบเป็น JSON object เดียว โดย key ต้องตรงตามชื่อสินทรัพย์ที่ให้: {schema}\n\n"
        + "\n\n".join(blocks)
    )

    try:
        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.3,
                "stream": False,
            },
            timeout=60,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[ai] เรียก API ไม่สำเร็จ: {exc}")
        return {}

    if resp.status_code != 200:
        print(f"[ai] API error {resp.status_code}: {resp.text[:200]}")
        return {}

    try:
        content = resp.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, json.JSONDecodeError) as exc:
        print(f"[ai] อ่านผลลัพธ์ไม่สำเร็จ: {exc}")
        return {}
