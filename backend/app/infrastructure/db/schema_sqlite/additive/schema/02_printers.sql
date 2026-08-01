-- ============================================================
-- 02. Справочник принтеров
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/02_printers.sql
-- ============================================================

CREATE TABLE printer_manufacturer (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    VARCHAR(200) NOT NULL UNIQUE,   -- 'Bambu Lab', 'Prusa Research', 'Formlabs', 'Anycubic', 'EOS'
    country VARCHAR(100)
);

-- Справочник моделей 3D-принтеров с паспортными характеристиками
CREATE TABLE printer_model (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_type_id          INTEGER NOT NULL REFERENCES printer_type(id),
    manufacturer_id           INTEGER REFERENCES printer_manufacturer(id),
    model_name                 VARCHAR(200) NOT NULL,     -- 'Bambu Lab X1-Carbon', 'Prusa MK4', 'Formlabs Form 3', 'EOS P 396'

    -- Рабочая область (build volume) — для FDM/SLA в мм, для SLS может быть больше
    build_volume_x_mm          NUMERIC(10,2),
    build_volume_y_mm          NUMERIC(10,2),
    build_volume_z_mm          NUMERIC(10,2),

    -- Точность/разрешение
    layer_height_min_mm         NUMERIC(10,4),
    layer_height_max_mm          NUMERIC(10,4),
    xy_resolution_mm               NUMERIC(10,4),           -- для SLA/DLP/MSLA — разрешение матрицы/лазера в плоскости XY
    positioning_accuracy_mm         NUMERIC(10,4),

    -- FDM-специфичные ТХ (NULL для других технологий)
    nozzle_diameter_mm                NUMERIC(10,3),
    max_nozzle_temp_c                  INTEGER,
    max_bed_temp_c                      INTEGER,
    number_of_extruders                  SMALLINT,
    heated_chamber                        BOOLEAN,

    -- SLA/DLP/MSLA-специфичные ТХ
    light_source                          VARCHAR(30),        -- 'laser', 'dlp_projector', 'lcd_masking'
    wavelength_nm                          INTEGER,

    -- SLS-специфичные ТХ
    laser_power_w                           NUMERIC(10,2),
    chamber_temp_max_c                       INTEGER,

    is_industrial                             BOOLEAN NOT NULL DEFAULT 0,
    description                                 TEXT,

    UNIQUE (manufacturer_id, model_name)
);

-- Конкретные физические единицы принтеров на предприятии
CREATE TABLE printer (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    printer_model_id     INTEGER NOT NULL REFERENCES printer_model(id),
    inventory_number       VARCHAR(50) UNIQUE,
    location                 VARCHAR(100),                 -- участок/помещение
    firmware_version           VARCHAR(50),
    commissioned_at              DATE,
    status                        VARCHAR(20) NOT NULL DEFAULT 'active'
                                  CHECK (status IN ('active', 'maintenance', 'decommissioned')),
    total_print_hours              NUMERIC(12,2) DEFAULT 0,
    notes                             TEXT
);

CREATE INDEX idx_printer_model ON printer(printer_model_id);
CREATE INDEX idx_printer_model_type ON printer_model(printer_type_id);

-- printer_model.light_source: источник засветки для фотополимерных технологий:
-- лазер (SLA), DLP-проектор, LCD-маска (MSLA)
