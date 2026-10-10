# AI Conversation Copilot (PR007) — Meeting Application

> **PR007** · Real-Time Audio & Video Meeting Application with Live Speech Transcription & Instant Sidebar Q&A Copilot Answers.

## Project Location
[pr007-conversation-copilot/](file:///c:/Users/psamy/define/pr007-conversation-copilot)

---

## Current Status & Verification
- **Live Meeting Server:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/api/docs`
- **Frontend Meeting App:** `http://127.0.0.1:8000/` (served natively)
- **Configured API Key:** Loaded into `.env` and `backend/.env`
- **Acceptance Tests:** **7/7 pytest tests passing**

---

## 🚀 Key Features Implemented

### 1. Real Meeting Application (Zoom-Style Stage & Controls)
- **Meeting Room Layout:** Real-time top bar displaying Meeting Title, Room ID badge (`Click to copy invite link`), Live Timer (`00:04:12`), Call Mode (`VIDEO CALL` / `AUDIO CALL`), and Live Transcription indicator.
- **Video & Audio Stage:**
  - **Local Host Tile:** Supports real webcam video feed via `navigator.mediaDevices.getUserMedia` with mirror mode, or elegant avatar with dynamic audio waveform rings when camera is muted.
  - **Remote Attender Tiles:** Interactive participant tiles for organizational attenders (e.g. *Sarah Chen — VP Engineering*, *David Miller — Procurement*) with live speaking border animations (`is-speaking` glow).
  - **Audio-Only Meeting Mode:** One-click toggle between full Video Call grid and Audio-only conference room.
  - **Screen Sharing:** Host can share their desktop, tab, or window directly onto the meeting tile via `getDisplayMedia`.
- **Zoom-Style Meeting Dock:**
  - 🎙️ **Mute / Unmute Mic** (with real microphone control)
  - 📹 **Start / Stop Camera** (with webcam stream control)
  - 🔄 **Mode Toggle** (Video Call vs Audio Meeting)
  - 🖥️ **Share Screen**
  - 🔴 **Live Audio Transcription** (Web Speech API STT)
  - ⚡ **Easy Answers** quick drawer toggle
  - 👥 **Attenders List** (shows participants and invite link)
  - ☎️ **End Meeting** (leaves call and generates full structured report)

### 2. Live Speech-to-Text Audio Transcription
- Integrated continuous browser **Web Speech API** (`SpeechRecognition` / `webkitSpeechRecognition`).
- Speech from the microphone is continuously transcribed into the floating live captions banner on the video stage and saved to the backend database.
- **Attender Simulator Quick-Bar:** Built-in buttons for instant demonstration (*Ask Pricing & Pilot*, *Ask SOC2 & Security*, *Ask Slack Integration*, *Ask Onboarding Timeline*, and custom prompts).

### 3. Real-Time Question Detection & Instant "Easy Answers"
- As attenders speak in the meeting, questions are automatically detected in real-time.
- The sidebar immediately presents an **Easy Answer Card**:
  - **Attender Question:** Verbatim question text and speaker label.
  - **💡 Easy Answer (Suggested Response):** Crisp, authoritative 1-2 sentence response ready for the host to recite aloud immediately.
  - **Key Talking Points:** Bullet points for additional depth.
  - **Objective Alignment:** Tag indicating whether the question/answer supports or risks the session goal.
  - **📋 Copy Answer:** 1-click clipboard copy.
  - **🗣️ Speak Answer:** Browser text-to-speech recitation via `speechSynthesis`.
  - **→ Action:** 1-click promotion to follow-up deliverable.

### 4. Black and White High-Contrast UI
- Pitch black (`#000000`) and obsidian surfaces (`#0c0c0e`, `#17171a`).
- High-contrast typography with pure white text and silver accents.
- Distinct monochrome badges for insight types, confidence scores, and statuses.
- **Dashboard Hero Section Kept Untouched:** The hero section on `dashboard.html` remains fully preserved.

---

## 🛠️ How to Test

1. Visit **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.
2. Sign in with:
   - **Email:** `demo@copilot.ai`
   - **Password:** `demopassword123`
3. Click **+ Create Meeting** (or select any existing meeting from the grid).
4. In the meeting room:
   - Toggle **🎙️ Mic** or **📹 Camera** to test real media feeds.
   - Click any button on the **⚡ Attender Simulator** (e.g. *Ask Pricing & Pilot* or *Ask SOC2 & Security*).
   - Observe the live captions on the video stage and the **Easy Answer** card immediately popping up in the sidebar!
   - Click **📋 Copy Answer** or **🗣️ Speak Answer** to hear the copilot recite it.
