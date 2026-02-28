import matplotlib
matplotlib.use("Agg")

import requests
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time
from io import BytesIO

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8797196483:AAEhff8rGx7S_SCcNGQInnZUuNhpbGAUWXo"

CHAT_ID = None

BIST_SYMBOLS = [
"THYAO","GARAN","AKBNK","ISCTR","YKBNK","ASELS","SISE","TUPRS",
"EREGL","BIMAS","FROTO","TOASO","SASA","KOZAL","MGROS"
]

# ------------------ INDICATORS ------------------

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])

    for i in range(period, len(prices)-1):
        avg_gain = (avg_gain * (period-1) + gain[i]) / period
        avg_loss = (avg_loss * (period-1) + loss[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ------------------ ANALYSIS ------------------

def analyze_stock(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.IS?range=1y&interval=1d"
        r = requests.get(url, timeout=10)
        data = r.json()

        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        volumes = result["indicators"]["quote"][0]["volume"]

        closes = [c for c in closes if c is not None]
        volumes = [v for v in volumes if v is not None]

        if len(closes) < 200:
            return None

        closes = np.array(closes)
        volumes = np.array(volumes)

        ma50 = np.mean(closes[-50:])
        ma200 = np.mean(closes[-200:])
        rsi = calculate_rsi(closes)
        momentum = closes[-1] - closes[-20]
        volume_avg = np.mean(volumes[-30:])

        score = 0

        if closes[-1] > ma200: score += 2
        if ma50 > ma200: score += 2
        if rsi < 45: score += 2
        if momentum > 0: score += 2
        if volumes[-1] > volume_avg: score += 2

        if score >= 8:
            signal = "🔥 GÜÇLÜ AL"
        elif score >= 6:
            signal = "AL"
        else:
            signal = "BEKLE"

        return {
            "symbol": symbol,
            "score": score,
            "signal": signal,
            "closes": closes
        }

    except:
        return None

# ------------------ GRAPH ------------------

def create_chart(symbol, closes):
    plt.figure(figsize=(8,6))

    plt.subplot(2,1,1)
    plt.plot(closes[-100:])
    plt.title(f"{symbol} Fiyat")

    rsi = calculate_rsi(closes)
    plt.subplot(2,1,2)
    plt.axhline(70)
    plt.axhline(30)
    plt.plot([rsi]*100)
    plt.title("RSI")

    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)

    return buffer

# ------------------ BOT ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    await update.message.reply_text(
        "🔥 PRO BOT AKTİF\n10 saniye içinde test mesajı gelecek.\nHer gün 10:00 otomatik tarama."
    )

    context.job_queue.run_once(send_scan, 10, chat_id=CHAT_ID)
    context.job_queue.run_daily(send_scan, time=time(10,0), chat_id=CHAT_ID)

async def send_scan(context: ContextTypes.DEFAULT_TYPE):
    results = []

    for symbol in BIST_SYMBOLS:
        data = analyze_stock(symbol)
        if data:
            results.append(data)

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    top5 = results[:5]

    message = f"🔥 PRO BIST TARAMA ({datetime.now().strftime('%d-%m-%Y')})\n\n"

    for stock in top5:
        message += f"{stock['symbol']} - {stock['score']} - {stock['signal']}\n"

    await context.bot.send_message(chat_id=context.job.chat_id, text=message)

    # En iyi 1 hisseye grafik
    if top5:
        chart = create_chart(top5[0]["symbol"], top5[0]["closes"])
        await context.bot.send_photo(chat_id=context.job.chat_id, photo=chart)

# ------------------ RUN ------------------

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("🔥 PRO MASTER BOT ÇALIŞIYOR...")
app.run_polling()