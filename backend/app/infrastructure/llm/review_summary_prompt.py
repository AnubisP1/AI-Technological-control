"""Общий системный промпт и построение пользовательского сообщения для
резюме отчёта КД (Модуль 1.2) — используется ОБОИМИ провайдерами
(QwenTextGenerator — локальный, PolzaTextGenerator — облачный), чтобы
не дублировать и не рассинхронизировать формулировку антигаллюцинационных
ограничений между реализациями одного порта ITextGenerator.
"""

from __future__ import annotations

SYSTEM_PROMPT = (
    "Ты — технолог машиностроительного производства, эксперт по нормативно-"
    "справочной информации (НСИ) и технологичности деталей. Тебе дан список "
    "находок по результатам сверки чертежа детали со справочником НСИ, "
    "подобранный материал (если найден) и ПОЛНЫЙ список материалов из "
    "справочника с их технологическими свойствами (плотность, предел "
    "прочности, твёрдость по Бринеллю или Роквеллу, красностойкость для "
    "инструментальных сталей, индекс обрабатываемости резанием — чем выше "
    "индекс, тем легче материал обрабатывается, — химический состав, режим "
    "термообработки и типовое применение марки).\n\n"
    "Сформулируй связный анализ на русском языке (4-7 предложений) для "
    "главного технолога:\n"
    "1. Кратко резюмируй находки сверки.\n"
    "2. Если материал найден — дай короткую оценку его технологичности "
    "(обрабатываемость, прочность, требуемая термообработка) на основе "
    "переданных свойств.\n"
    "3. Если среди материалов справочника есть более технологичный аналог "
    "(выше индекс обрабатываемости при сопоставимой или большей прочности, "
    "либо более подходящий по типовому применению) — явно предложи его как "
    "альтернативу с обоснованием по цифрам и назначению.\n\n"
    "СТРОГО используй ТОЛЬКО переданные факты и цифры — не придумывай марки, "
    "ГОСТы, свойства, химсостав или находки, которых нет во входных данных. "
    "Если материал не найден или список материалов пуст, честно скажи об "
    "этом, не предлагай выдуманную замену."
)


def format_material(m: dict) -> str:
    parts = [m["grade"]]
    if m.get("gost_standard"):
        parts.append(m["gost_standard"])
    props = []
    if m.get("density_kg_m3") is not None:
        props.append(f"плотность {m['density_kg_m3']} кг/м³")
    if m.get("tensile_strength_mpa") is not None:
        props.append(f"предел прочности {m['tensile_strength_mpa']} МПа")
    if m.get("hardness_hb") is not None:
        props.append(f"твёрдость {m['hardness_hb']} HB")
    if m.get("hardness_hrc") is not None:
        props.append(f"твёрдость {m['hardness_hrc']} HRC")
    if m.get("red_hardness_c") is not None:
        props.append(f"красностойкость {m['red_hardness_c']}°C")
    if m.get("machinability_index") is not None:
        props.append(f"индекс обрабатываемости {m['machinability_index']}")
    if m.get("chemical_composition"):
        props.append(f"состав: {m['chemical_composition']}")
    if m.get("heat_treatment"):
        props.append(f"термообработка: {m['heat_treatment']}")
    if m.get("application"):
        props.append(f"применение: {m['application']}")
    if props:
        parts.append("(" + ", ".join(props) + ")")
    return " ".join(parts)


def build_user_prompt(facts: dict) -> str:
    findings = facts.get("findings", [])
    findings_text = "\n".join(f"- [{f['severity']}] {f['message']}" for f in findings) or "Находок нет."

    matched = facts.get("matched_material")
    matched_text = format_material(matched) if matched else "не найден в справочнике"

    candidates = facts.get("candidate_materials", [])
    candidates_text = "\n".join(f"- {format_material(m)}" for m in candidates) or "Справочник пуст."

    return (
        f"Находки сверки КД:\n{findings_text}\n\n"
        f"Подобранный материал: {matched_text}\n\n"
        f"Полный список материалов в справочнике НСИ:\n{candidates_text}"
    )
