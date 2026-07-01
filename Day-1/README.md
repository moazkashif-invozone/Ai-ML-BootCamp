# AI Service — Practical LLM Utilities for Everyday Business Tasks

This project is a reusable JavaScript service that wraps large language model (LLM) capabilities behind four focused, production-minded functions. Instead of treating AI as a generic chat box, the goal here was to solve specific, recurring business problems: qualifying sales leads, triaging support tickets, drafting emails, and pulling structured data out of messy text.

Each function is built around a clear prompt, a predictable JSON response shape, and sensible defaults for temperature — so outputs are useful in real workflows, not just interesting to read.

---

## What I Built

I created **`AIService.js`**, a single class that centralizes all LLM interactions. Behind the scenes it uses the OpenAI-compatible SDK, which means it works with providers like **Groq**, **xAI**, or **OpenAI** — as long as you supply an API key and base URL.

On top of that core service, I added **`demo.js`**, a small script that runs all four functions end-to-end so you can see how each one behaves with sample input.

The design choices I made along the way:

- **Structured JSON responses** — Every function returns parsed JSON, not free-form text. That makes it easy to plug into dashboards, CRMs, or backend pipelines without extra parsing logic.
- **Task-specific temperature settings** — Classification and extraction use low temperature for consistency. Email drafting exposes temperature as a parameter so you can deliberately control creativity.
- **Flexible input** — Lead qualification accepts either plain text or a structured object. Data extraction accepts a simple field list or a full schema.
- **Environment-based configuration** — API keys and model settings live in `.env`, keeping secrets out of source code.

---

## The Four Functions

### 1. Lead Qualification — `qualifyLead(leadInfo)`

Takes raw lead information and evaluates whether it is worth pursuing.

**Input:** A string or object (name, company, role, message, etc.)

**Output:** A qualification report including score (0–100), priority, reasoning, recommended next step, and key buying signals.

**Why it matters:** Sales teams often receive inbound leads in inconsistent formats. This function turns that noise into a quick, actionable assessment.

---

### 2. Support Ticket Classifier — `classifySupportTicket(ticketText)`

Reads a customer support message and routes it intelligently.

**Input:** The raw ticket text

**Output:** Category, priority, sentiment, a one-line summary, suggested team, and whether escalation is needed.

**Why it matters:** Support queues grow fast. Automated triage helps the right team respond sooner — especially for urgent or billing-related issues.

---

### 3. Email Drafter — `draftEmail({ purpose, audience, context, tone, temperature })`

Generates a subject line and email body based on context you provide.

**Input:** Purpose, audience, background context, tone, and optionally **temperature**

**Output:** `{ subject, body }`

**Temperature and creativity:** This is the one function where temperature is intentionally exposed. Lower values (e.g. `0.2`) produce safer, more formal copy. Higher values (e.g. `0.9`) allow more creative and varied wording. The demo runs both side by side so you can compare the difference on the same prompt.

**Why it matters:** Email writing is repetitive but context-sensitive. This function saves time while still letting you tune how bold or conservative the tone should be.

---

### 4. Data Extractor — `extractData(rawText, fields)`

Pulls structured fields from unstructured text.

**Input:** Raw text plus a list of field names (or a schema)

**Output:** A JSON object with extracted values. Missing fields return `null` rather than invented data.

**Why it matters:** Invoices, contact forms, shipping notifications, and chat logs often contain useful data buried in plain text. This function turns that into something your app can actually use.

---

## Project Structure

```
.
├── AIService.js      # Core service class with all four functions
├── demo.js           # Runnable examples for each function
├── package.json      # Dependencies and scripts
├── .env              # Environment variable template
└── README.md         # This file
```

---

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or later recommended)
- An API key from a supported provider (Groq, xAI, or OpenAI) (#I have used Groq api key here.)

### Installation

```bash
npm install
```

### Configuration

Copy the example environment file and add your credentials:

```bash
cp .env
```

Edit `.env` with your values:

```env
GROK_API_KEY=your_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

The service also accepts `XAI_API_KEY`, `OPENAI_API_KEY`, and matching model/base URL variables if you prefer a different provider.

### Run the Demo

```bash
npm run demo
```

This will sequentially run lead qualification, ticket classification, two email drafts (low vs. high temperature), and a data extraction example — printing each result to the console.

---

## Usage Example

```javascript
import dotenv from "dotenv";
import AIService from "./AIService.js";

dotenv.config();

const ai = new AIService();

// Qualify a lead
const lead = await ai.qualifyLead({
  name: "Jane Doe",
  company: "Acme Corp",
  role: "VP Engineering",
  message: "We need an enterprise plan for 200 seats by Q3.",
});

// Classify a support ticket
const ticket = await ai.classifySupportTicket(
  "I was charged twice and cannot log in. This is urgent."
);

// Draft an email with controlled creativity
const email = await ai.draftEmail({
  purpose: "Follow up after product demo",
  audience: "Prospect CTO",
  context: "They liked the dashboard but asked about SSO.",
  tone: "professional",
  temperature: 0.7,
});

// Extract structured data from raw text
const data = await ai.extractData(
  "Contact: John Smith, john@example.com, Order #48291",
  ["name", "email", "orderId"]
);
```

---

## What I Learned

Building this service reinforced a few practical lessons about working with LLMs in application code:

1. **Prompt design is half the product.** Clear system prompts and fixed JSON schemas make outputs far more reliable than open-ended instructions.
2. **Temperature is not one-size-fits-all.** Deterministic tasks (classification, extraction) benefit from low temperature. Creative tasks (email drafting) benefit from giving the caller control.
3. **A thin abstraction goes a long way.** One shared `_chat` helper keeps the four functions consistent while letting each define its own behavior.
4. **Provider flexibility matters early.** Using the OpenAI SDK with a configurable `baseURL` avoids locking the project to a single vendor from day one.

---

## License

This project was built as a learning and portfolio exercise. Feel free to use and adapt it for your own work.
