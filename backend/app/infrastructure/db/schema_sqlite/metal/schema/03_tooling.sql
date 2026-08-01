-- ============================================================
-- 03. Справочник оснастки и инструмента
-- Адаптировано из ../../../../../../БД НСИ/schema/03_tooling.sql
-- ============================================================

CREATE TABLE tooling_manufacturer (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    VARCHAR(200) NOT NULL UNIQUE   -- 'Sandvik Coromant', 'ВНИИинструмент', 'Iskar'
);

-- Справочник оснастки и инструмента (типоразмеры/артикулы)
CREATE TABLE tooling (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tooling_type_id     INTEGER NOT NULL REFERENCES tooling_type(id),
    manufacturer_id     INTEGER REFERENCES tooling_manufacturer(id),
    designation         VARCHAR(200) NOT NULL,        -- обозначение/артикул: 'Резец 2102-0055 Т15К6', 'Сверло Ø10 Р6М5 ГОСТ 10903-77'
    gost_standard       VARCHAR(50),

    -- Геометрия / параметры, значимые для подбора и совместимости
    diameter_mm          NUMERIC(10,3),                -- диаметр (для свёрл, фрез, патронов)
    length_mm             NUMERIC(10,2),
    shank_type            VARCHAR(50),                  -- 'Морзе 3', 'Цилиндрический 10мм', 'ISO 40', 'HSK-A63' — должен матчиться с equipment_model.spindle_nose_type
    max_clamping_diameter_mm NUMERIC(10,2),              -- для патронов/тисков — макс. размер зажимаемой заготовки
    min_clamping_diameter_mm NUMERIC(10,2),

    material              VARCHAR(100),                 -- материал режущей части: 'Т15К6', 'Р6М5', 'ВК8'

    measuring_range_min   NUMERIC(10,3),                 -- для измерительного инструмента
    measuring_range_max   NUMERIC(10,3),
    measuring_accuracy_mm NUMERIC(10,4),

    description            TEXT
);

-- Физическая единица оснастки (конкретный экземпляр на складе/в цехе, опционально —
-- если нужен учёт по инвентарным номерам, как со станками)
CREATE TABLE tooling_instance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tooling_id      INTEGER NOT NULL REFERENCES tooling(id),
    inventory_number VARCHAR(50) UNIQUE,
    storage_location VARCHAR(100),
    status           VARCHAR(20) NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active', 'repair', 'decommissioned')),
    wear_percent      NUMERIC(5,2)                      -- % износа, если ведётся учёт стойкости
);

CREATE INDEX idx_tooling_type ON tooling(tooling_type_id);

-- tooling.shank_type: тип хвостовика/крепления — сверяется с
-- equipment_model.spindle_nose_type при проверке совместимости
