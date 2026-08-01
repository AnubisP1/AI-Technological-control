-- ============================================================
-- 08. Правила подбора по назначению детали и условиям эксплуатации
-- (для БПЛА/дронов и аналогичных изделий)
--
-- Отвечает на вопрос: "деталь такого-то класса, в таких-то условиях
-- эксплуатации → какая технология/материал/принтер рекомендуются
-- и почему". Это отдельный слой поверх 05_compatibility.sql —
-- та таблица про физическую СОВМЕСТИМОСТЬ (может ли принтер вообще
-- напечатать материал), а эта — про инженерную ЦЕЛЕСООБРАЗНОСТЬ
-- выбора конкретного материала для конкретного назначения.
--
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/08_application_rules.sql
-- ============================================================

-- Классификатор деталей БПЛА по функциональному назначению
-- (обтекатель, корпус, винт, кронштейн и т.п.)
CREATE TABLE part_application_class (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(30)  NOT NULL UNIQUE,   -- 'NOSE_CONE', 'FUSELAGE', 'WING', 'PROPELLER', 'MOUNT_BRACKET', 'LANDING_GEAR', 'DUCT', 'ANTENNA_HOUSING'
    name            VARCHAR(200) NOT NULL,           -- 'Носовой обтекатель', 'Корпус (фюзеляж)', 'Крыло/консоль', 'Винт (пропеллер)', 'Кронштейн навески', 'Стойка шасси', 'Воздуховод/канал', 'Кожух антенны'
    description     TEXT
);

-- Условия эксплуатации как независимые оси нагрузки: температура, скорость
-- потока, УФ, вибрация и т.д. — каждая ось отдельной строкой с диапазоном,
-- чтобы деталь могла попадать сразу под несколько условий
CREATE TABLE operating_condition (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_type  VARCHAR(20) NOT NULL
                    CHECK (condition_type IN ('temperature','airspeed','uv_exposure','vibration','impact','humidity','chemical')),
    code            VARCHAR(30) NOT NULL UNIQUE,   -- 'TEMP_HIGH_60_80', 'AIRSPEED_HIGH_150PLUS', 'UV_OUTDOOR_LONGTERM', 'VIBRATION_HIGH_MOTOR_MOUNT'
    name            VARCHAR(200) NOT NULL,           -- 'Высокая температура 60-80°C (близко к двигателю/электронике)', 'Высокая скорость набегающего потока >150 км/ч', 'Длительная эксплуатация на улице под УФ', 'Высокая вибрация (крепление двигателя)'
    range_min       NUMERIC(10,2),                    -- нижняя граница диапазона (для temperature — °C, для airspeed — км/ч)
    range_max       NUMERIC(10,2),
    unit             VARCHAR(20),                       -- '°C', 'км/ч', NULL для качественных категорий
    description        TEXT
);

-- Источник инженерной рекомендации — для трассируемости и оценки достоверности
CREATE TABLE recommendation_source (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type     VARCHAR(20) NOT NULL
                    CHECK (source_type IN ('community_practice','manufacturer_datasheet','standard','forum_thread','internal_test')),
    title           VARCHAR(300) NOT NULL,   -- 'Типовая практика сообщества FPV/DIY-дронов', 'Datasheet производителя филамента', 'Внутренние испытания предприятия'
    url             VARCHAR(500),             -- ссылка, если есть конкретный источник (форум/статья) — NULL для обобщённой практики
    reliability     VARCHAR(20) NOT NULL DEFAULT 'medium'
                    CHECK (reliability IN ('low','medium','high')),  -- насколько источнику можно доверять как основанию для прод-решения
    notes           TEXT
);

-- Ядро: связывает класс детали + условие эксплуатации → рекомендуемый
-- материал/технологию, с обоснованием и источником
CREATE TABLE application_material_recommendation (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    part_application_class_id    INTEGER NOT NULL REFERENCES part_application_class(id),
    operating_condition_id         INTEGER REFERENCES operating_condition(id),  -- NULL = рекомендация базовая, без учёта доп. условия
    am_material_group_id             INTEGER NOT NULL REFERENCES am_material_group(id),
    am_technology_id                   INTEGER NOT NULL REFERENCES am_technology(id),

    priority                             SMALLINT NOT NULL DEFAULT 1,   -- 1 = основная рекомендация, 2+ = альтернативы по убыванию предпочтения
    min_infill_percent                     NUMERIC(5,2),                  -- минимальная рекомендуемая плотность заполнения для этого назначения
    recommended_wall_count                   SMALLINT,
    orientation_note                           TEXT,                        -- 'Печатать вертикально для нагрузки вдоль оси', 'Ориентировать слои перпендикулярно направлению изгиба'

    recommendation_source_id                     INTEGER NOT NULL REFERENCES recommendation_source(id),
    rationale                                      TEXT NOT NULL,            -- почему именно этот материал/технология — обязательное текстовое обоснование

    UNIQUE (part_application_class_id, operating_condition_id, am_material_group_id, am_technology_id)
);

-- Рекомендация типа принтера под класс детали с учётом минимальных габаритов рабочей области
CREATE TABLE application_printer_recommendation (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    part_application_class_id    INTEGER NOT NULL REFERENCES part_application_class(id),
    printer_type_id                INTEGER NOT NULL REFERENCES printer_type(id),
    min_build_volume_x_mm            NUMERIC(10,2),   -- минимальные требования к рабочей области под этот класс детали
    min_build_volume_y_mm             NUMERIC(10,2),
    min_build_volume_z_mm              NUMERIC(10,2),
    priority                             SMALLINT NOT NULL DEFAULT 1,
    recommendation_source_id               INTEGER NOT NULL REFERENCES recommendation_source(id),
    rationale                               TEXT NOT NULL
);

-- Связь класса детали с типичными условиями эксплуатации (многие-ко-многим):
-- позволяет приложению при выборе класса детали сразу подсказать "для этого
-- класса обычно значимы такие-то условия", не заставляя перебирать всё вручную
CREATE TABLE part_application_class_typical_condition (
    part_application_class_id  INTEGER NOT NULL REFERENCES part_application_class(id),
    operating_condition_id       INTEGER NOT NULL REFERENCES operating_condition(id),
    PRIMARY KEY (part_application_class_id, operating_condition_id)
);

-- Расширение am_part: привязка к классу применения (для приложений БПЛА)
ALTER TABLE am_part
    ADD COLUMN part_application_class_id INTEGER REFERENCES part_application_class(id);

CREATE INDEX idx_amr_class ON application_material_recommendation(part_application_class_id);
CREATE INDEX idx_amr_condition ON application_material_recommendation(operating_condition_id);
CREATE INDEX idx_apr_class ON application_printer_recommendation(part_application_class_id);
