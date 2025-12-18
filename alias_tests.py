import pytest
import tempfile
import os
from alias import load_words, get_random_word, game_state


def test_load_words_works():
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
        f.write("КОТ\nСТОЛ\n")
        path = f.name
    try:
        words = load_words(path)
        assert words == ["КОТ", "СТОЛ"]
    finally:
        os.remove(path)


def test_load_words_file_missing():
    with pytest.raises(FileNotFoundError):
        load_words("нет_такого_файла.txt")


def test_get_random_word_works():
    word = get_random_word(["А", "Б"], set())
    assert word in ["А", "Б"]


def test_get_random_word_fails_when_all_used():
    with pytest.raises(ValueError):
        get_random_word(["СЛОВО"], {"СЛОВО"})


def test_game_state_resets_on_start():
    game_state.update({
        'current_team': 1,
        'scores': {1: 0, 2: 0},
        'current_word': None,
        'used_words': set(),
    })
    assert game_state['scores'][1] == 0
    assert game_state['current_team'] == 1


def test_game_needs_words_to_start():
    with pytest.raises(ValueError):
        get_random_word([], set())

def test_button_handler_positive():
    original_score = game_state['scores'][1]
    game_state['current_team'] = 1
    game_state['scores'][game_state['current_team']] += 1
    assert game_state['scores'][1] == original_score + 1


def test_button_handler_negative():
    with pytest.raises(ValueError):
        get_random_word([], set())


def test_main_positive():
    assert os.path.isfile("words.txt")


def test_main_negative():
    assert not os.path.isfile("missing_words.txt")
