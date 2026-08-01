-- ============================================================
-- 01. Базовые классификаторы (справочники типов)
-- Отвечают на вопрос "что вообще бывает", независимо от того,
-- что конкретно закуплено на предприятии.
--
-- Адаптировано из ../../../../../../БД НСИ/schema/01_classifiers.sql
-- (PostgreSQL -> SQLite): SERIAL -> INTEGER PRIMARY KEY AUTOINCREMENT,
-- COMMENT ON перенесены в обычные SQL-комментарии.
-- ============================================================

-- ---------- Типы станков (группы оборудования по ГОСТ/ОКОФ-подобной классификации) ----------
-- Классификатор типов станков — верхний уровень иерархии оборудования
CREATE TABLE equipment_type (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- напр. 'LATHE', 'MILL_VERT', 'MILL_HOR', 'DRILL', 'GRIND_CYL'
    name            VARCHAR(200) NOT NULL,           -- 'Токарный станок', 'Вертикально-фрезерный станок'
    parent_id       INTEGER REFERENCES equipment_type(id), -- иерархия: Металлорежущий -> Токарный -> Токарно-винторезный
    description     TEXT
);

-- ---------- Виды технологических операций (по ГОСТ 3.1109, классификатор ТП) ----------
-- Классификатор видов технологических операций
CREATE TABLE operation_type (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- '005', 'TURN', 'MILL', 'DRILL', 'GRIND', 'WELD'
    name            VARCHAR(200) NOT NULL,           -- 'Токарная', 'Фрезерная', 'Сверлильная', 'Шлифовальная'
    gost_code       VARCHAR(20),                     -- код операции по классификатору ЕСТПП, если нужен
    description     TEXT
);

-- ---------- Типы оснастки и инструмента ----------
CREATE TABLE tooling_category (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- 'CUTTING', 'FIXTURE', 'MEASURING', 'AUXILIARY'
    name            VARCHAR(200) NOT NULL            -- 'Режущий инструмент', 'Приспособление (зажимное)', 'Измерительный инструмент', 'Вспомогательная оснастка'
);

-- Классификатор типов оснастки/инструмента
CREATE TABLE tooling_type (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id     INTEGER NOT NULL REFERENCES tooling_category(id),
    code            VARCHAR(30)  NOT NULL UNIQUE,   -- 'CUTTER_TURN', 'DRILL_TWIST', 'CHUCK_3JAW', 'VISE', 'CALIPER'
    name            VARCHAR(200) NOT NULL,           -- 'Резец токарный', 'Сверло спиральное', 'Патрон трёхкулачковый', 'Тиски станочные', 'Штангенциркуль'
    gost_standard   VARCHAR(50),                     -- 'ГОСТ 18879-73' и т.п.
    description     TEXT
);

-- ---------- Группы материалов заготовок ----------
-- Группы конструкционных материалов заготовок
CREATE TABLE material_group (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- 'STEEL_CARBON', 'STEEL_ALLOY', 'STEEL_STAINLESS', 'ALUM', 'CAST_IRON', 'BRASS', 'TITAN'
    name            VARCHAR(200) NOT NULL,           -- 'Сталь углеродистая', 'Сталь легированная', 'Сталь нержавеющая', 'Алюминиевые сплавы', 'Чугун', 'Латунь', 'Титановые сплавы'
    machinability_index NUMERIC(4,2),                 -- коэффициент обрабатываемости резанием (справочно, база = сталь 45 = 1.0)
    description     TEXT
);

-- ---------- Виды заготовок (по способу получения, ГОСТ 3.1109) ----------
-- Виды заготовок по способу получения
CREATE TABLE workpiece_type (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(20)  NOT NULL UNIQUE,   -- 'ROLLED_BAR', 'ROLLED_SHEET', 'FORGING', 'CASTING', 'STAMPING', 'WELDMENT'
    name            VARCHAR(200) NOT NULL,           -- 'Прокат сортовой (пруток)', 'Прокат листовой', 'Поковка', 'Отливка', 'Штамповка', 'Сварная заготовка'
    description     TEXT
);
