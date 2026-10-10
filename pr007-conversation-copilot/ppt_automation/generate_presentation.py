"""
Nimad AI Conversation Copilot — DEFINE 4.0 Hackathon Presentation Generator
Preserves official DEFINE branding, dimensions, logos, and slide structure.
Outputs: Nimad_DEFINE4.0_Final_Presentation.pptx
"""
import os
import shutil
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = r"C:\Users\psamy\define\pr007-conversation-copilot"
TEMPLATE_PATH = os.path.join(BASE_DIR, "General - DEFINE Template.pptx")
OUTPUT_PATH = os.path.join(BASE_DIR, "Nimad_DEFINE4.0_Final_Presentation.pptx")
AUTO_DIR = os.path.join(BASE_DIR, "ppt_automation")

# Authentic Screenshots
SHOT_DASHBOARD = os.path.join(BASE_DIR, "frontend", "dashboard_live_screen.png")
SHOT_LANDING = os.path.join(AUTO_DIR, "shot_landing_hd.png")
SHOT_INTEGRATIONS = os.path.join(AUTO_DIR, "shot_integrations.png")
SHOT_POPUP = os.path.join(AUTO_DIR, "shot_extension_popup.png")
SHOT_LOGIN = os.path.join(AUTO_DIR, "shot_login.png")

# ── Color Palette (Modern Executive Dark/Red Theme) ───────────────────────────
CLR_WHITE = RGBColor(255, 255, 255)
CLR_OFF_WHITE = RGBColor(248, 250, 252)
CLR_GRAY_LIGHT = RGBColor(226, 232, 240)
CLR_GRAY_MUTED = RGBColor(148, 163, 184)
CLR_GRAY_DARK = RGBColor(51, 65, 85)
CLR_DARK_BG = RGBColor(15, 23, 42)        # Slate 900
CLR_CARD_BG = RGBColor(17, 24, 39)        # Gray 900
CLR_CARD_BG_ALT = RGBColor(24, 31, 47)    # Slightly lighter slate
CLR_DEFINE_RED = RGBColor(220, 38, 38)     # Official DEFINE Crimson Red (Red 600)
CLR_DEFINE_RED_DARK = RGBColor(153, 27, 27) # Deep Red (Red 800)
CLR_BORDER_RED = RGBColor(239, 68, 68)    # Border Red
CLR_BORDER_MUTED = RGBColor(71, 85, 105)  # Slate 600
CLR_EMERALD = RGBColor(16, 185, 129)      # Emerald for implemented
CLR_AMBER = RGBColor(245, 158, 11)        # Amber for partial
CLR_CYAN = RGBColor(14, 165, 233)         # Cyan for future scope

FONT_TITLE = "Clash Display"
FONT_BODY = "Segoe UI"

def build_presentation():
    print(f"Loading template from {TEMPLATE_PATH}...")
    prs = Presentation(TEMPLATE_PATH)
    assert len(prs.slides) == 10, f"Expected 10 slides, found {len(prs.slides)}"

    # ─────────────────────────────────────────────────────────────────────────
    # Helper Functions
    # ─────────────────────────────────────────────────────────────────────────
    def remove_empty_placeholders(slide):
        """Remove empty default Title/Subtitle placeholders so they don't block content."""
        to_remove = []
        for shape in slide.shapes:
            if shape.name in ["Title 1", "Subtitle 2"] and shape.has_text_frame and not shape.text_frame.text.strip():
                to_remove.append(shape)
        for shape in to_remove:
            sp = shape._element
            sp.getparent().remove(sp)

    def add_card(slide, left, top, width, height, bg_color=CLR_CARD_BG, border_color=None):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1.5)
        else:
            card.line.fill.background()
        tf = card.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.TOP
        tf.margin_left = Inches(0.22)
        tf.margin_right = Inches(0.22)
        tf.margin_top = Inches(0.25)
        tf.margin_bottom = Inches(0.2)
        return card

    def add_badge(slide, left, top, width, height, text, bg_color=CLR_DEFINE_RED, text_color=CLR_WHITE):
        badge = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        badge.fill.solid()
        badge.fill.fore_color.rgb = bg_color
        badge.line.fill.background()
        tf = badge.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = text
        run.font.name = FONT_BODY
        run.font.size = Pt(9.5)
        run.font.bold = True
        run.font.color.rgb = text_color
        return badge

    def set_slide_header(slide, title_text):
        """Ensure TextBox 7 has the correct title and font styling."""
        for shape in slide.shapes:
            if shape.name == "TextBox 7" and shape.has_text_frame:
                shape.text_frame.word_wrap = False
                shape.text_frame.text = title_text
                p = shape.text_frame.paragraphs[0]
                p.font.name = FONT_TITLE
                p.font.size = Pt(22)
                p.font.bold = True
                p.font.color.rgb = CLR_WHITE

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 1: TITLE SLIDE
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 1: Title...")
    s1 = prs.slides[0]
    remove_empty_placeholders(s1)

    # Top Cluster (Above DEFINE logo): Track, Project Title, Tagline
    for shape in s1.shapes:
        if shape.name == "TextBox 5" and shape.has_text_frame:
            shape.left = Inches(1.0)
            shape.top = Inches(0.9)
            shape.width = Inches(11.333)
            shape.height = Inches(2.3)
            
            tf = shape.text_frame
            tf.clear()
            tf.word_wrap = True
            tf.vertical_anchor = MSO_ANCHOR.TOP

            # Track / Problem Badge
            p0 = tf.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "HACKATHON TRACK: OVERALL   |   PROBLEM STATEMENT: PR 007\n"
            r0.font.name = FONT_BODY
            r0.font.size = Pt(13)
            r0.font.bold = True
            r0.font.color.rgb = RGBColor(254, 202, 202)

            # Main Title
            p1 = tf.add_paragraph()
            p1.alignment = PP_ALIGN.CENTER
            p1.space_before = Pt(4)
            r1 = p1.add_run()
            r1.text = "nimad — AI Conversation Copilot\n"
            r1.font.name = FONT_TITLE
            r1.font.size = Pt(38)
            r1.font.bold = True
            r1.font.color.rgb = CLR_WHITE

            # Tagline (Gold highlight)
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            p2.space_before = Pt(2)
            r2 = p2.add_run()
            r2.text = "“Listen Better. Think Smarter. Decide Confidently.”"
            r2.font.name = FONT_BODY
            r2.font.size = Pt(18)
            r2.font.bold = True
            r2.font.color.rgb = RGBColor(253, 224, 71)

    # Bottom Cluster (Below DEFINE logo): Team Name, DEFINE 4.0, Project Scope
    bot_box = s1.shapes.add_textbox(Inches(1.0), Inches(5.0), Inches(11.333), Inches(2.0))
    tf_bot = bot_box.text_frame
    tf_bot.word_wrap = True
    tf_bot.vertical_anchor = MSO_ANCHOR.TOP

    p_team = tf_bot.paragraphs[0]
    p_team.alignment = PP_ALIGN.CENTER
    r_team = p_team.add_run()
    r_team.text = "TEAM: FUTURESTACK   •   DEFINE 4.0 NATIONAL HACKATHON\n"
    r_team.font.name = FONT_BODY
    r_team.font.size = Pt(18)
    r_team.font.bold = True
    r_team.font.color.rgb = CLR_WHITE

    p_desc = tf_bot.add_paragraph()
    p_desc.alignment = PP_ALIGN.CENTER
    p_desc.space_before = Pt(4)
    r_desc = p_desc.add_run()
    r_desc.text = "An in-meeting AI intelligence layer that understands objectives, answers questions, and records decisions in real-time.\n"
    r_desc.font.name = FONT_BODY
    r_desc.font.size = Pt(12.5)
    r_desc.font.color.rgb = RGBColor(254, 202, 202)

    p_stack = tf_bot.add_paragraph()
    p_stack.alignment = PP_ALIGN.CENTER
    p_stack.space_before = Pt(2)
    r_stack = p_stack.add_run()
    r_stack.text = "FastAPI Async Core  •  128-dim Vector Memory Engine  •  Unobtrusive Browser HUD Over Any Meeting"
    r_stack.font.name = FONT_BODY
    r_stack.font.size = Pt(10.5)
    r_stack.font.bold = True
    r_stack.font.color.rgb = RGBColor(226, 232, 240)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 2: INTRODUCTION
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 2: Introduction...")
    s2 = prs.slides[1]
    remove_empty_placeholders(s2)
    set_slide_header(s2, "Introduction — The Human Conversation Dilemma")

    # Left Column: Strategic Context & Overview Cards
    c1 = add_card(s2, Inches(0.8), Inches(1.15), Inches(5.8), Inches(5.8), CLR_CARD_BG, CLR_BORDER_RED)
    tf1 = c1.text_frame
    tf1.word_wrap = True
    tf1.margin_left = Inches(0.25)
    tf1.margin_right = Inches(0.25)
    tf1.margin_top = Inches(0.25)
    
    p = tf1.paragraphs[0]
    r = p.add_run()
    r.text = "THE CORE COGNITIVE CONFLICT IN MEETINGS\n"
    r.font.name = FONT_TITLE
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = CLR_DEFINE_RED

    points_intro = [
        ("The 'Listen-Think-Respond' Trap", "In sales calls, customer support, contract negotiations, and technical reviews, people are forced to listen actively, synthesize complex concepts, and formulate articulate replies simultaneously."),
        ("Cognitive Overload & Blind Spots", "Because human working memory is severely constrained, critical nuances, unanswered objections, and binding commitments routinely get dropped in high-velocity discussions."),
        ("What Nimad Actually Does", "Nimad is an objective-aware AI copilot that runs silently alongside live discussions. It captures speech, tracks conversation progress against your goals, and surfaces instant 1-2 sentence spoken answers in real time."),
        ("Who Benefits Immediately", "Sales reps closing enterprise deals, support engineers resolving technical escalations, executives negotiating M&A, and distributed engineering teams finalizing SLAs.")
    ]
    for title, desc in points_intro:
        p = tf1.add_paragraph()
        p.space_before = Pt(8)
        r = p.add_run()
        r.text = f"• {title}: "
        r.font.name = FONT_BODY
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = CLR_WHITE
        r2 = p.add_run()
        r2.text = desc
        r2.font.name = FONT_BODY
        r2.font.size = Pt(10)
        r2.font.color.rgb = CLR_GRAY_LIGHT

    # Right Column: Authentic Application Visual Card
    c2 = add_card(s2, Inches(6.8), Inches(1.15), Inches(5.7), Inches(5.8), CLR_CARD_BG_ALT, CLR_BORDER_MUTED)
    tf2 = c2.text_frame
    tf2.margin_left = Inches(0.2)
    tf2.margin_top = Inches(0.2)
    p = tf2.paragraphs[0]
    r = p.add_run()
    r.text = "LIVE PRODUCT INTERFACE — NIMAD CALENDAR & WORKSPACE"
    r.font.name = FONT_TITLE
    r.font.size = Pt(12)
    r.font.bold = True
    r.font.color.rgb = CLR_WHITE

    if os.path.exists(SHOT_DASHBOARD):
        s2.shapes.add_picture(SHOT_DASHBOARD, Inches(7.0), Inches(1.75), width=Inches(5.3), height=Inches(3.3))
    
    # Caption box under screenshot
    c2_sub = add_card(s2, Inches(7.0), Inches(5.2), Inches(5.3), Inches(1.5), CLR_DARK_BG)
    tf_sub = c2_sub.text_frame
    tf_sub.margin_left = Inches(0.15)
    tf_sub.margin_top = Inches(0.12)
    p = tf_sub.paragraphs[0]
    r = p.add_run()
    r.text = "Key Verified Capability:\n"
    r.font.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = CLR_EMERALD
    r2 = p.add_run()
    r2.text = "Synchronized Google Calendar workspace with meeting motive tracking, attended vs. upcoming shading, and instantaneous Q&A ledger previews."
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = CLR_GRAY_LIGHT

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 3: PROBLEM STATEMENT
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 3: Problem Statement...")
    s3 = prs.slides[2]
    remove_empty_placeholders(s3)
    set_slide_header(s3, "Problem Statement — Why Important Discussions Fail (PR 007)")

    # 4 Problem Quadrants
    problems = [
        ("1. Missed Critical Points", "Fast discussions outpace note-taking. Crucial customer requirements, technical objections, and implicit caveats are lost forever once the video call disconnects.", CLR_DEFINE_RED),
        ("2. Unfamiliar Concepts & Terms", "Prospects and stakeholders bring up niche compliance standards (SOC2, CMEK), competitor claims, or legal terms that catch the host off guard without real-time recall.", CLR_AMBER),
        ("3. Unanswered & Stalled Questions", "When tough questions arise, people either guess incorrectly or say 'I'll get back to you', which stalls negotiation momentum and prolongs enterprise sales cycles.", CLR_CYAN),
        ("4. Forgotten Decisions & Next Steps", "Commitments made verbally during meetings evaporate without clear accountability, owners, or confirmed delivery dates, creating project execution bottlenecks.", CLR_EMERALD)
    ]

    card_coords = [
        (Inches(0.8), Inches(1.15)),
        (Inches(6.8), Inches(1.15)),
        (Inches(0.8), Inches(3.9)),
        (Inches(6.8), Inches(3.9)),
    ]

    for idx, (title, desc, color) in enumerate(problems):
        x, y = card_coords[idx]
        card = add_card(s3, x, y, Inches(5.7), Inches(2.45), CLR_CARD_BG, color)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.25)
        tf.margin_top = Inches(0.2)
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = title + "\n"
        r.font.name = FONT_TITLE
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = color
        
        p2 = tf.add_paragraph()
        p2.space_before = Pt(6)
        r2 = p2.add_run()
        r2.text = desc
        r2.font.name = FONT_BODY
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = CLR_GRAY_LIGHT

    # Bottom Callout Strip
    strip = add_card(s3, Inches(0.8), Inches(6.5), Inches(11.7), Inches(0.7), CLR_DEFINE_RED_DARK, CLR_DEFINE_RED)
    tf_strip = strip.text_frame
    tf_strip.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf_strip.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = "THE ROOT CAUSE: Humans cannot multitask listening, analytical reasoning, and vocal synthesis simultaneously under pressure."
    r.font.name = FONT_BODY
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = CLR_WHITE

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 4: PROPOSED SOLUTION
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 4: Proposed Solution...")
    s4 = prs.slides[3]
    remove_empty_placeholders(s4)
    set_slide_header(s4, "Proposed Solution — An AI Intelligence Layer Over Any Call")

    # Banner Statement
    banner = add_card(s4, Inches(0.8), Inches(1.15), Inches(11.7), Inches(0.85), CLR_CARD_BG, CLR_BORDER_RED)
    tf_b = banner.text_frame
    tf_b.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf_b.margin_left = Inches(0.2)
    p = tf_b.paragraphs[0]
    r = p.add_run()
    r.text = "CORE ARCHITECTURAL THESIS:\n"
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = CLR_DEFINE_RED
    r2 = p.add_run()
    r2.text = "“We are not building another video-conferencing platform. We are building an AI intelligence layer on top of existing meeting ecosystems.”"
    r2.font.name = FONT_TITLE
    r2.font.size = Pt(13)
    r2.font.bold = True
    r2.font.color.rgb = CLR_WHITE

    # 4-Step Horizontal Pipeline
    steps = [
        ("Step 1: Dual Audio Ingestion", "Captures local mic and attendee speaker audio without clunky bot avatars joining the call.", CLR_CYAN),
        ("Step 2: Objective Understanding", "Anchors dialogue to the user's defined meeting motive and live 0–100% alignment meter.", CLR_AMBER),
        ("Step 3: Instant Spoken Answers", "Surfaces 1–2 sentence ready-to-speak suggestions before you reply, powered by vector memory.", CLR_DEFINE_RED),
        ("Step 4: Decisions & Governance", "Extracts confirmed agreements, assigns action items with deadlines, and drafts recap emails.", CLR_EMERALD)
    ]
    step_width = Inches(2.75)
    for idx, (stitle, sdesc, scolor) in enumerate(steps):
        sx = Inches(0.8) + idx * Inches(2.98)
        scard = add_card(s4, sx, Inches(2.15), step_width, Inches(3.2), CLR_CARD_BG, scolor)
        tf_s = scard.text_frame
        tf_s.word_wrap = True
        tf_s.margin_left = Inches(0.18)
        tf_s.margin_top = Inches(0.2)
        p = tf_s.paragraphs[0]
        r = p.add_run()
        r.text = stitle + "\n\n"
        r.font.name = FONT_TITLE
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = scolor
        
        r2 = p.add_run()
        r2.text = sdesc
        r2.font.name = FONT_BODY
        r2.font.size = Pt(10)
        r2.font.color.rgb = CLR_GRAY_LIGHT

    # Bottom Summary Box: Confidential & Multi-Mode
    bot_card = add_card(s4, Inches(0.8), Inches(5.5), Inches(11.7), Inches(1.65), CLR_DARK_BG, CLR_BORDER_MUTED)
    tf_bot = bot_card.text_frame
    tf_bot.margin_left = Inches(0.25)
    tf_bot.margin_top = Inches(0.15)
    p = tf_bot.paragraphs[0]
    r = p.add_run()
    r.text = "DESIGNED FOR DISCRETION AND DUAL CONVERSATIONAL MODES:\n"
    r.font.bold = True
    r.font.size = Pt(11)
    r.font.color.rgb = CLR_WHITE

    p2 = tf_bot.add_paragraph()
    p2.space_before = Pt(4)
    r = p2.add_run()
    r.text = "• 1-on-1 vs. Group Mode: "
    r.font.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = CLR_CYAN
    r_sub = p2.add_run()
    r_sub.text = "Customized diarization for single-buyer discovery vs. multi-attendee team consensus reviews.\n"
    r_sub.font.size = Pt(10)
    r_sub.font.color.rgb = CLR_GRAY_LIGHT

    r = p2.add_run()
    r.text = "• Confidentiality & Ephemeral Processing: "
    r.font.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = CLR_EMERALD
    r_sub2 = p2.add_run()
    r_sub2.text = "In-memory processing with automatic session purge, audio consent flags, and zero vendor model training."
    r_sub2.font.size = Pt(10)
    r_sub2.font.color.rgb = CLR_GRAY_LIGHT

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 5: TECHNICAL ARCHITECTURE
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 5: Technical Architecture...")
    s5 = prs.slides[4]
    remove_empty_placeholders(s5)
    set_slide_header(s5, "Technical Architecture & Tech Stack (Verified Implementation)")

    # 3-Tier Architecture Columns
    arch_cols = [
        ("1. Presentation & Client Tier", [
            ("Frontend Core", "Modern Vanilla HTML5, CSS3, ES Modules"),
            ("Dashboard HUD", "Real-time Google Calendar workspace & motive score"),
            ("Silver-White Shader", "Custom WebGL fluid wave animation + 2D canvas fallback"),
            ("Chrome Extension", "Manifest V3 DOM observers for Meet, Zoom & Teams")
        ], CLR_CYAN),
        ("2. Application & API Gateway", [
            ("FastAPI Backend", "High-performance asynchronous Python (ASGI)"),
            ("Audio Diarization", "Dual-channel WebRTC + tab speaker stream isolation"),
            ("AI Inference Engine", "Groq / OpenAI API with smart structured JSON schema"),
            ("Deterministic Fallback", "100% offline local heuristic NLP fallback analyzer")
        ], CLR_DEFINE_RED),
        ("3. Storage & Semantic Memory", [
            ("Relational DB", "SQLite async via SQLAlchemy connection pooling"),
            ("Vector Memory", "Native 128-dim dense embeddings with cosine similarity"),
            ("Multi-Speaker Diarization", "Attendee voice profiling & screen role mapping"),
            ("Data Privacy", "AES-256 transit/rest encryption, ephemeral purges")
        ], CLR_EMERALD)
    ]

    col_w = Inches(3.75)
    for idx, (title, items, color) in enumerate(arch_cols):
        cx = Inches(0.8) + idx * Inches(3.97)
        card = add_card(s5, cx, Inches(1.15), col_w, Inches(4.5), CLR_CARD_BG, color)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.2)
        tf.margin_top = Inches(0.2)
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = title + "\n"
        r.font.name = FONT_TITLE
        r.font.size = Pt(13)
        r.font.bold = True
        r.font.color.rgb = color
        
        for k, v in items:
            p = tf.add_paragraph()
            p.space_before = Pt(8)
            r = p.add_run()
            r.text = f"• {k}: "
            r.font.bold = True
            r.font.size = Pt(10)
            r.font.color.rgb = CLR_WHITE
            r2 = p.add_run()
            r2.text = v
            r2.font.size = Pt(9.5)
            r2.font.color.rgb = CLR_GRAY_LIGHT

    # Dataflow Callout Bar
    df_card = add_card(s5, Inches(0.8), Inches(5.8), Inches(11.7), Inches(1.35), CLR_DARK_BG, CLR_BORDER_MUTED)
    tf_df = df_card.text_frame
    tf_df.margin_left = Inches(0.25)
    tf_df.margin_top = Inches(0.12)
    p = tf_df.paragraphs[0]
    r = p.add_run()
    r.text = "VERIFIED END-TO-END DATAFLOW:\n"
    r.font.bold = True
    r.font.size = Pt(10.5)
    r.font.color.rgb = CLR_WHITE
    r2 = p.add_run()
    r2.text = "Microphone & Tab Audio  →  STT Engine  →  FastAPI Router  →  AI Adapter (Groq / Heuristic)  →  Vector DB Memory Matching  →  Real-Time HUD Suggestions & Action Log"
    r2.font.name = FONT_BODY
    r2.font.size = Pt(10)
    r2.font.bold = True
    r2.font.color.rgb = CLR_AMBER

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 6: USER EXPERIENCE AND USABILITY
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 6: User Experience and Usability...")
    s6 = prs.slides[5]
    remove_empty_placeholders(s6)
    set_slide_header(s6, "User Experience & Usability — Unobtrusive & Accessible")

    # Left Column: UX Principles
    c_ux = add_card(s6, Inches(0.8), Inches(1.15), Inches(5.6), Inches(5.8), CLR_CARD_BG, CLR_BORDER_RED)
    tf_ux = c_ux.text_frame
    tf_ux.margin_left = Inches(0.25)
    tf_ux.margin_top = Inches(0.2)
    p = tf_ux.paragraphs[0]
    r = p.add_run()
    r.text = "INTUITIVE, HIGH-CONTRAST INTERFACE DESIGN\n"
    r.font.name = FONT_TITLE
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = CLR_DEFINE_RED

    ux_features = [
        ("Discreet Floating HUD Pill", "Chrome extension overlay rests unobtrusively at the screen perimeter without blocking slides or attendee faces."),
        ("Objective Coverage Meter", "Live visual 0–100% progress gauge indicates in real-time whether the host is covering planned agenda points."),
        ("Interactive Transcript Stream", "Searchable, speaker-filtered transcript feed with instant copy-to-clipboard and export to .txt and .md formats."),
        ("Multi-Speaker Diarization Hotkeys", "Switch active speaking participant instantly using single-key hotkeys (Keys 1-4 for You, Sarah, David, Priya)."),
        ("Multilingual Accessibility", "Real-time speech-to-text and instant localized suggestion cards in English, Tamil (தமிழ்), and Malayalam (മലയാളം).")
    ]
    for utitle, udesc in ux_features:
        p = tf_ux.add_paragraph()
        p.space_before = Pt(8)
        r = p.add_run()
        r.text = f"• {utitle}: "
        r.font.bold = True
        r.font.size = Pt(10.5)
        r.font.color.rgb = CLR_WHITE
        r2 = p.add_run()
        r2.text = udesc
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = CLR_GRAY_LIGHT

    # Right Column: UI Screenshots Showcase
    c_shot = add_card(s6, Inches(6.2), Inches(1.15), Inches(6.3), Inches(5.75), CLR_CARD_BG_ALT, CLR_BORDER_MUTED)

    # Left inside container: Chrome Extension Popup (vertical: 480x720)
    if os.path.exists(SHOT_POPUP):
        s6.shapes.add_picture(SHOT_POPUP, Inches(6.35), Inches(1.55), width=Inches(2.55), height=Inches(4.45))
        add_badge(s6, Inches(6.35), Inches(6.12), Inches(2.55), Inches(0.42), "Chrome Extension HUD\n(Google Meet, Zoom, Teams)", CLR_DARK_BG, CLR_AMBER)

    # Right inside container: Dashboard & Landing
    if os.path.exists(SHOT_DASHBOARD):
        s6.shapes.add_picture(SHOT_DASHBOARD, Inches(9.05), Inches(1.55), width=Inches(3.35), height=Inches(2.15))
        add_badge(s6, Inches(9.05), Inches(3.76), Inches(3.35), Inches(0.3), "Calendar Workspace & Motive Score", CLR_DARK_BG, CLR_EMERALD)

    if os.path.exists(SHOT_LANDING):
        s6.shapes.add_picture(SHOT_LANDING, Inches(9.05), Inches(4.18), width=Inches(3.35), height=Inches(1.88))
        add_badge(s6, Inches(9.05), Inches(6.12), Inches(3.35), Inches(0.42), "1-Click Meeting Launch\n& Real-Time WebGL HUD", CLR_DARK_BG, CLR_CYAN)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 7: KEY FEATURES AND IMPLEMENTATION
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 7: Key Features and Implementation...")
    s7 = prs.slides[6]
    remove_empty_placeholders(s7)
    set_slide_header(s7, "Key Features & Implementation Status (Strict Verification)")

    # 3 Status Categories (Green, Amber, Blue)
    feat_cats = [
        ("IMPLEMENTED & FULLY TESTED (100%)", [
            ("Real-Time Dual Audio Diarization", "Separates user mic from screen attendee audio"),
            ("Sub-Second Spoken Answer Generator", "Instant 1-2 sentence replies & talking points"),
            ("Objective Alignment Meter", "Live 0-100% goal coverage & drift prevention"),
            ("Decisions & Action Items Ledger", "Automated extraction with owner and due date"),
            ("Vector Semantic Memory Engine", "128-dim dense embedding cosine retrieval"),
            ("Multilingual Support (EN, TA, ML)", "Automatic language detection & native answers"),
            ("Google Calendar Visual Workspace", "Attended vs. upcoming meeting state shading"),
            ("Backend Test Suite", "26 / 26 unit and integration tests passing")
        ], CLR_EMERALD),
        ("PARTIALLY IMPLEMENTED / BETA", [
            ("WebRTC Peer-to-Peer Signaling", "Multi-party mesh operational on local/LAN; STUN/TURN traversal in staging"),
            ("Google Calendar OAuth Sync", "Database models and endpoints active; production Google Cloud verification in progress"),
            ("Audio Tone & Sentiment Analysis", "Heuristic indicators active; fine-grained acoustic emotion modeling in progress")
        ], CLR_AMBER),
        ("FUTURE ROADMAP / PLANNED", [
            ("Native Desktop Tray HUD", "Electron / Tauri system-tray app for zero-browser overlay"),
            ("Bi-Directional CRM Sync", "Automated push to Salesforce, HubSpot, and Notion"),
            ("Hardware Audio Controller", "Stream Deck integration for silent physical mute & suggestion cycling")
        ], CLR_CYAN)
    ]

    col_w7 = Inches(3.75)
    for idx, (ctitle, clist, ccolor) in enumerate(feat_cats):
        cx = Inches(0.8) + idx * Inches(3.97)
        card = add_card(s7, cx, Inches(1.15), col_w7, Inches(5.8), CLR_CARD_BG, ccolor)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.18)
        tf.margin_top = Inches(0.18)
        
        # Category Title Badge
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = ctitle + "\n"
        r.font.name = FONT_TITLE
        r.font.size = Pt(11.5)
        r.font.bold = True
        r.font.color.rgb = ccolor

        for fname, fdesc in clist:
            p = tf.add_paragraph()
            p.space_before = Pt(6)
            r = p.add_run()
            r.text = f"✓ {fname}: " if ccolor == CLR_EMERALD else f"• {fname}: "
            r.font.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = CLR_WHITE
            r2 = p.add_run()
            r2.text = fdesc
            r2.font.size = Pt(8.5)
            r2.font.color.rgb = CLR_GRAY_LIGHT

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 8: LIVE DEMO WITH UI
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 8: Live Demo with UI...")
    s8 = prs.slides[7]
    remove_empty_placeholders(s8)
    set_slide_header(s8, "Live Demo with UI — Real 4-Step Operational Flow")

    # Left Column: 4-Step Narrative
    c_demo = add_card(s8, Inches(0.8), Inches(1.15), Inches(5.2), Inches(5.75), CLR_CARD_BG, CLR_BORDER_RED)
    tf_d = c_demo.text_frame
    tf_d.margin_left = Inches(0.22)
    tf_d.margin_top = Inches(0.2)
    p = tf_d.paragraphs[0]
    r = p.add_run()
    r.text = "END-TO-END DEMO WORKFLOW\n"
    r.font.name = FONT_TITLE
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = CLR_DEFINE_RED

    demo_steps = [
        ("Step 1: Setup Meeting Objective", "User opens Google Calendar workspace and schedules meeting with Primary Objective (e.g., 'Review high-availability architecture & verify SOC2 SIEM export')."),
        ("Step 2: Dual-Channel Live Meeting", "Host and remote attendee talk. WebRTC & tab observer streams real-time speech into distinct audio channels without bot intrusion."),
        ("Step 3: Instant Suggestion Surfaced", "Prospect asks: 'How do you handle failovers?'. Nimad triggers instant 1-2 sentence answer citing 99.9% uptime SLA across GCP regions."),
        ("Step 4: Decisions & Action Items Logged", "Meeting wraps up. 1-click generation of confirmed decisions, action item assignments, and ready-to-send recap email draft.")
    ]
    for sname, stext in demo_steps:
        p = tf_d.add_paragraph()
        p.space_before = Pt(8)
        r = p.add_run()
        r.text = sname + "\n"
        r.font.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = CLR_AMBER
        r2 = p.add_run()
        r2.text = stext
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = CLR_GRAY_LIGHT

    # Right Column: Screenshot Visuals
    c_img = add_card(s8, Inches(6.2), Inches(1.15), Inches(6.3), Inches(5.75), CLR_CARD_BG_ALT, CLR_BORDER_MUTED)

    if os.path.exists(SHOT_DASHBOARD):
        s8.shapes.add_picture(SHOT_DASHBOARD, Inches(6.4), Inches(1.55), width=Inches(5.9), height=Inches(2.15))
        add_badge(s8, Inches(6.4), Inches(3.76), Inches(5.9), Inches(0.3), "Step 1 & 2: Google Calendar Workspace, Agenda & Objective Setup", CLR_DARK_BG, CLR_EMERALD)

    if os.path.exists(SHOT_LANDING):
        s8.shapes.add_picture(SHOT_LANDING, Inches(6.4), Inches(4.18), width=Inches(5.9), height=Inches(1.88))
        add_badge(s8, Inches(6.4), Inches(6.12), Inches(5.9), Inches(0.42), "Step 3 & 4: Live Meeting Room Copilot & Sub-Second Answer Extraction", CLR_DARK_BG, CLR_AMBER)

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 9: IMPACT, FEASIBILITY AND SCALABILITY
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 9: Impact, Feasibility and Scalability...")
    s9 = prs.slides[8]
    remove_empty_placeholders(s9)
    set_slide_header(s9, "Impact, Feasibility & Scalability — Built for Enterprise")

    # 3 Pillars
    pillars = [
        ("1. High-Value Business Impact", [
            ("Sales Pitches", "Eliminates hesitant pauses; increases deal velocity by resolving objections immediately."),
            ("Customer Support", "Resolves complex technical tickets on first contact without escalation delays."),
            ("Contract Negotiations", "Anchors dialogue to pre-set boundaries and prevents unplanned commercial concessions."),
            ("Engineering Reviews", "Ensures zero architectural decisions or action items are lost to conversational drift.")
        ], CLR_CYAN),
        ("2. Technical Feasibility", [
            ("Sub-100ms Latency", "Asynchronous FastAPI pipeline delivers instant spoken suggestions during live speech."),
            ("Graceful Degradation", "Seamless fallback to local heuristic NLP if third-party LLM APIs are unreachable."),
            ("Zero Bot Overhead", "Runs cleanly in browser without hosting compute-heavy bot instances per attendee."),
            ("Resource Attribution", "Tested and verified across local SQLite and scalable enterprise databases.")
        ], CLR_AMBER),
        ("3. Realistic Scalability Roadmap", [
            ("Phase 1 (Completed)", "Real-time transcription, instant answer generation, and Google Calendar sync."),
            ("Phase 2 (Completed)", "128-dim dense vector memory graph and cross-meeting semantic search."),
            ("Phase 3 (Next Quarter)", "Automated bi-directional CRM connectors (Salesforce, HubSpot, Jira, Notion)."),
            ("Phase 4 (Enterprise)", "Zero-knowledge on-premise private cloud deployment with CMEK encryption.")
        ], CLR_EMERALD)
    ]

    col_w9 = Inches(3.75)
    for idx, (ptitle, pitems, pcolor) in enumerate(pillars):
        cx = Inches(0.8) + idx * Inches(3.97)
        card = add_card(s9, cx, Inches(1.15), col_w9, Inches(5.8), CLR_CARD_BG, pcolor)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.2)
        tf.margin_top = Inches(0.2)
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = ptitle + "\n"
        r.font.name = FONT_TITLE
        r.font.size = Pt(13)
        r.font.bold = True
        r.font.color.rgb = pcolor

        for ik, iv in pitems:
            p = tf.add_paragraph()
            p.space_before = Pt(8)
            r = p.add_run()
            r.text = f"• {ik}: "
            r.font.bold = True
            r.font.size = Pt(10)
            r.font.color.rgb = CLR_WHITE
            r2 = p.add_run()
            r2.text = iv
            r2.font.size = Pt(9.5)
            r2.font.color.rgb = CLR_GRAY_LIGHT

    # ─────────────────────────────────────────────────────────────────────────
    # SLIDE 10: CONCLUSION
    # ─────────────────────────────────────────────────────────────────────────
    print("Building Slide 10: Conclusion...")
    s10 = prs.slides[9]
    remove_empty_placeholders(s10)
    set_slide_header(s10, "Conclusion — Summary & Vision")

    # Center Hero Card
    c_hero = add_card(s10, Inches(1.5), Inches(1.2), Inches(10.3), Inches(5.6), CLR_CARD_BG, CLR_BORDER_RED)
    tf_h = c_hero.text_frame
    tf_h.margin_left = Inches(0.4)
    tf_h.margin_top = Inches(0.3)
    tf_h.word_wrap = True

    # 3 Summary Pillars
    p = tf_h.paragraphs[0]
    r = p.add_run()
    r.text = "THE INNOVATION AT A GLANCE\n\n"
    r.font.name = FONT_TITLE
    r.font.size = Pt(18)
    r.font.bold = True
    r.font.color.rgb = CLR_DEFINE_RED

    conclusions = [
        ("The Problem Solved", "Eliminates the cognitive impossibility of listening, thinking, and replying at the same time in high-stakes conversations."),
        ("The Architectural Innovation", "An objective-aware AI layer that connects directly into your existing video meeting tools (Meet, Zoom, Teams) without replacing them."),
        ("The Proven Reality", "Full working implementation with dual-channel audio, sub-second suggestion engine, vector semantic memory, and Google Calendar sync.")
    ]
    for ctitle, cdesc in conclusions:
        p = tf_h.add_paragraph()
        p.space_before = Pt(8)
        r = p.add_run()
        r.text = f"• {ctitle}: "
        r.font.bold = True
        r.font.size = Pt(12)
        r.font.color.rgb = CLR_WHITE
        r2 = p.add_run()
        r2.text = cdesc
        r2.font.size = Pt(11)
        r2.font.color.rgb = CLR_GRAY_LIGHT

    # Big Tagline Box
    p_tag = tf_h.add_paragraph()
    p_tag.space_before = Pt(24)
    p_tag.alignment = PP_ALIGN.CENTER
    r_tag = p_tag.add_run()
    r_tag.text = "“Nimad — Listen Better. Think Smarter. Decide Confidently.”\n"
    r_tag.font.name = FONT_TITLE
    r_tag.font.size = Pt(20)
    r_tag.font.bold = True
    r_tag.font.color.rgb = CLR_AMBER

    # Thank you & credentials
    p_ty = tf_h.add_paragraph()
    p_ty.space_before = Pt(12)
    p_ty.alignment = PP_ALIGN.CENTER
    r_ty = p_ty.add_run()
    r_ty.text = "Thank You! We Welcome Questions & Live Evaluation.\n"
    r_ty.font.bold = True
    r_ty.font.size = Pt(14)
    r_ty.font.color.rgb = CLR_WHITE

    r_team = p_ty.add_run()
    r_team.text = "Team FutureStack   |   Problem Statement: PR 007   |   DEFINE 4.0 Hackathon"
    r_team.font.size = Pt(11)
    r_team.font.color.rgb = CLR_GRAY_MUTED

    # ─────────────────────────────────────────────────────────────────────────
    # Save Presentation
    # ─────────────────────────────────────────────────────────────────────────
    print(f"Saving final presentation to {OUTPUT_PATH}...")
    prs.save(OUTPUT_PATH)
    print(f"Successfully generated presentation: {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)} bytes)")

if __name__ == "__main__":
    build_presentation()
