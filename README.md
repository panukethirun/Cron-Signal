# Cron-Signal 📊

ยิงสัญญาณ **Long / Short** ของ **BTC, ETH, USD/JPY, XAU (ทองคำ)** บน **Timeframe 1 ชั่วโมง**
เข้า **Telegram** อัตโนมัติ + มี **เว็บ Dashboard** + วิเคราะห์ **ข่าวด้วย AI** — **ฟรีแทบทุกขั้นตอน**

| ส่วน | ใช้อะไร |
|---|---|
| ข้อมูลราคา | [Twelve Data](https://twelvedata.com/) (ฟรี 800 req/วัน) |
| ข่าว | Google News RSS (ฟรี ไม่ต้องมี key) |
| วิเคราะห์ข่าว (AI) | DeepSeek (ถูกมาก) — สลับไป Groq/Gemini ฟรีได้ |
| แจ้งเตือน | Telegram Bot (ฟรี ไม่จำกัด) |
| ตั้งเวลา (Cron) | GitHub Actions (ฟรี ไม่ต้องเปิดเครื่อง) |
| Dashboard | Vercel (static ฟรี) |

> ⚠️ **คำเตือน:** สัญญาณนี้ผ่าน backtest แล้ว **ยังไม่มี edge (ขาดทุนในอดีต)** — ใช้เพื่อ **การศึกษา/ดูภาพตลาด** เท่านั้น **ไม่ใช่คำแนะนำการลงทุน** เทรดมีความเสี่ยง (ดูหัวข้อ [Backtest](#-backtest-วัดผลจริง))

---

## 🔧 สถาปัตยกรรม

```
GitHub Actions (cron รายชั่วโมง)
   ├─ ดึงราคา (Twelve Data) → คำนวณอินดิเคเตอร์ + สัญญาณ + Confidence
   ├─ ดึงข่าว (Google News) → DeepSeek วิเคราะห์ sentiment
   ├─ ส่งเข้า Telegram
   └─ เขียน signals.json + commit กลับ repo
                          ↓ raw.githubusercontent.com
        Vercel (static) → index.html ดึง signals.json มาแสดงเป็น dashboard
```

---

## 📐 วิธีคำนวณสัญญาณ

ใช้ **multi-indicator confluence แบบถ่วงน้ำหนัก** บนแท่ง 1H ล่าสุด ([strategy.py](strategy.py)):

| ปัจจัย | น้ำหนัก | ขึ้น (+) / ลง (−) |
|---|---|---|
| เทรนด์ EMA20 vs EMA50 | 2.0 | EMA20 > / < EMA50 |
| เทรนด์ใหญ่ EMA50 vs EMA200 | 2.0 | (multi-timeframe) |
| โซน MACD | 1.5 | MACD line > / < 0 |
| โมเมนตัม MACD | 1.0 | histogram > / < 0 |
| ทิศทาง +DI/−DI | 1.5 | +DI > / < −DI |
| RSI(14) | 1.0 | ≥ 55 / ≤ 45 |

- **ADX เป็น regime filter:** ADX < 20 = ไซด์เวย์ → ไม่ออกสัญญาณ (NEUTRAL)
- **Confidence (0–100%)** = (อินดิเคเตอร์เห็นพ้องกันแค่ไหน) × (เทรนด์แข็งแค่ไหนจาก ADX)
- **TP/SL** คำนวณจาก ATR (LONG: TP +2.5×ATR, SL −1.5×ATR / SHORT กลับด้าน)
- **🤖 AI ข่าว** ให้คะแนน sentiment −1 ถึง +1 (− ลบ/กดราคาลง, + บวก/ดันขึ้น) แสดงควบคู่กับสัญญาณเทคนิค

---

## 🗂 ไฟล์ในโปรเจค

| ไฟล์ | หน้าที่ |
|---|---|
| [data.py](data.py) | ดึง OHLC จาก Twelve Data + รายชื่อสัญลักษณ์ |
| [indicators.py](indicators.py) | EMA / RSI / MACD / ADX / ATR |
| [strategy.py](strategy.py) | ตัดสินสัญญาณ + Confidence |
| [news.py](news.py) | ดึงข่าวจาก Google News RSS |
| [ai_sentiment.py](ai_sentiment.py) | วิเคราะห์ข่าวด้วย DeepSeek |
| [notify.py](notify.py) | ส่ง Telegram / LINE |
| [main.py](main.py) | ตัวรันหลัก + เขียน signals.json |
| [index.html](index.html) | เว็บ dashboard |
| [backtest.py](backtest.py) · [backtest_confidence.py](backtest_confidence.py) | เครื่องมือวัดผลย้อนหลัง |
| [.github/workflows/signals.yml](.github/workflows/signals.yml) | ตั้งเวลารันอัตโนมัติ |

---

## 🚀 ติดตั้ง

### 1️⃣ คีย์ข้อมูลราคา — Twelve Data
สมัครฟรีที่ https://twelvedata.com/ → หน้า **API Keys** → คัดลอก key

### 2️⃣ Telegram Bot
1. เปิด Telegram หา **@BotFather** → `/newbot` → ตั้งชื่อ + username (ลงท้าย `bot`) → ได้ **bot token**
2. **กด Start คุยกับบอทที่เพิ่งสร้าง** (สำคัญ! บอทส่งหาเราได้ต่อเมื่อเราทักก่อน)
3. หา **chat id** จาก **@userinfobot** (กด Start แล้วมันตอบเลข id)

### 3️⃣ (ไม่บังคับ) AI วิเคราะห์ข่าว — DeepSeek
สมัคร https://platform.deepseek.com/ → เติมเงิน (ใช้แค่ ~1 call/รอบ ถูกมาก) → ได้ API key
> อยากใช้ฟรี: เปลี่ยนไป **Groq/Gemini** โดยตั้ง `AI_BASE_URL` + `AI_MODEL` (ดูหัวคอมเมนต์ใน [ai_sentiment.py](ai_sentiment.py))

### 4️⃣ ตั้ง GitHub Secrets
repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | จำเป็น |
|---|---|
| `TWELVEDATA_API_KEY` | ✅ |
| `TELEGRAM_BOT_TOKEN` | ✅ |
| `TELEGRAM_CHAT_ID` | ✅ |
| `DEEPSEEK_API_KEY` | ⭐ (ใส่ถ้าอยากได้บรรทัด AI) |

จากนั้นแท็บ **Actions → trading-signals → Run workflow** เพื่อทดสอบ — หลังจากนี้รันเองตามเวลา ✅

### 5️⃣ (ไม่บังคับ) Dashboard บน Vercel
ไป https://vercel.com → ล็อกอินด้วย GitHub → **Add New → Project** → import repo นี้ → **Deploy**
(ไม่ต้องตั้ง Environment Variables — หน้าเว็บดึง `signals.json` จาก GitHub raw)

---

## 💻 รันบนเครื่องตัวเอง (ทดสอบ)
```bash
pip install -r requirements.txt
cp .env.example .env          # ใส่คีย์ในไฟล์ .env
set -a && source .env && set +a && python3 main.py
```
ถ้าไม่ตั้งช่องทางส่ง โปรแกรมจะ **พิมพ์ข้อความออกจอ** ให้เห็นหน้าตาสัญญาณ

---

## 🧪 Backtest (วัดผลจริง)
```bash
TWELVEDATA_API_KEY=xxx python3 backtest.py             # ผลรวม Win rate / กำไร / Drawdown
TWELVEDATA_API_KEY=xxx python3 backtest_confidence.py  # แยกผลตามระดับ Confidence
```
**ผลล่าสุด (ตามจริง):** กลยุทธ์ขาดทุน — รวม ~−75%, Win rate 31.5%, Profit Factor 0.79 (ต่ำกว่าจุดคุ้มทุน), ซื้อถือเฉยๆ ชนะ
👉 **อย่าใช้เทรดด้วยเงินจริง** — เป็นโครงให้ต่อยอด/ศึกษา ควรปรับกลยุทธ์ + backtest ใหม่ก่อน

---

## ⚙️ ปรับแต่ง
| อยากทำอะไร | แก้ที่ไหน |
|---|---|
| เพิ่ม/ลดเหรียญ | `SYMBOL_MAP` ใน [data.py](data.py) + `SYMBOLS` ใน [main.py](main.py) |
| เปลี่ยน timeframe | `interval` ใน [data.py](data.py) + cron ใน workflow |
| ปรับเงื่อนไข/น้ำหนักสัญญาณ | [strategy.py](strategy.py) |
| ส่งทุกรอบ (ไม่รอสัญญาณเปลี่ยน) | `ALWAYS_SEND: "true"` ใน workflow (ตอนนี้เปิดอยู่) |
| กลับไปใช้ LINE | เปิดคอมเมนต์ในฟังก์ชัน `send_signal` ของ [notify.py](notify.py) |

---

## 📝 หมายเหตุ
- **GitHub cron ฟรีไม่ตรงเวลา** — รันจริงทุก ~2-3 ชม. (ไม่ใช่ทุกชั่วโมงเป๊ะ) อยากตรงเป๊ะต้องใช้ตัวกระตุ้นภายนอก เช่น cron-job.org
- repo เงียบเกิน 60 วัน GitHub จะปิด schedule (push อะไรเข้าไปก็กลับมาทำงาน)
- บอท commit `state.json` + `signals.json` กลับเข้า repo ทุกรอบ (มี `.gitattributes` แก้ conflict ให้อัตโนมัติ) — ปกติไม่ต้องแตะ
