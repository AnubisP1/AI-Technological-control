# Размещение AI-Технолог на домене aifactorymai.ru

Продакшен-стек состоит из трёх процессов, поднимаемых на локальной
машине; наружу его публикует Cloudflare Tunnel, поэтому проброс портов
на роутере и внешний IP не требуются.

## Состав стека

| Компонент | Порт | Роль |
|---|---|---|
| uvicorn (backend) | 8000 | FastAPI-приложение, слушает только localhost |
| Caddy | 8787 | Раздаёт `frontend-v2/dist/`, проксирует `/api/*` на 8000 |
| cloudflared | — | Туннель `ai-tehnolog` → `aifactorymai.ru` |

HTTPS терминируется на стороне Cloudflare, поэтому в `Caddyfile`
установлено `auto_https off`: Caddy отдаёт обычный HTTP на localhost и
не пытается сам получать TLS-сертификат.

Префикс `/api` Caddy отрезает (`handle_path`) — так же, как это делает
Vite dev-прокси в режиме разработки. Благодаря этому фронтенд
обращается к бэкенду по одному и тому же относительному пути `/api`
и в разработке, и в продакшене, без переменных окружения с адресом.

## Запуск и остановка

```bash
cd dev/frontend-v2 && npm run build   # обязательно: Caddy раздаёт dist/
dev/deploy/start-stack.sh
dev/deploy/stop-stack.sh
```

Скрипты идемпотентны: повторный запуск не поднимает второй экземпляр —
процессы отслеживаются по PID-файлам в `deploy/pids/`, логи пишутся в
`deploy/logs/`. Оба каталога не версионируются (см. `.gitignore`) —
это локальное состояние процессов, а не исходный код.

## Автозапуск

Стек рассчитан на запуск launchd-агентом `ru.aitehnolog.stack.start`
(09:00, Europe/Moscow). Известная проблема: launchd не может исполнить
скрипты из `~/Documents` без разрешения Full Disk Access — каталог
защищён механизмом macOS TCC. Варианты решения: выдать Full Disk Access
интерпретатору `/bin/bash` либо перенести `deploy/` за пределы
`~/Documents`.

## Проверка

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs   # backend
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8787/       # Caddy
curl -s -o /dev/null -w "%{http_code}\n" https://aifactorymai.ru/     # снаружи
```
