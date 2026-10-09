/**
 * UI helpers — toast notifications, modal management, DOM utilities.
 */

// ── Toast ──────────────────────────────────────────────────────────────
let toastContainer = null;

function getToastContainer() {
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);
  }
  return toastContainer;
}

export function toast(message, type = 'info', duration = 3500) {
  const container = getToastContainer();
  const el = document.createElement('div');
  el.className = `toast ${type}`;

  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  el.innerHTML = `<span style="margin-right:8px;font-weight:700">${icons[type] || ''}</span>${message}`;

  container.appendChild(el);
  setTimeout(() => {
    el.style.animation = 'fadeIn .25s ease reverse forwards';
    setTimeout(() => el.remove(), 250);
  }, duration);
}

// ── Modal ──────────────────────────────────────────────────────────────
export function showModal(html, { onClose } = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal" role="dialog" aria-modal="true">${html}</div>`;

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeModal(overlay);
      onClose?.();
    }
  });

  document.addEventListener('keydown', function handler(e) {
    if (e.key === 'Escape') {
      closeModal(overlay);
      onClose?.();
      document.removeEventListener('keydown', handler);
    }
  });

  document.body.appendChild(overlay);
  return overlay;
}

export function closeModal(overlay) {
  overlay.style.animation = 'fadeIn .2s ease reverse forwards';
  setTimeout(() => overlay.remove(), 200);
}

// ── Button loading state ───────────────────────────────────────────────
export function setLoading(btn, loading, text = '') {
  if (loading) {
    if (!btn._originalHTML) {
      btn._originalHTML = btn.innerHTML;
    }
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span>${text ? ' ' + text : ''}`;
  } else {
    btn.disabled = false;
    if (btn._originalHTML) {
      btn.innerHTML = btn._originalHTML;
      delete btn._originalHTML;
    }
  }
}

// ── Format helpers ─────────────────────────────────────────────────────
export function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso)) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str ?? '';
  return d.innerHTML;
}

// ── Debounce ───────────────────────────────────────────────────────────
export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
