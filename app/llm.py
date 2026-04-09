import os
import json
import re
import logging
from dotenv import load_dotenv

# LangChain imports
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Pydantic models for structured output
from .schema_pydantic import QueryPlan,SortModel, AggregationModel

from .schema import extract_schema
from .database import ALLOWED_COLLECTIONS

logger = logging.getLogger("invoicifyx.llm")

load_dotenv()

MODEL_NAME = "qwen/qwen3-32b"

# LangChain Groq client
langchain_model = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name=MODEL_NAME,
    temperature=0
)

RESPONSE_FORMATTER_SYSTEM = """You are a helpful Real Estate & Property Management assistant for CodnestX.

You receive:
1. The user's original question.
2. Raw data from the database (JSON).

Your job:
- Summarise the data in clear, natural language related to property management.
- Include specific numbers, amounts (prefix with AED), names, and dates when available.
- If the data is empty, say "No relevant property records found."
- Keep it concise — 2-4 sentences max.
- Do NOT invent data that is not in the raw results.
- Use AED currency formatting (e.g., AED 15,000).
"""

def generate_query_plan(user_message: str, history: list = None) -> dict:
    """
    Use LLM to convert natural language → structured query plan.
    Uses manual parsing + Pydantic validation for maximum compatibility with Groq.
    """
    live_schema = extract_schema()
    allowed_schema = {col: live_schema.get(col, {}) for col in ALLOWED_COLLECTIONS.keys()}

    # Build conversation history lines for context
    history_text = "None"
    if history:
        recent = history[-4:]  # last 2 turns (user + ai each)
        lines = []
        for role, text in recent:
            prefix = "User" if role == "user" else "Assistant"
            lines.append(f"{prefix}: {text[:200]}")
        history_text = "\n".join(lines)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a professional Real Estate Data Assistant for CodnestX. 
You must output ONLY valid JSON.

[DATABASE CONTEXT]
- 'tenants': Tenants and property owners details, lease status.
- 'rent_invoices': Rental payments, service charges, maintenance bills.
- 'maintenance_vendors', 'properties', 'bank_accounts', 'transactions': Property maintenance, unit listings, and rental accounts.

[LIVE SCHEMA & SAMPLE ENTITIES]
{schema}

[CONVERSATION HISTORY]
{history}

[RESPONSE FORMAT]
{{
  "collection": "string",
  "filters": {{}},
  "aggregation": null | {{"group_by": "string", "operation": "sum|count|avg|max|min", "field": "string"}},
  "sort": null | {{"field": "string", "order": "asc|desc"}},
  "limit": number,
  "fields": ["string"]
}}

[RULES]
1. Use ONLY collections and fields listed in the LIVE SCHEMA.
2. Cross-reference user entities with 'sample_entities'.
3. If asking for "status" of a company, check 'clients' first.
4. Use CONVERSATION HISTORY to resolve pronouns (it, that, its).
5. Never use the string "None" for field values; use literal null.
6. NO EXPLANATION. ONLY RAW JSON."""),
        ("human", "{user_message}")
    ]).partial(schema=json.dumps(allowed_schema, indent=2), history=history_text)

    structured_llm = langchain_model.with_structured_output(QueryPlan, method="json_mode")
    chain = prompt | structured_llm

    try:
        plan_obj = chain.invoke({"user_message": user_message})
        
        # Fallback if the model returns something that isn't a QueryPlan object (rare with with_structured_output)
        if isinstance(plan_obj, dict):
            # Ensure filters is a dict if LLM sent []
            if isinstance(plan_obj.get("filters"), list):
                plan_obj["filters"] = {}
            plan_obj = QueryPlan(**plan_obj)

        return plan_obj.model_dump()
    except Exception as e:
        logger.error(f"Query Plan Error (Parsing/Validation): {e}")
        # Return a safe plan with None collection to trigger a "could not process" message
        # instead of returning random data from 'invoices'.
        return {"collection": None, "filters": {}, "aggregation": None, "limit": 10, "fields": []}

def generate_nl_response(user_message: str, raw_data: list) -> str:
    """
    Convert raw DB results into natural language using LangChain.
    """
    data_str = json.dumps(raw_data[:30], default=str, indent=2)

    prompt = ChatPromptTemplate.from_messages([
        ("system", RESPONSE_FORMATTER_SYSTEM),
        ("human", "User question: {user_message}\n\nDatabase results ({count} records):\n{data}")
    ])

    chain = prompt | langchain_model | StrOutputParser()

    try:
        content = chain.invoke({
            "user_message": user_message,
            "count": len(raw_data),
            "data": data_str
        })
        # Note: structured output modes usually don't need think tag cleaning, 
        # but for text responses we keep a simple cleanup just in case.
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content
    except Exception as e:
        logger.error(f"NL Response Error: {e}")
        return f"Error generating response: {str(e)}"