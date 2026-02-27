import os
import re
import sqlite3
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

DB_PATH = "db/badminton.db"


def get_gsheet_client():
    try:
        import streamlit as st
        import json
        creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    except Exception:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)


def normalize_date(date_str: str) -> str:
    """날짜 형식을 YYYY-MM-DD로 통일"""
    if not date_str:
        return date_str
    date_str = re.sub(r'\s+', '', str(date_str))
    date_str = date_str.replace('.', '-').strip('-')
    try:
        from datetime import datetime
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    except:
        return date_str


def calc_player_stats(df: pd.DataFrame, season: str) -> pd.DataFrame:
    """경기기록에서 개인통계 자동 계산"""
    stats = {}

    for _, row in df.iterrows():
        team_a = [row['팀A-1'], row['팀A-2']]
        team_b = [row['팀B-1'], row['팀B-2']]
        score_a, score_b = row['점수A'], row['점수B']
        winner = row['승리팀']

        for player in team_a:
            if player not in stats:
                stats[player] = {'승리': 0, '패배': 0, '총득점': 0, '총실점': 0}
            stats[player]['총득점'] += score_a
            stats[player]['총실점'] += score_b
            if winner == 'A':
                stats[player]['승리'] += 1
            else:
                stats[player]['패배'] += 1

        for player in team_b:
            if player not in stats:
                stats[player] = {'승리': 0, '패배': 0, '총득점': 0, '총실점': 0}
            stats[player]['총득점'] += score_b
            stats[player]['총실점'] += score_a
            if winner == 'B':
                stats[player]['승리'] += 1
            else:
                stats[player]['패배'] += 1

    rows = []
    for player, s in stats.items():
        total = s['승리'] + s['패배']
        win_rate = f"{round(s['승리'] / total * 100, 1)}%" if total > 0 else "0.0%"
        avg_score = round(s['총득점'] / total, 1) if total > 0 else 0
        rows.append({
            '선수': player,
            '총경기': total,
            '승리': s['승리'],
            '패배': s['패배'],
            '승률': win_rate,
            '총득점': s['총득점'],
            '총실점': s['총실점'],
            '득실차': s['총득점'] - s['총실점'],
            '평균득점': avg_score,
            'season': season
        })
    return pd.DataFrame(rows)


def calc_pair_stats(df: pd.DataFrame, season: str) -> pd.DataFrame:
    """경기기록에서 조합통계 자동 계산"""
    stats = {}

    for _, row in df.iterrows():
        pairs = [
            tuple(sorted([row['팀A-1'], row['팀A-2']])),
            tuple(sorted([row['팀B-1'], row['팀B-2']]))
        ]
        winner = row['승리팀']

        for i, pair in enumerate(pairs):
            if pair not in stats:
                stats[pair] = {'승리': 0, '패배': 0}
            if (i == 0 and winner == 'A') or (i == 1 and winner == 'B'):
                stats[pair]['승리'] += 1
            else:
                stats[pair]['패배'] += 1

    rows = []
    for (p1, p2), s in stats.items():
        total = s['승리'] + s['패배']
        win_rate = f"{round(s['승리'] / total * 100, 1)}%" if total > 0 else "0.0%"
        rows.append({
            '선수1': p1,
            '선수2': p2,
            '경기수': total,
            '승리': s['승리'],
            '패배': s['패배'],
            '승률': win_rate,
            'season': season
        })
    return pd.DataFrame(rows)


def load_sheets_to_sqlite():
    """Google Sheets 경기기록 → SQLite DB 저장 + 통계 자동 계산"""
    os.makedirs("db", exist_ok=True)

    client = get_gsheet_client()
    spreadsheet = client.open_by_url(os.getenv("SPREADSHEET_URL"))

    # 경기기록 시트 로드
    worksheet = spreadsheet.worksheet("경기기록")
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)

    # 빈 행 제거
    df = df[df['날짜'] != '']
    df = df[df['날짜'].astype(str).str.strip() != '']

    # 날짜 정규화
    df['날짜'] = df['날짜'].astype(str).apply(normalize_date)

    conn = sqlite3.connect(DB_PATH)

    # match_records 저장
    df = df.rename(columns={'시즌': 'season'})
    df.to_sql('match_records', conn, if_exists='replace', index=False)

    # 시즌 목록 추출
    seasons = df['season'].unique().tolist()

    # 개인통계 자동 계산 (전체 + 시즌별)
    player_dfs = [calc_player_stats(df, '전체')]
    for season in seasons:
        season_df = df[df['season'] == season]
        player_dfs.append(calc_player_stats(season_df, season))
    pd.concat(player_dfs, ignore_index=True).to_sql('player_stats', conn, if_exists='replace', index=False)
    print(f"✅ player_stats 저장 완료 (시즌: {['전체'] + seasons})")

    # 조합통계 자동 계산 (전체 + 시즌별)
    pair_dfs = [calc_pair_stats(df, '전체')]
    for season in seasons:
        season_df = df[df['season'] == season]
        pair_dfs.append(calc_pair_stats(season_df, season))
    pd.concat(pair_dfs, ignore_index=True).to_sql('pair_stats', conn, if_exists='replace', index=False)
    print(f"✅ pair_stats 저장 완료 (시즌: {['전체'] + seasons})")

    conn.close()
    print("🎉 DB 생성 완료!")


if __name__ == "__main__":
    load_sheets_to_sqlite()