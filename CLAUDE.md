# 배드민턴 스탯 챗봇

배드민턴 경기 기록과 후기를 자연어로 질문할 수 있는 Text-to-SQL + RAG 하이브리드 챗봇.

## 기술 스택

- **프론트엔드**: Streamlit (layout=centered, 단일 채팅 UI)
- **LLM**: GPT-4.1-mini (OpenAI API via LangChain)
- **DB**: SQLite (`db/badminton.db`) — Google Sheets에서 자동 로드
- **벡터 DB**: FAISS (`db/faiss/`) — 경기 후기 텍스트 검색용
- **데이터 소스**: Google Sheets (경기기록 시트), 텍스트 파일 (`data/reviews/*.txt`)

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### 환경 변수 (`.env`)

- `OPENAI_API_KEY` — OpenAI API 키
- `SPREADSHEET_URL` — Google Sheets URL
- Google 서비스 계정 인증: `credentials.json` 파일 또는 Streamlit secrets의 `GOOGLE_CREDENTIALS`

## 프로젝트 구조

```
streamlit_app.py          # 진입점 — Streamlit 채팅 UI
src/
  chain.py                # LLM 체인 — 라우터, Text-to-SQL, RAG, 답변 생성
  prompts.py              # 프롬프트 템플릿 (TEXT_TO_SQL, RAG, ROUTER, ANSWER)
  db_loader.py            # Google Sheets → SQLite 로드 + 통계 자동 계산
  rag_loader.py           # 후기 텍스트 → FAISS 벡터 DB 생성/로드
data/reviews/             # 경기 후기 텍스트 파일 (YYYYMMDD.txt)
db/                       # 런타임 생성 — badminton.db, faiss/
```

## 핵심 아키텍처

1. **라우터**: 질문을 `sql` (통계/수치) 또는 `rag` (후기/주관적) 유형으로 분류
2. **SQL 경로**: 프롬프트로 SQL 생성 → SQLite 실행 → 결과를 자연어로 변환
3. **RAG 경로**: FAISS 검색 → 관련 후기 컨텍스트로 답변 생성
   - "최근/마지막" 키워드가 있으면 먼저 SQL로 최신 날짜를 확정한 후 검색 쿼리에 반영

## DB 스키마

- `match_records`: 날짜, 팀A-1, 팀A-2, 팀B-1, 팀B-2, 점수A, 점수B, 승리팀, season
- `player_stats`: 선수, 총경기, 승리, 패배, 승률(문자열 "75.0%"), 총득점, 총실점, 득실차, 평균득점, season
- `pair_stats`: 선수1, 선수2, 경기수, 승리, 패배, 승률(문자열), season

`player_stats`와 `pair_stats`는 `match_records`에서 자동 계산됨 (전체 + 시즌별). 승률은 `"75.0%"` 같은 문자열 형식.

## 주의사항

- 하이픈이 포함된 컬럼명(`팀A-1` 등)은 SQL에서 큰따옴표로 감싸야 함
- `db/` 디렉터리는 gitignore 대상 — 첫 실행 시 자동 생성됨
- `season` 값: `'전체'`, `'시즌1'`, `'시즌2'` 등
