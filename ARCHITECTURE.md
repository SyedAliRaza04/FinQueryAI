# FinQuery AI — System Architecture

> **Version:** 2.0 · **Last Updated:** March 2026

---

## 1. High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FinQuery AI Platform                            │
│                                                                         │
│  ┌─────────────┐    SSE / REST     ┌─────────────────────────┐          │
│  │   React UI  │ ◄──────────────► │   Django REST Backend    │          │
│  │  (Vite Dev) │    Port 5173      │      Port 8000          │          │
│  └─────────────┘                   └──────────-┬─────────────┘          │
│                                                │                        │
│                              ┌──────────────-──┼────────────────┐       │
│                              │                 │                │       │
│                        ┌─────▼──────┐   ┌──────▼─────┐   ┌──────▼───┐   │
│                        │  Ollama    │   │  SQLite    │   │  Redis   │   │ 
│                        │  LLM API   │   │  (Banking) │   │  (Cache) │   │
│                        │  llama3.1  │   │  36 MB     │   │  Opt.    │   │
│                        └────────────┘   └────────────┘   └──────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Repository Structure

```
finquery/
├── config/                          # Django project configuration
│   ├── settings.py                  # CORS, Celery, DB, middleware config
│   ├── urls.py                      # Root URL router → api/ namespace
│   ├── celery.py                    # Celery app config (memory broker for dev)
│   ├── wsgi.py                      # WSGI entry point
│   └── asgi.py                      # ASGI entry point
│
├── finquery_app/                    # Main Django application
│   ├── domain/                      # Domain layer (empty — future entities)
│   ├── application/                 # Application layer
│   │   └── services/
│   │       └── query_service.py     # Core SQL-RAG pipeline + SSE streaming
│   ├── infrastructure/              # Infrastructure layer
│   │   ├── llm/
│   │   │   └── ollama_client.py     # Ollama LLM wrapper (streaming + non-streaming)
│   │   └── repositories/
│   │       └── schema_repository.py # SQLAlchemy schema introspection → DDL
│   ├── interfaces/                  # Interface layer
│   │   └── api/
│   │       └── views.py             # DRF ViewSets + SSE stream endpoint
│   ├── models.py                    # ChatSession + ChatMessage ORM models
│   ├── serializers.py               # DRF serializers for sessions/messages
│   ├── urls.py                      # App-level URL routing
│   └── tasks.py                     # Celery task wrappers
│
├── frontend_react/                  # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx                  # Root component (Sidebar + Chat/Analytics)
│   │   ├── main.jsx                 # Vite entry point
│   │   ├── context/
│   │   │   └── ThemeContext.jsx      # Global theme/accent/font provider
│   │   └── components/
│   │       ├── Sidebar/Sidebar.jsx   # Navigation + chat history + settings
│   │       ├── Chat/
│   │       │   ├── ChatMain.jsx      # SSE streaming controller
│   │       │   ├── ChatFeed.jsx      # Message renderer + CoT + markdown
│   │       │   ├── InputBox.jsx      # Smart input with action chips
│   │       │   └── DataChart.jsx     # Recharts bar chart visualizations
│   │       ├── Analytics/
│   │       │   └── AnalyticsMain.jsx # KPI dashboard with live data
│   │       └── Settings/
│   │           └── SettingsModal.jsx # Theme, accent, font, backend info
│   ├── Dockerfile                   # Node 20 Alpine container
│   └── package.json                 # React 19, recharts, react-markdown
│
├── helpers/                         # One-off data scripts
│   ├── enrich_db.py                 # Faker-based data enrichment
│   └── cleanup_db.py               # Table rename utility
│
├── Dockerfile                       # Python 3.12 backend container
├── docker-compose.yml               # Full stack orchestration
├── requirements.txt                 # Python dependencies
├── manage.py                        # Django management CLI
├── bank_customers.db                # Core banking database (SQLite, 36 MB)
├── db.sqlite3                       # Django metadata DB (sessions, messages)
├── database_schema.json             # Exported schema snapshot
└── research.md                      # Research notes on AI pipeline design
```

---

## 3. Backend Architecture

### 3.1 Clean Architecture Layers

The backend follows the **Clean Architecture** pattern with four layers:

| Layer              | Directory                   | Responsibility                                      |
|--------------------|-----------------------------|------------------------------------------------------|
| **Domain**         | `domain/`                   | Business entities (reserved for future use)           |
| **Application**    | `application/services/`     | Core business logic — the SQL-RAG pipeline            |
| **Infrastructure** | `infrastructure/`           | External integrations — Ollama LLM, SQLAlchemy DB     |
| **Interface**      | `interfaces/api/`           | HTTP layer — DRF ViewSets, SSE endpoint               |

### 3.2 Data Models

```
┌──────────────────────┐        ┌──────────────────────────────┐
│    ChatSession       │        │       ChatMessage            │
├──────────────────────┤        ├──────────────────────────────┤
│ id         UUID (PK) │───1:N──│ id            UUID (PK)      │
│ user_identifier  str │        │ session       FK → Session   │
│ title            str │        │ role          enum(user/asst) │
│ created_at       dt  │        │ content       text            │
│ updated_at       dt  │        │ code_snippet  text (nullable) │
└──────────────────────┘        │ raw_data_json JSON (nullable) │
                                │ cards_json    JSON (nullable) │
                                │ created_at    dt              │
                                └──────────────────────────────┘
```

### 3.3 API Endpoints

| Method | Endpoint                      | Description                             | Auth |
|--------|-------------------------------|-----------------------------------------|------|
| GET    | `/api/sessions/`              | List all chat sessions                  | None |
| POST   | `/api/sessions/`              | Create a new session                    | None |
| GET    | `/api/sessions/{id}/`         | Get session with messages               | None |
| DELETE | `/api/sessions/{id}/`         | Delete a session                        | None |
| GET    | `/api/query/stream/`          | SSE streaming query endpoint            | None |
| POST   | `/api/query/execute/`         | Celery-based async query (non-stream)   | None |
| GET    | `/api/query/{task_id}/status/`| Check Celery task status                | None |
| GET    | `/api/analytics/`             | Live dashboard KPIs from banking DB     | None |

---

## 4. SQL-RAG Pipeline (Core Engine)

The heart of FinQuery is a 6-stage streaming pipeline in `query_service.py`:

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│  Stage 0: GUARDRAIL CHECK           │
│  Keyword-based relevance filter     │
│  Off-topic → sarcastic response     │
│  Financial → proceed to pipeline    │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Stage 1: SCHEMA EXTRACTION         │
│  SQLAlchemy inspector → DDL         │
│  Column descriptions auto-inferred  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Stage 2: TEXT-TO-SQL (Streaming)   │
│  Ollama llama3.1 with CoT prompt    │
│  Tokens streamed as SSE events      │
│  SQL extracted from ```sql``` block  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Stage 3: SQL EXECUTION             │
│  SQLAlchemy → SQLite                │
│  On error: self-correction via LLM  │
│  Re-execute corrected SQL           │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Stage 4: SYNTHESIS (Silent Buffer) │
│  Senior Financial Analyst persona   │
│  CoT/Answer split via regex markers │
│  Answer sent as single token event  │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  Stage 5: CACHE & PERSIST           │
│  Django cache (MD5 key, 24h TTL)    │
│  ChatMessage saved to PostgreSQL/   │
│  SQLite for session history         │
└─────────────────────────────────────┘
```

### SSE Event Protocol

| Event Type        | Payload                        | Purpose                          |
|-------------------|--------------------------------|----------------------------------|
| `status`          | `{content: "Reading schema…"}` | UI toast (silent in current UI)  |
| `reasoning_token` | `{content: "Thought: I…"}`     | Streaming CoT tokens             |
| `sql`             | `{content: "SELECT …"}`        | Extracted clean SQL              |
| `raw_data`        | `{content: [{…}, …]}`          | JSON array of query results      |
| `reasoning_done`  | `{content: "…"}`               | Seals thinking bubble            |
| `token`           | `{content: "**Executive…"}`    | Complete answer (single event)   |
| `done`            | `{}`                           | Signals stream completion        |

---

## 5. Frontend Architecture

### 5.1 Component Tree

```
<ThemeProvider>
  └── <App>
       ├── <Sidebar>
       │    ├── New Chat button
       │    ├── Analytics nav
       │    ├── Chat history (grouped: Today / This Week / Older)
       │    └── Settings (footer) → <SettingsModal>
       │
       └── <main>
            ├── <ChatMain>           (when activeView = 'chat')
            │    ├── Hero State      (when no messages)
            │    ├── <ChatFeed>
            │    │    ├── <ReasoningBlock>    (collapsible CoT)
            │    │    ├── <ReactMarkdown>     (answer with GFM)
            │    │    ├── SQL code block
            │    │    ├── <DataChart>         (recharts bar chart)
            │    │    └── Action bar (Copy, Retry, Visualize)
            │    └── <InputBox>
            │         └── Action chips (Brainstorm, Query DB, Risk, Summary)
            │
            └── <AnalyticsMain>      (when activeView = 'analytics')
                 ├── KPI cards (4x)
                 ├── Transaction volume chart (CSS bars)
                 └── Top portfolios list
```

### 5.2 State Management

| State            | Owner        | Description                    |
|------------------|--------------|--------------------------------|
| `activeView`     | `App`        | `'chat'` or `'analytics'`     |
| `activeSessionId`| `App`        | Current session UUID           |
| `messages`       | `ChatMain`   | Array of chat messages         |
| `isThinking`     | `ChatMain`   | True during SSE streaming      |
| `theme`          | `ThemeContext`| `'dark'`, `'light'`, `'midnight'` |
| `accent`         | `ThemeContext`| Accent color key               |
| `fontSize`       | `ThemeContext`| `'small'`, `'medium'`, `'large'`  |

### 5.3 SSE Stream Lifecycle

```
handleSendMessage()
  │
  ├── Create session (if new)
  ├── Add user message to UI
  ├── Add assistant placeholder
  ├── Set streamingRef = true
  │
  ├── Open EventSource(/api/query/stream/?query=…&session_id=…)
  │     │
  │     ├── onmessage → parse JSON → switch(type)
  │     │     ├── reasoning_token → append to msg.reasoning
  │     │     ├── reasoning_done  → seal CoT, set reasoningDone
  │     │     ├── token           → set msg.content
  │     │     ├── sql             → set msg.code
  │     │     ├── raw_data        → set msg.raw_data_json
  │     │     └── done            → set streamDoneRef, close
  │     │
  │     └── onerror → check streamDoneRef
  │           ├── true  → expected close (ignore)
  │           └── false → real error (show warning)
  │
  └── streamingRef = false
```

---

## 6. Deployment Architecture

### 6.1 Docker Services

```
docker-compose.yml
  │
  ├── backend   (Python 3.12-slim, Gunicorn, port 8000)
  ├── frontend  (Node 20, Nginx, port 80)
  ├── celery    (same image as backend, Celery worker)
  ├── redis     (Redis 7 Alpine, port 6379)
  └── ollama    (ollama/ollama, GPU passthrough, port 11434)
```

### 6.2 Production Stack

```
                     ┌──────────┐
                     │  Nginx   │ :80 / :443
                     └────┬─────┘
                          │
                ┌─────────┼──────────┐
                │         │          │
          /api/*│    /*   │    /ws/* │
                ▼         ▼          ▼
          ┌──────────┐ ┌──────┐ ┌──────────┐
          │ Gunicorn │ │React │ │ Future   │
          │ Django   │ │ SPA  │ │ WebSocket│
          │ :8000    │ │static│ │          │
          └────┬─────┘ └──────┘ └──────────┘
               │
       ┌───────┼───────┐
       │       │       │
       ▼       ▼       ▼
   ┌───────┐┌──────┐┌───────┐
   │SQLite ││Redis ││Ollama │
   │Banking││Cache ││LLM    │
   └───────┘└──────┘└───────┘
```

---

## 7. Security Considerations

| Area             | Current State                        | Production Recommendation             |
|------------------|--------------------------------------|---------------------------------------|
| Authentication   | None (anonymous sessions)            | Add JWT via `rest_framework_simplejwt`|
| CORS             | `ALLOW_ALL_ORIGINS = True`           | Whitelist frontend domain only        |
| Secret Key       | Hardcoded dev key                    | Load from `DJANGO_SECRET_KEY` env var |
| SQL Injection    | Parameterized via SQLAlchemy `text()`| Already safe                          |
| CSRF             | Disabled for API                     | Token-based auth handles this         |
| Rate Limiting    | None                                 | Add `django-ratelimit` or DRF throttle|

---

## 8. Performance & Caching

- **Query Cache:** MD5-hashed query → Django cache (24-hour TTL)
- **LLM Latency:** ~5-15s per query (llama3.1 local inference)
- **SSE Buffering Fix:** Single-event emission avoids WSGI buffering
- **Schema Caching:** DDL extracted on each request (opportunity: cache per session)
- **Database:** SQLite with WAL mode (auto-enabled by SQLAlchemy)
