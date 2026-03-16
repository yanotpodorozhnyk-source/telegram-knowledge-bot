import os
import json
import logging
import re
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

# --- Логування ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Google Sheets через ENV змінну ---
try:
    creds_json = os.environ["GOOGLE_CREDENTIALS_JSON"]
except KeyError:
    logging.error("❌ Environment variable 'GOOGLE_CREDENTIALS_JSON' not found!")
    raise KeyError("Please set GOOGLE_CREDENTIALS_JSON in Railway")

creds_dict = json.loads(creds_json)

# 🔧 FIX для Railway (переноси рядків у private_key)
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

creds = Credentials.from_service_account_info(creds_dict)

gc = gspread.authorize(creds)

# --- Відкриваємо таблицю ---
sheet = gc.open("База знань").sheet1
data = sheet.get_all_records()

# --- Створюємо дерево меню ---
tree = {}

for row in data:
    cat = row["Категорія"].strip()
    sub = row["Підтема"].strip()
    q = row["Питання"].strip()
    ans = row.get("Відповідь", "").strip()

    if cat not in tree:
        tree[cat] = {}

    if sub not in tree[cat]:
        tree[cat][sub] = {}

    tree[cat][sub][q] = ans


# --- Безпечний callback ---
def safe_callback(text):
    clean = re.sub(r"\s+", "_", text.strip())
    clean = re.sub(r"[^a-zA-Z0-9_]", "", clean)
    h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
    return f"{clean}_{h}"


# --- Старт ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(cat, callback_data=safe_callback(cat))]
        for cat in tree
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привіт! Обери категорію:",
        reply_markup=reply_markup
    )


# --- Обробка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data_cb = query.data

    # --- Категорія ---
    for cat in tree:
        if safe_callback(cat) == data_cb:

            keyboard = [
                [InlineKeyboardButton(sub, callback_data=safe_callback(f"{cat}|{sub}"))]
                for sub in tree[cat]
            ]

            keyboard.append([InlineKeyboardButton("Головне меню", callback_data="main_menu")])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"Категорія: {cat}\nОберіть підтему:",
                reply_markup=reply_markup
            )
            return

    # --- Підтема ---
    for cat in tree:
        for sub in tree[cat]:

            if safe_callback(f"{cat}|{sub}") == data_cb:

                keyboard = [
                    [InlineKeyboardButton(q, callback_data=safe_callback(f"{cat}|{sub}|{q}"))]
                    for q in tree[cat][sub]
                ]

                keyboard.append([InlineKeyboardButton("Назад", callback_data=safe_callback(cat))])
                keyboard.append([InlineKeyboardButton("Головне меню", callback_data="main_menu")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    f"Підтема: {sub}\nОберіть питання:",
                    reply_markup=reply_markup
                )
                return

    # --- Питання ---
    for cat in tree:
        for sub in tree[cat]:
            for q, ans in tree[cat][sub].items():

                if safe_callback(f"{cat}|{sub}|{q}") == data_cb:

                    keyboard = [
                        [InlineKeyboardButton("Назад", callback_data=safe_callback(f"{cat}|{sub}"))],
                        [InlineKeyboardButton("Головне меню", callback_data="main_menu")]
                    ]

                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await query.edit_message_text(
                        ans,
                        reply_markup=reply_markup
                    )
                    return

    # --- Головне меню ---
    if data_cb == "main_menu":

        keyboard = [
            [InlineKeyboardButton(cat, callback_data=safe_callback(cat))]
            for cat in tree
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "Привіт! Обери категорію:",
            reply_markup=reply_markup
        )


# --- Запуск ---
if __name__ == "__main__":

    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not TOKEN:
        raise KeyError("Please set TELEGRAM_BOT_TOKEN in Railway")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущений...")

    app.run_polling()
