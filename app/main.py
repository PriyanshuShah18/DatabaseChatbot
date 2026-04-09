import logging
from typing import List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .llm import generate_query_plan, generate_nl_response
from .services import execute_query_plan, QueryValidationError
from .database import get_allowed_fields
from .llm import MODEL_NAME
#from .seed import seed_database

# ── Logging
logger = logging.getLogger("uvicorn.error")

import os

app = FastAPI(title="CodnestX AI Copilot", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup 

@app.on_event("startup")
def startup_event():
    # seed_database() 
    pass


# ── Models

class HistoryMessage(BaseModel):
    role: str  # "user" or "ai"
    text: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[HistoryMessage]] = []

class ChatResponse(BaseModel):
    answer: str
    query_plan: dict | None = None
    raw_data: list | None = None
    error: str | None = None


# ── Routes

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    user_msg = request.message.strip()

    if not user_msg:
        return ChatResponse(answer="Please enter a question.", error="empty_query")

    history = [(h.role, h.text) for h in (request.history or [])]

    try:
        # Step 1 — LLM generates a structured query plan (now powered by LangChain)
        plan = generate_query_plan(user_msg, history=history)

        if not plan.get("collection"):
            return ChatResponse(
                answer="I couldn't determine which data to query. Please try rephrasing.",
                error="invalid_collection"
            )

        logger.info("Query plan: %s", plan)

        # Step 2 — Execute the plan against MongoDB (with validation)
        raw_data = execute_query_plan(plan)
        logger.info("Query returned %d records", len(raw_data))

        # Step 3 — LLM converts raw results into natural language
        answer = generate_nl_response(user_msg, raw_data)

        return ChatResponse(
            answer=answer,
            query_plan=plan,
            raw_data=raw_data,
        )

    except QueryValidationError as e:
        logger.warning("Validation error for plan %s: %s", plan, e)
        return ChatResponse(
            answer="I'm sorry, I couldn't process that query safely. It seems like the AI tried to access restricted data or used an invalid field.",
            query_plan=plan,
            error=str(e),
        )

    except Exception as e:
        logger.exception("Unexpected error in /chat")
        return ChatResponse(
            answer="Something went wrong while processing your request. Please try again.",
            error=str(e),
        )

@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}

@app.get("/schema-info")
def schema_info():
    return get_allowed_fields()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
