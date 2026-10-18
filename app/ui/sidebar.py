"""Gemini-styled sidebar navigation matching the clean layout."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import streamlit as st

from app.config.settings import AppSettings
from app.ui.chat_state import ChatSession


def render_sidebar_navigation(st_module, settings: AppSettings) -> dict[str, bool]:
    """Render the dark Gemini-styled sidebar navigation."""
    actions = {
        "new_chat_clicked": False,
        "settings_clicked": False,
    }

    # 1. Header: Gemini Sparkle Icon + Title
    st_module.sidebar.markdown(
        """
        <div style="display:flex;align-items:center;gap:11px;margin:0 0 18px;padding:4px 2px 14px;border-bottom:1px solid rgba(226,232,240,.10);">
            <span style="display:flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:14px;background:linear-gradient(145deg,#263b5b,#182536);border:1px solid rgba(155,188,255,.25);font-size:1.35rem;">✦</span>
            <div>
                <div style="font-size:1.08rem;font-weight:700;color:#eef4ff;letter-spacing:-.025em;">HealthAI</div>
                <div style="font-size:.72rem;color:#92a1b5;margin-top:2px;">Private healthcare assistant</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Pill-shaped New Chat button
    if st_module.sidebar.button("✏️  New chat", use_container_width=True, type="primary"):
        new_sess = ChatSession.create_new()
        st_module.session_state.sessions[new_sess.session_id] = new_sess
        st_module.session_state.active_session_id = new_sess.session_id
        st_module.session_state.temp_mode = False
        st_module.rerun()

    st_module.sidebar.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 3. Searchable Consultations List
    st_module.sidebar.markdown(
        "<p style='font-size:.72rem;font-weight:650;color:#8e9db1;margin:10px 0 8px;text-transform:uppercase;letter-spacing:.12em;'>Your conversations</p>",
        unsafe_allow_html=True,
    )

    search_query = st_module.sidebar.text_input(
        "Search consultations...",
        placeholder="Search past chats",
        label_visibility="collapsed",
        key="search_chat_history",
    ).strip().lower()

    sessions: dict[str, ChatSession] = st_module.session_state.sessions
    matching_sessions = []

    for sid, s in sorted(sessions.items(), key=lambda item: item[1].created_at, reverse=True):
        if s.is_temporary:
            continue
        if not search_query:
            matching_sessions.append((sid, s))
        else:
            title_match = search_query in s.title.lower()
            msg_match = any(search_query in m.get("content", "").lower() for m in s.messages)
            if title_match or msg_match:
                matching_sessions.append((sid, s))

    if not matching_sessions:
        if search_query:
            st_module.sidebar.caption("No matching consultations.")
        else:
            st_module.sidebar.caption("Your conversations will appear here after your first question.")
    else:
        for sid, s in matching_sessions:
            is_active = (sid == st_module.session_state.active_session_id and not st_module.session_state.temp_mode)
            btn_label = f"{'▸ ' if is_active else '  '}{s.title}"
            if st_module.sidebar.button(btn_label, key=f"session_btn_{sid}", use_container_width=True):
                st_module.session_state.active_session_id = sid
                st_module.session_state.temp_mode = False
                st_module.rerun()

    st_module.sidebar.divider()
    if st_module.sidebar.button(
        "⚙️ Settings & system status",
        key="btn_open_settings",
        use_container_width=True,
    ):
        st_module.session_state.show_settings_dialog = True
        actions["settings_clicked"] = True
        st_module.rerun()

    return actions
