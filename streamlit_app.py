"""
🤖 Chatbot Kinh Tế Việt Nam - Streamlit Frontend
Giao diện demo cho hệ thống RAG với Energy-Based Distance Retriever.
"""
import os
import sys
import time
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
# Load env và setup path
load_dotenv()
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
from chatbot.main import ChatbotRunner
# ──────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Chatbot Kinh Tế Việt Nam",
    page_icon="🇻🇳",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ──────────────────────────────────────────────
# Custom CSS - Premium Dark Theme
# ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    /* ── Global ── */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    /* ── Main header ── */
    .main-header {
        text-align: center;
        padding: 1.5rem 0 1rem;
    }
    .main-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .main-header p {
        color: #9ca3af;
        font-size: 0.95rem;
        font-weight: 300;
    }
    /* ── Chat message containers ── */
    .user-msg {
        background: linear-gradient(135deg, #667eea22, #764ba222);
        border: 1px solid #667eea44;
        border-radius: 16px 16px 4px 16px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        animation: fadeInUp 0.3s ease;
    }
    .bot-msg {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 16px 16px 16px 4px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        animation: fadeInUp 0.4s ease;
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    /* ── Stat cards ── */
    .stat-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        border-color: #667eea;
    }
    .stat-value {
        font-size: 1.6rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stat-label {
        font-size: 0.75rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 0.2rem;
    }
    /* ── Sidebar styling ── */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #334155;
    }
    .sidebar-title {
        font-size: 1rem;
        font-weight: 600;
        color: #e2e8f0;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    /* ── Source docs expander ── */
    .source-doc {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.4rem 0;
        font-size: 0.85rem;
        line-height: 1.5;
        color: #cbd5e1;
    }
    .source-doc-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #667eea;
        margin-bottom: 0.4rem;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }
    /* ── Badge ──*/
    .badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .badge-green {
        background: #065f4620;
        color: #34d399;
        border: 1px solid #34d39944;
    }
    .badge-blue {
        background: #667eea20;
        color: #818cf8;
        border: 1px solid #818cf844;
    }
    .badge-amber {
        background: #92400e20;
        color: #fbbf24;
        border: 1px solid #fbbf2444;
    }
    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #334155, transparent);
        margin: 1rem 0;
    }
    /* ── Footer ── */
    .footer {
        text-align: center;
        padding: 1.5rem 0 0.5rem;
        color: #4b5563;
        font-size: 0.75rem;
    }
    /* Hide default streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Input styling */
    .stChatInput > div {
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)
# ──────────────────────────────────────────────
# Session State Initialization
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chatbot" not in st.session_state:
    st.session_state.chatbot = None
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0
if "total_time" not in st.session_state:
    st.session_state.total_time = 0.0
if "current_llm" not in st.session_state:
    st.session_state.current_llm = "openai"
# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">⚙️ Cấu Hình Hệ Thống</div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    # LLM Provider Selection
    llm_options = {
        "openai": "🟢 OpenAI (GPT)",
        "gemini": "🔵 Google Gemini",
        "groq": "🟡 Groq (Llama)",
    }
    selected_llm = st.selectbox(
        "🤖 Chọn LLM Provider",
        options=list(llm_options.keys()),
        format_func=lambda x: llm_options[x],
        index=0,
        key="llm_selector",
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    # System Prompt
    st.markdown('<div class="sidebar-title">📝 System Prompt</div>', unsafe_allow_html=True)
    custom_prompt = st.text_area(
        "Tùy chỉnh prompt hệ thống",
        value="Bạn là một chuyên gia tư vấn kinh tế Việt Nam.\nHãy trả lời câu hỏi CHỈ dựa trên thông tin trong ngữ cảnh được cung cấp.\nNếu ngữ cảnh không chứa thông tin cần thiết, hãy nói rõ là không có thông tin.",
        height=130,
        key="custom_prompt",
        label_visibility="collapsed",
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    # Pipeline info
    st.markdown('<div class="sidebar-title">🔧 Thông Số Pipeline</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="source-doc" style="font-size: 0.8rem;">
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="color:#9ca3af">Embedding</span>
            <span class="badge badge-blue">multilingual-e5-base</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="color:#9ca3af">Retrieval</span>
            <span class="badge badge-green">Energy Distance</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="color:#9ca3af">Top-K Cosine</span>
            <span class="badge badge-amber">40 docs</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="color:#9ca3af">Clustering</span>
            <span class="badge badge-blue">K-Means (auto)</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="color:#9ca3af">Top Clusters</span>
            <span class="badge badge-green">1 cluster</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    # Clear chat button
    if st.button("🗑️ Xóa Lịch Sử Chat", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.session_state.total_questions = 0
        st.session_state.total_time = 0.0
        st.rerun()
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="footer">
        <div style="color:#667eea; font-weight:600; margin-bottom:2px;">RAG Chatbot v1.0</div>
        Energy-Based Distance Retriever
    </div>
    """, unsafe_allow_html=True)
# ──────────────────────────────────────────────
# Init / Re-init chatbot when LLM changes
# ──────────────────────────────────────────────
VECTOR_STORE_PATH = str(PROJECT_ROOT / "chroma_economy_db")
def init_chatbot(llm_provider: str):
    """Khởi tạo chatbot với LLM provider được chọn."""
    if not os.path.exists(VECTOR_STORE_PATH):
        st.error(f"❌ Vector store không tìm thấy tại `{VECTOR_STORE_PATH}`")
        st.info("💡 Vui lòng chạy: `python ingestion/vector_data_builder.py`")
        st.stop()
    with st.spinner(f"🚀 Đang khởi tạo chatbot ({llm_provider})... Có thể mất 30-60s lần đầu"):
        try:
            bot = ChatbotRunner(
                path_vector_store=VECTOR_STORE_PATH,
                llm_provider=llm_provider,
            )
            return bot
        except Exception as e:
            st.error(f"❌ Lỗi khởi tạo: {e}")
            st.stop()
# Re-init if LLM changed or not yet created
if st.session_state.chatbot is None or st.session_state.current_llm != selected_llm:
    st.session_state.chatbot = init_chatbot(selected_llm)
    st.session_state.current_llm = selected_llm
# ──────────────────────────────────────────────
# Main Content
# ──────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🇻🇳 Chatbot Kinh Tế Việt Nam</h1>
    <p>Hệ thống hỏi đáp thông minh sử dụng RAG với Energy-Based Distance</p>
</div>
""", unsafe_allow_html=True)
# Stats row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{st.session_state.total_questions}</div>
        <div class="stat-label">Câu hỏi</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    avg_time = (st.session_state.total_time / st.session_state.total_questions) if st.session_state.total_questions > 0 else 0
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{avg_time:.1f}s</div>
        <div class="stat-label">TB Response</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{selected_llm.upper()}</div>
        <div class="stat-label">LLM Provider</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    status = "🟢 Online" if st.session_state.chatbot else "🔴 Offline"
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value" style="font-size:1.1rem;">{status}</div>
        <div class="stat-label">Trạng Thái</div>
    </div>
    """, unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
# ──────────────────────────────────────────────
# Chat History Display
# ──────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        # Show source documents if available
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(f"📄 Xem {len(msg['sources'])} tài liệu nguồn", expanded=False):
                for i, doc in enumerate(msg["sources"]):
                    source_name = doc.metadata.get("source", "Không rõ nguồn")
                    st.markdown(f"""
                    <div class="source-doc">
                        <div class="source-doc-title">📑 Tài liệu {i+1} — {Path(source_name).name if source_name != "Không rõ nguồn" else source_name}</div>
                        {doc.page_content[:500]}{'...' if len(doc.page_content) > 500 else ''}
                    </div>
                    """, unsafe_allow_html=True)
        # Show timing
        if msg["role"] == "assistant" and msg.get("time"):
            st.caption(f"⏱️ {msg['time']:.2f}s")
# ──────────────────────────────────────────────
# Chat Input
# ──────────────────────────────────────────────
if user_input := st.chat_input("💬 Nhập câu hỏi về kinh tế Việt Nam..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
    # Generate response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🔍 Đang truy xuất và phân tích tài liệu..."):
            start_time = time.time()
            try:
                # Prepare input state
                input_state = {
                    "question": user_input,
                    "generation": "",
                    "documents": [],
                    "prompt": custom_prompt,
                }
                # Run workflow
                output_state = st.session_state.chatbot.compiled_workflow.invoke(input_state)
                elapsed = time.time() - start_time
                answer = output_state.get("generation", "❌ Không thể tạo câu trả lời.")
                docs = output_state.get("documents", [])
            except Exception as e:
                elapsed = time.time() - start_time
                answer = f"❌ Lỗi xử lý: {str(e)}"
                docs = []
        # Display answer
        st.markdown(answer)
        # Show source documents
        if docs:
            with st.expander(f"📄 Xem {len(docs)} tài liệu nguồn", expanded=False):
                for i, doc in enumerate(docs):
                    source_name = doc.metadata.get("source", "Không rõ nguồn")
                    st.markdown(f"""
                    <div class="source-doc">
                        <div class="source-doc-title">📑 Tài liệu {i+1} — {Path(source_name).name if source_name != "Không rõ nguồn" else source_name}</div>
                        {doc.page_content[:500]}{'...' if len(doc.page_content) > 500 else ''}
                    </div>
                    """, unsafe_allow_html=True)
        st.caption(f"⏱️ {elapsed:.2f}s")
    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": docs,
        "time": elapsed,
    })
    st.session_state.total_questions += 1
    st.session_state.total_time += elapsed