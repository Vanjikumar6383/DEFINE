/**
 * Nimad Copilot — Manifest V3 Background Service Worker
 * Handles: install defaults, context menu, platform detection relay,
 *          live caption state routing between content scripts and popup.
 */

const DEFAULT_API_URL = 'http://127.0.0.1:8000';

// ── Install / defaults ───────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(['apiUrl', 'defaultObjective'], (result) => {
    if (!result.apiUrl)          chrome.storage.local.set({ apiUrl: DEFAULT_API_URL });
    if (!result.defaultObjective) chrome.storage.local.set({ defaultObjective: 'Strategic Alignment & Decision Review' });
  });

  try {
    chrome.contextMenus.create({
      id: 'Nimad-analyze-selection',
      title: 'Analyze with Nimad Copilot',
      contexts: ['selection']
    });
  } catch (err) {
    console.debug('Context menu:', err);
  }
});

// ── Context menu: pre-fill popup transcript from selected text ───────────────
chrome.contextMenus.onClicked.addListener((info, _tab) => {
  if (info.menuItemId === 'Nimad-analyze-selection' && info.selectionText) {
    chrome.storage.local.set({
      pendingTranscript: info.selectionText.trim(),
      pendingTimestamp: Date.now()
    });
  }
});

// ── Live capture state (in-memory, per-tab) ──────────────────────────────────
const liveCaptureState = {
  // tabId → { platform, status, transcript }
};

// ── Message routing ──────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // ── Messages FROM content scripts → relay to popup ──
  if (msg.type === 'PLATFORM_DETECTED') {
    const tabId = sender.tab?.id;
    if (tabId) {
      liveCaptureState[tabId] = {
        ...(liveCaptureState[tabId] || {}),
        platform: msg.platform,
        url: msg.url,
        tabId
      };
      // Update badge
      chrome.action.setBadgeText({ text: platformBadge(msg.platform), tabId });
      chrome.action.setBadgeBackgroundColor({ color: '#00c6a0', tabId });
    }
    // Forward to all popup ports (best-effort)
    forwardToPopup(msg);
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === 'CAPTURE_STATUS') {
    const tabId = sender.tab?.id;
    if (tabId) {
      liveCaptureState[tabId] = {
        ...(liveCaptureState[tabId] || {}),
        status: msg.status,
        platform: msg.platform,
        lastMessage: msg.message,
        tabId
      };
      const badge = msg.status === 'capturing' ? '🔴' : msg.status === 'waiting' ? '⏳' : '';
      chrome.action.setBadgeText({ text: badge, tabId }).catch(() => {});
    }
    forwardToPopup(msg);
    sendResponse({ ok: true });
    return true;
  }

  if (msg.type === 'LIVE_CAPTION_UPDATE') {
    const tabId = sender.tab?.id;
    if (tabId && liveCaptureState[tabId]) {
      liveCaptureState[tabId].transcript = msg.formatted;
      liveCaptureState[tabId].lineCount = msg.buffer?.length || 0;
    }
    // Store latest transcript in chrome.storage for popup to read on open
    chrome.storage.local.set({
      liveTranscript: msg.formatted,
      liveTranscriptPlatform: msg.platform,
      liveTranscriptUpdatedAt: Date.now()
    });
    forwardToPopup(msg);
    sendResponse({ ok: true });
    return true;
  }

  // ── Messages FROM popup → send to active meeting tab ──
  if (msg.type === 'POPUP_COMMAND') {
    handlePopupCommand(msg, sendResponse);
    return true; // async
  }

  // ── Popup requesting current state ──
  if (msg.type === 'GET_ACTIVE_CAPTURE_STATE') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0]?.id;
      const state = tabId ? liveCaptureState[tabId] : null;
      sendResponse({ ok: true, state: state || null, tabId });
    });
    return true;
  }

  sendResponse({ ok: false, reason: 'unknown_message_type' });
  return false;
});

// ── Find Active Meeting Tab (checks current tab, then queries all open tabs) ───
async function findMeetingTab() {
  // 1. Check currently active tab
  const [activeTab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (activeTab?.url && isMeetingUrl(activeTab.url)) {
    return activeTab;
  }

  // 2. Query any open tab with Google Meet, Zoom, or Teams
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
      return tabs[0];
    }
  }

  return activeTab || null;
}

function isMeetingUrl(url) {
  if (!url) return false;
  return url.includes('meet.google.com') ||
         url.includes('zoom.us') ||
         url.includes('teams.microsoft.com') ||
         url.includes('teams.live.com');
}

function getScriptForUrl(url) {
  if (!url) return null;
  if (url.includes('meet.google.com')) return 'content-gmeet.js';
  if (url.includes('zoom.us')) return 'content-zoom.js';
  if (url.includes('teams.')) return 'content-teams.js';
  return null;
}

// ── Command handler (popup → content script with auto-injection) ─────────────
async function handlePopupCommand(msg, sendResponse) {
  try {
    const tab = await findMeetingTab();
    if (!tab?.id) {
      sendResponse({ ok: false, reason: 'No meeting tab found. Open Google Meet, Zoom, or Teams.' });
      return;
    }

    try {
      // First attempt: send message to existing content script
      const response = await chrome.tabs.sendMessage(tab.id, { action: msg.action });
      sendResponse({ ok: true, tabId: tab.id, ...response });
      return;
    } catch (sendErr) {
      // If content script is not yet injected (e.g. page opened before extension reload),
      // dynamically inject it using scripting API!
      const scriptFile = getScriptForUrl(tab.url);
      if (scriptFile) {
        console.log(`[Nimad Service Worker] Injecting ${scriptFile} into tab ${tab.id}…`);
        try {
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: [scriptFile]
          });

          // Wait 150ms for script initialization then retry sending message
          await new Promise(r => setTimeout(r, 150));
          const response = await chrome.tabs.sendMessage(tab.id, { action: msg.action });
          sendResponse({ ok: true, tabId: tab.id, ...response });
          return;
        } catch (injectErr) {
          console.error('[Nimad Service Worker] Script injection failed:', injectErr);
        }
      }
      sendResponse({ ok: false, reason: sendErr.message });
    }
  } catch (err) {
    sendResponse({ ok: false, reason: err.message });
  }
}

// ── Forward message to popup (runtime.sendMessage — popup listens) ────────────
function forwardToPopup(msg) {
  chrome.runtime.sendMessage(msg).catch(() => { /* popup may be closed */ });
}

function platformBadge(platform) {
  const map = { google_meet: 'MEET', zoom: 'ZOOM', teams: 'TEAM' };
  return map[platform] || 'LIVE';
}
