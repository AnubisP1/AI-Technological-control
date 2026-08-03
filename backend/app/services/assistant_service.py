"""AI-ассистент по вопросам НСИ и технологичности (Фаза 17, часть 5 —
по прямому запросу пользователя, экран "Обзор"): "я мог спросить любой
вопрос по НСИ или в целом о технологичсности и он отвечал по БД НСИ".

Контекст для ответа собирается ДО обращения к LLM простым keyword-
поиском по ключевым справочникам обеих независимых баз НСИ (металл +
аддитив) — без векторного поиска/RAG (согласовано с пользователем при
планировании Фазы 15, см. dev/PLAN.md). Само формулирование ответа —
через IChatResponder, с тем же принципом, что и KdReviewService._summarize:
LLM пробуется первой, любая ошибка откатывается на офлайн-шаблон, чтобы
чат оставался рабочим без сети (см. dev/QUESTIONS.md №12).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.domain.assistant.chat_responder_port import ChatReply, IChatResponder
from app.infrastructure.db.nsi_db import NsiDatabase, connect
from app.infrastructure.llm.template_chat_responder import TemplateChatResponder

logger = logging.getLogger(__name__)

_MAX_MATCHES = 6
_MIN_KEYWORD_LENGTH = 3

# Простое суффиксное усечение (не полноценная морфология, без внешних
# библиотек, см. dev/QUESTIONS.md — офлайн-требование не оправдывает
# зависимость от pymorphy2/natasha ради демонстрационного keyword-поиска)
# — снимает типичные окончания падежей/чисел русских существительных и
# прилагательных, чтобы "марки"/"стали"/"пропеллера" находили "марка"/
# "сталь"/"PROPELLER" по общей основе. Длиннейший суффикс проверяется
# первым, чтобы "-ями" не срезалось как "-я" раньше времени.
_RU_SUFFIXES = (
    "иями", "ями", "ами", "его", "ему", "ыми", "ими",
    "ов", "ев", "ей", "ах", "ях", "ию", "ья", "ье", "ья",
    "ая", "яя", "ое", "ее", "ы", "и", "а", "я", "у", "ю", "е", "о", "й", "ь",
)
_RU_STEM_MIN_LENGTH = 4  # не усекать короткие слова/коды станков вроде "16К20"


def _stem_ru(word: str) -> str:
    for suffix in _RU_SUFFIXES:
        if len(word) - len(suffix) >= _RU_STEM_MIN_LENGTH and word.endswith(suffix):
            return word[: -len(suffix)]
    return word

# Стоп-слова русского языка, не несущие поискового смысла — исключаются
# из ключевых слов вопроса, чтобы не засорять LIKE-поиск общими словами.
_STOPWORDS = frozenset(
    {
        "как", "что", "какой", "какая", "какое", "какие", "для", "при", "это",
        "если", "или", "как", "его", "она", "они", "мне", "нам", "можно",
        "есть", "нет", "чем", "где", "почему", "нужно", "нужен", "нужна",
        "подойдет", "подходит", "подойдёт", "используется", "какой-то",
        "про", "расскажи", "скажи", "хочу", "могу", "должен",
    }
)

# (таблица, колонки для LIKE-поиска, колонки для строки-описания результата)
_METAL_SEARCH_TARGETS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("material", ("grade", "gost_standard", "description"), ("grade", "gost_standard", "description")),
    ("equipment_model", ("model_name", "control_system", "description"), ("model_name", "control_system", "description")),
    ("tooling", ("designation", "gost_standard", "material", "description"), ("designation", "material", "description")),
    ("operation_type", ("code", "name", "gost_code", "description"), ("code", "name", "description")),
    ("workpiece_type", ("code", "name", "description"), ("code", "name", "description")),
)

_ADDITIVE_SEARCH_TARGETS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("am_material", ("trade_name", "gost_or_standard", "description"), ("trade_name", "gost_or_standard", "description")),
    ("am_technology", ("code", "name", "description"), ("code", "name", "description")),
    ("printer_model", ("model_name", "description"), ("model_name", "description")),
    ("part_application_class", ("code", "name", "description"), ("code", "name", "description")),
)


@dataclass(frozen=True)
class ContextMatch:
    table: str
    summary: str


class AssistantService:
    def __init__(
        self,
        metal_db_path: Path,
        additive_db_path: Path,
        chat_responder: IChatResponder | None = None,
    ) -> None:
        self._db_paths = {NsiDatabase.METAL: metal_db_path, NsiDatabase.ADDITIVE: additive_db_path}
        self._template_responder = TemplateChatResponder()
        # chat_responder опционален — без него (обычный офлайн запуск без
        # настроенного YandexGPT API) ассистент работает целиком на
        # шаблонном перечислении найденных фактов, без обращения к сети.
        self._chat_responder = chat_responder

    def ask(self, question: str) -> ChatReply:
        matches = self._search(question)
        context_facts = {"matches": [{"table": m.table, "summary": m.summary} for m in matches]}

        if self._chat_responder is not None:
            try:
                return self._chat_responder.reply(question=question, context_facts=context_facts)
            except Exception:
                # Сеть/ключ API/формат ответа — любая причина не должна
                # ронять чат целиком. Откат на шаблонный ответ, который
                # всегда доступен офлайн (тот же принцип, что KdReviewService).
                logger.warning(
                    "Чат-ассистент LLM недоступен, используется шаблонный fallback",
                    exc_info=True,
                )

        return self._template_responder.reply(question=question, context_facts=context_facts)

    def _search(self, question: str) -> list[ContextMatch]:
        keywords = self._extract_keywords(question)
        if not keywords:
            return []

        matches: list[ContextMatch] = []
        matches.extend(self._search_database(NsiDatabase.METAL, _METAL_SEARCH_TARGETS, keywords))
        if len(matches) < _MAX_MATCHES:
            matches.extend(self._search_database(NsiDatabase.ADDITIVE, _ADDITIVE_SEARCH_TARGETS, keywords))
        return matches[:_MAX_MATCHES]

    def _extract_keywords(self, question: str) -> list[str]:
        words = re.findall(r"[\wА-Яа-яЁё-]+", question.lower())
        return [_stem_ru(w) for w in words if len(w) >= _MIN_KEYWORD_LENGTH and w not in _STOPWORDS]

    def _search_database(
        self,
        database: NsiDatabase,
        targets: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...],
        keywords: list[str],
    ) -> list[ContextMatch]:
        connection = connect(self._db_paths[database])
        # Встроенный SQLite LOWER()/LIKE регистронезависимы только для
        # ASCII, кириллицу не сворачивают ("Сталь" != "сталь") — без
        # этого поиск по-русски находил бы записи только при точном
        # совпадении регистра пользовательского ввода с БД (реальный
        # баг, найден при разработке на вопросе "12ХН3А" в нижнем регистре).
        connection.create_function("PY_LOWER", 1, lambda s: s.lower() if s is not None else None)
        try:
            found: list[ContextMatch] = []
            for table, search_columns, summary_columns in targets:
                if len(found) >= _MAX_MATCHES:
                    break
                rows = self._search_table(connection, table, search_columns, keywords)
                for row in rows:
                    summary = " · ".join(str(row[c]) for c in summary_columns if row[c] is not None)
                    found.append(ContextMatch(table=table, summary=summary))
            return found
        finally:
            connection.close()

    def _search_table(self, connection, table: str, search_columns: tuple[str, ...], keywords: list[str]):
        # table/search_columns взяты только из фиксированных констант
        # модуля (_METAL_SEARCH_TARGETS/_ADDITIVE_SEARCH_TARGETS), не от
        # пользователя — безопасно подставлять напрямую в SQL, как и в
        # NsiBrowserService.
        or_clauses = " OR ".join(f'PY_LOWER("{col}") LIKE ?' for col in search_columns)
        where_per_keyword = " OR ".join(f"({or_clauses})" for _ in keywords)
        params = [f"%{kw.lower()}%" for kw in keywords for _ in search_columns]
        sql = f'SELECT * FROM "{table}" WHERE {where_per_keyword} LIMIT 3'
        return connection.execute(sql, params).fetchall()
