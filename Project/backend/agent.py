import json
import uuid
from typing import Optional, Callable
from openai import OpenAI
from backend.config import settings
from backend.models import AgentAction, ToolCallLog
from backend.tool_log import log_tool_call, get_tool_logs

_client: Optional[OpenAI] = None
_pending_actions: dict[str, AgentAction] = {}

DESTRUCTIVE_TOOLS = {"issue_refund", "escalate_to_human"}


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.xai_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


# --- Mock Tool Implementations ---

def lookup_order_status(order_id: str) -> dict:
    if not order_id or not order_id.startswith("ORD-"):
        return {"status": "error", "error": "Invalid order ID format"}
    mock_db = {
        "ORD-12345": {"status": "shipped", "estimated_delivery": "2026-07-16", "items": ["TechGear Pro - Midnight Black"]},
        "ORD-12346": {"status": "processing", "estimated_delivery": "2026-07-20", "items": ["TechGear Pro - Arctic White"]},
        "ORD-12347": {"status": "delivered", "delivered_date": "2026-07-10", "items": ["TechGear Pro - Ocean Blue"]},
        "ORD-12348": {"status": "cancelled", "reason": "customer request", "items": ["TechGear Pro - Midnight Black"]},
    }
    result = mock_db.get(order_id)
    if result:
        return {"status": "success", "order_id": order_id, "data": result}
    return {"status": "not_found", "error": f"No order found with ID {order_id}"}


def issue_refund(order_id: str, amount: float = None, reason: str = "") -> dict:
    return {
        "status": "pending_approval",
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "message": "Refund requires human approval before processing"
    }


def escalate_to_human(ticket_summary: str, reason: str = "") -> dict:
    return {
        "status": "pending_approval",
        "ticket_summary": ticket_summary,
        "reason": reason,
        "priority": "high",
        "message": "Escalation requires human approval before submitting"
    }


def send_customer_email(to: str, subject: str, body: str) -> dict:
    return {
        "status": "success",
        "to": to,
        "subject": subject,
        "message": f"Email queued for delivery to {to}"
    }


TOOLS_REGISTRY: dict[str, Callable] = {
    "lookup_order_status": lookup_order_status,
    "issue_refund": issue_refund,
    "escalate_to_human": escalate_to_human,
    "send_customer_email": send_customer_email,
}

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order_status",
            "description": "Look up the status and details of a customer order by order ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to look up (e.g. ORD-12345)"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": "Issue a refund for a customer order. This is a destructive action that requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to refund"
                    },
                    "amount": {
                        "type": "number",
                        "description": "The amount to refund in USD"
                    },
                    "reason": {
                        "type": "string",
                        "description": "The reason for the refund"
                    }
                },
                "required": ["order_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Escalate a ticket to a human support agent. This is used when the issue cannot be resolved automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_summary": {
                        "type": "string",
                        "description": "Summary of the ticket to escalate"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for escalation"
                    }
                },
                "required": ["ticket_summary", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_customer_email",
            "description": "Send an email to a customer with a subject and body",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Customer email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    }
]

AGENT_SYSTEM_PROMPT = """You are a support operations copilot agent. Your job is to handle customer support tickets.

You have access to tools that can help you:
- Look up order status
- Issue refunds (requires approval)
- Escalate to human support (requires approval)
- Send customer emails

Rules:
1. First, understand the customer's issue from the ticket.
2. Use tools when needed to gather information or take action.
3. For destructive actions (refund, escalation), clearly explain what you want to do and ask for approval.
4. Be helpful, concise, and professional in your responses.
5. If a tool fails, explain what happened to the customer and suggest alternatives.
6. Never fabricate information. If you don't know something, use a tool to find out.
"""


def run_agent(ticket_text: str, classification_category: str = "") -> tuple[str, Optional[AgentAction], list[dict]]:
    trace = []
    final_action: Optional[AgentAction] = None

    try:
        client = get_client()
    except Exception as exc:
        trace.append({"role": "error", "error": str(exc)})
        return (
            "The agent service is unavailable right now because the LLM connection could not be initialized.",
            None,
            trace,
        )

    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": f"Ticket: {ticket_text}\n\nCategory: {classification_category}\n\nHandle this ticket appropriately."},
    ]

    max_iterations = 5
    for iteration in range(max_iterations):
        try:
            resp = client.chat.completions.create(
                model=settings.xai_model,
                messages=messages,
                tools=TOOLS_DEFINITIONS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=2048,
            )
        except Exception as exc:
            trace.append({"role": "error", "error": str(exc)})
            return (
                "The agent service is unavailable right now because the LLM request failed.",
                None,
                trace,
            )

        msg = resp.choices[0].message

        if not msg.tool_calls:
            trace.append({"role": "assistant", "content": msg.content or ""})
            return msg.content or "", final_action, trace

        messages.append(msg)

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                tool_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                tool_args = {}
            tool_fn = TOOLS_REGISTRY.get(tool_name)
            if not tool_fn:
                trace.append({"role": "tool", "tool": tool_name, "output": {"status": "error", "error": f"Unknown tool: {tool_name}"}})
                continue

            try:
                output = tool_fn(**tool_args)
            except Exception as e:
                output = {"status": "error", "error": str(e)}

            log_tool_call(
                tool_name=tool_name, inp=tool_args, output=output,
                status=output.get("status", "error"),
            )

            trace.append({"role": "assistant", "tool_call": tool_name, "input": tool_args})
            trace.append({"role": "tool", "tool": tool_name, "output": output})

            if tool_name in DESTRUCTIVE_TOOLS and output.get("status") == "pending_approval":
                action_id = str(uuid.uuid4())[:8]
                action = AgentAction(
                    action_id=action_id,
                    tool_name=tool_name,
                    tool_input=tool_args,
                    status="pending",
                    ticket_text=ticket_text,
                    summary=f"Request to {tool_name}: {json.dumps(tool_args)}",
                )
                _pending_actions[action_id] = action
                final_action = action

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(output),
                })
                messages.append({
                    "role": "assistant",
                    "content": f"Action {tool_name} requires approval. Action ID: {action_id}. Waiting for human decision."
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(output),
                })

        if final_action and final_action.status == "pending":
            break

    return "Agent interaction complete. Check the action log for details.", final_action, trace


def approve_action(action_id: str, approved: bool) -> Optional[AgentAction]:
    action = _pending_actions.get(action_id)
    if not action:
        return None

    action.approved = approved
    if approved:
        tool_fn = TOOLS_REGISTRY.get(action.tool_name)
        if tool_fn:
            try:
                output = tool_fn(**action.tool_input)
                action.status = "executed"
                log_tool_call(
                    tool_name=action.tool_name, inp=action.tool_input,
                    output=output, status="executed", user_approved=True,
                )
            except Exception as e:
                action.status = "failed"
                output = {"status": "error", "error": str(e)}
                log_tool_call(
                    tool_name=action.tool_name, inp=action.tool_input,
                    output=output, status="failed", user_approved=True,
                )
        else:
            action.status = "failed"
    else:
        action.status = "rejected"
        log_tool_call(
            tool_name=action.tool_name, inp=action.tool_input,
            output={"status": "rejected", "message": "Approval denied"},
            status="rejected", user_approved=False,
        )

    _pending_actions.pop(action_id, None)
    return action


def get_pending_action(action_id: str) -> Optional[AgentAction]:
    return _pending_actions.get(action_id)
