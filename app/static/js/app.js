/* app/static/js/app.js */
/* Local AI Assistant — Main Application */

/* ---- Utility ---- */
const API = 'http://127.0.0.1:18765/api';

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function showStatus(id, text, type = 'neutral') {
  const el = $(`#${id}-status`);
  if (!el) return;
  el.textContent = text;
  el.style.color = type === 'error' ? '#f85149'
    : type === 'success' ? '#3fb950'
    : type === 'loading' ? '#d29922'
    : '#8b949e';
}

function showResult(id, content) {
  const result = $(`#${id}-result`);
  if (!result) return;
  result.style.display = 'block';
  const contentEl = $(`#${id}-content`) || result.querySelector('.result-textarea');
  if (contentEl) {
    if (contentEl.tagName === 'TEXTAREA') {
      contentEl.value = content;
    } else {
      contentEl.innerHTML = escapeHtml(content);
    }
  }
}

function hideResult(id) {
  const result = $(`#${id}-result`);
  if (result) result.style.display = 'none';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function copyResult(id) {
  const contentEl = $(`#${id}-content`);
  if (!contentEl) return;
  const text = contentEl.value || contentEl.textContent;
  navigator.clipboard.writeText(text).then(() => {
    // Brief visual feedback
    const btn = $(`#${id}-result .result-actions .btn-sm`);
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = '✓ Copied';
      setTimeout(() => btn.textContent = orig, 1500);
    }
  });
}

/* ---- Module Switching ---- */
function switchModule(moduleName) {
  // Hide all modules
  $$('.module').forEach(m => m.classList.remove('active'));
  // Show target
  const target = $(`#module-${moduleName}`);
  if (target) target.classList.add('active');

  // Update nav
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  $(`.nav-item[data-module="${moduleName}"]`)?.classList.add('active');
}

$$('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchModule(btn.dataset.module));
});

/* ---- LM Studio Health Check ---- */
async function checkHealth() {
  const dot = $('.status-dot');
  const text = $('.status-text');
  if (!dot || !text) return;

  dot.className = 'status-dot checking';
  text.textContent = 'Checking LM Studio...';

  try {
    const resp = await fetch(`${API}/health`);
    const data = await resp.json();

    if (data.lm_studio === 'ok') {
      dot.className = 'status-dot ok';
      text.textContent = 'LM Studio connected';
    } else {
      dot.className = 'status-dot error';
      text.textContent = 'LM Studio not found';
    }
  } catch {
    dot.className = 'status-dot error';
    text.textContent = 'LM Studio not found';
  }
}

/* ---- Chat History / Session Management ---- */
let currentSessionId = null;

async function loadChatHistory() {
  try {
    const resp = await fetch(`${API}/chat/history`);
    if (!resp.ok) {
      console.error(`Chat history API error: ${resp.status} ${resp.statusText}`);
      renderHistoryList([]);
      return;
    }
    const data = await resp.json();
    renderHistoryList(data.sessions || []);
  } catch (err) {
    console.error('Failed to load chat history:', err);
    renderHistoryList([]);
  }
}

function renderHistoryList(sessions) {
  const container = $('#chat-history-list');
  if (!container) return;
  container.innerHTML = '';

  if (sessions.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'history-empty';
    empty.textContent = 'No sessions yet';
    empty.style.cssText = 'padding:8px 16px;font-size:12px;color:var(--text-muted);font-style:italic;';
    container.appendChild(empty);
    const clearBtn = $('#clear-history-btn');
    if (clearBtn) clearBtn.style.display = 'none';
    return;
  }

  sessions.forEach(session => {
    const btn = document.createElement('button');
    btn.className = 'chat-history-item' + (session.id === currentSessionId ? ' active' : '');
    btn.dataset.sessionId = session.id;

    const msgCount = session.messages ? session.messages.length : 0;

    btn.innerHTML = `
      <span class="history-name" title="${escapeAttr(session.name)}">${escapeHtml(session.name)}</span>
      <span class="history-count">${msgCount} msg${msgCount !== 1 ? 's' : ''}</span>
      <button class="history-delete" title="Delete session" data-session-id="${session.id}">✕</button>
    `;

    btn.addEventListener('click', (e) => {
      if (e.target.classList.contains('history-delete')) return;
      switchSession(session.id);
    });

    const delBtn = btn.querySelector('.history-delete');
    if (delBtn) {
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteSession(session.id);
      });
    }

    container.appendChild(btn);
  });

  const clearBtn = $('#clear-history-btn');
  if (clearBtn) clearBtn.style.display = sessions.length > 0 ? 'flex' : 'none';
}

async function createNewSession() {
  try {
    const resp = await fetch(`${API}/chat/history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Untitled' })
    });
    if (!resp.ok) {
      const errText = await resp.text();
      console.error(`Create session failed (${resp.status}):`, errText);
      return null;
    }
    const data = await resp.json();
    if (data.session) {
      currentSessionId = data.session.id;
      await loadChatHistory();
      updateSessionName(data.session.name);
      clearChatView();
      chatInput.focus();
      return data.session;
    }
    return null;
  } catch (err) {
    console.error('Failed to create session:', err);
    return null;
  }
}

async function switchSession(sessionId) {
  if (sessionId === currentSessionId) return;

  try {
    const resp = await fetch(`${API}/chat/history/${sessionId}`);
    const data = await resp.json();
    if (data.session) {
      currentSessionId = sessionId;
      loadSessionMessages(data.session.messages || []);
      updateSessionName(data.session.name);
      await loadChatHistory(); // refresh active state
    }
  } catch (err) {
    console.error('Failed to load session:', err);
  }
}

function loadSessionMessages(messages) {
  chatMessages.innerHTML = '';

  if (messages.length === 0) {
    const welcome = document.createElement('div');
    welcome.className = 'welcome-message';
    welcome.innerHTML = `
      <div class="welcome-icon">⚡</div>
      <h2>Local AI Assistant</h2>
      <p>Ask me anything — powered by your local LM Studio model.</p>
      <div class="suggestions">
        <button class="suggestion-chip" data-msg="What can you help me with?">What can you help me with?</button>
        <button class="suggestion-chip" data-msg="Explain how RAG works">Explain how RAG works</button>
        <button class="suggestion-chip" data-msg="Summarize my project structure">Summarize my project structure</button>
      </div>
    `;
    chatMessages.appendChild(welcome);
    return;
  }

  messages.forEach(msg => {
    const role = msg.role === 'user' ? 'user' : 'ai';
    addMessage(role, msg.content);
  });

  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function deleteSession(sessionId) {
  if (!confirm('Delete this session? This cannot be undone.')) return;

  try {
    const resp = await fetch(`${API}/chat/history/${sessionId}`, { method: 'DELETE' });
    const data = await resp.json();
    if (data.status === 'deleted') {
      if (currentSessionId === sessionId) {
        currentSessionId = null;
        createNewSession();
      }
      await loadChatHistory();
    }
  } catch (err) {
    console.error('Failed to delete session:', err);
  }
}

async function clearAllSessions() {
  if (!confirm('Delete ALL chat sessions? This cannot be undone.')) return;

  try {
    const resp = await fetch(`${API}/chat/history/clear`, { method: 'POST' });
    const data = await resp.json();
    if (data.status === 'cleared') {
      currentSessionId = null;
      clearChatView();
      updateSessionName('New Session');
      await loadChatHistory();
    }
  } catch (err) {
    console.error('Failed to clear sessions:', err);
  }
}

function updateSessionName(name) {
  const el = $('#current-session-name');
  if (el) el.textContent = name;
}

function clearChatView() {
  chatMessages.innerHTML = '';
  const welcome = document.createElement('div');
  welcome.className = 'welcome-message';
  welcome.innerHTML = `
    <div class="welcome-icon">⚡</div>
    <h2>Local AI Assistant</h2>
    <p>Ask me anything — powered by your local LM Studio model.</p>
    <div class="suggestions">
      <button class="suggestion-chip" data-msg="What can you help me with?">What can you help me with?</button>
      <button class="suggestion-chip" data-msg="Explain how RAG works">Explain how RAG works</button>
      <button class="suggestion-chip" data-msg="Summarize my project structure">Summarize my project structure</button>
    </div>
  `;
  chatMessages.appendChild(welcome);
}

function escapeAttr(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ---- Chat Module ---- */
const chatMessages = $('#chat-messages');
const chatInput = $('#chat-input');
const chatSend = $('#chat-send');

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message ${role}`;

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'You' : 'AI';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.textContent = text;

  div.appendChild(label);
  div.appendChild(bubble);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function addTypingIndicator() {
  const div = document.createElement('div');
  div.className = 'message ai typing';
  div.id = 'typing-indicator';

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = 'AI';

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  bubble.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

  div.appendChild(label);
  div.appendChild(bubble);
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function removeTypingIndicator() {
  const el = $('#typing-indicator');
  if (el) el.remove();
}

async function sendMessage(text) {
  if (!text.trim()) return;

  // Ensure we have a session
  if (!currentSessionId) {
    const session = await createNewSession();
    if (!session) {
      addMessage('error', 'Could not create a session. Is the app connected to the server?');
      return;
    }
  }

  // Hide welcome message
  const welcome = chatMessages.querySelector('.welcome-message');
  if (welcome) welcome.style.display = 'none';

  addMessage('user', text);
  chatInput.value = '';
  chatInput.style.height = 'auto';
  chatSend.disabled = true;

  const typing = addTypingIndicator();

  try {
    const resp = await fetch(`${API}/chat/${currentSessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await resp.json();

    removeTypingIndicator();

    if (data.response) {
      addMessage('ai', data.response);
      await loadChatHistory(); // Refresh sidebar
    } else {
      addMessage('error', `Error: ${data.error || 'Unknown error'}`);
    }
  } catch (err) {
    removeTypingIndicator();
    addMessage('error', `Connection error: ${err.message}\n\nIs LM Studio running?`);
  }

  chatSend.disabled = false;
  chatInput.focus();
}

chatSend.addEventListener('click', () => sendMessage(chatInput.value));

chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(chatInput.value);
  }
});

// Auto-resize textarea
chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
});

// Suggestion chips
$$('.suggestion-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    sendMessage(chip.dataset.msg);
  });
});

/* ---- Email Module ---- */
$('#email-generate')?.addEventListener('click', async () => {
  const topic = $('#email-topic').value.trim();
  const tone = $('#email-tone').value;

  if (!topic) {
    showStatus('email', 'Please describe the email you want to write.', 'error');
    return;
  }

  $('#email-generate').disabled = true;
  showStatus('email', 'Generating email...', 'loading');
  hideResult('email');

  try {
    const resp = await fetch(`${API}/email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, tone })
    });
    const data = await resp.json();

    if (data.response) {
      showResult('email', data.response);
      showStatus('email', `Done! Saved to: ${data.filepath || 'output/'}`, 'success');
    } else {
      showStatus('email', `Error: ${data.error}`, 'error');
    }
  } catch (err) {
    showStatus('email', `Connection error: ${err.message}`, 'error');
  }

  $('#email-generate').disabled = false;
});

/* ---- Quote Generator Module ---- */
let quoteItems = [];

function addQuoteItem() {
  const container = $('#quote-pricing-items');
  if (!container) return;

  const id = Date.now();
  const row = document.createElement('div');
  row.className = 'pricing-row';
  row.dataset.id = id;
  row.innerHTML = `
    <input type="text" class="desc-input" placeholder="Description">
    <input type="number" class="qty-input" placeholder="Qty" value="1" min="1">
    <input type="number" class="price-input" placeholder="Price" value="0.00" step="0.01">
    <button class="remove-item" title="Remove">×</button>
  `;

  row.querySelector('.remove-item').addEventListener('click', () => {
    row.remove();
    recalcQuotePricing();
  });

  row.querySelectorAll('input').forEach(input => {
    input.addEventListener('input', recalcQuotePricing);
  });

  container.appendChild(row);
}

function recalcQuotePricing() {
  const rows = $$('#quote-pricing-items .pricing-row');
  let subtotal = 0;

  rows.forEach(row => {
    const inputs = row.querySelectorAll('input');
    const qty = parseFloat(inputs[1]?.value) || 0;
    const price = parseFloat(inputs[2]?.value) || 0;
    subtotal += qty * price;
  });

  const tax = subtotal * 0.10;
  const total = subtotal + tax;

  // Update or create total display
  let totalEl = $('#quote-pricing-total');
  if (!totalEl) {
    totalEl = document.createElement('div');
    totalEl.id = 'quote-pricing-total';
    totalEl.className = 'pricing-total';
    document.querySelector('#module-quote .form-card')?.appendChild(totalEl);
  }
  totalEl.innerHTML = `
    <span>Subtotal: $${subtotal.toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
    <span>Tax (10%): $${tax.toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
    <span>Total: $${total.toLocaleString('en-US', {minimumFractionDigits: 2})}</span>
  `;
}

$('#quote-add-item')?.addEventListener('click', addQuoteItem);

$('#quote-generate')?.addEventListener('click', async () => {
  const category = $('#quote-category').value;
  const customerName = $('#quote-customer-name').value.trim();
  const customerPhone = $('#quote-customer-phone').value.trim();
  const customerAddress = $('#quote-customer-address').value.trim();
  const servicesDesc = $('#quote-services').value.trim();

  if (!servicesDesc) {
    showStatus('quote', 'Please describe the services you need a quote for.', 'error');
    return;
  }

  // Gather pricing items
  const pricingItems = [];
  $$('#quote-pricing-items .pricing-row').forEach(row => {
    const inputs = row.querySelectorAll('input');
    const desc = inputs[0]?.value.trim();
    const qty = parseFloat(inputs[1]?.value) || 0;
    const price = parseFloat(inputs[2]?.value) || 0;
    if (desc) {
      pricingItems.push({ description: desc, qty, price, total: qty * price });
    }
  });

  $('#quote-generate').disabled = true;
  showStatus('quote', 'Generating quote...', 'loading');
  hideResult('quote');

  try {
    const resp = await fetch(`${API}/quote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category, customerName, customerPhone, customerAddress,
        servicesDesc, pricingItems
      })
    });
    const data = await resp.json();

    if (data.response) {
      showResult('quote', data.response);
      showStatus('quote', `Done! Saved to: ${data.filepath || 'output/'}`, 'success');
    } else {
      showStatus('quote', `Error: ${data.error}`, 'error');
    }
  } catch (err) {
    showStatus('quote', `Connection error: ${err.message}`, 'error');
  }

  $('#quote-generate').disabled = false;
});

/* ---- Business Brain Module ---- */
$('#brain-ask')?.addEventListener('click', async () => {
  const question = $('#brain-question').value.trim();

  if (!question) {
    showStatus('brain', 'Please enter a question.', 'error');
    return;
  }

  $('#brain-ask').disabled = true;
  showStatus('brain', 'Searching documents and generating answer...', 'loading');
  hideResult('brain');

  try {
    const resp = await fetch(`${API}/brain/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });
    const data = await resp.json();

    if (data.response) {
      showResult('brain', data.response);
      showStatus('brain', 'Done', 'success');
    } else if (data.error) {
      showStatus('brain', `Error: ${data.error}`, 'error');
    } else {
      showStatus('brain', 'No answer returned.', 'error');
    }
  } catch (err) {
    showStatus('brain', `Connection error: ${err.message}`, 'error');
  }

  $('#brain-ask').disabled = false;
});

$('#brain-reindex')?.addEventListener('click', async () => {
  $('#brain-reindex').disabled = true;
  showStatus('brain', 'Re-indexing documents...', 'loading');

  try {
    const resp = await fetch(`${API}/brain/reindex`, { method: 'POST' });
    const data = await resp.json();

    if (data.status === 'ok') {
      showStatus('brain', data.message, 'success');
    } else {
      showStatus('brain', `Error: ${data.error}`, 'error');
    }
  } catch (err) {
    showStatus('brain', `Connection error: ${err.message}`, 'error');
  }

  $('#brain-reindex').disabled = false;
});

$('#brain-question').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') $('#brain-ask').click();
});

/* ---- PDF Summarizer Module ---- */
$('#pdf-summarize')?.addEventListener('click', async () => {
  const fileInput = $('#pdf-file');
  if (!fileInput.files.length) {
    showStatus('pdf', 'Please select a PDF file.', 'error');
    return;
  }

  const file = fileInput.files[0];
  const summaryLength = $('#pdf-length').value;
  const plainEnglish = $('#pdf-plain').checked;

  // Read file as base64 to send to API
  const reader = new FileReader();
  reader.onload = async (e) => {
    const base64 = e.target.result.split(',')[1];
    const filename = file.name;

    $('#pdf-summarize').disabled = true;
    showStatus('pdf', 'Processing PDF...', 'loading');
    hideResult('pdf');

    try {
      const resp = await fetch(`${API}/pdf/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_data: base64,
          filename,
          summary_length: summaryLength,
          plain_english: plainEnglish
        })
      });
      const data = await resp.json();

      if (data.response) {
        showResult('pdf', data.response);
        showStatus('pdf', `Done! Saved to: ${data.filepath || 'output/'}`, 'success');
      } else {
        showStatus('pdf', `Error: ${data.error}`, 'error');
      }
    } catch (err) {
      showStatus('pdf', `Connection error: ${err.message}`, 'error');
    }

    $('#pdf-summarize').disabled = false;
  };
  reader.readAsDataURL(file);
});

/* ---- Chat History Event Listeners ---- */
$('#new-session-btn')?.addEventListener('click', createNewSession);
$('#clear-history-btn')?.addEventListener('click', clearAllSessions);

// Rename session
$('#session-rename-btn')?.addEventListener('click', () => {
  if (!currentSessionId) return;
  const currentName = $('#current-session-name')?.textContent || 'Untitled';
  const newName = prompt('Rename session:', currentName);
  if (newName && newName.trim()) {
    fetch(`${API}/chat/history/${currentSessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.trim() })
    }).then(() => {
      updateSessionName(newName.trim());
      loadChatHistory();
    }).catch(err => console.error('Rename failed:', err));
  }
});

/* ---- Init ---- */
checkHealth();
setInterval(checkHealth, 30000); // Re-check every 30s

// Load chat history on startup
loadChatHistory();
