-- ============================================================
-- SEED: примеры реальных данных — аддитивные технологии (печать пластиком)
-- Адаптировано из ../../../../../../БД НСИ Аддитив/seed/seed_data.sql
-- (TRUE/FALSE -> 1/0)
-- ============================================================

-- ---------- Технологии ----------
INSERT INTO am_technology (id, code, name, process_family) VALUES
(1, 'FDM',  'Наплавление нитью (FDM/FFF)',        'material_extrusion'),
(2, 'SLA',  'Стереолитография (SLA, лазер)',       'vat_photopolymerization'),
(3, 'MSLA', 'Маскированная стереолитография (MSLA/LCD)', 'vat_photopolymerization'),
(4, 'SLS',  'Селективное лазерное спекание (SLS)', 'powder_bed_fusion');

-- ---------- Типы принтеров ----------
INSERT INTO printer_type (id, am_technology_id, code, name) VALUES
(1, 1, 'FDM_CARTESIAN', 'FDM, картезианская кинематика'),
(2, 1, 'FDM_COREXY',    'FDM, CoreXY кинематика'),
(3, 2, 'SLA_LASER',     'SLA с лазерной засветкой'),
(4, 3, 'MSLA_LCD',      'MSLA с LCD-маскированием'),
(5, 4, 'SLS_LASER',     'SLS с лазерным спеканием порошка');

-- ---------- Группы материалов ----------
INSERT INTO am_material_group (id, am_technology_id, code, name, physical_form) VALUES
(1, 1, 'PLA',        'PLA (полилактид)',            'filament'),
(2, 1, 'PETG',        'PETG',                         'filament'),
(3, 1, 'ABS',          'ABS',                           'filament'),
(4, 1, 'ASA',           'ASA',                            'filament'),
(5, 1, 'TPU',            'TPU (гибкий эластомер)',          'filament'),
(6, 1, 'NYLON_FDM',       'Полиамид (нейлон) для FDM',         'filament'),
(7, 1, 'PVA_SUPPORT',      'PVA (растворимая поддержка)',        'filament'),
(8, 2, 'RESIN_STD',         'Смола стандартная',                    'resin'),
(9, 2, 'RESIN_TOUGH',        'Смола ударопрочная (Tough/Durable)',    'resin'),
(10,3, 'RESIN_STD_MSLA',      'Смола стандартная (MSLA)',               'resin'),
(11,3, 'RESIN_CAST',           'Смола выжигаемая (для литья)',            'resin'),
(12,4, 'PA12_SLS',               'Полиамид PA12 (SLS)',                       'powder'),
(13,4, 'TPU_SLS',                 'TPU порошок (SLS)',                          'powder');

-- ---------- Категории и типы оснастки постобработки ----------
INSERT INTO pp_tooling_category (id, code, name) VALUES
(1, 'WASH',            'Отмывка'),
(2, 'CURE',             'УФ-дозасветка'),
(3, 'SUPPORT_REMOVAL',   'Удаление поддержек'),
(4, 'SURFACE_FINISH',     'Финишная обработка поверхности'),
(5, 'BED_ADHESION',        'Адгезия к столу'),
(6, 'POWDER_HANDLING',      'Работа с порошком');

INSERT INTO pp_tooling_type (id, category_id, code, name) VALUES
(1, 1, 'WASH_STATION_IPA',   'Мойка в изопропиловом спирте (ИПС)'),
(2, 1, 'WASH_STATION_WATER',  'Мойка водосмываемых смол'),
(3, 2, 'UV_CURE_CHAMBER',      'УФ-камера дозасветки'),
(4, 3, 'SUPPORT_CUTTER',        'Инструмент для срезания поддержек'),
(5, 4, 'SANDING_KIT',            'Набор для шлифовки/полировки'),
(6, 5, 'BUILD_PLATE_PEI',         'Стол с PEI-покрытием'),
(7, 5, 'ADHESIVE_SPRAY',           'Аэрозольная адгезия (для смол/ABS)'),
(8, 6, 'SIEVE_STATION',              'Станция просеивания и восстановления порошка'),
(9, 6, 'BEAD_BLASTING',               'Пескоструйная/дробеструйная очистка (SLS)');

-- ---------- Виды исходных файлов моделей ----------
INSERT INTO model_source_type (id, code, name) VALUES
(1, 'STL', 'STL (сеточная модель)'),
(2, 'STEP', 'STEP (параметрическая CAD-модель)'),
(3, '3MF', '3MF (с метаданными печати)');

-- ---------- Производители принтеров ----------
INSERT INTO printer_manufacturer (id, name, country) VALUES
(1, 'Bambu Lab', 'Китай'),
(2, 'Prusa Research', 'Чехия'),
(3, 'Formlabs', 'США'),
(4, 'Anycubic', 'Китай'),
(5, 'EOS', 'Германия');

-- ---------- Модели принтеров ----------
INSERT INTO printer_model (
    id, printer_type_id, manufacturer_id, model_name,
    build_volume_x_mm, build_volume_y_mm, build_volume_z_mm,
    layer_height_min_mm, layer_height_max_mm,
    nozzle_diameter_mm, max_nozzle_temp_c, max_bed_temp_c, number_of_extruders, heated_chamber,
    light_source, wavelength_nm, laser_power_w, chamber_temp_max_c, is_industrial
) VALUES
-- FDM CoreXY, потребительский с закрытой камерой
(1, 2, 1, 'Bambu Lab X1-Carbon',
    256, 256, 256,
    0.08, 0.28,
    0.4, 300, 120, 1, 1,
    NULL, NULL, NULL, NULL, 0),
-- FDM картезианский, открытый
(2, 1, 2, 'Prusa MK4',
    250, 210, 220,
    0.05, 0.30,
    0.4, 290, 120, 1, 0,
    NULL, NULL, NULL, NULL, 0),
-- SLA лазерный
(3, 3, 3, 'Formlabs Form 3',
    145, 145, 185,
    0.025, 0.3,
    NULL, NULL, NULL, NULL, NULL,
    'laser', 405, NULL, NULL, 0),
-- MSLA LCD
(4, 4, 4, 'Anycubic Photon Mono X2',
    196, 122, 250,
    0.01, 0.1,
    NULL, NULL, NULL, NULL, NULL,
    'lcd_masking', 405, NULL, NULL, 0),
-- SLS промышленный
(5, 5, 5, 'EOS P 396',
    340, 340, 600,
    0.06, 0.15,
    NULL, NULL, NULL, NULL, NULL,
    NULL, NULL, 70, 180, 1);

-- ---------- Физические единицы принтеров ----------
INSERT INTO printer (printer_model_id, inventory_number, location, status) VALUES
(1, 'ПР-0001', 'Участок прототипирования', 'active'),
(2, 'ПР-0002', 'Участок прототипирования', 'active'),
(3, 'ПР-0003', 'Лаборатория постобработки смол', 'active'),
(4, 'ПР-0004', 'Лаборатория постобработки смол', 'active'),
(5, 'ПР-0005', 'Цех промышленной печати', 'active');

-- ---------- Производители материалов ----------
INSERT INTO material_manufacturer (id, name) VALUES
(1, 'eSUN'),
(2, 'Bambu Lab'),
(3, 'Formlabs'),
(4, 'Polymaker'),
(5, 'EOS');

-- ---------- Материалы ----------
INSERT INTO am_material (
    id, am_material_group_id, manufacturer_id, trade_name, color,
    diameter_mm, spool_weight_kg, bottle_volume_ml, powder_batch_kg,
    density_g_cm3, print_temp_min_c, print_temp_max_c, bed_temp_c,
    tensile_strength_mpa, requires_heated_chamber, requires_dry_storage, is_soluble_support
) VALUES
(1, 1, 1, 'eSUN PLA+', 'Серый', 1.75, 1.0, NULL, NULL, 1.24, 190, 220, 60, 45, 0, 0, 0),
(2, 2, 2, 'Bambu Lab PETG HF', 'Чёрный', 1.75, 1.0, NULL, NULL, 1.27, 230, 260, 80, 50, 0, 1, 0),
(3, 3, 4, 'Polymaker PolyLite ABS', 'Белый', 1.75, 1.0, NULL, NULL, 1.04, 240, 260, 100, 40, 1, 0, 0),
(4, 7, 1, 'eSUN PVA', 'Натуральный', 1.75, 0.5, NULL, NULL, 1.23, 190, 210, 60, NULL, 0, 1, 1),
(5, 8, 3, 'Formlabs Grey Resin V5', 'Серый', NULL, NULL, 1000, NULL, 1.10, NULL, NULL, NULL, 65, 0, 0, 0),
(6, 9, 3, 'Formlabs Tough 2000 Resin', 'Тёмно-серый', NULL, NULL, 1000, NULL, 1.05, NULL, NULL, NULL, 55, 0, 0, 0),
(7, 12, 5, 'EOS PA 2200', 'Белый', NULL, NULL, NULL, 20, 0.93, NULL, NULL, NULL, 48, 0, 1, 0);

-- ---------- Оборудование постобработки ----------
INSERT INTO pp_tooling_manufacturer (id, name) VALUES (1, 'Formlabs'), (2, 'EOS');

INSERT INTO pp_tooling (id, pp_tooling_type_id, manufacturer_id, designation, chamber_volume_x_mm, chamber_volume_y_mm, chamber_volume_z_mm, uv_wavelength_nm) VALUES
(1, 1, 1, 'Formlabs Form Wash', 200, 200, 200, NULL),
(2, 3, 1, 'Formlabs Form Cure', 200, 200, 200, 405),
(3, 8, 2, 'Станция просеивания порошка EOS', NULL, NULL, NULL, NULL);

-- ============================================================
-- Матрицы совместимости
-- ============================================================

-- Какие материалы поддерживает тип принтера
INSERT INTO printer_type_material_group (printer_type_id, am_material_group_id) VALUES
(1,1),(1,2),(1,3),(1,4),(1,5),(1,6),(1,7),   -- CoreXY закрытая камера — весь спектр FDM-материалов
(2,1),(2,2),(2,5),(2,7),                      -- открытый картезианский — без ABS/нейлона (нужна камера)
(3,8),(3,9),                                   -- SLA лазерный
(4,10),(4,11),                                  -- MSLA
(5,12),(5,13);                                   -- SLS

-- Какая постобработка нужна для группы материала
INSERT INTO material_group_pp_tooling_type (am_material_group_id, pp_tooling_type_id, is_required, typical_order) VALUES
(8, 1, 1, 1),  (8, 3, 1, 2),    -- смола стандартная -> мойка -> дозасветка
(9, 1, 1, 1),  (9, 3, 1, 2),
(10,1, 1, 1),  (10,3, 1, 2),
(11,1, 1, 1),  (11,3, 1, 2),
(1, 4, 0, 1), (2, 4, 0, 1), (3,4, 0, 1),   -- филаменты -> опционально удаление поддержек
(1, 5, 0, 2), (2, 5, 0, 2), (3,5, 0, 2),   -- опционально шлифовка
(12,8, 1, 1), (12,9, 0, 2),                  -- SLS порошок -> просеивание, опц. пескоструй
(13,8, 1, 1);

-- Какая постобработка в принципе применима к технологии
INSERT INTO am_technology_pp_tooling_type (am_technology_id, pp_tooling_type_id) VALUES
(1,4),(1,5),(1,6),(1,7),        -- FDM: срезка поддержек, шлифовка, адгезия стола
(2,1),(2,3),(2,4),(2,5),        -- SLA: мойка, дозасветка, срезка поддержек, шлифовка
(3,1),(3,3),(3,4),(3,5),        -- MSLA: аналогично
(4,8),(4,9);                    -- SLS: просеивание, пескоструй

-- Точное исключение: Formlabs Form 3 работает только со смолами Formlabs (закрытая экосистема)
INSERT INTO printer_material_override (printer_model_id, am_material_id, is_allowed, reason) VALUES
(3, 5, 1,  'Родная смола Formlabs, картридж с чипом распознаётся принтером'),
(3, 6, 1,  'Родная смола Formlabs, картридж с чипом распознаётся принтером');

-- ============================================================
-- Пример: деталь, техпроцесс печати, параметры, постобработка
-- ============================================================

INSERT INTO am_part (id, designation, name, model_source_type_id, bounding_x_mm, bounding_y_mm, bounding_z_mm) VALUES
(1, 'ADD.001.001', 'Корпус датчика', 1, 60, 40, 25);

INSERT INTO print_process (id, am_part_id, code, name, am_technology_id, printer_type_id, am_material_id, production_type, status) VALUES
(1, 1, 'ПП-001', 'Печать корпуса датчика FDM PETG', 1, 2, 2, 'prototype', 'draft');

INSERT INTO print_parameters (print_process_id, layer_height_mm, infill_percent, infill_pattern, wall_count, top_bottom_layers,
                                nozzle_temp_c, bed_temp_c, print_speed_mm_s, support_needed,
                                estimated_print_time_min, estimated_material_g) VALUES
(1, 0.2, 25, 'gyroid', 3, 4, 245, 80, 60, 1, 185, 42);

INSERT INTO postprocessing_step (print_process_id, sequence_no, pp_tooling_type_id, description, duration_min) VALUES
(1, 1, 4, 'Срезать поддержки под нависающими элементами', 10),
(1, 2, 5, 'Зачистить места контакта с поддержками наждачной бумагой P400', 5);

-- ---------- Шаблоны документов ----------
INSERT INTO am_document_template (id, code, name, applicable_to, layout_schema) VALUES
(1, 'PRINT_CARD', 'Карта техпроцесса печати', 'print_process',
  '{"columns": ["Технология", "Принтер", "Материал", "Высота слоя", "Заполнение", "Время печати", "Расход материала"]}'),
(2, 'PP_CARD', 'Карта постобработки', 'postprocessing',
  '{"columns": ["№ шага", "Операция", "Оборудование", "Длительность", "Температура", "Влияние на точность/шероховатость"]}');
