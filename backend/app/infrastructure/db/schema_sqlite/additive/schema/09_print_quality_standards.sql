-- ============================================================
-- 09. Допуски, шероховатость и справочник ГОСТ для 3D-печати
--
-- Наполняет БД реальными числовыми данными для генерации содержательных
-- маршрутной/операционной карт печати, а не только пустых граф.
-- Источники (см. также ../../../../../../БД НСИ Аддитив/ГОСТы 3Д печать.md
-- для полного списка стандартов с областью применения):
--
-- 1. Допуски/шероховатость/минимальная толщина стенки/резьба по
--    ТЕХНОЛОГИИ (не по конкретному материалу — сами материалы внутри
--    одной технологии печати нормируются близко, отдельных числовых
--    данных по материалам в доступных источниках нет, дублировать
--    значения технологии на каждый материал не стали, чтобы не создавать
--    ложное впечатление точности): агрегированная статья с таблицами
--    допусков/шероховатости, ссылающаяся на ISO/ASTM 52900:2021,
--    ISO/ASTM 52901:2017, ГОСТ Р 57558-2017, ГОСТ 2789-73, ГОСТ Р 70117-2022
--    (https://inner.su/articles/tablitsy-dopuskov-i-sherokhovatosti-3d-pechati-standarty-additivnogo-proizvodstva/,
--    таблицы 1, 2 и текстовые данные по резьбе/зазорам сборки).
-- 2. Квалитеты IT6-IT8 по диапазону размера — стандартная ISO-таблица
--    допусков (та же статья, таблица 3), не зависит от конкретной
--    технологии печати, применяется как справочная классификация точности.
-- 3. Улучшение точности/шероховатости при постобработке (та же статья,
--    таблица 4) — по методу обработки, не привязано к конкретной
--    технологии печати (в источнике общее для FDM/SLA/SLS/металл АП).
-- 4. Справочник ГОСТ/ИСО-АСТМ по аддитивным технологиям — из перечня,
--    сформированного пользователем (ГОСТы 3Д печать.md) — только номер,
--    название и краткая область применения, БЕЗ выдуманных числовых
--    значений из самих стандартов (полные тексты не парсились на числа,
--    кроме явно найденных в статье выше).
-- ============================================================

-- Допуски/шероховатость/дизайн-правила по технологии печати. Диапазоны
-- (не единое число) — источник даёт вилку значений, не фиксирует одно;
-- приложение показывает вилку как есть, не выбирает медиану произвольно.
CREATE TABLE am_technology_tolerance (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    am_technology_id             INTEGER NOT NULL REFERENCES am_technology(id),
    tolerance_min_mm               NUMERIC(6,3) NOT NULL,   -- нижняя граница допуска, мм (±)
    tolerance_max_mm                NUMERIC(6,3) NOT NULL,   -- верхняя граница допуска, мм (±)
    min_wall_thickness_mm             NUMERIC(6,3) NOT NULL,
    max_wall_thickness_mm              NUMERIC(6,3),          -- NULL, если источник даёт только нижнюю границу
    layer_resolution_min_mm              NUMERIC(6,4) NOT NULL,
    layer_resolution_max_mm               NUMERIC(6,4) NOT NULL,
    positioning_accuracy_min_mm             NUMERIC(6,4) NOT NULL,
    positioning_accuracy_max_mm              NUMERIC(6,4) NOT NULL,
    roughness_ra_raw_min_um                    NUMERIC(6,2) NOT NULL,  -- Ra без постобработки, мкм
    roughness_ra_raw_max_um                     NUMERIC(6,2) NOT NULL,
    roughness_ra_finished_min_um                  NUMERIC(6,2),          -- Ra после шлифовки/полировки, мкм
    roughness_ra_finished_max_um                   NUMERIC(6,2),
    min_thread_pitch_mm                              NUMERIC(6,2),          -- минимальный шаг резьбы, мм (NULL — нет данных)
    assembly_clearance_min_mm                          NUMERIC(6,3),          -- рекомендуемый зазор сборки, мм
    assembly_clearance_max_mm                           NUMERIC(6,3),
    source_note                                          TEXT NOT NULL,        -- откуда взяты числа, дословно
    UNIQUE (am_technology_id)
);

-- Квалитеты точности IT6-IT8 по диапазону номинального размера —
-- стандартная ISO-таблица допусков, не специфична для одной технологии
-- печати; используется как справочная классификация ("для этого размера
-- при квалитете IT7 допуск составляет N мкм"), не для автоподбора.
CREATE TABLE dimensional_tolerance_class (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    size_min_mm           NUMERIC(8,2) NOT NULL,   -- нижняя граница диапазона номинального размера (не включая)
    size_max_mm            NUMERIC(8,2) NOT NULL,   -- верхняя граница диапазона (включительно)
    it6_um                  NUMERIC(6,1) NOT NULL,   -- допуск по IT6, мкм
    it7_um                   NUMERIC(6,1) NOT NULL,   -- допуск по IT7, мкм
    it8_um                    NUMERIC(6,1) NOT NULL,   -- допуск по IT8, мкм
    UNIQUE (size_min_mm, size_max_mm)
);

-- Улучшение точности/шероховатости при постобработке — по методу
-- обработки, применимо к нескольким технологиям сразу (источник не
-- детализирует по каждой технологии отдельно).
CREATE TABLE postprocessing_quality_effect (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    pp_tooling_type_id               INTEGER REFERENCES pp_tooling_type(id),  -- связь с уже существующим справочником оснастки постобработки, если есть прямое соответствие; NULL — метод шире одного вида оснастки
    method_name                       VARCHAR(200) NOT NULL,   -- 'Механическая обработка', 'Абразивоструйная обработка', 'Химическое травление', 'Ультразвуковая обработка', 'Полировка'
    tolerance_improvement_min_percent   NUMERIC(5,1) NOT NULL,
    tolerance_improvement_max_percent    NUMERIC(5,1) NOT NULL,
    roughness_reduction_factor_min         NUMERIC(5,1) NOT NULL,  -- во сколько раз снижается Ra, нижняя граница
    roughness_reduction_factor_max          NUMERIC(5,1) NOT NULL,
    processing_time_note                     VARCHAR(100),           -- '2-6 часов', '30-60 мин' — текстом, т.к. источник не даёт единой размерности для всех методов
    relative_cost                             VARCHAR(10) CHECK (relative_cost IN ('low','medium','high'))
);

-- Справочник ГОСТ/ИСО-АСТМ стандартов аддитивного производства — для
-- отображения в отчётах/картах ("Изготовлено в соответствии с ГОСТ ...").
-- Только номер/название/область применения, без выдуманных числовых
-- требований из текста самих стандартов, которые не были распарсены.
CREATE TABLE am_gost_reference (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    designation      VARCHAR(60)  NOT NULL UNIQUE,  -- 'ГОСТ Р 57558-2017'
    title             VARCHAR(400) NOT NULL,          -- полное название стандарта
    scope_summary       TEXT NOT NULL,                  -- краткая область применения (1 фраза из источника)
    document_available    BOOLEAN NOT NULL DEFAULT 0     -- есть ли сам PDF в БД НСИ Аддитив/ (не все в перечне подгружены)
);
