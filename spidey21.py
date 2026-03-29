import os, logging, requests, json, html, re, asyncio
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# =============== RENDER ALIVE SERVER =============== #
app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "SPIDEYOSINT PRO ADMIN IS LIVE"

def run_flask(): 
    # Render ke liye port fix
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

# =============== SETTINGS & DATABASE =============== #
def load_settings():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"users": {}, "bot_status": True, "search_limit": 100}

def save_settings(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

db = load_settings()

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
    db["users"][uid] = {"name": user.first_name, "username": f"@{user.username}" if user.username else "N/A"}
    save_settings(db)

    if not db["bot_status"] and user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bot is under maintenance.")
        return

    if not await check_subs(user.id, context.bot):
        btns = [[InlineKeyboardButton("📢 Join Channel", url=c["link"])] for c in FORCE_CHANNELS]
        btns.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")])
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption="🚫 Join channel first!", reply_markup=InlineKeyboardMarkup(btns))
        return

    greet = (f"🔥 SPIDEYOSINT OSINT BOT 🔥\n\nNamaste {user.first_name} 👋\n\n"
             "🇮🇳 POWERED BY SPIDEYOSINT 💀\n═══════════════════════\n"
             "🚀 ADVANCED OSINT TOOL\n⚡ MULTIPLE API INTEGRATED\n💀 USE WISELY\n"
             "═══════════════════════\n\n📌 COMMANDS:\n/num <number>\n/family <aadhaar>\n/tg <id>")
    await update.message.reply_photo(photo=WELCOME_IMAGE, caption=greet)

async def handle_osint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["bot_status"] and update.effective_user.id != ADMIN_ID: return
    cmd = update.message.text.split()[0][1:]
    if not context.args: await update.message.reply_text("❌ Input missing!"); return
    
    val = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching {cmd.upper()}...")
    try:
        p = {'key': API_KEYS[cmd], ('number' if cmd=='num' else 'id' if cmd=='tg' else 'term'): val}
        r = requests.get(API_URLS[cmd], params=p, timeout=20).json()
        data = r.get('result', r.get('data'))
        if data:
            await msg.delete()
            await update.message.reply_text(f"🔍 {cmd.upper()} RESULT:\n\n<code>{json.dumps(data, indent=2)}</code>", parse_mode='HTML')
        else: await msg.edit_text("❌ No data found.")
    except: await msg.edit_text("❌ API Error.")

# =============== ADMIN PANEL =============== #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kb = [[InlineKeyboardButton(f"Status: {'🟢 ON' if db['bot_status'] else '🔴 OFF'}", callback_data="toggle_bot")],
          [InlineKeyboardButton("👥 User List", callback_data="view_users"), InlineKeyboardButton("📢 Broadcast", callback_data="prep_bc")]]
    await update.message.reply_text("🔐 ADMIN PANEL", reply_markup=InlineKeyboardMarkup(kb))

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "toggle_bot":
        db["bot_status"] = not db["bot_status"]; save_settings(db)
        await q.message.edit_text("🔄 Status Updated. Use /admin to see changes.")
    elif q.data == "view_users":
        txt = "👥 USERS:\n" + "\n".join([f"▪️ {v['name']} ({k})" for k,v in list(db['users'].items())[-20:]])
        await q.message.reply_text(txt[:4000])
    elif q.data == "prep_bc":
        context.user_data['action'] = 'bc'
        await q.message.reply_text("📢 Send broadcast text (or /cancel)")
    elif q.data == "check_sub":
        if await check_subs(q.from_user.id, context.bot): await q.edit_message_text("✅ Granted! Use /start")
        else: await q.answer("❌ Join first!", show_alert=True)

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or 'action' not in context.user_data: return
    if update.message.text == "/cancel": context.user_data.clear(); return
    
    for uid in db["users"].keys():
        try: await context.bot.send_message(uid, update.message.text)
        except: pass
    await update.message.reply_text("✅ Broadcast Sent."); context.user_data.clear()

# =============== RUNNER (FIXED FOR PYTHON 3.14) =============== #
async def main():
    # Application setup
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler(["num", "family", "tg"], handle_osint))
    app.add_handler(CallbackQueryHandler(callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))

    # Start Flask in a separate thread
    Thread(target=run_flask, daemon=True).start()

    # Manual loop management for Render/Python 3.14
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        print("✅ BOT IS LIVE!")
        # Keep the loop running
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        passNGS & DATABASE =============== #
def load_settings():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"users": {}, "bot_status": True, "search_limit": 100}

def save_settings(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

db = load_settings()

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
    
    # Save user info
    db["users"][uid] = {"name": user.first_name, "username": f"@{user.username}" if user.username else "No Username"}
    save_settings(db)

    if not db["bot_status"] and user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bot is currently under maintenance by Admin.")
        return

    if not await check_subs(user.id, context.bot):
        btns = [[InlineKeyboardButton("📢 Join Channel", url=c["link"])] for c in FORCE_CHANNELS]
        btns.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_sub")])
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption="🚫 Pehle Channel Join Karo!", reply_markup=InlineKeyboardMarkup(btns))
        return

    greet = (
        f"🔥 SPIDEYOSINT OSINT BOT 🔥\n\nNamaste {user.first_name} 👋\n\n"
        f"🇮🇳 POWERED BY SPIDEYOSINT 💀\n═══════════════════════\n"
        f"🚀 ADVANCED OSINT TOOL\n⚡ MULTIPLE API INTEGRATED\n💀 USE WISELY\n"
        f"═══════════════════════\n\n📌 COMMANDS:\n/num <number>\n/family <aadhaar>\n/tg <id>\n\n"
        f"⚠️ LIMITED TIME API\n👑 DEVELOPED BY SPIDEYOSINT"
    )
    await update.message.reply_photo(photo=WELCOME_IMAGE, caption=greet)

async def handle_osint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["bot_status"] and update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bot is OFF by Admin."); return
    
    cmd = update.message.text.split()[0][1:]
    if not context.args: await update.message.reply_text("❌ Input do!"); return
    
    val = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching {cmd.upper()}...")
    try:
        p = {'key': API_KEYS[cmd]}
        if cmd == 'num': p['number'] = val
        elif cmd == 'tg': p['id'] = val
        else: p['term'] = val
        
        r = requests.get(API_URLS[cmd], params=p, timeout=25).json()
        data = r.get('result', r.get('data'))
        if data:
            await msg.delete()
            await update.message.reply_text(f"🔍 {cmd.upper()} RESULT:\n\n<code>{json.dumps(data, indent=2)}</code>", parse_mode='HTML')
        else: await msg.edit_text("❌ No data found.")
    except: await msg.edit_text("❌ API Error.")

# =============== PRO ADMIN PANEL =============== #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    status_text = "🟢 ON" if db["bot_status"] else "🔴 OFF"
    kb = [
        [InlineKeyboardButton(f"Bot Status: {status_text}", callback_data="toggle_bot")],
        [InlineKeyboardButton("👥 User List", callback_data="view_users"), InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="prep_bc"), InlineKeyboardButton("⚙️ Set Limit", callback_data="prep_limit")]
    ]
    await update.message.reply_text("🔐 **PRO ADMIN CONTROL**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data == "toggle_bot":
        db["bot_status"] = not db["bot_status"]
        save_settings(db)
        await admin_panel(update, context) # Refresh panel
        await q.message.delete()
    
    elif q.data == "view_users":
        u_txt = "👥 **REGISTERED USERS**\n\n"
        for uid, info in db["users"].items():
            u_txt += f"▪️ {info['name']} ({info['username']}) -> ` {uid} `\n"
        if len(u_txt) > 4000: # Split if too long
            await q.message.reply_text(u_txt[:4000], parse_mode='Markdown')
        else: await q.message.reply_text(u_txt, parse_mode='Markdown')

    elif q.data == "stats":
        await q.message.reply_text(f"📊 **BOT STATS**\n\nTotal Users: {len(db['users'])}\nBot Status: {'ACTIVE' if db['bot_status'] else 'OFFLINE'}\nSearch Limit: {db['search_limit']}")

    elif q.data == "prep_bc":
        context.user_data['action'] = 'broadcast'
        await q.message.reply_text("📢 Send the message you want to Broadcast (or /cancel)")

    elif q.data == "prep_limit":
        context.user_data['action'] = 'set_limit'
        await q.message.reply_text("⚙️ Send the new global search limit (Number only)")

    elif q.data == "check_sub":
        if await check_subs(q.from_user.id, context.bot):
            await q.edit_message_text("✅ Access Granted! Use /start")
        else: await q.answer("❌ Join pehle!", show_alert=True)

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or 'action' not in context.user_data: return
    
    action = context.user_data['action']
    text = update.message.text
    if text == "/cancel": 
        context.user_data.clear(); await update.message.reply_text("❌ Cancelled"); return

    if action == 'broadcast':
        count = 0
        for uid in db["users"].keys():
            try: await context.bot.send_message(uid, text); count += 1
            except: pass
        await update.message.reply_text(f"✅ Broadcast sent to {count} users.")
    
    elif action == 'set_limit':
        if text.isdigit():
            db["search_limit"] = int(text); save_settings(db)
            await update.message.reply_text(f"✅ Search limit updated to {text}")
        else: await update.message.reply_text("❌ Sirf number bhejo!")

    context.user_data.clear()

# =============== RUNNER =============== #
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler(["num", "family", "tg"], handle_osint))
    app.add_handler(CallbackQueryHandler(callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))
    
    Thread(target=run_flask, daemon=True).start()
    async with app:
        await app.initialize(); await app.start(); await app.updater.start_polling()
        while True: await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
