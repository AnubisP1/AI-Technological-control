-- ============================================================
-- Сид: пункты ГОСТ 25142-82 (шероховатость поверхности, термины
-- и определения).
--
-- Характер стандарта: терминологический — он не задаёт числовых
-- границ, а определяет параметры (Ra, Rz, Rmax, Rp, Rv, Rq и др.),
-- которыми оперируют требования к поверхностям в других документах
-- и в технических требованиях чертежа. Поэтому почти все пункты
-- размечены как DEFINITION, а не NUMERIC_LIMIT.
--
-- Практическая ценность для проекта: когда Модуль 1.1 извлекает с
-- чертежа обозначение вида «Ra 3.2», система по этой таблице
-- определяет, что за параметр указан и что он означает, а не
-- обрабатывает подстроку вслепую.
--
-- Размечены параметры раздела 2 (высотные свойства неровностей)
-- и опорные термины раздела 1, на которые они ссылаются —
-- не все 32 термина раздела 1.
-- ============================================================

-- ---------- Раздел 1: опорные термины, нужные для понимания параметров ----------
INSERT INTO gost_clause (gost_standard_id, clause_number, section_title, clause_text, requirement_type, parameter_name) VALUES
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '1',
    'Общие понятия',
    'Раздел устанавливает общие термины, относящиеся к поверхности, её сечениям, профилю и неровностям, на которых основаны числовые параметры шероховатости раздела 2.',
    'DEFINITION',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '1.16',
    NULL,
    'Базовая длина l — длина базовой линии, используемая для выделения неровностей, характеризующих шероховатость поверхности.',
    'DEFINITION',
    'базовая длина l'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '1.17',
    NULL,
    'Длина оценки L — длина, на которой оцениваются значения параметров шероховатости. Она может содержать одну или несколько базовых длин.',
    'DEFINITION',
    'длина оценки L'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '1.19',
    NULL,
    'Средняя линия профиля — базовая линия, имеющая форму номинального профиля и проведённая так, что в пределах базовой длины среднее квадратическое отклонение профиля до этой линии минимально.',
    'DEFINITION',
    'средняя линия профиля'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '1.29',
    NULL,
    'Шероховатость поверхности — совокупность неровностей поверхности с относительно малыми шагами, выделенная, например, с помощью базовой длины.',
    'DEFINITION',
    'шероховатость поверхности'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '1.32',
    NULL,
    'Уровень сечения профиля p — расстояние между линией выступов профиля и линией, пересекающей профиль эквидистантно линии выступов профиля.',
    'DEFINITION',
    'уровень сечения профиля p'
);

-- ---------- Раздел 2: параметры шероховатости (высотные свойства) ----------
INSERT INTO gost_clause (gost_standard_id, clause_number, section_title, clause_text, requirement_type, parameter_name, unit) VALUES
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '2',
    'Параметры шероховатости, связанные с высотными свойствами неровностей',
    'Раздел устанавливает параметры шероховатости, характеризующие высотные свойства неровностей профиля: Rp, Rv, Rmax, Rz, Ra, Rq и связанные с ними величины.',
    'DEFINITION',
    NULL,
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '2.4',
    NULL,
    'Высота наибольшего выступа профиля Rp — расстояние от средней линии до высшей точки профиля в пределах базовой длины.',
    'DEFINITION',
    'Rp — высота наибольшего выступа профиля',
    'мкм'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '2.5',
    NULL,
    'Глубина наибольшей впадины профиля Rv — расстояние от низшей точки профиля до средней линии в пределах базовой длины. (Измененная редакция, Изм. № 1)',
    'DEFINITION',
    'Rv — глубина наибольшей впадины профиля',
    'мкм'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '2.6',
    NULL,
    'Полная высота профиля Rmax — сумма высоты наибольшего выступа профиля Rp и глубины наибольшей впадины профиля Rv в пределах длины оценки L. (Измененная редакция, Изм. № 1)',
    'DEFINITION',
    'Rmax — полная высота профиля',
    'мкм'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '2.7',
    NULL,
    'Наибольшая высота профиля Rz — сумма высоты наибольшего выступа профиля Rp и глубины наибольшей впадины профиля Rv в пределах базовой длины l. (Измененная редакция, Изм. № 1)',
    'DEFINITION',
    'Rz — наибольшая высота профиля',
    'мкм'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '2.8',
    NULL,
    'Среднее арифметическое отклонение профиля Ra — среднее арифметическое абсолютных значений отклонений профиля в пределах базовой длины.',
    'DEFINITION',
    'Ra — среднее арифметическое отклонение профиля',
    'мкм'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982'),
    '2.9',
    NULL,
    'Среднее квадратическое отклонение профиля Rq — среднее квадратическое значение отклонений профиля в пределах базовой длины.',
    'DEFINITION',
    'Rq — среднее квадратическое отклонение профиля',
    'мкм'
);

-- Иерархия разделов
UPDATE gost_clause
SET parent_clause_id = (SELECT id FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982') AND clause_number = '1')
WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND clause_number IN ('1.16', '1.17', '1.19', '1.29', '1.32');

UPDATE gost_clause
SET parent_clause_id = (SELECT id FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982') AND clause_number = '2')
WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND clause_number IN ('2.4', '2.5', '2.6', '2.7', '2.8', '2.9');

-- Внутренние смысловые связи: параметры раздела 2 определены через
-- термины раздела 1 (базовая длина, длина оценки, средняя линия).
-- Здесь to_clause_id заполняется реально — оба пункта размечены в БД.
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT
    src.id,
    dst.id,
    'REFERS_TO',
    'Параметр определён в пределах базовой длины l'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND src.clause_number IN ('2.4', '2.5', '2.7', '2.8', '2.9')
  AND dst.clause_number = '1.16';

INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT
    src.id,
    dst.id,
    'REFERS_TO',
    'Параметр определён в пределах длины оценки L'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND src.clause_number = '2.6'
  AND dst.clause_number = '1.17';

INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT
    src.id,
    dst.id,
    'REFERS_TO',
    'Отклонения профиля отсчитываются от средней линии профиля'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND src.clause_number IN ('2.4', '2.5', '2.8', '2.9')
  AND dst.clause_number = '1.19';

-- Rz и Rmax выражаются через Rp и Rv — связь CLARIFIES между параметрами
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT
    src.id,
    dst.id,
    'CLARIFIES',
    'Rz и Rmax вычисляются как сумма Rp и Rv (различаются интервалом усреднения)'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 25142-1982')
  AND src.clause_number IN ('2.6', '2.7')
  AND dst.clause_number IN ('2.4', '2.5');
