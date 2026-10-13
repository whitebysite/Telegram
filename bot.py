
import os
import logging
from uuid import uuid4

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

# မူလသတ်မှတ်ထားသော Menu နှင့် စျေးနှုန်းများ
SERVICES = {
    "telegram": {"name": "Telegram", "price": 3000},
    "wechat": {"name": "WeChat", "price": 30000},
    "whatsapp": {"name": "Whatapp", "price": 3000},
    "viber": {"name": "Viber", "price": 2000},
}

PAYMENT_TEXT = (
    "💸 ငွေလွှဲရန်\n\n"
    "KPay - 09680000080\n"
    "Wave - 09680000080\n\n"
    "ငွေလွှဲပြီးပါက Screenshot ကို ဒီ Chat ထဲသို့ ပို့ပေးပါ။\n"
    "Admin မှ စစ်ဆေးပြီး အတည်ပြုပေးပါမည်။"
)

# လက်ရှိ session အတွင်း အသုံးပြုသူရွေးချယ်မှုနှင့် Order များ
user_selections = {}
pending_orders = {}


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Telegram", callback_data="service:telegram"
            ),
            InlineKeyboardButton(
                "WeChat", callback_data="service:wechat"
            ),
        ],
        [
            InlineKeyboardButton(
                "Whatapp", callback_data="service:whatsapp"
            ),
            InlineKeyboardButton(
                "Viber", callback_data="service:viber"
            ),
        ],
    ])


def service_menu(key):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "ဝယ်ယူမည်", callback_data=f"buy:{key}"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ နောက်သို့", callback_data="back:menu"
            )
        ],
    ])


def payment_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ နောက်သို့", callback_data="back:service"
            )
        ],
        [
            InlineKeyboardButton(
                "မီနူးသို့ ပြန်သွားရန်", callback_data="back:menu"
            )
        ],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_selections.pop(user.id, None)

    await update.effective_message.reply_text(
        "မင်္ဂလာပါ။ ဝယ်ယူလိုသော ဝန်ဆောင်မှုကို ရွေးချယ်ပါ။",
        reply_markup=main_menu(),
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.effective_message.reply_text(
        f"သင်၏ Telegram User ID: {user.id}"
    )


async def button_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data or ""

    if data == "back:menu":
        user_selections.pop(user.id, None)
        await query.edit_message_text(
            "ဝယ်ယူလိုသော ဝန်ဆောင်မှုကို ရွေးချယ်ပါ။",
            reply_markup=main_menu(),
        )
        return

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

    if data.startswith("order:"):
        if not ADMIN_CHAT_ID or str(user.id) != ADMIN_CHAT_ID:
            await query.answer(
                "Admin သာ လုပ်ဆောင်နိုင်ပါသည်။",
                show_alert=True,
            )
            return

        _, action, order_id = data.split(":", 2)
        order = pending_orders.get(order_id)

        if not order or order["status"] != "pending":
            await context.bot.send_message(
                chat_id=user.id,
                text="ဒီ Order ကို စစ်ဆေးပြီးပါပြီ သို့မဟုတ် မတွေ့ပါ။",
            )
            return

        if action == "approve":
            status = "အတည်ပြုပြီးပါပြီ ✅"
            order["status"] = "approved"
        elif action == "reject":
            status = "ငြင်းပယ်လိုက်ပါပြီ ❌"
            order["status"] = "rejected"
        else:
            return

        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"Order ID: {order_id}\n"
                f"ဝန်ဆောင်မှု: {order['service']}\n"
                f"စျေးနှုန်း: {order['price']} Ks\n"
                f"Admin အခြေအနေ: {status}"
            ),
        )

        try:
            await query.edit_message_caption(
                caption=(query.message.caption or "")
                + f"\n\nအခြေအနေ: {status}",
                reply_markup=None,
            )
        except Exception:
            logger.exception("Could not update admin order message")

        return


async def screenshot_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
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

    service = SERVICES[key]
    order_id = uuid4().hex[:10].upper()

    order = {
        "user_id": user.id,
        "service": service["name"],
        "price": service["price"],
        "status": "pending",
    }

    if not ADMIN_CHAT_ID:
        await message.reply_text(
            "Admin Chat ID မသတ်မှတ်ရသေးပါ။ "
            "Admin ကို အသိပေးနိုင်ရန် Server Setting ကို ပြင်ဆင်ပေးပါ။"
        )
        logger.error("ADMIN_CHAT_ID is not configured.")
        return

    pending_orders[order_id] = order

    await message.reply_text(
        "✅ ငွေလွှဲ Screenshot လက်ခံရရှိပါပြီ။\n"
        f"Order ID: {order_id}\n"
        f"ဝန်ဆောင်မှု: {service['name']}\n"
        f"စျေးနှုန်း: {service['price']} Ks\n"
        "Admin စစ်ဆေးပြီးနောက် အကြောင်းကြားပေးပါမည်။"
    )

    username = (
        f"@{user.username}" if user.username else "(username မရှိ)"
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

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "အတည်ပြုမည် ✅",
            callback_data=f"order:approve:{order_id}",
        ),
        InlineKeyboardButton(
            "ငြင်းပယ်မည် ❌",
            callback_data=f"order:reject:{order_id}",
        ),
    ]])

    try:
        await context.bot.send_photo(
            chat_id=int(ADMIN_CHAT_ID),
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=keyboard,
        )
    except Exception:
        logger.exception("Failed to notify admin.")
        await message.reply_text(
            "Screenshot လက်ခံရရှိပါပြီ။ Admin ထံ ပို့မရပါ။ "
            "Admin Chat ID နှင့် Bot ကို စစ်ဆေးပါ။"
        )


async def text_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    await update.effective_message.reply_text(
        "ငွေလွှဲ Screenshot ကို ပုံအဖြစ် ပို့ပေးပါ။\n"
        "Menu ပြန်ဖွင့်ရန် /start ကိုနှိပ်ပါ။"
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN ကို Server Environment မှာ ထည့်ပါ။"
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", my_id))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)
    )

    logger.info("Telegram bot is starting...")
    app.run_polling(drop_pending_updates=False)


if __name__ == "__main__":
    main()
