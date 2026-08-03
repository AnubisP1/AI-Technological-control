-- ============================================================
-- 09. Коэффициенты режимов резания (Фаза 17, по решению пользователя
-- 2026-08-03: точный расчёт V/S/t/n/То, не оставлять графы ОК пустыми).
--
-- Источник формул и табличных коэффициентов — Справочник технолога-
-- машиностроителя (общеизвестная отраслевая методика, не выдуманные
-- числа): классическая эмпирическая формула скорости резания
--   V = Cv / (T^m * t^xv * S^yv) * Kv
-- где T — стойкость инструмента (мин, берётся из справочника константой
-- для данной пары инструмент/операция), t — глубина резания, S — подача,
-- Cv/m/xv/yv — табличные показатели по виду обработки и группе
-- инструмента, Kv — общий поправочный коэффициент (материал, состояние
-- поверхности заготовки и т.д. в этой модели уже учтён через
-- material_group.machinability_index — отдельно не хранится, чтобы не
-- дублировать один и тот же смысл в двух местах).
--
-- Каждая строка ОБЯЗАНА иметь source (проверяемая ссылка на таблицу
-- справочника) — не заводить коэффициент без указания, откуда он взят.
-- ============================================================

-- Материал режущей части инструмента — влияет на допустимую скорость
-- резания сильнее, чем что-либо ещё (твёрдый сплав режет в разы быстрее
-- быстрорежущей стали). tooling.material в текущей схеме хранит
-- конкретную марку ('Т15К6', 'Р6М5') свободным текстом — этот
-- классификатор группирует марки по признаку, который знает формула.
CREATE TABLE tool_material_group (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    code     VARCHAR(20) NOT NULL UNIQUE,   -- 'HSS' | 'CARBIDE'
    name      VARCHAR(100) NOT NULL
);

-- Связь конкретной марки инструментального материала (как она записана
-- в tooling.material) с группой — отдельная таблица, а не колонка в
-- tooling, чтобы не менять существующую seed-структуру tooling и не
-- терять уже читаемые designation/material.
CREATE TABLE tool_material_grade (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    grade                  VARCHAR(50) NOT NULL UNIQUE,  -- 'Т15К6', 'Р6М5' — дословно как в tooling.material
    tool_material_group_id   INTEGER NOT NULL REFERENCES tool_material_group(id)
);

-- Коэффициенты формулы скорости резания по виду обработки (operation_type)
-- и группе инструментального материала. Стойкость T — типовая для данного
-- сочетания (не варьируется по детали), указана явно, а не выведена.
CREATE TABLE cutting_mode_formula (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type_id           INTEGER NOT NULL REFERENCES operation_type(id),
    tool_material_group_id        INTEGER NOT NULL REFERENCES tool_material_group(id),
    tool_life_min                   NUMERIC(6,1) NOT NULL,  -- T, стойкость инструмента, мин
    cv                                NUMERIC(8,3) NOT NULL,
    m                                   NUMERIC(5,3) NOT NULL,
    xv                                   NUMERIC(5,3) NOT NULL,
    yv                                     NUMERIC(5,3) NOT NULL,
    source                                  TEXT NOT NULL,   -- 'Справочник технолога-машиностроителя, т.2, табл. 17' и т.п.
    UNIQUE (operation_type_id, tool_material_group_id)
);

-- Типовая подача по виду обработки и группе материала заготовки — в
-- практике технолога подача берётся табличным диапазоном (не считается
-- по отдельной формуле), окончательное значение выбирает технолог из
-- этого диапазона по шероховатости/точности. Модель берёт середину
-- диапазона, если система сама не может уточнить требование чертежа.
CREATE TABLE feed_reference (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type_id       INTEGER NOT NULL REFERENCES operation_type(id),
    material_group_id         INTEGER NOT NULL REFERENCES material_group(id),
    feed_mm_rev_min              NUMERIC(6,3) NOT NULL,
    feed_mm_rev_max               NUMERIC(6,3) NOT NULL,
    depth_of_cut_mm_min             NUMERIC(6,3),  -- NULL для сверления: глубина резания = D/2 сверла, не табличный диапазон
    depth_of_cut_mm_max               NUMERIC(6,3),
    source                              TEXT NOT NULL,
    UNIQUE (operation_type_id, material_group_id)
);
