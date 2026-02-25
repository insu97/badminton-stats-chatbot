from langchain_core.prompts import PromptTemplate

# Text-to-SQL 프롬프트
TEXT_TO_SQL_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template="""
당신은 배드민턴 경기 기록 데이터베이스 전문가입니다.
아래 테이블 구조를 참고하여 질문에 맞는 SQL 쿼리를 작성하세요.

[테이블 구조]
{schema}

[테이블 설명]
- match_records: 경기 기록 (경기번호, 날짜, 팀A-1, 팀A-2, 팀B-1, 팀B-2, 점수A, 점수B, 승리팀, 점수차, season)
- player_stats: 개인 통계 (선수, 총경기, 승리, 패배, 승률, 총득점, 총실점, 득실차, 평균득점, season)
- pair_stats: 파트너 조합 통계 (선수1, 선수2, 경기수, 승리, 패배, 승률, season)

[규칙]
- 반드시 SQLite 문법을 사용하세요
- 선수 이름은 정확하게 매칭하세요
- season 컬럼은 '전체' 또는 '시즌1' 값을 가집니다
- SQL 쿼리만 반환하고 다른 설명은 하지 마세요

[질문]
{question}

[SQL 쿼리]
"""
)

# RAG 프롬프트
RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""
당신은 배드민턴 경기 후기 분석 전문가입니다.
아래 경기 후기 내용을 참고하여 질문에 답하세요.

[경기 후기]
{context}

[규칙]
- 후기 내용에 없는 정보는 "기록된 후기에서 찾을 수 없습니다"라고 답하세요
- 선수 이름을 정확하게 언급하세요
- 친근하고 자연스러운 한국어로 답하세요

[질문]
{question}

[답변]
"""
)

# 라우터 프롬프트 (질문 유형 판단)
ROUTER_PROMPT = PromptTemplate(
    input_variables=["question"],
    template="""
아래 질문이 어떤 유형인지 판단하세요.

[질문]
{question}

[유형 설명]
- sql: 승률, 점수, 경기 수, 통계 등 수치 데이터를 묻는 질문
- rag: 경기 후기, 컨디션, 플레이 스타일 등 텍스트 기반 질문

반드시 "sql" 또는 "rag" 중 하나만 반환하세요.

[유형]
"""
)