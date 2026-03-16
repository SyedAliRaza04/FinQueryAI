# Responsible & Frugal AI (RAI) Policy — FinQuery AI

FinQuery AI is built with a commitment to privacy-preserving, cost-effective, and robust AI engineering. This document outlines the technical choices made to ensure the system is responsible (safe/private) and frugal (efficient/low-cost).

---

## 1. Responsible AI Principles

### 1.1 Privacy by Design (Data Residency)
- **Local Inference**: FinQuery uses **Ollama** for all LLM operations. No financial data, schemas, or user queries ever leave the local environment or are transmitted to third-party cloud LLM providers (OpenAI, Anthropic, etc.).
- **On-Premises Storage**: Banking data is stored in localized SQLite databases, ensuring the data remains within the enterprise boundary.

### 1.2 Multi-Layered Safety Guardrails
- **Stage 0 Keyword Filter**: A deterministic, zero-token cost guardrail intercepts queries. If a query does not contain financial or database-relevant keywords, it is rejected before reaching the LLM.
- **SELECT-Only Enforcement**: The system prompt and SQL parsing logic strictly enforce read-only operations. The engine rejects DML (INSERT/UPDATE/DELETE) and DDL tokens.
- **Tone Control**: The system is programmed to maintain a professional, senior financial analyst persona, avoiding conversational drift or inappropriate responses.

### 1.3 Auditability
- **Reasoning Transparency**: Every answer includes a "Thought Process" (Chain-of-Thought) section, showing the executive how the AI interpreted the query and arrived at the SQL.
- **SQL Visibility**: The generated SQL is displayed alongside the data, allowing human-in-the-loop verification of the query logic.

---

## 2. Frugal AI Principles

FinQuery is optimized to run on standard hardware with minimal operational expenditure (OpEx).

### 2.1 Cost Optimization (Zero API Fees)
- **Open Source Models**: By utilizing **Llama 3.1 (8B)** or similar quantized models, the system incurs zero per-token costs.
- **Local Infrastructure**: All processing happens on the host machine (Mac/Linux/Docker), eliminating the need for expensive cloud compute instances.

### 2.2 Latency and Throughput Efficiency
- **Deterministic Pre-Filtering**: The Stage 0 guardrail saves significant computation time and GPU cycles by rejecting off-topic queries instantly without calling the LLM.
- **Multi-Level Caching**:
    - **Query Cache**: Identical natural language queries are served from the Django/Redis cache within milliseconds.
    - **Embedding Caching**: (Planned) To reduce compute load for semantic retrieval.
- **Quantization**: We recommend using 4-bit or 8-bit quantized models to reduce memory footprint and increase inference speed.

### 2.3 Resource Stewardship
- **Small Context Windows**: Prompts are engineered to be concise, providing only necessary schema context to keep the token count (and memory pressure) low.
- **Batch Processing**: Non-interactive queries (Analytics) are handled via Celery workers to avoid blocking the main server thread.

---

## 3. Evaluation and Monitoring

### 3.1 Performance Metrics
| Metric | Target | Rationale |
|---|---|---|
| Latency (SQL Gen) | < 5s | Real-time interactivity |
| Latency (Synthesis) | < 8s | Comprehensive analysis speed |
| SQL Accuracy | > 95% | Critical for financial reliability |
| Token Usage | Minimal | Efficiency and context window management |

### 3.2 Continuous Improvement
- **Feedback Loop**: Users can "Retry" or "Visualize" data, providing implicit signals for query refinement.
- **Self-Correction**: The Stage 3 SQL Execution layer includes an automated "Retrying/Fixing" logic to handle minor syntax errors without manual intervention.
