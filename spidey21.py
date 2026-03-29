import os, logging, requests, json, html, re, asyncio
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# =============== RENDER ALIVE SERVER =============== #
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "SPIDEYOSINT IS LIVE"

def run_flask(): 
    port = int(os.environ.get('PORT', 10000))
    app_flask.run(host='0.0.0.0', port=port)

# =============== CONFIGURATION =============== #
TOKEN = "8772935900:AAFAWA70z_pvqphM1xRbRy5efuCEpvNmbN4"
ADMIN_ID = 6593129349
DB_FILE = "bot_settings.json"
WELCOME_IMAGE = "https://i.postimg.cc/6381GR85/IMG-20260320-165905-146.jpg"

API_URLS = {
    'num': "https://ayaanmods.site/number.php",
    'tg': "https://ayaanmods.site/tg2num.php",
    'family': "https://ayaanmods.site/family.php"
}
API_KEYS = {'num': 'annonymous', 'tg': 'annonymoustgtonum', 'family': 'annonymousfamily'}
FORCE_CHANNELS = [{"chat_id": "-1003767136934", "link": "https://t.me/+skVu9tSSuccyYTQ1"}]

# =============== DATABASE SYSTEM =============== #
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"users": {}, "bot_status": True}

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

db = load_db()

# =============== HELPERS =============== #
async def check_subs(user_id, bot):
    if user_id == ADMIN_ID: return True
    for c in FORCE_CHANNELS:
        try:
            m = await bot.get_chat_member(c["chat_id"], user_id)
            if m.status in ['left', 'kicked']: return False
        except: return False
    return True

# =============== HANDLERS =============== #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    
    # User info save in "Database"
    db["users"][uid] = {"name": user.first_name, "username": f"@{user.username}" if user.username else "N/A"}
    save_db(db)

    if not db["bot_status"] and user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bot is currently OFF by Admin.")
        return

    if not await check_subs(user.id, context.bot):
        btns = [[InlineKeyboardButton("📢 Join Channel", url=c["link"])] for c in FORCE_CHANNELS]
        btns.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")])
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption="🚫 Pehle Channel Join Karo!", reply_markup=InlineKeyboardMarkup(btns))
        return

    greet = (
        f"🔥 SPIDEYOSINT OSINT BOT 🔥\n\n"
        f"Namaste {user.first_name} 👋\n\n"
        f"🇮🇳 POWERED BY SPIDEYOSINT 💀\n"
        f"═══════════════════════\n"
        f"🚀 ADVANCED OSINT TOOL\n"
        f"⚡ MULTIPLE API INTEGRATED\n"
        f"💀 USE WISELY\n"
        f"═══════════════════════\n\n"
        f"📌 COMMANDS:\n"
        f"/num <number> Mobile number lookup\n"
        f"/family <aadhaar>- Family lookup\n"
        f"/tg <telegram_id>- Telegram_ID lookup\n\n"
        f"⚠️ LIMITED TIME API\n"
        f"👑 DEVELOPED BY SPIDEYOSINT"
    )
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
        r = requests.get(API_URLS[cmd], params=p, timeout=20).json()
        data = r.get('result', r.get('data'))
        if data:
            await msg.delete()
            res = f"🔍 {cmd.upper()} RESULT:\n\n<code>{json.dumps(data, indent=2)}</code>"
            await update.message.reply_text(res, parse_mode='HTML')
        else: await msg.edit_text("❌ No data found.")
    except: await msg.edit_text("❌ API Error or Timeout.")

# =============== ADMIN PANEL =============== #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    st = "🟢 ON" if db["bot_status"] else "🔴 OFF"
    kb = [
        [InlineKeyboardButton(f"Bot Status: {st}", callback_data="toggle")],
        [InlineKeyboardButton("👥 User List", callback_data="list"), InlineKeyboardButton("📢 Broadcast", callback_data="bc")]
    ]
    await update.message.reply_text("🔐 ADMIN CONTROL", reply_markup=InlineKeyboardMarkup(kb))

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "toggle":
        db["bot_status"] = not db["bot_status"]; save_db(db)
        await q.message.edit_text("✅ Status Updated! Check /admin.")
    elif q.data == "list":
        u_list = "👥 **LAST 20 USERS:**\n\n"
        for k, v in list(db["users"].items())[-20:]:
            u_list += f"▪️ {v['name']} ({v['username']}) -> `{k}`\n"
        await q.message.reply_text(u_list, parse_mode='Markdown')
    elif q.data == "bc":
        context.user_data['mode'] = 'bc'
        await q.message.reply_text("📢 Send message for broadcast (or /cancel)")
    elif q.data == "check_sub":
        if await check_subs(q.from_user.id, context.bot):
            await q.edit_message_text("✅ Access Granted! Use /start")
        else: await q.answer("❌ Join pehle!", show_alert=True)

async def admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or 'mode' not in context.user_data: return
    if update.message.text == "/cancel": context.user_data.clear(); return
    
    count = 0
    for uid in db["users"].keys():
        try: await context.bot.send_message(uid, update.message.text); count += 1
        except: pass
    await update.message.reply_text(f"✅ Sent to {count} users."); context.user_data.clear()

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
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass
