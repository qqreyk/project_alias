import random
import argparse
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# глобальные переменные состояния
game_state = {
    'current_team': 1,
    'scores': {1: 0, 2: 0},
    'current_word': None,
    'word_list': [],
    'used_words': set(),
    'target_score': 20,
}


def load_words(filepath):
    """
    Загружает список слов из текстового файла.

    :param filepath: Путь к файлу со словами
    :type filepath: str
    :returns: Список слов в верхнем регистре, без пустых строк
    :rtype: list
    :raises FileNotFoundError: Если файл не найден
    :raises ValueError: Если файл пуст
    :raises UnicodeDecodeError: Если файл не в кодировке UTF-8
    """

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            words = [line.strip().upper() for line in f if line.strip()]
        if not words:
            raise ValueError("Файл со словами пуст.")
        return words
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Файл не найден: {filepath}") from e
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(
            "Файл должен быть в кодировке UTF-8.",
            e.object, e.start, e.end, e.reason
        ) from e


def get_random_word(word_list, used_words):
    """
    Возвращает случайное слово из списка, которого ещё не было использовано.

    :param word_list: Полный список слов
    :type word_list: list
    :param used_words: Множество уже использованных слов
    :type used_words: set
    :returns: Новое слово, не входящее в used_words
    :rtype: str
    :raises ValueError: Если все слова из word_list уже использованы
    """

    available = [w for w in word_list if w not in used_words]
    if not available:
        raise ValueError("Все слова уже использованы!")
    return random.choice(available)


async def start_game(update, context):
    """
    Обработчик команды /start — начинает новую игру.

    :param update: Объект, содержащий информацию о входящем сообщении
    :type update: telegram.Update
    :param context: Контекст выполнения (хранит данные между вызовами)
    :type context: telegram.ext.ContextTypes.DEFAULT_TYPE
    :returns: None
    :rtype: None
    """

    global game_state

    # сброс состояния
    game_state = {
        'current_team': 1,
        'scores': {1: 0, 2: 0},
        'current_word': None,
        'used_words': set(),
        'target_score': 20,
    }

    # загрузка слов
    words_path = context.bot_data.get('words_path', 'words.txt')
    try:
        game_state['word_list'] = load_words(words_path)
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as e:
        await update.message.reply_text(f"Ошибка загрузки слов: {e}")
        return

    # показ первого слова
    try:
        game_state['current_word'] = get_random_word(game_state['word_list'], game_state['used_words'])
        game_state['used_words'].add(game_state['current_word'])
    except ValueError as e:
        await update.message.reply_text(f"Ошибка: {e}")
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Отгадал", callback_data='correct'),
            InlineKeyboardButton("⏭ Пропустить", callback_data='skip'),
        ],
        [InlineKeyboardButton("⏹ Завершить раунд", callback_data='end_round')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Команда {game_state['current_team']} — объясняйте это слово:\n\n"
        f"👉 <b>{game_state['current_word']}</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def button_handler(update, context):
    """
    Обрабатывает нажатия на кнопки в интерфейсе бота.

    :param update: Объект с данными о callback-запросе
    :type update: telegram.Update
    :param context: Контекст выполнения
    :type context: telegram.ext.ContextTypes.DEFAULT_TYPE
    :returns: None
    :rtype: None
    """

    global game_state
    query = update.callback_query
    await query.answer()

    if not game_state['word_list']:
        await query.edit_message_text("Игра не начата. Напишите /start.")
        return

    try:
        if query.data == 'correct':
            game_state['scores'][game_state['current_team']] += 1
            # Проверка победы
            if game_state['scores'][game_state['current_team']] >= game_state['target_score']:
                await query.edit_message_text(
                    f"🎉 Команда {game_state['current_team']} победила! "
                    f"Счёт: {game_state['scores'][1]} : {game_state['scores'][2]}"
                )
                return

        elif query.data == 'skip':
            pass

        elif query.data == 'end_round':
            game_state['current_team'] = 2 if game_state['current_team'] == 1 else 1

        # новое слово
        try:
            game_state['current_word'] = get_random_word(game_state['word_list'], game_state['used_words'])
            game_state['used_words'].add(game_state['current_word'])
        except ValueError:
            await query.edit_message_text(
                "Слова закончились!\n"
                f"Текущий счёт:\nКоманда 1: {game_state['scores'][1]}\n"
                f"Команда 2: {game_state['scores'][2]}"
            )
            return

        # обновляем сообщение
        keyboard = [
            [
                InlineKeyboardButton("✅ Отгадал", callback_data='correct'),
                InlineKeyboardButton("⏭ Пропустить", callback_data='skip'),
            ],
            [InlineKeyboardButton("⏹ Завершить раунд", callback_data='end_round')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"Команда {game_state['current_team']} — объясняйте это слово:\n\n"
            f"👉 <b>{game_state['current_word']}</b>\n\n"
            f"Счёт: {game_state['scores'][1]} : {game_state['scores'][2]}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        await query.edit_message_text(f"Произошла ошибка: {e}")


def main():
    """
    Основная функция запуска бота. Парсит аргументы командной строки и запускает polling.

    :returns: None
    :rtype: None
    """

    parser = argparse.ArgumentParser(description="Запуск Telegram-бота для игры Alias.")
    parser.add_argument('--token', required=True, help="Токен Telegram-бота")
    parser.add_argument('--words', default='words.txt', help="Путь к файлу со словами")
    args = parser.parse_args()

    if not os.path.isfile(args.words):
        print(f"Ошибка: файл со словами не найден: {args.words}")
        return

    # создаём приложение
    application = Application.builder().token(args.token).build()

    # сохраняем путь к словам
    application.bot_data['words_path'] = args.words

    # регистрация обработчиков
    application.add_handler(CommandHandler("start", start_game))
    application.add_handler(CallbackQueryHandler(button_handler))

    # запуск
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling()


if __name__ == '__main__':
    main()
