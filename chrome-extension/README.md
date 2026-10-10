# Nimad Copilot — Chrome Browser Extension (Manifest V3)

> **Nimad — AI Conversation Copilot** companion browser extension for real-time meeting intelligence, suggested responses, key insights, decision ledger tracking, and session summaries across **Google Meet**, **Zoom**, and **Microsoft Teams**.

---

## 🚀 Key Features

- **⚡ Instant Smart Replies:** Objective-aligned suggested responses ready to recite aloud or paste.
- **🧠 Key Insights:** High-confidence extracted commitments, risks, objections, and facts with verifiable transcript quotes.
- **⚖️ Decision Ledger & Action Items:** Auto-detects ratified decisions and action items with deadlines and owners.
- **📋 Executive Summaries:** Structured session recaps ready for immediate follow-up.
- **🛡️ Privacy & Consent-First:** Operates strictly on explicit user action. Never scrapes private tabs or secretly monitors audio without user action. Zero server secrets stored in the browser extension.
- **🌐 Multilingual Support:** Compatible with English, Tamil, and Malayalam conversation transcripts.

---

## 📦 How to Install in Google Chrome (Developer Mode)

### Step 1: Ensure Your Nimad Backend is Running
Verify your local Nimad server is running:
```powershell
# In pr007-conversation-copilot/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)** in Chrome to verify `{"status": "ok"}`.

### Step 2: Open Extensions in Google Chrome
1. In Google Chrome, open a new tab and navigate to:
   ```
   chrome://extensions
   ```
2. In the top-right corner, toggle on **Developer mode**.

### Step 3: Load the Unpacked Extension
1. Click the **Load unpacked** button in the top-left corner.
2. Select the `chrome-extension` directory:
   ```
   c:\Users\psamy\define\pr007-conversation-copilot\chrome-extension
   ```
   *(or `c:\Users\psamy\define\chrome-extension`)*
3. **Nimad — AI Conversation Copilot** will now appear in your active extensions list!

### Step 4: Pin the Extension
1. Click the **Puzzle Piece icon** (Extensions) in your Chrome toolbar.
2. Click the **Pin icon** next to **Nimad — AI Conversation Copilot** for 1-click access.

---

## 🎯 How to Use Nimad Copilot

### 1. Sign In
1. Click the **Nimad diamond icon (`◆`)** in your Chrome toolbar.
2. If not already signed in, enter your account credentials:
   - **Email:** `demo@copilot.ai`
   - **Password:** `demopassword123`
   *(Or click "Use Demo Account" for instant fill).*
3. Click **Sign In**.

### 2. Enter Objective & Paste Transcript
1. Enter your **Meeting Objective** (e.g. *Enterprise Pricing & Pilot Approval*, or click any quick chip).
2. Paste your meeting transcript, notes, or spoken words into the textarea.
   - *Tip:* You can also click **Insert Sample Transcript** for an instant working demo!
   - *Tip:* Highlight any text on any web page → right click → **Analyze with Nimad Copilot**.
3. Click **⚡ Analyze Conversation with AI**.

### 3. Review AI Intelligence
- Browse **⚡ Replies** and click **📋 Copy Reply** to use suggested responses in real-time.
- Check **🧠 Insights** with objective alignment badges (`SUPPORTS GOAL`, `RISKS GOAL`).
- Track **⚖️ Decisions** and **✓ Actions**.
- View **📋 Summary** and copy the executive report.
- Click **Open in Workspace ↗** to jump straight into the full Nimad meeting room and video stage!

---

## ⚙️ Options & Settings

Right-click the extension icon → **Options** (or click the ⚙️ gear icon in the popup):
- **Backend API URL:** Change from `http://127.0.0.1:8000` to your production HTTPS server if hosted remotely.
- **Test Connection:** Runs an immediate latency and health check against `/healthz`.
- **Default Objective:** Set a standard goal to automatically pre-fill for all your meetings.
- **Sign Out / Token Manager:** Securely clear stored JWT tokens.

---

## 🛡️ Architecture & Security Disclosures

- **Manifest V3:** Built with the latest, secure Chrome Manifest V3 standard with minimal permissions (`storage`, `contextMenus`).
- **Zero Server Secrets:** All AI provider keys (Groq, OpenAI, ElevenLabs) remain securely on the backend server.
- **CORS Support:** The backend includes `allow_origin_regex=r"^chrome-extension://.*$"` to permit authenticated extension API calls cleanly.
