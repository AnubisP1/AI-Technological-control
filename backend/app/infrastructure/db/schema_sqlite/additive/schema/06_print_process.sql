-- ============================================================
-- 06. Технологический процесс печати: деталь, модель, job печати,
-- параметры печати, шаги постобработки
--
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/06_print_process.sql
-- TIMESTAMP NOT NULL DEFAULT now() -> TEXT NOT NULL DEFAULT (datetime('now'))
-- ============================================================

-- Деталь/изделие для печати
CREATE TABLE am_part (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    designation     VARCHAR(100) NOT NULL UNIQUE,   -- обозначение по чертежу/наименованию модели
    name            VARCHAR(300) NOT NULL,
    model_source_type_id INTEGER REFERENCES model_source_type(id),
    file_reference    VARCHAR(500),                  -- путь/ссылка на файл модели (во внешнем хранилище/PDM)
    bounding_x_mm       NUMERIC(10,2),                -- габариты детали — для проверки помещаемости в build volume
    bounding_y_mm        NUMERIC(10,2),
    bounding_z_mm          NUMERIC(10,2),
    notes                     TEXT
);

-- Технологический процесс печати (вариант ТП на деталь — может быть несколько
-- вариантов под разную технологию/материал, как process у механообработки)
CREATE TABLE print_process (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    am_part_id            INTEGER NOT NULL REFERENCES am_part(id),
    code                    VARCHAR(50) NOT NULL,
    name                      VARCHAR(300),
    am_technology_id           INTEGER NOT NULL REFERENCES am_technology(id),
    printer_type_id              INTEGER REFERENCES printer_type(id),
    am_material_id                 INTEGER NOT NULL REFERENCES am_material(id),
    production_type                  VARCHAR(30) CHECK (production_type IN ('prototype','single','serial')),
    status                             VARCHAR(20) NOT NULL DEFAULT 'draft'
                                       CHECK (status IN ('draft','approved','archived')),
    created_at                          TEXT NOT NULL DEFAULT (datetime('now')),
    approved_at                          TEXT,
    UNIQUE (am_part_id, code)
);

-- Параметры печати (слайсер-настройки), 1:1 с print_process
CREATE TABLE print_parameters (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    print_process_id      INTEGER NOT NULL UNIQUE REFERENCES print_process(id) ON DELETE CASCADE,

    -- Общие
    layer_height_mm          NUMERIC(10,4),
    infill_percent              NUMERIC(5,2),
    infill_pattern                VARCHAR(30),        -- 'grid', 'gyroid', 'honeycomb', NULL для SLA/SLS
    wall_count                      SMALLINT,           -- количество периметров (FDM)
    top_bottom_layers                 SMALLINT,

    -- FDM-специфичные
    nozzle_temp_c                       INTEGER,
    bed_temp_c                            INTEGER,
    print_speed_mm_s                        NUMERIC(10,2),
    support_needed                            BOOLEAN DEFAULT 0,
    support_material_id                        INTEGER REFERENCES am_material(id),  -- отдельный материал поддержек (напр. PVA)

    -- SLA/DLP/MSLA-специфичные
    exposure_time_s                              NUMERIC(10,2),
    bottom_exposure_time_s                         NUMERIC(10,2),
    lift_speed_mm_min                                NUMERIC(10,2),

    -- SLS-специфичные
    bed_temp_powder_c                                  INTEGER,
    laser_scan_speed_mm_s                                NUMERIC(10,2),

    -- Расчётные результаты (аналог То в механообработке)
    estimated_print_time_min                               NUMERIC(10,2),
    estimated_material_g                                     NUMERIC(10,2),

    notes                                                      TEXT
);

-- Упорядоченный шаг постобработки после печати (аналог transition — упорядоченная
-- последовательность операций после печати)
CREATE TABLE postprocessing_step (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    print_process_id      INTEGER NOT NULL REFERENCES print_process(id) ON DELETE CASCADE,
    sequence_no             INTEGER NOT NULL,
    pp_tooling_type_id        INTEGER NOT NULL REFERENCES pp_tooling_type(id),
    pp_tooling_id                INTEGER REFERENCES pp_tooling(id),   -- конкретное оборудование, если закреплено
    description                    TEXT NOT NULL,                     -- 'Отмывка в ИПС 5 мин', 'УФ-дозасветка 15 мин при 60°C'
    duration_min                     NUMERIC(10,2),
    temperature_c                      INTEGER,
    UNIQUE (print_process_id, sequence_no)
);

CREATE INDEX idx_print_process_part ON print_process(am_part_id);
CREATE INDEX idx_postprocessing_step_process ON postprocessing_step(print_process_id);
