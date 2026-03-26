import os
import logging
import requests
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode

# =============== CONFIGURATION =============== #
TOKEN = "8772935900:AAFAWA70z_pvqphM1xRbRy5efuCEpvNmbN4"  # Apna bot token daalo
API_URL = "https://ayaanmods.site/number.php?key=annonymous&number="  # API URL daalo yahan - YAHAN APNI API DAALO
API_KEY = "YOUR_API_KEY_HERE"  # Agar API key chahiye to daalo

# Admin IDs (jinko admin panel chahiye)
ADMIN_IDS = [6593129349]  # Apne Telegram IDs daalo

# Channel Owners/Admins (jinko force subscribe nahi karna)
CHANNEL_OWNERS = [6593129349]  # Apna ID daalo yahan

# Force Subscribe Channels
FORCE_CHANNELS = [
    {
        "chat_id": "-1003767136934",
        "username": "",
        "link": "https://t.me/+skVu9tSSuccyYTQ1"
    }
]

# =============== LOGGING =============== #
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =============== HELPER FUNCTIONS =============== #
def check_force_subscribe(user_id: int, context: CallbackContext) -> tuple:
    """Check if user is subscribed to all required channels"""
    
    # Channel owners/admin ko force subscribe skip
    if user_id in CHANNEL_OWNERS:
        return True, []
    
    not_subscribed = []
    
    for channel in FORCE_CHANNELS:
        try:
            chat_member = context.bot.get_chat_member(chat_id=channel["chat_id"], user_id=user_id)
            if chat_member.status in ['left', 'kicked']:
                not_subscribed.append(channel)
        except Exception as e:
            logger.error(f"Force subscribe check error for {user_id}: {e}")
            not_subscribed.append(channel)
    
    return len(not_subscribed) == 0, not_subscribed

def get_subscribe_keyboard(not_subscribed_channels):
    """Generate inline keyboard with subscribe buttons"""
    keyboard = []
    for idx, channel in enumerate(not_subscribed_channels):
        keyboard.append([InlineKeyboardButton(
            text=f"📢 Join Channel {idx+1}", 
            url=channel["link"]
        )])
    keyboard.append([InlineKeyboardButton(
        text="✅ Check Subscription", 
        callback_data="check_subscription"
    )])
    return InlineKeyboardMarkup(keyboard)

def format_api_response(api_data):
    """Format API response to show only required fields"""
    try:
        if isinstance(api_data, dict):
            # Check if result exists in response
            if 'result' in api_data and api_data['result']:
                data = api_data['result'][0] if isinstance(api_data['result'], list) else api_data['result']
            else:
                data = api_data
            
            # Extract only required fields
            formatted = (
                f"🔍 DETAILS FOUND 🔍\n\n"
                f"👤 Name: {data.get('name', 'N/A')}\n"
                f"👨 Father's Name: {data.get('father_name', 'N/A')}\n"
                f"📍 Address: {data.get('address', 'N/A')}\n"
                f"🔄 Circle: {data.get('circle', 'N/A')}\n"
                f"📱 Mobile: {data.get('mobile', 'N/A')}\n"
                f"🔄 Alternate: {data.get('alternate', 'N/A')}\n"
                f"📧 Email: {data.get('email', 'N/A')}\n"
                f"🆔 ID: {data.get('id', 'N/A')}"
            )
            return formatted
        else:
            return None
    except Exception as e:
        logger.error(f"Formatting error: {e}")
        return None

def search_number(number: str):
    """Search number on API"""
    try:
        # Agar API URL set nahi hai to error do
        if API_URL == "YOUR_API_URL_HERE":
            logger.error("API URL not configured")
            return None
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if API_KEY != "YOUR_API_KEY_HERE":
            headers['Authorization'] = f'Bearer {API_KEY}'
        
        # API call - format according to your API
        # Agar GET method se kaam karti hai:
        response = requests.get(
            f"{API_URL}?number={number}",
            headers=headers,
            timeout=15
        )
        
        # Agar POST method se kaam karti hai to ye use karo:
        # response = requests.post(
        #     API_URL,
        #     json={"mobile": number, "number": number},
        #     headers=headers,
        #     timeout=15
        # )
        
        if response.status_code == 200:
            data = response.json()
            return format_api_response(data)
        else:
            logger.error(f"API Error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("API Timeout")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("API Connection Error")
        return None
    except Exception as e:
        logger.error(f"API Exception: {e}")
        return None

# =============== BOT COMMANDS =============== #
async def start(update: Update, context: CallbackContext):
    """Handle /start command"""
    user = update.effective_user
    
    # Check force subscribe
    is_subscribed, not_subscribed = check_force_subscribe(user.id, context)
    
    if not is_subscribed:
        keyboard = get_subscribe_keyboard(not_subscribed)
        await update.message.reply_text(
            f"🚫 ACCESS DENIED 🚫\n\n"
            f"Bhai {user.first_name}, pehle channel join kar laal! 🔥\n\n"
            f"Join karne ke baad 'Check Subscription' button dabao 👇",
            reply_markup=keyboard
        )
        return
    
    # Cyberpunk style welcome message with SpideyOsint branding
    welcome_text = (
        f"🔥 BHAI AA GAYA SYSTEM 🔥\n\n"
        f"Namaste {user.first_name}! 👋\n\n"
        f"🇮🇳 POWERED BY SPIDEYOSINT 💀\n"
        f"═══════════════════════\n"
        f"🚀 TERA APNA TRUECALLER BOT\n"
        f"⚡ BAS NUMBER DAL KE MAAR\n"
        f"💀 JITNA USE KAR SAKE UTNA KAR\n"
        f"═══════════════════════\n\n"
        f"⚠️ NOTICE: \n"
        f"API sirf limited time ke liye valid hai!\n"
        f"Abhi jitna use karna hai kar lo 🔥\n\n"
        f"💀 COMMANDS: \n"
        f"• Direct number bhej - Search karega\n"
        f"• Idhar kya padh raha hai time kam ja jake bot use kar \n\n"
        f"👑 DEVELOPED BY: SPIDEYOSINT\n"
        f"═══════════════════════"
    )
    
    await update.message.reply_text(welcome_text)

async def handle_number(update: Update, context: CallbackContext):
    """Handle mobile number input"""
    user = update.effective_user
    number = update.message.text.strip()
    
    # Check force subscribe
    is_subscribed, not_subscribed = check_force_subscribe(user.id, context)
    
    if not is_subscribed:
        keyboard = get_subscribe_keyboard(not_subscribed)
        await update.message.reply_text(
            f"🚫 BHAI PEHLE JOIN TO KAR 🚫\n\n"
            f"Channel join kiye bina number nahi chalega! 🔥\n\n"
            f"Join kar ke aa phir se try kar 👇",
            reply_markup=keyboard
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        f"🔄 PROCESSING... 🔄\n\n"
        f"📱 Number: {number}\n"
        f"⏳ API se data la raha hu..."
    )
    
    # Search the number
    result = search_number(number)
    
    if result:
        await processing_msg.edit_text(
            f"{result}\n\n"
            f"✅ SEARCH COMPLETE ✅\n"
            f"🔍 Number: {number}\n"
            f"👑 POWERED BY SPIDEYOSINT"
        )
    else:
        await processing_msg.edit_text(
            f"❌ ERROR ❌\n\n"
            f"📱 Number: {number}\n"
            f"⚠️ Kuch to gadbad hai!\n\n"
            f"• Number sahi hai? 🔢\n"
            f"• API thodi der mein aayegi ⏳\n"
            f"• Ya phir data hi nahi mila 📭\n\n"
            f"Thodi der baad try kar bro! 🔥\n\n"
            f"👑 DEVELOPED BY SPIDEYOSINT"
        )

async def admin_panel(update: Update, context: CallbackContext):
    """Admin panel - only for admins"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text(
            f"🚫 ACCESS DENIED 🚫\n\n"
            f"Ye sirf ADMIN ke liye hai bhai!\n"
            f"Tu to outsider hai 😎"
        )
        return
    
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
        f"🔗 Channels: {len(FORCE_CHANNELS)}\n\n"
        f"Select an option:\n"
        f"👑 POWERED BY SPIDEYOSINT",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: CallbackContext):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    if query.data == "check_subscription":
        is_subscribed, not_subscribed = check_force_subscribe(user.id, context)
        
        if is_subscribed:
            await query.edit_message_text(
                f"✅ VERIFIED ✅\n\n"
                f"Ab tu member hai bro! 🎉\n"
                f"Ab /start kar ke bot use kar sakta hai 🔥\n\n"
                f"👑 POWERED BY SPIDEYOSINT"
            )
        else:
            keyboard = get_subscribe_keyboard(not_subscribed)
            await query.edit_message_text(
                f"🚫 ABHI BHI NAHI JOIN KIYA 🚫\n\n"
                f"Bhai {user.first_name}, tu abhi bhi channel join nahi kiya!\n\n"
                f"Join kar phir se check kar 👇",
                reply_markup=keyboard
            )
    
    elif query.data == "admin_stats" and user.id in ADMIN_IDS:
        await query.edit_message_text(
            f"📊 BOT STATS 📊\n\n"
            f"Coming soon...\n\n"
            f"👑 POWERED BY SPIDEYOSINT"
        )
    
    elif query.data == "admin_close":
        await query.message.delete()

async def set_commands(application: Application):
    """Set bot commands"""
    commands = [
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("admin", "🔐 Admin Panel"),
    ]
    await application.bot.set_my_commands(commands)

# =============== MAIN FUNCTION =============== #
def main():
    """Start the bot"""
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.post_init = set_commands
    
    print("🤖 Bot is running...")
    print("✅ Bot started successfully!")
    print("👑 POWERED BY SPIDEYOSINT")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()