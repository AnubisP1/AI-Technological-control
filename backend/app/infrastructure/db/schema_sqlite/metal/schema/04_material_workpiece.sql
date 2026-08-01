-- ============================================================
-- 04. Справочник материалов и заготовок
-- Адаптировано из ../../../../../../БД НСИ/schema/04_material_workpiece.sql
--
-- Отличие от оригинала: FK workpiece.part_id объявлен сразу здесь
-- (REFERENCES part(id)), а не добавлен позже через ALTER TABLE ...
-- ADD CONSTRAINT, т.к. SQLite не поддерживает добавление FK к уже
-- созданной таблице. SQLite не проверяет существование таблицы part
-- на момент CREATE TABLE (PRAGMA foreign_keys проверяется только при
-- DML), поэтому порядок файлов (part создаётся позже, в 06_process.sql)
-- не вызывает ошибки.
-- ============================================================

-- Марка материала (сталь 45, АМг6, СЧ20 и т.д.) — справочник марок материалов
CREATE TABLE material (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    material_group_id   INTEGER NOT NULL REFERENCES material_group(id),
    grade                VARCHAR(50)  NOT NULL UNIQUE,  -- 'Сталь 45', '12Х18Н10Т', 'АМг6', 'СЧ20', 'Л63'
    gost_standard         VARCHAR(50),                    -- 'ГОСТ 1050-2013'
    density_kg_m3          NUMERIC(10,2),
    tensile_strength_mpa   NUMERIC(10,2),                  -- предел прочности
    hardness_hb             NUMERIC(10,2),                  -- твёрдость по Бринеллю (для расчёта режимов резания)
    machinability_index     NUMERIC(4,2),                    -- коэфф. обрабатываемости (может переопределять material_group.machinability_index)
    description              TEXT
);

-- Типоразмер сортового проката/полуфабриката (справочник заготовок общего вида,
-- ещё не привязан к детали) — НСИ уровня "что можно заказать"
CREATE TABLE workpiece_blank (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    workpiece_type_id   INTEGER NOT NULL REFERENCES workpiece_type(id),
    material_id          INTEGER NOT NULL REFERENCES material(id),
    designation           VARCHAR(200) NOT NULL,           -- 'Круг Ø40 ГОСТ 2590-2006', 'Лист 10 ГОСТ 19903-2015'

    -- Геометрия — заполняется по применимости (для прутка — диаметр+длина, для листа — толщина+размеры)
    diameter_mm            NUMERIC(10,2),
    thickness_mm            NUMERIC(10,2),
    width_mm                 NUMERIC(10,2),
    length_mm                 NUMERIC(10,2),

    weight_per_unit_kg        NUMERIC(10,3),
    description                 TEXT
);

-- Конкретная заготовка, привязанная к детали в техпроцессе
CREATE TABLE workpiece (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    workpiece_blank_id  INTEGER NOT NULL REFERENCES workpiece_blank(id),
    part_id              INTEGER REFERENCES part(id),      -- part создаётся в 06_process.sql, см. заголовок файла
    cut_length_mm         NUMERIC(10,2),                     -- длина отрезаемой заготовки под конкретную деталь
    weight_kg               NUMERIC(10,3),
    notes                    TEXT
);

CREATE INDEX idx_workpiece_blank_material ON workpiece_blank(material_id);
CREATE INDEX idx_workpiece_blank_type ON workpiece_blank(workpiece_type_id);
