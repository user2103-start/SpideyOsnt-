import os
import logging
import requests
import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler

# =============== CONFIGURATION =============== #
TOKEN = "8772935900:AAFAWA70z_pvqphM1xRbRy5efuCEpvNmbN4"
ADMIN_ID = 6593129349
CHANNEL_OWNER_ID = 6593129349

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

FORCE_CHANNELS = [
    {"chat_id": "-1003767136934", "link": "https://t.me/+skVu9tSSuccyYTQ1"}
]

user_db = {}

# =============== LOGGING =============== #
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============== FORCE SUBSCRIBE =============== #
def check_force_subscribe(user_id: int, bot) -> tuple:
    if user_id == CHANNEL_OWNER_ID:
        return True, []
    
    not_subscribed = []
    for channel in FORCE_CHANNELS:
        try:
            chat_member = bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
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

# =============== EMOJI =============== #
def get_emoji(key):
    emojis = {
        'name': '👤', 'father_name': '👨', 'mother_name': '👩', 'address': '📍',
        'mobile': '📱', 'phone': '📱', 'email': '📧', 'id': '🆔',
        'aadhaar': '🪪', 'dob': '🎂', 'date_of_birth': '🎂', 'gender': '⚥',
        'city': '🏙️', 'state': '🗺️', 'pincode': '📮', 'relation': '👥',
        'card_type': '💳', 'scheme': '📜'
    }
    key_lower = key.lower()
    for emoji_key, emoji in emojis.items():
        if emoji_key in key_lower:
            return emoji
    return '📌'

# =============== FORMATTING =============== #
def format_number_response(api_data):
    try:
        if not api_data.get('success', True):
            return None
        
        if 'result' in api_data and isinstance(api_data['result'], list):
            data = api_data['result'][0]
        elif 'result' in api_data:
            data = api_data['result']
        else:
            data = api_data
        
        unwanted = ['API_Developer', 'channel_name', 'channel_link', 'total_records', 
                   'success', 'owner', 'cached', 'proxyUsed', 'attempt', 'error']
        
        clean_data = {}
        for key, value in data.items():
            if key not in unwanted and value and str(value).strip():
                clean_data[key.replace('_', ' ').title()] = value
        
        if not clean_data:
            return None
        
        lines = ["🔍 NUMBER DETAILS FOUND 🔍", "━━━━━━━━━━━━━━━━━━━━━━", ""]
        for key, value in clean_data.items():
            lines.append(f"{get_emoji(key)} {key}: {value}")
        lines.append("")
        lines.append("⏳ This message will auto-delete in 60 seconds")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Number formatting error: {e}")
        return None

def format_adhaar_response(api_data):
    try:
        if api_data.get('error') or not api_data.get('success', True):
            return None
        
        if 'data' in api_data and isinstance(api_data['data'], dict):
            data = api_data['data']
        elif 'result' in api_data:
            data = api_data['result']
        else:
            data = api_data
        
        clean_data = {}
        for key, value in data.items():
            if value and str(value).strip():
                formatted_key = key.replace('_', ' ').title()
                formatted_key = formatted_key.replace('Dob', 'Date of Birth')
                formatted_key = formatted_key.replace('Aadhaar', 'Aadhaar Number')
                clean_data[formatted_key] = value
        
        if not clean_data:
            return None
        
        lines = ["🪪 FAMILY/AADHAAR DETAILS 🪪", "━━━━━━━━━━━━━━━━━━━━━━", ""]
        for key, value in clean_data.items():
            lines.append(f"{get_emoji(key)} {key}: {value}")
        lines.append("")
        lines.append("⏳ This message will auto-delete in 60 seconds")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Aadhaar formatting error: {e}")
        return None

def format_tg_response(api_data):
    try:
        if api_data.get('error') or not api_data.get('success', True):
            return None
        
        if 'result' in api_data:
            data = api_data['result']
        elif 'data' in api_data:
            data = api_data['data']
        else:
            data = api_data
        
        clean_data = {}
        for key, value in data.items():
            if value and str(value).strip():
                clean_data[key.replace('_', ' ').title()] = value
        
        if not clean_data:
            return None
        
        lines = ["📱 TELEGRAM DETAILS FOUND 📱", "━━━━━━━━━━━━━━━━━━━━━━", ""]
        for key, value in clean_data.items():
            lines.append(f"{get_emoji(key)} {key}: {value}")
        lines.append("")
        lines.append("⏳ This message will auto-delete in 60 seconds")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"TG formatting error: {e}")
        return None

# =============== API CALLS =============== #
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
            if 'image_url' in data:
                return data['image_url']
            elif 'url' in data:
                return data['url']
            elif 'result' in data and isinstance(data['result'], str):
                return data['result']
        return None
    except Exception as e:
        logger.error(f"Image API Error: {e}")
        return None

def get_user_stats():
    total_users = len(user_db)
    today_users = 0
    today = datetime.now().strftime("%Y-%m-%d")
    for user_id, data in user_db.items():
        if data.get('last_used', '').startswith(today):
            today_users += 1
    return total_users, today_users

# =============== AUTO DELETE =============== #
async def auto_delete(context: CallbackContext, chat_id: int, message_id: int, delay: int = 60):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# =============== BOT HANDLERS =============== #
async def start(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id not in user_db:
        user_db[user_id] = {
            'first_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'username': user.username,
            'first_name': user.first_name
        }
    
    is_subscribed, not_subscribed = check_force_subscribe(user.id, context.bot)
    
    if not is_subscribed:
        keyboard = get_subscribe_keyboard(not_subscribed)
        await update.message.reply_text(
            f"🚫 ACCESS DENIED 🚫\n\nBhai {user.first_name}, pehle channel join kar! 🔥",
            reply_markup=keyboard
        )
        return
    
    welcome_text = (
        f"🔥 SPIDEYOSINT OSINT BOT 🔥\n\n"
        f"Namaste {user.first_name}! 👋\n\n"
        f"🇮🇳 POWERED BY SPIDEYOSINT 💀\n"
        f"═══════════════════════\n"
        f"🚀 ADVANCED OSINT TOOL\n"
        f"⚡ MULTIPLE API INTEGRATED\n"
        f"💀 USE WISELY\n"
        f"═══════════════════════\n\n"
        f"📌 COMMANDS:\n"
        f"/num <number> - Mobile number lookup\n"
        f"/adhaar <aadhaar/ration> - Aadhaar/Family lookup\n"
        f"/tg <telegram_id> - Telegram ID lookup\n"
        f"/img <prompt> - Generate image\n"
        f"/admin - Admin panel\n\n"
        f"⚠️ LIMITED TIME API\n"
        f"⏳ All results auto-delete in 60 seconds\n"
        f"👑 DEVELOPED BY SPIDEYOSINT"
    )
    msg = await update.message.reply_text(welcome_text)
    asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 120))

async def num_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context.bot)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        msg = await update.message.reply_text("❌ Usage: /num <mobile_number>\nExample: /num 9876543210")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))
        return
    
    number = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching number: {number}...")
    
    result = search_number(number)
    if result:
        await msg.delete()
        result_msg = await update.message.reply_text(f"{result}\n\n✅ POWERED BY SPIDEYOSINT")
        asyncio.create_task(auto_delete(context, result_msg.chat_id, result_msg.message_id, 60))
    else:
        await msg.edit_text(f"❌ No data found for: {number}\n\n👑 SPIDEYOSINT")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))

async def adhaar_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context.bot)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        msg = await update.message.reply_text("❌ Usage: /adhaar <aadhaar_number/ration_number>\nExample: /adhaar 123456789012")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))
        return
    
    term = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching Aadhaar/Family: {term}...")
    
    result = search_adhaar(term)
    if result:
        await msg.delete()
        result_msg = await update.message.reply_text(f"{result}\n\n✅ POWERED BY SPIDEYOSINT")
        asyncio.create_task(auto_delete(context, result_msg.chat_id, result_msg.message_id, 60))
    else:
        await msg.edit_text(f"❌ No data found for: {term}\n\n👑 SPIDEYOSINT")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))

async def tg_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context.bot)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        msg = await update.message.reply_text("❌ Usage: /tg <telegram_id/username>\nExample: /tg 123456789")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))
        return
    
    tg_id = context.args[0]
    msg = await update.message.reply_text(f"🔄 Searching Telegram: {tg_id}...")
    
    result = search_tg(tg_id)
    if result:
        await msg.delete()
        result_msg = await update.message.reply_text(f"{result}\n\n✅ POWERED BY SPIDEYOSINT")
        asyncio.create_task(auto_delete(context, result_msg.chat_id, result_msg.message_id, 60))
    else:
        await msg.edit_text(f"❌ No data found for: {tg_id}\n\n👑 SPIDEYOSINT")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))

async def img_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in user_db:
        user_db[user_id]['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    is_subscribed, _ = check_force_subscribe(user.id, context.bot)
    
    if not is_subscribed:
        await update.message.reply_text("🚫 Pehle channel join kar!")
        return
    
    if not context.args:
        msg = await update.message.reply_text("❌ Usage: /img <prompt>\nExample: /img cyberpunk hacker")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))
        return
    
    prompt = ' '.join(context.args)
    msg = await update.message.reply_text(f"🎨 Generating image for: {prompt}...\n⏳ This may take a moment...")
    
    image_url = generate_image(prompt)
    if image_url:
        await msg.delete()
        photo_msg = await update.message.reply_photo(
            photo=image_url,
            caption=f"🖼️ Generated: {prompt}\n👑 SPIDEYOSINT\n\n⏳ This image will auto-delete in 60 seconds"
        )
        asyncio.create_task(auto_delete(context, photo_msg.chat_id, photo_msg.message_id, 60))
    else:
        await msg.edit_text(f"❌ Failed to generate image\nPrompt: {prompt}\n\n👑 SPIDEYOSINT")
        asyncio.create_task(auto_delete(context, msg.chat_id, msg.message_id, 60))

async def admin_panel(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("🚫 ACCESS DENIED\n\nYe sirf ADMIN ke liye hai bhai!")
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
        f"🔐 ADMIN PANEL 🔐\n\n"
        f"👑 Admin: {user.first_name}\n"
        f"📡 Bot Status: Active ✅\n"
        f"🔗 Channels: {len(FORCE_CHANNELS)}\n"
        f"👥 Total Users: {total_users}\n"
        f"📅 Active Today: {today_users}\n\n"
        f"Select an option:\n"
        f"👑 POWERED BY SPIDEYOSINT",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "check_subscription":
        is_subscribed, not_subscribed = check_force_subscribe(user.id, context.bot)
        if is_subscribed:
            await query.edit_message_text("✅ VERIFIED! Use /start")
        else:
            await query.edit_message_text(
                "🚫 Still not subscribed!",
                reply_markup=get_subscribe_keyboard(not_subscribed)
            )
    
    elif query.data == "admin_stats" and user.id == ADMIN_ID:
        total_users, today_users = get_user_stats()
        stats_text = (
            f"📊 BOT STATISTICS 📊\n\n"
            f"👥 Total Users: {total_users}\n"
            f"📅 Active Today: {today_users}\n"
            f"🔗 Force Channels: {len(FORCE_CHANNELS)}\n"
            f"🤖 Bot Status: Running ✅\n\n"
            f"👑 SPIDEYOSINT"
        )
        await query.edit_message_text(stats_text)
    
    elif query.data == "admin_users" and user.id == ADMIN_ID:
        if not user_db:
            await query.edit_message_text("📭 No users found")
            return
        
        users_list = "👥 USER LIST 👥\n\n"
        for uid, data in list(user_db.items())[:20]:
            users_list += f"🆔 {uid}\n"
            users_list += f"👤 {data.get('first_name', 'N/A')}\n"
            users_list += f"📅 {data.get('first_seen', 'N/A')}\n"
            users_list += f"─────────────\n"
        
        if len(user_db) > 20:
            users_list += f"\n... and {len(user_db) - 20} more users"
        
        await query.edit_message_text(users_list)
    
    elif query.data == "admin_broadcast" and user.id == ADMIN_ID:
        context.user_data['broadcast_mode'] = True
        await query.edit_message_text(
            "📢 BROADCAST MODE 📢\n\n"
            "Send me the message you want to broadcast to all users.\n\n"
            "Type /cancel to cancel."
        )
    
    elif query.data == "admin_add_channel" and user.id == ADMIN_ID:
        context.user_data['add_channel_mode'] = True
        await query.edit_message_text(
            "➕ ADD CHANNEL ➕\n\n"
            "Send me the channel details in this format:\n"
            "chat_id|invite_link\n\n"
            "Example:\n"
            "-100123456789|https://t.me/+xxxxx\n\n"
            "Type /cancel to cancel."
        )
    
    elif query.data == "admin_refresh" and user.id == ADMIN_ID:
        await query.edit_message_text(
            f"🔄 Force Subscribe List Refreshed 🔄\n\n"
            f"Current channels: {len(FORCE_CHANNELS)}\n\n"
            f"✅ All good!"
        )
    
    elif query.data == "admin_close":
        await query.message.delete()

async def message_handler(update: Update, context: CallbackContext):
    if context.user_data.get('broadcast_mode'):
        message_text = update.message.text
        
        if message_text == "/cancel":
            context.user_data.pop('broadcast_mode', None)
            await update.message.reply_text("❌ Broadcast cancelled")
            return
        
        processing_msg = await update.message.reply_text("📢 Broadcasting message...")
        
        success = 0
        failed = 0
        
        for user_id in user_db.keys():
            try:
                await context.bot.send_message(chat_id=int(user_id), text=message_text)
                success += 1
            except:
                failed += 1
        
        await processing_msg.edit_text(
            f"📢 BROADCAST COMPLETED 📢\n\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}\n\n"
            f"👑 SPIDEYOSINT"
        )
        
        context.user_data.pop('broadcast_mode', None)
    
    elif context.user_data.get('add_channel_mode'):
        channel_input = update.message.text.strip()
        
        if channel_input == "/cancel":
            context.user_data.pop('add_channel_mode', None)
            await update.message.reply_text("❌ Operation cancelled")
            return
        
        try:
            chat_id, link = channel_input.split('|')
            chat_id = chat_id.strip()
            link = link.strip()
            
            FORCE_CHANNELS.append({"chat_id": chat_id, "link": link})
            
            await update.message.reply_text(
                f"✅ Channel Added Successfully!\n\n"
                f"📢 Chat ID: {chat_id}\n"
                f"🔗 Link: {link}\n\n"
                f"Total channels: {len(FORCE_CHANNELS)}"
            )
        except:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "Use: chat_id|invite_link\n"
                "Example: -100123456789|https://t.me/+xxxxx"
            )
        
        context.user_data.pop('add_channel_mode', None)

async def cancel(update: Update, context: CallbackContext):
    if context.user_data.get('broadcast_mode'):
        context.user_data.pop('broadcast_mode')
        await update.message.reply_text("❌ Broadcast cancelled")
    elif context.user_data.get('add_channel_mode'):
        context.user_data.pop('add_channel_mode')
        await update.message.reply_text("❌ Add channel cancelled")
    else:
        await update.message.reply_text("ℹ️ No active operation to cancel")

# =============== MAIN =============== #
def main():
    print("🤖 SPIDEYOSINT BOT STARTING...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"🔗 Force Channels: {len(FORCE_CHANNELS)}")
    print("⏳ Auto-delete: 60 seconds")
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("num", num_command))
    application.add_handler(CommandHandler("adhaar", adhaar_command))
    application.add_handler(CommandHandler("tg", tg_command))
    application.add_handler(CommandHandler("img", img_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("📱 Open Telegram and send /start")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
