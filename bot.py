import logging
import os
import json
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, CallbackQueryHandler
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Health check server for Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server started on port {port}")

# Conversation states
SELECT_PACKAGE, ENTER_UID, ENTER_SERVER_ID, CONFIRM_ORDER = range(4)

# MLBB Price List
PRICE_LIST = [

    {"diamonds": 202, "price": 12000},
    {"diamonds": 257, "price": 15000},
    {"diamonds": 404, "price": 20600},
    {"diamonds": 429, "price": 22000},
    {"diamonds": 514, "price": 28000},
    {"diamonds": 600, "price": 31000},
    {"diamonds": 706, "price": 38000},
    {"diamonds": 829, "price": 33000},
    {"diamonds": 878, "price": 45000},
    {"diamonds": 1049, "price": 55800},
    {"diamonds": 1135, "price": 64000},
    {"diamonds": 1412, "price": 73000},
    {"diamonds": 2157, "price": 101000},
    {"diamonds": 2195, "price": 105000},
    {"diamonds": 3489, "price": 165000},
    {"diamonds": 3688, "price": 176000},
    {"diamonds": 4362, "price": 203000},
    {"diamonds": 5532, "price": 255000},
    {"diamonds": 6598, "price": 298000},
    {"diamonds": 8796, "price": 400000},
    {"diamonds": 9288, "price": 428000},
    {"diamonds": 9625, "price": 438000},
]

# Payment methods
PAYMENT_METHODS = "KBZ Pay / Wave / UAB"
PAYMENT_NUMBERS = "09761457415"
# Orders file
ORDERS_FILE = "orders.json"

def load_orders():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_order(order):
    orders = load_orders()
    orders.append(order)
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def format_price(price):
    """Format price with commas"""
    return f"{price:,}"

async def start(update: Update, context) -> None:
    """Send welcome message"""
    welcome = (
        "💎 *LGAIR Top-Up Bot* 💎\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 Mobile Legends Diamond Top-Up Service\n\n"
        "📋 *Commands:*\n"
        "/order - Diamond အော်ဒါတင်ရန်\n"
        "/pricelist - စျေးနှုန်းများ ကြည့်ရန်\n"
        "/help - အကူအညီ\n\n"
        "💳 *Payment Methods:*\n"
        f"📱 {PAYMENT_METHODS}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚡ Fast & Reliable Service ⚡"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def pricelist(update: Update, context) -> None:
    """Show price list"""
    msg = "💎 *MLBB Diamond Price List* 💎\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    
    for item in PRICE_LIST:
        msg += f"💎 {item['diamonds']} ➠ {format_price(item['price'])} Ks\n"
    
    msg += "\n━━━━━━━━━━━━━━━━━━\n"
    msg += f"💳 Payment: {PAYMENT_METHODS}\n"
    msg += "📲 /order နှိပ်ပြီး အော်ဒါတင်ပါ"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def order(update: Update, context) -> int:
    """Start order process - show package selection"""
    # Create inline keyboard with packages (4 per row)
    keyboard = []
    row = []
    for i, item in enumerate(PRICE_LIST):
        btn = InlineKeyboardButton(
            f"💎{item['diamonds']} - {format_price(item['price'])}Ks",
            callback_data=f"pkg_{i}"
        )
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💎 *Diamond Package ရွေးပါ:*\n\n"
        "အောက်က button တစ်ခုကို နှိပ်ပါ:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return SELECT_PACKAGE

async def select_package(update: Update, context) -> int:
    """Handle package selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Order ပယ်ဖျက်ပြီး။")
        return ConversationHandler.END
    
    pkg_index = int(query.data.split("_")[1])
    selected = PRICE_LIST[pkg_index]
    context.user_data["package"] = selected
    
    await query.edit_message_text(
        f"✅ ရွေးချယ်ပြီး: 💎 {selected['diamonds']} Diamonds = {format_price(selected['price'])} Ks\n\n"
        f"📝 သင့် MLBB User ID ရိုက်ထည့်ပါ:\n"
        f"(ဥပမာ: 123456789)",
        parse_mode="Markdown"
    )
    return ENTER_UID

async def enter_uid(update: Update, context) -> int:
    """Get user ID"""
    uid = update.message.text.strip()
    
    if not uid.isdigit():
        await update.message.reply_text("❌ User ID မှားနေပါတယ်။ ဂဏန်းသာ ရိုက်ထည့်ပါ:")
        return ENTER_UID
    
    context.user_data["game_uid"] = uid
    
    await update.message.reply_text(
        "📝 Server ID ရိုက်ထည့်ပါ:\n"
        "(ဥပမာ: 2001, 2002, 5001 စသည်)"
    )
    return ENTER_SERVER_ID

async def enter_server_id(update: Update, context) -> int:
    """Get server ID and show confirmation"""
    server_id = update.message.text.strip()
    
    if not server_id.isdigit():
        await update.message.reply_text("❌ Server ID မှားနေပါတယ်။ ဂဏန်းသာ ရိုက်ထည့်ပါ:")
        return ENTER_SERVER_ID
    
    context.user_data["server_id"] = server_id
    
    package = context.user_data["package"]
    uid = context.user_data["game_uid"]
    
    # Show confirmation
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    confirm_msg = (
        "📋 *Order Confirmation*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🎮 Game: Mobile Legends\n"
        f"💎 Package: {package['diamonds']} Diamonds\n"
        f"💰 Price: {format_price(package['price'])} Ks\n"
        f"🆔 User ID: {uid}\n"
        f"🌐 Server ID: {server_id}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "✅ မှန်ကန်ပါက Confirm နှိပ်ပါ"
    )
    
    await update.message.reply_text(confirm_msg, reply_markup=reply_markup, parse_mode="Markdown")
    return CONFIRM_ORDER

async def confirm_order(update: Update, context) -> int:
    """Handle order confirmation"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_order":
        await query.edit_message_text("❌ Order ပယ်ဖျက်ပြီး။")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Save order
    package = context.user_data["package"]
    uid = context.user_data["game_uid"]
    server_id = context.user_data["server_id"]
    user = query.from_user
    
    order_data = {
        "order_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "customer_name": user.full_name,
        "customer_username": f"@{user.username}" if user.username else "N/A",
        "customer_id": user.id,
        "game_uid": uid,
        "server_id": server_id,
        "diamonds": package["diamonds"],
        "price": package["price"],
        "status": "PENDING"
    }
    save_order(order_data)
    
    # Send success message to customer
    success_msg = (
        "✅ *Order တင်ပြီးပါပြီ!*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 {package['diamonds']} Diamonds\n"
        f"💰 {format_price(package['price'])} Ks\n"
        f"🆔 UID: {uid} ({server_id})\n\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 *ငွေလွှဲရန်:*\n"
        f"📱 {PAYMENT_METHODS}\n\n"
        "💬 ငွေလွှဲပြီးရင် screenshot ပို့ပေးပါ။\n"
        "⏰ Diamond ဖြည့်ပေးပါမယ်။\n\n"
        "🙏 ကျေးဇူးတင်ပါသည်!"
    )
    
    await query.edit_message_text(success_msg, parse_mode="Markdown")
    
    # Notify admin
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        admin_msg = (
            "🔔 *New Order!*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Customer: {user.full_name}\n"
            f"📱 Username: @{user.username if user.username else 'N/A'}\n"
            f"💎 Package: {package['diamonds']} Diamonds\n"
            f"💰 Price: {format_price(package['price'])} Ks\n"
            f"🆔 Game UID: {uid}\n"
            f"🌐 Server: {server_id}\n"
            f"🕐 Time: {order_data['order_time']}\n\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        try:
            await context.bot.send_message(chat_id=admin_chat_id, text=admin_msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context) -> int:
    """Cancel the conversation"""
    await update.message.reply_text("❌ Order ပယ်ဖျက်ပြီး။ /order နှိပ်ပြီး ပြန်စနိုင်ပါတယ်။")
    context.user_data.clear()
    return ConversationHandler.END

async def help_command(update: Update, context) -> None:
    """Help command"""
    help_text = (
        "ℹ️ *LGAIR Top-Up Bot Help*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📋 *Commands:*\n"
        "/start - Bot စတင်ရန်\n"
        "/order - Diamond အော်ဒါတင်ရန်\n"
        "/pricelist - စျေးနှုန်းများ ကြည့်ရန်\n"
        "/help - အကူအညီ\n\n"
        "📝 *အော်ဒါတင်နည်း:*\n"
        "1. /order နှိပ်ပါ\n"
        "2. Diamond package ရွေးပါ\n"
        "3. MLBB User ID ထည့်ပါ\n"
        "4. Server ID ထည့်ပါ\n"
        "5. Confirm နှိပ်ပါ\n"
        "6. ငွေလွှဲပြီး screenshot ပို့ပါ\n\n"
        f"💳 *Payment:* {PAYMENT_METHODS}\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

def main() -> None:
    """Run the bot."""
    # Start health check server
    start_health_server()
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    application = Application.builder().token(bot_token).build()

    # Conversation handler for orders
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("order", order)],
        states={
            SELECT_PACKAGE: [CallbackQueryHandler(select_package)],
            ENTER_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_uid)],
            ENTER_SERVER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_server_id)],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("pricelist", pricelist))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
