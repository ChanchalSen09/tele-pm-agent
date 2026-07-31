# Autonomous Agentic Project Manager on Telegram

> **Kwartz Project Manager Bot**  
> Developed by **Chanchal Sen**  
> **Live Bot Demo**: [https://t.me/agent_sen_09_bot](https://t.me/agent_sen_09_bot)

---

## 1. Project Overview

This repository contains an **Autonomous Agentic Project Manager** built for Telegram team groups using Python, aiogram 3.x, Google Gemini API, and PostgreSQL (AsyncPG & SQLAlchemy 2.0). The bot serves as an in-group project office that creates, assigns, tracks, and closes tasks, actively pulls status updates from team members, and generates real-time project progress reports. It strictly enforces Clean Architecture and Domain-Driven Design (DDD) principles with an Async Unit of Work pattern for ACID transactional data safety.

---

## 2. Features

- **Agentic Task Management**: Create, assign, track, update, and close project tasks (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`) via `/create_task`, `/tasks`, `/status`.
- **Proactive Status Pulling**: Use `/pull_updates` to have the agent actively tag assigned team members (`@username`) in Telegram groups and request progress updates for open tasks.
- **Project Progress Reports**: Generate sprint completion summaries and task breakdowns using `/status`.
- **Multi-Turn Group Conversation Memory**: Retains conversation history per user using PostgreSQL sliding window context memory.
- **Group Chat Mention Filtering**: Operates inside Telegram team groups, responding only when tagged (`@agent_sen_09_bot`) or replied to directly.
- **Prompt Engineering & XML Injection Defense**: Encapsulates user inputs inside `<user_query>` tags and manages versioned system prompts (`system_base:v1.0.0`).
- **Transactional Persistence**: Implements `AsyncUnitOfWork` for atomic multi-repository writes (`users`, `conversations`, `messages`, `tasks`, `ai_responses`, `audit_logs`).
- **Telemetry & Health Diagnostics**: Records prompt/completion token metrics, execution latency, and provides a system `/health` check command.

---

## 3. Architecture

The codebase strictly separates concerns into four layers following the Dependency Inversion Principle:

```
[ Telegram Team Group / Client ]
            │
            ▼
[ Presentation Layer: aiogram 3.x Routers & Middlewares ]
            │
            ▼
[ Application Layer: ConversationService & PromptBuilder ]
       │            │
       ▼            ▼
[ Domain Layer: Abstract Interfaces & Task Domain Entities ]
       ▲            ▲
       │            │
[ Infrastructure Layer: Gemini LLM Adapter & PostgreSQL AsyncUnitOfWork ]
```

- **Presentation**: Processes Telegram updates, applies correlation IDs and exception safety nets, and routes commands (`/tasks`, `/create_task`, `/status`, `/pull_updates`).
- **Application**: Coordinates project workflows, task queries, sliding context memory windows, and prompt payload construction.
- **Domain**: Defines abstract interfaces (`ILLMProvider`, `ITaskRepository`, `IUnitOfWork`) and pure domain entities without framework leaks.
- **Infrastructure**: Implements Gemini LLM calls via `google-genai` SDK and database persistence via SQLAlchemy 2.0 and AsyncPG.

---

## 4. Project Structure

- `app/domain/`: Pure Python domain entities, custom exception classes, and repository contracts (`ITaskRepository`, `ILLMProvider`).
- `app/application/`: Orchestration services (`ConversationService`), DTOs (`TaskCreateDTO`), and prompt formatting logic (`PromptBuilder`).
- `app/infrastructure/`: Implements concrete database repositories (`TaskRepository`, `UserRepository`), `AsyncUnitOfWork`, and Gemini client adapter.
- `app/presentation/`: Telegram routers (`chat`, `start`, `health`), custom middlewares, and bot creation factory.
- `app/core/`: Application settings, security helpers, exception hierarchies, and structured logging configuration (`structlog`).
- `tests/`: 33 unit and integration test modules for config, task repository, LLM adapter, prompt builder, and end-to-end pipeline.

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
   git clone https://github.com/ChanchalSen09/telegram-ai-assistant.git
   cd telegram-ai-assistant
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
   Look for logger output: `Starting Telegram Bot Long Polling Runner...` and test `/start` or `/tasks` in Telegram.

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
python -m pytest -v
```
*Expected Result*: 33 passing test cases across test modules (`test_config.py`, `test_conversation_service.py`, `test_end_to_end_pipeline.py`, `test_gemini_client.py`, `test_prompt_builder.py`, `test_repositories.py`, `test_security.py`, `test_task_repository.py`, `test_telegram_handlers.py`).

### Type Checking & Code Quality
```bash
ruff check app tests
```

### Manual Testing
1. Send `/start` or `/help` to `@agent_sen_09_bot` → Verify onboarding commands.
2. Run `/create_task Fix auth bug @alex` → Verify task creation and assignment in DB.
3. Run `/tasks` → Verify project task board rendering (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`).
4. Run `/status` → Verify project completion percentage and status breakdown.
5. Run `/pull_updates` in group → Verify agent tags assigned team members (`@alex`) for progress updates.

---

## 10. Assignment Coverage

| Requirement | Status | Notes |
| :--- | :---: | :--- |
| Live inside a Telegram group | Implemented | Serves as group office with `@mention` filtering and tag cleanup. |
| Talk via Telegram channels only | Implemented | 100% Telegram interface (group + DMs). Zero external web UI or Slack dependence. |
| Manage project tasks | Implemented | `TaskModel` and `TaskRepository` for task creation, assignment, tracking, and completion. |
| Pull updates from users | Implemented | `/pull_updates` command actively tags assigned members and requests progress reports. |
| Provide regular status | Implemented | `/status` command generates sprint completion percentages and task summaries. |
| Clean Architecture & DDD | Implemented | Domain layer has zero external framework dependencies; infrastructure implements abstract contracts. |
| Async Unit of Work Pattern | Implemented | `AsyncUnitOfWork` ensures atomic multi-table updates (`users`, `conversations`, `messages`, `tasks`). |
| Automated Test Suite | Implemented | 33 passing PyTest unit & integration tests covering tasks, repositories, Gemini client, and routers. |

---

## 11. Design Decisions

### 1. Task Domain Model & Async Unit of Work
- **Decision**: Added `TaskModel` and `TaskRepository` managed through `AsyncUnitOfWork`.
- **Rationale**: Project management requires persisting discrete tasks alongside conversation messages. Wrapping both in `AsyncUnitOfWork` ensures task state and message logs remain synchronized.
- **Tradeoff**: Increases entity count, but prevents stale or untracked task states.

### 2. Explicit Command & Natural Language Hybrid Task Interface
- **Decision**: Implemented explicit slash commands (`/create_task`, `/tasks`, `/status`, `/pull_updates`) combined with NLP conversational capabilities.
- **Rationale**: Commands provide predictable, deterministic task operations for group members, while Gemini NLP enables natural chat interaction.
- **Tradeoff**: Requires routing both commands and free-form message updates.

### 3. XML Encapsulation for Prompt Safety
- **Decision**: Untrusted user messages are wrapped inside `<user_query>...</user_query>` XML blocks.
- **Rationale**: Prevents untrusted text in team groups from overriding system prompt instructions.
- **Tradeoff**: Minor character overhead, but guarantees system prompt protection.

---

## 12. Current Limitations

- **Character-Based Token Estimation**: Token counting in `PromptBuilder` uses a heuristic ratio ($\approx 4\text{ chars/token}$) rather than an exact tokenizer API call.
- **In-Memory Polling Cadence Trigger**: Periodic status pulls are currently triggered via `/pull_updates` or long polling lifespan tasks rather than an external cron daemon.
- **Single Group Project Context**: Active tasks are tracked across a global project scope per installation rather than multi-project workspace switching.

---

## 13. What I'd Build Next

- **Automated Cron Status Cadence**: Schedule daily automated update pulls (e.g. 9 AM every weekday) via APScheduler or Celery.
- **Interactive Inline Telegram Buttons**: Add inline keyboard buttons (`[Mark Done]`, `[Block]`, `[Reassign]`) on task notifications.
- **Redis-Backed Task Caching**: Cache task board queries in Redis to minimize PostgreSQL database load in high-volume groups.
- **Streaming Response Support**: Implement `generate_content_stream` to stream status reports to Telegram in real-time.

---

## 14. AI Usage

AI development tools were used strictly as a productivity aid for code completion, boilerplate generation, and pytest fixture templates.

- **System Architecture & Domain Design**: Architected manually following Clean Architecture / DDD patterns, establishing domain boundary interfaces (`ITaskRepository`, `ILLMProvider`, `IUnitOfWork`).
- **Core Logic & Verification**: All business rules in `ConversationService`, prompt versioning in `PromptBuilder`, PostgreSQL transaction handling in `AsyncUnitOfWork`, and task commands were implemented, code-reviewed, and verified through 33 automated PyTest tests.
