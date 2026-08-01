-- ============================================================
-- 06. Технологический процесс: деталь, ТП, операции, переходы
-- Адаптировано из ../../../../../../БД НСИ/schema/06_process.sql
--
-- Отличия от оригинала:
--   - ALTER TABLE workpiece ADD CONSTRAINT ... FOREIGN KEY убран:
--     SQLite не поддерживает добавление FK к существующей таблице,
--     FK на part(id) уже объявлен прямо в CREATE TABLE workpiece
--     (см. 04_material_workpiece.sql).
--   - TIMESTAMP NOT NULL DEFAULT now() -> TEXT NOT NULL DEFAULT (datetime('now'))
-- ============================================================

-- Деталь/изделие (минимально — то, что нужно приложению для привязки ТП;
-- геометрия/чертежи предполагаются во внешней CAD/PDM системе)
CREATE TABLE part (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    designation     VARCHAR(100) NOT NULL UNIQUE,    -- обозначение по чертежу: 'АБВ.001.005'
    name            VARCHAR(300) NOT NULL,            -- 'Вал выходной'
    drawing_number  VARCHAR(100),
    material_id     INTEGER REFERENCES material(id),  -- материал детали (может совпадать с материалом заготовки)
    notes           TEXT
);

-- Технологический процесс (вариант ТП) на деталь (может быть несколько
-- вариантов ТП на одну деталь — напр. для разных типов производства,
-- поэтому не 1:1 с part)
CREATE TABLE process (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id              INTEGER NOT NULL REFERENCES part(id),
    code                  VARCHAR(50) NOT NULL,          -- обозначение ТП
    name                   VARCHAR(300),
    workpiece_type_id      INTEGER REFERENCES workpiece_type(id),  -- вид исходной заготовки для этого варианта ТП
    workpiece_blank_id      INTEGER REFERENCES workpiece_blank(id), -- конкретный типоразмер проката
    production_type          VARCHAR(30) CHECK (production_type IN ('single','serial','mass')), -- тип производства (влияет на выбор оснастки/оборудования)
    status                    VARCHAR(20) NOT NULL DEFAULT 'draft'
                              CHECK (status IN ('draft','approved','archived')),
    created_at                TEXT NOT NULL DEFAULT (datetime('now')),
    approved_at                TEXT,
    UNIQUE (part_id, code)
);

-- Операция техпроцесса — строка маршрутной карты
CREATE TABLE operation (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id           INTEGER NOT NULL REFERENCES process(id) ON DELETE CASCADE,
    sequence_no            INTEGER NOT NULL,             -- номер операции по порядку, напр. 005, 010, 015...
    operation_type_id       INTEGER NOT NULL REFERENCES operation_type(id),
    name                     VARCHAR(300),                 -- 'Токарная черновая'
    equipment_model_id       INTEGER REFERENCES equipment_model(id),  -- выбранная модель станка (или equipment_id для конкретной единицы — см. ниже)
    equipment_id              INTEGER REFERENCES equipment(id),        -- опционально: закрепление за конкретной физ. единицей
    workshop                   VARCHAR(100),
    workplace_code               VARCHAR(50),
    setup_time_min                NUMERIC(10,2),          -- подготовительно-заключительное время (Тпз)
    piece_time_min                 NUMERIC(10,2),          -- штучное время (Тшт)
    labor_grade                     SMALLINT,               -- разряд работ (из WorkNorm)
    notes                             TEXT,
    UNIQUE (process_id, sequence_no)
);

-- Оснастка/инструмент, закреплённые за операцией (без детализации по переходам —
-- используется если переходы не детализируются отдельно)
CREATE TABLE operation_tooling (
    operation_id    INTEGER NOT NULL REFERENCES operation(id) ON DELETE CASCADE,
    tooling_id       INTEGER NOT NULL REFERENCES tooling(id),
    role              VARCHAR(30),  -- 'cutting', 'fixture', 'measuring', 'auxiliary'
    PRIMARY KEY (operation_id, tooling_id)
);

-- Переход операции — строка операционной карты с режимами резания
-- (самый детальный уровень техпроцесса, аналог модуля CuttingModes)
CREATE TABLE transition (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id     INTEGER NOT NULL REFERENCES operation(id) ON DELETE CASCADE,
    sequence_no        INTEGER NOT NULL,
    description          TEXT NOT NULL,                -- 'Точить поверхность 1 начерно'
    tooling_id             INTEGER REFERENCES tooling(id),  -- основной режущий инструмент перехода
    fixture_tooling_id      INTEGER REFERENCES tooling(id),  -- приспособление перехода (если отличается от операции)
    measuring_tooling_id     INTEGER REFERENCES tooling(id),  -- контрольный инструмент перехода

    -- Режимы резания (результат расчёта)
    cutting_speed_m_min        NUMERIC(10,2),   -- V
    spindle_speed_rpm            INTEGER,        -- n
    feed_mm_rev                   NUMERIC(10,4),  -- S
    depth_of_cut_mm                 NUMERIC(10,3),  -- t
    machining_time_min                NUMERIC(10,3),  -- То

    UNIQUE (operation_id, sequence_no)
);

CREATE INDEX idx_operation_process ON operation(process_id);
CREATE INDEX idx_transition_operation ON transition(operation_id);
CREATE INDEX idx_operation_equipment_model ON operation(equipment_model_id);
