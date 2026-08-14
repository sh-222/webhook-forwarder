# Tim Mashkov Python Engineering Standards

## 1. Code Style & Typing
- **Target:** Python 3.11+. Use modern syntax (`X | None`, `tuple[int, ...]`, `type Alias = int`).
- **Strict Typing:** All functions, methods, and class attributes must be explicitly typed. No `Any` without explicit justification.
- **Protocols & Interfaces:** Prefer `typing.Protocol` over abstract base classes for decoupling interfaces.
- **Immutability:** Use `@dataclass(frozen=True, slots=True)` or Pydantic models with `frozen=True` for domain entities and values objects.

## 2. Configuration & Data Parsing
- **Settings:** Use `pydantic-settings` with `BaseSettings`. Load configuration explicitly via environment variables.
- **Validation:** Strict validation schemas with Pydantic V2. Keep DTOs separate from Domain models.

## 3. Architecture & Patterns
- **Layer Separation:** 
  - `core/` (settings, logging, base exceptions)
  - `domain/` (entities, domain errors, protocols)
  - `services/` (business logic, orchestrators)
  - `adapters/` or `infrastructure/` (external clients, storage, databases)
  - `presentation/` (CLI, handlers, API endpoints)
- **Dependency Injection:** Explicit dependency inversion. Pass protocols/interfaces into service constructors, avoid global singletons.
- **Lifecycle Management:** Use explicit async context managers (`@asynccontextmanager`) for lifespan, connections, and graceful shutdown.

## 4. Error Handling & Logging
- **Custom Exceptions:** Inherit all project exceptions from a base `AppError`. Never swallow broad exceptions (`except Exception: pass`).
- **Structured Logging:** Use `structlog` or contextual logging with key-value pairs (e.g., `logger.info("event_name", user_id=123, status="ok")`).
- **No Prints:** Standard `print()` is strictly forbidden.

## 5. Async & Concurrency
- Fully asynchronous architecture (`async`/`await`).
- Use `asyncio.TaskGroup` (Python 3.11+) or explicit worker pools for concurrent jobs.
- Handle `asyncio.CancelledError` properly to ensure clean shutdown.
