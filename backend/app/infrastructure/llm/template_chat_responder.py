"""Базовая (не-LLM) реализация IChatResponder — offline, без сети.
Служит основным путём при отсутствии/ошибке LLM-провайдера и
самостоятельной офлайн-реализацией, когда пользователь не настроил
облачный API (см. dev/QUESTIONS.md №12, тот же принцип, что
TemplateTextGenerator для резюме отчёта КД).

Не формулирует связную прозу — просто перечисляет найденные по вопросу
факты из справочников НСИ. Хуже читается, чем ответ LLM, но не
выдумывает ничего, чего нет в переданном контексте.
"""

from __future__ import annotations

from app.domain.assistant.chat_responder_port import ChatReply


class TemplateChatResponder:
    def reply(self, *, question: str, context_facts: dict) -> ChatReply:
        matches = context_facts.get("matches", [])
        if not matches:
            return ChatReply(
                text=(
                    "По вашему вопросу не найдено записей в базе НСИ (материалы, оборудование, "
                    "оснастка, операции, режимы резания). Попробуйте переформулировать вопрос, "
                    "используя точные термины — например, марку материала ('Сталь 45'), код "
                    "операции ('TURN_ROUGH') или модель станка ('16К20')."
                ),
                generated_by="template",
            )

        lines = [f"По вашему вопросу найдено в базе НСИ ({len(matches)}):"]
        for m in matches:
            lines.append(f"— {m['table']} · {m['summary']}")
        return ChatReply(text="\n".join(lines), generated_by="template")
