<p align="center">
  <h1 align="center">🤖 FinQuery AI</h1>
  <p align="center">
    <strong>Natural Language → SQL → Financial Insights</strong><br/>
    An AI-powered financial analyst that converts plain English questions into SQL queries,
    executes them against a banking database, and delivers professional-grade financial briefs.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-6.0-green?logo=django" alt="Django"/>
  <img src="https://img.shields.io/badge/React-19-blue?logo=react" alt="React"/>
  <img src="https://img.shields.io/badge/LLM-Llama_3.1-orange?logo=meta" alt="LLM"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License"/>
</p>

---

## ✨ Key Features

- **Natural Language SQL** — Ask questions in plain English; the AI generates, executes, and explains SQL
- **Real-Time Streaming** — Server-Sent Events (SSE) stream the thinking process and answer live
- **Smart Guardrails** — Off-topic queries get a sarcastic rejection without wasting LLM tokens
- **SQL Self-Correction** — If a generated query fails, the LLM automatically fixes and retries it
- **Data Visualization** — One-click bar charts via Recharts for any query result
- **Analytics Dashboard** — Live KPIs (total assets, customers, loans, transactions) from the DB
- **Theme Engine** — Dark / Light / Midnight modes with 4 accent colors and font size control
- **Session Management** — Full chat history with create, select, delete, and export (.txt)
- **Query Caching** — Repeated queries return instantly from the Django cache (24h TTL)

---

## 🏗️ Tech Stack

| Layer        | Technology                                 |
|--------------|--------------------------------------------|
| **Frontend** | React 19, Vite 8, Recharts, react-markdown |
| **Backend**  | Django 6, Django REST Framework             |
| **LLM**      | Ollama (Llama 3.1, local inference)         |
| **Database** | SQLite (banking data + Django metadata)     |
| **Async**    | Celery (memory broker in dev, Redis in prod)|
| **Styling**  | Vanilla CSS with CSS variables              |

---

## 🚀 Quick Start

### Prerequisites

| Tool    | Version | Install                        |
|---------|---------|--------------------------------|
| Python  | 3.12+   | [python.org](https://python.org)|
| Node.js | 20+     | [nodejs.org](https://nodejs.org)|
| Ollama  | Latest  | [ollama.com](https://ollama.com)|

### 1. Clone & Setup Backend

```bash
# Clone the repository
git clone <repo-url>
cd finquery

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate     # macOS/Linux
# .venv\Scripts\activate      # Windows

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Start the backend server
python manage.py runserver 8000
```

### 2. Setup Frontend

```bash
# In a new terminal
cd frontend_react

# Install Node dependencies
npm install

# Start the dev server
npm run dev
```

### 3. Start Ollama

```bash
# In a third terminal — pull the model (first time only)
ollama pull llama3.1

# Ollama runs automatically after pull
# Verify it's running:
curl http://localhost:11434/api/tags
```

### 4. Open the App

Visit **http://localhost:5173** in your browser.

---

## 🐳 Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Services:
#   Backend  → http://localhost:8000
#   Frontend → http://localhost:5173
#   Redis    → localhost:6379
#   Ollama   → http://localhost:11434
```

> **Note:** Ensure Ollama is running on the host or add the ollama service
> to docker-compose. See `docker-compose.yml` for the full configuration.

---

## 📁 Project Structure

```
finquery/
├── config/                    # Django settings, URLs, Celery, WSGI
├── finquery_app/              # Main application
│   ├── application/services/  # Core SQL-RAG pipeline (query_service.py)
│   ├── infrastructure/        # Ollama client + schema repository
│   ├── interfaces/api/        # REST + SSE endpoints (views.py)
│   ├── models.py              # ChatSession, ChatMessage
│   ├── serializers.py         # DRF serializers
│   └── tasks.py               # Celery task definitions
├── frontend_react/            # React + Vite frontend
│   └── src/components/        # Sidebar, Chat, Analytics, Settings
├── helpers/                   # DB enrichment & cleanup scripts
├── Dockerfile                 # Backend container
├── docker-compose.yml         # Full stack orchestration
└── requirements.txt           # Python dependencies
```

For the complete low-level architecture, see [**ARCHITECTURE.md**](./ARCHITECTURE.md).

---

## 🔄 How It Works

```
1. User types a question in natural language
       │
2. Guardrail check → off-topic queries get a sarcastic response
       │
3. Schema extracted from SQLite via SQLAlchemy inspector
       │
4. LLM generates SQL with Chain-of-Thought reasoning (streamed live)
       │
5. SQL executed → if error, LLM auto-corrects and retries
       │
6. LLM synthesizes a financial analysis brief (Executive Summary)
       │
7. Results cached (24h) and saved to chat history
       │
8. Frontend renders: CoT bubble + markdown answer + SQL block + chart
```

---

## 🧪 API Reference

| Method | Endpoint                       | Description                    |
|--------|--------------------------------|--------------------------------|
| GET    | `/api/sessions/`               | List all chat sessions         |
| POST   | `/api/sessions/`               | Create a new session           |
| GET    | `/api/sessions/{id}/`          | Get session with messages      |
| DELETE | `/api/sessions/{id}/`          | Delete a session               |
| GET    | `/api/query/stream/?query=…`   | SSE streaming query endpoint   |
| POST   | `/api/query/execute/`          | Async query via Celery         |
| GET    | `/api/analytics/`              | Live dashboard KPIs            |

---

## ⚙️ Configuration

### Environment Variables

| Variable                | Default                        | Description              |
|-------------------------|--------------------------------|--------------------------|
| `DJANGO_SECRET_KEY`     | `django-insecure-test-key…`    | Django secret (change!)  |
| `DEBUG`                 | `True`                         | Debug mode               |
| `CELERY_BROKER_URL`     | `memory://`                    | Celery broker (use Redis)|
| `CELERY_RESULT_BACKEND` | `django-db`                    | Task result storage      |
| `OLLAMA_HOST`           | `http://localhost:11434`       | Ollama API endpoint      |

### Database

The app uses two SQLite databases:
- **`bank_customers.db`** — Core banking data (customers, loans, transactions, investments)
- **`db.sqlite3`** — Django metadata (chat sessions, messages, Celery results)

---

## 📊 Database Schema

The banking database contains these tables:

| Table                | Key Columns                                      |
|----------------------|--------------------------------------------------|
| `customers`          | customer_id, customer_name, age, balance, email   |
| `loans`              | loan_id, customer_id, amount, status, interest    |
| `transactions`       | tx_id, customer_id, amount, type, date            |
| `investment_accounts`| account_id, customer_id, balance, account_type    |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License. See `LICENSE` for details.

---

## 📚 Additional Documentation

- [**ARCHITECTURE.md**](./ARCHITECTURE.md) — Complete system architecture
- [**BUSINESS_FEATURES.md**](./BUSINESS_FEATURES.md) — All features and components
- [**research.md**](./research.md) — AI pipeline research notes
