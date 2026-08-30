"""Проверки обработки текста, истории и путей к моделям.

Микрофон и модель Vosk для них не нужны.
"""

import pytest

from src import models, textproc
from src.database import Database


# --- знаки препинания голосом ------------------------------------------------


def test_punctuation_commands_become_marks():
    assert textproc.polish("привет как дела точка") == "Привет как дела."


def test_comma_does_not_get_a_space_before_it():
    assert textproc.polish("сначала запятая потом") == "Сначала, потом"


def test_long_command_wins_over_short_one():
    """«точка с запятой» не должна распасться на «точка» + «с» + «запятой»."""
    assert textproc.polish("первое точка с запятой второе") == "Первое; второе"


def test_new_line_command():
    assert "\n" in textproc.polish("первая строка новая строка вторая")


def test_paragraph_command():
    assert "\n\n" in textproc.polish("абзац первый новый абзац абзац второй")


def test_command_inside_a_word_is_not_touched():
    """«заточка» содержит «точка», но точкой не является."""
    assert "." not in textproc.polish("это заточка")


def test_question_mark():
    assert textproc.polish("который час вопросительный знак") == "Который час?"


def test_brackets():
    assert textproc.polish("слово открыть скобку пояснение закрыть скобку") == (
        "Слово (пояснение)"
    )


# --- заглавные буквы ------------------------------------------------------------


def test_first_letter_is_capital():
    assert textproc.polish("первое слово").startswith("П")


def test_every_sentence_starts_with_a_capital():
    result = textproc.polish("первое точка второе точка третье")
    assert result == "Первое. Второе. Третье"


def test_capitalisation_can_be_switched_off():
    assert textproc.polish("привет", capitalize=False) == "привет"


def test_new_line_starts_a_sentence():
    result = textproc.polish("первое новая строка второе")
    assert result.split("\n")[1].startswith("В")


# --- пробелы --------------------------------------------------------------------


def test_repeated_spaces_collapse():
    assert textproc.polish("много     пробелов") == "Много пробелов"


def test_empty_input_gives_empty_output():
    assert textproc.polish("") == ""
    assert textproc.polish("   ") == ""


# --- склейка кусков ---------------------------------------------------------------


def test_join_after_a_full_stop_capitalises():
    assert textproc.join("Первое.", "второе") == "Первое. Второе"


def test_join_inside_a_sentence_keeps_lowercase():
    assert textproc.join("Начало", "Продолжение") == "Начало продолжение"


def test_join_with_empty_parts():
    assert textproc.join("", "первое") == "первое"
    assert textproc.join("первое", "") == "первое"


def test_join_after_a_line_break():
    """Новая строка — новое предложение, значит с заглавной."""
    assert textproc.join("Первое\n", "второе") == "Первое\nВторое"


# --- история ---------------------------------------------------------------------


@pytest.fixture
def history(tmp_path):
    database = Database(str(tmp_path / "history.db"))
    yield database
    database.close()


def test_phrase_is_saved(history):
    history.add("Проверка связи")
    assert history.count() == 1
    assert history.recent()[0]["text"] == "Проверка связи"


def test_empty_phrase_is_not_saved(history):
    assert history.add("   ") is None
    assert history.count() == 0


def test_recent_returns_newest_first(history):
    history.add("первая")
    history.add("вторая")
    assert history.recent()[0]["text"] == "вторая"


def test_search_finds_a_phrase(history):
    history.add("надиктованный текст про кошек")
    history.add("совсем другое")

    found = history.search("кошек")

    assert len(found) == 1
    assert "кошек" in found[0]["text"]


def test_history_survives_a_restart(tmp_path):
    path = str(tmp_path / "history.db")
    with Database(path) as database:
        database.add("не потеряйся")

    with Database(path) as database:
        assert database.count() == 1


def test_clear_empties_the_history(history):
    history.add("что-то")
    history.clear()
    assert history.count() == 0


# --- модели -----------------------------------------------------------------------


def test_model_paths_do_not_depend_on_the_current_folder():
    """Путь считается от папки проекта: раньше он был относительным,
    и запуск из другого каталога модель не находил."""
    assert models.get("ru").path.is_absolute()


def test_unknown_language_falls_back_to_the_default():
    assert models.get("эльфийский").language == models.DEFAULT_LANGUAGE


def test_download_url_is_built_from_the_folder_name():
    info = models.get("ru")
    assert info.url.endswith(f"{info.folder}.zip")


def test_description_mentions_both_languages():
    description = models.describe()
    assert "Русский" in description
    assert "English" in description
