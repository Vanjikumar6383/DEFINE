/**
 * Nimad Copilot — Google Meet Caption Capture Content Script
 * 
 * Accurately extracts real-time closed captions and speaker names from Google Meet,
 * automatically assists with turning on Closed Captions (CC), and renders a sleek
 * in-meeting floating badge with live counters and 1-click transcript export.
 */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let capturing = false;
let captureObserver = null;
let pollInterval = null;
let transcriptBuffer = [];   // [{speaker: string, text: string, ts: number}]
let activeStreams = new Map(); // entryElement -> {speaker, text, ts}
let lastSpeaker = '';
let lastText = '';
let floatingBadgeEl = null;

// ── Google Meet DOM Selectors (Comprehensive 2024–2026 UI + Fallbacks) ───────
// Container for captions
const CONTAINER_SELECTORS = [
  '[role="region"].vNKgIf.UDinHf',        // Current Meet layout
  'div[jscontroller="soHjq"]',            // Controller-based container
  'div.a4cQT',                            // Classic Meet caption container
  'div.iO57B',                            // Alternate layout container
  '[role="region"][aria-label*="aption" i]',
  '[role="region"][aria-label*="subtítulo" i]'
];

// Individual caption utterance blocks
const ENTRY_SELECTORS = [
  '.nMcdL',                               // Current Meet entry block
  '.TBMuR',                               // Alternate entry block
  '[jscontroller][jsmodel]'
];

// Speaker name element within an entry block
const SPEAKER_SELECTORS = [
  '.NWpY1d',                              // Current Meet speaker name
  '.zs75bd',                              // Classic speaker name
  '[data-speaker-name]',
  '.j3vdgc'
];

// Caption text element within an entry block
const TEXT_SELECTORS = [
  '.ygicle',                              // Current Meet caption text
  '.iTTPOb',                              // Classic caption text
  'span[jsname="YS01Ge"]'
];

// CC Toggle button in Google Meet control bar
const CC_BUTTON_SELECTORS = [
  'button[aria-label*="Turn on captions" i]',
  'button[aria-label*="Turn off captions" i]',
  'button[data-tooltip*="Turn on captions" i]',
  'button[data-tooltip*="Turn off captions" i]',
  'button[aria-label*="captions" i]',
  'button[aria-label*="subtítulos" i]',
  'button[data-tooltip*="captions" i]',
  'button[jsname="r8qRAd"]'
];

/** Check if Closed Captions (CC) are currently active in Google Meet */
function isCCActive() {
  // Check if caption container exists and is visible
  const container = findCaptionContainer();
  if (container && container.offsetHeight > 0) return true;

  // Check CC button aria-pressed status
  for (const sel of CC_BUTTON_SELECTORS) {
    const btn = document.querySelector(sel);
    if (btn) {
      const pressed = btn.getAttribute('aria-pressed');
      if (pressed === 'true') return true;
      const label = btn.getAttribute('aria-label') || '';
      if (label.toLowerCase().includes('turn off captions')) return true;
    }
  }
  return false;
}

/** Automatically turn on Closed Captions (CC) in Google Meet if off */
function ensureCCEnabled() {
  if (isCCActive()) return true;

  for (const sel of CC_BUTTON_SELECTORS) {
    const btn = document.querySelector(sel);
    if (btn) {
      const label = (btn.getAttribute('aria-label') || '').toLowerCase();
      const pressed = btn.getAttribute('aria-pressed');
      if (pressed === 'false' || label.includes('turn on') || !pressed) {
        console.log('[Nimad Copilot] Auto-enabling Closed Captions in Google Meet…');
        btn.click();
        return true;
      }
    }
  }

  // Keyboard shortcut fallback ('c' toggles captions in Meet)
  try {
    const keyEvent = new KeyboardEvent('keydown', {
      key: 'c',
      code: 'KeyC',
      keyCode: 67,
      which: 67,
      bubbles: true,
      cancelable: true
    });
    document.dispatchEvent(keyEvent);
  } catch (_) {}

  return false;
}

/** Find the main Google Meet captions container */
function findCaptionContainer() {
  for (const sel of CONTAINER_SELECTORS) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  // Fallback: search for any element containing .ygicle or .nMcdL
  const textEl = document.querySelector('.ygicle, .nMcdL');
  if (textEl) {
    return textEl.closest('[role="region"]') || textEl.parentElement?.parentElement || null;
  }
  return null;
}

/** Extract speaker name and caption text from an entry block */
function parseCaptionEntry(entry) {
  if (!entry) return null;

  // 1. Speaker
  let speaker = '';
  for (const sel of SPEAKER_SELECTORS) {
    const spkEl = entry.querySelector(sel);
    if (spkEl && spkEl.textContent.trim()) {
      speaker = spkEl.textContent.trim();
      break;
    }
  }

  // Fallback to avatar image alt text
  if (!speaker) {
    const avatarImg = entry.querySelector('img[alt]');
    if (avatarImg && avatarImg.getAttribute('alt')) {
      const alt = avatarImg.getAttribute('alt').trim();
      if (alt && !alt.toLowerCase().includes('avatar') && !alt.toLowerCase().includes('profile')) {
        speaker = alt;
      }
    }
  }

  // 2. Text
  let text = '';
  for (const sel of TEXT_SELECTORS) {
    const txtEl = entry.querySelector(sel);
    if (txtEl && txtEl.textContent.trim()) {
      text = txtEl.textContent.trim();
      break;
    }
  }

  // Fallback: extract all spans excluding speaker
  if (!text) {
    const allSpans = Array.from(entry.querySelectorAll('span'));
    if (allSpans.length > 1) {
      text = allSpans.slice(1).map(s => s.textContent.trim()).join(' ').trim();
    } else if (allSpans.length === 1) {
      text = allSpans[0].textContent.trim();
    }
  }

  if (!text || text.length < 2) return null;

  return {
    speaker: speaker || lastSpeaker || 'Participant',
    text: text
  };
}

/** Scrape all caption entries currently rendered in the Meet UI */
function extractAllCaptions() {
  if (!capturing) return;

  const container = findCaptionContainer();
  let entries = [];

  if (container) {
    for (const sel of ENTRY_SELECTORS) {
      const found = container.querySelectorAll(sel);
      if (found.length > 0) {
        entries = Array.from(found);
        break;
      }
    }
    if (entries.length === 0 && container.children.length > 0) {
      entries = Array.from(container.children);
    }
  } else {
    // Search document for .nMcdL or .ygicle anywhere
    const found = document.querySelectorAll('.nMcdL, .TBMuR');
    if (found.length > 0) {
      entries = Array.from(found);
    }
  }

  if (entries.length === 0) {
    // If captions container is missing, verify CC status
    if (!isCCActive()) {
      updateFloatingBadgeStatus('waiting_cc');
    }
    return;
  }

  updateFloatingBadgeStatus('active');

  for (const entry of entries) {
    const parsed = parseCaptionEntry(entry);
    if (!parsed) continue;

    processCaptionStream(entry, parsed.speaker, parsed.text);
  }
}

/** Process a caption stream, deduplicating progressive live speech */
function processCaptionStream(entryKey, speaker, text) {
  const existing = activeStreams.get(entryKey);

  if (existing && existing.speaker === speaker && existing.text === text) {
    return; // No change
  }

  activeStreams.set(entryKey, { speaker, text, ts: Date.now() });

  // Update transcript buffer
  if (transcriptBuffer.length > 0) {
    const lastEntry = transcriptBuffer[transcriptBuffer.length - 1];

    // If same speaker and new text is an extension or update of the last line
    const isSameSpeaker = lastEntry.speaker === speaker;
    const isExtension = text.startsWith(lastEntry.text.substring(0, Math.min(15, lastEntry.text.length))) ||
                        lastEntry.text.startsWith(text.substring(0, Math.min(15, text.length)));

    if (isSameSpeaker && isExtension) {
      lastEntry.text = text;
      lastEntry.ts = Date.now();
      lastText = text;
      broadcastUpdate();
      updateFloatingBadgeCount();
      return;
    }
  }

  // Different speaker or brand new utterance: push new line
  transcriptBuffer.push({
    speaker: speaker,
    text: text,
    ts: Date.now()
  });

  lastSpeaker = speaker;
  lastText = text;

  broadcastUpdate();
  updateFloatingBadgeCount();
}

/** Broadcast live update to background and popup */
function broadcastUpdate() {
  try {
    chrome.runtime.sendMessage({
      type: 'LIVE_CAPTION_UPDATE',
      platform: 'google_meet',
      buffer: transcriptBuffer,
      formatted: formatTranscript()
    });
  } catch (_) {}
}

/** Format transcript into clean readable text */
function formatTranscript() {
  return transcriptBuffer
    .map(l => `[${l.speaker}]: ${l.text}`)
    .join('\n');
}

/** Start live caption capture */
function startCapture() {
  if (capturing) return;
  capturing = true;
  transcriptBuffer = [];
  activeStreams.clear();
  lastText = '';
  lastSpeaker = '';

  // Auto-enable Closed Captions in Meet if off
  ensureCCEnabled();

  // Create on-screen floating badge
  injectFloatingBadge();

  // 1. Mutation Observer on caption container or document.body
  const container = findCaptionContainer() || document.body;
  captureObserver = new MutationObserver(() => {
    extractAllCaptions();
  });

  captureObserver.observe(container, {
    childList: true,
    subtree: true,
    characterData: true
  });

  // Also observe document.body for caption container mount/unmount
  if (container !== document.body) {
    captureObserver.observe(document.body, {
      childList: true,
      subtree: false
    });
  }

  // 2. Backup polling interval every 350ms ensures NO speech is missed
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(extractAllCaptions, 350);

  // Initial immediate extraction
  extractAllCaptions();

  const ccOn = isCCActive();
  chrome.runtime.sendMessage({
    type: 'CAPTURE_STATUS',
    status: ccOn ? 'capturing' : 'waiting',
    platform: 'google_meet',
    message: ccOn
      ? 'Live caption capture active in Google Meet.'
      : 'Waiting for captions. Please enable CC in Meet (press "c" or click the CC button at bottom).'
  }).catch(() => {});
}

/** Stop live capture */
function stopCapture() {
  capturing = false;

  if (captureObserver) {
    captureObserver.disconnect();
    captureObserver = null;
  }
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }

  updateFloatingBadgeStatus('stopped');

  chrome.runtime.sendMessage({
    type: 'CAPTURE_STATUS',
    status: 'stopped',
    platform: 'google_meet',
    transcript: formatTranscript(),
    lineCount: transcriptBuffer.length
  }).catch(() => {});
}

/** Clear buffer */
function clearBuffer() {
  transcriptBuffer = [];
  activeStreams.clear();
  lastText = '';
  lastSpeaker = '';
  updateFloatingBadgeCount();
}

/** Export active transcript directly from the page as .txt */
function exportTranscriptFile() {
  if (transcriptBuffer.length === 0) {
    alert('No transcript captured yet to export.');
    return;
  }

  const meetingUrl = window.location.href;
  const now = new Date().toLocaleString();
  let content = `Nimad MEETING TRANSCRIPT — GOOGLE MEET\nDate: ${now}\nMeeting URL: ${meetingUrl}\n${'═'.repeat(60)}\n\n`;
  content += formatTranscript();

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Nimad-transcript-meet-${Date.now()}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ── In-Meeting Floating Overlay Badge ───────────────────────────────────────
function injectFloatingBadge() {
  if (document.getElementById('Nimad-meet-badge')) return;

  floatingBadgeEl = document.createElement('div');
  floatingBadgeEl.id = 'Nimad-meet-badge';
  floatingBadgeEl.style.cssText = `
    position: fixed;
    bottom: 90px;
    left: 24px;
    z-index: 999999;
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(15, 23, 42, 0.92);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(59, 130, 246, 0.5);
    border-radius: 9999px;
    padding: 6px 14px;
    color: #f8fafc;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 12px;
    font-weight: 500;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    transition: all 0.2s ease;
  `;

  floatingBadgeEl.innerHTML = `
    <span id="Nimad-badge-dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#10b981;box-shadow:0 0 6px #10b981;animation:Nimad-pulse 1.8s infinite;"></span>
    <span style="font-weight:700;color:#60a5fa">Nimad:</span>
    <span id="Nimad-badge-status">Live Transcribing</span>
    <span id="Nimad-badge-count" style="background:#1e293b;padding:2px 8px;border-radius:9999px;font-family:monospace;font-size:11px;color:#94a3b8">0 lines</span>
    <button id="Nimad-badge-enable-cc" style="display:none;background:#f59e0b;color:#0f172a;border:none;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;cursor:pointer">Turn ON CC</button>
    <button id="Nimad-badge-export" style="background:#2563eb;color:#fff;border:none;border-radius:4px;padding:2px 8px;font-size:11px;cursor:pointer" title="Export captured transcript as .txt">💾 Export</button>
    <button id="Nimad-badge-close" style="background:transparent;border:none;color:#94a3b8;font-size:13px;cursor:pointer;padding:0 2px" title="Hide badge">×</button>
  `;

  // Append keyframe animation
  if (!document.getElementById('Nimad-styles')) {
    const style = document.createElement('style');
    style.id = 'Nimad-styles';
    style.textContent = `
      @keyframes Nimad-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.9); }
      }
    `;
    document.head.appendChild(style);
  }

  document.body.appendChild(floatingBadgeEl);

  // Button actions
  floatingBadgeEl.querySelector('#Nimad-badge-enable-cc').addEventListener('click', () => {
    ensureCCEnabled();
  });

  floatingBadgeEl.querySelector('#Nimad-badge-export').addEventListener('click', () => {
    exportTranscriptFile();
  });

  floatingBadgeEl.querySelector('#Nimad-badge-close').addEventListener('click', () => {
    floatingBadgeEl.style.display = 'none';
  });
}

function updateFloatingBadgeCount() {
  const countEl = document.getElementById('Nimad-badge-count');
  if (countEl) {
    const len = transcriptBuffer.length;
    countEl.textContent = `${len} line${len !== 1 ? 's' : ''}`;
  }
}

function updateFloatingBadgeStatus(status) {
  const statusEl = document.getElementById('Nimad-badge-status');
  const dotEl = document.getElementById('Nimad-badge-dot');
  const ccBtn = document.getElementById('Nimad-badge-enable-cc');
  if (!statusEl || !dotEl) return;

  if (status === 'waiting_cc') {
    statusEl.textContent = 'CC is OFF';
    statusEl.style.color = '#f59e0b';
    dotEl.style.background = '#f59e0b';
    dotEl.style.boxShadow = '0 0 6px #f59e0b';
    if (ccBtn) ccBtn.style.display = 'inline-block';
  } else if (status === 'active') {
    statusEl.textContent = 'Live Transcribing';
    statusEl.style.color = '#f8fafc';
    dotEl.style.background = '#10b981';
    dotEl.style.boxShadow = '0 0 6px #10b981';
    if (ccBtn) ccBtn.style.display = 'none';
  } else if (status === 'stopped') {
    statusEl.textContent = 'Capture Stopped';
    statusEl.style.color = '#94a3b8';
    dotEl.style.background = '#64748b';
    dotEl.style.boxShadow = 'none';
    if (ccBtn) ccBtn.style.display = 'none';
  }
}

// ── Message Listener ───────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.action) {
    case 'Nimad_START_CAPTURE':
      startCapture();
      sendResponse({ ok: true, status: capturing ? 'capturing' : 'waiting', ccActive: isCCActive() });
      break;
    case 'Nimad_STOP_CAPTURE':
      stopCapture();
      sendResponse({ ok: true, transcript: formatTranscript(), lines: transcriptBuffer.length });
      break;
    case 'Nimad_GET_TRANSCRIPT':
      sendResponse({ ok: true, transcript: formatTranscript(), lines: transcriptBuffer.length, capturing });
      break;
    case 'Nimad_CLEAR_TRANSCRIPT':
      clearBuffer();
      sendResponse({ ok: true });
      break;
    case 'Nimad_TOGGLE_CC':
      ensureCCEnabled();
      sendResponse({ ok: true, ccActive: isCCActive() });
      break;
    case 'Nimad_EXPORT_TRANSCRIPT':
      exportTranscriptFile();
      sendResponse({ ok: true });
      break;
    case 'Nimad_PING':
      sendResponse({ ok: true, platform: 'google_meet', url: window.location.href, capturing, ccActive: isCCActive() });
      break;
    default:
      break;
  }
  return true;
});

// Announce presence to background
chrome.runtime.sendMessage({
  type: 'PLATFORM_DETECTED',
  platform: 'google_meet',
  url: window.location.href
}).catch(() => {});

console.log('[Nimad Copilot] Google Meet live caption capture script initialized.');
