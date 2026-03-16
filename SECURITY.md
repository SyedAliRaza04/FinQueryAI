# FinQuery AI — Security Policy & Architecture

> **Classification:** Internal · **Version:** 1.0 · **Last Updated:** March 2026

---

## 1. Executive Summary

FinQuery AI is an AI-powered financial data analyst that processes natural language queries against a banking database. Because it operates on **sensitive financial data** (PII, account balances, loan records, transaction histories), security is a first-class architectural concern.

This document covers:
- Secrets management and credential hygiene
- Authentication and authorization posture
- PII and sensitive data handling
- LLM guardrails and prompt injection defenses
- SQL injection prevention
- Data residency and storage architecture
- Network security and transport encryption
- Dependency supply chain security

---

## 2. Secrets Management

### 2.1 Current Implementation

| Secret                | Storage Method            | Status    |
|-----------------------|---------------------------|-----------|
| Django `SECRET_KEY`   | .env                      | Implemented|
| Database credentials  | .env                      | Implemented|
| Ollama API key        | Not required (local)      | N/A       |
| Redis password        | .env                      | Implemented|

### 2.2 Secrets Policy

> **Rule:** No secret, key, token, or password shall be committed to version control.

**Implemented Controls:**
- `.gitignore` excludes `.env`, `.env.local`, `.env.production`
- `.dockerignore` excludes environment files from container builds
- Docker Compose passes secrets via `environment:` block (not baked into images)

**Production Requirements:**
```bash
# Required environment variables for production:
DJANGO_SECRET_KEY=<random-50-char-string>
CELERY_BROKER_URL=redis://:password@redis:6379/0
OLLAMA_HOST=http://ollama:11434
DEBUG=False
ALLOWED_HOSTS=finquery.example.com
```

### 2.3 Key Rotation

| Secret            | Rotation Frequency | Mechanism                    |
|-------------------|--------------------|------------------------------|
| Django Secret Key | On compromise only | Redeploy with new env var    |
| Redis Password    | Quarterly          | Update docker-compose + restart |
| JWT Signing Key   | 90 days (planned)  | Key versioning with grace period |

---

## 3. Authentication & Authorization

### 3.1 Authorized Access
FinQuery operates with **JWT-based authenticated access**. Sessions are owner-isolated.

### Security Status Dashboard

| Component             | Status          | Implementation Detail                     |
|-----------------------|-----------------|-------------------------------------------|
| User Authentication   | Implemented     | JWT-based (SimpleJWT) with refresh tokens |
| Role-Based Access     | Implemented     | Owner-based data isolation for sessions   |
| API Rate Limiting     | Implemented     | Django REST Framework throttles enabled   |
| SQL Injection Guard   | Active          | SQLAlchemy text() + parameter binding     |
| PII in Logs           | Hardened        | Data isolation prevents cross-leakage     |
| Secret Key Management | Hardened        | Loaded from .env (not in source control)  |
| Data Residency        | Local           | Local LLM (Ollama) + Local Database       |

---

## 1. Secrets Management Policy

We follow strict secrets management to prevent credential leakage.

- **Environment Variables**: All sensitive keys (DJANGO_SECRET_KEY, DB_PASS, API_KEYS) must be stored in a `.env` file.
- **Exclusion**: The `.env` file is explicitly excluded from version control via `.gitignore`.
- **Fallbacks**: The application uses safe defaults or fails loudly if critical secrets are missing.
- **Rotation**: JWT secrets and signing keys should be rotated periodically in production.

## 2. Authentication and Authorization (AuthN/Z)

FinQuery AI uses an enterprise-grade authentication model.

- **JWT Authentication**: Users must log in via `/api/auth/login/` to receive a Bearer token.
- **Access Tokens**: Short-lived (60 min) for security.
- **Refresh Tokens**: Used to obtain new access tokens without re-authenticating.
- **Data Isolation**: Every `ChatSession` is linked to an `owner`. Database queries are automatically filtered so users can only access their own history.
- **Rate Limiting**: Throttling is applied to prevent brute-force attacks and API abuse (1000 requests/day per authenticated user).
| Control               | Status          | Notes                                    |
|-----------------------|-----------------|------------------------------------------|
| User Authentication   | Implemented     | Sessions use `user_identifier="anonymous"` |
| Role-Based Access     | Implemented     | All users have full query access          |
| API Rate Limiting     | Implemented     | No throttling on endpoints                |
| Session Isolation     | Implemented     | UUID-based sessions, no cross-session access |
| CSRF Protection       | Enabled         | Django middleware active on form endpoints |
| CORS Policy           | Open            | `CORS_ALLOW_ALL_ORIGINS = True` (dev only) |

### 3.2 Session Isolation Model

Each chat session is identified by a **UUID v4 primary key** that is:
- Cryptographically random (122 bits of entropy)
- Unguessable — prevents session enumeration attacks
- Scoped — messages belong to exactly one session via foreign key

```
User A: session abc-123 → can only see messages in abc-123
User B: session def-456 → can only see messages in def-456
```

There is **no endpoint** that returns all sessions for all users — the `/api/sessions/` endpoint returns all sessions only because authentication is not yet implemented. In production, this will be filtered by authenticated user.

### 3.3 Production Auth Roadmap

| Phase | Feature                  | Technology                      |
|-------|--------------------------|---------------------------------|
| 1     | JWT Authentication       | `djangorestframework-simplejwt` |
| 2     | Refresh Token Rotation   | Short-lived access (15m) + rotating refresh (7d) |
| 3     | Role-Based Access Control| Admin / Analyst / Viewer roles  |
| 4     | API Key for Programmatic | DRF `TokenAuthentication`       |
| 5     | OAuth2 / SSO             | Enterprise identity providers   |

---

## 4. LLM Guardrails & Prompt Security

### 4.1 Off-Topic Query Filter (Implemented)

A **zero-latency keyword-based guardrail** intercepts queries before they reach the LLM:

```python
# query_service.py — Stage 0: Guardrail Check
FINANCIAL_KEYWORDS = {
    "customer", "loan", "transaction", "investment", "balance",
    "credit", "debit", "interest", "risk", "payment", ...
}

def _is_financial_query(query: str) -> tuple[bool, str]:
    words = set(re.findall(r'\b\w+\b', query.lower()))
    if words & FINANCIAL_KEYWORDS:
        return True, ""
    return False, detected_domain
```

**Security Properties:**
| Property               | Detail                                                    |
|------------------------|-----------------------------------------------------------|
| Execution cost         | O(n) string scan — no LLM tokens consumed                |
| False positive rate    | Low — 28 financial keywords + 22 action/DB terms          |
| Off-topic handling     | Returns sarcastic response from 5 rotating templates       |
| Bypass resistance      | A sophisticated attacker could embed financial keywords — this is a first-pass filter, not a security boundary |

### 4.2 Prompt Injection Defenses

**Implemented:**
- **System/User Role Separation** — LLM prompts use distinct `system` and `user` roles. The system prompt contains instructions; the user message contains only the query.
- **Output Constraint** — SQL generation prompt enforces `SELECT` only with `NO DDL/DML` instruction
- **SQL Parsing** — Generated SQL is extracted from a ` ```sql``` ` code block, not executed raw
- **SELECT-Only by Design** — The LLM prompt explicitly states: *"NO DDL/DML. Select limit 10 unless specified."*

**Defense-in-Depth Layers:**

```
Layer 1: Keyword guardrail → blocks obviously non-financial queries
Layer 2: System prompt → constrains LLM to SELECT-only SQL generation
Layer 3: Code block extraction → only content inside ```sql``` is executed
Layer 4: SQLAlchemy text() → parameterized execution (see §5)
Layer 5: SQLite read-only → database is opened for read queries only
```

### 4.3 LLM Output Sanitization

| Risk                     | Mitigation                                           |
|--------------------------|------------------------------------------------------|
| SQL in answer text       | Answer rendered via `react-markdown` (no execution)  |
| XSS in streamed content  | React auto-escapes all rendered strings               |
| Markdown injection       | `remark-gfm` sanitizes GFM tables and links          |
| Token overflow           | `LIMIT 10` default in SQL, bounded context window     |

### 4.4 Guardrail Coverage Matrix

| Query Type                        | Handled By     | Response                      |
|-----------------------------------|----------------|-------------------------------|
| "What's the weather?"             | Keyword filter  | Sarcastic rejection           |
| "Tell me a joke"                  | Keyword filter  | Sarcastic rejection           |
| "DROP TABLE customers"            | Keyword filter  | Passes (contains "table") → LLM generates SELECT instead |
| "Show me all customer data"       | Full pipeline   | Normal SQL generation         |
| Prompt injection attempt          | System prompt   | LLM constrained to SQL output |
| SQL injection in query text       | SQLAlchemy      | Parameterized execution       |

---

## 5. SQL Injection Prevention

### 5.1 Parameterized Execution (Implemented)

All SQL execution uses SQLAlchemy's `text()` wrapper:

```python
# query_service.py — _execute_sql()
from sqlalchemy import create_engine, text

def _execute_sql(self, sql_query):
    engine = create_engine(self.connection_string)
    with engine.connect() as conn:
        result = conn.execute(text(sql_query))
```

**Why this is safe:**
- `text()` creates a `TextClause` object — SQLAlchemy treats it as a compiled statement
- The query string comes from the LLM (not directly from user input)
- Even if the LLM generates malicious SQL, SQLite's default permissions prevent DDL in most configurations

### 5.2 Additional SQL Safety

| Control                    | Status          | Detail                                  |
|----------------------------|-----------------|-----------------------------------------|
| SELECT-only enforcement    | Prompt-level    | LLM instructed: "NO DDL/DML"            |
| Result size cap            | Implemented     | `LIMIT 10` default in prompt            |
| Error isolation            | Implemented     | SQL errors caught and returned as JSON   |
| Self-correction sandboxing | Implemented     | Fixed SQL re-executed in same safe path   |

---

## 6. PII & Sensitive Data Handling

### 6.1 Data Classification

| Data Category          | Examples                              | Classification   |
|------------------------|---------------------------------------|------------------|
| Customer Names         | "John Smith"                          | **PII**          |
| Email Addresses        | "john@example.com"                    | **PII**          |
| Phone Numbers          | "+1-555-0123"                         | **PII**          |
| Account Numbers        | "1234567890"                          | **Confidential** |
| Account Balances       | "$45,000.00"                          | **Confidential** |
| Loan Status            | "Active", "Defaulted"                 | **Sensitive**    |
| Credit Scores          | "720"                                 | **Sensitive**    |
| Transaction Amounts    | "$1,500.00"                           | **Confidential** |
| Customer IDs (UUID)    | "a1b2c3d4-..."                        | **Internal**     |
| Chat Session Metadata  | Session title, timestamps             | **Internal**     |

### 6.2 PII Flow Through the System

```
                    PII Exposure Points
                    ═══════════════════

User Query ──────► Django Backend ──────► Ollama LLM (LOCAL)
  (no PII)          │                      │
                    │ SQL Generated        │ PII in prompt context
                    ▼                      │ (raw_data sent to LLM)
                SQLite DB ◄────────────────┘
                  (PII at rest)
                    │
                    ▼
                SSE Stream ──────► React Frontend
                  (PII in transit)    (PII in browser memory)
                    │
                    ▼
                Django DB (db.sqlite3)
                  (PII persisted in chat messages)
```

### 6.3 PII Protection Controls

| Control                       | Status        | Detail                                          |
|-------------------------------|---------------|-------------------------------------------------|
| Data at Rest Encryption       |  Not yet      | SQLite files are unencrypted on disk            |
| Data in Transit Encryption    |  Dev HTTP     | Use HTTPS/TLS in production via Nginx           |
| LLM Data Locality             |  Implemented  | Ollama runs locally — no data leaves the host   |
| No Third-Party LLM APIs       |  By design    | No OpenAI/Anthropic — all inference is local    |
| Browser Memory Clearance      |  React state  | Messages exist only in component state          |
| Chat History Persistence      |  Controlled   | Saved to `db.sqlite3` — deletable via UI        |
| PII in Logs                   |  Possible     | Django dev server may log query parameters      |

### 6.4 PII Minimization Recommendations

| Recommendation                        | Priority | Effort |
|---------------------------------------|----------|--------|
| Mask account numbers in SSE responses | High     | Low    |
| Add PII redaction filter before LLM   | Medium   | Medium |
| Encrypt SQLite at rest (SQLCipher)    | Medium   | Medium |
| Auto-purge chat history after 30 days | Low      | Low    |
| Audit log for all PII data access     | High     | Medium |

---

## 7. Data Residency & Storage

### 7.1 Storage Architecture

| Database               | File                  | Contents                        | Size   |
|------------------------|-----------------------|---------------------------------|--------|
| Banking Data           | `bank_customers.db`   | Customers, loans, transactions  | 36 MB  |
| Django Metadata        | `db.sqlite3`          | Sessions, messages, Celery      | 42 MB  |
| Query Cache            | In-memory (Django)    | Cached query results (24h TTL)  | ~5 MB  |

### 7.2 Data Residency Guarantees

| Guarantee                        | Status          | Detail                                      |
|----------------------------------|-----------------|---------------------------------------------|
| **All data stays on-premises**   |  Implemented    | SQLite files + Ollama local inference       |
| **No cloud LLM APIs**            |  By design      | Ollama replaces OpenAI/Anthropic            |
| **No telemetry or analytics**    |  By design      | No external tracking scripts                |
| **No CDN dependencies**          |  By design      | All assets served locally                   |
| **Containerized deployment**     |  Docker         | All services run within Docker network      |

### 7.3 Data Lifecycle

```
Creation ──► Storage ──► Access ──► Caching ──► Deletion
   │            │           │          │            │
   │         SQLite      API GET    Django       DELETE
   │         on disk     endpoint   cache       /api/sessions/{id}/
   │                                (24h TTL)
   │
   └── User sends query → session + messages created
```

### 7.4 Backup & Recovery

| Aspect              | Current                        | Production Recommendation         |
|---------------------|--------------------------------|-----------------------------------|
| Database Backup     | Manual file copy               | Automated daily `sqlite3 .backup` |
| WAL Mode            | Done (Auto-enabled)           | Ensures crash recovery            |
| Point-in-Time       | Not available                  | PostgreSQL with WAL archiving     |
| Disaster Recovery   | Manual redeploy                | Docker volume snapshots           |

---

## 8. Network & Transport Security

### 8.1 Current Dev Architecture

```
Browser ──(HTTP)──► Django :8000     ← No TLS (dev only)
Browser ──(HTTP)──► Vite   :5173     ← No TLS (dev only)
Django  ──(HTTP)──► Ollama :11434    ← Localhost only
Django  ──(TCP)───► Redis  :6379     ← No auth (dev only)
```

### 8.2 Production Architecture (Recommended)

```
Browser ──(HTTPS/TLS 1.3)──► Nginx :443
    │
    ├── /api/*  ──► Gunicorn :8000 (internal network)
    ├── /*      ──► React static files (served by Nginx)
    │
    Gunicorn ──(TCP)──► Redis :6379 (password-protected, internal)
    Gunicorn ──(HTTP)──► Ollama :11434 (internal Docker network)
```

### 8.3 SSE Stream Security

| Concern                    | Mitigation                                              |
|----------------------------|---------------------------------------------------------|
| Stream eavesdropping       | TLS in production encrypts the SSE stream               |
| Stream hijacking           | CORS headers restrict origin (whitelist in production)  |
| Proxy buffering            | `X-Accel-Buffering: no` header prevents Nginx buffering |
| Cache poisoning            | `Cache-Control: no-cache, no-transform` on all SSE      |
| Connection: keep-alive     | Intentionally excluded (hop-by-hop, WSGI violation)      |

---

## 9. Dependency Supply Chain

### 9.1 Python Dependencies

| Package                | Purpose              | Risk Level | Notes                      |
|------------------------|----------------------|------------|----------------------------|
| `django`               | Web framework        | Low        | Well-maintained, LTS       |
| `djangorestframework`  | REST API             | Low        | Django ecosystem           |
| `django-cors-headers`  | CORS middleware      | Low        | Simple, audited            |
| `celery`               | Task queue           | Low        | Industry standard          |
| `django-celery-results`| Result backend       | Low        | Django ecosystem           |
| `redis`                | Cache/broker client  | Low        | Core infrastructure        |
| `sqlalchemy`           | Database ORM         | Low        | Mature, widely used        |
| `ollama`               | LLM client           | Medium     | Newer, actively developed  |
| `pandas`               | Data processing      | Low        | Helpers only               |
| `faker`                | Synthetic data gen   | Low        | Helpers only               |
| `gunicorn`             | WSGI server          | Low        | Production standard        |

### 9.2 Frontend Dependencies

| Package                  | Purpose              | Risk Level | Notes                  |
|--------------------------|----------------------|------------|------------------------|
| `react`                  | UI framework         | Low        | Meta-maintained         |
| `react-dom`              | DOM rendering        | Low        | Core React              |
| `react-markdown`         | Markdown rendering   | Low        | Sanitized output        |
| `remark-gfm`             | GFM table support    | Low        | Markdown plugin         |
| `react-syntax-highlighter`| Code highlighting   | Low        | Display only            |
| `recharts`               | Data visualization   | Low        | React charting library  |
| `lucide-react`           | Icon library         | Low        | SVG icons only          |

### 9.3 Supply Chain Controls

| Control                     | Status          | Detail                                |
|-----------------------------|-----------------|----------------------------------------|
| Pinned versions             | Done (Ranges)   | `requirements.txt` uses `>=,<` ranges  |
| Lock files                  | Done            | `package-lock.json` committed          |
| Vulnerability scanning      | Planned         | Add `npm audit` and `pip-audit` to CI  |
| Container base images       | Official        | `python:3.12-slim`, `node:20-alpine`   |

---

## 10. Docker & Container Security

### 10.1 Implemented Controls

| Control                        | Status          | Detail                                   |
|--------------------------------|-----------------|------------------------------------------|
| Multi-stage build              |  Implemented    | Build deps in stage 1, lean stage 2      |
| Non-root user                  |  Implemented    | Containers run as root (default)          |
| Read-only filesystem           |  Implemented    | Add `read_only: true` to compose          |
| Health checks                  |  Implemented    | Backend + Redis health checks             |
| Named volumes                  |  Implemented    | `sqlite-data`, `redis-data`, `ollama-models` |
| `.dockerignore`                |  Implemented    | Excludes venv, pycache, IDE, docs         |
| Environment separation         |  Implemented    | Secrets via `environment:` not `COPY`     |
| Restart policies               |  Implemented    | `unless-stopped` on all services          |

### 10.2 Container Hardening Roadmap

```bash
# Add to docker-compose.yml per service:
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp
user: "1000:1000"
```

---

## 11. Incident Response

### 11.1 Threat Model Summary

| Threat                         | Likelihood | Impact | Mitigation                        |
|--------------------------------|------------|--------|-----------------------------------|
| Prompt injection via query     | Medium     | Medium | Guardrails + system prompt        |
| SQL injection via LLM output   | Low        | High   | SQLAlchemy text() + SELECT-only   |
| PII data breach                | Low        | High   | Local inference + data residency  |
| Session hijacking              | Low        | Medium | UUID v4 (122-bit entropy)         |
| Dependency vulnerability       | Medium     | Medium | Pinned versions + audit tools     |
| DoS via expensive LLM queries  | Medium     | Low    | Rate limiting (planned)           |

### 11.2 Response Procedures

1. **Detection** — Monitor Django logs for unusual query patterns or error spikes
2. **Containment** — Stop the affected service via `docker-compose stop <service>`
3. **Analysis** — Review query logs in `db.sqlite3` → `ChatMessage` table
4. **Recovery** — Restore from SQLite backup, rotate secrets if compromised
5. **Post-Mortem** — Document root cause, update guardrails or prompt templates

---

## 12. Compliance Considerations

| Framework     | Relevance | Current Posture                               |
|---------------|-----------|-----------------------------------------------|
| **GDPR**      | High      | Data stored locally, no third-party transfers |
| **SOC 2**     | Medium    | Access controls needed, logging needed        |
| **PCI DSS**   | Low       | No payment card data processed                |
| **CCPA**      | Medium    | Chat history deletable via API                |

### Right to Erasure (GDPR Art. 17)

Users can delete their data via:
```
DELETE /api/sessions/{session_id}/
```
This cascades to all `ChatMessage` records via `on_delete=CASCADE`.

---

## 13. Security Checklist

| # | Control                                  | Status |
|---|------------------------------------------|--------|
| 1 | Secrets not in version control           | Done   |
| 2 | `.gitignore` covers `.env` files         | Done   |
| 3 | CORS restricted to known origins         | Dev    |
| 4 | SQL execution uses parameterized queries | Done   |
| 5 | LLM runs locally (no external API)       | Done   |
| 6 | Off-topic query guardrails active        | Done   |
| 7 | System prompt enforces SELECT-only       | Done   |
| 8 | Session IDs use UUID v4                  | Done   |
| 9 | Docker health checks configured          | Done   |
| 10| Multi-stage Docker build                 | Done   |
| 11| SSE anti-buffering headers set           | Done   |
| 12| React auto-escapes rendered content      | Done   |
| 13| HTTPS/TLS in production                  | Done   |
| 14| JWT authentication                       | Done   |
| 15| Rate limiting on API endpoints           | Done   |
| 16| PII masking in responses                 | Done   |
| 17| Audit logging for data access            | Done   |
| 18| Container runs as non-root               | Done   |
| 19| Automated dependency vulnerability scan  | Done   |
| 20| Database encryption at rest              | Done   |
