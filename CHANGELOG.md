# Changelog — FinQuery AI

All notable changes to this project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-16

### Added
- **Core SQL-RAG Pipeline**: Implemented 6-stage pipeline (Guardrails, Schema Extraction, Text-to-SQL, Execution, Synthesis, Persistence).
- **Streaming Experience**: Token-by-token streaming for both thought process (CoT) and final financial synthesis via SSE.
- **Enterprise Security**:
    - JWT-based Authentication with Login/Register endpoints.
    - CORS whitelisting support.
    - Deterministic keyword-based guardrails.
    - Restricted SQL engine (SELECT-only).
- **Interactive UI**:
    - React-based dashboard with dynamic theme/accent/font customizer.
    - Live Analytics dashboard with KPI cards and portfolio lists.
    - Integrated Recharts for instant data visualization from SQL results.
- **Project Documentation**: Comprehensive ARCHITECTURE.md, SECURITY.md, and RAI.md files.
- **Docker Orchestration**: Full-stack multi-container setup (Backend, Frontend, Redis, Celery, Ollama).

### Changed
- Refactored LLM synthesis to stream tokens instead of buffering, reducing perceived latency.
- Migrated from anonymous sessions to user-isolated persistent storage.
- Improved sidebar navigation with categorized chat history (Today, This Week, Older).

### Fixed
- Fixed SSE buffering issues in Django backend.
- Resolved SQL extraction edge cases where markdown blocks were improperly parsed.
- Corrected database persistence for guardrail-triggered messages.

---

## [0.1.0] - 2026-03-11
### Added
- Initial POC with simple natural language to SQL conversion.
- Basic React frontend with chat bubbles.
- SQLite backend for banking data demo.
