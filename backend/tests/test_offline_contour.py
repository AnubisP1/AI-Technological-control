"""Защита офлайн-контура ветки dev_locall (см. BRANCHES.md).

Требование ветки — «не должно быть обращений по api через интернет» —
проверяется структурно, по исходному коду, а не по поведению в рантайме:
рантайм-проверка (подмена socket.socket.connect) в этом проекте
невозможна, так как ProcessPoolExecutor из app/infrastructure/worker_pool.py
использует сокеты для порождения воркеров, и её срабатывание ломало бы
сам пул, а не ловило обращение наружу.

Тест намеренно грубый: любой новый HTTP-клиент или внешний URL в app/
уронит сборку и потребует осознанного решения, а не пройдёт незаметно.
"""

from __future__ import annotations

import re
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent / "app"

# Признаки исходящего сетевого вызова.
_NETWORK_CLIENT_PATTERNS = (
    r"\burllib\.request\b",
    r"\bimport\s+httpx\b",
    r"\bimport\s+aiohttp\b",
    r"\brequests\.(get|post|put|delete|patch)\b",
    r"\bsocket\.create_connection\b",
)

# Локальные адреса разрешены (Vite-прокси, локальный backend), как и
# XML-неймспейсы в шаблонах документов — это идентификаторы, не запросы.
_ALLOWED_URL_SUBSTRINGS = (
    "localhost",
    "127.0.0.1",
    "schemas.xmlsoap",
    "www.w3.org",
    "schemas.openxmlformats",
    "purl.org",
)


def _python_sources() -> list[Path]:
    return [p for p in _APP_DIR.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_http_clients_in_backend():
    """В офлайн-сборке не должно быть ни одного HTTP-клиента."""
    offenders: list[str] = []
    for path in _python_sources():
        text = path.read_text(encoding="utf-8")
        for pattern in _NETWORK_CLIENT_PATTERNS:
            if re.search(pattern, text):
                offenders.append(f"{path.relative_to(_APP_DIR.parent)}: {pattern}")
    assert not offenders, "Найдены HTTP-клиенты в офлайн-контуре:\n" + "\n".join(offenders)


def test_no_external_urls_in_backend():
    """Внешних URL быть не должно — только локальные адреса и неймспейсы."""
    offenders: list[str] = []
    for path in _python_sources():
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for url in re.findall(r"https?://[^\s\"'<>)]+", line):
                if not any(allowed in url for allowed in _ALLOWED_URL_SUBSTRINGS):
                    offenders.append(f"{path.relative_to(_APP_DIR.parent)}:{line_no}: {url}")
    assert not offenders, "Найдены внешние URL в офлайн-контуре:\n" + "\n".join(offenders)


def test_no_domain_references_in_backend():
    """Связи с доменом aifactorymai быть не должно (требование ветки)."""
    offenders = [
        str(path.relative_to(_APP_DIR.parent))
        for path in _python_sources()
        if "aifactorymai" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, "Найдены ссылки на домен:\n" + "\n".join(offenders)
