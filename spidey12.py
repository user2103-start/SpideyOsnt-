import os
import logging
import requests
import json
from datetime import datetime, timedelta
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# =============== CONFIGURATION =============== #
TOKEN = os.getenv("TOKEN", "8772935900:AAFAWA70z_pvqphM1xRbRy5efuCEpvNmbN4")

# APIs
API_NUM_URL = "https://ayaanmods.site/number.php"
API_TG_URL = "https://ayaanmods.site/tg2num.php"
API_ADHAAR_URL = "https://ayaanmods.site/family.php"
API_IMG_URL = "https://ayaanmods.site/aiimage.php"

# API Keys
API_KEY_NUM = "annonymous"
API_KEY_TG = "annonymoustgtonum"
API_KEY_ADHAAR = "annonymousfamily"
API_KEY_IMG = "annonymousai"

ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "6593129349").split(",")]
CHANNEL_OWNERS = [int(id) for id in os.getenv("CHANNEL_OWNERS", "6593129349").split(",")]

FORCE_CHANNELS = [
    {"chat_id": "-1003767136934", "link": "https://t.me/+skVu9tSSuccyYTQ1"}
]

# User database (simple in-memory, upgrade to DB later)
user_db = {}

# =============== FLASK APP =============== #
app = Flask(__name__)
application = None

# =============== LOGGING =============== #
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============== FORCE SUBSCRIBE FUNCTIONS =============== #
def check_force_subscribe(user_id: int, context: CallbackContext) -> tuple:
    if user_id in CHANNEL_OWNERS:
        return True, []
    
    not_subscribed = []
    for channel in FORCE_CHANNELS:
        try:
            chat_member = context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            if chat_member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except:
            not_subscribed.append(channel)
    return len(not_subscribed) == 0, not_subscribed

def get_subscribe_keyboard(not_subscribed_channels):
    keyboard = []
    for idx, channel in enumerate(not_subscribed_channels):
        keyboard.append([InlineKeyboardButton(f"📢 Join Channel {idx+1}", url=channel["link"])])
    keyboard.append([InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")])
    return InlineKeyboardMarkup(keyboard)

# =============== FORMATTING FUNCTIONS =============== #

def format_number_response(api_data):
    """Format mobile number API response"""
    try:
        # Check if success is false
        if not api_data.get('success', True):
            return None
        
        # Remove unwanted fields
        unwanted = ['API_Developer', 'channel_name', 'channel_link', 'total_records', 
                   'success', 'owner', 'cached', 'proxyUsed', 'attempt', 'error']
        
        # Extract result
        if 'result' in api_data and isinstance(api_data['result'], list):
            data = api_data['result'][0]
        elif 'result' in api_data:
            data = api_data['result']
        else:
            data = api_data
        
        # Clean data
        clean_data = {}
        for key, value in data.items():
            if key not in unwanted and value and str(value).strip():
                clean_data[key] = value
        
        if not clean_data:
            return None
        
        formatted = "🔍 *NUMBER DETAILS FOUND* 🔍\n\n"
        for key, value in clean_data.items():
            emoji = get_emoji(key)
            formatted += f"{emoji} *{key.replace('_', ' ').title()}:* {value}\n"
        
        return formatted
    except Exception as e:
        logger.error(f"Number formatting error: {e}")
        return None

def format_adhaar_response(api_data):
    """Format Aadhaar/Family API response"""
    try:
        # Check for error
        if api_data.get('error') or not api_data.get('success', True):
            return None
        
        # Remove unwanted fields
        unwanted = ['success', 'owner', 'cached', 'proxyUsed', 'attempt', 'error']
        
        # Extract data - family API returns data in 'data' field
        if 'data' in api_data and isinstance(api_data['data'], dict):
            data = api_data['data']
        elif 'result' in api_data:
            data = api_data['result']
        else:
            data = api_data
        
        # Clean data
        clean_data = {}
        for key, value in data.items():
            if key not in unwanted and value and str(value).strip():
                clean_data[key] = value
        
        if not clean_data:
            return None
        
        formatted = "🪪 *FAMILY/AADHAAR DETAILS FOUND* 🪪\n\n"
        for key, value in clean_data.items():
            emoji = get_emoji(key)
            formatted += f"{emoji} *{key.replace('_', ' ').title()}:* {value}\n"
        
        return formatted
    except Exception as e:
        logger.error(f"Aadhaar formatting error: {e}")
        return None

def format_tg_response(api_data):
    """Format Telegram to Number API response"""
    try:
        # Check for error
        if api_data.get('error') or not api_data.get('success', True):
            return None
        
        # Remove unwanted fields
        unwanted = ['success', 'owner', 'cached', 'proxyUsed', 'attempt', 'error']
        
        # Extract data
        if 'result' in api_data:
            data = api_data['result']
        elif 'data' in api_data:
            data = api_data['data']
        else:
            data = api_data
        
        # Clean data
        clean_data = {}
        for key, value in data.items():
            if key not in unwanted and value and str(value).strip():
                clean_data[key] = value
        
        if not clean_data:
            return None
        
        formatted = "📱 *TELEGRAM DETAILS FOUND* 📱\n\n"
        for key, value in clean_data.items():
            emoji = get_emoji(key)
            formatted += f"{emoji} *{key.replace('_', ' ').title()}:* {value}\n"
        
        return formatted
    except Exception as e:
        logger.error(f"TG formatting error: {e}")
        return None

def format_image_response(api_data):
    """Format Image API response - extract image URL"""
    try:
        # Check for error
        if api_data.get('error') or not api_data.get('success', True):
            return None
        
        # Extract image URL
        if 'image_url' in api_data:
            return api_data['image_url']
        elif 'url' in api_data:
            return api_data['url']
        elif 'result' in api_data and isinstance(api_data['result'], str):
            return api_data['result']
        
        return None
    except Exception as e:
        logger.error(f"Image formatting error: {e}")
        return None

def get_emoji(key):
    emojis = {
        'name': '👤', 'father_name': '👨', 'mother_name': '👩', 'address': '📍',
        'mobile': '📱', 'phone': '📱', 'email': '📧', 'id': '🆔',
        'aadhaar': '🪪', 'dob': '🎂', 'date_of_birth': '🎂', 'gender': '⚥',
        'city': '🏙️', 'state': '🗺️', 'pincode': '📮', 'photo': '🖼️',
        'username': '👤', 'first_name': '👤', 'last_name': '👤', 'number': '📱'
    }
    return emojis.get(key, '📌')

# =============== API CALL FUNCTIONS =============== #

def search_number(number: str):
    try:
        response = requests.get(f"{API_NUM_URL}?key={API_KEY_NUM}&number={number}", timeout=15)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Number API Response: {json.dumps(data, indent=2)}")
            return format_number_response(data)
        return None
    except Exception as e:
        logger.error(f"Number API Error: {e}")
        return None

def search_adhaar(term: str):
    try:
        response = requests.get(f"{API_ADHAAR_URL}?key={API_KEY_ADHAAR}&term={term}", timeout=15)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Aadhaar API Response: {json.dumps(data, indent=2)}")
            return format_adhaar_response(data)
        return None
    except Exception as e:
        logger.error(f"Aadhaar API Error: {e}")
        return None

def search_tg(tg_id: str):
    try:
        response = requests.get(f"{API_TG_URL}?key={API_KEY_TG}&id={tg_id}", timeout=15)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"TG API Response: {json.dumps(data, indent=2)}")
            return format_tg_response(data)
        return None
    except Exception as e:
        logger.error(f"TG API Error: {e}")
        return None

def generate_image(prompt: str):
    try:
        response = requests.get(f"{API_IMG_URL}?key={API_KEY_IMG}&prompt={prompt}", timeout=30)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Image API Response: {json.dumps(data, indent=2)}")
            return format_image_response(data)
        return None
    except Exception as e:
        logger.error(f"Image API Error: {e}")
        return None

# =============== ADMIN FUNCTIONS =============== #

def get_user_stats():
    """Get bot statistics"""
    total_users = len(user_db)
    today_users = 0
    today = datetime.now().strftime("%Y-%m-%d")
    
    for user_id, data in user_db.items():
        if data.get('last_used', '').startswith(today):
            today_users += 1
    
    return total_users, today_users

async def broadcast_message(context: CallbackContext, message: str):
    """Broadcast message to all users"""
    success = 0
    failed = 0
    
    for user_id in user_db.keys():
        try:
            await context.bot.send_message(chat_id=int(user_id), text=message)
            success += 1
        except:
            failed += 1
    
    return success, failed

# =============== BOT COMMANDS =============== #

async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    # Add user to database
    if user_id not in user_db:
        user_db[user_id] = {
            'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'username': user.username,
            'first_name': user.first_name
        }
    
    is_subscribed, not_subscribed = check_force_subscribe(user.id, context)
    
    if not is_subscribed:
        keyboard = get_subscribe_keyboard(not_subscribed)
        await update.message.reply_text(
            f"🚫 ACCESS DENIED 🚫\n\nBhai {user.first_name}, pehle channel join kar! 🔥",
            reply_markup=keyboard
        )
        return
    
    welcome_text = (
        f"🔥 *SPIDEYOSINT OSINT BOT* 🔥\n\n"
        f"Namaste {user.first_name}! 👋\n\n"
        f"🇮🇳 *POWERED BY SPIDEYOSINT* 💀\n"
        f"═══════════════════════\n"
        f"🚀 *ADVANCED OSINT TOOL*\n"
        f"⚡ *MULTIPLE API INTEGRATED*\n"
        f"💀 *USE WISELY*\n"
        f"═══════════════════════\n\n"
        f"📌 *COMMANDS:*\n"
        f"/num <number> - Mobile number lookup\n"
        f"/adhaar <aadhaar/ration> - Aadhaar/Family lookup\n"
        f"/tg <telegram_id> - Telegram ID lookup\n"
        f"/img <prompt> - Generate image\n"
        f"/admin - Admin panel\n\n"
        f"⚠️ *LIMITED TIME API*\n"
        f"👑 *DEVELOPED BY SPIDEYOSINT*"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def num_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    # Update user last used
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /num <mobile_number>\nExample: /num 9876543210")
        return
    
    number = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching number: {number}...")
    
    result = search_number(number)
    if result:
        await msg.edit_text(f"{result}\n\n✅ *POWERED BY SPIDEYOSINT*", parse_mode='Markdown')
    else:
        await msg.edit_text(f"❌ No data found for: {number}\n\n👑 *SPIDEYOSINT*", parse_mode='Markdown')

async def adhaar_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /adhaar <aadhaar_number/ration_number>\nExample: /adhaar 123456789012")
        return
    
    term = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching Aadhaar/Family: {term}...")
    
    result = search_adhaar(term)
    if result:
        await msg.edit_text(f"{result}\n\n✅ *POWERED BY SPIDEYOSINT*", parse_mode='Markdown')
    else:
        await msg.edit_text(f"❌ No data found for: {term}\n\n👑 *SPIDEYOSINT*", parse_mode='Markdown')

async def tg_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /tg <telegram_id/username>\nExample: /tg 123456789")
        return
    
    tg_id = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching Telegram: {tg_id}...")
    
    result = search_tg(tg_id)
    if result:
        await msg.edit_text(f"{result}\n\n✅ *POWERED BY SPIDEYOSINT*", parse_mode='Markdown')
    else:
        await msg.edit_text(f"❌ No data found for: {tg_id}\n\n👑 *SPIDEYOSINT*", parse_mode='Markdown')

async def img_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /img <prompt>\nExample: /img cyberpunk hacker")
        return
    
    prompt = ' '.join(context.args)
    msg = await update.message.reply_text(f"🎨 Generating image for: {prompt}...\n⏳ This may take a moment...")
    
    image_url = generate_image(prompt)
    if image_url:
        await msg.delete()
        await update.message.reply_photo(
            photo=image_url, 
            caption=f"🖼️ *Generated:* {prompt}\n👑 *SPIDEYOSINT*",
            parse_mode='Markdown'
        )
    else:
        await msg.edit_text(f"❌ Failed to generate image\nPrompt: {prompt}\n\n👑 *SPIDEYOSINT*", parse_mode='Markdown')

# =============== ADMIN PANEL =============== #

async def admin_panel(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 *ACCESS DENIED*\n\nYe sirf ADMIN ke liye hai bhai!", parse_mode='Markdown')
        return
    
    total_users, today_users = get_user_stats()
    
    keyboard = [
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Total Users", callback_data="admin_users")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="admin_add_channel")],
        [InlineKeyboardButton("🔄 Refresh Force Subs", callback_data="admin_refresh")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔐 *ADMIN PANEL* 🔐\n\n"
        f"👑 *Admin:* {user.first_name}\n"
        f"📡 *Bot Status:* Active ✅\n"
        f"🔗 *Channels:* {len(FORCE_CHANNELS)}\n"
        f"👥 *Total Users:* {total_users}\n"
        f"📅 *Active Today:* {today_users}\n\n"
        f"*Select an option:*\n"
        f"👑 *POWERED BY SPIDEYOSINT*",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "check_subscription":
        is_subscribed, not_subscribed = check_force_subscribe(user.id, context)
        if is_subscribed:
            await query.edit_message_text("✅ *VERIFIED!* Use /start", parse_mode='Markdown')
        else:
            await query.edit_message_text(
                "🚫 Still not subscribed!",
                reply_markup=get_subscribe_keyboard(not_subscribed)
            )
    
    elif query.data == "admin_stats" and user.id in ADMIN_IDS:
        total_users, today_users = get_user_stats()
        stats_text = (
            f"📊 *BOT STATISTICS* 📊\n\n"
            f"👥 *Total Users:* {total_users}\n"
            f"📅 *Active Today:* {today_users}\n"
            f"🔗 *Force Channels:* {len(FORCE_CHANNELS)}\n"
            f"🤖 *Bot Status:* Running ✅\n\n"
            f"👑 *SPIDEYOSINT*"
        )
        await query.edit_message_text(stats_text, parse_mode='Markdown')
    
    elif query.data == "admin_users" and user.id in ADMIN_IDS:
        if not user_db:
            await query.edit_message_text("📭 *No users found*", parse_mode='Markdown')
            return
        
        users_list = "👥 *USER LIST* 👥\n\n"
        for uid, data in list(user_db.items())[:20]:  # Show first 20
            users_list += f"🆔 `{uid}`\n"
            users_list += f"👤 {data.get('first_name', 'N/A')}\n"
            users_list += f"📅 {data.get('first_seen', 'N/A')}\n"
            users_list += f"─────────────\n"
        
        if len(user_db) > 20:
            users_list += f"\n... and {len(user_db) - 20} more users"
        
        await query.edit_message_text(users_list, parse_mode='Markdown')
    
    elif query.data == "admin_broadcast" and user.id in ADMIN_IDS:
        context.user_data['broadcast_mode'] = True
        await query.edit_message_text(
            "📢 *BROADCAST MODE* 📢\n\n"
            "Send me the message you want to broadcast to all users.\n\n"
            "Type /cancel to cancel.",
            parse_mode='Markdown'
        )
    
    elif query.data == "admin_add_channel" and user.id in ADMIN_IDS:
        context.user_data['add_channel_mode'] = True
        await query.edit_message_text(
            "➕ *ADD CHANNEL* ➕\n\n"
            "Send me the channel details in this format:\n"
            "`chat_id|invite_link`\n\n"
            "Example:\n"
            "`-100123456789|https://t.me/+xxxxx`\n\n"
            "Type /cancel to cancel.",
            parse_mode='Markdown'
        )
    
    elif query.data == "admin_refresh" and user.id in ADMIN_IDS:
        await query.edit_message_text(
            "🔄 *Force Subscribe List Refreshed* 🔄\n\n"
            f"Current channels: {len(FORCE_CHANNELS)}\n\n"
            "✅ All good!",
            parse_mode='Markdown'
        )
    
    elif query.data == "admin_close":
        await query.message.delete()

async def handle_broadcast_message(update: Update, context: CallbackContext):
    """Handle broadcast message input"""
    if context.user_data.get('broadcast_mode'):
        message_text = update.message.text
        
        if message_text == "/cancel":
            context.user_data.pop('broadcast_mode', None)
            await update.message.reply_text("❌ *Broadcast cancelled*", parse_mode='Markdown')
            return
        
        processing_msg = await update.message.reply_text("📢 *Broadcasting message...*", parse_mode='Markdown')
        
        success, failed = await broadcast_message(context, message_text)
        
        await processing_msg.edit_text(
            f"📢 *BROADCAST COMPLETED* 📢\n\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}\n\n"
            f"👑 *SPIDEYOSINT*",
            parse_mode='Markdown'
        )
        
        context.user_data.pop('broadcast_mode', None)

async def handle_add_channel(update: Update, context: CallbackContext):
    """Handle add channel input"""
    if context.user_data.get('add_channel_mode'):
        channel_input = update.message.text.strip()
        
        if channel_input == "/cancel":
            context.user_data.pop('add_channel_mode', None)
            await update.message.reply_text("❌ *Operation cancelled*", parse_mode='Markdown')
            return
        
        try:
            chat_id, link = channel_input.split('|')
            chat_id = chat_id.strip()
            link = link.strip()
            
            FORCE_CHANNELS.append({"chat_id": chat_id, "link": link})
            
            await update.message.reply_text(
                f"✅ *Channel Added Successfully!*\n\n"
                f"📢 Chat ID: `{chat_id}`\n"
                f"🔗 Link: {link}\n\n"
                f"Total channels: {len(FORCE_CHANNELS)}",
                parse_mode='Markdown'
            )
        except:
            await update.message.reply_text(
                "❌ *Invalid format!*\n\n"
                "Use: `chat_id|invite_link`\n"
                "Example: `-100123456789|https://t.me/+xxxxx`",
                parse_mode='Markdown'
            )
        
        context.user_data.pop('add_channel_mode', None)

async def cancel(update: Update, context: CallbackContext):
    """Cancel ongoing operations"""
    if context.user_data.get('broadcast_mode'):
        context.user_data.pop('broadcast_mode')
        await update.message.reply_text("❌ *Broadcast cancelled*", parse_mode='Markdown')
    elif context.user_data.get('add_channel_mode'):
        context.user_data.pop('add_channel_mode')
        await update.message.reply_text("❌ *Add channel cancelled*", parse_mode='Markdown')
    else:
        await update.message.reply_text("ℹ️ *No active operation to cancel*", parse_mode='Markdown')

# =============== WEBHOOK SETUP =============== #
@app.route('/webhook', methods=['POST'])
async def webhook():
    if application:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    return 'ok', 200

@app.route('/health', methods=['GET'])
def health():
    return 'Bot is running', 200

# =============== MAIN =============== #
async def setup_webhook():
    webhook_url = os.getenv("RENDER_EXTERNAL_URL", "").replace("http://", "https://") + "/webhook"
    await application.bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

def main():
    global application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("num", num_command))
    application.add_handler(CommandHandler("adhaar", adhaar_command))
    application.add_handler(CommandHandler("tg", tg_command))
    application.add_handler(CommandHandler("img", img_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_channel))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    if os.getenv("RENDER"):
        application.post_init = setup_webhook
        app.run(host='0.0.0.0', port=int(os.getenv("PORT", 10000)))
    else:
        application.run_polling()

if __name__ == "__main__":
    main()