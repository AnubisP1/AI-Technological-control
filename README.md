# AI-Технолог — размещение на домене (ветка `web`)

Ветка содержит **только инфраструктуру публикации** проекта на домене
`aifactorymai.ru` через Cloudflare Tunnel. Прикладного кода здесь нет:
бэкенд, фронтенд и документация продукта живут в ветках `main` и
`demo_web` (см. `BRANCHES.md`).

## Состав

```text
deploy/
├── Caddyfile        # раздача статики фронтенда + прокси /api → :8000
├── start-stack.sh   # запуск: uvicorn + Caddy + cloudflared
├── stop-stack.sh    # остановка стека по PID-файлам
└── README.md        # подробности развёртывания и диагностики
```

## Схема публикации

```text
Интернет → Cloudflare (HTTPS) → Tunnel «ai-tehnolog» → Caddy :8787
                                                        ├── /api/* → uvicorn :8000
                                                        └── /*     → frontend-v2/dist/
```

Внешний IP и проброс портов не нужны: `cloudflared` устанавливает
исходящее соединение к Cloudflare, а входящий трафик приходит уже по
нему. HTTPS терминируется на границе Cloudflare, поэтому Caddy работает
по обычному HTTP на localhost (`auto_https off`).

## Развёртывание

Стек запускается на машине, где находится рабочая копия проекта с
собранным фронтендом (ветка `main` или `demo_web`):

```bash
cd dev/frontend-v2 && npm run build
dev/deploy/start-stack.sh
```

Полная инструкция, автозапуск через launchd и проверка доступности —
в [deploy/README.md](deploy/README.md).

## Предварительные требования

- `caddy` и `cloudflared` установлены и доступны в `PATH`;
- туннель `ai-tehnolog` создан в аккаунте Cloudflare, DNS-запись
  `aifactorymai.ru` указывает на него;
- пути в `Caddyfile` и `start-stack.sh` соответствуют расположению
  рабочей копии на конкретной машине (сейчас заданы абсолютными).
