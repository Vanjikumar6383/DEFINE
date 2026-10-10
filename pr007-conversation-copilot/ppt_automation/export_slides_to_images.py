import os
import sys

out_dir = r"C:\Users\psamy\define\pr007-conversation-copilot\ppt_automation\slide_renders"
os.makedirs(out_dir, exist_ok=True)
pptx_path = r"C:\Users\psamy\define\pr007-conversation-copilot\Nimad_DEFINE4.0_Final_Presentation.pptx"

try:
    import win32com.client
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    # Open presentation in read-only / background mode
    pres = ppt_app.Presentations.Open(pptx_path, WithWindow=False)
    print(f"Opened presentation with {pres.Slides.Count} slides.")
    
    for idx in range(1, pres.Slides.Count + 1):
        slide = pres.Slides(idx)
        slide_img = os.path.join(out_dir, f"slide_{idx}.png")
        slide.Export(slide_img, "PNG", 1920, 1080)
        print(f"Exported Slide {idx} to {slide_img} ({os.path.getsize(slide_img)} bytes)")
        
    pres.Close()
    ppt_app.Quit()
    print("All slides exported to images successfully!")
except Exception as e:
    print(f"PowerPoint export note: {e}")
