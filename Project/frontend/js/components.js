function renderConfidence(value) {
  const pct = Math.round(value * 100);
  const cls = pct >= 70 ? 'high' : pct >= 40 ? 'medium' : 'low';
  return `
    <div class="confidence-bar">
      <div class="bar-track">
        <div class="bar-fill ${cls}" style="width:${pct}%"></div>
      </div>
      <span class="confidence-text">${pct}%</span>
    </div>
  `;
}

function renderClassification(data) {
  if (!data) return '<div class="loading-spinner"></div>';
  if (data.error) return `<div class="result-item"><span class="value" style="color:var(--accent-red)">Error: ${data.error}</span></div>`;
  const urgencyColors = {
    low: 'var(--accent-green)',
    medium: 'var(--accent-yellow)',
    high: 'var(--accent-red)',
    critical: 'var(--accent-red)',
  };
  return `
    <div class="result-item">
      <span class="label">Category</span>
      <span class="value highlight">${data.category || 'unknown'}</span>
    </div>
    <div class="result-item">
      <span class="label">Urgency</span>
      <span class="value" style="color:${urgencyColors[data.urgency] || 'var(--text-primary)'}">${data.urgency || 'unknown'}</span>
    </div>
    <div class="result-item">
      <span class="label">Confidence</span>
      ${renderConfidence(data.confidence)}
    </div>
    ${data.flagged_for_review ? '<div class="result-item"><span class="label">Flagged</span><span class="value" style="color:var(--accent-yellow)">&#9873; Needs Review</span></div>' : ''}
    ${retryBadge(data.retry_count)}
    ${data.error ? `<div class="result-item"><span class="label">Error</span><span class="value" style="color:var(--accent-red)">${escapeHtml(data.error)}</span></div>` : ''}
  `;
}

function retryBadge(count) {
  if (!count || count === 0) return '';
  const label = count >= 3 ? 'Max retries exhausted' : `Retried ${count} time${count > 1 ? 's' : ''}`;
  const color = count >= 3 ? 'var(--accent-red)' : 'var(--accent-yellow)';
  return `<div class="result-item"><span class="label">Retries</span><span class="value" style="color:${color}">&#8635; ${label}</span></div>`;
}

function renderExtraction(data) {
  if (!data) return '<div class="loading-spinner"></div>';
  if (data.error) return `<div class="result-item"><span class="value" style="color:var(--accent-red)">Error: ${data.error}</span></div>`;
  return `
    <div class="result-item">
      <span class="label">Name</span>
      <span class="value">${data.name || '<span style="color:var(--text-muted)">Not found</span>'}</span>
    </div>
    <div class="result-item">
      <span class="label">Issue</span>
      <span class="value">${data.issue || '<span style="color:var(--text-muted)">Not found</span>'}</span>
    </div>
    <div class="result-item">
      <span class="label">Order ID</span>
      <span class="value highlight">${data.order_id || '<span style="color:var(--text-muted)">Not found</span>'}</span>
    </div>
    <div class="result-item">
      <span class="label">Confidence</span>
      ${renderConfidence(data.confidence)}
    </div>
    ${data.flagged_for_review ? '<div class="result-item"><span class="label">Flagged</span><span class="value" style="color:var(--accent-yellow)">&#9873; Needs Review</span></div>' : ''}
    ${retryBadge(data.retry_count)}
    ${data.error ? `<div class="result-item"><span class="label">Error</span><span class="value" style="color:var(--accent-red)">${escapeHtml(data.error)}</span></div>` : ''}
  `;
}

function renderReply(data, sources) {
  if (!data) return '<div class="loading-spinner"></div>';
  if (data.error) return `<div class="result-item"><span class="value" style="color:var(--accent-red)">Error: ${data.error}</span></div>`;
  let html = '';
  if (data.reply_text) {
    html += `<div class="reply-text">${escapeHtml(data.reply_text)}</div>`;
  } else {
    html += '<div class="no-agent">No reply drafted.</div>';
  }
  html += `
    <div class="result-item">
      <span class="label">Confidence</span>
      ${renderConfidence(data.confidence)}
    </div>
  `;
  html += retryBadge(data.retry_count);
  if (data.error) {
    html += `<div class="result-item"><span class="label">Error</span><span class="value" style="color:var(--accent-red)">${escapeHtml(data.error)}</span></div>`;
  }
  if (sources && sources.length > 0) {
    html += `<div class="sources-section"><h4>Sources (${sources.length})</h4>`;
    sources.forEach(s => {
      html += `<span class="source-tag">${escapeHtml(s.source)}</span>`;
    });
    html += '</div>';
  }
  return html;
}

function renderAgent(data, action) {
  if (action) {
    return `
      <div class="agent-response">${escapeHtml(data || '')}</div>
      <div class="agent-action-card">
        <h4>&#9888; Action Pending Approval</h4>
        <p><strong>Tool:</strong> ${action.tool_name}</p>
        <p><strong>Input:</strong> ${escapeHtml(JSON.stringify(action.tool_input, null, 2))}</p>
        <div style="margin-top:12px;display:flex;gap:8px">
          <button class="btn-success" onclick="window.__approveAction('${action.action_id}', true)">&#10003; Approve</button>
          <button class="btn-danger" onclick="window.__approveAction('${action.action_id}', false)">&#10007; Reject</button>
        </div>
      </div>
    `;
  }
  if (data) {
    return `<div class="agent-response">${escapeHtml(data)}</div>`;
  }
  return '<div class="no-agent">No agent action needed.</div>';
}

function renderTrace(trace) {
  if (!trace || trace.length === 0) return 'No trace data.';
  return trace.map(t => {
    if (typeof t === 'string') return `// ${t}`;
    return JSON.stringify(t, null, 2);
  }).join('\n\n');
}

function renderToolLog(logs) {
  if (!logs || logs.length === 0) {
    return '<tr><td colspan="5" class="empty-state">No tool calls yet.</td></tr>';
  }
  return logs.map(log => `
    <tr>
      <td style="font-size:11px;color:#fff;font-family:var(--font-mono)">${new Date(log.timestamp).toLocaleString()}</td>
      <td><strong>${escapeHtml(log.tool_name)}</strong></td>
      <td><div class="tool-input-preview" title="${escapeHtml(JSON.stringify(log.input))}">${escapeHtml(JSON.stringify(log.input))}</div></td>
      <td><span class="log-status ${log.status}">${log.status}</span></td>
      <td>${log.user_approved === true ? '<span style="color:var(--accent-green)">&#10003;</span>' : log.user_approved === false ? '<span style="color:var(--accent-red)">&#10007;</span>' : '<span style="color:#fff">--</span>'}</td>
    </tr>
  `).join('');
}

function renderReviewItem(item) {
  return `
    <div class="review-item">
      <div class="review-header">
        <span style="font-weight:600;font-size:13px">${escapeHtml(item.category || 'Unknown')} / ${escapeHtml(item.urgency || 'Unknown')}</span>
        <span style="font-size:11px;color:var(--text-muted)">${Math.round((item.confidence || 0) * 100)}% confident</span>
      </div>
      <div class="review-ticket">${escapeHtml(item.ticket)}</div>
      <div class="review-reason">&#9873; ${item.error || 'Low confidence — flagged for human review'}</div>
    </div>
  `;
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);

  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
  });

  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  html = html.replace(/### ([^\n]+)/g, '<h3>$1</h3>');
  html = html.replace(/## ([^\n]+)/g, '<h2>$1</h2>');
  html = html.replace(/# ([^\n]+)/g, '<h1>$1</h1>');

  html = html.replace(/\n---\n/g, '\n<hr>\n');

  html = html.replace(/^\*\*(.+?)\*\*[ \t]*(.*)$/gm, (_, bold, rest) => {
    return `<div class="product-section"><strong>${bold}</strong>${rest ? ' ' + rest : ''}</div>`;
  });

  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  html = html.replace(/^- ([^\n]+)/gm, '<li class="ul">$1</li>');
  html = html.replace(/((?:<li class="ul">.*<\/li>\n?)+)/g, '<ul>$1</ul>');
  html = html.replace(/<li class="ul">/g, '<li>');

  html = html.replace(/^\d+\. ([^\n]+)/gm, '<li class="ol">$1</li>');
  html = html.replace(/((?:<li class="ol">.*<\/li>\n?)+)/g, '<ol>$1</ol>');
  html = html.replace(/<li class="ol">/g, '<li>');

  html = html.replace(/\|(.+)\|/g, (match) => {
    const cells = match.split('|').filter(c => c.trim());
    if (cells.every(c => /^[-:\s]+$/.test(c.trim()))) return '';
    return '<tr><td>' + cells.join('</td><td>') + '</td></tr>';
  });

  html = html.replace(/((?:<tr>.*?(?:<\/tr>)\s?)+)/g, '<table>$1</table>');

  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p><\/?ul>/g, '');
  html = html.replace(/<\/ul><\/p>/g, '</ul>');
  html = html.replace(/<p><\/?ol>/g, '');
  html = html.replace(/<\/ol><\/p>/g, '</ol>');
  html = html.replace(/<p>\s*<hr>\s*<\/p>/g, '<hr>');
  html = html.replace(/<p><div class="product-section"/g, '<div class="product-section"');
  html = html.replace(/<\/div><\/p>/g, '</div>');

  return html;
}
