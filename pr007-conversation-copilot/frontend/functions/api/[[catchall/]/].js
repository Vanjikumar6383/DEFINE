/**
 * Cloudflare Pages Function — Reverse Proxy for FastAPI Backend
 * 
 * Intercepts all requests matching /api/* and proxies them to the backend server.
 * Handles both standard HTTP REST requests and WebSocket connection upgrades.
 */

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  // Target backend URL: Configured via Cloudflare Pages Environment Variables or wrangler.toml
  // Default fallback if not set in Cloudflare dashboard
  const backendBase = env.BACKEND_URL || 'http://127.0.0.1:8000';
  
  // Construct destination URL preserving the full pathname and query search params
  const targetUrl = new URL(url.pathname + url.search, backendBase);

  // Clone headers and remove CF-specific or hop-by-hop headers that shouldn't be forwarded
  const forwardHeaders = new Headers(request.headers);
  forwardHeaders.set('X-Forwarded-Host', url.host);
  forwardHeaders.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

  // Detect WebSocket Upgrade requests
  const upgradeHeader = request.headers.get('Upgrade');
  const isWebSocket = upgradeHeader && upgradeHeader.toLowerCase() === 'websocket';

  // Handle CORS Preflight (OPTIONS) directly at the edge
  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type, Accept, X-Requested-With',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  try {
    // Forward the request to the backend
    const backendResponse = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: forwardHeaders,
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
      redirect: 'manual',
    });

    // If WebSocket upgrade response
    if (isWebSocket && backendResponse.status === 101) {
      return backendResponse;
    }

    // Build the response to return to the client with CORS enabled
    const responseHeaders = new Headers(backendResponse.headers);
    responseHeaders.set('Access-Control-Allow-Origin', '*');
    responseHeaders.set('Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS');
    responseHeaders.set('Access-Control-Allow-Headers', 'Authorization, Content-Type, Accept, X-Requested-With');

    return new Response(backendResponse.body, {
      status: backendResponse.status,
      statusText: backendResponse.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    return new Response(
      JSON.stringify({
        detail: `Cloudflare Pages Proxy Error: Could not connect to backend at ${backendBase}. Please verify that the backend server is running and BACKEND_URL is reachable.`,
        error: String(err),
      }),
      {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    );
  }
}
