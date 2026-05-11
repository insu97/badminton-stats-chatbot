import os
import sqlite3
import streamlit as st
from dotenv import load_dotenv
from streamlit_calendar import calendar as st_calendar
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
tab_dashboard, tab_chat, tab_review = st.tabs(["📊 대시보드", "💬 챗봇", "📝 후기 작성"])

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
        st.session_state["pending_question"] = prompt
        st.rerun()


# ── 후기 작성 탭 ──
def get_match_dates() -> list[str]:
    """match_records에서 날짜 목록을 내림차순으로 반환"""
    if not os.path.exists("db/badminton.db"):
        return []
    conn = sqlite3.connect("db/badminton.db")
    try:
        rows = conn.execute(
            "SELECT DISTINCT 날짜 FROM match_records ORDER BY 날짜 DESC"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_matches_for_date(date: str) -> list[dict]:
    """특정 날짜의 경기 목록을 반환"""
    conn = sqlite3.connect("db/badminton.db")
    try:
        rows = conn.execute(
            """SELECT rowid, "팀A-1", "팀A-2", "팀B-1", "팀B-2", 점수A, 점수B
               FROM match_records WHERE 날짜 = ? ORDER BY rowid""",
            (date,)
        ).fetchall()
        matches = []
        for i, r in enumerate(rows, 1):
            matches.append({
                "no": i,
                "label": f"게임 {i}: {r[1]}·{r[2]} vs {r[3]}·{r[4]}  ({r[5]}:{r[6]})",
            })
        return matches
    finally:
        conn.close()


def load_review_file(date: str) -> str:
    """날짜에 해당하는 후기 파일 내용을 읽어 반환 (없으면 빈 문자열)"""
    path = f"data/reviews/{date.replace('-', '')}.txt"
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def save_review_file(date: str, content: str):
    """후기 내용을 파일에 저장"""
    os.makedirs("data/reviews", exist_ok=True)
    path = f"data/reviews/{date.replace('-', '')}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def rebuild_vector_db():
    """후기 파일을 다시 읽어 벡터 DB 재생성"""
    docs = load_reviews()
    chunks = split_documents(docs)
    create_vector_store(chunks)
    st.cache_resource.clear()


def get_review_password() -> str:
    """로컬(.env)과 Streamlit Cloud(secrets) 모두 지원"""
    try:
        return st.secrets.get("REVIEW_PASSWORD", os.getenv("REVIEW_PASSWORD", ""))
    except Exception:
        return os.getenv("REVIEW_PASSWORD", "")


with tab_review:
    st.markdown("### 📝 경기 후기 작성")

    # ── 로컬 전용 게이트 ──
    if os.getenv("REVIEW_ENABLED", "").lower() != "true":
        st.info("📝 후기 작성은 로컬 환경에서만 사용할 수 있습니다.")
        st.stop()

    # ── 비밀번호 인증 게이트 ──
    if not st.session_state.get("review_authenticated"):
        st.markdown(
            "<p style='color:#90A4AE; font-size:0.9rem;'>후기 작성은 인증된 사용자만 가능합니다.</p>",
            unsafe_allow_html=True,
        )
        pwd_input = st.text_input("비밀번호", type="password", key="review_pwd_input")
        if st.button("확인", key="review_pwd_submit"):
            correct = get_review_password()
            if not correct:
                st.error("서버에 REVIEW_PASSWORD가 설정되어 있지 않습니다.")
            elif pwd_input == correct:
                st.session_state["review_authenticated"] = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
        st.stop()

    # 로그아웃
    col_title, col_logout = st.columns([5, 1])
    with col_logout:
        if st.button("🔒 로그아웃", use_container_width=True):
            st.session_state["review_authenticated"] = False
            st.rerun()

    # 범례
    st.markdown(
        "<div style='display:flex; gap:20px; margin-bottom:12px;'>"
        "<span><span style='display:inline-block;width:12px;height:12px;"
        "background:#66BB6A;border-radius:3px;vertical-align:middle;margin-right:5px;'></span>"
        "<span style='color:#90A4AE;font-size:0.82rem;'>경기 있음 (후기 없음)</span></span>"
        "<span><span style='display:inline-block;width:12px;height:12px;"
        "background:#42A5F5;border-radius:3px;vertical-align:middle;margin-right:5px;'></span>"
        "<span style='color:#90A4AE;font-size:0.82rem;'>후기 작성됨</span></span>"
        "</div>",
        unsafe_allow_html=True,
    )

    dates = get_match_dates()
    dates_set = set(dates)

    if not dates:
        st.warning("경기 데이터가 없습니다. 먼저 데이터를 갱신해주세요.")
    else:
        # 달력 이벤트 생성
        cal_events = []
        for d in dates:
            has_review = os.path.exists(f"data/reviews/{d.replace('-', '')}.txt")
            cal_events.append({
                "title": "후기 있음" if has_review else "경기",
                "start": d,
                "backgroundColor": "#42A5F5" if has_review else "#66BB6A",
                "borderColor": "#1565C0" if has_review else "#2E7D32",
                "textColor": "#ffffff",
                "allDay": True,
            })

        cal_options = {
            "initialView": "dayGridMonth",
            "locale": "ko",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "",
            },
            "selectable": True,
            "height": 500,
            "dayMaxEvents": True,
            "eventDisplay": "block",
        }

        custom_css = """
        .fc { background: transparent; }
        .fc-toolbar-title { font-size: 1.05rem !important; font-weight: 700; }
        .fc-button-primary {
            background-color: #2E7D32 !important;
            border-color: #2E7D32 !important;
            font-size: 0.8rem !important;
        }
        .fc-button-primary:hover {
            background-color: #388E3C !important;
            border-color: #388E3C !important;
        }
        .fc-day-today { background: rgba(102,187,106,0.08) !important; }
        .fc-event { cursor: pointer; border-radius: 4px !important; font-size: 0.75rem !important; }
        """

        cal_state = st_calendar(
            events=cal_events,
            options=cal_options,
            custom_css=custom_css,
            key="review_calendar",
        )

        # 클릭 이벤트에서 날짜 추출 후 session_state에 저장
        if cal_state.get("dateClick"):
            clicked = cal_state["dateClick"]["date"][:10]
            if clicked in dates_set:
                st.session_state["review_selected_date"] = clicked
        elif cal_state.get("eventClick"):
            clicked = cal_state["eventClick"]["event"]["start"][:10]
            st.session_state["review_selected_date"] = clicked

        selected_date = st.session_state.get("review_selected_date")

        if not selected_date:
            st.info("📅 달력에서 경기가 있는 날짜를 클릭하세요.")
        else:
            st.divider()
            st.markdown(
                f"<p style='font-weight:700; color:#C8E6C9; font-size:1rem;'>선택된 날짜: {selected_date}</p>",
                unsafe_allow_html=True,
            )

            # 경기 목록
            matches = get_matches_for_date(selected_date)
            if matches:
                with st.expander("📋 해당 날짜 경기 목록", expanded=True):
                    for m in matches:
                        st.markdown(
                            f"<div style='padding:5px 0; color:#C8E6C9; font-size:0.9rem;'>• {m['label']}</div>",
                            unsafe_allow_html=True,
                        )

            # 기존 후기 불러오기
            existing_content = load_review_file(selected_date)
            is_new = existing_content == ""
            status_color = "#90A4AE" if is_new else "#66BB6A"
            status_text = "✏️ 새 후기 작성" if is_new else "📄 기존 후기 수정"
            st.markdown(
                f"<p style='font-size:0.85rem; color:{status_color};'>{status_text}</p>",
                unsafe_allow_html=True,
            )

            review_content = st.text_area(
                label="후기 내용",
                value=existing_content,
                height=320,
                placeholder=f"게임 1: [선수명] ...\n게임 2: [선수명] ...\n\n날짜: {selected_date}",
                key=f"review_text_{selected_date}",
            )

            if st.button("💾 저장 및 벡터 DB 갱신", type="primary"):
                if not review_content.strip():
                    st.error("내용을 입력해주세요.")
                else:
                    with st.spinner("저장 중..."):
                        save_review_file(selected_date, review_content)
                    with st.spinner("벡터 DB 재생성 중..."):
                        rebuild_vector_db()
                    st.success(f"✅ {selected_date} 후기가 저장되었으며 벡터 DB가 갱신되었습니다.")
                    st.rerun()