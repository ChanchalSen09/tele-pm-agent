# Autonomous Agentic Project Manager on Telegram

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Google Gemini API](https://img.shields.io/badge/Google%20Gemini%20AI-2.5--flash-orange.svg)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791.svg)](https://www.postgresql.org/)
[![Test Suite](https://img.shields.io/badge/tests-63%20passed-brightgreen.svg)](tests/)

> **Telegram AI Project Manager Bot**  
> Developed by **Chanchal Sen**  
> **Live Bot Demo**: [https://t.me/agent_sen_09_bot](https://t.me/agent_sen_09_bot)

---

## Overview

An autonomous, agentic Project Manager bot designed for Telegram team groups. Powered by Python 3.10+, **aiogram 3.x**, **FastAPI**, **Google Gemini AI API (`google-genai`)**, and **PostgreSQL** (AsyncPG & SQLAlchemy 2.0).

The bot serves as an in-group AI Project Management Office (PMO) to create, assign, track, and close tasks, pull status updates from team members, coordinate daily standups, and generate real-time progress reports using Clean Architecture and Domain-Driven Design (DDD) with Async Unit of Work.

---

## Features

- 🎯 **Task Management**: Create, update, track, and close tasks (`TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`) via slash commands or natural language AI chat.
- 📣 **Proactive Status Pulling**: Tag assigned team members (`@username`) in Telegram groups to request progress reports on open tasks via `/pull_updates`.
- ⏰ **Automated Reminders**: Background service (`ReminderService`) running every 30 minutes to notify assignees of pending or upcoming tasks.
- 📋 **Asynchronous Standups**: Conduct daily team standups using `/standup` or `/checkin` with aggregated summaries via `StandupEngine`.
- 👤 **Smart User & Role Resolution**: Dynamically map Telegram handles (`@username`) or roles (`@backend-lead`, `@frontend-dev`) to team member entities.
- 📊 **Progress & Health Reports**: Generate sprint completion summaries, task breakdowns, and service health diagnostics via `/status` and `/health`.
- 🛡️ **Prompt Safety & PII Protection**: XML prompt framing (`<user_query>`), system prompt versioning, PII sanitization (`SecurityPII`), and content guardrails.

---

## Project Architecture & Structure

Built following the **Dependency Inversion Principle**:

```
[ Telegram Group / DM Client ]
              │
              ▼
[ Presentation Layer: aiogram 3.x Routers & FastAPI ]
              │
              ▼
[ Application Layer: Business Engines & Services ]
(ConversationService, NaturalPMEngine, StandupEngine, UserResolver, ReminderService)
              │
              ▼
[ Domain Layer: Abstract Contracts & Entities ]
              ▲
              │
[ Infrastructure Layer: Gemini LLM Adapter & Async Unit of Work Persistence ]
```

```
.
├── app/
│   ├── main.py                     # FastAPI Webhook / Lifespan Long-Polling entrypoint
│   ├── core/                       # Config, guardrails, security, PII sanitizer & logger
│   ├── domain/                     # Pure domain models & repository contracts
│   ├── application/                # Business services, prompt builder & DTOs
│   ├── infrastructure/             # PostgreSQL AsyncPG repositories & Gemini LLM adapter
│   └── presentation/               # Telegram routers (chat, start, standup, health)
├── alembic/                        # Database migration scripts
├── scripts/                        # DB reset utilities
├── tests/                          # 18 unit & integration test modules (63 passing tests)
├── Dockerfile                      # Production Docker container image
├── docker-compose.yml              # Local multi-container environment (App + DB + Redis)
└── pyproject.toml                  # Project metadata & dependencies
```

---

## Telegram Command Reference

| Command | Syntax / Example | Description |
| :--- | :--- | :--- |
| `/start` | `/start` | Bot greeting and feature onboarding. |
| `/help` | `/help` | Complete user guide and command reference. |
| `/health` | `/health` | Diagnostic probe for database and service status. |
| `/tasks` | `/tasks [IN_PROGRESS]` | Display task board filtered by status. |
| `/create_task` | `/create_task Fix login bug @alex priority:HIGH` | Create and assign a project task. |
| `/update_task` | `/update_task 3 IN_PROGRESS` | Update task status or priority. |
| `/close_task` | `/close_task 3` | Mark a task as completed (`DONE`). |
| `/status` | `/status` | Generate sprint progress report & task breakdown. |
| `/pull_updates` | `/pull_updates` | Tag team members for progress updates on open tasks. |
| `/standup` | `/standup Completed API endpoints, blocked on DB` | Submit daily standup check-in. |

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 14+ (or Supabase / Aiven)
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Google Gemini API Key ([Google AI Studio](https://ai.google.dev/))

### 2. Local Setup

```bash
# Clone repository
git clone https://github.com/ChanchalSen09/tele-pm-agent.git
cd tele-pm-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment variables
cp .env.example .env
# Edit .env and enter TELEGRAM_BOT_TOKEN and GEMINI_API_KEY

# Run database migrations
alembic upgrade head

# Start application (Long Polling)
python app/main.py
```

### 3. Docker Deployment

```bash
docker compose up --build -d
```

---

## Testing & Quality Assurance

Run the PyTest test suite (63 passing tests):

```bash
python -m pytest
```

Run code quality & linting checks:

```bash
ruff check app tests
```
