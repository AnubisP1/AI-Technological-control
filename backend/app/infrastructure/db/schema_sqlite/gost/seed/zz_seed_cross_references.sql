-- ============================================================
-- Сид: МЕЖСТАНДАРТНЫЕ связи графа требований.
--
-- Вынесены в отдельный файл намеренно: связи вида
-- «пункт стандарта A -> пункт стандарта B» через to_clause_id можно
-- вставлять только когда ОБА стандарта уже размечены. Если такие
-- INSERT ... SELECT лежат внутри сида одного стандарта, они молча
-- вставляют 0 строк при загрузке в неудачном порядке (SELECT не
-- находит целевой пункт, ошибки при этом не возникает) — эта ошибка
-- уже была допущена и найдена проверкой целостности.
--
-- Имя файла начинается с 'zz_', чтобы при загрузке по алфавиту он
-- гарантированно шёл после всех сидов отдельных стандартов.
-- ============================================================

-- 5.9 -> ГОСТ Р 2.316 (размечен в БД: указываем конкретный раздел 6 про ТТ)
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'REFERS_TO', 'Текстовая часть чертежа (надписи, таблицы, ТТ) выполняется по правилам ГОСТ Р 2.316'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND src.clause_number = '5.9'
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.316-2023') AND dst.clause_number = '6';

-- 5.10 -> ГОСТ 2.307 (размечен в БД: раздел 6 про предельные отклонения)
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'REFERS_TO', 'Размеры и предельные отклонения на чертеже указывают по ГОСТ 2.307'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND src.clause_number = '5.10'
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND dst.clause_number = '6';

-- 5.10 -> стандарты, не размеченные построчно (только обозначение)
INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ Р 2.308', 'REFERS_TO', 'Геометрические допуски (допуски формы и расположения поверхностей)'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND clause_number = '5.10';

INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 2.309', 'REFERS_TO', 'Обозначения шероховатости поверхностей на чертеже'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND clause_number = '5.10';

-- 4.6 -> форматы и масштабы
INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 2.301', 'REFERS_TO', 'Форматы листов'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND clause_number = '4.6';

INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 2.302-1968', 'REFERS_TO', 'Масштабы изображения'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND clause_number = '4.6';

-- 5.12 уточняет общее правило 5.10 (исключение из него)
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'EXCEPTION_TO', 'Случай припуска на обработку при сборке — данные заключают в скобки, п.5.10 в этом случае применяется иначе'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND src.clause_number = '5.12'
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ Р 2.109-2023') AND dst.clause_number = '5.10';
