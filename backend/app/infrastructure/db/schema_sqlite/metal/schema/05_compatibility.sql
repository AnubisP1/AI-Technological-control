-- ============================================================
-- 05. Таблицы совместимости (правила НСИ верхнего уровня)
-- Это прямой аналог TechClassesRelationsManager из модели ASCON:
-- связи задаются МЕЖДУ ТИПАМИ, а не между конкретными экземплярами.
-- Именно эти таблицы использует интерактивное приложение для
-- построения выпадающих списков "что можно выбрать дальше".
--
-- Адаптировано из ../../../../../../БД НСИ/schema/05_compatibility.sql
-- ============================================================

-- Матрица: какие операции умеет выполнять тип станка (1 станок -> N операций)
CREATE TABLE equipment_type_operation_type (
    equipment_type_id  INTEGER NOT NULL REFERENCES equipment_type(id),
    operation_type_id  INTEGER NOT NULL REFERENCES operation_type(id),
    PRIMARY KEY (equipment_type_id, operation_type_id)
);

-- Матрица: какая оснастка физически ставится на тип станка
-- (крепится физически — патрон, тиски, делительная головка и т.п.)
CREATE TABLE equipment_type_tooling_type (
    equipment_type_id  INTEGER NOT NULL REFERENCES equipment_type(id),
    tooling_type_id    INTEGER NOT NULL REFERENCES tooling_type(id),
    is_required          BOOLEAN NOT NULL DEFAULT 0,  -- обязательна ли эта оснастка для работы станка (напр. патрон для токарного)
    PRIMARY KEY (equipment_type_id, tooling_type_id)
);

-- Матрица: какая оснастка нужна для вида операции (напр. "Фрезерная" требует "Фреза" + "Тиски"/"Приспособление")
CREATE TABLE operation_type_tooling_type (
    operation_type_id  INTEGER NOT NULL REFERENCES operation_type(id),
    tooling_type_id     INTEGER NOT NULL REFERENCES tooling_type(id),
    is_required           BOOLEAN NOT NULL DEFAULT 1,
    PRIMARY KEY (operation_type_id, tooling_type_id)
);

-- Матрица: какие материалы заготовок обрабатывает тип станка
-- (грубый фильтр верхнего уровня; точная проверка — по мощности/твёрдости, см. ниже)
CREATE TABLE equipment_type_material_group (
    equipment_type_id  INTEGER NOT NULL REFERENCES equipment_type(id),
    material_group_id  INTEGER NOT NULL REFERENCES material_group(id),
    PRIMARY KEY (equipment_type_id, material_group_id)
);

-- Матрица: какие виды заготовок типичны для типа станка
-- (напр. на токарный - "Прокат сортовой", на фрезерный - "Поковка"/"Отливка")
CREATE TABLE equipment_type_workpiece_type (
    equipment_type_id  INTEGER NOT NULL REFERENCES equipment_type(id),
    workpiece_type_id  INTEGER NOT NULL REFERENCES workpiece_type(id),
    PRIMARY KEY (equipment_type_id, workpiece_type_id)
);

-- ------------------------------------------------------------
-- Точная совместимость на уровне КОНКРЕТНЫХ объектов
-- (не обязательна к заполнению целиком — используется как
-- "исключение из правил" или как точный подбор оснастки под станок
-- по геометрическому интерфейсу: shank_type = spindle_nose_type)
-- ------------------------------------------------------------

-- Точечные исключения совместимости на уровне конкретных моделей/артикулов:
-- явно разрешённая (или явно запрещённая) пара станок-оснастка, когда общего
-- правила по типам недостаточно (напр. конкретный патрон физически не влезает
-- в конкретный станок несмотря на совпадение типов)
CREATE TABLE equipment_tooling_override (
    equipment_model_id  INTEGER NOT NULL REFERENCES equipment_model(id),
    tooling_id            INTEGER NOT NULL REFERENCES tooling(id),
    is_allowed              BOOLEAN NOT NULL,
    reason                   TEXT,
    PRIMARY KEY (equipment_model_id, tooling_id)
);
