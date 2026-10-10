import zipfile
import os

pptx_path = r"C:\Users\psamy\define\pr007-conversation-copilot\General - DEFINE Template.pptx"
out_dir = r"C:\Users\psamy\define\pr007-conversation-copilot\ppt_automation\template_media"
os.makedirs(out_dir, exist_ok=True)

with zipfile.ZipFile(pptx_path, 'r') as z:
    for name in z.namelist():
        if name.startswith('ppt/media/'):
            filename = os.path.basename(name)
            if filename:
                out_path = os.path.join(out_dir, filename)
                with open(out_path, 'wb') as f:
                    f.write(z.read(name))
                print(f"Extracted: {filename} ({os.path.getsize(out_path)} bytes)")
