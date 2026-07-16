from pydantic import BaseModel, Field
from typing import Optional


class ClassificationResult(BaseModel):
    category: str
    urgency: str
    confidence: float = Field(ge=0.0, le=1.0)
    flagged_for_review: bool = False
    retry_count: int = 0
    error: Optional[str] = None


class DraftReply(BaseModel):
    reply_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[dict] = []
    flagged_for_review: bool = False
    retry_count: int = 0
    error: Optional[str] = None


class ExtractedData(BaseModel):
    name: Optional[str] = None
    issue: Optional[str] = None
    order_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    flagged_for_review: bool = False
    retry_count: int = 0
    error: Optional[str] = None


class AgentAction(BaseModel):
    action_id: str
    tool_name: str
    tool_input: dict
    status: str = "pending"  # pending, approved, rejected, executed, failed
    ticket_text: str = ""
    summary: str = ""
    approved: Optional[bool] = None


class ToolCallLog(BaseModel):
    timestamp: str
    tool_name: str
    input: dict
    output: dict
    status: str
    user_approved: Optional[bool] = None


class ProcessTicketRequest(BaseModel):
    ticket_text: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class ApproveActionRequest(BaseModel):
    action_id: str
    approved: bool


class ProcessTicketResponse(BaseModel):
    classification: ClassificationResult
    extracted_data: Optional[ExtractedData] = None
    draft_reply: Optional[DraftReply] = None
    agent_action: Optional[AgentAction] = None
    full_trace: list[dict] = []
