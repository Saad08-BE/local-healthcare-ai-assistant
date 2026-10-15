"""Chat session and multi-conversation state management."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import time
import uuid

from app.llm.rag_pipeline import RAGResponse


@dataclass
class ChatSession:
    """A single conversation session containing messages."""

    session_id: str
    title: str
    created_at: float
    messages: list[dict]
    is_temporary: bool = False

    @classmethod
    def create_new(cls, title: str = "New Consultation", is_temporary: bool = False) -> "ChatSession":
        return cls(
            session_id=str(uuid.uuid4())[:8],
            title=title if not is_temporary else "🔒 Temporary Consultation",
            created_at=time.time(),
            messages=[],
            is_temporary=is_temporary,
        )

    def add_message(self, role: str, content: str, response: RAGResponse | None = None) -> None:
        """Add message to session and auto-update title from first user query."""
        self.messages.append({
            "role": role,
            "content": content,
            "response": response,
            "timestamp": time.time(),
        })
        if role == "user" and (self.title == "New Consultation" or not self.title) and not self.is_temporary:
            # Auto-title conversation using first 30 characters
            clean_title = " ".join(content.strip().split())
            self.title = clean_title[:28] + ("..." if len(clean_title) > 28 else "")


def initialize_session_state(st_module) -> None:
    """Initialize conversation history and active session pointers in st.session_state."""
    if "sessions" not in st_module.session_state:
        st_module.session_state.sessions = {}

    if "active_session_id" not in st_module.session_state or st_module.session_state.active_session_id not in st_module.session_state.sessions:
        first_session = ChatSession.create_new(title="New Consultation")
        st_module.session_state.sessions[first_session.session_id] = first_session
        st_module.session_state.active_session_id = first_session.session_id

    if "temp_mode" not in st_module.session_state:
        st_module.session_state.temp_mode = False

    if "temp_session" not in st_module.session_state:
        st_module.session_state.temp_session = ChatSession.create_new(is_temporary=True)

    if "show_settings_dialog" not in st_module.session_state:
        st_module.session_state.show_settings_dialog = False

    if "show_upload_modal" not in st_module.session_state:
        st_module.session_state.show_upload_modal = False


def get_current_session(st_module) -> ChatSession:
    """Return active session depending on temporary mode."""
    if st_module.session_state.temp_mode:
        return st_module.session_state.temp_session

    active_id = st_module.session_state.active_session_id
    if active_id not in st_module.session_state.sessions:
        new_sess = ChatSession.create_new()
        st_module.session_state.sessions[new_sess.session_id] = new_sess
        st_module.session_state.active_session_id = new_sess.session_id
        return new_sess
    return st_module.session_state.sessions[active_id]
