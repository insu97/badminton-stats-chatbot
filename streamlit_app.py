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
    st.title("배드민턴 스탯 챗봇")
    
    if st.button("🔄 데이터 갱신", use_container_width=True):
        refresh_db()
        st.rerun()
    
    st.divider()
    
    with st.expander("📊 통계 질문 예시"):
        st.caption("• 박인수 승률이 어떻게 돼?")
        st.caption("• 장호성과 최승원 파트너 승률은?")
        st.caption("• 시즌1 가장 많이 이긴 선수는?")
    
    with st.expander("📝 후기 질문 예시"):
        st.caption("• 최근 경기 변형섭 컨디션은?")
        st.caption("• 김연준이 자주 하는 실수는?")
        st.caption("• 박인수 개선할 점이 있어?")
    
    st.divider()
    st.caption("Text-to-SQL + RAG 하이브리드 챗봇")

# 메인 화면
st.title("배드민턴 스탯 챗봇")

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