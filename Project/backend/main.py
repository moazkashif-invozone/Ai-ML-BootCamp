import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.config import settings
from backend.models import (
    ProcessTicketRequest, ProcessTicketResponse,
    ApproveActionRequest, ChatRequest, ChatResponse,
    ClassificationResult, DraftReply, ExtractedData, AgentAction,
)
from backend.ai_service import classify_ticket, draft_reply, extract_data
from backend.rag_pipeline import build_knowledge_base as build_rag, get_grounded_context, get_collection
from backend.agent import run_agent, approve_action as approve_agent_action, get_pending_action
from backend.tool_log import get_tool_logs
from backend.chat_agent import chat as chat_with_agent, chat_stream, clear_session as clear_chat_session
from fastapi.responses import StreamingResponse

app = FastAPI(title="Support Ops Copilot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.on_event("startup")
async def startup():
    build_rag()


@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.post("/api/classify")
async def api_classify(req: ProcessTicketRequest):
    result = classify_ticket(req.ticket_text)
    return result.model_dump()


@app.post("/api/extract")
async def api_extract(req: ProcessTicketRequest):
    result = extract_data(req.ticket_text)
    return result.model_dump()


@app.post("/api/process-ticket")
async def api_process_ticket(req: ProcessTicketRequest):
    ticket = req.ticket_text
    trace = []

    cls_result = classify_ticket(ticket)
    trace.append({"step": "classification", "result": cls_result.model_dump()})

    ext_result = extract_data(ticket)
    trace.append({"step": "extraction", "result": ext_result.model_dump()})

    context = ""
    rag_used = False
    try:
        col = get_collection()
        if col.count() > 0:
            context = get_grounded_context(ticket)
            rag_used = bool(context)
    except Exception:
        pass

    draft_result = draft_reply(ticket, cls_result, context)
    if context:
        draft_result.sources = [
            {"source": s["source"], "distance": s["distance"]}
            for s in retrieve_context_for_draft(ticket)
        ]
    trace.append({"step": "draft_reply", "result": draft_result.model_dump(), "rag_used": rag_used})

    agent_response, agent_action, agent_trace = run_agent(ticket, cls_result.category)
    trace.append({"step": "agent", "response": agent_response, "action": agent_action.model_dump() if agent_action else None})

    return ProcessTicketResponse(
        classification=cls_result,
        extracted_data=ext_result,
        draft_reply=draft_result,
        agent_action=agent_action,
        full_trace=trace,
    ).model_dump()


def retrieve_context_for_draft(ticket: str) -> list[dict]:
    from backend.rag_pipeline import retrieve_context
    return retrieve_context(ticket)


@app.post("/api/approve-action")
async def api_approve_action(req: ApproveActionRequest):
    result = approve_agent_action(req.action_id, req.approved)
    if not result:
        raise HTTPException(status_code=404, detail="Action not found or already processed")
    return result.model_dump()


@app.get("/api/tool-log")
async def api_tool_log():
    return get_tool_logs()


@app.get("/api/health")
async def api_health():
    try:
        col = get_collection()
        kb_count = col.count()
    except Exception:
        kb_count = 0
    return {
        "status": "ok",
        "knowledge_base_chunks": kb_count,
        "model": settings.xai_model,
    }


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    reply, session_id = chat_with_agent(req.message, req.session_id)
    return ChatResponse(reply=reply, session_id=session_id).model_dump()


@app.post("/api/chat/stream")
async def api_chat_stream(req: ChatRequest):
    return StreamingResponse(
        chat_stream(req.message, req.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/clear")
async def api_chat_clear(req: ChatRequest):
    if req.session_id:
        clear_chat_session(req.session_id)
    return {"status": "ok"}


@app.post("/api/knowledge/rebuild")
async def api_rebuild_knowledge():
    try:
        col = get_collection()
        existing_ids = col.get()["ids"]
        if existing_ids:
            col.delete(existing_ids)
    except Exception:
        pass
    count = build_rag()
    return {"status": "ok", "chunks_ingested": count}


@app.get("/{path:path}")
async def serve_static(path: str):
    filepath = FRONTEND_DIR / path
    if filepath.exists() and filepath.is_file():
        return FileResponse(str(filepath))
    return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
