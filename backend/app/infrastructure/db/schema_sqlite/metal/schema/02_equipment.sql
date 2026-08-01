-- ============================================================
-- 02. Справочник станков (конкретное оборудование)
-- Адаптировано из ../../../../../../БД НСИ/schema/02_equipment.sql
-- ============================================================

CREATE TABLE equipment_manufacturer (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(200) NOT NULL UNIQUE,   -- 'Стерлитамак-Станкозавод', 'DMG MORI', 'HAAS', 'Рязанский СЗ'
    country         VARCHAR(100)
);

-- Справочник моделей станков (паспортные ТХ) — используется для подбора при формировании ТП
CREATE TABLE equipment_model (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_type_id   INTEGER NOT NULL REFERENCES equipment_type(id),
    manufacturer_id     INTEGER REFERENCES equipment_manufacturer(id),
    model_name          VARCHAR(200) NOT NULL,       -- '16К20', 'DMU 50', 'VF-2'
    control_system      VARCHAR(100),                 -- 'УЧПУ Н33', 'Siemens 840D', 'Fanuc 0i-MF', NULL = ручной/универсальный

    -- Рабочая зона / габариты обработки
    max_workpiece_diameter_mm   NUMERIC(10,2),        -- макс. диаметр обрабатываемой заготовки (для токарных)
    max_workpiece_length_mm     NUMERIC(10,2),        -- макс. длина обрабатываемой заготовки
    work_table_x_mm              NUMERIC(10,2),        -- размер стола X (для фрезерных/сверлильных)
    work_table_y_mm              NUMERIC(10,2),
    travel_x_mm                  NUMERIC(10,2),        -- ход по осям
    travel_y_mm                  NUMERIC(10,2),
    travel_z_mm                  NUMERIC(10,2),

    -- Приводные характеристики
    spindle_power_kw             NUMERIC(8,2),
    spindle_speed_min_rpm        INTEGER,
    spindle_speed_max_rpm        INTEGER,
    max_torque_nm                NUMERIC(10,2),

    -- Точность
    positioning_accuracy_mm      NUMERIC(8,4),

    -- Инструментальный магазин (для ЧПУ обрабатывающих центров)
    tool_magazine_capacity       INTEGER,

    -- Крепление инструмента/заготовки — тип интерфейса, важен для совместимости оснастки
    spindle_nose_type            VARCHAR(50),          -- 'ISO 40', 'BT40', 'HSK-A63', 'Морзе 4', 'Патрон 3-кул. 250мм'

    is_cnc                       BOOLEAN NOT NULL DEFAULT 0,
    description                  TEXT,

    UNIQUE (manufacturer_id, model_name)
);

-- Конкретные физические единицы оборудования на предприятии (инвентарные объекты)
CREATE TABLE equipment (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_model_id  INTEGER NOT NULL REFERENCES equipment_model(id),
    inventory_number    VARCHAR(50) UNIQUE,           -- инвентарный номер на предприятии
    workshop            VARCHAR(100),                  -- цех/участок
    workplace_code      VARCHAR(50),                   -- код рабочего места (для тех.документов)
    commissioned_at      DATE,
    status               VARCHAR(20) NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'maintenance', 'decommissioned')),
    notes                TEXT
);

CREATE INDEX idx_equipment_model ON equipment(equipment_model_id);
CREATE INDEX idx_equipment_model_type ON equipment_model(equipment_type_id);

-- spindle_nose_type: тип интерфейса крепления инструмента/патрона — ключевое поле
-- для проверки совместимости с оснасткой (сверяется с tooling.shank_type)
