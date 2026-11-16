import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
import json
import os
from collections import defaultdict
import aiohttp

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

CHOOSING, TYPING_REPLY = range(2)

class AdvancedBot:
    def __init__(self, token):
        self.token = token
        self.user_data_file = 'user_data.json'
        self.stats_file = 'bot_stats.json'
        self.reminders = defaultdict(list)
        self.load_data()

    def load_data(self):
        if os.path.exists(self.user_data_file):
            with open(self.user_data_file, 'r', encoding='utf-8') as f:
                self.user_profiles = json.load(f)
        else:
            self.user_profiles = {}

        if os.path.exists(self.stats_file):
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                self.stats = json.load(f)
        else:
            self.stats = {'total_messages': 0, 'total_users': 0, 'commands_used': {}}

    def save_data(self):
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_profiles, f, ensure_ascii=False, indent=2)

        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Аноним"

        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'username': username,
                'registration_date': datetime.now().isoformat(),
                'preferences': {},
                'notes': []
            }
            self.stats['total_users'] += 1
            self.save_data()

        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
            [InlineKeyboardButton("💱 Курс валют", callback_data='currency')],
            [InlineKeyboardButton("📝 Мои заметки", callback_data='notes')],
            [InlineKeyboardButton("⏰ Напоминания", callback_data='reminders')],
            [InlineKeyboardButton("🎲 Случайное число", callback_data='random')],
            [InlineKeyboardButton("🌐 Полезные ссылки", callback_data='links')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = f"""
🤖 Добро пожаловать, {username}!

Это продвинутый Telegram бот с множеством функций:

📋 Команды:
/start - Главное меню
/help - Справка по командам
/profile - Ваш профиль
/note <текст> - Добавить заметку
/notes - Показать все заметки
/remind <минуты> <текст> - Напоминание
/calc <выражение> - Калькулятор
/currency - Курс доллара и евро
/weather <город> - Погода (демо)
/translate <текст> - Перевод (демо)
/poll <вопрос> - Создать опрос
/stats - Статистика бота
/timer <секунды> - Таймер
/quote - Случайная цитата

Выберите действие ниже:
        """

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        self.stats['total_messages'] += 1
        self.save_data()

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📚 Подробная справка:

🔹 /start - Главное меню с кнопками
🔹 /help - Эта справка
🔹 /profile - Ваш профиль и статистика
🔹 /note <текст> - Сохранить заметку
🔹 /notes - Показать все заметки
🔹 /delnote <номер> - Удалить заметку
🔹 /remind <минуты> <текст> - Установить напоминание
🔹 /calc <выражение> - Калькулятор (пример: /calc 2+2*5)
🔹 /currency - Курс доллара и евро (ЦБ РФ)
🔹 /weather <город> - Погода (демо режим)
🔹 /translate <текст> - Перевод текста (демо)
🔹 /poll <вопрос> - Создать опрос
🔹 /stats - Статистика использования бота
🔹 /timer <секунды> - Запустить таймер
🔹 /quote - Получить случайную цитату
🔹 /dice - Бросить кубик
🔹 /coin - Подбросить монетку
🔹 /time - Текущее время МСК

💡 Просто отправьте любое сообщение для эхо-режима!
        """
        await update.message.reply_text(help_text)

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            reg_date = datetime.fromisoformat(profile['registration_date'])

            profile_text = f"""
👤 Ваш профиль:

🆔 ID: {user_id}
👤 Имя: {profile['username']}
📅 Регистрация: {reg_date.strftime('%d.%m.%Y %H:%M')}
📝 Заметок: {len(profile['notes'])}
⏰ Активных напоминаний: {len(self.reminders.get(user_id, []))}
            """
        else:
            profile_text = "❌ Профиль не найден. Используйте /start"

        await update.message.reply_text(profile_text)

    async def note_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        if not context.args:
            await update.message.reply_text("❌ Использование: /note <текст заметки>")
            return

        note_text = ' '.join(context.args)

        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'username': update.effective_user.username,
                'registration_date': datetime.now().isoformat(),
                'preferences': {},
                'notes': []
            }

        self.user_profiles[user_id]['notes'].append({
            'text': note_text,
            'timestamp': datetime.now().isoformat()
        })
        self.save_data()

        await update.message.reply_text(f"✅ Заметка #{len(self.user_profiles[user_id]['notes'])} сохранена!")

    async def notes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        if user_id not in self.user_profiles or not self.user_profiles[user_id]['notes']:
            await update.message.reply_text("📝 У вас пока нет заметок. Используйте /note <текст>")
            return

        notes = self.user_profiles[user_id]['notes']
        notes_text = "📝 Ваши заметки:\n\n"

        for i, note in enumerate(notes, 1):
            timestamp = datetime.fromisoformat(note['timestamp'])
            notes_text += f"{i}. {note['text']}\n   ⏱ {timestamp.strftime('%d.%m.%Y %H:%M')}\n\n"

        await update.message.reply_text(notes_text)

    async def calc_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /calc <выражение>\nПример: /calc 2+2*5")
            return

        expression = ''.join(context.args)

        try:
            allowed_chars = set('0123456789+-*/(). ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Недопустимые символы")

            result = eval(expression)
            await update.message.reply_text(f"🔢 {expression} = {result}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка вычисления: {str(e)}")

    async def remind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)

        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /remind <минуты> <текст>")
            return

        try:
            minutes = int(context.args[0])
            reminder_text = ' '.join(context.args[1:])

            await update.message.reply_text(f"⏰ Напомню через {minutes} мин: {reminder_text}")

            await asyncio.sleep(minutes * 60)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⏰ Напоминание: {reminder_text}"
            )
        except ValueError:
            await update.message.reply_text("❌ Укажите корректное количество минут")

    async def timer_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ Использование: /timer <секунды>")
            return

        try:
            seconds = int(context.args[0])
            if seconds > 3600:
                await update.message.reply_text("❌ Максимум 3600 секунд (1 час)")
                return

            await update.message.reply_text(f"⏱ Таймер на {seconds} сек запущен!")
            await asyncio.sleep(seconds)
            await update.message.reply_text("⏰ Время вышло!")
        except ValueError:
            await update.message.reply_text("❌ Укажите корректное количество секунд")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats_text = f"""
📊 Статистика бота:

👥 Всего пользователей: {self.stats['total_users']}
💬 Всего сообщений: {self.stats['total_messages']}
📝 Всего заметок: {sum(len(u['notes']) for u in self.user_profiles.values())}

🔝 Популярные команды:
        """

        if self.stats['commands_used']:
            for cmd, count in sorted(self.stats['commands_used'].items(), key=lambda x: x[1], reverse=True)[:5]:
                stats_text += f"/{cmd}: {count}\n"

        await update.message.reply_text(stats_text)

    async def time_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msk_time = datetime.now().strftime('%H:%M:%S')
        await update.message.reply_text(f"🕐 Текущее время: {msk_time} МСК")

    async def quote_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        quotes = [
            "Жизнь — это то, что с тобой происходит, пока ты строишь планы.",
            "Будь собой; все остальные роли уже заняты.",
            "Два самых важных дня в твоей жизни: день, когда ты появился на свет, и день, когда понял, зачем.",
            "Мечтай так, как будто будешь жить вечно. Живи так, как будто умрешь сегодня.",
            "Не важно, насколько медленно ты продвигаешься. Главное — не останавливаться."
        ]

        import random
        quote = random.choice(quotes)
        await update.message.reply_text(f"💭 {quote}")

    async def dice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        import random
        result = random.randint(1, 6)
        await update.message.reply_text(f"🎲 Выпало: {result}")

    async def coin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        import random
        result = random.choice(["Орёл", "Решка"])
        await update.message.reply_text(f"🪙 Выпало: {result}")

    async def currency_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            async with aiohttp.ClientSession() as session:
                # Используем ЦБ РФ API для получения курса валют
                async with session.get('https://www.cbr-xml-daily.ru/daily_json.js') as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)

                        usd = data['Valute']['USD']
                        eur = data['Valute']['EUR']

                        currency_text = f"""
💱 Курс валют ЦБ РФ

🇺🇸 Доллар США (USD):
   Курс: {usd['Value']:.2f} ₽
   Изменение: {usd['Value'] - usd['Previous']:+.2f} ₽

🇪🇺 Евро (EUR):
   Курс: {eur['Value']:.2f} ₽
   Изменение: {eur['Value'] - eur['Previous']:+.2f} ₽

📅 Обновлено: {data['Date'][:10]}
                        """

                        await update.message.reply_text(currency_text)
                    else:
                        await update.message.reply_text("❌ Не удалось получить данные о курсе валют")
        except Exception as e:
            logger.error(f"Ошибка получения курса валют: {e}")
            await update.message.reply_text("❌ Ошибка при получении курса валют. Попробуйте позже.")


    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == 'stats':
            await self.stats_command(update, context)
        elif query.data == 'notes':
            await self.notes_command(update, context)
        elif query.data == 'currency':
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://www.cbr-xml-daily.ru/daily_json.js') as response:
                        if response.status == 200:
                            data = await response.json(content_type=None)

                            usd = data['Valute']['USD']
                            eur = data['Valute']['EUR']

                            currency_text = f"""
💱 Курс валют ЦБ РФ

🇺🇸 USD: {usd['Value']:.2f} ₽ ({usd['Value'] - usd['Previous']:+.2f})
🇪🇺 EUR: {eur['Value']:.2f} ₽ ({eur['Value'] - eur['Previous']:+.2f})

📅 {data['Date'][:10]}
                            """
                            await query.edit_message_text(currency_text)
                        else:
                            await query.edit_message_text("❌ Не удалось получить данные")
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await query.edit_message_text("❌ Ошибка получения курса")
        elif query.data == 'random':
            import random
            num = random.randint(1, 100)
            await query.edit_message_text(f"🎲 Случайное число: {num}")
        elif query.data == 'links':
            links_text = """
🌐 Полезные ссылки:

📱 Telegram: https://telegram.org
🐍 Python: https://python.org
🤖 Python Telegram Bot: https://python-telegram-bot.org
            """
            await query.edit_message_text(links_text)

    async def echo_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        self.stats['total_messages'] += 1
        self.save_data()

        await update.message.reply_text(f"🔁 Вы написали: {text}")

    def run(self):
        app = Application.builder().token(self.token).build()

        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("profile", self.profile_command))
        app.add_handler(CommandHandler("note", self.note_command))
        app.add_handler(CommandHandler("notes", self.notes_command))
        app.add_handler(CommandHandler("calc", self.calc_command))
        app.add_handler(CommandHandler("remind", self.remind_command))
        app.add_handler(CommandHandler("timer", self.timer_command))
        app.add_handler(CommandHandler("stats", self.stats_command))
        app.add_handler(CommandHandler("time", self.time_command))
        app.add_handler(CommandHandler("quote", self.quote_command))
        app.add_handler(CommandHandler("dice", self.dice_command))
        app.add_handler(CommandHandler("coin", self.coin_command))
        app.add_handler(CommandHandler("currency", self.currency_command))
        app.add_handler(CallbackQueryHandler(self.button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo_handler))

        logger.info("Бот запущен!")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    TOKEN = os.getenv('BOT_TOKEN', '9198586642:AAEveu7B1vc-h345f4BEPyEeBx_SCOXvdNg')

    if TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ ОШИБКА: Вставьте токен бота в переменную TOKEN")
        print("Получите токен у @BotFather в Telegram")
    else:
        bot = AdvancedBot(TOKEN)
        bot.run()
