# Day-2 — Validated AI Service (Python)

An extended, production-ready Python port of the **Day-1** AI service. Day-1 remains untouched; all new work lives in this folder.

Day-2 refactors every Day-1 function to return **schema-validated JSON**, adds **automatic retry logic**, includes a **`confidence_score`** on every response, and **flags low-confidence outputs** for human review.

---

## Directory Structure

```
Day-2/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .gitignore
├── main.py                   # Interactive CLI (primary entry point)
├── demo.py                   # Batch demo of all four functions
├── config/
│   ├── __init__.py
│   └── settings.py           # Environment-based configuration
├── schemas/
│   ├── __init__.py
│   ├── base.py               # Base response with confidence_score
│   ├── lead.py               # Lead qualification schema
│   ├── support.py            # Support ticket schema
│   ├── email.py              # Email draft schema
│   └── extraction.py         # Data extraction schema
├── services/
│   ├── __init__.py
│   ├── ai_client.py          # OpenAI-compatible client with retries
│   └── ai_service.py         # Four refactored Day-1 functions
└── utils/
    ├── __init__.py
    ├── retry.py              # Retry decorator (max 3 attempts)
    ├── validators.py         # Temperature validation
    ├── response_handler.py   # JSON parsing & schema validation
    └── display.py            # Pretty-print validated responses
```

---

## Improvements Over Day-1

| Feature | Day-1 | Day-2 |
|---|---|---|
| Language | JavaScript | Python |
| Response format | Parsed JSON (unvalidated) | Pydantic schema validation |
| Retry logic | None | Up to 3 automatic retries on transient API errors |
| Confidence scoring | None | `confidence_score` (0.0–1.0) on every response |
| Human review flag | None | Auto-flags responses below configurable threshold |
| Temperature validation | None | CLI rejects values outside 0.0–2.0 |
| User interface | Script-only demo | Interactive CLI + demo script |

---

## Prerequisites

- Python 3.9 or later
- An API key from a supported provider (Groq, xAI, or OpenAI)

---

## Setup

### 1. Create a virtual environment

```bash
cd Day-2
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate       # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_BASE_URL=https://api.groq.com/openai/v1
CONFIDENCE_THRESHOLD=0.7
MAX_RETRIES=3
```

---

## Usage

### Interactive CLI (recommended)

```bash
python main.py
```

The CLI will:

1. Show a menu of the four Day-1 functions plus a custom-prompt mode.
2. Collect the required input for the selected task.
3. Ask you to specify the **model temperature**.
4. Validate that temperature is between **0.0 and 2.0** (rejecting invalid values with a clear error).
5. Execute the request with automatic retries.
6. Display the **validated JSON response** in readable format.
7. Highlight responses flagged for **human review** when confidence is below the threshold.

### Run the batch demo

```bash
python demo.py
```

Runs the same examples as Day-1's `demo.js`, printing validated JSON for each function.

---

## The Four Functions

### `qualify_lead(lead_info, temperature=0.1)`

Evaluates a sales lead. Returns a validated `LeadQualificationResponse` with `qualified`, `score`, `priority`, `reasoning`, `recommended_next_step`, `key_signals`, and `confidence_score`.

### `classify_support_ticket(ticket_text, temperature=0.0)`

Triages a support ticket. Returns a validated `SupportTicketResponse` with `category`, `priority`, `sentiment`, `summary`, `suggested_team`, `requires_escalation`, and `confidence_score`.

### `draft_email(purpose, audience, context, tone, temperature=0.7)`

Drafts a business email. Returns a validated `EmailDraftResponse` with `subject`, `body`, and `confidence_score`.

### `extract_data(raw_text, fields, temperature=0.0)`

Extracts structured fields from unstructured text. Returns a validated `DataExtractionResponse` with `extracted_fields` and `confidence_score`.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | API key (also accepts `OPENAI_API_KEY`, `XAI_API_KEY`) |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Model identifier |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Provider base URL |
| `CONFIDENCE_THRESHOLD` | `0.7` | Responses below this score are flagged for human review |
| `MAX_RETRIES` | `3` | Maximum API retry attempts before raising an error |

---

## Error Handling

- **Invalid temperature** — Rejected immediately with a clear message; the CLI re-prompts.
- **Transient API failures** — Automatically retried up to 3 times with exponential backoff.
- **Invalid model JSON** — Re-requested up to 3 times; raises `ResponseValidationError` if still invalid.
- **Missing API key** — Caught at startup with a configuration error message.

---

## Relationship to Day-1

Day-1 (`../Day-1/`) is preserved as-is. Day-2 is a standalone Python reimplementation that mirrors the same four business functions with added reliability and validation layers. No Day-1 files are modified.

---

## License

Built as a learning and portfolio exercise. Feel free to use and adapt for your own work.
