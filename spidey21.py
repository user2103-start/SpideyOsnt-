import os, requests, json, asyncio
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
TOKEN = "8772935900:AAHKNkv3MtEfSqubU1UZEp2zLyqqKAi0XSU"
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
    return {
        "users": {}, 
        "bot_status": True, 
        "channels": [{"chat_id": "-1003767136934", "link": "https://t.me/+skVu9tSSuccyYTQ1"}],
        "search_limit": 100,
        "total_searches": 0
    }

def save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

db = load_db()

# =============== HELPERS & FORMATTERS =============== #
async def check_subs(user_id, bot):
    if user_id == ADMIN_ID: return True
    for c in db.get("channels", []):
        try:
            m = await bot.get_chat_member(c["chat_id"], user_id)
            if m.status in ['left', 'kicked']: return False
        except: continue
    return True

def smart_format(data, indent=0):
    report = ""
    prefix = "  " * indent
    if isinstance(data, list):
        for i, item in enumerate(data):
            report += f"\n{prefix}📍 ITEM {i+1}:\n" + smart_format(item, indent + 1)
    elif isinstance(data, dict):
        for k, v in data.items():
            if v in [None, "N/A", "None", "False", "", "null"]: continue
            key_name = k.replace("_", " ").title()
            if isinstance(v, (dict, list)):
                report += f"{prefix}🔹 {key_name}:\n" + smart_format(v, indent + 1)
            else:
                report += f"{prefix}🔹 {key_name}: `{v}`\n"
    else: report += f"{prefix}🔸 {data}\n"
    return report

def split_message(text, limit=3800):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

# =============== HANDLERS =============== #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db["users"][str(user.id)] = {"name": user.first_name, "username": user.username or "N/A"}
    save_db(db)

    if not await check_subs(user.id, context.bot):
        btns = [[InlineKeyboardButton("📢 Join Channel", url=c["link"])] for c in db["channels"]]
        btns.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")])
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption="🚫 Access Denied! Join channels first.", reply_markup=InlineKeyboardMarkup(btns))
        return

    welcome_text = (
        "🔥 SPIDEYOSINT OSINT BOT 🔥\n\n"
        f"Namaste {user.first_name} 👋\n\n"
        "🇮🇳 POWERED BY SPIDEYOSINT 💀\n"
        "═══════════════════════\n"
        "🚀 ADVANCED OSINT TOOL\n"
        "⚡ MULTIPLE API INTEGRATED\n"
        "💀 USE WISELY\n"
        "═══════════════════════\n\n"
        "📌 COMMANDS:\n"
        "/num <number> - Mobile number lookup\n"
        "/family <aadhaar/ration> - Family lookup\n"
        "/tg <telegram_id> - Telegram ID lookup\n\n"
        "⚠️ LIMITED TIME API\n"
        "👑 DEVELOPED BY SPIDEYOSINT"
    )
    await update.message.reply_photo(photo=WELCOME_IMAGE, caption=welcome_text)

async def handle_osint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["bot_status"] and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🔴 Bot is currently Offline.")
        return
    
    if db["total_searches"] >= db["search_limit"]:
        db["bot_status"] = False; save_db(db)
        await update.message.reply_text("🚫 Search Limit Reached! Bot Auto-Off.")
        return

    cmd = update.message.text.split()[0][1:]
    if not context.args:
        await update.message.reply_text(f"❌ Usage: `/{cmd} <input>`")
        return
    
    val = context.args[0]
    status_msg = await update.message.reply_text(f"🔄 Searching {cmd.upper()}...")
    
    try:
        p = {'key': API_KEYS[cmd], ('number' if cmd=='num' else 'id' if cmd=='tg' else 'term'): val}
        r = requests.get(API_URLS[cmd], params=p, timeout=30).json()
        final_data = r.get('results', r.get('result', r.get('data', r)))
        
        if final_data:
            db["total_searches"] += 1; save_db(db)
            report = smart_format(final_data)
            output = f"🔍 {cmd.upper()} RESULT:\n{report}"
            await status_msg.delete()
            
            # --- FIX: Message Splitting for Large Data ---
            parts = split_message(output)
            for part in parts:
                try:
                    await update.message.reply_text(part, parse_mode='Markdown')
                except:
                    # Fallback for special characters that break Markdown
                    await update.message.reply_text(part)
            # ---------------------------------------------
        else:
            await status_msg.edit_text("❌ No data found.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

# =============== ADMIN PANEL (VERTICAL & COLORFUL) =============== #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    st = "🟢 ON" if db["bot_status"] else "🔴 OFF"
    total_u = len(db["users"])
    
    kb = [
        [InlineKeyboardButton(f"🤖 Bot Status: {st}", callback_data="toggle")],
        [InlineKeyboardButton(f"👥 Total Users: {total_u}", callback_data="none")],
        [InlineKeyboardButton("👤 View User Details", callback_data="u_list")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="bc")],
        [InlineKeyboardButton("🔗 Add/Update Channel", callback_data="chan")],
        [InlineKeyboardButton(f"📉 Search Limit: {db['search_limit']}", callback_data="lim")]
    ]
    await update.message.reply_text("🛠 **SPIDEY ADMIN CONSOLE**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "toggle":
        db["bot_status"] = not db["bot_status"]; save_db(db)
        await admin_panel(q.message, context) # Refresh
    elif q.data == "u_list":
        u_text = "👥 **USER LIST:**\n" + "\n".join([f"🔹 `{k}` | {v['name']}" for k,v in db['users'].items()])
        for part in split_message(u_text): await q.message.reply_text(part, parse_mode='Markdown')
    elif q.data == "bc":
        context.user_data['mode'] = 'bc'
        await q.message.reply_text("📢 Send broadcast text.")
    elif q.data == "chan":
        context.user_data['mode'] = 'chan'
        await q.message.reply_text("🔗 Send Channel ID and Link (Format: `ID|Link`)")
    elif q.data == "lim":
        context.user_data['mode'] = 'lim'
        await q.message.reply_text("📉 Send new search limit number.")

async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or 'mode' not in context.user_data: return
    mode = context.user_data['mode']; val = update.message.text
    
    if mode == 'bc':
        for uid in db["users"].keys():
            try: await context.bot.send_message(uid, f"📢 **ADMIN:**\n{val}")
            except: pass
        await update.message.reply_text("✅ Sent.")
    elif mode == 'chan':
        try:
            cid, link = val.split('|')
            db["channels"] = [{"chat_id": cid.strip(), "link": link.strip()}]
            save_db(db); await update.message.reply_text("✅ Channel Updated.")
        except:
            await update.message.reply_text("❌ Format error! Use ID|Link")
    elif mode == 'lim':
        try:
            db["search_limit"] = int(val); db["total_searches"] = 0
            save_db(db); await update.message.reply_text(f"✅ Limit set to {val}.")
        except:
            await update.message.reply_text("❌ Enter a valid number.")
    
    context.user_data.clear()

# =============== RUNNER =============== #
async def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler(["num", "family", "tg"], handle_osint))
    app.add_handler(CallbackQueryHandler(cb_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_input))
    Thread(target=run_flask, daemon=True).start()
    async with app:
        await app.initialize(); await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    try: asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit): pass
