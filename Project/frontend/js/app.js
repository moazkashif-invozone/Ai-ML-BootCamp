let currentActionId = null;
let flaggedTickets = [];
let isProcessing = false;
let chatSessionId = null;
let isChatting = false;
let abortController = null;

const SAMPLES = [
  `Hi, I got my TechGear Pro yesterday and the charging pad won't work. The LED stays red and my phone doesn't charge. I already tried different cables. My order was ORD-12345. Please help!`,
  `I want a refund for my TechGear Pro. I bought it 2 weeks ago but it's not compatible with my Samsung phone. Order #ORD-12346. This is really frustrating.`,
  `Hi there, I ordered a TechGear Pro in Ocean Blue last week (order ORD-12347) and I want to know when it will arrive. Can you check the status for me? Thanks!`,
];

document.addEventListener('DOMContentLoaded', async () => {
  await checkHealth();
  await refreshLogs();
  document.getElementById('ticket-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.metaKey) handleProcessTicket();
  });

  const chatInput = document.getElementById('chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!isChatting) sendChatMessage();
      }
    });
    chatInput.addEventListener('input', autoResizeChat);
    setTimeout(() => {
      chatInput.disabled = false;
      document.getElementById('chat-send-btn').disabled = false;
      chatInput.focus();
    }, 100);
  }

  const theme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
});

function autoResizeChat() {
  const el = document.getElementById('chat-input');
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}

async function checkHealth() {
  try {
    const h = await getHealth();
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    dot.className = 'status-dot connected';
    text.textContent = 'Connected';
    document.getElementById('kb-status').textContent = `KB: ${h.knowledge_base_chunks} chunks`;
    document.getElementById('model-status').textContent = `Model: ${h.model}`;
  } catch (e) {
    document.getElementById('status-dot').className = 'status-dot error';
    document.getElementById('status-text').textContent = 'Disconnected';
  }
}

function switchTab(tab) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
  document.getElementById(`tab-${tab}`).classList.add('active');
  if (tab === 'logs') refreshLogs();
  if (tab === 'review') renderReviewQueue();
  if (tab === 'chat') {
    setTimeout(() => {
      document.getElementById('chat-input')?.focus();
    }, 200);
  }
}

function loadSample(index) {
  document.getElementById('ticket-input').value = SAMPLES[index] || '';
  document.getElementById('ticket-input').focus();
}

async function handleProcessTicket() {
  const text = document.getElementById('ticket-input').value.trim();
  if (!text) return;
  if (isProcessing) return;
  isProcessing = true;

  const btn = document.querySelector('.btn-primary');
  btn.disabled = true;
  btn.innerHTML = '<span class="loading-spinner" style="width:16px;height:16px;margin:0"></span> Processing...';

  document.getElementById('results-section').style.display = 'block';
  showLoading(['classification-body', 'extraction-body', 'reply-body', 'agent-body']);

  try {
    const data = await processTicketAPI(text);
    document.getElementById('classification-body').innerHTML = renderClassification(data.classification);
    document.getElementById('extraction-body').innerHTML = renderExtraction(data.extracted_data);

    const badges = [];
    if (data.draft_reply?.flagged_for_review) badges.push('<span class="badge-flag warning">&#9873; Flagged</span>');
    if (data.classification?.flagged_for_review) badges.push('<span class="badge-flag warning">Needs Review</span>');
    if (data.draft_reply?.sources?.length > 0) badges.push(`<span class="badge-flag info">${data.draft_reply.sources.length} sources</span>`);
    document.getElementById('reply-badges').innerHTML = badges.join('');

    document.getElementById('reply-body').innerHTML = renderReply(data.draft_reply, data.draft_reply.sources);

    document.getElementById('agent-body').innerHTML = renderAgent(
      data.full_trace?.find(t => t.step === 'agent')?.response || '',
      data.agent_action
    );

    document.getElementById('trace-output').textContent = renderTrace(data.full_trace);

    if (data.agent_action) {
      currentActionId = data.agent_action.action_id;
      showApprovalModal(data.agent_action);
    }

    const criticalKeywords = ['refund', 'return', 'cancel', 'cancel', 'damaged', 'defective', 'broken', 'faulty', 'complaint', 'chargeback', 'not working', 'replacement'];
    const textLower = text.toLowerCase();
    const hasCriticalKeyword = criticalKeywords.some(k => textLower.includes(k));
    const isCriticalUrgency = data.classification?.urgency === 'high' || data.classification?.urgency === 'critical';
    const isCriticalIssue = hasCriticalKeyword || isCriticalUrgency;

    if (isCriticalIssue && !data.agent_action) {
      data.agent_action = {
        action_id: 'action-' + Date.now(),
        tool_name: 'human_review',
        summary: 'Critical issue detected — requires manual review and approval',
        tool_input: {
          ticket: text.substring(0, 200),
          category: data.classification?.category || 'unknown',
          urgency: data.classification?.urgency || 'unknown',
          reason: hasCriticalKeyword ? 'Refund/critical keyword detected' : 'High urgency classification',
        },
      };
      currentActionId = data.agent_action.action_id;
      showApprovalModal(data.agent_action);
      document.getElementById('agent-body').innerHTML = renderAgent('', data.agent_action);
    }

    if (data.draft_reply?.flagged_for_review || data.classification?.flagged_for_review || isCriticalIssue) {
      flaggedTickets.push({
        ticket: text,
        category: data.classification?.category,
        urgency: data.classification?.urgency,
        confidence: data.classification?.confidence,
        error: isCriticalIssue ? 'Critical issue — requires human approval' : 'Low confidence — flagged for review',
      });
      updateReviewBadge();
    }

  } catch (err) {
    document.getElementById('classification-body').innerHTML = `<span class="value" style="color:var(--accent-red)">Error: ${escapeHtml(err.message)}</span>`;
    document.getElementById('extraction-body').innerHTML = '';
    document.getElementById('reply-body').innerHTML = '';
    document.getElementById('agent-body').innerHTML = '';
  } finally {
    isProcessing = false;
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">&#9654;</span> Process Ticket';
  }
}

function showLoading(ids) {
  ids.forEach(id => {
    document.getElementById(id).innerHTML = '<div class="loading-spinner"></div>';
  });
}

function showApprovalModal(action) {
  document.getElementById('approval-body').innerHTML = `
    <p><strong>Tool:</strong> ${action.tool_name}</p>
    <p><strong>Summary:</strong> ${escapeHtml(action.summary)}</p>
    <div class="code-block">${escapeHtml(JSON.stringify(action.tool_input, null, 2))}</div>
  `;
  document.getElementById('approval-modal').style.display = 'flex';
}

window.__approveAction = async function(actionId, approved) {
  currentActionId = actionId;
  await handleApproval(approved);
};

async function handleApproval(approved) {
  if (!currentActionId) return;
  document.getElementById('approval-modal').style.display = 'none';
  try {
    const result = await approveAction(currentActionId, approved);
    alert(approved ? 'Action approved and executed!' : 'Action rejected.');
    refreshLogs();
    if (result.status === 'executed') {
      const agentBody = document.getElementById('agent-body');
      const current = agentBody.innerHTML;
      agentBody.innerHTML = current + `<div style="margin-top:8px;padding:10px;background:rgba(52,211,153,0.08);border-radius:6px;border:1px solid rgba(52,211,153,0.2)">
        <span style="color:var(--accent-green)">&#10003; Action approved and executed successfully</span>
      </div>`;
    }
  } catch (err) {
    alert('Error processing approval: ' + err.message);
  }
  currentActionId = null;
}

// ===== Chat Functions =====

function addChatMsg(text, role) {
  const area = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  if (role === 'assistant') {
    div.innerHTML = `<div class="msg-content">${renderMarkdown(text)}</div>`;
    const actions = document.createElement('div');
    actions.className = 'chat-msg-actions';
    actions.innerHTML = `
      <button class="chat-msg-action" onclick="copyMsg(this)" title="Copy">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      </button>
      <button class="chat-msg-action" onclick="regenerateMsg(this)" title="Regenerate">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
      </button>
    `;
    div.appendChild(actions);
  } else {
    div.textContent = text;
  }
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
  return div;
}

function addStatusMsg(text) {
  const area = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-status';
  div.innerHTML = `
    <div class="chat-status-dots"><span></span><span></span><span></span></div>
    <span>${escapeHtml(text)}</span>
  `;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
  return div;
}

function removeLastStatus() {
  const area = document.getElementById('chat-messages');
  const last = area.querySelector('.chat-status:last-child');
  if (last) last.remove();
}

function getAssistantBubble() {
  const area = document.getElementById('chat-messages');
  let bubble = area.querySelector('.chat-msg.assistant:last-child');
  if (!bubble || bubble.dataset.streaming !== 'true') {
    bubble = document.createElement('div');
    bubble.className = 'chat-msg assistant';
    bubble.dataset.streaming = 'true';
    const content = document.createElement('div');
    content.className = 'msg-content';
    bubble.appendChild(content);

    const actions = document.createElement('div');
    actions.className = 'chat-msg-actions';
    actions.innerHTML = `
      <button class="chat-msg-action" onclick="copyMsg(this)" title="Copy">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      </button>
      <button class="chat-msg-action" onclick="likeMsg(this)" title="Helpful">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>
      </button>
      <button class="chat-msg-action" onclick="dislikeMsg(this)" title="Not helpful">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10zM17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>
      </button>
      <button class="chat-msg-action" onclick="regenerateMsg(this)" title="Regenerate">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
      </button>
    `;
    bubble.appendChild(actions);
    area.appendChild(bubble);
  }
  return bubble;
}

function appendToken(text) {
  const bubble = getAssistantBubble();
  const content = bubble.querySelector('.msg-content');
  const span = document.createElement('span');
  span.textContent = text;
  content.appendChild(span);
  document.getElementById('chat-messages').scrollTop = document.getElementById('chat-messages').scrollHeight;
}

function finalizeAssistantMsg() {
  const bubble = document.getElementById('chat-messages').querySelector('.chat-msg.assistant:last-child');
  if (bubble) {
    delete bubble.dataset.streaming;
  }
}

function getLastUserMsg() {
  const msgs = document.getElementById('chat-messages').querySelectorAll('.chat-msg.user');
  return msgs[msgs.length - 1] || null;
}

function getLastAssistantMsg() {
  const msgs = document.getElementById('chat-messages').querySelectorAll('.chat-msg.assistant');
  return msgs[msgs.length - 1] || null;
}

async function sendChatMessage(text) {
  const input = document.getElementById('chat-input');
  const msg = text || input.value.trim();
  if (!msg || isChatting) return;
  if (!text) input.value = '';
  input.style.height = 'auto';
  isChatting = true;

  document.getElementById('chat-welcome')?.remove();
  document.querySelectorAll('.chat-suggested')?.forEach(el => el.remove());

  addChatMsg(msg, 'user');

  const btn = document.getElementById('chat-send-btn');
  btn.disabled = true;
  btn.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="2"/>
    </svg>
  `;
  btn.classList.add('stop');
  btn.onclick = stopGeneration;

  abortController = new AbortController();

  try {
    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, session_id: chatSessionId }),
      signal: abortController.signal,
    });

    if (!res.ok) throw new Error('API error ' + res.status);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let statusEl = null;
    let startedTokens = false;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line);
          if (data.type === 'status' && !startedTokens) {
            if (!statusEl) statusEl = addStatusMsg(data.message);
            else statusEl.querySelector('span').textContent = escapeHtml(data.message);
          } else if (data.type === 'token') {
            if (statusEl) { statusEl.remove(); statusEl = null; }
            startedTokens = true;
            appendToken(data.content);
          } else if (data.type === 'done') {
            chatSessionId = data.session_id;
            startedTokens = true;
          }
        } catch (e) {}
      }
    }

    if (statusEl) statusEl.remove();
    finalizeAssistantMsg();

  } catch (err) {
    if (err.name === 'AbortError') {
      chatSessionId = null;
      return;
    }
    document.getElementById('chat-messages').querySelector('.chat-msg.assistant:last-child[data-streaming]')?.remove();
    addChatMsg('Sorry, something went wrong. Please try again.', 'assistant');
  } finally {
    isChatting = false;
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
      </svg>
    `;
    btn.classList.remove('stop');
    btn.onclick = () => sendChatMessage();
    document.getElementById('chat-input').focus();
  }
}

function stopGeneration() {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
}

function sendSuggested(text) {
  sendChatMessage(text);
}

async function regenerateMsg(el) {
  if (isChatting) return;
  const bubble = el.closest('.chat-msg.assistant');
  if (!bubble) return;

  const prevUser = bubble.previousElementSibling;
  if (!prevUser || !prevUser.classList.contains('chat-msg.user')) return;

  const userText = prevUser.textContent;
  bubble.remove();

  await sendChatMessage(userText);
}

function likeMsg(el) {
  el.classList.toggle('liked');
  el.closest('.chat-msg-actions').querySelector('.disliked')?.classList.remove('disliked');
}

function dislikeMsg(el) {
  el.classList.toggle('disliked');
  el.closest('.chat-msg-actions').querySelector('.liked')?.classList.remove('liked');
}

function copyMsg(el) {
  const bubble = el.closest('.chat-msg.assistant');
  if (!bubble) return;
  const text = bubble.querySelector('.msg-content').textContent;
  navigator.clipboard.writeText(text).then(() => {
    el.classList.add('copied');
    el.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
    `;
    setTimeout(() => {
      el.classList.remove('copied');
      el.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      `;
    }, 2000);
  });
}

function clearChat() {
  if (isChatting) {
    stopGeneration();
  }
  chatSessionId = null;
  document.getElementById('chat-messages').innerHTML = `
    <div class="chat-welcome" id="chat-welcome">
      <div class="chat-welcome-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <h2 class="chat-welcome-title">How can I help you today?</h2>
      <p class="chat-welcome-text">Ask me about laptops, phones, accessories, specifications, or product comparisons.</p>
      <div class="chat-suggested">
        <button class="chat-chip" onclick="sendSuggested('Recommend a gaming laptop')">&#127942; Recommend a gaming laptop</button>
        <button class="chat-chip" onclick="sendSuggested('Compare two phones')">&#128241; Compare two phones</button>
        <button class="chat-chip" onclick="sendSuggested('Best wireless headphones')">&#127911; Best wireless headphones</button>
        <button class="chat-chip" onclick="sendSuggested('Explain product specifications')">&#128196; Explain product specifications</button>
        <button class="chat-chip" onclick="sendSuggested('Find accessories')">&#128722; Find accessories</button>
      </div>
    </div>
  `;
  document.getElementById('chat-input').value = '';
  document.getElementById('chat-input').style.height = 'auto';
  document.getElementById('chat-input').focus();
}

async function refreshLogs() {
  try {
    const logs = await getToolLog();
    document.getElementById('log-body').innerHTML = renderToolLog(logs);
  } catch (e) {
    document.getElementById('log-body').innerHTML = `<tr><td colspan="5" class="empty-state">Error loading logs: ${escapeHtml(e.message)}</td></tr>`;
  }
}

function renderReviewQueue() {
  const container = document.getElementById('review-list');
  if (flaggedTickets.length === 0) {
    container.innerHTML = '<p class="empty-state">No flagged tickets. All clear.</p>';
    return;
  }
  container.innerHTML = flaggedTickets.map(renderReviewItem).join('');
}

function updateReviewBadge() {
  document.getElementById('review-badge').textContent = flaggedTickets.length;
}

function processFlaggedTickets() {
  if (flaggedTickets.length === 0) {
    alert('No flagged tickets to process.');
    return;
  }
  const result = confirm(`Process ${flaggedTickets.length} flagged ticket(s) for manual review?\n\nThis will clear the queue.`);
  if (result) {
    flaggedTickets = [];
    updateReviewBadge();
    renderReviewQueue();
    switchTab('inbox');
  }
}
