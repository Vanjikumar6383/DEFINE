/**
 * Nimad Copilot — Zoom Web Caption Capture Content Script
 * Captures live captions from Zoom Web Client (app.zoom.us meetings).
 *
 * WORKS WITH: Zoom in-browser meetings (not the desktop app)
 * CAPTION SOURCE: Zoom's subtitle/caption div rendered in the web client DOM.
 * NO AUDIO RECORDING — reads text elements only.
 */

'use strict';

let capturing = false;
let captureObserver = null;
let transcriptBuffer = [];
let lastText = '';
let lastSpeaker = '';

// Zoom Web Client caption selectors (multiple fallbacks for different versions)
const ZOOM_CAPTION_SELECTORS = [
  // Live transcript panel
  '.live-transcription-subtitle',
  '.subtitle-section__text',
  '[class*="subtitle"]',
  '[class*="caption"]',
  '[class*="transcript"]',
  // Closed-caption overlay
  '.closed-caption-container span',
  '[aria-label*="Caption"]',
  '[aria-label*="caption"]',
  // Meeting transcript (when shown as panel)
  '.transcript-participant__name',
  '.transcript-sentence',
];

function findZoomCaptionRoot() {
  for (const sel of ZOOM_CAPTION_SELECTORS) {
    const el = document.querySelector(sel);
    if (el) return el.closest('[class*="caption"], [class*="subtitle"], [class*="transcript"]') || el.parentElement || document.body;
  }
  // Fallback: look for aria-live
  return document.querySelector('[aria-live]') || null;
}

function extractZoomCaption(node) {
  // Zoom transcript format: <div class="speaker-name">Name</div><div class="text">…</div>
  const nameEl = node.querySelector('[class*="name"], [class*="speaker"]');
  const textEl = node.querySelector('[class*="text"], [class*="sentence"], [class*="subtitle"]');
  
  const speaker = nameEl ? nameEl.textContent.trim() : lastSpeaker || 'Speaker';
  const text = textEl ? textEl.textContent.trim() : node.textContent.trim();
  
  return text && text !== lastText ? { speaker, text } : null;
}

function onZoomMutation(mutations) {
  if (!capturing) return;
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node.nodeType !== Node.ELEMENT_NODE) continue;
      const line = extractZoomCaption(node);
      if (line) pushLine(line.speaker, line.text);
    }
    if (mutation.type === 'characterData') {
      const text = mutation.target.textContent.trim();
      if (text && text !== lastText && text.length > 2) {
        pushLine(lastSpeaker || 'Speaker', text);
      }
    }
  }
}

function pushLine(speaker, text) {
  if (text === lastText) return;
  if (speaker === lastSpeaker && transcriptBuffer.length > 0 &&
      text.startsWith(transcriptBuffer[transcriptBuffer.length - 1].text.substring(0, 20))) {
    transcriptBuffer[transcriptBuffer.length - 1].text = text;
  } else {
    transcriptBuffer.push({ speaker, text, ts: Date.now() });
  }
  lastSpeaker = speaker;
  lastText = text;
  broadcastUpdate();
}

function broadcastUpdate() {
  try {
    chrome.runtime.sendMessage({
      type: 'LIVE_CAPTION_UPDATE',
      platform: 'zoom',
      buffer: transcriptBuffer,
      formatted: formatTranscript()
    });
  } catch (_) {}
}

function formatTranscript() {
  return transcriptBuffer.map(l => `[${l.speaker}]: ${l.text}`).join('\n');
}

function startCapture() {
  if (capturing) return;
  capturing = true;
  transcriptBuffer = [];
  lastText = '';
  lastSpeaker = '';

  let root = findZoomCaptionRoot();
  if (!root) {
    const initObs = new MutationObserver(() => {
      root = findZoomCaptionRoot();
      if (root) {
        initObs.disconnect();
        attachObserver(root);
        chrome.runtime.sendMessage({ type: 'CAPTURE_STATUS', status: 'capturing', platform: 'zoom', message: 'Zoom captions detected.' });
      }
    });
    initObs.observe(document.body, { childList: true, subtree: true });
    chrome.runtime.sendMessage({
      type: 'CAPTURE_STATUS', status: 'waiting', platform: 'zoom',
      message: 'Waiting for Zoom captions. Enable "Live Transcript" in the meeting (... More → Live Transcript → Enable Auto-Transcription).'
    });
  } else {
    attachObserver(root);
    chrome.runtime.sendMessage({ type: 'CAPTURE_STATUS', status: 'capturing', platform: 'zoom', message: 'Live capture active.' });
  }
}

function attachObserver(root) {
  captureObserver = new MutationObserver(onZoomMutation);
  captureObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
}

function stopCapture() {
  capturing = false;
  if (captureObserver) { captureObserver.disconnect(); captureObserver = null; }
  chrome.runtime.sendMessage({ type: 'CAPTURE_STATUS', status: 'stopped', platform: 'zoom', transcript: formatTranscript(), lineCount: transcriptBuffer.length });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.action) {
    case 'Nimad_START_CAPTURE': startCapture(); sendResponse({ ok: true, status: capturing ? 'capturing' : 'waiting' }); break;
    case 'Nimad_STOP_CAPTURE': stopCapture(); sendResponse({ ok: true, transcript: formatTranscript(), lines: transcriptBuffer.length }); break;
    case 'Nimad_GET_TRANSCRIPT': sendResponse({ ok: true, transcript: formatTranscript(), lines: transcriptBuffer.length, capturing }); break;
    case 'Nimad_CLEAR_TRANSCRIPT': transcriptBuffer = []; lastText = ''; lastSpeaker = ''; sendResponse({ ok: true }); break;
    case 'Nimad_PING': sendResponse({ ok: true, platform: 'zoom', url: window.location.href, capturing }); break;
  }
  return true;
});

chrome.runtime.sendMessage({ type: 'PLATFORM_DETECTED', platform: 'zoom', url: window.location.href }).catch(() => {});
console.log('[Nimad Copilot] Zoom content script loaded.');
