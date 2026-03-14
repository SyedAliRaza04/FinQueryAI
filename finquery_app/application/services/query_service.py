import json
import re
import os
import random
from sqlalchemy import create_engine, text
from finquery_app.infrastructure.llm.ollama_client import OllamaClient
from finquery_app.infrastructure.repositories.schema_repository import SchemaRepository
from django.conf import settings


# ─── Guardrail keyword sets ────────────────────────────────────────────────────
# Fast, zero-latency check before hitting the LLM for query relevance.
FINANCIAL_KEYWORDS = {
    # Tables / entities
    "customer", "customers", "loan", "loans", "transaction", "transactions",
    "investment", "investments", "account", "accounts", "balance", "portfolio",
    # Financial concepts
    "credit", "debit", "interest", "rate", "risk", "default", "debt",
    "payment", "deposit", "withdrawal", "transfer", "revenue", "profit",
    "loss", "asset", "liability", "equity", "income", "expense",
    # Actions
    "show", "list", "get", "fetch", "find", "query", "summarize", "analyse",
    "analyze", "report", "top", "total", "average", "count", "sum",
    # DB terms
    "table", "database", "sql", "select", "where", "join", "record", "data",
    # Finance-adjacent
    "bank", "banking", "financial", "finance", "fiscal", "monetary",
    "amount", "value", "score", "status", "active", "overdue",
}

SARCASTIC_RESPONSES = [
    "📊 Ah, asking me about **{topic}**? Bold move. I'm a **financial data analyst** — "
    "I live in spreadsheets, not {domain}. Try asking me something actually useful, "
    "like *'What's the total outstanding loan balance?'*",

    "🏦 Fascinating question about **{topic}**. Unfortunately, my entire existence is dedicated "
    "to querying financial databases, not answering {domain} questions. "
    "I'd redirect you to Google, but I'm busy being a *Senior Financial AI*.",

    "💼 Dear user, I appreciate the creativity, but asking me about **{topic}** is like "
    "asking your accountant for relationship advice. I only speak the language of **SQL** "
    "and **financial data**. Want to ask about loans or customer balances instead?",

    "📈 My financial analyst brain just tried to find **{topic}** in the database... "
    "shockingly, it's not there. I'm strictly a **finance & database** assistant. "
    "Try something like *'Show me the top 10 customers by balance'*.",

    "🤓 Interesting. I ran a query for **{topic}** in our financial database and got: "
    "`ERROR: Table 'not_my_job' does not exist`. Stick to financial queries and we'll get along great.",
]

def _is_financial_query(query: str) -> tuple[bool, str]:
    """
    Fast keyword-based relevance check.
    Returns (is_relevant, detected_topic).
    """
    words = re.findall(r'\b\w+\b', query.lower())
    word_set = set(words)
    if word_set & FINANCIAL_KEYWORDS:
        return True, ""

    # Detect off-topic domains for sarcasm
    off_topic_map = {
        "weather": "weather",
        "recipe": "cooking", "cook": "cooking", "food": "cooking",
        "sport": "sports", "football": "sports", "soccer": "sports",
        "movie": "entertainment", "film": "entertainment",
        "music": "music", "song": "music",
        "health": "medicine", "doctor": "medicine",
        "joke": "comedy", "funny": "comedy",
        "politic": "politics",
        "game": "gaming",
        "travel": "travel",
    }
    detected_topic = query.strip()[:40]
    for kw, domain in off_topic_map.items():
        if kw in " ".join(words):
            return False, domain

    return False, "general topics"


class FinQueryService:
    """
    Core service orchestrating the full SQL-RAG pipeline:
    1. Guardrail check (instant keyword filter)
    2. Schema extraction
    3. Text-to-SQL generation (streamed as CoT)
    4. SQL execution with self-correction
    5. Synthesis (silent buffer → clean split → single token emit)
    6. Cache + persist
    """

    def __init__(self):
        base_dir = settings.BASE_DIR
        self.db_path = os.path.join(base_dir, "bank_customers.db")
        self.connection_string = f"sqlite:///{self.db_path}"
        self.llm_client = OllamaClient()
        self.schema_repository = SchemaRepository(self.connection_string)

    def get_schema_context(self) -> str:
        """Extract minimal DDL schema — reduces LLM context size and improves accuracy."""
        return self.schema_repository.extract_ddl_schema()

    def process_query_stream(self, user_query, cache_key=None, session=None):
        """
        Full SSE streaming pipeline. Yields SSE-formatted strings.

        Event types emitted:
          status          → informational label (UI toast, ignored visually)
          reasoning_token → CoT thinking (SQL generation phase)
          sql             → extracted clean SQL query for the code block
          raw_data        → JSON list of query results
          reasoning_done  → seals CoT box with final CoT-only text
          token           → the complete financial analysis answer (single event)
          done            → signals stream completion

        IMPORTANT: The answer is sent as ONE `token` event (not a loop of chunks).
        Sending chunks in a tight for-loop with no I/O between yields causes WSGI
        to buffer all events and deliver them together at generator exhaustion,
        which means nothing appears until the stream is fully complete.
        """

        # ── 0. Guardrail Check (instant, no LLM needed) ───────────────────────
        is_relevant, off_topic_domain = _is_financial_query(user_query)
        if not is_relevant:
            # Detect topic for personalised sarcasm
            topic = user_query.strip()[:40]
            sarcastic = random.choice(SARCASTIC_RESPONSES).format(
                topic=topic, domain=off_topic_domain
            )
            yield f"data: {json.dumps({'type': 'reasoning_done', 'content': ''})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'content': sarcastic})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # ── 1. Schema Extraction ───────────────────────────────────────────────
        schema_context = self.get_schema_context()
        yield f"data: {json.dumps({'type': 'status', 'content': 'Reading schema...'})}\n\n"

        # ── 2. Text-to-SQL (streamed as CoT reasoning) ────────────────────────
        # Each token from Ollama has real I/O between yields, so these stream
        # correctly without WSGI buffering.
        sql_query_full = ""
        yield f"data: {json.dumps({'type': 'status', 'content': 'Generating SQL...'})}\n\n"
        for token in self.llm_client.generate_sql_stream(user_query, schema_context):
            sql_query_full += token
            yield f"data: {json.dumps({'type': 'reasoning_token', 'content': token})}\n\n"

        sql_query, _ = self.llm_client._parse_sql_response(sql_query_full)
        yield f"data: {json.dumps({'type': 'sql', 'content': sql_query})}\n\n"

        # ── 3. SQL Execution with Self-Correction ─────────────────────────────
        yield f"data: {json.dumps({'type': 'status', 'content': 'Executing query...'})}\n\n"
        raw_data = self._execute_sql(sql_query)

        if isinstance(raw_data, dict) and "error" in raw_data:
            # Show error in CoT, attempt silent self-correction
            sql_err_msg = raw_data["error"]
            cot_err = f"\n\n⚠️ SQL Error detected: {sql_err_msg}\nApplying self-correction..."
            yield f"data: {json.dumps({'type': 'reasoning_token', 'content': cot_err})}\n\n"

            fix_prompt = (
                "ROLE\nYou are a SQL Fixer.\n"
                f"TASK\nFix the broken SQL for this user question: {user_query}\n"
                f"SCHEMA\n{schema_context}\n"
                f"BROKEN SQL\n{sql_query}\n"
                f"ERROR\n{sql_err_msg}\n"
                "OUTPUT: Only output the corrected SQL in a ```sql``` code block."
            )
            fixed_sql_full = ""
            for token in self.llm_client._call_llm_stream([
                {'role': 'system', 'content': fix_prompt},
                {'role': 'user', 'content': "Fix this SQL."}
            ]):
                fixed_sql_full += token
                yield f"data: {json.dumps({'type': 'reasoning_token', 'content': token})}\n\n"

            fixed_sql, _ = self.llm_client._parse_sql_response(fixed_sql_full)
            fixed_raw_data = self._execute_sql(fixed_sql)

            if not (isinstance(fixed_raw_data, dict) and "error" in fixed_raw_data):
                sql_query = fixed_sql
                raw_data = fixed_raw_data
                yield f"data: {json.dumps({'type': 'sql', 'content': sql_query})}\n\n"

        yield f"data: {json.dumps({'type': 'raw_data', 'content': raw_data})}\n\n"

        # ── 4. Synthesis — Silent Buffer + Clean Split ────────────────────────
        # We collect the entire synthesis silently (no token streaming to UI).
        # Then we split the CoT from the answer using regex, and emit:
        #   - reasoning_done  → seals the CoT box with clean CoT-only text
        #   - token           → the COMPLETE answer as a SINGLE event
        #
        # CRITICAL: Do NOT use a `for i in range(0, len(text), chunk)` loop here.
        # That tight loop has no I/O between yields, so WSGI buffers ALL events
        # and the frontend receives nothing until the generator is exhausted.
        # Sending ONE token event avoids all buffering entirely.
        yield f"data: {json.dumps({'type': 'status', 'content': 'Analysing results...'})}\n\n"

        synthesis_full = ""
        for token in self.llm_client.synthesize_results_stream(user_query, sql_query, raw_data):
            synthesis_full += token
        # ↑ No yields inside — synthesis collected silently

        # Regex-split: CoT before the answer start marker, answer from marker onward
        answer_text = synthesis_full
        cot_text = ""

        split_markers = [
            r'(\*\*Executive Summary\*\*)',
            r'(Executive Summary:?)',
            r'(\*\*Summary\*\*)',
            r'(## Summary)',
            r'(## Analysis)',
            r'(## Financial Brief)',
        ]
        for marker in split_markers:
            match = re.search(marker, synthesis_full, re.IGNORECASE)
            if match:
                split_idx = match.start()
                cot_text = synthesis_full[:split_idx].strip()
                answer_text = synthesis_full[split_idx:].strip()
                break

        # Seal CoT box with only the thinking portion
        yield f"data: {json.dumps({'type': 'reasoning_done', 'content': cot_text})}\n\n"

        # Send the complete answer as a SINGLE token event.
        # This is the critical fix: one yield = one flush = immediate browser receipt.
        yield f"data: {json.dumps({'type': 'token', 'content': answer_text})}\n\n"

        # ── 5. Cache & Persist ────────────────────────────────────────────────
        if cache_key:
            from django.core.cache import cache
            cache.set(cache_key, {
                'sql_query': sql_query,
                'raw_data': raw_data,
                'summary': answer_text
            }, timeout=3600 * 24)

        if session:
            from finquery_app.models import ChatMessage
            ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=answer_text,
                code_snippet=sql_query,
                raw_data_json=raw_data
            )

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    def process_query(self, user_query):
        """Non-streaming query execution (used by Celery task)."""
        schema_context = self.get_schema_context()
        sql_query, reasoning = self.llm_client.generate_sql(user_query, schema_context)
        raw_data = self._execute_sql(sql_query)

        if isinstance(raw_data, dict) and "error" in raw_data:
            print(f"Initial SQL failed: {raw_data['error']}. Attempting fix...")
            fixed_sql, fixed_reasoning = self.llm_client.fix_sql(
                user_query, sql_query, raw_data["error"], schema_context
            )
            fixed_raw_data = self._execute_sql(fixed_sql)
            if not (isinstance(fixed_raw_data, dict) and "error" in fixed_raw_data):
                sql_query = fixed_sql
                reasoning = reasoning + "\n\n[Correction]: " + fixed_reasoning
                raw_data = fixed_raw_data
            else:
                raw_data["error"] += f" | Fix Attempt Failed: {fixed_raw_data.get('error')}"

        summary = self.llm_client.synthesize_results(user_query, sql_query, raw_data)
        return {
            "user_query": user_query,
            "generated_sql": sql_query,
            "reasoning": reasoning,
            "raw_data": raw_data,
            "summary": summary
        }

    def _execute_sql(self, sql_query):
        """Execute SQL and return list of row dicts, or error dict on failure."""
        engine = create_engine(self.connection_string)
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql_query))
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            return {"error": f"SQL Execution Failed: {str(e)}"}
