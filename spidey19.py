import os
import logging
import requests
import json
import html
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# =============== CONFIGURATION =============== #
TOKEN = "8772935900:AAFAWA70z_pvqphM1xRbRy5efuCEpvNmbN4"
ADMIN_ID = 6593129349
CHANNEL_OWNER_ID = 6593129349

WELCOME_IMAGE = "https://i.postimg.cc/6381GR85/IMG-20260320-165905-146.jpg"

API_NUM_URL = "https://ayaanmods.site/number.php"
API_TG_URL = "https://ayaanmods.site/tg2num.php"
API_ADHAAR_URL = "https://ayaanmods.site/family.php"
API_IMG_URL = "https://ayaanmods.site/aiimage.php"

API_KEY_NUM = "annonymous"
API_KEY_TG = "annonymoustgtonum"
API_KEY_ADHAAR = "annonymousfamily"
API_KEY_IMG = "annonymousai"

FORCE_CHANNELS = [{"chat_id": "-1003767136934", "link": "https://t.me/+skVu9tSSuccyYTQ1"}]

user_db = {} 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# =============== TAG FIXER & SPLITTER =============== #
def close_open_tags(text):
    for tag in ['b', 'code', 'u', 'i']:
        opened = len(re.findall(f'<{tag}>', text))
        closed = len(re.findall(f'</{tag}>', text))
        if opened > closed:
            text += f'</{tag}>' * (opened - closed)
    return text

async def send_safe_parts(update, text: str):
    MAX_LEN = 3800
    target = update.message if hasattr(update, 'message') and update.message else update.callback_query.message
    
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
            if not value or str(value).strip().lower() in ['none', 'null', 'false', 'invalid umang response']: continue
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}<b>{clean_key}:</b>")
                lines.append(smart_format(value, indent + 1))
            else:
                safe_val = html.escape(str(value))
                lines.append(f"{prefix}🔹 <b>{clean_key}:</b> <code>{safe_val}</code>")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(smart_format(item, indent + 1))
            else:
                lines.append(f"{prefix}▪️ {html.escape(str(item))}")
    return "\n".join(lines)

def format_api_response(api_data, title, icon):
    try:
        raw_results = api_data.get('result', api_data.get('data', []))
        if not raw_results: return None
        body = smart_format(raw_results)
        return f"{icon} {title} FOUND {icon}\n━━━━━━━━━━━━━━━━━━━━━━\n\n{body}"
    except: return None

# =============== HANDLERS =============== #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    if uid not in user_db:
        user_db[uid] = {'name': user.first_name, 'id': user.id, 'last_used': datetime.now().strftime("%Y-%m-%d")}
    
    ok, channels = await check_force_subscribe(user.id, context.bot)
    if not ok:
        await update.message.reply_photo(photo=WELCOME_IMAGE, caption=f"🚫 ACCESS DENIED 🚫\n\nBhai {user.first_name}, pehle channel join kar! 🔥", reply_markup=get_subscribe_keyboard(channels))
        return

    # AESTHETIC VERTICAL START MESSAGE
    start_text = (
        f"🔥 SPIDEYOSINT OSINT BOT 🔥\n\n"
        f"Namaste {user.first_name} 👋\n\n"
        f"🇮🇳 POWERED BY SPIDEYOSINT 💀\n"
        f"═══════════════════════\n"
        f"🚀 ADVANCED OSINT TOOL\n"
        f"⚡ MULTIPLE API INTEGRATED\n"
        f"💀 USE WISELY\n"
        f"═══════════════════════\n\n"
        f"📌 COMMANDS:\n"
        f"/num <number> - Mobile number lookup (all results)\n"
        f"/family <aadhaar/ration> - Family/Aadhaar lookup\n"
        f"/tg <telegram_id> - Telegram ID lookup\n\n\n"
        f"⚠️ LIMITED TIME API\n"
        f"👑 DEVELOPED BY SPIDEYOSINT"
    )
    await update.message.reply_photo(photo=WELCOME_IMAGE, caption=start_text)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    # VERTICAL BUTTONS FOR ADMIN
    keyboard = [
        [InlineKeyboardButton("📊 Bot Status", callback_data="adm_status")],
        [InlineKeyboardButton("👥 Total Users", callback_data="adm_users")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_bc")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="adm_add")],
        [InlineKeyboardButton("🔄 Refresh Force Subs", callback_data="adm_ref")]
    ]
    await update.message.reply_text(f"🔐 ADMIN PANEL\n\nTotal Registered: {len(user_db)}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    if uid in user_db: user_db[uid]['last_used'] = datetime.now().strftime("%Y-%m-%d")
    
    cmd = update.message.text.split()[0][1:]
    if not context.args: await update.message.reply_text("❌ Input do!"); return
    val = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching {cmd.upper()}...")
    
    res = None
    try:
        if cmd == 'num': r = requests.get(API_NUM_URL, params={'key':API_KEY_NUM, 'number':val}, timeout=20).json(); res = format_api_response(r, "NUMBER", "🔍")
        elif cmd == 'family': r = requests.get(API_ADHAAR_URL, params={'key':API_KEY_ADHAAR, 'term':val}, timeout=20).json(); res = format_api_response(r, "FAMILY", "👨‍👩‍👧‍👦")
        elif cmd == 'tg': r = requests.get(API_TG_URL, params={'key':API_KEY_TG, 'id':val}, timeout=20).json(); res = format_api_response(r, "TELEGRAM", "📱")
    except: res = None

    if res:
        await msg.delete()
        await send_safe_parts(update, res + "\n\n✅ POWERED BY SPIDEYOSINT")
    else:
        await msg.edit_text("❌ No results found.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "adm_status":
        await query.edit_message_text(f"🤖 BOT STATUS\n\n✅ Status: Running\n👥 Total Users: {len(user_db)}\n🔗 Channels: {len(FORCE_CHANNELS)}")
    elif query.data == "adm_users":
        if not user_db: await query.edit_message_text("📭 No users yet."); return
        ulist = "👥 BOT USERS LIST\n━━━━━━━━━━━━━━\n\n"
        for uid, info in user_db.items():
            ulist += f"👤 Name: {info['name']}\n🆔 ID: <code>{info['id']}</code>\n\n"
        await send_safe_parts(update, ulist)
    elif query.data == "adm_bc":
        context.user_data['mode'] = 'bc'
        await query.message.reply_text("📢 Send message for broadcast (or /cancel).")
    elif query.data == "adm_add":
        context.user_data['mode'] = 'add'
        await query.message.reply_text("➕ Format: chat_id|link")
    elif query.data == "adm_ref":
        await query.answer("🔄 Force Subscribe List Refreshed!", show_alert=True)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    if not mode or update.effective_user.id != ADMIN_ID: return
    text = update.message.text
    if text == "/cancel": context.user_data.clear(); await update.message.reply_text("❌ Cancelled"); return

    if mode == 'bc':
        count = 0
        for uid in user_db.keys():
            try: await context.bot.send_message(uid, text); count += 1
            except: pass
        await update.message.reply_text(f"✅ Broadcast Done: {count} users")
    elif mode == 'add':
        try:
            cid, link = text.split('|')
            FORCE_CHANNELS.append({"chat_id": cid.strip(), "link": link.strip()})
            await update.message.reply_text("✅ Added!")
        except: await update.message.reply_text("❌ Invalid format")
    context.user_data.clear()

async def check_force_subscribe(user_id, bot):
    if user_id == CHANNEL_OWNER_ID: return True, []
    not_sub = []
    for c in FORCE_CHANNELS:
        try:
            m = await bot.get_chat_member(c["chat_id"], user_id)
            if m.status in ['left', 'kicked']: not_sub.append(c)
        except: not_sub.append(c)
    return len(not_sub) == 0, not_sub

def get_subscribe_keyboard(channels):
    btns = [[InlineKeyboardButton(f"📢 Join {i+1}", url=c["link"])] for i, c in enumerate(channels)]
    btns.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")])
    return InlineKeyboardMarkup(btns)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler(["num", "family", "tg"], handle_commands))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("✅ Bot is Live with Aesthetic Vertical UI!")
    app.run_polling()

if __name__ == "__main__": main()