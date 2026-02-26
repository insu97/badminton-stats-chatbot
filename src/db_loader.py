import os
import re
import gspread
import pandas as pd
import sqlite3
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

def normalize_date(date_str: str) -> str:
    """날짜 형식을 YYYY-MM-DD로 통일"""
    if not date_str:
        return date_str
    date_str = re.sub(r'\s+', '', str(date_str))
    date_str = date_str.replace('.', '-').strip('-')
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    except:
        return date_str

def get_gsheet_client():
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=SCOPES
    )
    return gspread.authorize(creds)

def load_main_sheets(spreadsheet, conn):
    target_sheets = {
        "경기기록": "match_records",
        "개인통계": "player_stats",
        "조합통계": "pair_stats"
    }

    for sheet_name, table_name in target_sheets.items():
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # 빈 행 제거
        df = df[df["날짜"] != ""] if "날짜" in df.columns else df

        # 날짜 형식 통일
        if "날짜" in df.columns:
            df["날짜"] = df["날짜"].astype(str).apply(normalize_date)

        df["season"] = "전체"
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"✅ {sheet_name} → {table_name} 저장 완료 ({len(df)}행)")

def load_season1(spreadsheet, conn):
    """시즌1 시트 로드 - 각 섹션 분리 후 기존 테이블에 추가"""
    worksheet = spreadsheet.worksheet("시즌1")
    all_values = worksheet.get_all_values()

    sections = {
        "match_records":  (3, 10),
        "player_stats":   (13, 19),
        "pair_stats":     (22, 30),
    }

    for table_name, (header_row, end_row) in sections.items():
        headers = all_values[header_row]
        rows = all_values[header_row + 1: end_row]
        df = pd.DataFrame(rows, columns=headers)

        # 빈 행 제거
        df = df[df.iloc[:, 0] != ""]

        # 빈 컬럼명 제거
        df = df.loc[:, df.columns != ""]

        # 시즌1 경기기록은 날짜 오름차순 정렬 ← 추가
        if table_name == "match_records" and "날짜" in df.columns:
            df["날짜"] = pd.to_datetime(df["날짜"])
            df = df.sort_values("날짜").reset_index(drop=True)
            df["날짜"] = df["날짜"].astype(str)

        df["season"] = "시즌1"
        df.to_sql(table_name, conn, if_exists="append", index=False)
        print(f"✅ 시즌1 {table_name} 추가 완료 ({len(df)}행)")

def load_sheets_to_sqlite():
    spreadsheet_url = os.getenv("SPREADSHEET_URL")

    if not spreadsheet_url:
        raise ValueError("❌ .env 파일에 SPREADSHEET_URL이 없어요!")

    client = get_gsheet_client()
    spreadsheet = client.open_by_url(spreadsheet_url)

    os.makedirs("db", exist_ok=True)
    conn = sqlite3.connect("db/badminton.db")

    load_main_sheets(spreadsheet, conn)
    load_season1(spreadsheet, conn)

    conn.close()
    print("🎉 SQLite DB 생성 완료!")

if __name__ == "__main__":
    load_sheets_to_sqlite()