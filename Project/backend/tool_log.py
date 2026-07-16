import json
import os
from datetime import datetime, timezone
from backend.config import settings


def log_tool_call(tool_name: str, inp: dict, output: dict,
                  status: str, user_approved: bool = None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "input": inp,
        "output": output,
        "status": status,
        "user_approved": user_approved,
    }
    path = settings.tool_log_path
    logs = []
    if os.path.exists(path):
        try:
            with open(path) as f:
                logs = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []
    logs.append(entry)
    with open(path, "w") as f:
        json.dump(logs, f, indent=2)
    return entry


def get_tool_logs() -> list[dict]:
    path = settings.tool_log_path
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []
