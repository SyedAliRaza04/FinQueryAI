from sqlalchemy import create_engine, text
from finquery_app.infrastructure.llm.ollama_client import OllamaClient
from finquery_app.infrastructure.repositories.schema_repository import SchemaRepository
from django.conf import settings
from django.core.cache import cache
from finquery_app.models import ChatSession
import os
import sqlite3
import re
import json
import random


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
            
            if session:
                try:
                    from finquery_app.models import ChatMessage
                    ChatMessage.objects.create(
                        session=session,
                        role='assistant',
                        content=sarcastic
                    )
                except Exception:
                    pass

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

        # ── 4. Synthesis — Streaming Answer with Marker Detection ─────────────
        # We stream tokens. Initially sent as 'reasoning_token'.
        # Once we detect a split marker, we switch to 'token'.
        yield f"data: {json.dumps({'type': 'status', 'content': 'Analysing results...'})}\n\n"

        synthesis_full = ""
        has_switched_to_answer = False
        
        # We need a small buffer to detect split markers effectively
        split_markers = [
            "Executive Summary",
            "**Executive Summary**",
            "Summary:",
            "**Summary**",
            "## Summary",
            "## Analysis",
            "## Financial Brief"
        ]

        for token in self.llm_client.synthesize_results_stream(user_query, sql_query, raw_data):
            synthesis_full += token
            
            if not has_switched_to_answer:
                # Check for markers in the last chunk of text
                # We check a window to catch markers like "Executive Summary" that might be split across tokens
                lookback = synthesis_full[-50:] 
                marker_found = False
                for marker in split_markers:
                    if marker in lookback:
                        marker_found = True
                        break
                
                if marker_found:
                    has_switched_to_answer = True
                    # Split at the first occurrence of any marker
                    # We might have some reasoning before the marker
                    # Find where the marker starts in the full text
                    marker_idx = len(synthesis_full)
                    for marker in split_markers:
                        idx = synthesis_full.find(marker)
                        if idx != -1 and idx < marker_idx:
                            marker_idx = idx
                    
                    cot_text = synthesis_full[:marker_idx].strip()
                    answer_start = synthesis_full[marker_idx:]
                    
                    # Seal the reasoning box with whatever we collected before the marker
                    yield f"data: {json.dumps({'type': 'reasoning_done', 'content': cot_text})}\n\n"
                    # Start the answer stream with the marker itself
                    if answer_start:
                        yield f"data: {json.dumps({'type': 'token', 'content': answer_start})}\n\n"
                else:
                    # Still reasoning — emit token
                    yield f"data: {json.dumps({'type': 'reasoning_token', 'content': token})}\n\n"
            else:
                # Already in answer mode — emit directly
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # Final cleanup for persistence
        # If we never found a marker, use the whole thing as answer
        if not has_switched_to_answer:
            answer_text = synthesis_full
            yield f"data: {json.dumps({'type': 'reasoning_done', 'content': ''})}\n\n"
            # We don't yield token here because they were all yielded as reasoning_tokens above
            # But the UI will look weird (empty answer bubble). Usually LLM follows instructions.
        else:
            # answer_text for saving
            answer_text = synthesis_full # We split it logically for display, but save the full synthesis or a parsed version?
            # Re-parse correctly for saving
            for marker in split_markers:
                match = re.search(re.escape(marker), synthesis_full, re.IGNORECASE)
                if match:
                    answer_text = synthesis_full[match.start():].strip()
                    break

        # ── 5. Cache & Persist ────────────────────────────────────────────────
        if cache_key:
            from django.core.cache import cache
            cache.set(cache_key, {
                'sql_query': sql_query,
                'raw_data': raw_data,
                'summary': answer_text
            }, timeout=3600 * 24)

        if session:
            try:
                from finquery_app.models import ChatMessage
                print(f"DEBUG: Attempting to save assistant message for session {session.id}")
                ChatMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=answer_text,
                    code_snippet=sql_query,
                    raw_data_json=raw_data
                )
                print(f"DEBUG: Successfully saved assistant message for session {session.id}")
            except Exception as e:
                print(f"DEBUG ERROR: Failed to save assistant message: {e}")

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
