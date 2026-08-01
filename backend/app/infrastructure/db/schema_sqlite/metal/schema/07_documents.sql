-- ============================================================
-- 07. Документы техпроцесса: шаблоны форм, маршрутная и
-- операционная карты (печатные/экспортные представления)
--
-- Адаптировано из ../../../../../../БД НСИ/schema/07_documents.sql
-- Отличие: JSONB -> TEXT (SQLite хранит JSON как текст;
-- валидация формата — на уровне приложения).
-- ============================================================

-- Шаблоны печатных форм документов ТП (по ГОСТ серии 3.1***), аналог .vtp/.ttp в ASCON Вертикаль
CREATE TABLE document_template (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code             VARCHAR(30) NOT NULL UNIQUE,      -- 'MK', 'OK', 'KTP', 'VO'
    name              VARCHAR(200) NOT NULL,             -- 'Маршрутная карта', 'Операционная карта', 'Карта технологического процесса', 'Ведомость оснастки'
    gost_form          VARCHAR(50),                       -- 'ГОСТ 3.1118-82 форма 1', 'ГОСТ 3.1404-86 форма 3'
    applicable_to       VARCHAR(20) CHECK (applicable_to IN ('process','operation')),
    layout_schema        TEXT,                             -- JSON-описание колонок/полей формы — используется фронтендом для рендера бланка без хардкода вёрстки
    description            TEXT
);

-- Маршрутная карта техпроцесса (ГОСТ 3.1118) — документ на весь техпроцесс (шапка + ссылки на операции)
CREATE TABLE route_card (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id           INTEGER NOT NULL REFERENCES process(id) ON DELETE CASCADE,
    document_template_id  INTEGER NOT NULL REFERENCES document_template(id),
    doc_number             VARCHAR(100),
    revision                 VARCHAR(20) DEFAULT '01',
    issued_at                  DATE,
    issued_by                    VARCHAR(200),
    UNIQUE (process_id, document_template_id)
);

-- Строка маршрутной карты — фактически проекция operation, но как отдельная
-- сущность документа (позволяет хранить специфичное для печатной формы:
-- переносы текста по строкам формы ГОСТ, коды профессий и т.д.)
CREATE TABLE route_card_row (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    route_card_id     INTEGER NOT NULL REFERENCES route_card(id) ON DELETE CASCADE,
    operation_id        INTEGER NOT NULL REFERENCES operation(id),
    row_no                INTEGER NOT NULL,
    profession_code        VARCHAR(20),   -- код профессии по классификатору
    UNIQUE (route_card_id, operation_id)
);

-- Операционная карта (ГОСТ 3.1404 и др.) — документ на одну операцию, детализация по переходам
CREATE TABLE operation_card (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id          INTEGER NOT NULL UNIQUE REFERENCES operation(id) ON DELETE CASCADE,
    document_template_id   INTEGER NOT NULL REFERENCES document_template(id),
    doc_number               VARCHAR(100),
    revision                   VARCHAR(20) DEFAULT '01'
);

-- Строка операционной карты — проекция transition в печатную форму
CREATE TABLE operation_card_transition_row (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_card_id     INTEGER NOT NULL REFERENCES operation_card(id) ON DELETE CASCADE,
    transition_id           INTEGER NOT NULL REFERENCES transition(id),
    row_no                    INTEGER NOT NULL,
    UNIQUE (operation_card_id, transition_id)
);
