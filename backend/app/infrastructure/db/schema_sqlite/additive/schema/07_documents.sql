-- ============================================================
-- 07. Документы техпроцесса печати
-- Адаптировано из ../../../../../../БД НСИ Аддитив/schema/07_documents.sql
-- JSONB -> TEXT (JSON хранится как текст, валидация — на уровне приложения)
-- ============================================================

-- Шаблоны документов техпроцесса печати (аналог document_template из механообработки)
CREATE TABLE am_document_template (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code             VARCHAR(30) NOT NULL UNIQUE,      -- 'PRINT_CARD', 'PP_CARD', 'PART_PASSPORT'
    name              VARCHAR(200) NOT NULL,             -- 'Карта техпроцесса печати', 'Карта постобработки', 'Паспорт напечатанной детали'
    applicable_to       VARCHAR(20) CHECK (applicable_to IN ('print_process','postprocessing')),
    layout_schema         TEXT,
    description             TEXT
);

-- Карта техпроцесса печати — основной документ на вариант ТП (аналог маршрутной карты)
CREATE TABLE print_process_card (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    print_process_id          INTEGER NOT NULL UNIQUE REFERENCES print_process(id) ON DELETE CASCADE,
    am_document_template_id     INTEGER NOT NULL REFERENCES am_document_template(id),
    doc_number                    VARCHAR(100),
    revision                        VARCHAR(20) DEFAULT '01',
    issued_at                         DATE,
    issued_by                           VARCHAR(200)
);

-- Карта постобработки — детализация по шагам (аналог операционной карты)
CREATE TABLE postprocessing_card (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    print_process_id          INTEGER NOT NULL UNIQUE REFERENCES print_process(id) ON DELETE CASCADE,
    am_document_template_id     INTEGER NOT NULL REFERENCES am_document_template(id),
    doc_number                    VARCHAR(100),
    revision                        VARCHAR(20) DEFAULT '01'
);

CREATE TABLE postprocessing_card_row (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    postprocessing_card_id    INTEGER NOT NULL REFERENCES postprocessing_card(id) ON DELETE CASCADE,
    postprocessing_step_id      INTEGER NOT NULL REFERENCES postprocessing_step(id),
    row_no                         INTEGER NOT NULL,
    UNIQUE (postprocessing_card_id, postprocessing_step_id)
);

-- Паспорт конкретного напечатанного экземпляра — трассируемость: принтер,
-- партия материала, факт. время/расход (готовое изделие — для контроля качества)
CREATE TABLE printed_part_passport (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    print_process_id      INTEGER NOT NULL REFERENCES print_process(id),
    printer_id               INTEGER NOT NULL REFERENCES printer(id),
    am_material_batch_id       INTEGER REFERENCES am_material_batch(id),
    serial_number                 VARCHAR(100) UNIQUE,
    printed_at                      TEXT,
    actual_print_time_min             NUMERIC(10,2),
    actual_material_used_g              NUMERIC(10,2),
    qc_status                             VARCHAR(20) DEFAULT 'pending'
                                          CHECK (qc_status IN ('pending','passed','failed')),
    notes                                   TEXT
);
