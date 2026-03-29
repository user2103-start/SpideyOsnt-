import os
import logging
import requests
import json
import html
import re
import asyncio
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# =============== FLASK SERVER FOR RENDER =============== #
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "SPIDEYOSINT Bot is Running 24/7!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

# =============== CONFIGURATION =============== #
TOKEN = "8772935900:AAFAWA70z_pvqphM1xRbRy5efuCEpvNmbN4"
ADMIN_ID = 6593129349
CHANNEL_OWNER_ID = 6593129349

WELCOME_IMAGE = "https://i.postimg.cc/6381GR85/IMG-20260320-165905-146.jpg"

API_NUM_URL = "https://ayaanmods.site/number.php"
API_TG_URL = "https://ayaanmods.site/tg2num.php"
API_ADHAAR_URL = "https://ayaanmods.site/family.php"

API_KEY_NUM = "annonymous"
API_KEY_TG = "annonymoustgtonum"
API_KEY_ADHAAR = "annonymousfamily"

FORCE_CHANNELS = [{"chat_id": "-1003767136934", "link": "https://t.me/+skVu9tSSuccyYTQ1"}]

user_db = {} 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# =============== TAG FIXER & SPLITTER =============== #
def close_open_tags(text):
    for tag in ['b', 'code', 'u', 'i']:
        opened = len(re.findall(f'<{tag}>', text))
        closed = len(re.findall(f'</{tag}>', text))
        if opened > closed: text += f'</{tag}>' * (opened - closed)
    return text

async def send_safe_parts(update, text: str):
    target = update.message if hasattr(update, 'message') and update.message else update.callback_query.message
    MAX_LEN = 3800
    if len(text) <= MAX_LEN:
        await target.reply_text(text, parse_mode='HTML')
        return
    lines = text.split('\n')
    current_part = ""
    for line in lines:
        if len(current_part) + len(line) + 1 > MAX_LEN:
            await target.reply_text(close_open_tags(current_part), parse_mode='HTML')
            current_part = ""
        current_part += line + "\n"
    if current_part:
        await target.reply_text(close_open_tags(current_part), parse_mode='HTML')

# =============== FORMATTER =============== #
def smart_format(data, indent=0):
    lines = []
    prefix = "  " * indent
    if isinstance(data, dict):
        for key, value in data.items():
            clean_key = key.replace('_', ' ').title()
            if not value or str(value).strip().lower() in ['none', 'null', 'false']: continue
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}<b>{clean_key}:</b>")
                lines.append(smart_format(value, indent + 1))
            else:
                lines.append(f"{prefix}🔹 <b>{clean_key}:</b> <code>{html.escape(str(value))}</code>")
    elif isinstance(data, list):
        for item in data: lines.append(smart_format(item, indent + 1))
    return "\n".join(lines)

# =============== HANDLERS =============== #
async def check_force_subscribe(user_id, bot):
    if user_id == CHANNEL_OWNER_ID: return True, []
    not_sub = []
    for c in FORCE_CHANNELS:
        try:
            m = await bot.get_chat_member(c["chat_id"], user_id)
            if m.status in ['left', 'kicked']: not_sub.append(c)
        except: not_sub.append(c)
    return len(not_sub) == 0, not_sub

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    if uid not in user_db: user_db[uid] = {'name': user.first_name, 'id': user.id}
    
    ok, channels = await check_force_subscribe(user.id, context.bot)
    if not ok:
        btns = [[InlineKeyboardButton(f"📢 Join {i+1}", url=c["link"])] for i, c in enumerate(channels)]
        btns.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")])
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption=f"🚫 ACCESS DENIED 🚫\n\nBhai {user.first_name}, pehle channel join kar!", reply_markup=InlineKeyboardMarkup(btns))
        return

    start_text = (
        f"🔥 SPIDEYOSINT OSINT BOT 🔥\n\nNamaste {user.first_name} 👋\n\n"
        f"🇮🇳 POWERED BY SPIDEYOSINT 💀\n═══════════════════════\n"
        f"🚀 ADVANCED OSINT TOOL\n⚡ MULTIPLE API INTEGRATED\n💀 USE WISELY\n"
        f"═══════════════════════\n\n📌 COMMANDS:\n/num <number>\n/family <aadhaar>\n/tg <id>\n\n"
        f"⚠️ LIMITED TIME API\n👑 DEVELOPED BY SPIDEYOSINT"
    )
    await update.message.reply_photo(photo=WELCOME_IMAGE, caption=start_text)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("📊 Bot Status", callback_data="adm_status")],
        [InlineKeyboardButton("👥 Total Users", callback_data="adm_users")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="adm_add")]
    ]
    await update.message.reply_text(f"🔐 ADMIN PANEL\n\nRegistered: {len(user_db)}", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "adm_status":
        await query.edit_message_text(f"🤖 STATUS: Running\n👥 Users: {len(user_db)}\n📢 Channels: {len(FORCE_CHANNELS)}")
    elif query.data == "adm_users":
        ulist = "👥 USER LIST:\n\n"
        for uid, info in user_db.items(): ulist += f"👤 {info['name']} | <code>{uid}</code>\n"
        await send_safe_parts(update, ulist)
    elif query.data == "adm_bc":
        context.user_data['mode'] = 'bc'
        await query.message.reply_text("📢 Send broadcast message (or /cancel)")
    elif query.data == "adm_add":
        context.user_data['mode'] = 'add'
        await query.message.reply_text("➕ Send: chat_id|link")
    elif query.data == "check_subscription":
        ok, _ = await check_force_subscribe(query.from_user.id, context.bot)
        if ok: await query.edit_message_text("✅ Access Granted! Use /start");
        else: await query.answer("❌ Join karo pehle!", show_alert=True)

async def handle_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.split()[0][1:]
    if not context.args: await update.message.reply_text("❌ Input do!"); return
    val = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching {cmd.upper()}...")
    try:
        if cmd == 'num': r = requests.get(API_NUM_URL, params={'key':API_KEY_NUM, 'number':val}).json()
        elif cmd == 'family': r = requests.get(API_ADHAAR_URL, params={'key':API_KEY_ADHAAR, 'term':val}).json()
        elif cmd == 'tg': r = requests.get(API_TG_URL, params={'key':API_KEY_TG, 'id':val}).json()
        body = smart_format(r.get('result', r.get('data', {})))
        await msg.delete()
        if body: await send_safe_parts(update, f"🔍 {cmd.upper()} RESULT:\n\n{body}")
        else: await update.message.reply_text("❌ No data.")
    except: await msg.edit_text("❌ API Error.")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    if not mode or update.effective_user.id != ADMIN_ID: return
    text = update.message.text
    if text == "/cancel": context.user_data.clear(); await update.message.reply_text("❌ Cancelled"); return
    if mode == 'bc':
        for uid in user_db.keys():
            try: await context.bot.send_message(uid, text)
            except: pass
        await update.message.reply_text("✅ Broadcast Sent!")
    elif mode == 'add':
        try:
            cid, link = text.split('|')
            FORCE_CHANNELS.append({"chat_id": cid.strip(), "link": link.strip()})
            await update.message.reply_text("✅ Channel Added!")
        except: await update.message.reply_text("❌ Format: chat_id|link")
    context.user_data.clear()

# =============== RUNNER =============== #
async def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler(["num", "family", "tg"], handle_commands))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    Thread(target=run_flask).start()
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True: await asyncio.sleep(10)

if __name__ == "__main__":
    try: asyncio.run(run_bot())
    except: pass
