/**
 * Nimad Copilot — Runtime Environment Configuration
 * 
 * By default, Nimad uses relative endpoints (window.location.origin), which works
 * automatically with:
 *   1. Direct FastAPI serving (http://127.0.0.1:8000)
 *   2. Cloudflare Tunnel (https://your-tunnel.trycloudflare.com)
 *   3. Cloudflare Pages with Functions API reverse-proxy
 * 
 * If hosting frontend on Cloudflare Pages and backend on a separate domain (e.g., Render, Fly.io, or VPS),
 * uncomment and set your backend URL below:
 */

// window.__COPILOT_API_BASE__ = 'https://api.your-domain.com';
// window.__COPILOT_WS_HOST__ = 'api.your-domain.com';
