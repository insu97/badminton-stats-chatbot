# 🏸 Badminton Stats Chatbot

> 배드민턴 경기 기록 데이터를 기반으로 자연어로 질문할 수 있는 챗봇

## 📌 프로젝트 소개
Google Sheets에 기록된 배드민턴 경기 데이터를 SQLite DB로 변환하고,
Text-to-SQL 방식으로 자연어 질문에 답하는 챗봇입니다.

## 🛠 기술 스택
- **Language**: Python 3.13
- **Database**: SQLite
- **Framework**: LangChain, Streamlit
- **Data**: Google Sheets API (gspread)
- **LLM**: OpenAI GPT

## 📁 프로젝트 구조
\```
badminton-stats-chatbot/
├── src/
│   ├── db_loader.py    # Google Sheets → SQLite 변환
│   ├── chain.py        # LangChain Text-to-SQL 체인
│   └── prompts.py      # 프롬프트 템플릿
├── db/
│   └── badminton.db    # SQLite DB
├── app.py              # Streamlit 메인 앱
├── requirements.txt
└── .env.example
\```

## ✨ 주요 기능
- Google Sheets 데이터 실시간 연동
- 자연어 질문 → SQL 자동 변환 (Text-to-SQL)
- 시즌별 / 전체 경기 데이터 조회
- 개인 통계 및 파트너 조합 승률 조회

## ⚙️ 실행 방법

**1. 패키지 설치**
\```bash
pip install -r requirements.txt
\```

**2. 환경변수 설정**: .env.example을 참고하여 .env 파일을 생성하세요

**3. DB 생성**
\```bash
python src/db_loader.py
\```

**4. 앱 실행**
\```bash
streamlit run app.py
\```

## 📊 데이터 구조
| 테이블 | 설명 |
|---|---|
| match_records | 경기기록 (시즌1 + 전체) |
| player_stats | 개인 통계 |
| pair_stats | 파트너 조합 통계 |