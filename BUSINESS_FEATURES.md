# FinQuery AI — Business Features & Component Guide

> A complete reference of every user-facing feature, component, and capability.

---

## 1. Core AI Capabilities

### 1.1 Natural Language to SQL
| Feature | Description |
|---------|-------------|
| **Text-to-SQL** | Converts plain English questions into valid SQLite queries |
| **Chain-of-Thought** | Shows the AI's reasoning process in real-time (collapsible) |
| **SQL Self-Correction** | If generated SQL fails, the LLM auto-fixes and retries |
| **Professional Synthesis** | Results are interpreted as a Senior Financial Analyst brief |

### 1.2 Guardrails
| Feature | Description |
|---------|-------------|
| **Off-Topic Detection** | Keyword-based filter catches non-financial questions instantly |
| **Sarcastic Response** | 5 rotating witty responses redirect users to financial queries |
| **Zero LLM Cost** | Off-topic queries are blocked before reaching the LLM |

### 1.3 Query Caching
| Feature | Description |
|---------|-------------|
| **MD5-Based Cache** | Identical queries return cached results instantly |
| **24-Hour TTL** | Cache expires daily to ensure data freshness |
| **Cache-Hit Indicator** | UI shows "Cache hit!" status when serving cached results |

---

## 2. Chat Interface

### 2.1 Chat Feed (`ChatFeed.jsx`)
| Feature | Description |
|---------|-------------|
| **Streaming CoT** | Thinking process streams token-by-token in a collapsible bubble |
| **Auto-Collapse** | CoT bubble auto-collapses 600ms after reasoning completes |
| **Markdown Rendering** | Full GFM support: tables, code blocks, bold, lists, blockquotes |
| **Smart Auto-Scroll** | Only scrolls when user is near the bottom (prevents glitch) |
| **Typing Indicator** | Three-dot animation shown before any tokens arrive |
| **SQL Code Block** | Generated SQL displayed in a styled code block with copy button |
| **Data Visualization** | One-click bar chart rendering via Recharts |
| **Copy to Clipboard** | Copy answer text or SQL with checkmark confirmation |
| **Retry Button** | Re-submits the previous user query for a fresh response |

### 2.2 Input Box (`InputBox.jsx`)
| Feature | Description |
|---------|-------------|
| **Auto-Resize** | Textarea grows vertically as you type (up to 200px) |
| **Enter to Send** | Submit with Enter, new line with Shift+Enter |
| **Send Button** | Circular arrow button with active state highlighting |
| **Disabled During Processing** | Input and chips locked while AI is generating |

### 2.3 Smart Action Chips
| Chip | Icon | What It Does |
|------|------|--------------|
| **💡 Brainstorm** | Lightbulb | Full customer overview with loan status, balances, and distribution |
| **🗄️ Query DB** | Database | Top 10 records from customers, loans, and transactions tables |
| **📈 Risk Report** | TrendingUp | Delinquent/defaulted loans with risk exposure summary |
| **📋 Summarize** | FileText | Executive summary: total assets, customers, loans, KPIs |

### 2.4 Hero State (Empty Chat)
| Feature | Description |
|---------|-------------|
| **Welcome Message** | "FinQuery AI" branding with description |
| **Quick Start Chips** | 4 pre-built queries: Loan Overview, Top Customers, Credit Analysis, Risk Report |

---

## 3. Session Management

### 3.1 Sidebar (`Sidebar.jsx`)
| Feature | Description |
|---------|-------------|
| **New Chat** | Creates a fresh session and clears the chat |
| **Session History** | Lists all past conversations, grouped by date |
| **Date Grouping** | Today / This Week / Older |
| **Active Highlight** | Current session highlighted in the list |
| **Hover Delete** | Trash icon appears on hover to delete sessions |
| **Session Title** | Auto-generated from the first query (30 chars) |

### 3.2 Chat Persistence
| Feature | Description |
|---------|-------------|
| **Auto-Save** | Messages saved to DB after each query/response cycle |
| **Full History** | User + assistant messages with SQL, raw data, and reasoning |
| **Export** | Download conversation as a `.txt` file |
| **Refresh** | Reload session messages from the database |

---

## 4. Analytics Dashboard (`AnalyticsMain.jsx`)

### 4.1 KPI Cards
| Metric | Source | Icon |
|--------|--------|------|
| **Total Managed Assets** | `SUM(balance) FROM investment_accounts` | 💰 |
| **Active Customers** | `COUNT(*) FROM customers` | 👥 |
| **Active Loans** | `COUNT(*) FROM loans WHERE status='Active'` | 💼 |
| **Monthly Transacted** | `SUM(amount) FROM transactions` | 📊 |

### 4.2 Charts & Widgets
| Widget | Description |
|--------|-------------|
| **Transaction Volume** | CSS-animated bar chart (7 months) |
| **Top Portfolios** | List of top 4 investment accounts with name, type, amount, and RoR |
| **Live Update** | Refresh button re-fetches all metrics from the database |

---

## 5. Settings (`SettingsModal.jsx`)

### 5.1 Theme Control
| Setting | Options |
|---------|---------|
| **Theme** | Dark 🌙 / Light ☀️ / Midnight 🌌 |
| **Accent Color** | Emerald, Electric Blue, Violet, Gold |
| **Font Size** | Small (14px) / Medium (16px) / Large (18px) |

### 5.2 Backend Info
| Info | Value |
|------|-------|
| **Model** | Llama 3.1 (Ollama) |
| **Backend URL** | http://localhost:8000 |
| **Status** | 🟢 Connected |

### 5.3 Persistence
All settings saved to `localStorage` and restored on refresh:
- `fq-theme` → Theme selection
- `fq-accent` → Accent color
- `fq-fontsize` → Font size

---

## 6. Data Visualization (`DataChart.jsx`)

| Feature | Description |
|---------|-------------|
| **Auto Axis Detection** | Automatically finds string columns for X and numeric for Y |
| **Financial Formatting** | Y-axis formats as `$1.5M` or `2.3k` for large numbers |
| **Custom Tooltips** | Dark-themed tooltips with column name and formatted value |
| **Alternating Colors** | Green/teal alternating bar colors |
| **Responsive** | Fills container width, fixed 300px height |

---

## 7. Feature Matrix

| Category | Feature | Status |
|----------|---------|--------|
| **AI** | Text-to-SQL Generation | ✅ Live |
| **AI** | CoT Streaming | ✅ Live |
| **AI** | SQL Self-Correction | ✅ Live |
| **AI** | Financial Synthesis | ✅ Live |
| **AI** | Off-Topic Guardrails | ✅ Live |
| **AI** | Query Caching | ✅ Live |
| **UI** | Dark/Light/Midnight Themes | ✅ Live |
| **UI** | Accent Color Picker | ✅ Live |
| **UI** | Font Size Control | ✅ Live |
| **UI** | Markdown Table Rendering | ✅ Live |
| **UI** | Code Syntax Highlighting | ✅ Live |
| **UI** | Data Visualization (Charts) | ✅ Live |
| **UI** | Copy to Clipboard | ✅ Live |
| **UI** | Chat Export (.txt) | ✅ Live |
| **UX** | Smart Action Chips | ✅ Live |
| **UX** | Hero Quick-Start Chips | ✅ Live |
| **UX** | Auto-Scroll (glitch-free) | ✅ Live |
| **UX** | Session Management (CRUD) | ✅ Live |
| **Dashboard** | KPI Cards (live data) | ✅ Live |
| **Dashboard** | Transaction Volume Chart | ✅ Live |
| **Dashboard** | Top Portfolios Widget | ✅ Live |
| **DevOps** | Docker Compose | ✅ Ready |
| **DevOps** | Multi-Stage Dockerfile | ✅ Ready |
| **Auth** | JWT Authentication | 🔜 Planned |
| **Auth** | Multi-Tenant Isolation | 🔜 Planned |
| **Perf** | Redis Cache Backend | 🔜 Planned |
| **Perf** | Embedding Cache | 🔜 Planned |
| **ML** | RAG (Vector Search) | 🔜 Planned |
| **ML** | Batch Query Processing | 🔜 Planned |
