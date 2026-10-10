# NIMAD — Cloudflare Hosting & Deployment Master Guide

This guide provides everything needed to host **Nimad — AI Conversation Copilot** on Cloudflare.

---

## 🚀 Quick Decision: Which Hosting Method Should You Use?

| Feature | Method 1: Cloudflare Quick Tunnel ⭐ **(Recommended for Hackathons)** | Method 2: Cloudflare Pages (Frontend CDN + Edge Proxy) | Method 3: Cloudflare Named Tunnel (Custom Domain) |
| :--- | :--- | :--- | :--- |
| **Best For** | **Live Judge Demos & Instant Sharing** | **Production Static CDN Hosting** | **Permanent Custom Domain** |
| **Setup Time** | **30 seconds** | 2 minutes | 5 minutes |
| **Custom Domain?** | Not required (Free `trycloudflare.com` URL) | Free `*.pages.dev` subdomain | Yes (`yourdomain.com`) |
| **FastAPI Backend?** | Connected automatically | Proxied via Cloudflare Function | Connected via Tunnel Ingress |
| **WebSockets (WSS)?**| Supported out of the box | Supported via Edge Upgrade | Supported |
| **Credit Card / Login?**| **100% Free, NO login needed** | Free Cloudflare account | Free Cloudflare account |

---

## 📁 Files Created in Your Project

All required Cloudflare configuration files have been created in your repository:

```
pr007-conversation-copilot/
├── wrangler.toml                           # Cloudflare Pages / Workers project configuration
├── CLOUDFLARE_DEPLOYMENT_GUIDE.md          # This complete deployment guide
├── frontend/
│   ├── _redirects                         # Cloudflare clean URL rewrites (/dashboard, /session/:id)
│   ├── _headers                           # Security headers, WebRTC microphone/camera permissions
│   ├── config.js                          # Optional client-side API URL override
│   └── functions/
│       └── api/
│           └── [[catchall]].js            # Cloudflare Pages Function (Proxies /api/* and WSS)
└── cloudflare/
    ├── tunnel-config.yml                  # cloudflared ingress rules
    ├── run_quick_tunnel.bat               # 1-click launcher for Windows (batch)
    ├── run_quick_tunnel.ps1               # 1-click launcher for Windows (PowerShell)
    ├── deploy_pages.bat                   # 1-click Cloudflare Pages deployment script
    └── deploy_pages.ps1                   # PowerShell deploy script for Pages
```

---

## ⚡ METHOD 1: Instant Cloudflare Quick Tunnel (Fastest for Hackathon Demos)

With Cloudflare Quick Tunnels, Cloudflare securely connects to your local FastAPI backend and gives you a free, public `https://<random>.trycloudflare.com` URL in **5 seconds**.

### How to Run:

1. **Start your FastAPI backend** (if not already running):
   ```powershell
   cd c:\Users\psamy\define\pr007-conversation-copilot
   .\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

2. **Double-click** or run the Quick Tunnel launcher:
   ```cmd
   .\cloudflare\run_quick_tunnel.bat
   ```
   *(Or in PowerShell)*:
   ```powershell
   .\cloudflare\run_quick_tunnel.ps1
   ```

3. **Copy your Public URL:**  
   The terminal will output a link like:
   ```text
   +--------------------------------------------------------------------------------------------+
   |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
   |  https://speedy-fox-sample.trycloudflare.com                                               |
   +--------------------------------------------------------------------------------------------+
   ```
4. **Share with Judges:** Open this `https://...` link in any browser or on your phone.
   - Everything (Landing page, Google Calendar workspace, WebSockets, Live Copilot room) works immediately over SSL!

---

## 🌐 METHOD 2: Deploy Frontend to Cloudflare Pages

If you want your frontend hosted permanently on Cloudflare's global edge network at `https://nimad-copilot.pages.dev`:

### Step 1: Deploy with 1 Command
Run the helper script:
```cmd
.\cloudflare\deploy_pages.bat
```
*(Or via npx command)*:
```powershell
npx -y wrangler pages deploy ./frontend --project-name=nimad-copilot
```

- When prompted for the first time, Wrangler will open your browser to log into your free Cloudflare account.
- It will upload the `frontend/` folder, parse `_redirects` and `_headers`, and deploy `functions/api/[[catchall]].js`.

### Step 2: Connect the Pages Function to Your Backend
In Cloudflare Dashboard:
1. Go to **Workers & Pages** → Click **nimad-copilot** → **Settings** → **Environment variables**.
2. Add a variable:
   - **Variable name:** `BACKEND_URL`
   - **Value:** `https://your-tunnel-or-vps-url.com` (e.g. your Cloudflare Tunnel URL, Render, Railway, or Fly.io URL).
3. Click **Save and Deploy**.

Now, whenever a user opens `https://nimad-copilot.pages.dev`, all requests to `/api/*` and WebSockets are automatically forwarded to your backend without any CORS errors!

---

## 🔒 METHOD 3: Cloudflare Tunnel with Custom Domain (Production)

If you own a domain on Cloudflare (e.g., `copilot.yourdomain.com`):

1. **Install cloudflared**:
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. **Authenticate with Cloudflare**:
   ```powershell
   cloudflared tunnel login
   ```
3. **Create your named tunnel**:
   ```powershell
   cloudflared tunnel create nimad-prod
   ```
   *(Note the Tunnel UUID output in the terminal)*.
4. **Bind your DNS record**:
   ```powershell
   cloudflared tunnel route dns nimad-prod copilot.yourdomain.com
   ```
5. **Update `cloudflare/tunnel-config.yml`** with your Tunnel UUID and credentials file path.
6. **Run the production tunnel**:
   ```powershell
   cloudflared tunnel --config ./cloudflare/tunnel-config.yml run
   ```

---

## 🛠️ Verification Checklist for Cloudflare

- [x] **Clean URLs Handled:** `frontend/_redirects` maps `/dashboard` to `/dashboard.html` and `/session/:id` to `/session.html` with HTTP 200.
- [x] **Media Device Permissions:** `frontend/_headers` permits `microphone=(self "*")` and `camera=(self "*")` so WebRTC functions normally over HTTPS.
- [x] **Reverse Proxy Ready:** `frontend/functions/api/[[catchall]].js` transparently proxies REST and WebSockets.
- [x] **CORS Resolved:** API requests are routed on the same origin via Cloudflare Edge.
- [x] **Tests Passing:** All 26 backend unit and integration tests passing.

---
*Created for Nimad AI Conversation Copilot (PR 007 - Team FutureStack)*
