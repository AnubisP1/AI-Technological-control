-- ============================================================
-- 05. Таблицы совместимости — ядро логики подбора в приложении.
-- Аналог equipment_type_* из механообработки, но для аддитивных
-- технологий: печать не "обрабатывает материал", а "строит из него",
-- поэтому добавлена отдельная совместимость с постобработкой.
--
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/05_compatibility.sql
-- ============================================================

-- Матрица: какие группы материалов поддерживает тип принтера
-- (главное правило: FDM печатает филамент, SLA/DLP/MSLA — смолу, SLS — порошок;
-- но внутри технологии не все принтеры поддерживают все марки — напр. нужен heated chamber)
CREATE TABLE printer_type_material_group (
    printer_type_id      INTEGER NOT NULL REFERENCES printer_type(id),
    am_material_group_id  INTEGER NOT NULL REFERENCES am_material_group(id),
    PRIMARY KEY (printer_type_id, am_material_group_id)
);

-- Матрица: какая постобработка нужна для группы материала, с порядком в цепочке
-- (напр. SLA-смола ТРЕБУЕТ мойку+дозасветку; FDM PLA обычно не требует ничего)
CREATE TABLE material_group_pp_tooling_type (
    am_material_group_id  INTEGER NOT NULL REFERENCES am_material_group(id),
    pp_tooling_type_id     INTEGER NOT NULL REFERENCES pp_tooling_type(id),
    is_required              BOOLEAN NOT NULL DEFAULT 0,
    typical_order             SMALLINT,   -- порядок в цепочке постобработки (мойка -> сушка -> дозасветка -> ...)
    PRIMARY KEY (am_material_group_id, pp_tooling_type_id)
);

-- Матрица: какая постобработка в принципе применима к технологии печати
-- (напр. удаление поддержек актуально для FDM и SLA, просеивание порошка — только для SLS)
CREATE TABLE am_technology_pp_tooling_type (
    am_technology_id     INTEGER NOT NULL REFERENCES am_technology(id),
    pp_tooling_type_id     INTEGER NOT NULL REFERENCES pp_tooling_type(id),
    PRIMARY KEY (am_technology_id, pp_tooling_type_id)
);

-- Точечные исключения совместимости принтер-материал (закрытые экосистемы, картриджи):
-- точная совместимость конкретной модели принтера с конкретным материалом, когда
-- общего правила по группам недостаточно (напр. Formlabs принтер работает только
-- со своими картриджами смолы)
CREATE TABLE printer_material_override (
    printer_model_id   INTEGER NOT NULL REFERENCES printer_model(id),
    am_material_id       INTEGER NOT NULL REFERENCES am_material(id),
    is_allowed              BOOLEAN NOT NULL,
    reason                   TEXT,
    PRIMARY KEY (printer_model_id, am_material_id)
);

-- Проверка геометрической применимости: материал реально влезает в камеру постобработки
-- (не таблица связей типов, а логика на уровне приложения через chamber_volume_* в pp_tooling
-- и build_volume_* в printer_model — см. 00_ER_diagram.md, "Правила совместимости")
