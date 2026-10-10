/**
 * Nimad Copilot — Chrome Extension Popup Controller
 * Connects directly to the existing Nimad FastAPI backend.
 */

const DEFAULT_API_URL = 'http://127.0.0.1:8000';

let currentApiUrl = DEFAULT_API_URL;
let currentAuthToken = null;
let currentActiveSessionId = null;

// ── DOM ELEMENTS ──
const connectionPill = document.getElementById('connection-pill');
const connectionText = document.getElementById('connection-text');
const btnOpenDashboard = document.getElementById('btn-open-dashboard');
const btnOpenSettings = document.getElementById('btn-open-settings');
const authSection = document.getElementById('auth-section');
const mainContent = document.getElementById('main-content');
const userDisplayName = document.getElementById('user-display-name');
const btnLogout = document.getElementById('btn-logout');
const noticeBox = document.getElementById('notice-box');
const noticeText = document.getElementById('notice-text');

const inputObjective = document.getElementById('input-objective');
const inputTitle = document.getElementById('input-title');
const inputTranscript = document.getElementById('input-transcript');
const transcriptStats = document.getElementById('transcript-stats');
const btnClearTranscript = document.getElementById('btn-clear-transcript');
const btnPasteSample = document.getElementById('btn-paste-sample');
const btnAnalyze = document.getElementById('btn-analyze');
const btnAnalyzeText = document.getElementById('btn-analyze-text');

const resultsSection = document.getElementById('results-section');
const btnOpenWorkspace = document.getElementById('btn-open-workspace');
const resultsSessionBadge = document.getElementById('results-session-badge');

const countReplies = document.getElementById('count-replies');
const countInsights = document.getElementById('count-insights');
const countDecisions = document.getElementById('count-decisions');
const countActions = document.getElementById('count-actions');

const paneReplies = document.getElementById('pane-replies');
const paneInsights = document.getElementById('pane-insights');
const paneDecisions = document.getElementById('pane-decisions');
const paneActions = document.getElementById('pane-actions');
const paneSummary = document.getElementById('pane-summary');
const summaryText = document.getElementById('summary-text');
const btnCopySummary = document.getElementById('btn-copy-summary');

const listReplies = document.getElementById('list-replies');
const listInsights = document.getElementById('list-insights');
const listDecisions = document.getElementById('list-decisions');
const listActions = document.getElementById('list-actions');

const recentList = document.getElementById('recent-list');
const btnRefreshSessions = document.getElementById('btn-refresh-sessions');
const footerEndpointText = document.getElementById('footer-endpoint-text');
const linkOptions = document.getElementById('link-options');
const linkHelp = document.getElementById('link-help');

// ── LIVE CAPTURE DOM ELEMENTS ──
const livePanel               = document.getElementById('live-panel');
const livePlatformBadge       = document.getElementById('live-platform-badge');
const liveNoMeeting           = document.getElementById('live-no-meeting');
const livePlatformLabel       = document.getElementById('live-platform-label');
const liveControls            = document.getElementById('live-controls');
const btnStartCapture         = document.getElementById('btn-start-capture');
const btnStopCapture          = document.getElementById('btn-stop-capture');
const liveStatusMsg           = document.getElementById('live-status-msg');
const btnToggleMeetCc         = document.getElementById('btn-toggle-meet-cc');
const liveTranscriptContainer = document.getElementById('live-transcript-container');
const liveTranscriptFeed      = document.getElementById('live-transcript-feed');
const liveLineCount           = document.getElementById('live-line-count');
const btnClearLive            = document.getElementById('btn-clear-live');
const btnExportLiveTxt        = document.getElementById('btn-export-live-txt');
const btnExportLiveMd         = document.getElementById('btn-export-live-md');
const btnCopyLive             = document.getElementById('btn-copy-live');
const btnUseLiveTranscript    = document.getElementById('btn-use-live-transcript');
const liveIndicatorDot        = document.getElementById('live-indicator-dot');

let livePlatform     = null; // 'google_meet' | 'zoom' | 'teams'
let liveCapturing    = false;
let liveLines        = [];   // [{speaker, text}]

// ── INITIALIZATION ──
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  setupLiveCaptureListeners();
  await loadStoredConfig();
  await checkBackendAndAuth();
  await detectActiveMeetingTab();
});

function setupEventListeners() {
  btnOpenDashboard.addEventListener('click', openDashboard);
  btnOpenSettings.addEventListener('click', () => chrome.runtime.openOptionsPage());
  linkOptions.addEventListener('click', (e) => { e.preventDefault(); chrome.runtime.openOptionsPage(); });
  linkHelp.addEventListener('click', (e) => { e.preventDefault(); chrome.runtime.openOptionsPage(); });

  // Login form
  document.getElementById('popup-login-form').addEventListener('submit', handleLogin);
  document.getElementById('btn-login-demo').addEventListener('click', () => {
    document.getElementById('login-email').value = 'demo@copilot.ai';
    document.getElementById('login-password').value = 'demopassword123';
  });
  btnLogout.addEventListener('click', handleLogout);

  // Quick objective chips
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      inputObjective.value = chip.dataset.obj;
    });
  });

  // Transcript character counters
  inputTranscript.addEventListener('input', updateTranscriptStats);
  btnClearTranscript.addEventListener('click', () => {
    inputTranscript.value = '';
    updateTranscriptStats();
  });
  btnPasteSample.addEventListener('click', insertSampleTranscript);

  // Analyze button
  btnAnalyze.addEventListener('click', runConversationAnalysis);

  // Results Tab Switching
  document.querySelectorAll('.res-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.res-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.res-tab-pane').forEach(p => p.style.display = 'none');
      tab.classList.add('active');
      const targetPane = document.getElementById(`pane-${tab.dataset.tab}`);
      if (targetPane) targetPane.style.display = 'flex';
    });
  });

  // Open Workspace
  btnOpenWorkspace.addEventListener('click', () => {
    if (currentActiveSessionId) {
      chrome.tabs.create({ url: `${currentApiUrl}/session/${currentActiveSessionId}` });
    } else {
      openDashboard();
    }
  });

  btnCopySummary.addEventListener('click', () => {
    copyToClipboard(summaryText.textContent, btnCopySummary, 'Summary Copied!');
  });

  btnRefreshSessions.addEventListener('click', loadRecentSessions);
}

// ── LIVE CAPTURE EVENT LISTENERS ──
function setupLiveCaptureListeners() {
  // Start capture
  btnStartCapture.addEventListener('click', async () => {
    try {
      const resp = await chrome.runtime.sendMessage({
        type: 'POPUP_COMMAND',
        action: 'Nimad_START_CAPTURE'
      });
      if (resp?.ok) {
        setLiveCaptureUI('waiting');
      } else {
        showLiveStatus('Could not reach the meeting tab. Make sure the meeting is open in another tab.', 'warn');
      }
    } catch (err) {
      showLiveStatus('Error: ' + err.message, 'warn');
    }
  });

  // Stop capture
  btnStopCapture.addEventListener('click', async () => {
    try {
      await chrome.runtime.sendMessage({ type: 'POPUP_COMMAND', action: 'Nimad_STOP_CAPTURE' });
      setLiveCaptureUI('stopped');
    } catch (_) {
      setLiveCaptureUI('stopped');
    }
  });

  // Clear live buffer
  btnClearLive.addEventListener('click', () => {
    liveLines = [];
    renderLiveFeed();
    chrome.runtime.sendMessage({ type: 'POPUP_COMMAND', action: 'Nimad_CLEAR_TRANSCRIPT' }).catch(() => {});
  });

  // Use live transcript → paste into the analyze textarea
  btnUseLiveTranscript.addEventListener('click', () => {
    const formatted = liveLines.map(l => `[${l.speaker}]: ${l.text}`).join('\n');
    if (formatted.trim()) {
      inputTranscript.value = formatted;
      updateTranscriptStats();
      // Scroll down to the analyze button
      inputTranscript.scrollIntoView({ behavior: 'smooth', block: 'center' });
      showLiveStatus(`${liveLines.length} lines copied to analysis input. Click "Analyze Conversation" below.`, 'info');
    }
  });

  // Export Live Transcript as TXT
  btnExportLiveTxt.addEventListener('click', () => {
    if (liveLines.length === 0) {
      showLiveStatus('No transcript lines captured yet to export.', 'warn');
      return;
    }
    const formatted = liveLines.map(l => `[${l.speaker}]: ${l.text}`).join('\n');
    const header = `Nimad MEETING TRANSCRIPT\nPlatform: ${livePlatform || 'Live Meeting'}\nDate: ${new Date().toLocaleString()}\nLines: ${liveLines.length}\n${'═'.repeat(60)}\n\n`;
    downloadTextFile(header + formatted, `meeting-transcript-${livePlatform || 'live'}-${Date.now()}.txt`);
    showLiveStatus('Transcript downloaded as .txt file!', 'info');
  });

  // Export Live Transcript as Markdown
  btnExportLiveMd.addEventListener('click', () => {
    if (liveLines.length === 0) {
      showLiveStatus('No transcript lines captured yet to export.', 'warn');
      return;
    }
    const header = `# Meeting Transcript — ${livePlatform || 'Live Meeting'}\n\n**Date:** ${new Date().toLocaleString()}  \n**Total Utterances:** ${liveLines.length}\n\n---\n\n`;
    const formatted = liveLines.map(l => `> **${l.speaker}:** ${l.text}\n`).join('\n');
    downloadTextFile(header + formatted, `meeting-transcript-${livePlatform || 'live'}-${Date.now()}.md`);
    showLiveStatus('Transcript downloaded as Markdown file!', 'info');
  });

  // Copy Live Transcript to Clipboard
  btnCopyLive.addEventListener('click', () => {
    if (liveLines.length === 0) {
      showLiveStatus('No transcript lines to copy.', 'warn');
      return;
    }
    const formatted = liveLines.map(l => `[${l.speaker}]: ${l.text}`).join('\n');
    copyToClipboard(formatted, btnCopyLive, '✓');
    showLiveStatus('Copied live transcript to clipboard!', 'info');
  });

  // Turn ON CC in Meeting
  btnToggleMeetCc.addEventListener('click', async () => {
    try {
      await chrome.runtime.sendMessage({ type: 'POPUP_COMMAND', action: 'Nimad_TOGGLE_CC' });
      showLiveStatus('Sent request to turn ON Closed Captions in Google Meet.', 'info');
    } catch (_) {}
  });

  // Listen for messages from content scripts (relayed by background.js)
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'PLATFORM_DETECTED') {
      handlePlatformDetected(msg);
    } else if (msg.type === 'CAPTURE_STATUS') {
      handleCaptureStatus(msg);
    } else if (msg.type === 'LIVE_CAPTION_UPDATE') {
      handleLiveCaptionUpdate(msg);
    }
  });
}

function downloadTextFile(content, filename) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ── CONFIG & HEALTH ──
async function loadStoredConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get([
      'apiUrl',
      'authToken',
      'pendingTranscript',
      'defaultObjective'
    ], (stored) => {
      currentApiUrl = (stored.apiUrl || DEFAULT_API_URL).replace(/\/+$/, '');
      currentAuthToken = stored.authToken || null;

      try {
        const urlObj = new URL(currentApiUrl);
        footerEndpointText.textContent = urlObj.host;
      } catch (_) {
        footerEndpointText.textContent = currentApiUrl;
      }

      if (stored.defaultObjective && !inputObjective.value) {
        inputObjective.value = stored.defaultObjective;
      }

      // Check if context menu saved a pending transcript selection
      if (stored.pendingTranscript) {
        inputTranscript.value = stored.pendingTranscript;
        updateTranscriptStats();
        // Clear pending so it's not pasted again
        chrome.storage.local.remove(['pendingTranscript']);
      }

      resolve();
    });
  });
}

async function checkBackendAndAuth() {
  setConnectionStatus('checking', 'Connecting…');
  hideNotice();

  try {
    const healthResp = await fetch(`${currentApiUrl}/healthz`, { method: 'GET', cache: 'no-cache' });
    if (!healthResp.ok) throw new Error(`HTTP ${healthResp.status}`);
    setConnectionStatus('connected', 'Connected');
  } catch (err) {
    setConnectionStatus('disconnected', 'Offline');
    showNotice(`Cannot reach Nimad backend at ${currentApiUrl}. Make sure the server is running on 127.0.0.1:8000.`);
    return;
  }

  // Check authentication
  if (!currentAuthToken) {
    showAuthSection();
    return;
  }

  try {
    const userResp = await fetch(`${currentApiUrl}/api/v1/auth/me`, {
      headers: { 'Authorization': `Bearer ${currentAuthToken}` }
    });
    if (userResp.ok) {
      const user = await userResp.json();
      showMainSection(user);
      loadRecentSessions();
    } else {
      // Token invalid or expired
      currentAuthToken = null;
      chrome.storage.local.remove(['authToken']);
      showAuthSection();
    }
  } catch (err) {
    showNotice(`Authentication check failed: ${err.message}`);
    showAuthSection();
  }
}

function setConnectionStatus(status, label) {
  connectionPill.className = `status-pill status-${status}`;
  connectionText.textContent = label;
}

function showAuthSection() {
  authSection.style.display = 'block';
  mainContent.style.display = 'none';
}

function showMainSection(user) {
  authSection.style.display = 'none';
  mainContent.style.display = 'flex';
  userDisplayName.textContent = user.display_name || user.email || 'Authenticated User';
}

// ── AUTHENTICATION ──
async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn = document.getElementById('btn-login-submit');
  const errorBox = document.getElementById('auth-error-msg');

  errorBox.style.display = 'none';
  btn.disabled = true;
  btn.textContent = 'Signing in…';

  try {
    const resp = await fetch(`${currentApiUrl}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      throw new Error(data.detail || `Sign in failed (HTTP ${resp.status})`);
    }

    const authData = await resp.json();
    currentAuthToken = authData.access_token;
    await chrome.storage.local.set({ authToken: currentAuthToken });

    showMainSection(authData.user || { email });
    loadRecentSessions();
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In';
  }
}

async function handleLogout() {
  currentAuthToken = null;
  await chrome.storage.local.remove(['authToken']);
  showAuthSection();
}

// ── TRANSCRIPT & ANALYSIS ──
function updateTranscriptStats() {
  const chars = inputTranscript.value.length;
  const words = inputTranscript.value.trim() ? inputTranscript.value.trim().split(/\s+/).length : 0;
  transcriptStats.textContent = `${chars} chars • ${words} words`;
}

function insertSampleTranscript() {
  inputObjective.value = 'Enterprise Pricing & Pilot Approval';
  inputTitle.value = 'Zoom Technical Review with Acme Corp';
  inputTranscript.value = `[Sarah Chen (VP Eng)]: Good morning. Thanks for jumping on. Today we want to evaluate Nimad for 250 enterprise seats. What is your pricing tier and is there a pilot option?
[Host]: We offer enterprise licensing with dedicated SLA support, and we have a 30-day proof-of-concept pilot program.
[David Miller (Procurement)]: SOC2 Type II compliance is mandatory for our vendor audit. Do you have encryption at rest and in transit?
[Host]: Yes, we are fully SOC2 Type II compliant with AES-256 encryption at rest and TLS 1.3 in transit.
[Sarah Chen (VP Eng)]: Can this integrate directly with our Slack channels and custom webhooks?
[Host]: Absolutely, native webhooks and Slack notifications are supported out of the box.
[David Miller (Procurement)]: Excellent. If we approve the trial agreement by Thursday, we will initiate pilot onboarding next Monday.`;
  updateTranscriptStats();
}

async function runConversationAnalysis() {
  const text = inputTranscript.value.trim();
  if (!text) {
    showNotice('Please enter or paste meeting transcript text before running analysis.');
    inputTranscript.focus();
    return;
  }

  hideNotice();
  setLoadingState(true);

  try {
    const title = inputTitle.value.trim() || `Extension Meeting (${new Date().toLocaleTimeString()})`;
    const objective = inputObjective.value.trim() || 'General Business Meeting';

    // Step 1: Import Transcript to create a session in the existing backend
    const importPayload = {
      title,
      objective,
      content: text,          // backend TranscriptImportRequest uses 'content'
      import_method: 'paste', // import_method: 'paste' | 'url' | 'file'
      platform_source: 'manual_paste'
    };

    const importResp = await fetch(`${currentApiUrl}/api/v1/transcripts/import`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify(importPayload)
    });

    if (!importResp.ok) {
      const errData = await importResp.json().catch(() => ({}));
      throw new Error(errData.detail || `Transcript import failed (HTTP ${importResp.status})`);
    }

    const importResult = await importResp.json();
    const sessionId = importResult.session_id;
    currentActiveSessionId = sessionId;

    // Step 2: Run Full Intelligence Analysis Pipeline
    const analyzeResp = await fetch(`${currentApiUrl}/api/v1/sessions/${sessionId}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentAuthToken}`
      },
      body: JSON.stringify({})
    });

    if (!analyzeResp.ok) {
      const errData = await analyzeResp.json().catch(() => ({}));
      throw new Error(errData.detail || `AI analysis failed (HTTP ${analyzeResp.status})`);
    }

    const analysisData = await analyzeResp.json();
    renderAnalysisResults(analysisData, sessionId);
    loadRecentSessions();

  } catch (err) {
    showNotice(`Analysis failed: ${err.message}`);
  } finally {
    setLoadingState(false);
  }
}

function setLoadingState(loading) {
  if (loading) {
    btnAnalyze.disabled = true;
    btnAnalyzeText.innerHTML = '<span class="spinner"></span> Analyzing with AI…';
  } else {
    btnAnalyze.disabled = false;
    btnAnalyzeText.textContent = 'Analyze Conversation with AI';
  }
}

// ── RENDER RESULTS ──
function renderAnalysisResults(data, sessionId) {
  resultsSection.style.display = 'flex';
  resultsSessionBadge.textContent = sessionId.substring(0, 8).toUpperCase();

  const replies = data.smart_response_suggestions || [];
  const insights = data.insights || [];
  const decisions = data.decisions || [];
  const actions = data.action_items || [];
  const summary = data.summary || {};

  countReplies.textContent = replies.length;
  countInsights.textContent = insights.length;
  countDecisions.textContent = decisions.length;
  countActions.textContent = actions.length;

  // 1. Smart Replies
  listReplies.innerHTML = '';
  if (replies.length === 0) {
    listReplies.innerHTML = '<div class="recent-empty">No response suggestions generated.</div>';
  } else {
    replies.forEach((s) => {
      const card = document.createElement('div');
      card.className = 'res-card';
      const textToCopy = s.suggestion_text || s.suggestion || '';
      card.innerHTML = `
        <div class="res-card-top">
          <span class="res-card-title">${escapeHtml(s.title || 'Suggested Reply')}</span>
          <span class="badge" style="color:var(--clr-blue)">RECOMMENDED</span>
        </div>
        <div class="res-card-text">${escapeHtml(textToCopy)}</div>
        ${s.objective_relevance ? `<div class="res-card-meta">🎯 ${escapeHtml(s.objective_relevance)}</div>` : ''}
        ${s.supporting_excerpt ? `<div class="res-card-excerpt">"${escapeHtml(s.supporting_excerpt)}"</div>` : ''}
        <div class="res-card-actions">
          <button class="btn btn-secondary btn-xs copy-btn">📋 Copy Reply</button>
        </div>
      `;
      card.querySelector('.copy-btn').addEventListener('click', (e) => {
        copyToClipboard(textToCopy, e.target, 'Copied!');
      });
      listReplies.appendChild(card);
    });
  }

  // 2. Insights
  listInsights.innerHTML = '';
  if (insights.length === 0) {
    listInsights.innerHTML = '<div class="recent-empty">No insights extracted.</div>';
  } else {
    insights.forEach((ins) => {
      const card = document.createElement('div');
      card.className = 'res-card';
      const content = ins.content || '';
      const alignment = ins.objective_alignment || 'neutral';
      const alignColor = alignment === 'supports_goal' ? 'var(--clr-green)' : alignment === 'risks_goal' ? 'var(--clr-red)' : 'var(--text-muted)';
      const alignLabel = alignment === 'supports_goal' ? 'SUPPORTS GOAL' : alignment === 'risks_goal' ? 'RISKS GOAL' : 'NEUTRAL';
      const excerpt = (ins.evidence_refs?.evidence?.[0]?.excerpt) || '';

      card.innerHTML = `
        <div class="res-card-top">
          <span class="res-card-title">${escapeHtml((ins.type || 'point').toUpperCase())}</span>
          <span class="badge" style="color:${alignColor}">${alignLabel}</span>
        </div>
        <div class="res-card-text">${escapeHtml(content)}</div>
        ${excerpt ? `<div class="res-card-excerpt">"${escapeHtml(excerpt)}"</div>` : ''}
        <div class="res-card-actions">
          <button class="btn btn-secondary btn-xs copy-btn">📋 Copy</button>
        </div>
      `;
      card.querySelector('.copy-btn').addEventListener('click', (e) => {
        copyToClipboard(content, e.target, 'Copied!');
      });
      listInsights.appendChild(card);
    });
  }

  // 3. Decisions
  listDecisions.innerHTML = '';
  if (decisions.length === 0) {
    listDecisions.innerHTML = '<div class="recent-empty">No confirmed decisions detected.</div>';
  } else {
    decisions.forEach((d) => {
      const card = document.createElement('div');
      card.className = 'res-card';
      card.innerHTML = `
        <div class="res-card-top">
          <span class="res-card-title">${escapeHtml(d.category || 'General')}</span>
          <span class="badge" style="color:var(--clr-green)">${escapeHtml(d.status || 'CONFIRMED')}</span>
        </div>
        <div class="res-card-text">${escapeHtml(d.decision_text || d.text || '')}</div>
        ${d.supporting_excerpt ? `<div class="res-card-excerpt">"${escapeHtml(d.supporting_excerpt)}"</div>` : ''}
      `;
      listDecisions.appendChild(card);
    });
  }

  // 4. Action Items
  listActions.innerHTML = '';
  if (actions.length === 0) {
    listActions.innerHTML = '<div class="recent-empty">No action items detected.</div>';
  } else {
    actions.forEach((a) => {
      const card = document.createElement('div');
      card.className = 'res-card';
      card.innerHTML = `
        <div class="res-card-top">
          <span class="res-card-title">✓ ${escapeHtml(a.description)}</span>
          <span class="badge">${escapeHtml((a.priority || 'medium').toUpperCase())}</span>
        </div>
        <div class="res-card-meta">
          <span>👤 ${escapeHtml(a.owner || 'Unassigned')}</span>
          <span>📅 ${escapeHtml(a.due_date || 'No deadline')}</span>
        </div>
      `;
      listActions.appendChild(card);
    });
  }

  // 5. Summary
  summaryText.textContent = summary.summary_text || 'No summary text generated.';
}

// ── RECENT SESSIONS ──
async function loadRecentSessions() {
  if (!currentAuthToken) return;

  try {
    const resp = await fetch(`${currentApiUrl}/api/v1/sessions`, {
      headers: { 'Authorization': `Bearer ${currentAuthToken}` }
    });
    if (!resp.ok) return;

    const sessions = await resp.json();
    recentList.innerHTML = '';

    if (!sessions || sessions.length === 0) {
      recentList.innerHTML = '<div class="recent-empty">No recent meetings recorded yet.</div>';
      return;
    }

    sessions.slice(0, 4).forEach((s) => {
      const item = document.createElement('a');
      item.className = 'recent-item';
      item.href = '#';
      item.title = `Open ${s.title} in Nimad Workspace`;
      
      const timeStr = s.created_at ? new Date(s.created_at).toLocaleDateString() : '';
      item.innerHTML = `
        <span class="recent-item-title">${escapeHtml(s.title || 'Untitled Session')}</span>
        <span class="recent-item-time">${timeStr} ↗</span>
      `;
      item.addEventListener('click', (e) => {
        e.preventDefault();
        chrome.tabs.create({ url: `${currentApiUrl}/session/${s.id}` });
      });
      recentList.appendChild(item);
    });
  } catch (err) {
    console.debug('Failed to load recent sessions:', err);
  }
}

// ── HELPERS ──
function openDashboard() {
  chrome.tabs.create({ url: `${currentApiUrl}/dashboard` });
}

function showNotice(text) {
  noticeText.textContent = text;
  noticeBox.style.display = 'flex';
}

function hideNotice() {
  noticeBox.style.display = 'none';
}

function copyToClipboard(text, btnElement, successLabel = 'Copied!') {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btnElement.textContent;
    btnElement.textContent = successLabel;
    setTimeout(() => { btnElement.textContent = originalText; }, 1800);
  }).catch(() => {
    btnElement.textContent = 'Failed';
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ══════════════════════════════════════════════════════
// LIVE CAPTURE FUNCTIONS
// ══════════════════════════════════════════════════════

const PLATFORM_LABELS = {
  google_meet: { label: 'Google Meet', cls: 'platform-meet', icon: '🟢' },
  zoom:        { label: 'Zoom Web', cls: 'platform-zoom', icon: '🔵' },
  teams:       { label: 'Microsoft Teams', cls: 'platform-teams', icon: '🟣' },
};

/** Check if any open tab is a supported meeting platform */
async function detectActiveMeetingTab() {
  try {
    // Query ALL tabs for meeting URLs (not just active one)
    const meetingPatterns = [
      'https://meet.google.com/*',
      'https://*.zoom.us/j/*',
      'https://*.zoom.us/wc/*',
      'https://teams.microsoft.com/*',
      'https://teams.live.com/*'
    ];

    for (const pattern of meetingPatterns) {
      const tabs = await chrome.tabs.query({ url: pattern });
      if (tabs.length > 0) {
        const tab = tabs[0];
        let platform = 'unknown';
        if (tab.url.includes('meet.google.com'))  platform = 'google_meet';
        else if (tab.url.includes('zoom.us'))     platform = 'zoom';
        else if (tab.url.includes('teams.'))      platform = 'teams';
        handlePlatformDetected({ platform, url: tab.url });
        break;
      }
    }

    // Also restore any liveTranscript that was captured before popup opened
    chrome.storage.local.get(['liveTranscript', 'liveTranscriptPlatform', 'liveTranscriptUpdatedAt'], (stored) => {
      const age = Date.now() - (stored.liveTranscriptUpdatedAt || 0);
      if (stored.liveTranscript && age < 10 * 60 * 1000) { // within 10 min
        const lines = stored.liveTranscript.split('\n').map(l => {
          const m = l.match(/^\[([^\]]+)\]:\s*(.+)$/);
          return m ? { speaker: m[1], text: m[2] } : { speaker: 'Speaker', text: l };
        }).filter(l => l.text.trim());
        if (lines.length > 0) {
          liveLines = lines;
          liveTranscriptContainer.style.display = 'block';
          renderLiveFeed();
        }
      }
    });
  } catch (_) {}
}

function handlePlatformDetected(msg) {
  livePlatform = msg.platform;
  const meta = PLATFORM_LABELS[msg.platform] || { label: msg.platform, cls: '', icon: '🔵' };

  liveNoMeeting.style.display = 'none';
  livePlatformBadge.style.display = 'flex';
  livePlatformLabel.textContent = `${meta.icon} ${meta.label} detected`;
  livePlatformLabel.className = meta.cls;
  liveControls.style.display = 'flex';
  liveIndicatorDot.className = 'live-dot live-dot-inactive';
}

function handleCaptureStatus(msg) {
  if (msg.status === 'capturing') {
    setLiveCaptureUI('capturing');
    showLiveStatus(msg.message || 'Live caption capture active. Speak now.', 'capturing');
    if (btnToggleMeetCc) btnToggleMeetCc.style.display = 'none';
  } else if (msg.status === 'waiting') {
    setLiveCaptureUI('waiting');
    showLiveStatus(msg.message || 'Waiting for captions. Please enable CC in your meeting.', 'warn');
    if (btnToggleMeetCc && (livePlatform === 'google_meet' || !livePlatform)) {
      btnToggleMeetCc.style.display = 'inline-block';
    }
  } else if (msg.status === 'stopped') {
    setLiveCaptureUI('stopped');
    if (btnToggleMeetCc) btnToggleMeetCc.style.display = 'none';
    if (msg.lineCount > 0) {
      showLiveStatus(`Capture stopped. ${msg.lineCount} lines captured. Click "↓ Analyze" to analyze or "💾 TXT" to export.`, 'info');
    } else {
      showLiveStatus('Capture stopped.', 'info');
    }
  }
}

function handleLiveCaptionUpdate(msg) {
  if (!msg.buffer || msg.buffer.length === 0) return;

  // Merge: only add lines we don't have yet
  const prevCount = liveLines.length;
  liveLines = msg.buffer.map(b => ({ speaker: b.speaker, text: b.text }));

  liveTranscriptContainer.style.display = 'block';
  renderLiveFeed(prevCount); // pass previous count so we can highlight new lines
}

function renderLiveFeed(prevCount = 0) {
  liveLineCount.textContent = `${liveLines.length} line${liveLines.length !== 1 ? 's' : ''}`;

  if (liveLines.length === 0) {
    liveTranscriptFeed.innerHTML = '<div class="live-empty">Waiting for speech…</div>';
    return;
  }

  liveTranscriptFeed.innerHTML = '';
  liveLines.forEach((line, idx) => {
    const div = document.createElement('div');
    div.className = 'live-line' + (idx >= prevCount ? ' new-line' : '');
    div.innerHTML = `<span class="live-line-speaker">${escapeHtml(line.speaker)}:</span><span class="live-line-text">${escapeHtml(line.text)}</span>`;
    liveTranscriptFeed.appendChild(div);
  });

  // Auto-scroll to bottom
  liveTranscriptFeed.scrollTop = liveTranscriptFeed.scrollHeight;
}

function setLiveCaptureUI(state) {
  // state: 'idle' | 'waiting' | 'capturing' | 'stopped'
  switch (state) {
    case 'waiting':
      liveCapturing = false;
      btnStartCapture.style.display = 'none';
      btnStopCapture.style.display = 'inline-flex';
      liveIndicatorDot.className = 'live-dot live-dot-waiting';
      liveTranscriptContainer.style.display = 'block';
      break;
    case 'capturing':
      liveCapturing = true;
      btnStartCapture.style.display = 'none';
      btnStopCapture.style.display = 'inline-flex';
      liveIndicatorDot.className = 'live-dot live-dot-active';
      liveTranscriptContainer.style.display = 'block';
      break;
    case 'stopped':
    default:
      liveCapturing = false;
      btnStartCapture.style.display = 'inline-flex';
      btnStopCapture.style.display = 'none';
      liveIndicatorDot.className = 'live-dot live-dot-inactive';
      break;
  }
}

function showLiveStatus(text, type = 'warn') {
  liveStatusMsg.textContent = text;
  liveStatusMsg.className = 'live-status-msg' + (type === 'capturing' ? ' capturing' : '');
  liveStatusMsg.style.display = 'block';
}
