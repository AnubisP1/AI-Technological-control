-- ============================================================
-- 01. Базовые классификаторы (справочники типов) — аддитивные технологии
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/01_classifiers.sql
-- ============================================================

-- Классификатор технологий аддитивного производства (FDM/SLA/DLP/MSLA/SLS)
CREATE TABLE am_technology (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- 'FDM', 'SLA', 'DLP', 'MSLA', 'SLS'
    name            VARCHAR(200) NOT NULL,           -- 'Наплавление нитью (FDM/FFF)', 'Стереолитография (SLA)', ...
    process_family  VARCHAR(30)  NOT NULL
                     CHECK (process_family IN ('material_extrusion','vat_photopolymerization','powder_bed_fusion')),
    description     TEXT
);

-- Классификатор типов принтеров внутри технологии
CREATE TABLE printer_type (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    am_technology_id    INTEGER NOT NULL REFERENCES am_technology(id),
    code                VARCHAR(30) NOT NULL UNIQUE,   -- 'FDM_CARTESIAN', 'FDM_COREXY', 'FDM_DELTA', 'SLA_LASER', 'MSLA_LCD', 'SLS_LASER'
    name                VARCHAR(200) NOT NULL,
    description         TEXT
);

-- Группы материалов печати по химической природе, привязаны к технологии
CREATE TABLE am_material_group (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    am_technology_id INTEGER NOT NULL REFERENCES am_technology(id),
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- 'PLA', 'PETG', 'ABS', 'ASA', 'TPU', 'NYLON', 'PC', 'RESIN_STD', 'RESIN_TOUGH', 'RESIN_CAST', 'PA12_SLS', 'TPU_SLS'
    name            VARCHAR(200) NOT NULL,           -- 'PLA (полилактид)', 'ABS', 'Смола стандартная', 'Полиамид PA12 (SLS)'
    physical_form   VARCHAR(20)  NOT NULL
                     CHECK (physical_form IN ('filament','resin','powder')),
    description     TEXT
);

-- Категории оснастки/оборудования постобработки
CREATE TABLE pp_tooling_category (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- 'WASH', 'CURE', 'SUPPORT_REMOVAL', 'SURFACE_FINISH', 'BED_ADHESION', 'POWDER_HANDLING'
    name            VARCHAR(200) NOT NULL            -- 'Отмывка', 'УФ-дозасветка', 'Удаление поддержек', 'Финишная обработка поверхности', 'Адгезия к столу', 'Работа с порошком'
);

-- Типы оснастки и оборудования постобработки (мойка, засветка, удаление поддержек и т.п.)
CREATE TABLE pp_tooling_type (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id         INTEGER NOT NULL REFERENCES pp_tooling_category(id),
    code                VARCHAR(30) NOT NULL UNIQUE,  -- 'WASH_STATION_IPA', 'UV_CURE_CHAMBER', 'SUPPORT_CUTTER', 'SANDING_KIT', 'BUILD_PLATE_PEI', 'SIEVE_STATION'
    name                VARCHAR(200) NOT NULL,         -- 'Ультразвуковая мойка с ИПС', 'УФ-камера дозасветки', 'Кусачки/нож для поддержек', 'Набор наждачной бумаги', 'Стол с PEI-покрытием', 'Станция просеивания порошка'
    description          TEXT
);

-- Виды исходной геометрии/файла модели, поступающей на печать
CREATE TABLE model_source_type (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- 'STL', 'STEP', 'OBJ', '3MF'
    name            VARCHAR(200) NOT NULL
);
