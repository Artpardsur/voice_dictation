"""Приведение распознанного текста в читаемый вид.

Vosk отдаёт сплошную строку строчными буквами и без знаков препинания:
«привет как дела точка». Здесь голосовые команды превращаются в знаки,
предложения начинаются с большой буквы, а лишние пробелы убираются.

Ничего, кроме обработки строк, тут нет — поэтому всё проверяется тестами
без микрофона и без модели.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Команды, превращающиеся в знак препинания. Пробел перед знаком не ставится.
PUNCTUATION: Dict[str, str] = {
    "точка": ".",
    "запятая": ",",
    "вопросительный знак": "?",
    "восклицательный знак": "!",
    "двоеточие": ":",
    "точка с запятой": ";",
    "тире": " —",
    "дефис": "-",
    "многоточие": "…",
    "открыть скобку": " (",
    "закрыть скобку": ")",
    "кавычки": '"',
}

# Команды, меняющие разметку.
BREAKS: Dict[str, str] = {
    "новая строка": "\n",
    "с новой строки": "\n",
    "новый абзац": "\n\n",
    "абзац": "\n\n",
}

# Знаки, после которых следующее слово пишется с большой буквы.
SENTENCE_END = ".!?…"

# Длинные команды разбираются раньше коротких, иначе «точка с запятой»
# распалась бы на «точка» + «с» + «запятой».
_ORDERED = sorted(
    list(PUNCTUATION.items()) + list(BREAKS.items()),
    key=lambda pair: len(pair[0].split()),
    reverse=True,
)


def apply_commands(text: str) -> str:
    """Заменить голосовые команды на знаки и переводы строк."""
    result = text
    for phrase, replacement in _ORDERED:
        pattern = r"(?<![^\s])" + re.escape(phrase) + r"(?![^\s])"
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def tidy_spaces(text: str) -> str:
    """Убрать пробел перед знаком препинания и лишние пробелы подряд."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([.,!?;:…)])", r"\1", text)
    text = re.sub(r"([(])\s+", r"\1", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    return text.strip()


def capitalize_sentences(text: str) -> str:
    """Первая буква предложения — заглавная."""
    result: List[str] = []
    start_of_sentence = True
    for char in text:
        if start_of_sentence and char.isalpha():
            result.append(char.upper())
            start_of_sentence = False
            continue
        result.append(char)
        if char in SENTENCE_END or char == "\n":
            start_of_sentence = True
    return "".join(result)


def polish(text: str, commands: bool = True, capitalize: bool = True) -> str:
    """Полная обработка распознанного куска."""
    if not text or not text.strip():
        return ""
    result = text
    if commands:
        result = apply_commands(result)
    result = tidy_spaces(result)
    if capitalize:
        result = capitalize_sentences(result)
    return result


def join(previous: str, addition: str) -> str:
    """Приклеить новый кусок к уже надиктованному.

    Если предыдущий текст закончился точкой, новый начинается с заглавной —
    иначе продолжаем предложение.
    """
    addition = addition.strip()
    if not previous.strip():
        return addition
    if not addition:
        return previous.rstrip()
    # Проверять перевод строки надо до rstrip: иначе он же его и съест,
    # и новая строка склеится с предыдущей.
    if previous.endswith("\n"):
        return f"{previous}{addition[0].upper()}{addition[1:]}"

    previous = previous.rstrip()
    if previous[-1] in SENTENCE_END:
        return f"{previous} {addition[0].upper()}{addition[1:]}"
    return f"{previous} {addition[0].lower()}{addition[1:]}"
