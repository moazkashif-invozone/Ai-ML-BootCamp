import json
import uuid
from typing import Optional, Generator
from openai import OpenAI
from backend.config import settings
from backend.rag_pipeline import get_grounded_context

_client: Optional[OpenAI] = None
_sessions: dict[str, list[dict]] = {}

SYSTEM_TEMPLATE = (
    "You are Tech Gear Pro Assistant, a helpful AI shopping advisor for Tech Gear Pro — "
    "a store that sells the TechGear Pro wireless charging station and accessories.\n\n"
    "IMPORTANT RULES:\n"
    "1. ONLY answer questions using the knowledge base context below.\n"
    "2. If the context does NOT contain the needed information, say: "
    "\"I'm sorry, I don't have information about that in my knowledge base. "
    "Is there something else I can help you with regarding TechGear Pro?\"\n"
    "3. Do NOT make up or infer information not in the context.\n"
    "4. Do NOT use your general training knowledge to answer.\n"
    "5. When referencing info, mention the source document.\n"
    "6. Use markdown for formatting.\n"
    "7. Be friendly, professional, and concise.\n\n"
    "--- Knowledge Base Context ---\n"
    "{context}\n"
    "--- End of Context ---"
)

NO_CONTEXT = (
    "No relevant knowledge base information found for this query. "
    "Politely let the user know you don't have information on this topic."
)


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.xai_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


def _get_or_create_session(
    session_id: Optional[str] = None,
) -> tuple[str, list[dict]]:
    if not session_id or session_id not in _sessions:
        session_id = session_id or str(uuid.uuid4())[:8]
        _sessions[session_id] = []
    return session_id, _sessions[session_id]


def _update_system_message(messages: list[dict], context: str) -> None:
    content = SYSTEM_TEMPLATE.format(context=context or NO_CONTEXT)
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = content
    else:
        messages.insert(0, {"role": "system", "content": content})


def chat_stream(
    message: str, session_id: Optional[str] = None
) -> Generator[str, None, None]:
    session_id, messages = _get_or_create_session(session_id)

    processing_steps = [
        "Understanding your question...",
        "Searching product knowledge...",
        "Finding relevant information...",
        "Preparing answer...",
    ]
    for step in processing_steps:
        yield json.dumps({"type": "status", "message": step}) + "\n"

    context = get_grounded_context(message, n_results=5)
    _update_system_message(messages, context)
    messages.append({"role": "user", "content": message})

    client = get_client()
    stream = client.chat.completions.create(
        model=settings.xai_model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
        stream=True,
    )

    full_reply = ""
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        content = delta.content if delta and delta.content else ""
        if content:
            full_reply += content
            yield json.dumps({"type": "token", "content": content}) + "\n"

    messages.append({"role": "assistant", "content": full_reply})
    yield json.dumps({"type": "done", "session_id": session_id}) + "\n"


def chat(message: str, session_id: Optional[str] = None) -> tuple[str, str]:
    session_id, messages = _get_or_create_session(session_id)
    context = get_grounded_context(message, n_results=5)
    _update_system_message(messages, context)
    messages.append({"role": "user", "content": message})

    client = get_client()
    resp = client.chat.completions.create(
        model=settings.xai_model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )

    reply = resp.choices[0].message.content or ""
    messages.append({"role": "assistant", "content": reply})
    return reply, session_id


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
