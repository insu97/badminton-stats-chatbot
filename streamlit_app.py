import os
import streamlit as st
from dotenv import load_dotenv
from src.db_loader import load_sheets_to_sqlite
from src.rag_loader import create_vector_store, load_reviews, split_documents
from src.chain import ask

load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="배드민턴 스탯 챗봇",
    page_icon="🏸",
    layout="centered"
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
  }
  [data-testid="stChatInput"] textarea:focus {
    border-color: #66BB6A !important;
    box-shadow: 0 0 0 2px rgba(102, 187, 106, 0.2) !important;
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

  /* ── Spinner ── */
  .stSpinner > div {
    border-top-color: #66BB6A !important;
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

# 사이드바
with st.sidebar:
    st.markdown("### 🏸 배드민턴 스탯 챗봇")
    st.caption("Text-to-SQL + RAG 하이브리드")

    st.divider()

    if st.button("🔄 데이터 갱신", use_container_width=True):
        refresh_db()
        st.rerun()

    st.divider()

    with st.expander("📊 통계 질문 예시", expanded=False):
        st.markdown("""
        - 박인수 승률이 어떻게 돼?
        - 장호성과 최승원 파트너 승률은?
        - 시즌1 가장 많이 이긴 선수는?
        """)

    with st.expander("📝 후기 질문 예시", expanded=False):
        st.markdown("""
        - 최근 경기 변형섭 컨디션은?
        - 김연준이 자주 하는 실수는?
        - 박인수 개선할 점이 있어?
        """)

# 메인 화면
st.markdown("# 🏸 배드민턴 스탯 챗봇")

# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "안녕하세요! 배드민턴 경기 기록과 후기에 대해 질문해보세요 🏸"
    })

# 채팅 기록 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 질문 입력
if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            response = ask(prompt)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})