import os
import streamlit as st
from dotenv import load_dotenv
from src.db_loader import load_sheets_to_sqlite
from src.rag_loader import create_vector_store, load_reviews, split_documents
from src.chain import ask
from src.dashboard import render_dashboard

load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="배드민턴 스탯 챗봇",
    page_icon="🏸",
    layout="wide"
)

# ── CSS 커스텀 스타일 ──
st.markdown("""
<style>
  /* ── 전체 배경 ── */
  .stApp {
    background-color: #0f1117;
  }

  /* ── 사이드바 ── */
  [data-testid="stSidebar"] {
    background-color: #141922;
    border-right: 1px solid #1e2a3a;
  }
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #B0BEC5;
  }

  /* ── 사이드바 버튼 ── */
  [data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, #2E7D32, #388E3C);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s ease;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #388E3C, #43A047);
    box-shadow: 0 4px 12px rgba(102, 187, 106, 0.3);
    transform: translateY(-1px);
  }

  /* ── 채팅 메시지 — assistant ── */
  [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background-color: #1a2332;
    border: 1px solid #243447;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
  }

  /* ── 채팅 메시지 — user ── */
  [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background-color: #0d2818;
    border: 1px solid #1b5e20;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
  }

  /* ── 채팅 입력창 ── */
  [data-testid="stChatInput"] textarea {
    background-color: #1a2332 !important;
    border: 1px solid #2c3e50 !important;
    border-radius: 12px !important;
    color: #E8F5E9 !important;
    padding: 12px 16px !important;
  }
  [data-testid="stChatInput"] textarea:focus {
    border-color: #2c3e50 !important;
    box-shadow: none !important;
  }

  /* ── 제목 ── */
  h1 {
    color: #E8F5E9 !important;
    font-weight: 700 !important;
  }
  h2, h3 {
    color: #C8E6C9 !important;
  }

  /* ── Expander (질문 예시) ── */
  [data-testid="stExpander"] {
    background-color: #1a2332;
    border: 1px solid #243447;
    border-radius: 8px;
  }

  /* ── Divider ── */
  [data-testid="stDivider"] {
    border-color: #1e2a3a;
  }

  /* ── 스크롤바 ── */
  ::-webkit-scrollbar {
    width: 6px;
  }
  ::-webkit-scrollbar-track {
    background: #0f1117;
  }
  ::-webkit-scrollbar-thumb {
    background: #2c3e50;
    border-radius: 3px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: #3d5166;
  }

  /* ── 사이드바 예시 질문 버튼 ── */
  [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
    background-color: #1a2332 !important;
    color: #B0BEC5 !important;
    border: 1px solid #243447 !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-weight: 400 !important;
    text-align: left !important;
    padding: 8px 12px !important;
    transition: all 0.2s ease;
  }
  [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
    background-color: #243447 !important;
    color: #E8F5E9 !important;
    border-color: #66BB6A !important;
  }

  /* ── KPI 카드 ── */
  .kpi-card {
    background: linear-gradient(135deg, #1a2332, #243447);
    border: 1px solid #2c3e50;
    border-radius: 12px;
    padding: 20px 16px;
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(102, 187, 106, 0.15);
  }
  .kpi-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #66BB6A;
    margin: 4px 0;
  }
  .kpi-label {
    font-size: 0.8rem;
    color: #90A4AE;
    margin-top: 4px;
  }

  /* ── Spinner ── */
  .stSpinner > div {
    border-top-color: #66BB6A !important;
  }

  /* ── 탭 스타일 ── */
  .stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: transparent;
    border-bottom: 1px solid #1e2a3a;
  }
  .stTabs [data-baseweb="tab"] {
    font-size: 1rem;
    font-weight: 600;
    color: #90A4AE;
    padding: 10px 24px;
    border: none !important;
    background-color: transparent !important;
  }
  .stTabs [aria-selected="true"] {
    color: #66BB6A !important;
    background-color: transparent !important;
    border: none !important;
  }
  .stTabs [data-baseweb="tab-highlight"] {
    background-color: #66BB6A !important;
    height: 2px !important;
  }
  .stTabs [data-baseweb="tab-border"] {
    display: none;
  }
</style>
""", unsafe_allow_html=True)

# DB 초기화 함수
@st.cache_resource
def init_db():
    if not os.path.exists("db/badminton.db"):
        with st.spinner("DB 생성 중..."):
            load_sheets_to_sqlite()
    # FAISS 폴더가 있어도 index.faiss 파일 없으면 재생성
    if not os.path.exists("db/faiss/index.faiss"):
        with st.spinner("Vector DB 생성 중..."):
            docs = load_reviews()
            chunks = split_documents(docs)
            create_vector_store(chunks)

def refresh_db():
    """수동 갱신 - DB 전체 재생성"""
    with st.spinner("데이터 갱신 중..."):
        load_sheets_to_sqlite()
        docs = load_reviews()
        chunks = split_documents(docs)
        create_vector_store(chunks)
    st.cache_resource.clear()
    st.success("✅ 데이터 갱신 완료!")

# 첫 실행 시 자동 초기화
init_db()

# 질문 예시 목록
EXAMPLE_QUESTIONS = {
    "📊 통계 질문": [
        "박인수 승률이 어떻게 돼?",
        "장호성과 최승원 파트너 승률은?",
        "시즌1 가장 많이 이긴 선수는?",
    ],
    "📝 후기 질문": [
        "최근 경기 변형섭 컨디션은?",
        "김연준이 자주 하는 실수는?",
        "박인수 개선할 점이 있어?",
    ],
}

# 사이드바
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 16px 0 8px;">
        <div style="font-size: 2.5rem;">🏸</div>
        <div style="font-size: 1.2rem; font-weight: 700; color: #E8F5E9; margin-top: 4px;">배드민턴 스탯 챗봇</div>
        <div style="font-size: 0.75rem; color: #90A4AE; margin-top: 2px;">Text-to-SQL + RAG 하이브리드</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if st.button("🔄 데이터 갱신", use_container_width=True):
        refresh_db()
        st.rerun()

    st.divider()

    # 질문 예시 버튼
    for category, questions in EXAMPLE_QUESTIONS.items():
        st.markdown(f"<p style='font-size:0.85rem; font-weight:600; color:#90A4AE; margin-bottom:4px;'>{category}</p>", unsafe_allow_html=True)
        for q in questions:
            if st.button(q, key=f"example_{q}", use_container_width=True):
                st.session_state["example_question"] = q
                st.rerun()
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

    st.divider()

    # 하단 정보
    st.markdown("""
    <div style="text-align: center; padding: 4px 0;">
        <div style="font-size: 0.7rem; color: #546E7A;">v1.0 | GPT-4.1-mini</div>
    </div>
    """, unsafe_allow_html=True)

# ── 탭 구조 ──
tab_dashboard, tab_chat = st.tabs(["📊 대시보드", "💬 챗봇"])

# ── 대시보드 탭 ──
with tab_dashboard:
    render_dashboard()

# ── 답변 생성 헬퍼 ──
def generate_response(question: str):
    """st.status로 진행 단계를 보여주며 답변 생성"""
    step_labels = {
        "route": "🔀 질문 유형 분석 중...",
        "sql_generate": "🛠️ SQL 쿼리 생성 중...",
        "sql_execute": "🗄️ DB 조회 중...",
        "answer_generate": "💬 답변 생성 중...",
        "date_lookup": "📅 최근 경기 날짜 조회 중...",
        "rag_search": "🔍 경기 후기 검색 중...",
    }

    with st.status("답변 생성 중...", expanded=True) as status:
        def update_status(step: str, message: str):
            status.update(label=step_labels.get(step, message))
            st.write(step_labels.get(step, message))

        try:
            response = ask(question, status_callback=update_status)
            status.update(label="✅ 답변 완료", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ 오류 발생", state="error", expanded=False)
            response = None
            st.error(f"답변 생성 중 오류가 발생했습니다: {e}")

    return response


# ── 챗봇 탭 ──
with tab_chat:
    # 채팅 기록 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": "안녕하세요! 배드민턴 경기 기록과 후기에 대해 질문해보세요 🏸"
        })

    # 예시 질문 버튼 클릭 처리 — rerun 전에 pending으로 등록
    if "example_question" in st.session_state:
        eq = st.session_state.pop("example_question")
        st.session_state.messages.append({"role": "user", "content": eq})
        st.session_state["pending_question"] = eq

    # pending 질문이 있으면 응답 생성
    if "pending_question" in st.session_state:
        pending = st.session_state.pop("pending_question")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        with st.chat_message("assistant"):
            response = generate_response(pending)
            if response:
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 질문 입력
    if prompt := st.chat_input("질문을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = generate_response(prompt)
            if response:
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})