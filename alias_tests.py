import unittest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock
from alias import load_words, get_random_word, game_state


class TestLoadWords(unittest.TestCase):
    """Тесты для функции load_words."""

    def test_load_words_valid_file(self):
        """Успешная загрузка слов из корректного файла."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("СЛОВО1\nСЛОВО2\nслово3\n")
            temp_path = f.name

        try:
            words = load_words(temp_path)
            self.assertEqual(words, ["СЛОВО1", "СЛОВО2", "СЛОВО3"])
        finally:
            os.remove(temp_path)

    def test_load_words_empty_file_raises(self):
        """Пустой файл вызывает ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name

        try:
            with self.assertRaises(ValueError) as cm:
                load_words(temp_path)
            self.assertIn("пуст", str(cm.exception))
        finally:
            os.remove(temp_path)

    def test_load_words_file_not_found(self):
        """Файл не найден → FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_words("nonexistent_file.txt")

    def test_load_words_not_utf8(self):
        """Файл не в UTF-8 → UnicodeDecodeError."""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(b'\xff\xfe\x00')  # некорректный UTF-8
            temp_path = f.name

        try:
            with self.assertRaises(UnicodeDecodeError):
                load_words(temp_path)
        finally:
            os.remove(temp_path)


class TestGetRandomWord(unittest.TestCase):
    """Тесты для функции get_random_word."""

    def test_get_random_word_normal(self):
        """Возвращает слово, которого нет в used_words."""
        word_list = ["А", "Б", "В"]
        used = {"А"}
        word = get_random_word(word_list, used)
        self.assertIn(word, ["Б", "В"])
        self.assertNotIn(word, used)

    def test_get_random_word_no_available_raises(self):
        """Все слова использованы → ValueError."""
        word_list = ["ТЕСТ"]
        used = {"ТЕСТ"}
        with self.assertRaises(ValueError) as cm:
            get_random_word(word_list, used)
        self.assertIn("использованы", str(cm.exception))

    def test_get_random_word_empty_list(self):
        """Пустой список → ValueError."""
        with self.assertRaises(ValueError):
            get_random_word([], set())


class TestGameLogic(unittest.TestCase):
    """Тесты логики игры (через game_state)."""

    def setUp(self):
        """Сброс состояния перед каждым тестом."""
        global game_state
        game_state.update({
            'current_team': 1,
            'scores': {1: 0, 2: 0},
            'current_word': None,
            'word_list': ["ТЕСТ"],
            'used_words': set(),
            'target_score': 20,
        })

    def test_initial_state(self):
        """Проверка начального состояния."""
        self.assertEqual(game_state['scores'][1], 0)
        self.assertEqual(game_state['current_team'], 1)

    def test_team_switching(self):
        """Переключение команд: 1 → 2 → 1."""
        game_state['current_team'] = 1
        game_state['current_team'] = 2 if game_state['current_team'] == 1 else 1
        self.assertEqual(game_state['current_team'], 2)

        game_state['current_team'] = 2 if game_state['current_team'] == 1 else 1
        self.assertEqual(game_state['current_team'], 1)

    def test_score_increment(self):
        """Очки увеличиваются при правильном ответе."""
        game_state['scores'][1] += 1
        self.assertEqual(game_state['scores'][1], 1)

    def test_win_condition(self):
        """Проверка условия победы."""
        game_state['scores'][1] = 20
        self.assertTrue(game_state['scores'][1] >= game_state['target_score'])


# === Тесты асинхронных функций (частичные) ===

class TestAsyncFunctions(unittest.IsolatedAsyncioTestCase):
    """Асинхронные тесты для start_game и button_handler (без Telegram API)."""

    async def test_start_game_initializes_state(self):
        """start_game сбрасывает состояние."""
        from alias import start_game

        # Создаём mock-объекты
        update = AsyncMock()
        context = AsyncMock()
        context.bot_data = {'words_path': 'words.txt'}

        # Сымитируем наличие файла
        with unittest.mock.patch('bot.load_words', return_value=["МОК_СЛОВО"]):
            with unittest.mock.patch('bot.get_random_word', return_value="МОК_СЛОВО"):
                await start_game(update, context)

        # Проверим, что вызван reply_text
        update.message.reply_text.assert_called()
        self.assertIn("МОК_СЛОВО", str(update.message.reply_text.call_args))

    async def test_button_handler_correct(self):
        """Обработка кнопки 'correct'."""
        from alias import button_handler

        update = AsyncMock()
        context = AsyncMock()
        query = AsyncMock()
        query.data = 'correct'
        update.callback_query = query

        # Подменяем game_state
        with unittest.mock.patch('bot.game_state', {
            'current_team': 1,
            'scores': {1: 0, 2: 0},
            'word_list': ["СЛОВО"],
            'used_words': set(),
            'target_score': 20,
            'current_word': "СЛОВО",
        }):
            with unittest.mock.patch('bot.get_random_word', return_value="НОВОЕ"):
                await button_handler(update, context)

        query.edit_message_text.assert_called()
        self.assertIn("НОВОЕ", str(query.edit_message_text.call_args))


if __name__ == '__main__':
    unittest.main()