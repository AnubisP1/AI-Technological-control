"""Базовая (не-LLM) реализация ITextGenerator — offline, без сети.
Служит основным путём при отсутствии/ошибке LLM-провайдера (см.
YandexGptTextGenerator) и самостоятельной офлайн-реализацией, когда
пользователь не настроил облачный API (см. dev/QUESTIONS.md №12).

Не пытается писать связную "человеческую" прозу — просто перечисляет
уже готовые находки в порядке важности. Хуже читается, чем текст LLM,
но не выдумывает ничего, чего нет в переданных фактах.
"""

from __future__ import annotations

from app.domain.kd_review.text_generator_port import GeneratedText


class TemplateTextGenerator:
    def summarize_review(self, *, facts: dict) -> GeneratedText:
        findings = facts.get("findings", [])
        if not findings:
            return GeneratedText(
                text="Значимых замечаний по результатам сверки с НСИ не выявлено.",
                generated_by="template",
            )

        severity_labels = {"blocking": "Критично", "warning": "Внимание", "info": "Информация"}
        lines = [
            f"{severity_labels.get(f['severity'], f['severity'])}: {f['message']}"
            for f in findings
        ]
        return GeneratedText(text=" ".join(lines), generated_by="template")
