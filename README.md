# Cron-Signal 📊

ยิงสัญญาณ **Long / Short** ของ **BTC, ETH, XAU (ทองคำ)** บน **Timeframe 1 ชั่วโมง** เข้า **LINE** อัตโนมัติทุกชั่วโมง — **ฟรีทุกขั้นตอน**

- ข้อมูลราคา: [Twelve Data](https://twelvedata.com/) (ฟรี 800 req/วัน)
- แจ้งเตือน: LINE Messaging API (ฟรี)
- ตั้งเวลา (Cron): GitHub Actions (ฟรี ไม่ต้องเปิดเครื่องทิ้งไว้)

> ⚠️ สัญญาณคำนวณจากอินดิเคเตอร์ทางเทคนิค (EMA + RSI + MACD) เพื่อการศึกษา **ไม่ใช่คำแนะนำการลงทุน** เทรดมีความเสี่ยง

---

## วิธีคำนวณสัญญาณ
ให้คะแนนจาก 4 ปัจจัยบนแท่ง 1H ล่าสุด:
| ปัจจัย | ขึ้น (+1) | ลง (−1) |
|---|---|---|
| เทรนด์ | EMA20 > EMA50 | EMA20 < EMA50 |
| ทิศทางหลัก | MACD line > 0 | MACD line < 0 |
| โมเมนตัม | MACD hist > 0 | MACD hist < 0 |
| แรงซื้อ/ขาย | RSI ≥ 55 | RSI ≤ 45 |

คะแนนรวม **≥ +2 = 🟢 LONG**, **≤ −2 = 🔴 SHORT**, อื่น ๆ = **⚪ NEUTRAL**
พร้อมแนะนำ TP/SL จาก ATR (ความผันผวน)

---

## ติดตั้ง 4 ขั้นตอน

### 1️⃣ คีย์ข้อมูลราคา (Twelve Data)
1. สมัครฟรีที่ https://twelvedata.com/ → ยืนยันอีเมล
2. ไปหน้า **API Keys** → คัดลอก key

### 2️⃣ LINE Messaging API
1. เข้า https://developers.line.biz/console/ (ล็อกอินด้วยบัญชี LINE)
2. **Create a new provider** → ตั้งชื่ออะไรก็ได้
3. **Create a Messaging API channel** → ระบบจะสร้าง LINE Official Account ให้ฟรี
4. แท็บ **Messaging API** → เลื่อนลงหา **Channel access token (long-lived)** → กด **Issue** → คัดลอก token
5. สแกน **QR code** ของ OA นั้นด้วยมือถือ แล้ว **Add เป็นเพื่อน** (จำเป็น เพื่อให้ broadcast ส่งถึงคุณ)
6. (แนะนำ) แท็บ Messaging API → ปิด **Auto-reply messages** เพื่อไม่ให้ตอบอัตโนมัติรก

> โควต้าฟรีของ LINE มีจำกัดต่อเดือน โค้ดนี้จึง **ส่งเฉพาะตอนสัญญาณเปลี่ยน** เป็นค่าเริ่มต้น (ดู `ALWAYS_SEND`)

### 3️⃣ อัปขึ้น GitHub + ตั้ง Secrets
```bash
cd /Users/khr_panu/Documents/Cron-Signal
git init && git add . && git commit -m "init cron-signal"
gh repo create cron-signal --private --source=. --push   # หรือสร้าง repo เองแล้ว push
```
ใน repo บน GitHub → **Settings → Secrets and variables → Actions → New repository secret** เพิ่ม:
| ชื่อ Secret | ค่า |
|---|---|
| `TWELVEDATA_API_KEY` | คีย์จากข้อ 1 |
| `LINE_CHANNEL_ACCESS_TOKEN` | token จากข้อ 2 |
| `LINE_TO` | *(ไม่ต้องใส่ก็ได้ — เว้นว่าง = broadcast)* |

### 4️⃣ เปิดใช้งาน
ไปแท็บ **Actions** ของ repo → เลือก workflow **trading-signals** → กด **Run workflow** เพื่อทดสอบ
หลังจากนี้มันจะรันเองทุกชั่วโมงโดยอัตโนมัติ ✅

---

## รันบนเครื่องตัวเองก่อนได้ (ทดสอบ)
```bash
pip install -r requirements.txt
cp .env.example .env        # ใส่คีย์ลงในไฟล์ .env

# โหลด .env แล้วรัน
export $(grep -v '^#' .env | xargs)
python main.py
```
ถ้ายังไม่ใส่ LINE token โปรแกรมจะ **พิมพ์ข้อความออกจอแทน** ให้เห็นหน้าตาสัญญาณก่อน

### ตั้ง Cron บน Mac (ทางเลือก แทน GitHub Actions)
```cron
5 * * * * cd /Users/khr_panu/Documents/Cron-Signal && /usr/bin/python3 main.py >> cron.log 2>&1
```
(ข้อเสีย: เครื่องต้องเปิดตลอด — GitHub Actions จึงสะดวกกว่า)

---

## ปรับแต่ง
| อยากทำอะไร | แก้ที่ไหน |
|---|---|
| เพิ่ม/ลดเหรียญ | `SYMBOL_MAP` ใน [data.py](data.py) + `SYMBOLS` ใน [main.py](main.py) |
| เปลี่ยน timeframe | `interval="1h"` ใน [data.py](data.py) และ cron ใน workflow |
| ปรับเงื่อนไขสัญญาณ | [strategy.py](strategy.py) |
| ส่งทุกชั่วโมง (ไม่รอเปลี่ยน) | ตั้ง `ALWAYS_SEND=true` |
| เปลี่ยนข้อความ | `format_block()` ใน [main.py](main.py) |

---

## หมายเหตุ
- GitHub Actions cron อาจดีเลย์ได้ในช่วงคนใช้เยอะ และจะ **หยุดทำงานอัตโนมัติถ้า repo ไม่มีการเคลื่อนไหว 60 วัน** (push อะไรเข้าไปก็กลับมาทำงาน)
- โค้ดนี้ commit `state.json` กลับเข้า repo เพื่อจำสัญญาณล่าสุด — ปกติ ไม่ต้องแตะต้อง
