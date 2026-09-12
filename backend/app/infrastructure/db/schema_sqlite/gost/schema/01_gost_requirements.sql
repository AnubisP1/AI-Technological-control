-- ============================================================
-- 01. Нормативные требования ГОСТ ЕСКД (оформление конструкторской
-- документации: чертежи, размеры, шероховатость, основные надписи и т.п.)
--
-- Назначение — не архив текста для чтения человеком (для этого есть
-- markdown/ рядом), а машиночитаемый источник для сверки извлечённых
-- из КД данных с требованиями (Модуль 1.1-1.2 по Техническому заданию):
-- каждый пункт стандарта — отдельная проверяемая строка с типом
-- требования и, где применимо, числовыми границами, а не текст,
-- который нужно заново парсить на лету.
--
-- Схема общая для обеих веток производства (Металл и Аддитив) —
-- ГОСТ серии 2.1xx/2.3xx (оформление КД) не специфичен для отрасли,
-- в отличие от схем БД НСИ/schema/ и БД НСИ Аддитив/, которые остаются
-- независимыми друг от друга по замыслу проекта (см. корневой CLAUDE.md).
--
-- Принцип нумерации пунктов: сохраняется буквально как в стандарте
-- (например "5.37", "Б.1", "А.2") — это единственный стабильный
-- человекочитаемый идентификатор, на который сами стандарты ссылаются
-- друг на друга и внутри себя.
-- ============================================================

-- ---------- Сам стандарт (документ) ----------
CREATE TABLE gost_standard (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    designation         VARCHAR(50)  NOT NULL UNIQUE,   -- 'ГОСТ 2.307-2011', 'ГОСТ Р 2.104-2023' — точно как на титуле
    title               VARCHAR(300) NOT NULL,           -- 'Нанесение размеров и предельных отклонений'
    series              VARCHAR(100),                     -- 'Единая система конструкторской документации'
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                            CHECK (status IN ('ACTIVE','SUPERSEDED','WITHDRAWN')),
    supersedes          VARCHAR(50),                      -- обозначение стандарта, который заменён (напр. 'ГОСТ 2.307-68')
    superseded_by       VARCHAR(50),                      -- обозначение стандарта, которым заменён этот (если status='SUPERSEDED')
    effective_date      DATE,                             -- дата введения в действие
    source_file         VARCHAR(300),                     -- относительный путь к исходному PDF в БД НСИ/ГОСТ/
    source_pages        INTEGER,                          -- количество страниц источника — для контроля полноты переноса
    notes               TEXT
);

-- ---------- Поправки/изменения к стандарту (ИУС) ----------
-- Официальные правки меняют текст конкретных пунктов со временем;
-- без этой таблицы при обновлении gost_clause.text терялась бы история
-- "что было напечатано / что должно быть", которая в проекте уже
-- зафиксирована как принцип (см. markdown-версии — амендменты не
-- скрываются, а документируются рядом с основным текстом).
CREATE TABLE gost_amendment (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    gost_standard_id    INTEGER NOT NULL REFERENCES gost_standard(id) ON DELETE CASCADE,
    ius_number          VARCHAR(20),                      -- '12', '10', '8' — номер выпуска ИУС
    ius_year            INTEGER,                           -- 2012, 2014, 2018
    approved_order      VARCHAR(50),                       -- номер приказа Росстандарта, если известен
    effective_date      DATE,
    UNIQUE (gost_standard_id, ius_number, ius_year)
);

-- ---------- Пункты стандарта — единица сверки ----------
CREATE TABLE gost_clause (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    gost_standard_id    INTEGER NOT NULL REFERENCES gost_standard(id) ON DELETE CASCADE,
    clause_number       VARCHAR(20)  NOT NULL,            -- '5.37', 'Б.1', 'А.2', '4.2.14' — как в тексте стандарта
    parent_clause_id    INTEGER REFERENCES gost_clause(id), -- иерархия пунктов (5.37 -> раздел 5), NULL для пунктов верхнего уровня
    section_title       VARCHAR(300),                      -- заголовок раздела/подраздела, если пункт его открывает
    clause_text         TEXT NOT NULL,                      -- полный текст пункта, без сокращений
    requirement_type    VARCHAR(30) NOT NULL DEFAULT 'PROCEDURAL'
                            CHECK (requirement_type IN (
                                'NUMERIC_LIMIT',   -- числовая граница проверяемого параметра ("не более 1 мм")
                                'ENUM_CHOICE',      -- выбор из фиксированного набора обозначений/знаков
                                'PROCEDURAL',        -- порядок выполнения, не сводится к одной проверяемой величине
                                'CROSS_REFERENCE',   -- пункт целиком отсылает к другому документу/пункту
                                'DEFINITION'          -- термин/определение, не требование
                            )),
    -- Заполняются только для requirement_type = 'NUMERIC_LIMIT'; для
    -- прочих типов остаются NULL — не считать NULL "нулевым" значением.
    parameter_name       VARCHAR(200),                     -- 'радиус скругления (не указываемый на изображении)'
    unit                  VARCHAR(20),                       -- 'мм', 'мм (в масштабе чертежа)', '°'
    comparison_op          VARCHAR(10) CHECK (comparison_op IN ('<=','<','=','>=','>','BETWEEN')),
    limit_value_min          NUMERIC(10,4),
    limit_value_max          NUMERIC(10,4),                   -- используется вместе с BETWEEN
    -- Заполняется только для requirement_type = 'ENUM_CHOICE': закрытый
    -- перечень допустимых значений. Хранится машиночитаемо (через ';'),
    -- а не только внутри clause_text — иначе проверку «значение входит
    -- в допустимый ряд» пришлось бы делать парсингом текста пункта,
    -- ради ухода от которого эта схема и создавалась.
    -- Если ряд задан формулой, а не перечнем (напр. «(100n):1»),
    -- поле остаётся NULL, а правило описано в clause_text.
    allowed_values            TEXT,                            -- '1:2;1:2,5;1:4;1:5;1:10' и т.п.
    figure_refs             VARCHAR(200),                     -- 'Рисунок 44, 45, 47' — только для справки, без картинки
    amended_by_id            INTEGER REFERENCES gost_amendment(id), -- если формулировка внесена/изменена конкретной поправкой
    superseded_clause_text     TEXT,                             -- текст пункта ДО поправки, если отличается (аналог "Напечатано" в markdown-версиях)
    UNIQUE (gost_standard_id, clause_number)
);

-- ---------- Связи между пунктами (в т.ч. между разными стандартами) ----------
-- Отдельная таблица, а не FK-поле в gost_clause: у одного пункта может
-- быть несколько исходящих ссылок разных типов (например 5.37 ссылается
-- на "рисунок 47" внутри и на "ГОСТ 25348" снаружи одновременно).
CREATE TABLE gost_clause_reference (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    from_clause_id      INTEGER NOT NULL REFERENCES gost_clause(id) ON DELETE CASCADE,
    to_clause_id         INTEGER REFERENCES gost_clause(id),        -- заполнено, если целевой пункт уже размечен в этой БД
    to_standard_designation  VARCHAR(50),                            -- 'ГОСТ 25348', если целевой стандарт(пункт) ещё не размечен построчно
    reference_type          VARCHAR(20) NOT NULL DEFAULT 'REFERS_TO'
                                CHECK (reference_type IN (
                                    'REFERS_TO',    -- обычная ссылка "по ГОСТ..."
                                    'CLARIFIES',     -- уточняет/детализирует предыдущий пункт
                                    'SUPERSEDES',     -- заменяет собой более старое правило
                                    'EXCEPTION_TO'     -- исключение из общего правила другого пункта
                                )),
    note                    TEXT,
    CHECK (to_clause_id IS NOT NULL OR to_standard_designation IS NOT NULL)
);

-- ---------- Графы основной надписи (штампа) по ГОСТ Р 2.104 ----------
-- Отдельная таблица, а не строки gost_clause: графа штампа — это не
-- «пункт стандарта», а поле формы, у которого своя устойчивая
-- идентификация (номер графы), свои правила обязательности отдельно
-- для бумажного и электронного документа, и своя связь с реквизитом
-- КД. Модуль 1.1 извлекает штамп чертежа именно по номерам граф —
-- эта таблица даёт эталон, с которым сверяется извлечённое.
CREATE TABLE gost_title_block_field (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    gost_standard_id    INTEGER NOT NULL REFERENCES gost_standard(id) ON DELETE CASCADE,
    field_number        VARCHAR(10)  NOT NULL,            -- '1', '2', ... '41' — номер графы как в стандарте
    field_heading       VARCHAR(50),                       -- 'Лит.', 'Масса', 'Масштаб'; NULL если графа без заголовка
    content_kind        VARCHAR(60),                       -- 'Реквизит КД «Наименование»', 'Техническая характеристика изделия', 'Элемент оформления КД'
    fill_rule           TEXT NOT NULL,                      -- полный текст порядка заполнения графы
    required_paper      VARCHAR(2) CHECK (required_paper IN ('●','○','*')),   -- обязательность для бумажного КД
    required_electronic VARCHAR(2) CHECK (required_electronic IN ('●','○','*')), -- обязательность для электронного КД
    amended_by_id       INTEGER REFERENCES gost_amendment(id),
    UNIQUE (gost_standard_id, field_number)
);

