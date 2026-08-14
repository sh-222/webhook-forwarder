# Async Rate-Limited Webhook Forwarder & Dead-Letter Queue

Асинхронный сервис на Python 3.12 для пересылки вебхуков с rate limiting, exponential backoff и Dead Letter Queue.

## Архитектура

```
webhook-forwarder/
├── core/           # Конфигурация, логирование, исключения
├── domain/         # DTO, протоколы (интерфейсы)
├── services/       # Бизнес-логика: rate limiter, sender, DLQ, worker pool
├── adapters/       # Внешние клиенты (httpx)
├── presentation/   # CLI интерфейс (Rich)
└── main.py         # Точка входа + demo
```

## Бизнес-логика

1. **Event Queue** — PriorityQueue с поддержкой приоритетов (0-5)
2. **Worker Pool** — N асинхронных воркеров (настраивается через env)
3. **Rate Limiter** — Token Bucket на каждый `target_url`
4. **Exponential Backoff** — `min(base_delay * 2^retry, max_delay)` + jitter
5. **Dead Letter Queue** — JSON Lines файл + структурированные алерты
6. **Graceful Shutdown** — обработка SIGINT/SIGTERM, ожидание активных задач

## Быстрый старт

```bash
# Установка uv (если не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Клонирование
git clone https://github.com/sh-22/webhook-forwarder.git
cd webhook-forwarder

# Установка зависимостей
uv sync

# Запуск demo
uv run python main.py
```

## Конфигурация

Все настройки через переменные окружения с префиксом `WEBHOOK_`:

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `WEBHOOK_WORKER_COUNT` | `4` | Количество async воркеров |
| `WEBHOOK_QUEUE_MAX_SIZE` | `1000` | Максимальный размер очереди |
| `WEBHOOK_RATE_LIMIT_RATE` | `10.0` | Токенов в секунду на URL |
| `WEBHOOK_RATE_LIMIT_CAPACITY` | `20` | Макс. токенов в bucket |
| `WEBHOOK_MAX_RETRIES` | `3` | Максимальное количество повторов |
| `WEBHOOK_BASE_DELAY` | `1.0` | Базовая задержка backoff (сек) |
| `WEBHOOK_MAX_DELAY` | `60.0` | Максимальная задержка backoff (сек) |
| `WEBHOOK_HTTP_TIMEOUT` | `10.0` | HTTP таймаут (сек) |
| `WEBHOOK_DLQ_FILE` | `dlq.jsonl` | Путь к файлу DLQ |
| `WEBHOOK_SHUTDOWN_TIMEOUT` | `30.0` | Таймаут graceful shutdown (сек) |

Пример `.env` файла:

```env
WEBHOOK_WORKER_COUNT=8
WEBHOOK_RATE_LIMIT_RATE=50.0
WEBHOOK_MAX_RETRIES=5
WEBHOOK_DLQ_FILE=/var/log/webhook/dlq.jsonl
```

## Использование в коде

```python
import asyncio
from domain.entities import Event
from services.worker_pool import WorkerPool

async def main():
    pool = WorkerPool()
    await pool.start()

    event = Event(
        payload={"event": "user.created", "user_id": 123},
        target_url="https://api.example.com/webhook",
        priority=3,
    )

    await pool.submit(event)
    await asyncio.sleep(10)
    await pool.shutdown()

asyncio.run(main())
```

## Технологии

- **Python 3.12+** —现代ый синтаксис типов
- **pydantic-settings** — валидация конфигурации
- **structlog** — структурированное JSON логирование
- **httpx** — async HTTP клиент
- **Rich** — форматированный CLI вывод
- **uv** — управление пакетами и виртуальными окружениями

## Стандарты

Проект следует [Tim Mashkov Python Engineering Standards](opencode/context/timmashkov-style.md):

- Слоистая архитектура (core → domain → services → adapters → presentation)
- Dependency Injection через протоколы
- Immutable dataclass (`frozen=True, slots=True`)
- Строгая типизация всех функций
- structlog вместо print()
- Кастомные исключения от `AppError`

## Лицензия

MIT
