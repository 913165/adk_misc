"""
PDF RAG Manager — Streamlit UI
Upload PDFs, index them into Redis vector store, and chat with an ADK agent.
"""

import asyncio
import io
import os
import time

import pdfplumber
import streamlit as st
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

# ---------------------------------------------------------------------------
# ADK runner helpers (lazy imports to avoid slow startup on every rerun)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_redis_store():
    from rag_agent.redis_store import RedisVectorStore
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return RedisVectorStore(redis_url=redis_url)


def get_agent_runner():
    """Build and cache the ADK Runner + session."""
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from rag_agent.agent import root_agent

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="pdf_rag_app",
        session_service=session_service,
    )
    return runner, session_service


async def _create_session(session_service, session_id: str):
    return await session_service.create_session(
        app_name="pdf_rag_app",
        user_id="streamlit_user",
        session_id=session_id,
    )


async def _run_agent(runner, session_id: str, user_message: str):
    from google.genai import types

    content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id="streamlit_user",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text
    return final_text


# ---------------------------------------------------------------------------
# Streamlit page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="PDF RAG Manager", page_icon="📄", layout="wide")

st.markdown("""
<style>
    .main-header { font-size:2.2rem; font-weight:700; color:#1a1a2e; margin-bottom:0.2rem; }
    .sub-header  { color:#666; font-size:1rem; margin-bottom:2rem; }
    .pdf-card {
        background:#f8f9fa; border:1px solid #e0e0e0; border-radius:12px;
        padding:1.2rem 1.5rem; margin-bottom:1rem; border-left:5px solid #4f46e5;
    }
    .pdf-title { font-size:1.1rem; font-weight:600; color:#1a1a2e; }
    .pdf-meta  { color:#555; font-size:0.85rem; margin-top:0.3rem; }
    .badge {
        display:inline-block; background:#e0e7ff; color:#4f46e5;
        border-radius:6px; padding:2px 10px; font-size:0.8rem; font-weight:600; margin-right:6px;
    }
    .stat-box { background:#f0f4ff; border-radius:10px; padding:1rem; text-align:center; }
    .stat-num { font-size:2rem; font-weight:700; color:#4f46e5; }
    .stat-label { color:#666; font-size:0.85rem; }
    div[data-testid="stFileUploader"] {
        border:2px dashed #c7d2fe; border-radius:12px; padding:1rem; background:#f8f9ff;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "uploaded_pdfs" not in st.session_state:
    st.session_state.uploaded_pdfs = []
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "adk_session_id" not in st.session_state:
    st.session_state.adk_session_id = f"session_{int(time.time())}"
if "session_created" not in st.session_state:
    st.session_state.session_created = False

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown('<div class="main-header">📄 PDF RAG Manager</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">'
    'Upload PDFs → index into Redis vector DB → chat with your documents via Google ADK agent.'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    st.text_input("Redis URL", value=redis_url, disabled=True)
    st.text_input("ADK Model", value=os.getenv("ADK_MODEL", "gemini-2.0-flash"), disabled=True)

    st.markdown("---")
    st.markdown("### 📊 Index Stats")
    try:
        store = get_redis_store()
        indexed_files = store.list_indexed_files()
        st.metric("Indexed Files", len(indexed_files))
        if indexed_files:
            st.markdown("**Files:**")
            for f in indexed_files:
                st.markdown(f"- `{f}`")
    except Exception as e:
        st.error(f"Redis connection error: {e}")

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Drag & drop PDF files here, or click to browse",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files:
    new_names = {f.name for f in uploaded_files}
    existing_names = {pdf["name"] for pdf in st.session_state.uploaded_pdfs}
    new_files = [f for f in uploaded_files if f.name not in existing_names]

    if new_files:
        store = get_redis_store()
        progress = st.progress(0, text="Processing PDFs…")

        for fi, uploaded_file in enumerate(new_files):
            pdf_bytes = uploaded_file.read()
            reader = PdfReader(io.BytesIO(pdf_bytes))
            meta = reader.metadata or {}

            # Extract text from all pages
            pages_data = []
            preview_text = ""
            word_count = 0
            try:
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for pi, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        word_count += len(text.split())
                        if not preview_text and text.strip():
                            preview_text = text[:500].strip()
                        if text.strip():
                            pages_data.append({"page_num": pi + 1, "text": text})
            except Exception:
                preview_text = "Preview not available."

            # Index into Redis
            num_chunks = 0
            if pages_data:
                with st.spinner(f"Indexing {uploaded_file.name} into Redis…"):
                    num_chunks = store.ingest_pdf_text(uploaded_file.name, pages_data)

            pdf_info = {
                "name": uploaded_file.name,
                "size_kb": round(len(pdf_bytes) / 1024, 1),
                "pages": len(reader.pages),
                "title": meta.get("/Title", "—"),
                "author": meta.get("/Author", "—"),
                "subject": meta.get("/Subject", "—"),
                "creator": meta.get("/Creator", "—"),
                "word_count": word_count,
                "chunks_indexed": num_chunks,
                "preview": preview_text,
                "bytes": pdf_bytes,
                "added_at": time.strftime("%b %d, %Y %H:%M"),
            }
            st.session_state.uploaded_pdfs.append(pdf_info)
            progress.progress((fi + 1) / len(new_files), text=f"Processed {fi + 1}/{len(new_files)}")

        st.success(f"✅ {len(new_files)} PDF(s) uploaded and indexed!")
        st.rerun()

# ---------------------------------------------------------------------------
# PDF listing
# ---------------------------------------------------------------------------
if st.session_state.uploaded_pdfs:
    st.markdown("---")

    col_search, col_sort = st.columns([3, 1])
    with col_search:
        search = st.text_input(
            "🔍 Search by filename or author…",
            placeholder="Type to filter…",
            label_visibility="collapsed",
        )
    with col_sort:
        sort_by = st.selectbox("Sort by", ["Name", "Pages", "Size", "Date Added"], label_visibility="collapsed")

    pdfs = st.session_state.uploaded_pdfs
    if search:
        pdfs = [
            p for p in pdfs
            if search.lower() in p["name"].lower()
            or search.lower() in p["author"].lower()
            or search.lower() in p["title"].lower()
        ]

    sort_map = {"Name": "name", "Pages": "pages", "Size": "size_kb", "Date Added": "added_at"}
    pdfs = sorted(pdfs, key=lambda x: x[sort_map[sort_by]], reverse=(sort_by in ["Pages", "Size", "Date Added"]))

    if not pdfs:
        st.info("No PDFs match your search.")
    else:
        for idx, pdf in enumerate(pdfs):
            st.markdown(f"""
            <div class="pdf-card">
                <div class="pdf-title">📄 {pdf['name']}</div>
                <div class="pdf-meta">
                    <span class="badge">📃 {pdf['pages']} pages</span>
                    <span class="badge">💾 {pdf['size_kb']} KB</span>
                    <span class="badge">📝 {pdf['word_count']:,} words</span>
                    <span class="badge">🧩 {pdf.get('chunks_indexed', '?')} chunks</span>
                    &nbsp;&nbsp; Added: {pdf['added_at']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_exp, col_dl, col_del = st.columns([6, 1, 1])
            with col_exp:
                with st.expander("📖 View Details & Preview"):
                    meta_col, prev_col = st.columns([1, 2])
                    with meta_col:
                        st.markdown("**📌 Metadata**")
                        st.markdown(f"- **Title:** {pdf['title']}")
                        st.markdown(f"- **Author:** {pdf['author']}")
                        st.markdown(f"- **Subject:** {pdf['subject']}")
                        st.markdown(f"- **Creator:** {pdf['creator']}")
                        st.markdown(f"- **Pages:** {pdf['pages']}")
                        st.markdown(f"- **File Size:** {pdf['size_kb']} KB")
                        st.markdown(f"- **Word Count:** {pdf['word_count']:,}")
                        st.markdown(f"- **Chunks Indexed:** {pdf.get('chunks_indexed', '?')}")
                    with prev_col:
                        st.markdown("**📄 Text Preview (Page 1)**")
                        if pdf["preview"]:
                            st.text_area(
                                label="preview",
                                value=pdf["preview"],
                                height=180,
                                disabled=True,
                                label_visibility="collapsed",
                            )
                        else:
                            st.info("No text content found (may be a scanned/image PDF).")

            with col_dl:
                st.download_button(
                    label="⬇️",
                    data=pdf["bytes"],
                    file_name=pdf["name"],
                    mime="application/pdf",
                    key=f"dl_{idx}",
                    help="Download PDF",
                )
            with col_del:
                if st.button("🗑️", key=f"del_{idx}", help="Remove PDF"):
                    store = get_redis_store()
                    store.delete_file(pdf["name"])
                    st.session_state.uploaded_pdfs = [
                        p for p in st.session_state.uploaded_pdfs if p["name"] != pdf["name"]
                    ]
                    st.rerun()

    st.markdown("---")
    if st.button("🗑️ Clear All PDFs", type="secondary"):
        store = get_redis_store()
        store.clear_all()
        st.session_state.uploaded_pdfs = []
        st.rerun()
else:
    st.markdown("---")
    st.markdown("""
    <div style='text-align:center; color:#aaa; padding:3rem 0;'>
        <div style='font-size:3rem;'>📂</div>
        <div style='font-size:1.1rem; margin-top:0.5rem;'>No PDFs uploaded yet.</div>
        <div style='font-size:0.9rem;'>Upload one or more PDF files above to get started.</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Chat — ADK-powered RAG
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("#### 💬 Chat with your PDFs  *(powered by Google ADK + Redis)*")

chat_container = st.container(height=350)
with chat_container:
    if not st.session_state.chat_messages:
        st.markdown("""
        <div style='text-align:center; color:#bbb; padding:4rem 0;'>
            <div style='font-size:2rem;'>💬</div>
            <div style='font-size:0.9rem; margin-top:0.5rem;'>
                Ask anything about your uploaded PDFs…
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style='display:flex;justify-content:flex-end;margin-bottom:0.5rem;'>
                    <div style='background:#4f46e5;color:white;padding:0.55rem 1rem;
                                border-radius:16px 16px 4px 16px;max-width:72%;font-size:0.88rem;'>
                        {msg["content"]}
                    </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='display:flex;justify-content:flex-start;margin-bottom:0.5rem;'>
                    <div style='background:#f1f1f1;color:#333;padding:0.55rem 1rem;
                                border-radius:16px 16px 16px 4px;max-width:72%;font-size:0.88rem;'>
                        {msg["content"]}
                    </div>
                </div>""", unsafe_allow_html=True)

user_input = st.chat_input("Type a message…", key="chat_input")
if user_input:
    st.session_state.chat_messages.append({"role": "user", "content": user_input})

    try:
        runner, session_service = get_agent_runner()

        # Create session on first message
        if not st.session_state.session_created:
            asyncio.run(_create_session(session_service, st.session_state.adk_session_id))
            st.session_state.session_created = True

        with st.spinner("🤖 Thinking…"):
            response = asyncio.run(
                _run_agent(runner, st.session_state.adk_session_id, user_input)
            )

        if not response:
            response = "I couldn't generate a response. Please try again."

        st.session_state.chat_messages.append({"role": "assistant", "content": response})

    except Exception as e:
        error_msg = f"⚠️ Error: {str(e)}"
        st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    st.rerun()
