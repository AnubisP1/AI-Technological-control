-- ============================================================
-- 04. Справочник оснастки и оборудования постобработки
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/04_postprocessing_tooling.sql
-- ============================================================

CREATE TABLE pp_tooling_manufacturer (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    VARCHAR(200) NOT NULL UNIQUE   -- 'Formlabs', 'Anycubic', 'Generic'
);

-- Оснастка и оборудование постобработки: мойки, камеры дозасветки, инструмент удаления поддержек и т.п.
CREATE TABLE pp_tooling (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    pp_tooling_type_id    INTEGER NOT NULL REFERENCES pp_tooling_type(id),
    manufacturer_id          INTEGER REFERENCES pp_tooling_manufacturer(id),
    designation                VARCHAR(200) NOT NULL,      -- 'Formlabs Form Wash', 'Formlabs Form Cure', 'Ультразвуковая ванна 6л'

    -- Параметры, значимые для подбора под конкретную деталь/принтер
    chamber_volume_x_mm          NUMERIC(10,2),             -- рабочий объём камеры мойки/засветки — должен вмещать деталь
    chamber_volume_y_mm           NUMERIC(10,2),
    chamber_volume_z_mm            NUMERIC(10,2),
    uv_wavelength_nm                 INTEGER,                 -- для камер дозасветки — должна соответствовать материалу
    max_temp_c                         INTEGER,

    description                          TEXT
);

CREATE INDEX idx_pp_tooling_type ON pp_tooling(pp_tooling_type_id);
