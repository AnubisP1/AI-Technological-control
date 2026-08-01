-- ============================================================
-- 03. Справочник материалов печати (филамент/смола/порошок)
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/03_materials.sql
-- ============================================================

CREATE TABLE material_manufacturer (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    VARCHAR(200) NOT NULL UNIQUE   -- 'eSUN', 'Bambu Lab', 'Formlabs', 'EOS', 'Polymaker'
);

-- Справочник конкретных марок материалов печати (филамент/смола/порошок)
CREATE TABLE am_material (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    am_material_group_id     INTEGER NOT NULL REFERENCES am_material_group(id),
    manufacturer_id            INTEGER REFERENCES material_manufacturer(id),
    trade_name                   VARCHAR(200) NOT NULL,     -- 'eSUN PLA+', 'Bambu Lab PETG HF', 'Formlabs Grey Resin V5', 'EOS PA 2200'
    color                          VARCHAR(50),

    -- Форм-фактор и упаковка
    diameter_mm                     NUMERIC(6,2),             -- для филамента: 1.75 / 2.85
    spool_weight_kg                  NUMERIC(6,3),             -- для филамента
    bottle_volume_ml                   NUMERIC(10,2),           -- для смолы
    powder_batch_kg                     NUMERIC(10,2),           -- для порошка (SLS)

    -- Термические/механические свойства (значимы для подбора режимов и постобработки)
    density_g_cm3                        NUMERIC(6,3),
    print_temp_min_c                       INTEGER,             -- для филамента — температура сопла
    print_temp_max_c                        INTEGER,
    bed_temp_c                               INTEGER,
    tensile_strength_mpa                      NUMERIC(10,2),
    elongation_at_break_pct                    NUMERIC(6,2),
    heat_deflection_temp_c                      NUMERIC(6,2),

    requires_heated_chamber                       BOOLEAN DEFAULT 0,   -- напр. ABS/PC/нейлон часто требуют
    requires_dry_storage                           BOOLEAN DEFAULT 0,   -- гигроскопичные материалы (нейлон, PVA)
    is_soluble_support                              BOOLEAN DEFAULT 0,   -- PVA/HIPS как растворимая поддержка

    gost_or_standard                                 VARCHAR(50),
    description                                        TEXT
);

-- Партии материала на складе — для трассируемости и списания
CREATE TABLE am_material_batch (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    am_material_id   INTEGER NOT NULL REFERENCES am_material(id),
    batch_number       VARCHAR(100),
    received_at           DATE,
    expiry_date            DATE,
    remaining_qty            NUMERIC(10,3),   -- кг или мл, в единицах материала
    storage_location          VARCHAR(100),
    notes                       TEXT
);

CREATE INDEX idx_am_material_group ON am_material(am_material_group_id);

-- am_material.requires_dry_storage: материал гигроскопичен — требует сушки/
-- герметичного хранения (нейлон, PVA, некоторые PETG)
