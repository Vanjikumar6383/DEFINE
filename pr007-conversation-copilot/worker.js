/**
 * Cloudflare Worker Gateway for DEFINE / Nimad Copilot
 * Location: pr007-conversation-copilot/worker.js
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. Proxy API endpoints & health check to FastAPI backend
    if (url.pathname.startsWith('/api/') || url.pathname === '/healthz') {
      const backendUrl = env.BACKEND_API_URL || 'http://127.0.0.1:8000';
      const targetUrl = new URL(url.pathname + url.search, backendUrl);

      const requestHeaders = new Headers(request.headers);
      requestHeaders.set('X-Forwarded-Host', url.host);
      requestHeaders.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

      try {
        return await fetch(new Request(targetUrl, {
          method: request.method,
          headers: requestHeaders,
          body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
          redirect: 'follow',
        }));
      } catch (err) {
        return new Response(
          JSON.stringify({
            error: 'Backend API unreachable',
            detail: err.message,
            hint: 'Configure BACKEND_API_URL in wrangler.jsonc or Cloudflare Dashboard variables.',
          }),
          {
            status: 502,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
    }

    // 2. Map /static/* to /css/* (FastAPI StaticFiles compatibility)
    if (url.pathname.startsWith('/static/')) {
      const mappedPath = url.pathname.replace('/static/', '/css/');
      const staticReq = new Request(new URL(mappedPath, url.origin), request);
      return env.ASSETS.fetch(staticReq);
    }

    // 3. Dynamic clean route handling: /session/:id -> /session.html
    if (url.pathname.startsWith('/session/')) {
      const sessionReq = new Request(new URL('/session.html', url.origin), request);
      return env.ASSETS.fetch(sessionReq);
    }

    // 4. Clean URL routing for HTML pages
    const pageRoutes = {
      '/': '/index.html',
      '/dashboard': '/dashboard.html',
      '/integrations': '/integrations.html',
      '/session': '/session.html',
      '/login': '/login.html',
      '/meeting_test': '/meeting_test.html',
    };

    if (pageRoutes[url.pathname]) {
      const pageReq = new Request(new URL(pageRoutes[url.pathname], url.origin), request);
      return env.ASSETS.fetch(pageReq);
    }

    // 5. Default: serve asset directly via Cloudflare Assets
    return env.ASSETS.fetch(request);
  },
};
