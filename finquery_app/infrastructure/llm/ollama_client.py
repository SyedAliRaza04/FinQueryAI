import json
try:
    from ollama import chat
except ImportError:
    chat = None

class OllamaClient:
    def __init__(self, model: str = "llama3.1"):
        self.model = model

    def generate_sql_stream(self, user_query: str, schema_context: dict):
        """
        Task 1: Text-to-SQL Generation (Streaming)
        """
        system_prompt = f"""
        ROLE
        You are the "FinQuery SQL Architect," an expert data engineer specializing in SQLite/PostgreSQL and financial datasets.
        
        TASK
        Convert the [USER_QUERY] into a single, valid SQLite SELECT statement based on the [SCHEMA_CONTEXT].
        
        SCHEMA_CONTEXT
        {schema_context}
        
        INSTRUCTIONS
        1. THINKING PROCESS: Before writing SQL, explicitly print "Thought: " followed by a brief 1-2 sentence explanation of your reasoning.
        2. IDENTIFY: Determine which tables and columns are needed.
        3. CHECK: Verify that EVERY column and table used exists in the SCHEMA_CONTEXT.
        4. DEFENSIVE SQL: Always use `COLLATE NOCASE` for string comparisons (e.g., `status = 'Active' COLLATE NOCASE`). Use `IFNULL()` to handle potential null values in calculations.
        5. GENERATE: Produce ONLY the SQL query in a markdown code block following your thought process.
        6. NO DDL/DML. Select limit 10 unless specified.
        
        OUTPUT FORMAT
        Thought: I need to ...
        ```sql
        SELECT ...
        ```
        """
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_query}
        ]
        
        return self._call_llm_stream(messages)

    def synthesize_results_stream(self, user_query: str, sql_query: str, raw_data: list):
        """
        Task 2: Data Synthesis (Streaming)
        """
        system_prompt = f"""
        ROLE
        You are a Senior Financial Analyst at a top-tier institution.
        
        TASK
        You have been handed the raw database results ([RAW_DATA]) resulting from executing the [EXECUTED_SQL] based on the executive's question: [USER_QUERY].
        Your job is to interpret this data and provide a highly professional, insightful financial brief.
        
        INPUTS
        User Query: {user_query}
        SQL Executed: {sql_query}
        Raw Data: {json.dumps(raw_data, indent=2)}
        
        INSTRUCTIONS
        1. THINKING PROCESS: First, print "Thought: " and briefly explain how you are going to analyze this data.
        2. ACT AGENTIC: Don't just regurgitate numbers. Interpret what the data means in a financial context. Point out interesting variances, totals, or trends if applicable.
        3. FORMATTING: Present your brief starting with an 'Executive Summary' sentence. Use bullet points for key insights.
        4. TABLES: Always neatly format the raw tabular data into a sleek Markdown table embedded within your response to visualize the exact dataset.
        5. PROFESSIONAL TONE: Use a highly professional, confident, and consultative tone. Avoid conversational filler like "Here is your summary".
        6. FALLBACK: If the data array is empty or contains an error, clearly state "No matching records found" or explain the error gracefully without breaking character.
        
        OUTPUT FORMAT
        Thought: I will analyze the ...
        
        Executive Summary...
        """
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': "Output the analysis."}
        ]
        
        return self._call_llm_stream(messages)

    def _call_llm_stream(self, messages: list):
        if chat:
            try:
                response = chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.0},
                    stream=True
                )
                for chunk in response:
                    if chunk and 'message' in chunk and 'content' in chunk['message']:
                        yield chunk['message']['content']
            except Exception as e:
                yield f"Error calling OLLAMA: {e}"
        else:
            yield "OLLAMA library not installed. (Mock response)"

    def generate_sql(self, user_query: str, schema_context: dict) -> tuple[str, str]:
        # Syntactic sugar for non-streaming context
        full_response = "".join(list(self.generate_sql_stream(user_query, schema_context)))
        return self._parse_sql_response(full_response)
        
    def fix_sql(self, user_query: str, wrong_sql: str, error_message: str, schema_context: dict) -> tuple[str, str]:
        system_prompt = f"""
        ROLE
        You are the "FinQuery SQL Fixer."
        
        TASK
        The previous SQL query generated for the [USER_QUERY] failed with an [ERROR].
        Fix the SQL query based on the [SCHEMA_CONTEXT] and the error message.
        
        SCHEMA_CONTEXT
        {schema_context}
        
        INPUTS
        User Query: {user_query}
        Wrong SQL: {wrong_sql}
        Error: {error_message}
        
        INSTRUCTIONS
        1. ANALYZE: Understand why the SQL failed.
        2. FIX: Generate the corrected SQL query. Do NOT output explanations.
        
        OUTPUT FORMAT
        ```sql
        SELECT ...
        ```
        """
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': "Please fix the SQL query."}
        ]
        full_response = "".join(list(self._call_llm_stream(messages)))
        return self._parse_sql_response(full_response)
        
    def synthesize_results(self, user_query: str, sql_query: str, raw_data: list) -> str:
        # Syntactic sugar for non-streaming context
        return "".join(list(self.synthesize_results_stream(user_query, sql_query, raw_data)))

    def _parse_sql_response(self, response_content: str) -> tuple[str, str]:
        thought = "Reasoning not provided."
        sql = "SELECT 1;" # Fallback
        
        try:
            if "```sql" in response_content:
                parts = response_content.split("```sql")
                thought_part = parts[0]
                sql_part = parts[1].split("```")[0].strip()
                
                sql = sql_part
                thought = thought_part.replace("Thought:", "").replace("SQL:", "").strip()
                
            elif "```" in response_content:
                 parts = response_content.split("```")
                 if len(parts) >= 3:
                     sql = parts[1].strip()
                     thought = parts[0].replace("Thought:", "").replace("SQL:", "").strip()

            elif "Thought:" in response_content and "SQL:" in response_content:
                parts = response_content.split("SQL:")
                thought = parts[0].replace("Thought:", "").strip()
                sql = parts[1].strip()

            if not sql or sql == "SELECT 1;":
                 import re
                 match = re.search(r'SELECT\s+.*?;', response_content, re.IGNORECASE | re.DOTALL)
                 if match:
                     sql = match.group(0).strip()
                     
        except Exception as e:
            thought = f"Parsing Error: {e}. Raw: {response_content[:100]}..."

        return sql, thought
