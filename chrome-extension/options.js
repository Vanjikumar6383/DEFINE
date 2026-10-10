/**
 * Nimad Copilot — Extension Options & Settings Controller
 */

const DEFAULT_API_URL = 'http://127.0.0.1:8000';

const optApiUrl = document.getElementById('opt-api-url');
const optDefaultObjective = document.getElementById('opt-default-objective');
const btnTestConnection = document.getElementById('btn-test-connection');
const btnSaveSettings = document.getElementById('btn-save-settings');
const saveStatusMsg = document.getElementById('save-status-msg');
const testResultBox = document.getElementById('test-result-box');
const testResultIcon = document.getElementById('test-result-icon');
const testResultText = document.getElementById('test-result-text');
const optConnectionPill = document.getElementById('opt-connection-pill');
const optConnectionText = document.getElementById('opt-connection-text');

const optAuthBadge = document.getElementById('opt-auth-badge');
const optUserEmail = document.getElementById('opt-user-email');
const optTokenStatus = document.getElementById('opt-token-status');
const btnOptSignout = document.getElementById('btn-opt-signout');
const linkWebDashboard = document.getElementById('link-web-dashboard');

document.addEventListener('DOMContentLoaded', async () => {
  await loadOptions();
  btnTestConnection.addEventListener('click', testConnection);
  btnSaveSettings.addEventListener('click', saveSettings);
  btnOptSignout.addEventListener('click', clearAuthToken);
});

async function loadOptions() {
  chrome.storage.local.get(['apiUrl', 'defaultObjective', 'authToken'], async (data) => {
    const url = data.apiUrl || DEFAULT_API_URL;
    optApiUrl.value = url;
    optDefaultObjective.value = data.defaultObjective || 'Strategic Alignment & Technical Decisions';
    linkWebDashboard.href = `${url.replace(/\/+$/, '')}/dashboard`;

    await testConnectionQuiet(url);
    await checkAuthStatus(url, data.authToken);
  });
}

async function testConnection() {
  const url = (optApiUrl.value.trim() || DEFAULT_API_URL).replace(/\/+$/, '');
  btnTestConnection.disabled = true;
  btnTestConnection.textContent = 'Testing…';
  testResultBox.style.display = 'none';

  setConnectionPill('checking', 'Testing…');
  const startTime = performance.now();

  try {
    const resp = await fetch(`${url}/healthz`, { method: 'GET', cache: 'no-cache' });
    const latency = Math.round(performance.now() - startTime);

    if (resp.ok) {
      const data = await resp.json().catch(() => ({}));
      setConnectionPill('connected', 'Connected');
      showTestResult(true, `Reachable (${latency}ms) — Server status: ${data.status || 'ok'} (${data.env || 'dev'})`);
    } else {
      throw new Error(`HTTP ${resp.status}`);
    }
  } catch (err) {
    setConnectionPill('disconnected', 'Offline');
    showTestResult(false, `Connection failed: ${err.message}. Is your backend running on ${url}?`);
  } finally {
    btnTestConnection.disabled = false;
    btnTestConnection.textContent = 'Test Connection';
  }
}

async function testConnectionQuiet(url) {
  try {
    const resp = await fetch(`${url.replace(/\/+$/, '')}/healthz`, { method: 'GET', cache: 'no-cache' });
    if (resp.ok) {
      setConnectionPill('connected', 'Connected');
    } else {
      setConnectionPill('disconnected', 'Offline');
    }
  } catch (_) {
    setConnectionPill('disconnected', 'Offline');
  }
}

async function checkAuthStatus(url, token) {
  if (!token) {
    optAuthBadge.textContent = 'NOT SIGNED IN';
    optAuthBadge.style.color = 'var(--text-dim)';
    optUserEmail.textContent = 'None';
    optTokenStatus.textContent = 'No token stored';
    return;
  }

  try {
    const resp = await fetch(`${url.replace(/\/+$/, '')}/api/v1/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (resp.ok) {
      const user = await resp.json();
      optAuthBadge.textContent = 'AUTHENTICATED';
      optAuthBadge.style.color = 'var(--clr-green)';
      optUserEmail.textContent = `${user.display_name} (${user.email})`;
      optTokenStatus.textContent = `Valid JWT (${token.substring(0, 15)}…)`;
    } else {
      optAuthBadge.textContent = 'TOKEN EXPIRED';
      optAuthBadge.style.color = 'var(--clr-yellow)';
      optUserEmail.textContent = 'Session expired';
      optTokenStatus.textContent = 'Expired';
    }
  } catch (_) {
    optAuthBadge.textContent = 'UNVERIFIED';
    optUserEmail.textContent = 'Server unreachable';
  }
}

async function saveSettings() {
  const url = (optApiUrl.value.trim() || DEFAULT_API_URL).replace(/\/+$/, '');
  const objective = optDefaultObjective.value.trim();

  btnSaveSettings.disabled = true;
  saveStatusMsg.textContent = '';

  await chrome.storage.local.set({
    apiUrl: url,
    defaultObjective: objective
  });

  linkWebDashboard.href = `${url}/dashboard`;
  btnSaveSettings.disabled = false;
  saveStatusMsg.textContent = '✓ Preferences saved successfully!';
  setTimeout(() => { saveStatusMsg.textContent = ''; }, 3000);

  await testConnectionQuiet(url);
}

async function clearAuthToken() {
  await chrome.storage.local.remove(['authToken']);
  optAuthBadge.textContent = 'SIGNED OUT';
  optAuthBadge.style.color = 'var(--text-dim)';
  optUserEmail.textContent = 'None';
  optTokenStatus.textContent = 'Removed from extension storage';
}

function setConnectionPill(status, text) {
  optConnectionPill.className = `status-pill status-${status}`;
  optConnectionText.textContent = text;
}

function showTestResult(success, message) {
  testResultBox.style.display = 'flex';
  testResultBox.className = `test-result-box ${success ? 'success' : 'error'}`;
  testResultIcon.textContent = success ? '✓' : '⚠️';
  testResultText.textContent = message;
}
