# Telegram AI Assistant

## 1. Project Overview

This repository contains an AI-powered Telegram bot built using Python, aiogram 3.x, and Google Gemini API. It was developed as a technical assessment to demonstrate Clean Architecture and Domain-Driven Design (DDD) principles in a real-time messaging application. The bot supports multi-turn conversation memory, prompt versioning, structured prompt injection defenses, and group chat mentions. All interaction history, user records, and AI execution telemetry are transactionally persisted to a PostgreSQL database using SQLAlchemy 2.0 and AsyncPG.

---

## 2. Features

- **Multi-Turn Chat**: Retains conversation history per user using PostgreSQL sliding windows.
- **Group Chat Mentions**: Responds in Telegram groups when explicitly mentioned via `@username` or when replied to directly.
- **Prompt Engineering & Versioning**: Manages prompt templates via `PromptRegistry` (`system_base:v1.0.0`) with variable substitution (`{user_name}`, `{tier}`).
- **Prompt Injection Defense**: Encapsulates user inputs inside `<user_query>` XML blocks to prevent prompt overriding.
- **Token Trimming**: Trims older history turns using character-to-token heuristics ($\approx 4\text{ chars/token}$) to fit within configured token limits.
- **Transactional Persistence**: Implements `AsyncUnitOfWork` for atomic multi-repository writes (`users`, `conversations`, `messages`, `ai_responses`, `audit_logs`).
- **Telemetry & Diagnostics**: Records prompt tokens, completion tokens, latency, and finish reason per response; includes a `/health` system check command.
- **Middleware Pipeline**: Injects unique UUID correlation IDs per request and logs structured execution timing using `structlog`.

---

## 3. Architecture

The codebase strictly separates concerns into four layers following the Dependency Inversion Principle:

```
[ Telegram Client / Ingress ]
            │
            ▼
[ Presentation Layer: aiogram 3.x Routers & Middlewares ]
            │
            ▼
[ Application Layer: ConversationService & PromptBuilder ]
       │            │
       ▼            ▼
[ Domain Layer: Abstract Interfaces & Entities ]
       ▲            ▲
       │            │
[ Infrastructure Layer: Gemini Adapter & PostgreSQL AsyncUnitOfWork ]
```

- **Presentation**: Catches Telegram updates, applies correlation IDs and error handling, and routes events.
- **Application**: Coordinates conversation flow, resolves active threads, builds prompts, and manages history windows.
- **Domain**: Defines abstract interfaces (`ILLMProvider`, `IUnitOfWork`, repositories) and pure data structures without third-party framework leaks.
- **Infrastructure**: Implements Gemini API calls via `google-genai` SDK and database persistence via SQLAlchemy 2.0 and AsyncPG.

---

## 4. Project Structure

- `app/domain/`: Contains pure Python domain entities, custom exceptions, and repository interfaces.
- `app/application/`: Contains orchestration services (`ConversationService`), Data Transfer Objects (DTOs), and prompt construction logic (`PromptBuilder`).
- `app/infrastructure/`: Implements concrete database repositories, `AsyncUnitOfWork`, and the Gemini LLM adapter.
- `app/presentation/`: Implements Telegram routers (`chat`, `start`, `health`), custom middlewares, and bot factory.
- `app/core/`: Handles application settings, global exception classes, security helpers, and structured logging setup.
- `tests/`: Contains 32 unit and integration test modules for config, repositories, LLM adapter, prompt builder, and end-to-end pipeline.

---

## 5. Prerequisites

- **Python**: Version 3.10 or higher.
- **PostgreSQL**: Version 14 or higher (or cloud-managed PostgreSQL like Aiven / Supabase).
- **Telegram Bot Token**: Obtained from [@BotFather](https://t.me/BotFather).
- **Google Gemini API Key**: Obtained from [Google AI Studio](https://ai.google.dev/).

---

## 6. Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Assessment
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell)
   .\.venv\Scripts\activate
   # Linux / macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .
   ```

4. **Set up environment configuration**:
   ```bash
   cp .env.example .env
   ```

5. **Initialize database tables**:
   ```bash
   python app/infrastructure/database/init_db.py
   ```

6. **Start the application**:
   ```bash
   python run_bot.py
   ```

7. **Verify startup**:
   Look for logger output: `Starting Telegram Bot Long Polling Runner...` and test `/start` or `/health` in Telegram.

---

## 7. Configuration

All configuration is managed via environment variables defined in `.env` (loaded by `app/core/config.py`):

| Variable | Type | Description |
| :--- | :--- | :--- |
| `APP_ENV` | String | Application environment (`development`, `production`, `testing`). |
| `LOG_LEVEL` | String | Logging verbosity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `DEBUG` | Boolean | Enables debug flags and detailed log outputs. |
| `TELEGRAM_BOT_TOKEN` | String | Bot token issued by BotFather. |
| `TELEGRAM_WEBHOOK_SECRET` | String | Secret header token for FastAPI webhook verification. |
| `TELEGRAM_WEBHOOK_URL` | String | Optional public URL endpoint for webhook mode (empty for long polling). |
| `GEMINI_API_KEY` | String | Google Gemini API secret key. |
| `GEMINI_MODEL_NAME` | String | Gemini model identifier (e.g., `gemini-flash-latest`). |
| `GEMINI_TIMEOUT_SECONDS` | Float | Maximum timeout budget in seconds per LLM request (default: `15.0`). |
| `GEMINI_MAX_RETRIES` | Integer | Max retry attempts for failed LLM calls (default: `3`). |
| `DATABASE_URL` | String | Async PostgreSQL connection string (`postgresql+asyncpg://...`). |
| `REDIS_URL` | String | Connection string for Redis cache instance. |
| `RATE_LIMIT_MESSAGES_PER_MIN` | Integer | Configured rate limit threshold per user. |

---

## 8. Running the Project

### Option A: Long Polling (Recommended for Local Dev)
Run the single-process long polling runner:
```bash
python run_bot.py
```

### Option B: FastAPI Server with Lifespan Polling / Webhook
Run the main FastAPI application server:
```bash
python app/main.py
```

---

## 9. Testing & Quality Checks

### Run Automated Tests
```bash
pytest -v
```
*Expected Result*: 32 passing test cases across 8 test modules (`test_config.py`, `test_conversation_service.py`, `test_end_to_end_pipeline.py`, `test_gemini_client.py`, `test_prompt_builder.py`, `test_repositories.py`, `test_security.py`, `test_telegram_handlers.py`).

### Type Checking
```bash
mypy app
```
*Expected Result*: `Success: no issues found in 38 source files`.

### Linting & Formatting
```bash
ruff check app tests
black --check app tests
```

### Manual Testing
1. Send `/start` to `@agent_sen_09_bot` → Verify welcome message and user registration in DB.
2. Send `/health` → Verify status response indicating database and Gemini reachability.
3. Send `"My favorite language is Python"` followed by `"What is my favorite language?"` → Verify conversational memory response.
4. Add bot to a group and send `@agent_sen_09_bot hello` → Verify group reply behavior.

---

## 10. Assignment Coverage

| Requirement | Status | Notes |
| :--- | :---: | :--- |
| Clean Architecture & DDD Separation | Implemented | Domain layer has zero external framework dependencies; infrastructure implements abstract interfaces. |
| PostgreSQL Database Persistence | Implemented | Uses SQLAlchemy 2.0 ORM and AsyncPG for async DB operations across 5 tables. |
| Async Unit of Work Pattern | Implemented | `AsyncUnitOfWork` ensures atomic multi-repository updates with commit/rollback logic. |
| Telegram Ingress (aiogram 3.x) | Implemented | Built with aiogram 3.x routers, command handlers (`/start`, `/health`), and typing indicators. |
| Telegram Middlewares | Implemented | `RequestContextMiddleware` (correlation ID), `LoggingMiddleware`, and `ExceptionHandlingMiddleware`. |
| Google Gemini API Integration | Implemented | Implemented via `google-genai` SDK with retry logic, timeout budgets, and error translation. |
| Prompt Versioning & Formatting | Implemented | `PromptRegistry` manages `system_base:v1.0.0` templates with dynamic variable insertion. |
| Prompt Injection Defense | Implemented | User inputs are formatted inside `<user_query>` XML blocks to prevent prompt hijacking. |
| Context Memory & Token Trimming | Implemented | Sliding history window trims older turns using a character-to-token heuristic. |
| Group Chat Support | Implemented | Responds in group chats only when tagged (`@bot`) or directly replied to. |
| Unit & Integration Test Suite | Implemented | 32 automated tests passing with PyTest, MyPy type safety, and Black/Ruff formatting. |

---

## 11. Design Decisions

### 1. Async Unit of Work Pattern for Database Writes
- **Decision**: Implemented `AsyncUnitOfWork` context manager in `app/infrastructure/database/repositories/unit_of_work.py`.
- **Rationale**: Saving a user turn requires updating multiple tables (`messages`, `conversations`, `ai_responses`). Wrapping these in a single unit of work guarantees that either all writes commit or none do.
- **Tradeoff**: Slightly higher abstraction complexity compared to direct session usage, but prevents orphaned message records.

### 2. Module-Level Router Singleton Reset
- **Decision**: In `app/presentation/telegram/dispatcher.py`, `r._parent_router` is reset to `None` before calling `dp.include_router(r)`.
- **Rationale**: `aiogram 3.x` routers raise errors or skip registration if re-attached to a new `Dispatcher` during application reloads or testing cycles.
- **Tradeoff**: Accesses an internal attribute (`_parent_router`), but avoids runtime update routing drops.

### 3. XML Encapsulation for User Queries
- **Decision**: Injected user text is wrapped in `<user_query>...</user_query>` tags inside the constructed prompt.
- **Rationale**: Clarifies boundaries between system instructions and untrusted user input for the Gemini model.
- **Tradeoff**: Adds minor character overhead per prompt, but significantly mitigates prompt injection risks.

---

## 12. Current Limitations

- **Character-Based Token Estimation**: Token counting in `PromptBuilder` uses a heuristic ratio ($\approx 4\text{ chars/token}$) rather than an exact tokenizer API call before prompt assembly.
- **Single Active Conversation Thread**: Currently, the system resolves one active conversation per user (`is_active = True`). Multi-thread selection via UI commands is not implemented.
- **Rate Limiting Middleware Not Enforced**: Rate limiting configuration exists in `config.py` and `RateLimitExceededException` is defined, but active per-user sliding window middleware (e.g. via Redis) is not wired in the ingress pipeline.

---

## 13. What I'd Build Next

- **Redis-Backed Cache**: Cache user state and prompt templates in Redis to reduce PostgreSQL read latency on high-frequency messages.
- **Exact Token Counting**: Integrate Gemini's `count_tokens` SDK method to calculate exact prompt length prior to dispatching.
- **Webhook Production Deployment**: Set up HTTPS webhook endpoint integration with Nginx reverse proxy and SSL termination.
- **Streaming Response Support**: Implement `generate_content_stream` to stream token responses back to Telegram in real-time.

---

## 14. AI Usage

AI development tools were used strictly as an productivity aid for code completion, boilerplate generation, and pytest fixture templates.

- **System Architecture & Domain Design**: Architected manually following Clean Architecture / DDD patterns, establishing domain boundary interfaces (`ILLMProvider`, `IUnitOfWork`, repository contracts).
- **Core Logic & Verification**: All business rules in `ConversationService`, prompt versioning in `PromptBuilder`, PostgreSQL transaction handling in `AsyncUnitOfWork`, and aiogram middlewares were implemented, code-reviewed, and verified through automated tests (`pytest`) and static type checks (`mypy`).
