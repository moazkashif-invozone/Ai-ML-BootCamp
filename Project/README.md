# Support Ops Copilot

An AI-powered support assistant that classifies tickets, retrieves knowledge, drafts replies, and takes action through a tool-calling agent — all with human-in-the-loop approval for destructive operations.

Built as a 5-stage capstone project with Grok (xAI), FastAPI, ChromaDB, and a custom frontend.

---

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │              Frontend                    │
                    │       (HTML/CSS/JS — Vanilla)             │
                    │  Ticket Input | Review | Tool Log          │
                    └──────────────┬───────────────────────────┘
                                   │ REST API (JSON)
                    ┌──────────────▼───────────────────────────┐
                    │          FastAPI Backend                   │
                    │                                           │
                    │  POST /api/process-ticket                  │
                    │   ├── classify_ticket()  ──► Stage 1      │
                    │   ├── extract_data()     ──► Stage 1      │
                    │   ├── get_grounded_context() ──► Stage 3  │
                    │   │   └── ChromaDB (vector store)          │
                    │   │       └── knowledge_base/*.md          │
                    │   ├── draft_reply()      ──► Stage 1+3    │
                    │   └── run_agent()        ──► Stage 4      │
                    │       ├── lookup_order_status()            │
                    │       ├── issue_refund()  (needs approval) │
                    │       ├── escalate_to_human() (needs appr) │
                    │       └── send_customer_email()            │
                    │                                           │
                    │  All outputs validated via Pydantic (S2)   │
                    │  Low confidence → flagged for review       │
                    │                                           │
                    └──────────────┬───────────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────────┐
                    │           Grok API (xAI)                  │
                    │  base_url = "https://api.x.ai/v1"         │
                    │  Models: grok-3-mini / grok-4.5           │
                    └──────────────────────────────────────────┘
```

## Data Flow (End-to-End)

```
Ticket Input → Classify → Extract Data → Retrieve Knowledge (RAG) → Draft Reply → Agent Action → Response
                  │            │                 │                      │              │
                  ▼            ▼                 ▼                      ▼              ▼
            Category +    Name + Issue +    Top-k chunks          Grounded reply   Tool calls
            Urgency       Order ID          from ChromaDB         + citations       + approval
```

---

## Stages

| Stage | What | Files |
|---|---|---|
| 1 | Core AI Service — classify, extract, draft | `backend/ai_service.py` |
| 2 | Reliability — Pydantic validation, retry, confidence scoring | `backend/ai_service.py` (retry decorator), `backend/models.py` |
| 3 | RAG — ChromaDB + sentence embeddings + grounded answers | `backend/rag_pipeline.py`, `knowledge_base/*.md` |
| 4 | Agent — Tool-calling agent with human-in-the-loop approval | `backend/agent.py`, `backend/tool_log.py` |
| 5 | Full app — FastAPI routes + custom frontend | `backend/main.py`, `frontend/` |

---

## Setup

```bash
# 1. Clone and enter the project
cd support-ops-copilot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key
cp .env.example .env
# Edit .env and add your XAI_API_KEY (get one at https://console.x.ai)

# 5. Run the application
python -m backend.main
# Opens at http://localhost:8000
```

## Usage

1. Open `http://localhost:8000` in a browser
2. Type or paste a support ticket, or use the sample buttons
3. Click **Process Ticket** to run the full pipeline
4. View classification, extracted data, drafted reply, and agent actions
5. Approve or reject agent actions when prompted
6. Check the **Review Queue** for low-confidence tickets
7. Check **Tool Log** for a record of all agent tool calls

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/process-ticket` | Full pipeline: classify → extract → RAG → draft → agent |
| POST | `/api/classify` | Classify a ticket (category + urgency) |
| POST | `/api/extract` | Extract structured data (name, issue, order_id) |
| POST | `/api/approve-action` | Approve or reject a pending agent action |
| GET | `/api/tool-log` | Get all tool call logs |
| GET | `/api/health` | Health check + knowledge base stats |
| POST | `/api/knowledge/rebuild` | Rebuild the ChromaDB knowledge base |

## Tech Stack

- **LLM:** Grok (xAI API) via OpenAI-compatible client
- **Backend:** FastAPI (Python 3.9+)
- **Validation:** Pydantic v2
- **Vector DB:** ChromaDB (local, persistent)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Frontend:** Vanilla HTML/CSS/JS (no framework)

## Project Structure

```
support-ops-copilot/
├── backend/
│   ├── __init__.py
│   ├── main.py           # FastAPI app + routes (Stage 5)
│   ├── ai_service.py     # Core AI: classify, draft, extract (Stage 1-2)
│   ├── rag_pipeline.py   # ChromaDB + retrieval (Stage 3)
│   ├── agent.py          # Tool-calling agent (Stage 4)
│   ├── models.py         # Pydantic schemas
│   ├── config.py         # Settings
│   └── tool_log.py       # Tool call logging
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js
│       ├── components.js
│       └── app.js
├── knowledge_base/
│   ├── faq.md
│   ├── policies.md
│   └── past_tickets.md
├── BREAKING_IT.md        # Documented failure cases
├── .env.example
├── requirements.txt
└── README.md
```
