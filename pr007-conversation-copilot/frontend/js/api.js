/**
 * API Client — wraps all fetch calls to the backend.
 * Reads the JWT from localStorage and injects Authorization header.
 */

const BASE = window.location.origin;

function getToken() {
  return localStorage.getItem('copilot_token');
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const resp = await fetch(`${BASE}${path}`, { ...options, headers });

  if (resp.status === 401) {
    localStorage.removeItem('copilot_token');
    window.location.href = '/';
    throw new Error('Unauthorised');
  }

  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      msg = err.detail || JSON.stringify(err);
    } catch (_) {}
    throw new Error(msg);
  }

  if (resp.status === 204) return null;
  return resp.json();
}

// ── Auth ──────────────────────────────────────────────────────────────
export const api = {
  auth: {
    register: (email, displayName, password) =>
      apiFetch('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, display_name: displayName, password }),
      }),

    login: (email, password) =>
      apiFetch('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),

    me: () => apiFetch('/api/v1/auth/me'),
  },

  // ── Sessions ──────────────────────────────────────────────────────────
  sessions: {
    create: (payload) =>
      apiFetch('/api/v1/sessions', { method: 'POST', body: JSON.stringify(payload) }),

    list: () => apiFetch('/api/v1/sessions'),

    get: (id) => apiFetch(`/api/v1/sessions/${id}`),

    update: (id, payload) =>
      apiFetch(`/api/v1/sessions/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

    delete: (id) =>
      apiFetch(`/api/v1/sessions/${id}`, { method: 'DELETE' }),
  },

  // ── Transcript ────────────────────────────────────────────────────────
  transcript: {
    submit: (sessionId, payload) =>
      apiFetch(`/api/v1/sessions/${sessionId}/transcript`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    list: (sessionId) => apiFetch(`/api/v1/sessions/${sessionId}/transcript`),
  },

  // ── Insights ──────────────────────────────────────────────────────────
  insights: {
    generate: (sessionId) =>
      apiFetch(`/api/v1/sessions/${sessionId}/insights`, { method: 'POST' }),

    list: (sessionId) => apiFetch(`/api/v1/sessions/${sessionId}/insights`),

    feedback: (sessionId, insightId, rating, correction) =>
      apiFetch(`/api/v1/sessions/${sessionId}/insights/${insightId}/feedback`, {
        method: 'POST',
        body: JSON.stringify({ rating, correction }),
      }),
  },

  // ── Action items ──────────────────────────────────────────────────────
  actions: {
    create: (sessionId, payload) =>
      apiFetch(`/api/v1/sessions/${sessionId}/actions`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    list: (sessionId) => apiFetch(`/api/v1/sessions/${sessionId}/actions`),

    update: (sessionId, actionId, payload) =>
      apiFetch(`/api/v1/sessions/${sessionId}/actions/${actionId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),

    delete: (sessionId, actionId) =>
      apiFetch(`/api/v1/sessions/${sessionId}/actions/${actionId}`, {
        method: 'DELETE',
      }),
  },

  // ── Summary ───────────────────────────────────────────────────────────
  summary: {
    generate: (sessionId) =>
      apiFetch(`/api/v1/sessions/${sessionId}/summary`, { method: 'POST' }),

    get: (sessionId) => apiFetch(`/api/v1/sessions/${sessionId}/summary`),

    update: (sessionId, payload) =>
      apiFetch(`/api/v1/sessions/${sessionId}/summary`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),
  },

  // ── Meeting Q&A / Easy Answers ────────────────────────────────────────
  qa: {
    answer: (sessionId, question, speakerLabel = 'Attender') =>
      apiFetch(`/api/v1/sessions/${sessionId}/qa/answer`, {
        method: 'POST',
        body: JSON.stringify({ question, speaker_label: speakerLabel }),
      }),
  },

  // ── Meeting Integrations ──────────────────────────────────────────────
  integrations: {
    list: () => apiFetch('/api/v1/integrations'),

    getAuthUrl: (provider) =>
      apiFetch(`/api/v1/integrations/${provider}/auth-url`),

    connect: (provider, payload = {}) =>
      apiFetch(`/api/v1/integrations/${provider}/connect`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    disconnect: (provider) =>
      apiFetch(`/api/v1/integrations/${provider}/disconnect`, {
        method: 'POST',
      }),
  },

  // ── Transcript Import & Processing (Options A, B, C) ──────────────────
  transcripts: {
    validateUrl: (url) =>
      apiFetch('/api/v1/transcripts/validate-url', {
        method: 'POST',
        body: JSON.stringify({ url }),
      }),

    import: (payload) =>
      apiFetch('/api/v1/transcripts/import', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    uploadFile: async (file) => {
      const token = getToken();
      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch(`${BASE}/api/v1/transcripts/upload-file`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });
      if (!resp.ok) {
        let msg = `HTTP ${resp.status}`;
        try {
          const err = await resp.json();
          msg = err.detail || JSON.stringify(err);
        } catch (_) {}
        throw new Error(msg);
      }
      return resp.json();
    },
  },

  // ── Full Conversation Analysis (Clarivue Intelligence Layer) ──────────
  analysis: {
    run: (sessionId) =>
      apiFetch(`/api/v1/sessions/${sessionId}/analyze`, { method: 'POST' }),
  },

  // ── Suggestions ───────────────────────────────────────────────────────
  suggestions: {
    regenerate: (sessionId, payload = {}) =>
      apiFetch(`/api/v1/sessions/${sessionId}/suggestions/regenerate`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  },

  // ── Decision Ledger ───────────────────────────────────────────────────
  decisions: {
    list: (sessionId) =>
      apiFetch(`/api/v1/sessions/${sessionId}/decisions`),

    create: (sessionId, payload) =>
      apiFetch(`/api/v1/sessions/${sessionId}/decisions`, {
        method: 'POST',
        body: JSON.stringify(payload),
      }),

    update: (sessionId, decisionId, payload) =>
      apiFetch(`/api/v1/sessions/${sessionId}/decisions/${decisionId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }),

    delete: (sessionId, decisionId) =>
      apiFetch(`/api/v1/sessions/${sessionId}/decisions/${decisionId}`, {
        method: 'DELETE',
      }),
  },

  // ── Export ────────────────────────────────────────────────────────────
  export: {
    url: (sessionId, format = 'markdown') =>
      `${BASE}/api/v1/sessions/${sessionId}/export?format=${format}`,
  },
};

