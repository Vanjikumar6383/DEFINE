/**
 * Nimad Copilot — Microsoft Teams Caption Capture Content Script
 * Captures live captions from Microsoft Teams web (teams.microsoft.com / teams.live.com).
 *
 * NO AUDIO RECORDING — reads caption text nodes only.
 */

'use strict';

let capturing = false;
let captureObserver = null;
let transcriptBuffer = [];
let lastText = '';
let lastSpeaker = '';

function findTeamsCaptionRoot() {
  // Teams renders captions in a specific container
  const selectors = [
    '[data-tid="closed-captions-container"]',
    '[class*="captions-container"]',
    '[class*="caption-panel"]',
    '[aria-label*="Captions"]',
    '[aria-label*="captions"]',
    '[class*="transcript"]',
    '[aria-live="polite"]',
    '[aria-live="assertive"]',
  ];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) return el;
  }
  return null;
}

function extractTeamsLine(node) {
  // Teams: speaker name in one element, text in another
  const nameEl = node.querySelector('[data-tid="closed-caption-speaker"], [class*="speaker-name"], [class*="displayName"]');
  const textEl = node.querySelector('[data-tid="closed-caption-text"], [class*="caption-text"], [class*="utterance"]');
  const speaker = nameEl ? nameEl.textContent.trim() : lastSpeaker || 'Speaker';
  const text = textEl ? textEl.textContent.trim() : node.textContent.trim();
  return text && text !== lastText ? { speaker, text } : null;
}

function onTeamsMutation(mutations) {
  if (!capturing) return;
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node.nodeType !== Node.ELEMENT_NODE) continue;
      const line = extractTeamsLine(node);
      if (line) pushLine(line.speaker, line.text);
      // Also check children
      node.querySelectorAll && node.querySelectorAll('[class*="utterance"], [class*="caption"]').forEach(el => {
        const text = el.textContent.trim();
        if (text && text !== lastText && text.length > 2) pushLine(lastSpeaker || 'Speaker', text);
      });
    }
    if (mutation.type === 'characterData') {
      const text = mutation.target.textContent.trim();
      if (text && text !== lastText && text.length > 2) pushLine(lastSpeaker || 'Speaker', text);
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
  try {
    chrome.runtime.sendMessage({ type: 'LIVE_CAPTION_UPDATE', platform: 'teams', buffer: transcriptBuffer, formatted: formatTranscript() });
  } catch (_) {}
}

function formatTranscript() {
  return transcriptBuffer.map(l => `[${l.speaker}]: ${l.text}`).join('\n');
}

function startCapture() {
  if (capturing) return;
  capturing = true;
  transcriptBuffer = []; lastText = ''; lastSpeaker = '';
  let root = findTeamsCaptionRoot();
  if (!root) {
    const initObs = new MutationObserver(() => {
      root = findTeamsCaptionRoot();
      if (root) {
        initObs.disconnect();
        attachObserver();
        chrome.runtime.sendMessage({ type: 'CAPTURE_STATUS', status: 'capturing', platform: 'teams', message: 'Teams captions detected.' });
      }
    });
    initObs.observe(document.body, { childList: true, subtree: true });
    chrome.runtime.sendMessage({ type: 'CAPTURE_STATUS', status: 'waiting', platform: 'teams', message: 'Enable Teams Live Captions (More → Language & Speech → Turn on live captions), then speak.' });
  } else {
    attachObserver();
    chrome.runtime.sendMessage({ type: 'CAPTURE_STATUS', status: 'capturing', platform: 'teams', message: 'Live capture active.' });
  }
}

function attachObserver() {
  captureObserver = new MutationObserver(onTeamsMutation);
  captureObserver.observe(document.body, { childList: true, subtree: true, characterData: true });
}

function stopCapture() {
  capturing = false;
  if (captureObserver) { captureObserver.disconnect(); captureObserver = null; }
  chrome.runtime.sendMessage({ type: 'CAPTURE_STATUS', status: 'stopped', platform: 'teams', transcript: formatTranscript(), lineCount: transcriptBuffer.length });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  switch (msg.action) {
    case 'Nimad_START_CAPTURE': startCapture(); sendResponse({ ok: true }); break;
    case 'Nimad_STOP_CAPTURE': stopCapture(); sendResponse({ ok: true, transcript: formatTranscript() }); break;
    case 'Nimad_GET_TRANSCRIPT': sendResponse({ ok: true, transcript: formatTranscript(), lines: transcriptBuffer.length, capturing }); break;
    case 'Nimad_CLEAR_TRANSCRIPT': transcriptBuffer = []; lastText = ''; lastSpeaker = ''; sendResponse({ ok: true }); break;
    case 'Nimad_PING': sendResponse({ ok: true, platform: 'teams', capturing }); break;
  }
  return true;
});

chrome.runtime.sendMessage({ type: 'PLATFORM_DETECTED', platform: 'teams', url: window.location.href }).catch(() => {});
console.log('[Nimad Copilot] Teams content script loaded.');
