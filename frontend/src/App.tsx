import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Activity, AlertTriangle, ArrowUp, Check, ChevronDown, FileText, HeartPulse, LoaderCircle, Menu, MessageSquare, PanelLeftClose, Plus, Search, Settings2, ShieldCheck, Sparkles, Trash2, Upload, X, MoreHorizontal, Pin, PinOff, Pencil, Share2 } from "lucide-react";
import { api } from "./api";
import type { ChatMessage, Conversation, HealthStatus, LocalDocument } from "./types";

const makeId = () => globalThis.crypto?.randomUUID?.() ?? "chat-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
const suggestions = [
  { icon: "✳", title: "Understand my symptoms", prompt: "What could be causing my symptoms, and when should I seek medical care?" },
  { icon: "▤", title: "Understand a health report", prompt: "Can you explain my health report in simple language and identify values outside the reference ranges?" },
  { icon: "⌁", title: "Understand my test results", prompt: "What do my test results mean, and what questions should I ask my doctor?" },
];
function makeMessage(role: ChatMessage["role"], content: string, extra: Partial<ChatMessage> = {}): ChatMessage {
  return { id: makeId(), role, content, createdAt: Date.now(), ...extra };
}
export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState("");
  const [user, setUser] = useState<{ id: number; email: string } | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [draft, setDraft] = useState("");
  const [search, setSearch] = useState("");
  const [openMenuId, setOpenMenuId] = useState("");
  const [conversationMenuPosition, setConversationMenuPosition] = useState({ top: 8, left: 8 });
  const conversationMenuRef = useRef<HTMLDivElement | null>(null);
  const [model, setModel] = useState("qwen2.5:3b");
  const [models, setModels] = useState<string[]>(["qwen2.5:3b"]);
  const [documents, setDocuments] = useState<LocalDocument[]>([]);
  const [documentChoice, setDocumentChoice] = useState("__most_relevant__");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [documentsOpen, setDocumentsOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const workspaceLoadRef = useRef<Promise<void> | null>(null);
  const active = conversations.find((item) => item.id === activeId) ?? conversations[0];
  const filteredConversations = useMemo(() => conversations.filter((item) => item.title.toLowerCase().includes(search.toLowerCase().trim())).sort((a, b) => Number(b.isPinned) - Number(a.isPinned) || b.updatedAt - a.updatedAt), [conversations, search]);

  const refreshDocuments = useCallback(async (conversationId: string) => {
    try {
      const response = await api.documents(conversationId);
      setDocuments(response.documents);
      setDocumentChoice((current) => current !== "__all__" && current !== "__most_relevant__" && !response.documents.some((doc) => doc.id === current) ? "__most_relevant__" : current);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load this conversation's reports."); }
  }, []);

  const loadWorkspace = useCallback(async () => {
    if (workspaceLoadRef.current) return workspaceLoadRef.current;
    const task = (async () => {
      const existing = await api.conversations();
      if (existing.length === 0) {
        const created = await api.createConversation();
        setConversations([created]);
        setActiveId(created.id);
      } else {
        setConversations(existing);
        setActiveId(existing[0].id);
      }
    })();
    workspaceLoadRef.current = task;
    try { await task; } finally { workspaceLoadRef.current = null; }
  }, []);

  useEffect(() => {
    if (!openMenuId) return;
    const handleOutsidePointer = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (conversationMenuRef.current?.contains(target)) return;
      if (target instanceof Element && target.closest(".conversation-more-button")) return;
      setOpenMenuId("");
    };
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setOpenMenuId("");
    };
    document.addEventListener("pointerdown", handleOutsidePointer);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("pointerdown", handleOutsidePointer);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [openMenuId]);

  useEffect(() => {
    let alive = true;
    Promise.all([api.health(), api.models()]).then(([status, modelInfo]) => {
      if (!alive) return;
      setHealth(status); setModels(modelInfo.models.length ? modelInfo.models : [modelInfo.default_model]); setModel(modelInfo.default_model);
    }).catch((reason: unknown) => { if (alive) setError(reason instanceof Error ? reason.message : "The local API is unavailable."); });
    api.csrf().then(() => api.me()).then(async ({ user: currentUser }) => {
      if (!alive) return;
      await loadWorkspace();
      setUser(currentUser);
    }).catch(() => { if (alive) setUser(null); }).finally(() => { if (alive) setAuthLoading(false); });
    const timer = window.setInterval(() => { api.health().then((status) => { if (alive) setHealth(status); }).catch(() => { if (alive) setHealth(null); }); }, 15000);
    return () => { alive = false; window.clearInterval(timer); };
  }, [loadWorkspace]);

  useEffect(() => {
    if (!user || !activeId) return;
    let alive = true;
    setDocuments([]);
    setDocumentChoice("__most_relevant__");
    Promise.all([api.getConversation(activeId), api.documents(activeId)]).then(([detail, docs]) => {
      if (!alive) return;
      setConversations((current) => current.map((item) => item.id === activeId ? detail.conversation : item));
      setDocuments(docs.documents);
    }).catch((reason: unknown) => { if (alive) setError(reason instanceof Error ? reason.message : "Could not reopen this conversation."); });
    return () => { alive = false; };
  }, [user, activeId]);

  useEffect(() => { bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" }); }, [active?.messages.length, busy]);

  const handleAuthSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      const result = authMode === "register" ? await api.register(email, password) : await api.login(email, password);
      await loadWorkspace();
      setUser(result.user);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not authenticate."); }
  };
  const handleLogout = async () => {
    try { await api.logout(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not log out."); return; }
    workspaceLoadRef.current = null;
    setUser(null); setConversations([]); setActiveId(""); setDocuments([]); setDraft(""); setPassword(""); setEmail("");
  };

  const updateConversation = (id: string, updater: (conversation: Conversation) => Conversation) => setConversations((current) => current.map((item) => item.id === id ? updater(item) : item));
  const newChat = async () => {
    if (!user) return;
    try {
      const next = await api.createConversation();
      setConversations((current) => [next, ...current]);
      setActiveId(next.id); setDraft(""); setError(""); setMobileSidebarOpen(false);
      window.setTimeout(() => textareaRef.current?.focus(), 0);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create a conversation."); }
  };
  const renameConversation = async (conversation: Conversation) => {
    setOpenMenuId("");
    const requested = window.prompt("Rename conversation", conversation.title);
    if (requested === null) return;
    const title = requested.trim();
    if (!title) { setError("Conversation title cannot be empty."); return; }
    if (title.length > 120) { setError("Conversation titles must be 120 characters or fewer."); return; }
    try {
      const updated = await api.updateConversation(conversation.id, { title });
      updateConversation(conversation.id, (item) => ({ ...item, title: updated.title }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not rename this conversation."); }
  };
  const togglePinned = async (conversation: Conversation) => {
    setOpenMenuId("");
    try {
      const updated = await api.updateConversation(conversation.id, { is_pinned: !conversation.isPinned });
      updateConversation(conversation.id, (item) => ({ ...item, isPinned: updated.isPinned }));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update the pin state."); }
  };
  const shareConversation = async (conversation: Conversation) => {
    setOpenMenuId("");
    try {
      // Load the selected conversation's saved messages so sharing works for chats
      // that are not currently open, without exposing any other conversation's reports.
      const detail = await api.getConversation(conversation.id);
      const transcript = detail.conversation.messages.map((message) => (message.role === "user" ? "You" : "HealthAI") + ":\\n" + message.content).join("\\n\\n");
      const shareText = "HealthAI conversation: " + detail.conversation.title + "\\n\\n" + (transcript || "This conversation has no messages yet.");
      if (typeof navigator.share === "function") {
        await navigator.share({ title: detail.conversation.title, text: shareText });
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareText);
        window.alert("Conversation copied to your clipboard. You can now paste it into a message.");
      } else {
        window.prompt("Copy this conversation text to share it:", shareText);
      }
    } catch (reason) {
      if (reason instanceof Error && reason.name === "AbortError") return;
      try {
        const detail = await api.getConversation(conversation.id);
        const transcript = detail.conversation.messages.map((message) => (message.role === "user" ? "You" : "HealthAI") + ":\\n" + message.content).join("\\n\\n");
        const shareText = "HealthAI conversation: " + detail.conversation.title + "\\n\\n" + (transcript || "This conversation has no messages yet.");
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(shareText);
          window.alert("Conversation copied to your clipboard. You can now paste it into a message.");
        } else {
          window.prompt("Copy this conversation text to share it:", shareText);
        }
      } catch {
        setError("Could not share this conversation from this browser.");
      }
    }
  };
  const removeConversation = async (id: string) => {
    const target = conversations.find((item) => item.id === id);
    if (!target || !window.confirm('Delete "' + target.title + '" and its conversation-specific reports? This cannot be undone.')) return;
    setOpenMenuId("");
    try {
      await api.deleteConversation(id);
      const remaining = await api.conversations();
      if (remaining.length === 0) {
        const next = await api.createConversation();
        setConversations([next]); setActiveId(next.id);
      } else {
        setConversations(remaining);
        if (id === activeId) setActiveId(remaining[0].id);
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not delete this conversation."); }
  };

  useEffect(() => {
    const onShortcut = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        void newChat();
      }
    };
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  });

  const sendMessage = async (rawText = draft) => {
    const question = rawText.trim();
    if (!question || busy || !active) return;
    const targetId = active.id; setError(""); setDraft(""); setBusy(true);
    const userMessage = makeMessage("user", question);
    updateConversation(targetId, (conversation) => ({ ...conversation, title: conversation.messages.length === 0 ? question.slice(0, 42) + (question.length > 42 ? "…" : "") : conversation.title, updatedAt: Date.now(), messages: [...conversation.messages, userMessage] }));
    try {
      const result = await api.chat({
        question, model, document_filename: documentChoice === "__all__" ? "__all__" : "__most_relevant__",
        conversation_id: targetId,
        ...(documentChoice !== "__all__" && documentChoice !== "__most_relevant__" ? { document_id: documentChoice } : {}),
      });
      updateConversation(targetId, (conversation) => ({ ...conversation, updatedAt: Date.now(), messages: [...conversation.messages, makeMessage("assistant", result.answer, { result })] }));
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Something went wrong. Please try again.";
      updateConversation(targetId, (conversation) => ({ ...conversation, updatedAt: Date.now(), messages: [...conversation.messages, makeMessage("assistant", message, { error: true })] }));
    } finally { setBusy(false); window.setTimeout(() => textareaRef.current?.focus(), 0); }
  };
  const handleSubmit = (event: FormEvent) => { event.preventDefault(); void sendMessage(); };
  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void sendMessage(); }
  };
  const uploadFile = async (file?: File) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) { setError("Please choose a PDF file."); return; }
    if (file.size > 20 * 1024 * 1024) { setError("PDFs must be 20 MB or smaller."); return; }
    if (!active) { setError("Create or select a conversation before uploading a report."); return; }
    setUploading(true); setError("");
    try { const response = await api.upload(active.id, file); await refreshDocuments(active.id); setDocumentChoice(response.document.id); setDocumentsOpen(true); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The PDF could not be indexed."); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };
  const deleteDocument = async (documentId: string, filename: string) => {
    if (!active || !window.confirm("Permanently delete " + filename + " from this conversation?")) return;
    try { await api.removeDocument(active.id, documentId); await refreshDocuments(active.id); setDocumentChoice((current) => current === documentId ? "__most_relevant__" : current); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not delete that report."); }
  };

  if (authLoading) return <div className="auth-screen"><div className="auth-card"><div className="brand-mark"><HeartPulse size={22} /></div><h1>HealthAI</h1><p>Connecting to your private local workspace…</p></div></div>;
  if (!user) return <div className="auth-screen"><form className="auth-card" onSubmit={(event) => void handleAuthSubmit(event)}><div className="brand-mark"><HeartPulse size={22} /></div><h1>{authMode === "login" ? "Welcome back" : "Create your account"}</h1><p>Your conversations and reports are kept in your local workspace.</p><label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><label>Password<input type="password" autoComplete={authMode === "login" ? "current-password" : "new-password"} minLength={8} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></label>{error && <div className="inline-error" role="alert">{error}</div>}<button className="modal-done" type="submit">{authMode === "login" ? "Log in" : "Create account"}</button><button type="button" className="auth-switch" onClick={() => { setAuthMode((mode) => mode === "login" ? "register" : "login"); setError(""); }}>{authMode === "login" ? "New here? Create an account" : "Already have an account? Log in"}</button><p className="auth-footnote">Local academic prototype. Use a password you do not use for other accounts.</p></form></div>;

  return <div className={"app-shell " + (sidebarCollapsed ? "sidebar-collapsed" : "")}>
    {mobileSidebarOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMobileSidebarOpen(false)} />}
    <aside className={"sidebar " + (mobileSidebarOpen ? "sidebar-mobile-open" : "")}>
      <div className="brand-row"><div className="brand-mark"><HeartPulse size={22} strokeWidth={2.2} /></div><div className="brand-copy"><span className="brand-name">HealthAI</span><span className="brand-caption">Private health companion</span></div><button className="icon-button sidebar-collapse" aria-label="Collapse sidebar" onClick={() => setSidebarCollapsed(true)}><PanelLeftClose size={18} /></button><button className="icon-button mobile-close" aria-label="Close navigation" onClick={() => setMobileSidebarOpen(false)}><X size={18} /></button></div>
      <button className="new-chat-button" onClick={newChat}><Plus size={18} /><span>New chat</span><span className="shortcut">⌘ K</span></button>
      <label className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search conversations" aria-label="Search conversations" />{search && <button type="button" className="search-clear" aria-label="Clear search" onClick={() => setSearch("")}><X size={14} /></button>}</label>
      <div className="sidebar-section-label">Recent</div>
      <nav className="conversation-list" aria-label="Recent conversations">{filteredConversations.length === 0 && <p className="empty-history">No matching conversations.</p>}{filteredConversations.map((conversation) => <div className={"conversation-item " + (conversation.id === activeId ? "conversation-active" : "")} key={conversation.id}><button className="conversation-select" onClick={() => { setActiveId(conversation.id); setOpenMenuId(""); setMobileSidebarOpen(false); }}><MessageSquare size={15} />{conversation.isPinned && <Pin size={12} className="conversation-pin-indicator" aria-label="Pinned" />}<span>{conversation.title}</span></button><button type="button" className="conversation-more-button" aria-label={"Actions for " + conversation.title} title="Conversation actions" aria-haspopup="menu" aria-expanded={openMenuId === conversation.id} onClick={(event) => { if (openMenuId === conversation.id) { setOpenMenuId(""); return; } const rect = event.currentTarget.getBoundingClientRect(); setConversationMenuPosition({ top: Math.max(8, Math.min(rect.top - 66, window.innerHeight - 170)), left: Math.max(8, Math.min(rect.right + 8, window.innerWidth - 198)) }); setOpenMenuId(conversation.id); }}><MoreHorizontal size={17} /></button>{openMenuId === conversation.id && <div ref={conversationMenuRef} className="conversation-menu" style={{ top: conversationMenuPosition.top, left: conversationMenuPosition.left }} role="menu" aria-label={"Actions for " + conversation.title}><button type="button" role="menuitem" onClick={() => void shareConversation(conversation)}><Share2 size={14} />Share conversation</button><button type="button" role="menuitem" onClick={() => void togglePinned(conversation)}>{conversation.isPinned ? <PinOff size={14} /> : <Pin size={14} />}{conversation.isPinned ? "Unpin conversation" : "Pin conversation"}</button><button type="button" role="menuitem" onClick={() => void renameConversation(conversation)}><Pencil size={14} />Rename</button><div className="conversation-menu-divider" /><button type="button" role="menuitem" className="conversation-menu-delete" onClick={() => void removeConversation(conversation.id)}><Trash2 size={14} />Delete</button></div>}</div>)}</nav>
      <div className="sidebar-bottom">
        <button className={"sidebar-action " + (documentsOpen ? "sidebar-action-active" : "")} onClick={() => setDocumentsOpen((open) => !open)}><FileText size={17} /><span>Conversation reports</span><span className="count-pill">{documents.length}</span></button>
        {documentsOpen && <div className="document-library"><div className="document-library-heading">Reports in this conversation</div>{documents.length === 0 ? <p className="document-empty">No PDFs yet. Add one to ask questions about its contents.</p> : documents.map((document) => <div className="document-row" key={document.filename}><FileText size={15} /><button className="document-name" title={document.filename} onClick={() => setDocumentChoice(document.id)}>{document.filename}</button><button className="icon-button document-delete" aria-label={"Delete " + document.filename} onClick={() => void deleteDocument(document.id, document.filename)}><Trash2 size={13} /></button></div>)}<button className="upload-library-button" onClick={() => fileRef.current?.click()}><Upload size={14} /> Add a PDF</button></div>}
        <div className="account-widget">
          <div className="account-avatar" aria-hidden="true">{(user?.email || "U").trim().charAt(0).toUpperCase()}</div>
          <div className="account-identity"><strong>{user?.email?.split("@")[0] || "User"}</strong><span>{user?.email || "Signed-in account"}</span></div>
          <button type="button" className="account-settings-button" aria-label="Account settings" title="Account settings" onClick={() => setSettingsOpen(true)}><Settings2 size={18} /></button>
        </div>
      </div>
    </aside>
    {sidebarCollapsed && <button className="reopen-sidebar" aria-label="Open sidebar" onClick={() => setSidebarCollapsed(false)}><Menu size={19} /></button>}
    <main className="main-panel">
      <header className="topbar"><div className="topbar-left"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileSidebarOpen(true)}><Menu size={20} /></button><div className="breadcrumb"><span>Workspace</span><span className="breadcrumb-slash">/</span><strong>{active?.title || "New chat"}</strong></div></div><div className="topbar-right"><div className={"connection-chip " + (health?.ollama === "online" ? "connection-online" : "connection-offline")}><span className="status-dot" />{health?.ollama === "online" ? "Local AI connected" : "AI offline"}</div><button className="topbar-settings" onClick={() => void handleLogout()} title={"Log out " + user.email}><X size={16} /><span>Log out</span></button><button className="topbar-settings" onClick={() => setSettingsOpen(true)}><Settings2 size={16} /><span>Settings</span></button></div></header>
      <section className="chat-stage" aria-label="Chat workspace">
        <div className={"message-thread " + (active?.messages?.length ? "thread-has-messages" : "thread-welcome")}>
          {!active || !active.messages || active.messages.length === 0 ? <div className="welcome-panel"><div className="welcome-orb"><div className="orb-core"><HeartPulse size={31} /></div><span className="orb-spark orb-spark-one">✳</span><span className="orb-spark orb-spark-two">✦</span></div><div className="eyebrow"><span className="eyebrow-dot" /> YOUR LOCAL HEALTH COMPANION</div><h1>Good health starts<br />with <span>better understanding.</span></h1><p className="welcome-description">Ask general healthcare questions, explore medical documents, and understand retrieved evidence — with your local AI tools.</p><div className="suggestion-grid">{suggestions.map((item) => <button key={item.title} className="suggestion-card" onClick={() => { setDraft(item.prompt); textareaRef.current?.focus(); }}><span className="suggestion-icon">{item.icon}</span><span className="suggestion-title">{item.title}</span><span className="suggestion-prompt">{item.prompt}</span><ArrowUp size={15} className="suggestion-arrow" /></button>)}</div><div className="welcome-note"><ShieldCheck size={15} /> Private, local-first assistance. Not a substitute for professional medical care.</div></div> : <div className="messages">{active.messages.map((message) => <article className={"message message-" + message.role} key={message.id}><div className={"message-avatar " + (message.role === "assistant" ? "assistant-avatar" : "user-avatar")}>{message.role === "assistant" ? <Sparkles size={17} /> : <span>Y</span>}</div><div className="message-body"><div className="message-author">{message.role === "assistant" ? "HealthAI" : "You"}<span>{new Date(message.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></div><div className={"markdown-body " + (message.error ? "message-error" : "")}>{message.role === "assistant" ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown> : <p>{message.content}</p>}</div>{message.result && <div className="answer-meta"><span><Activity size={13} /> {message.result.latency_seconds.toFixed(1)}s</span><span>{message.result.offline_fallback ? "Evidence fallback" : message.result.model || model}</span><span><FileText size={13} /> {message.result.document_sources.length} PDF sources</span></div>}{message.result?.urgent_warning && <div className="urgent-banner"><AlertTriangle size={16} /><span>Potentially urgent symptoms were detected. Seek appropriate emergency medical care if needed.</span></div>}{message.result && (message.result.document_sources.length > 0 || message.result.retrieved_cases.length > 0 || Object.keys(message.result.cohort_statistics).length > 0) && <details className="sources-drawer"><summary><ShieldCheck size={15} /> Sources & supporting evidence <ChevronDown size={15} /></summary><div className="sources-content">{message.result.document_sources.map((source, index) => <div className="source-card" key={source.citation + "-" + index}><div className="source-heading"><FileText size={15} /><strong>{source.citation || "PDF source " + (index + 1)}</strong><span>Similarity {source.score.toFixed(2)}</span></div><p>{source.text}</p></div>)}{message.result.retrieved_cases.map((item, index) => <div className="source-card" key={"case-" + index}><div className="source-heading"><Activity size={15} /><strong>Retrieved clinical record {index + 1}</strong><span>Similarity {item.score.toFixed(2)}</span></div><p>{item.text}</p></div>)}{Object.keys(message.result.cohort_statistics).length > 0 && <pre className="cohort-data">{JSON.stringify(message.result.cohort_statistics, null, 2)}</pre>}</div></details>}{message.result?.disclaimer && <p className="message-disclaimer">{message.result.disclaimer}</p>}</div></article>)}{busy && <article className="message message-assistant"><div className="message-avatar assistant-avatar"><Sparkles size={17} /></div><div className="message-body"><div className="message-author">HealthAI <span>Working locally</span></div><div className="thinking-indicator"><span /><span /><span /><em>Retrieving evidence and preparing a grounded answer…</em></div></div></article>}<div ref={bottomRef} /> </div>}
        </div>
        {error && <div className="inline-error" role="alert"><AlertTriangle size={16} /><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={15} /></button></div>}
        <div className="composer-dock"><form className="composer" onSubmit={handleSubmit}><textarea ref={textareaRef} rows={1} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="Ask HealthAI about a health topic…" aria-label="Ask HealthAI" disabled={busy} /><div className="composer-toolbar"><div className="composer-tools"><button type="button" className="composer-tool" aria-label="Attach a medical PDF" title="Upload a local PDF" onClick={() => fileRef.current?.click()} disabled={uploading}><Plus size={18} /></button><span className="composer-divider" /><label className="model-picker"><span className="model-indicator" /><select value={model} onChange={(event) => setModel(event.target.value)} aria-label="Local AI model">{models.map((name) => <option key={name} value={name}>{name}</option>)}</select><ChevronDown size={13} /></label><label className="document-picker"><FileText size={14} /><select aria-label="PDF source" value={documentChoice} onChange={(event) => setDocumentChoice(event.target.value)}><option value="__most_relevant__">Auto PDF</option><option value="__all__">All reports in this chat</option>{documents.map((document) => <option key={document.id} value={document.id}>{document.filename}</option>)}</select><ChevronDown size={13} /></label></div><button type="submit" className="send-button" aria-label="Send message" disabled={!draft.trim() || busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <ArrowUp size={19} />}</button></div></form><input ref={fileRef} type="file" accept="application/pdf,.pdf" className="visually-hidden" onChange={(event) => void uploadFile(event.target.files?.[0])} />{uploading && <div className="upload-status"><LoaderCircle size={14} className="spin" /> Adding your PDF to the local search index…</div>}<p className="composer-disclaimer"><ShieldCheck size={12} /> Health information can be incomplete or wrong. Verify important decisions with a qualified healthcare professional.</p></div>
      </section>
    </main>
    {settingsOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setSettingsOpen(false); }}><section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title"><div className="modal-header"><div><div className="modal-kicker">WORKSPACE</div><h2 id="settings-title">Settings & privacy</h2></div><button className="icon-button" aria-label="Close settings" onClick={() => setSettingsOpen(false)}><X size={19} /></button></div><div className="settings-callout"><ShieldCheck size={20} /><div><strong>Local-first by design</strong><p>HealthAI is configured to use the Ollama service on this computer. Your chats and reports are saved locally and scoped to your account and each conversation.</p></div></div><div className="settings-row"><div><strong>Frontend</strong><span>React + TypeScript</span></div><span className="settings-status"><Check size={14} /> Running</span></div><div className="settings-row"><div><strong>Backend API</strong><span>127.0.0.1:8000</span></div><span className="settings-status"><Check size={14} /> Connected</span></div><div className="settings-row"><div><strong>Ollama</strong><span>Local model service</span></div><span className={"settings-status " + (health?.ollama !== "online" ? "settings-status-offline" : "")}>{health?.ollama === "online" ? <><Check size={14} /> Online</> : "Offline"}</span></div><div className="settings-row"><div><strong>Conversation reports</strong><span>Private to the selected conversation</span></div><span className="settings-value">{documents.length} files</span></div><div className="settings-footnote">This academic application is not a certified medical device. Local operation alone does not guarantee regulatory compliance or protect against access by other users of this Mac.</div><button className="modal-done" onClick={() => setSettingsOpen(false)}>Done</button></section></div>}
  </div>;
}
