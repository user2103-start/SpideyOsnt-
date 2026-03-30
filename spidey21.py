import os, requests, json, html, asyncio
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# =============== RENDER ALIVE SERVER =============== #
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "SPIDEYOSINT IS LIVE"
def run_flask(): 
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# =============== CONFIGURATION =============== #
TOKEN "8772935900:AAHKNkv3MtEfSqubU1UZEp2zLyqqKAi0XSU"
ADMIN_ID = 6593129349
DB_FILE = "bot_settings.json"
WELCOME_IMAGE = "https://i.postimg.cc/6381GR85/IMG-20260320-165905-146.jpg"

API_URLS = {
    'num': "https://ayaanmods.site/number.php",
    'tg': "https://ayaanmods.site/tg2num.php",
    'family': "https://ayaanmods.site/family.php"
}
API_KEYS = {'num': 'annonymous', 'tg': 'annonymoustgtonum', 'family': 'annonymousfamily'}

# =============== DATABASE SYSTEM =============== #
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"users": {}, "bot_status": True, "channels": [{"chat_id": "-1003767136934", "link": "https://t.me/+skVu9tSSuccyYTQ1"}]}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

db = load_db()

# =============== HELPERS =============== #
async def check_subs(user_id, bot):
    if user_id == ADMIN_ID: return True
    for c in db.get("channels", []):
        try:
            m = await bot.get_chat_member(c["chat_id"], user_id)
            if m.status in ['left', 'kicked']: return False
        except: continue
    return True

def format_osint_data(data):
    """JSON data ko clean vertical report mein badalne ke liye"""
    if isinstance(data, list): data = data[0]
    if not isinstance(data, dict): return str(data)
    
    report = ""
    for key, val in data.items():
        if val: # Khali fields skip karne ke liye
            clean_key = key.replace("_", " ").title()
            report += f"🔹 {clean_key}: {val}\n"
    return report

# =============== HANDLERS =============== #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    db["users"][uid] = {"name": user.first_name, "username": f"@{user.username}" if user.username else "N/A"}
    save_db(db)

    if not db["bot_status"] and user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bot is currently OFF.")
        return

    if not await check_subs(user.id, context.bot):
        btns = [[InlineKeyboardButton("📢 Join Channel", url=c["link"])] for c in db["channels"]]
        btns.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")])
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption="🚫 Pehle Channel Join Karo!", reply_markup=InlineKeyboardMarkup(btns))
        return

    greet = (f"🔥 SPIDEYOSINT OSINT BOT 🔥\n\nNamaste {user.first_name} 👋\n\n"
             "🇮🇳 POWERED BY SPIDEYOSINT 💀\n═══════════════════════\n"
             "🚀 ADVANCED OSINT TOOL\n⚡ MULTIPLE API INTEGRATED\n💀 USE WISELY\n"
             "═══════════════════════\n\n📌 COMMANDS:\n"
             "/num <number> Mobile number lookup\n"
             "/family <aadhaar>- Family lookup\n"
             "/tg <telegram_id>- Telegram_ID lookup\n\n"
             "⚠️ LIMITED TIME API\n👑 DEVELOPED BY SPIDEYOSINT")
    await update.message.reply_photo(photo=WELCOME_IMAGE, caption=greet)

async def handle_osint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["bot_status"] and update.effective_user.id != ADMIN_ID: return
    cmd = update.message.text.split()[0][1:]
    if not context.args:
        await update.message.reply_text(f"❌ Input missing! Use `/{cmd} <value>`")
        return
    
    val = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching {cmd.upper()}...")
    try:
        p = {'key': API_KEYS[cmd], ('number' if cmd=='num' else 'id' if cmd=='tg' else 'term'): val}
        r = requests.get(API_URLS[cmd], params=p, timeout=30).json()
        
        final_data = r.get('result', r.get('data', r))
        
        if final_data:
            await msg.delete()
            formatted_report = format_osint_data(final_data)
            output = f"🔍 {cmd.upper()} RESULT:\n\n{formatted_report}"
            
            # WORD LIMIT FIX: Agar result bahut bada hai toh file bana kar bhejega
            if len(output) > 4000:
                with open("result.txt", "w") as f: f.write(output)
                await update.message.reply_document(document=open("result.txt", "rb"), caption="📄 Result is too long, sending as file.")
            else:
                await update.message.reply_text(output)
        else: await msg.edit_text("❌ No data found.")
    except Exception as e: await msg.edit_text(f"❌ Error: {str(e)}")

# =============== ADMIN PANEL =============== #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    st = "🟢 ON" if db["bot_status"] else "🔴 OFF"
    kb = [
        [InlineKeyboardButton(f"Bot Status: {st}", callback_data="toggle")],
        [InlineKeyboardButton("📢 Channel Settings", callback_data="chan_set")],
        [InlineKeyboardButton("👥 User List", callback_data="list"), InlineKeyboardButton("📢 Broadcast", callback_data="bc")]
    ]
    await update.message.reply_text("🔐 ADMIN CONTROL PANEL", reply_markup=InlineKeyboardMarkup(kb))

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "toggle":
        db["bot_status"] = not db["bot_status"]; save_db(db)
        await q.message.edit_text("✅ Status Updated! Use /admin to see changes.")
    elif q.data == "chan_set":
        await q.message.reply_text("📌 Current Channels:\n" + "\n".join([c['chat_id'] for c in db['channels']]) + "\n\n(Feature to add/remove via command is active)")
    elif q.data == "list":
        u_list = "👥 **LAST 20 USERS:**\n\n" + "\n".join([f"▪️ {v['name']} -> `{k}`" for k,v in list(db["users"].items())[-20:]])
        await q.message.reply_text(u_list, parse_mode='Markdown')
    elif q.data == "bc":
        context.user_data['mode'] = 'bc'
        await q.message.reply_text("📢 Send message for broadcast (or /cancel)")
    elif q.data == "check_sub":
        if await check_subs(q.from_user.id, context.bot): await q.edit_message_text("✅ Access Granted! Use /start")
        else: await q.answer("❌ Join pehle!", show_alert=True)

async def admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or 'mode' not in context.user_data: return
    if update.message.text == "/cancel": context.user_data.clear(); return
    for uid in db["users"].keys():
        try: await context.bot.send_message(uid, update.message.text)
        except: pass
    await update.message.reply_text("✅ Broadcast Sent."); context.user_data.clear()

# =============== MAIN RUNNER =============== #
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler(["num", "family", "tg"], handle_osint))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_msg))
    Thread(target=run_flask, daemon=True).start()
    async with app:
        await app.initialize(); await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass
