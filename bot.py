
import os
import logging
from uuid import uuid4

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==============================
# SERVER SETTINGS
# ==============================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

ADMIN_USERNAME = "waiphyoe390844"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ==============================
# SERVICE MENU AND PRICES
# ==============================

SERVICES = {
    "telegram": {
        "name": "Telegram",
        "price": 3000,
    },
    "wechat": {
        "name": "WeChat",
        "price": 30000,
    },
    "whatsapp": {
        "name": "Whatapp",
        "price": 3000,
    },
    "viber": {
        "name": "Viber",
        "price": 2000,
    },
}

PAYMENT_TEXT = (
    "💸 ငွေလွှဲရန်\n\n"
    "KPay - 09680000080\n"
    "Wave - 09680000080\n\n"
    "ငွေလွှဲပြီးပါက Screenshot ကို "
    "ဒီ Chat ထဲသို့ ပို့ပေးပါ။\n"
    "Admin မှ စစ်ဆေးပြီး အတည်ပြုပါမည်။"
)

# ==============================
# TEMPORARY ORDER STORAGE
# ==============================

user_selections = {}
pending_orders = {}


# ==============================
# KEYBOARDS
# ==============================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Telegram",
                callback_data="service:telegram",
            ),
            InlineKeyboardButton(
                "WeChat",
                callback_data="service:wechat",
            ),
        ],
        [
            InlineKeyboardButton(
                "Whatapp",
                callback_data="service:whatsapp",
            ),
            InlineKeyboardButton(
                "Viber",
                callback_data="service:viber",
            ),
        ],
    ])


def service_menu(key):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "ဝယ်ယူမည်",
                callback_data=f"buy:{key}",
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ နောက်သို့",
                callback_data="back:menu",
            )
        ],
    ])


def payment_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ နောက်သို့",
                callback_data="back:service",
            )
        ],
        [
            InlineKeyboardButton(
                "မီနူးသို့ ပြန်သွားရန်",
                callback_data="back:menu",
            )
        ],
    ])


def contact_admin_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📩 Admin ကို ဆက်သွယ်ရန်",
                url=f"https://t.me/{ADMIN_USERNAME}",
            )
        ]
    ])


# ==============================
# START COMMAND
# ==============================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    user_selections.pop(user.id, None)

    await update.effective_message.reply_text(
        "မင်္ဂလာပါ။ 👋\n\n"
        "ဝယ်ယူလိုသော ဝန်ဆောင်မှုကို ရွေးချယ်ပါ။",
        reply_markup=main_menu(),
    )


# ==============================
# FIND TELEGRAM USER ID
# ==============================

async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    await update.effective_message.reply_text(
        f"သင်၏ Telegram User ID: {user.id}"
    )


# ==============================
# BUTTON HANDLER
# ==============================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data or ""

    # Return to main menu
    if data == "back:menu":
        user_selections.pop(user.id, None)

        await query.edit_message_text(
            "ဝယ်ယူလိုသော ဝန်ဆောင်မှုကို ရွေးချယ်ပါ။",
            reply_markup=main_menu(),
        )
        return

    # Return to selected service
    if data == "back:service":
        key = user_selections.get(user.id)

        if key in SERVICES:
            service = SERVICES[key]

            await query.edit_message_text(
                f"📦 {service['name']}\n"
                f"💰 စျေးနှုန်း - {service['price']} Ks",
                reply_markup=service_menu(key),
            )
        else:
            await query.edit_message_text(
                "ဝန်ဆောင်မှုကို ရွေးချယ်ပါ။",
                reply_markup=main_menu(),
            )
        return

    # Select a service
    if data.startswith("service:"):
        key = data.split(":", 1)[1]

        if key not in SERVICES:
            return

        user_selections[user.id] = key
        service = SERVICES[key]

        await query.edit_message_text(
            f"📦 {service['name']}\n"
            f"💰 စျေးနှုန်း - {service['price']} Ks",
            reply_markup=service_menu(key),
        )
        return

    # Buy a service
    if data.startswith("buy:"):
        key = data.split(":", 1)[1]

        if key not in SERVICES:
            return

        user_selections[user.id] = key

        await query.edit_message_text(
            PAYMENT_TEXT,
            reply_markup=payment_menu(),
        )
        return

    # Admin approves or rejects an order
    if data.startswith("order:"):

        if not ADMIN_CHAT_ID:
            await query.answer(
                "Admin Chat ID မသတ်မှတ်ရသေးပါ။",
                show_alert=True,
            )
            return

        if str(user.id) != ADMIN_CHAT_ID:
            await query.answer(
                "Admin သာ လုပ်ဆောင်နိုင်ပါသည်။",
                show_alert=True,
            )
            return

        parts = data.split(":", 2)

        if len(parts) != 3:
            return

        _, action, order_id = parts
        order = pending_orders.get(order_id)

        if not order:
            await query.answer(
                "Order မတွေ့ပါ။ Server Restart ဖြစ်ထားနိုင်ပါသည်။",
                show_alert=True,
            )
            return

        if order["status"] != "pending":
            await query.answer(
                "ဒီ Order ကို စစ်ဆေးပြီးပါပြီ။",
                show_alert=True,
            )
            return

        # APPROVE PAYMENT
        if action == "approve":
            order["status"] = "approved"
            status = "အတည်ပြုပြီးပါပြီ ✅"

            await context.bot.send_message(
                chat_id=order["user_id"],
                text=(
                    "✅ ငွေပေးချေမှု အတည်ပြုပြီးပါပြီ။\n\n"
                    f"Order ID: {order_id}\n"
                    f"ဝန်ဆောင်မှု: {order['service']}\n"
                    f"စျေးနှုန်း: {order['price']} Ks\n\n"
                    "ဆက်လက်ဆောင်ရွက်ရန် "
                    "Admin ကို ဆက်သွယ်ပေးပါ။"
                ),
                reply_markup=contact_admin_button(),
            )

        # REJECT PAYMENT
        elif action == "reject":
            order["status"] = "rejected"
            status = "ငြင်းပယ်လိုက်ပါပြီ ❌"

            await context.bot.send_message(
                chat_id=order["user_id"],
                text=(
                    "❌ ငွေလွှဲမှုကို အတည်မပြုနိုင်သေးပါ။\n\n"
                    f"Order ID: {order_id}\n"
                    f"ဝန်ဆောင်မှု: {order['service']}\n\n"
                    "အသေးစိတ်စစ်ဆေးရန် Admin ကို ဆက်သွယ်ပါ။"
                ),
                reply_markup=contact_admin_button(),
            )

        else:
            return

        # Update admin message
        try:
            await query.edit_message_caption(
                caption=(
                    (query.message.caption or "")
                    + f"\n\nအခြေအနေ: {status}"
                ),
                reply_markup=None,
            )
        except Exception:
            logger.exception(
                "Unable to update admin order message"
            )

        return


# ==============================
# PAYMENT SCREENSHOT HANDLER
# ==============================

async def screenshot_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    key = user_selections.get(user.id)

    if key not in SERVICES:
        await message.reply_text(
            "အရင်ဆုံး /start နှိပ်ပြီး ဝန်ဆောင်မှုရွေးချယ်ပါ။",
            reply_markup=main_menu(),
        )
        return

    if not ADMIN_CHAT_ID:
        await message.reply_text(
            "Admin Chat ID မသတ်မှတ်ရသေးပါ။\n"
            "Admin ကို အသိပေးနိုင်ရန် Server Setting ကို ပြင်ဆင်ပေးပါ။"
        )
        logger.error("ADMIN_CHAT_ID is not configured.")
        return

    service = SERVICES[key]
    order_id = uuid4().hex[:10].upper()

    order = {
        "user_id": user.id,
        "service": service["name"],
        "price": service["price"],
        "status": "pending",
    }

    pending_orders[order_id] = order

    username = (
        f"@{user.username}"
        if user.username
        else "(username မရှိ)"
    )

    caption = (
        "🧾 ငွေလွှဲ Screenshot — စစ်ဆေးရန်\n\n"
        f"Order ID: {order_id}\n"
        f"ဝယ်သူ: {user.full_name}\n"
        f"Username: {username}\n"
        f"User ID: {user.id}\n"
        f"ဝန်ဆောင်မှု: {service['name']}\n"
        f"စျေးနှုန်း: {service['price']} Ks\n"
        "အခြေအနေ: စစ်ဆေးဆဲ"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "အတည်ပြုမည် ✅",
                callback_data=f"order:approve:{order_id}",
            ),
            InlineKeyboardButton(
                "ငြင်းပယ်မည် ❌",
                callback_data=f"order:reject:{order_id}",
            ),
        ]
    ])

    try:
        # Send screenshot to admin
        await context.bot.send_photo(
            chat_id=int(ADMIN_CHAT_ID),
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=keyboard,
        )

        # Notify customer
        await message.reply_text(
            "✅ ငွေလွှဲ Screenshot လက်ခံရရှိပါပြီ။\n\n"
            f"Order ID: {order_id}\n"
            f"ဝန်ဆောင်မှု: {service['name']}\n"
            f"စျေးနှုန်း: {service['price']} Ks\n\n"
            "Admin မှ စစ်ဆေးပြီးနောက် "
            "အကြောင်းကြားပေးပါမည်။"
        )

    except Exception:
        logger.exception("Could not send screenshot to admin.")

        await message.reply_text(
            "Screenshot ကို Admin ထံ ပို့မရပါ။\n"
            "Admin Chat ID နဲ့ Bot Setting ကို စစ်ဆေးပါ။"
        )

        # Allow the order to be retried if delivery failed
        pending_orders.pop(order_id, None)


# ==============================
# OTHER MESSAGES
# ==============================

async def text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.effective_message.reply_text(
        "ငွေလွှဲ Screenshot ကို ပုံအဖြစ် ပို့ပေးပါ။\n"
        "Menu ပြန်ဖွင့်ရန် /start ကိုနှိပ်ပါ။"
    )


# ==============================
# RUN BOT
# ==============================

def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN ကို Render Environment မှာ ထည့်ပါ။"
        )

    if not ADMIN_CHAT_ID:
        logger.warning(
            "ADMIN_CHAT_ID မသတ်မှတ်ရသေးပါ။"
        )

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", my_id))

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            screenshot_handler,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler,
        )
    )

    logger.info("Telegram Bot is starting...")

    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
