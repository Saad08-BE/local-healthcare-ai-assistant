"""Clean Gemini-styled dark theme CSS and layout helpers."""

GEMINI_THEME_CSS = """
<style>
/* Base Dark Background */
.stApp {
    background-color: #0d0f12 !important;
    color: #e3e3e3 !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* Sidebar Styling matching Gemini */
[data-testid="stSidebar"] {
    background-color: #13161b !important;
    border-right: 1px solid rgba(255, 255, 255, 0.07) !important;
}

[data-testid="stSidebar"] * {
    color: #c4c7c5 !important;
}

/* New Chat Button (Pill shaped, prominent) */
div[data-testid="stSidebar"] button[kind="primary"] {
    background: #1e2229 !important;
    color: #e3e3e3 !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 24px !important;
    font-weight: 500 !important;
    padding: 10px 18px !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
}

div[data-testid="stSidebar"] button[kind="primary"]:hover {
    background: #2a2f38 !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
    color: #ffffff !important;
}

/* History consultation buttons (Subtle, sleek hover) */
div[data-testid="stSidebar"] button[kind="secondary"] {
    background: transparent !important;
    border: none !important;
    color: #9aa0a6 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 12px !important;
    padding: 8px 12px !important;
    font-size: 0.88rem !important;
    transition: background 0.15s ease, color 0.15s ease !important;
}

div[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: #1e2229 !important;
    color: #e3e3e3 !important;
}

/* Search bar styling in sidebar */
[data-testid="stSidebar"] .stTextInput input {
    background-color: #1e2229 !important;
    color: #e3e3e3 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 20px !important;
    padding: 8px 14px !important;
}

/* Center Hero Section */
.gemini-hero-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px 20px 20px;
    text-align: center;
}

.gemini-hero-title {
    font-size: 2.8rem;
    font-weight: 400;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #9bb5ff 0%, #d8b4fe 50%, #e2e8f0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 24px;
}

/* Suggestion prompt cards */
.suggestion-card {
    background: #181b20;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 14px 18px;
    margin: 6px 0;
    color: #c4c7c5;
    font-size: 0.92rem;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: background 0.2s ease, border-color 0.2s ease;
    cursor: pointer;
}

.suggestion-card:hover {
    background: #20242c;
    border-color: rgba(255, 255, 255, 0.15);
    color: #ffffff;
}

/* ── Unified Chat Input Pill (Form) ── */
[data-testid="stForm"] {
    background: #1a1e24 !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 28px !important;
    padding: 2px 6px 2px 4px !important;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4) !important;
    margin-bottom: 0 !important;
}

/* Remove extra padding Streamlit adds around the form's inner block */
[data-testid="stForm"] > div:first-child {
    padding: 0 !important;
    gap: 0 !important;
}

/* Text input inside the pill — borderless, transparent */
[data-testid="stForm"] [data-testid="stTextInput"] input {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: #f1f3f4 !important;
    font-size: 0.95rem !important;
    padding: 12px 6px !important;
}

[data-testid="stForm"] [data-testid="stTextInput"] > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* Model selector inside the pill — pill-shaped border */
[data-testid="stForm"] [data-testid="stSelectbox"] > div[data-baseweb="select"] > div {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.16) !important;
    border-radius: 20px !important;
    color: #e3e3e3 !important;
    font-size: 0.84rem !important;
    min-height: 34px !important;
}

/* + attach form submit button */
[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 50% !important;
    color: #9aa0a6 !important;
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    padding: 0 !important;
    font-size: 1.05rem !important;
    line-height: 36px !important;
}

[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
    background: rgba(255, 255, 255, 0.12) !important;
    color: #e3e3e3 !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
}

/* ➤ Send primary form submit button */
[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: transparent !important;
    border: none !important;
    color: #8ab4f8 !important;
    font-size: 1.15rem !important;
    padding: 4px 10px !important;
    border-radius: 50% !important;
}

[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
    background: rgba(138, 180, 248, 0.12) !important;
    color: #aecbfa !important;
}

/* Action bar above input */
.gemini-controls-bar {
    background: transparent;
    padding: 4px 6px;
    margin-bottom: 4px;
}

/* Badges and tags */
.privacy-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(34, 197, 94, 0.1);
    color: #4ade80;
    border: 1px solid rgba(34, 197, 94, 0.2);
    border-radius: 16px;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-weight: 500;
}

.temp-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(239, 68, 68, 0.12);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 16px;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-weight: 500;
}
</style>
"""


def apply_gemini_theme(st_module) -> None:
    """Inject the dark Gemini theme styles."""
    st_module.markdown(GEMINI_THEME_CSS, unsafe_allow_html=True)
