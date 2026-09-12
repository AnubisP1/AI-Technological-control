-- ============================================================
-- Сид: пункты ГОСТ 2.305-2008 (изображения — виды, разрезы, сечения).
--
-- Практическая ценность для проекта: Модуль 1.1 детектирует виды на
-- поле чертежа. Этот стандарт даёт (а) закрытый перечень названий
-- основных видов — против него можно проверять результат детекции,
-- и (б) словарь терминов (вид/разрез/сечение и их подвиды), который
-- нужен, чтобы отличать эти сущности друг от друга при разборе
-- надписей на чертеже («А—А», «Б (5:1)» и т.п.).
--
-- Размечены: раздел 3 (термины, выборка ключевых) и раздел 5 (виды).
-- Разделы 6-9 (разрезы, сечения, выносные элементы, условности и
-- упрощения) не размечены — следующий шаг.
--
-- Текст перенесён из вычитанной markdown-версии документа
-- (БД НСИ/ГОСТ/markdown/ГОСТ 2.305-2008_Изображения - виды, размеры, сечения.md).
-- ============================================================

-- ---------- Раздел 3: термины ----------
INSERT INTO gost_clause (gost_standard_id, clause_number, section_title, clause_text, requirement_type, parameter_name) VALUES
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3',
    'Термины и определения',
    'Раздел устанавливает термины, разграничивающие виды изображений на чертеже: вид, разрез, сечение, выносной элемент и их разновидности.',
    'DEFINITION',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.2',
    NULL,
    'вид предмета (вид): Ортогональная проекция обращенной к наблюдателю видимой части поверхности предмета, расположенного между ним и плоскостью проецирования.',
    'DEFINITION',
    'вид предмета'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.5',
    NULL,
    'главный вид предмета (главный вид): Основной вид предмета на фронтальной плоскости проекции, который дает наиболее полное представление о форме и размерах предмета, относительно которого располагают остальные основные виды.',
    'DEFINITION',
    'главный вид'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.7',
    NULL,
    'дополнительный вид предмета (дополнительный вид): Изображение предмета на плоскости, не параллельной ни одной из основных плоскостей проекций, применяемое для неискаженного изображения поверхности, если ее нельзя получить на основном виде.',
    'DEFINITION',
    'дополнительный вид'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.9',
    NULL,
    'местный вид предмета (местный вид): Изображение отдельного ограниченного участка поверхности предмета.',
    'DEFINITION',
    'местный вид'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.14',
    NULL,
    'основной вид предмета (основной вид): Вид предмета, который получен путем совмещения предмета и его изображения на одной из граней пустотелого куба, внутри которого мысленно помещен предмет, с плоскостью чертежа. Примечание — Основной вид предмета может относиться к предмету в целом, его разрезу или сечению.',
    'DEFINITION',
    'основной вид'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.20',
    NULL,
    'разрез предмета (разрез): Ортогональная проекция предмета, мысленно рассеченного полностью или частично одной или несколькими плоскостями для выявления его невидимых поверхностей.',
    'DEFINITION',
    'разрез предмета'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.21',
    NULL,
    'сечение предмета (сечение): Ортогональная проекция фигуры, получающейся в одной или нескольких секущих плоскостях или поверхностях при мысленном рассечении проецируемого предмета. Примечание — При необходимости в качестве секущей допускается применять цилиндрическую поверхность, развертываемую на плоскость чертежа.',
    'DEFINITION',
    'сечение предмета'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.4',
    NULL,
    'выносной элемент: Дополнительное, обычно увеличенное, отдельное изображение части предмета.',
    'DEFINITION',
    'выносной элемент'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.18',
    NULL,
    'простой разрез: Разрез, выполненный одной секущей плоскостью.',
    'DEFINITION',
    'простой разрез'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '3.22',
    NULL,
    'сложный разрез: Разрез, выполненный двумя и более секущими плоскостями.',
    'DEFINITION',
    'сложный разрез'
);

-- ---------- Раздел 5: виды ----------
INSERT INTO gost_clause (gost_standard_id, clause_number, section_title, clause_text, requirement_type, parameter_name, allowed_values, figure_refs) VALUES
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.1',
    'Виды',
    'Установлены следующие названия видов, получаемых на основных плоскостях проекций (основные виды): 1 — вид спереди (главный вид); 2 — вид сверху; 3 — вид слева; 4 — вид справа; 5 — вид снизу; 6 — вид сзади. При выполнении графических документов в форме электронных моделей (ГОСТ 2.052) для получения соответствующих изображений следует применять сохраненные виды. В строительных чертежах в необходимых случаях соответствующим видам допускается присваивать специальные названия, например «фасад». Названия видов на чертежах надписывать не следует, за исключением случая, предусмотренного в 5.2.',
    'ENUM_CHOICE',
    'название основного вида',
    'вид спереди;вид сверху;вид слева;вид справа;вид снизу;вид сзади',
    'Рисунок 2'
);

INSERT INTO gost_clause (gost_standard_id, clause_number, clause_text, requirement_type, figure_refs) VALUES
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.2',
    'Если виды сверху, слева, справа, снизу, сзади не находятся в непосредственной проекционной связи с главным изображением (видом или разрезом, изображенным на фронтальной плоскости проекции), то направление проецирования должно быть указано стрелкой около соответствующего изображения. Над стрелкой и над полученным изображением (видом) следует нанести одну и ту же прописную букву. Чертежи оформляют так же, если перечисленные виды отделены от главного изображения другими изображениями или расположены не на одном листе с ним. Когда отсутствует изображение, на котором может быть показано направление взгляда, название вида надписывают.',
    'PROCEDURAL',
    'Рисунок 8'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.3',
    'При необходимости получения на чертеже наглядного изображения предмета применяют аксонометрические проекции по ГОСТ 2.317.',
    'CROSS_REFERENCE',
    NULL
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.4',
    'Если какую-либо часть предмета на чертеже невозможно показать на перечисленных в 5.1 видах без искажения формы и размеров, то применяют дополнительные виды, получаемые на плоскостях, не параллельных основным плоскостям проекций.',
    'PROCEDURAL',
    'Рисунок 9, 10, 11'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.5',
    'Дополнительный вид должен быть отмечен на чертеже прописной буквой, а у связанного с дополнительным видом изображения предмета должна быть поставлена стрелка, указывающая направление взгляда, с соответствующим буквенным обозначением. Когда дополнительный вид расположен в непосредственной проекционной связи с соответствующим изображением, стрелку и обозначение вида не наносят.',
    'PROCEDURAL',
    'Рисунок 9, 10, 11'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.6',
    'Дополнительные виды располагают, как показано на рисунках 9—11. Расположение дополнительных видов по рисункам 9 и 11 предпочтительнее. Дополнительный вид допускается повертывать, но с сохранением, как правило, положения, принятого для данного предмета на главном изображении, при этом обозначение вида должно быть дополнено условным графическим обозначением «повёрнуто». При необходимости указывают угол поворота. Несколько одинаковых дополнительных видов, относящихся к одному предмету, обозначают одной буквой и вычерчивают один вид. Если при этом связанные с дополнительным видом части предмета расположены под различными углами, то к обозначению вида условное графическое обозначение «повёрнуто» не добавляют.',
    'PROCEDURAL',
    'Рисунок 9, 10, 11, 12'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.7',
    'Местный вид может быть ограничен линией обрыва, по возможности в наименьшем размере, или не ограничен. Местный вид должен быть отмечен на чертеже подобно дополнительному виду.',
    'PROCEDURAL',
    'Рисунок 8, 13'
),
(
    (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'),
    '5.8',
    'Соотношение размеров стрелок, указывающих направление взгляда, должно соответствовать приведенным на рисунке 14.',
    'PROCEDURAL',
    'Рисунок 14'
);

-- Иерархия
UPDATE gost_clause
SET parent_clause_id = (SELECT id FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND clause_number = '3')
WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND clause_number IN ('3.2','3.4','3.5','3.7','3.9','3.14','3.18','3.20','3.21','3.22');

UPDATE gost_clause
SET parent_clause_id = (SELECT id FROM gost_clause WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND clause_number = '5.1')
WHERE gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND clause_number IN ('5.2','5.3','5.4','5.5','5.6','5.7','5.8');

-- Внутренние связи: подвиды уточняют базовые термины
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'CLARIFIES', 'Разновидность вида предмета'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND src.clause_number IN ('3.5','3.7','3.9','3.14') AND dst.clause_number = '3.2';

INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'CLARIFIES', 'Разновидность разреза по числу секущих плоскостей'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND src.clause_number IN ('3.18','3.22') AND dst.clause_number = '3.20';

-- 5.4 (дополнительные виды) — исключение из закрытого перечня 5.1
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'EXCEPTION_TO', 'Когда основных видов из перечня 5.1 недостаточно, применяют дополнительные виды'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008')
  AND src.clause_number = '5.4' AND dst.clause_number = '5.1';

-- Поправка (ИУС 12-2018) затронула пункты 3.6 и 3.19 (обозначены «(Поправка)» в тексте)
INSERT INTO gost_amendment (gost_standard_id, ius_number, ius_year) VALUES
((SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008'), '12', 2018);

-- Пункт 5.7 прямо отсылает к правилам обозначения дополнительного вида
-- («Местный вид должен быть отмечен на чертеже подобно дополнительному
-- виду») — без этой связи проверяющий не найдёт, КАК именно его отмечать.
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'REFERS_TO', 'Местный вид отмечают на чертеже подобно дополнительному виду — правило обозначения см. в 5.5'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND src.clause_number = '5.7'
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND dst.clause_number = '5.5';

-- Правила разделов 5.x опираются на термины раздела 3: связь «правило -> термин»
-- позволяет собрать для проверки и правило, и определение того, что проверяется.
INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'REFERS_TO', 'Правило применяется к местному виду — определение термина'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND src.clause_number = '5.7'
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND dst.clause_number = '3.9';

INSERT INTO gost_clause_reference (from_clause_id, to_clause_id, reference_type, note)
SELECT src.id, dst.id, 'REFERS_TO', 'Правило применяется к дополнительному виду — определение термина'
FROM gost_clause src, gost_clause dst
WHERE src.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND src.clause_number IN ('5.4','5.5','5.6')
  AND dst.gost_standard_id = (SELECT id FROM gost_standard WHERE designation = 'ГОСТ 2.305-2008') AND dst.clause_number = '3.7';
