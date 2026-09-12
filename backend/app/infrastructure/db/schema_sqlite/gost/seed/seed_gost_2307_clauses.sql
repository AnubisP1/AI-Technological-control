-- ============================================================
-- Сид: пункты ГОСТ 2.307-2011 (нанесение размеров и предельных
-- отклонений) — выбраны пункты раздела 5 (частные случаи нанесения
-- размеров) и раздела 6 (предельные отклонения), содержащие
-- проверяемые числовые правила или прямые межстандартные ссылки.
-- Текст перенесён из уже вычитанной markdown-версии документа
-- (БД НСИ/ГОСТ/markdown/ГОСТ 2.307-2011_....md), не выдуман.
--
-- Это ПРИМЕР разметки, не полный перенос всех ~90 пунктов документа —
-- полная разметка оставлена как следующий шаг (см. dev/QUESTIONS.md).
-- ============================================================

INSERT INTO gost_clause (gost_standard_id, clause_number, section_title, clause_text, requirement_type, parameter_name, unit, comparison_op, limit_value_min, figure_refs) VALUES
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '5.37',
    NULL,
    'Размеры радиусов наружных скруглений наносят, как показано на рисунке 45, внутренних скруглений — на рисунке 46. Радиусы скругления, размер которых не более 1 мм, на изображении не указывают и их размеры наносят, как показано на рисунке 47.',
    'NUMERIC_LIMIT',
    'радиус скругления, не указываемый непосредственно на изображении',
    'мм',
    '<=',
    1.0,
    'Рисунок 45, 46, 47'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '5.44',
    NULL,
    'Размеры фасок под углом 45° наносят, как показано на рисунке 56. Допускается указывать размеры не изображенной на чертеже фаски под углом 45°, размер которой в масштабе чертежа не более 1 мм, на полке линии-выноски, проведенной от грани (см. рисунок 57). Размеры фасок под другими углами указывают по общим правилам — линейным и угловым размерами (см. рисунки 58а и 58б) или двумя линейными размерами (см. рисунок 58в).',
    'NUMERIC_LIMIT',
    'фаска 45°, размер которой в масштабе чертежа допускается не изображать',
    'мм',
    '<=',
    1.0,
    'Рисунок 56, 57, 58'
);

-- Пункты-определения/процедурные правила без единственной числовой границы
INSERT INTO gost_clause (gost_standard_id, clause_number, section_title, clause_text, requirement_type, figure_refs) VALUES
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '5.38',
    NULL,
    'При указании размера диаметра (во всех случаях) перед размерным числом наносят знак «⌀».',
    'ENUM_CHOICE',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '5.40',
    NULL,
    'Размеры квадрата наносят, как показано на рисунках 50—52. Высота знака «□» должна быть равна высоте размерных чисел. (Поправка)',
    'PROCEDURAL',
    'Рисунок 50, 51, 52'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '5.45',
    NULL,
    'Размеры нескольких одинаковых элементов изделия, как правило, наносят один раз с указанием на полке линии-выноски количества этих элементов (см. рисунок 59а). Допускается указывать количество элементов, как показано на рисунке 59б.',
    'PROCEDURAL',
    'Рисунок 59'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '6',
    'Нанесение предельных отклонений размеров',
    'Раздел, устанавливающий правила указания предельных отклонений размеров: общая запись в технических требованиях, условные обозначения полей допусков, числовые значения отклонений, а также правила для отклонений расположения осей отверстий.',
    'PROCEDURAL',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '6.1',
    NULL,
    'Предельные отклонения размеров следует указывать непосредственно после номинальных размеров. Предельные отклонения линейных и угловых размеров относительно низкой точности допускается не указывать непосредственно после номинальных размеров, а оговаривать общей записью в технических требованиях чертежа при условии, что эта запись однозначно определяет значения и знаки предельных отклонений. Общая запись о предельных отклонениях размеров с неуказанными допусками должна содержать условные обозначения предельных отклонений линейных размеров в соответствии с ГОСТ 25346 и ГОСТ 25348 (для отклонений по квалитетам) или по ГОСТ 30893.1 (для отклонений по классам точности).',
    'CROSS_REFERENCE',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '6.2',
    NULL,
    'Неуказанные предельные отклонения радиусов скруглений, фасок и углов не оговаривают отдельно, они должны соответствовать приведенным в ГОСТ 30893.1 в соответствии с квалитетом или классом точности неуказанных предельных отклонений линейных размеров.',
    'CROSS_REFERENCE',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '6.4а',
    NULL,
    'При указании предельных отклонений условными обозначениями обязательно и указание их числовых значений при назначении предельных отклонений (установленных стандартами на допуски и посадки) размеров, не включенных в ряды нормальных линейных размеров по ГОСТ 6636, например 41,5.',
    'CROSS_REFERENCE',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '6.4б',
    NULL,
    'При указании предельных отклонений условными обозначениями обязательно и указание их числовых значений при назначении предельных отклонений, условные обозначения которых не предусмотрены ГОСТ 25347, например для пластмассовой детали с предельными отклонениями по ГОСТ 25349 (см. рисунок 80).',
    'CROSS_REFERENCE',
    'Рисунок 80'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011'),
    '6.12а',
    NULL,
    'Предельные отклонения расположения осей отверстий можно указывать позиционными допусками осей отверстий в соответствии с требованиями ГОСТ 2.308.',
    'CROSS_REFERENCE',
    NULL
);

-- Иерархия: 6.1, 6.2, 6.4а, 6.4б, 6.12а — дочерние пункты раздела 6
UPDATE gost_clause
SET parent_clause_id = (SELECT id FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6')
WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011')
  AND clause_number IN ('6.1', '6.2', '6.4а', '6.4б', '6.12а');

-- Связи между пунктами и на внешние стандарты (граф требований)
INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 25346', 'REFERS_TO', 'Условные обозначения предельных отклонений линейных размеров'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6.1';

INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 25348', 'REFERS_TO', 'Отклонения по квалитетам'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6.1';

INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 30893.1', 'REFERS_TO', 'Отклонения по классам точности; текст обозначения в таблице 1 менялся поправкой ИУС №8-2018'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number IN ('6.1', '6.2');

INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 6636', 'REFERS_TO', 'Ряды нормальных линейных размеров'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6.4а';

INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 25347', 'REFERS_TO', 'Поля допусков размеров'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6.4б';

INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ 25349', 'REFERS_TO', 'Поля допусков размеров деталей из пластмасс'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6.4б';

-- В тексте ГОСТ 2.307-2011 стандарт назван «ГОСТ 2.308» (без «Р»), в БД он
-- заведён под актуальным обозначением «ГОСТ Р 2.308» — см. notes у записи.
INSERT INTO gost_clause_reference (from_clause_id, to_standard_designation, reference_type, note)
SELECT id, 'ГОСТ Р 2.308', 'REFERS_TO', 'Позиционные допуски осей отверстий как альтернативный способ указания (в тексте ГОСТ 2.307-2011 обозначен без «Р»)'
FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6.12а';

-- Поправка ИУС №8-2018 меняла именно формулировку в таблице 1 п.6.1
-- (см. markdown-версия документа, "Поправка", ИУС №8 2018 г.):
-- "ГОСТ 30893.1—2002" (3 раза) -> "ГОСТ 30893.1"
UPDATE gost_clause
SET amended_by_id = (SELECT id FROM gost_amendment WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND ius_number = '8' AND ius_year = 2018),
    superseded_clause_text = 'Общие допуски по ГОСТ 30893.1—2002: Н14, h14, ±IT14/2 (обозначение стандарта с годом утверждения указывалось 3 раза в таблице 1)'
WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.307-2011') AND clause_number = '6.1';
