const API_BASE = '';

async function apiCall(endpoint, body = null) {
  const opts = {
    method: body ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${endpoint}`, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json();
}

async function classifyTicket(text) {
  return apiCall('/api/classify', { ticket_text: text });
}

async function extractData(text) {
  return apiCall('/api/extract', { ticket_text: text });
}

async function processTicketAPI(text) {
  return apiCall('/api/process-ticket', { ticket_text: text });
}

async function approveAction(actionId, approved) {
  return apiCall('/api/approve-action', { action_id: actionId, approved });
}

async function getToolLog() {
  return apiCall('/api/tool-log');
}

async function getHealth() {
  return apiCall('/api/health');
}

async function rebuildKnowledge() {
  return apiCall('/api/knowledge/rebuild');
}
