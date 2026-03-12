import os
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate

from src.prompts import TEXT_TO_SQL_PROMPT, RAG_PROMPT, ROUTER_PROMPT, ANSWER_PROMPT
from src.rag_loader import get_retriever

load_dotenv()

def get_llm():
    return ChatOpenAI(
        model="gpt-4.1-mini", # gpt-4o-mini
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

def clean_sql(sql: str) -> str:
    """SQL 쿼리만 추출"""
    # 마크다운 코드 블록 제거
    sql = re.sub(r"```sql|```", "", sql)
    
    # SQLQuery: 이후 SQLResult: 이전 부분만 추출
    if "SQLQuery:" in sql:
        sql = sql.split("SQLQuery:")[-1]
    if "SQLResult:" in sql:
        sql = sql.split("SQLResult:")[0]
    
    sql = sql.strip()
    
    # 괄호 불균형 보정
    open_count = sql.count('(')
    close_count = sql.count(')')
    if open_count > close_count:
        # 세미콜론 앞에 닫는 괄호 추가
        if sql.endswith(';'):
            sql = sql[:-1] + ')' * (open_count - close_count) + ';'
        else:
            sql += ')' * (open_count - close_count)
    
    return sql

def get_sql_answer(question: str) -> str:
    """직접 SQL 생성 → 실행 → 자연어 답변 생성"""
    llm = get_llm()
    db = SQLDatabase.from_uri("sqlite:///db/badminton.db")

    # 1단계 - SQL 생성
    sql_chain = TEXT_TO_SQL_PROMPT | llm | StrOutputParser()
    sql_query = sql_chain.invoke({
        "input": question,
        "table_info": db.get_table_info(),
        "top_k": 5
    })
    sql_query = clean_sql(sql_query)
    print(f"🛠️ 생성된 SQL: {sql_query}")  # 디버깅용

    # 2단계 - SQL 실행
    try:
        sql_result = db.run(sql_query)
    except Exception as e:
        return f"SQL 실행 중 오류가 발생했습니다: {e}"

    # 빈 결과면 LLM 호출 없이 바로 반환
    if not sql_result or sql_result.strip() in ["", "[]", "None"]:
        return "DB에서 해당 데이터를 찾을 수 없습니다. 질문을 좀 더 구체적으로 해주세요."

    # 3단계 - 결과 있을 때만 자연어 변환
    answer_chain = ANSWER_PROMPT | llm | StrOutputParser()
    return answer_chain.invoke({
        "question": question,
        "sql_result": sql_result
    })

def get_rag_chain():
    """RAG 체인 생성"""
    llm = get_llm()
    retriever = get_retriever()

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )
    return chain

def route_question(question: str) -> str:
    """질문 유형 판단 (sql / rag)"""
    llm = get_llm()
    chain = ROUTER_PROMPT | llm | StrOutputParser()
    result = chain.invoke({"question": question})
    return result.strip().lower()

def ask(question: str) -> str:
    question_type = route_question(question)
    print(f"🔀 질문 유형: {question_type}")

    if question_type == "sql":
        return get_sql_answer(question)
    else:
        search_query = question
        db = SQLDatabase.from_uri("sqlite:///db/badminton.db")
        llm = get_llm()

        # 최근/마지막 키워드가 있으면 날짜를 먼저 확정하고 검색 쿼리에 반영
        if any(keyword in question for keyword in ["최근", "마지막", "최신", "저번"]):
            sql_chain = TEXT_TO_SQL_PROMPT | llm | StrOutputParser()
            sql_query = clean_sql(sql_chain.invoke({
                "input": "가장 최근 경기 날짜가 언제야?",
                "table_info": db.get_table_info(),
                "top_k": 1
            }))
            latest_date = db.run(sql_query)
            # 날짜를 질문 앞에 명시적으로 추가
            search_query = f"{latest_date} 날짜 경기 {question}"
            print(f"🔍 검색 쿼리: {search_query}")

        chain = get_rag_chain()
        return chain.invoke(search_query)

if __name__ == "__main__":
    # 테스트
    sql_question = "박인수 승률이 어떻게 돼?"
    rag_question = "최근 경기에서 변형섭 컨디션이 어땠어?"

    print("\n[SQL 테스트]")
    print(ask(sql_question))

    print("\n[RAG 테스트]")
    print(ask(rag_question))