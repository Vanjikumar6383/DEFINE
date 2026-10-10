import subprocess
import time
import os
import httpx

# 1. Login to get token
try:
    resp = httpx.post("http://127.0.0.1:8000/api/v1/auth/login", json={"email": "demo@copilot.ai", "password": "demopassword123"})
    token = resp.json()["access_token"]
    print("Logged in, token received.")
except Exception as e:
    print("Login error:", e)
    token = ""

# 2. We can create an HTML page that sets localStorage and redirects to /session/f1b1a202-695d-4bfe-978e-ce9702199850
bridge_html = rf"""<!DOCTYPE html>
<html>
<body>
<script>
  localStorage.setItem('copilot_token', '{token}');
  localStorage.setItem('copilot_user', JSON.stringify({{'email': 'demo@copilot.ai', 'display_name': 'Demo Host'}}));
  window.location.href = '/session/f1b1a202-695d-4bfe-978e-ce9702199850';
</script>
</body>
</html>
"""

bridge_path = r"C:\Users\psamy\define\pr007-conversation-copilot\frontend\bridge.html"
with open(bridge_path, "w", encoding="utf-8") as f:
    f.write(bridge_html)

out_shot = r"C:\Users\psamy\define\pr007-conversation-copilot\ppt_automation\shot_live_session.png"
chrome_cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless",
    f"--screenshot={out_shot}",
    "--window-size=1600,900",
    "--virtual-time-budget=5000",
    "http://127.0.0.1:8000/static/../bridge.html"
]

print("Capturing live session screenshot...")
subprocess.run(chrome_cmd)
if os.path.exists(bridge_path):
    os.remove(bridge_path)

if os.path.exists(out_shot):
    print(f"Captured: {out_shot} ({os.path.getsize(out_shot)} bytes)")
else:
    print("Could not capture session screenshot.")
