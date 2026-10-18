"""Polished dark theme and responsive layout helpers for the local healthcare assistant."""

GEMINI_THEME_CSS = """
<style>
:root {
    color-scheme: dark;
    --health-bg: #0b0e13;
    --health-panel: #121720;
    --health-panel-raised: #181f2a;
    --health-border: rgba(226, 232, 240, 0.10);
    --health-text: #e8edf5;
    --health-muted: #9aa8ba;
    --health-accent: #9bbcff;
    --health-accent-soft: rgba(125, 166, 255, 0.12);
}

/* App canvas and typography */
.stApp {
    background:
        radial-gradient(ellipse at 50% -18%, rgba(75, 104, 166, 0.16), transparent 48%),
        var(--health-bg) !important;
    color: var(--health-text) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
[data-testid="stHeader"] {
    background: rgba(11, 14, 19, 0.82) !important;
}
[data-testid="stMainBlockContainer"] {
    max-width: 1180px;
    padding-top: 1.4rem;
    padding-bottom: 2rem;
}
h1, h2, h3, h4 {
    color: #f0f4fb !important;
    letter-spacing: -0.025em;
}
p, li, label, [data-testid="stMarkdownContainer"] {
    line-height: 1.65;
}
small, .stCaption, [data-testid="stCaptionContainer"] {
    color: var(--health-muted) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #121720 0%, #0f131a 100%) !important;
    border-right: 1px solid var(--health-border) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.1rem;
}
[data-testid="stSidebar"] * {
    color: #cbd5e1;
}
[data-testid="stSidebar"] button {
    transition: background 160ms ease, border-color 160ms ease, transform 160ms ease;
}
div[data-testid="stSidebar"] button[kind="primary"] {
    background: linear-gradient(135deg, #26364e, #1c293c) !important;
    color: #eef4ff !important;
    border: 1px solid rgba(155, 188, 255, 0.28) !important;
    border-radius: 15px !important;
    font-weight: 600 !important;
    min-height: 2.7rem;
    box-shadow: 0 5px 18px rgba(0, 0, 0, 0.16) !important;
}
div[data-testid="stSidebar"] button[kind="primary"]:hover {
    background: linear-gradient(135deg, #304666, #24354d) !important;
    border-color: rgba(155, 188, 255, 0.48) !important;
}
div[data-testid="stSidebar"] button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #aebacc !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 11px !important;
    padding: 0.45rem 0.65rem !important;
    font-size: 0.88rem !important;
}
div[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.055) !important;
    border-color: var(--health-border) !important;
    color: #f4f7fc !important;
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #171e28 !important;
    color: #edf2fa !important;
    border: 1px solid var(--health-border) !important;
    border-radius: 12px !important;
}

/* Welcome / empty state */
.gemini-hero-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: clamp(2.5rem, 8vh, 5.5rem) 1rem 1rem;
    text-align: center;
}
.gemini-hero-title {
    font-size: clamp(2.1rem, 4.5vw, 3.25rem);
    line-height: 1.15;
    font-weight: 560;
    letter-spacing: -0.055em;
    background: linear-gradient(100deg, #a7c5ff 5%, #d4c4ff 48%, #edf2fa 92%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.65rem;
}
.gemini-hero-subtitle {
    max-width: 650px;
    color: #9eacc0;
    font-size: 1rem;
    line-height: 1.75;
    margin: 0 auto;
}

/* Privacy and temporary-mode status pills */
.privacy-pill, .temp-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    border-radius: 999px;
    padding: 0.38rem 0.75rem;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}
.privacy-pill {
    background: rgba(52, 211, 153, 0.09);
    color: #6ee7b7;
    border: 1px solid rgba(52, 211, 153, 0.22);
}
.temp-pill {
    background: rgba(251, 113, 133, 0.09);
    color: #fda4af;
    border: 1px solid rgba(251, 113, 133, 0.23);
}

/* Conversation messages */
[data-testid="stChatMessage"] {
    background: rgba(20, 26, 36, 0.70);
    border: 1px solid rgba(226, 232, 240, 0.075);
    border-radius: 18px;
    padding: 1rem 1.1rem;
    margin: 0.8rem 0;
    gap: 0.85rem;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: rgba(32, 43, 60, 0.62);
    border-color: rgba(155, 188, 255, 0.13);
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p:last-child {
    margin-bottom: 0;
}
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3 {
    margin-top: 1.1rem;
}
[data-testid="stChatMessage"] ul,
[data-testid="stChatMessage"] ol {
    padding-left: 1.35rem;
}
[data-testid="stChatMessage"] li {
    margin-bottom: 0.28rem;
}
[data-testid="stChatMessage"] blockquote {
    border-left: 3px solid #8db4ff;
    background: rgba(141, 180, 255, 0.07);
    border-radius: 0 10px 10px 0;
    padding: 0.65rem 0.9rem;
    color: #c8d5e8;
}
[data-testid="stChatMessage"] pre {
    background: #0c1118 !important;
    border: 1px solid var(--health-border);
    border-radius: 12px;
}
[data-testid="stChatMessage"] table {
    border-collapse: collapse;
    width: 100%;
}
[data-testid="stChatMessage"] th {
    background: #202a39;
    color: #eef4ff;
}
[data-testid="stChatMessage"] th,
[data-testid="stChatMessage"] td {
    border: 1px solid var(--health-border);
    padding: 0.55rem 0.7rem;
}

/* Unified chat composer */
[data-testid="stForm"] {
    background: linear-gradient(135deg, #171e28, #131922) !important;
    border: 1px solid rgba(190, 205, 228, 0.18) !important;
    border-radius: 24px !important;
    padding: 0.35rem 0.5rem !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.20) !important;
    margin-bottom: 0.5rem !important;
    transition: border-color 160ms ease, box-shadow 160ms ease;
}
[data-testid="stForm"]:focus-within {
    border-color: rgba(155, 188, 255, 0.48) !important;
    box-shadow: 0 0 0 3px rgba(125, 166, 255, 0.07), 0 8px 30px rgba(0, 0, 0, 0.22) !important;
}
[data-testid="stForm"] > div:first-child {
    padding: 0 !important;
    gap: 0.15rem !important;
}
[data-testid="stForm"] [data-testid="stTextInput"] input {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    color: #f1f5fb !important;
    font-size: 0.96rem !important;
    padding: 0.8rem 0.55rem !important;
    min-height: 2.7rem;
}
[data-testid="stForm"] [data-testid="stTextInput"] > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
[data-testid="stForm"] [data-testid="stSelectbox"] > div[data-baseweb="select"] > div {
    background: rgba(255, 255, 255, 0.055) !important;
    border: 1px solid rgba(255, 255, 255, 0.13) !important;
    border-radius: 15px !important;
    color: #e3eaf5 !important;
    font-size: 0.82rem !important;
    min-height: 2.35rem !important;
}
[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: #a8c7ff !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    color: #101827 !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    padding: 0.3rem 0.6rem !important;
    border-radius: 14px !important;
    min-height: 2.35rem;
    transition: transform 150ms ease, background 150ms ease;
}
[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
    background: #c0d6ff !important;
    transform: translateY(-1px);
}
[data-testid="stForm"] button[kind="secondaryFormSubmit"] {
    background: #171e28 !important;
    border: 1px solid var(--health-border) !important;
    border-radius: 14px !important;
    color: #cbd8ea !important;
    min-height: 2.35rem;
}
[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
    background: #242e3d !important;
    color: #ffffff !important;
}

/* Buttons, controls, upload panels and evidence drawers */
.stButton > button, [data-testid="stDownloadButton"] button {
    border-radius: 12px;
    transition: border-color 150ms ease, background 150ms ease, transform 150ms ease;
}
.stButton > button:focus-visible, input:focus-visible, button:focus-visible {
    outline: 2px solid #9bbcff !important;
    outline-offset: 2px !important;
}
[data-testid="stExpander"] {
    background: rgba(19, 25, 35, 0.62);
    border: 1px solid var(--health-border);
    border-radius: 14px;
    overflow: hidden;
}
[data-testid="stExpander"] summary {
    font-weight: 550;
}
[data-testid="stAlert"] {
    border-radius: 13px;
}
[data-testid="stMetric"] {
    background: rgba(24, 31, 42, 0.75);
    border: 1px solid var(--health-border);
    border-radius: 14px;
    padding: 0.8rem 0.95rem;
}
hr {
    border-color: var(--health-border) !important;
}

/* Small screens: prevent the composer and columns from feeling cramped */
@media (max-width: 760px) {
    [data-testid="stMainBlockContainer"] {
        padding: 0.8rem 0.8rem 1.4rem;
    }
    .gemini-hero-container {
        padding-top: 2.4rem;
    }
    [data-testid="stChatMessage"] {
        padding: 0.8rem;
        border-radius: 14px;
    }
    [data-testid="stForm"] {
        border-radius: 18px !important;
        padding: 0.25rem !important;
    }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
</style>
"""


def apply_gemini_theme(st_module) -> None:
    """Inject the polished dark theme styles."""
    st_module.markdown(GEMINI_THEME_CSS, unsafe_allow_html=True)
