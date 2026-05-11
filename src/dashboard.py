import sqlite3
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

DB_PATH = "db/badminton.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def load_player_stats(season: str = "전체") -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM player_stats WHERE season = ?", conn, params=(season,)
    )
    conn.close()
    # 승률 문자열 → float 변환
    df["승률_float"] = df["승률"].str.replace("%", "").astype(float)
    return df


def load_pair_stats(season: str = "전체") -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql(
        "SELECT * FROM pair_stats WHERE season = ?", conn, params=(season,)
    )
    conn.close()
    df["승률_float"] = df["승률"].str.replace("%", "").astype(float)
    return df


def get_seasons() -> list:
    conn = get_connection()
    df = pd.read_sql("SELECT DISTINCT season FROM player_stats", conn)
    conn.close()
    seasons = df["season"].tolist()
    # "전체"를 맨 앞으로
    if "전체" in seasons:
        seasons.remove("전체")
        seasons.insert(0, "전체")
    return seasons


def render_kpi_cards(player_df: pd.DataFrame):
    """KPI 카드 4개 렌더링"""
    total_games = int(player_df["총경기"].sum() // 4)  # 경기당 4명(팀A 2 + 팀B 2)
    # 최다승: 동률 선수 모두 표시 (승률 높은 순 → 경기수 많은 순)
    max_wins = player_df["승리"].max()
    top_winners = (
        player_df[player_df["승리"] == max_wins]
        .sort_values(["승률_float", "총경기"], ascending=[False, False])
    )
    if len(top_winners) == 1:
        most_wins_value = f"{top_winners.iloc[0]['선수']} ({int(max_wins)}승)"
    else:
        names = ", ".join(top_winners["선수"].tolist())
        most_wins_value = f"{names} ({int(max_wins)}승)"
    # 최고 승률: 총경기 3 이상 필터
    qualified = player_df[player_df["총경기"] >= 3]
    if not qualified.empty:
        best_rate = qualified.loc[qualified["승률_float"].idxmax()]
    else:
        best_rate = player_df.loc[player_df["승률_float"].idxmax()]
    total_players = len(player_df)

    kpi_data = [
        {"label": "총 경기 수", "value": f"{total_games}", "icon": "🏸"},
        {"label": "최다승 선수", "value": most_wins_value, "icon": "🏆"},
        {"label": "최고 승률", "value": f"{best_rate['선수']} ({best_rate['승률']})", "icon": "📈"},
        {"label": "등록 선수", "value": f"{total_players}명", "icon": "👥"},
    ]

    cols = st.columns(4)
    for col, kpi in zip(cols, kpi_data):
        with col:
            st.markdown(f"""
            <div class="kpi-card">
                <div style="font-size: 1.5rem; margin-bottom: 4px;">{kpi['icon']}</div>
                <div class="kpi-value">{kpi['value']}</div>
                <div class="kpi-label">{kpi['label']}</div>
            </div>
            """, unsafe_allow_html=True)


def render_win_rate_chart(player_df: pd.DataFrame):
    """선수별 승률 수평 바 차트"""
    df = player_df.sort_values("승률_float", ascending=True)

    colors = []
    for rate in df["승률_float"]:
        if rate >= 70:
            colors.append("#66BB6A")
        elif rate >= 50:
            colors.append("#FFA726")
        else:
            colors.append("#EF5350")

    fig = go.Figure(go.Bar(
        x=df["승률_float"],
        y=df["선수"],
        orientation="h",
        marker_color=colors,
        text=df["승률"],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "승률: %{x:.1f}%<br>"
            "총경기: %{customdata[0]}<br>"
            "승리: %{customdata[1]} | 패배: %{customdata[2]}"
            "<extra></extra>"
        ),
        customdata=df[["총경기", "승리", "패배"]].values,
    ))

    fig.update_layout(
        title=dict(text="선수별 승률", font=dict(color="#E8F5E9", size=18)),
        xaxis=dict(
            title="승률 (%)",
            range=[0, 105],
            gridcolor="#1e2a3a",
            color="#90A4AE",
        ),
        yaxis=dict(color="#E8F5E9"),
        plot_bgcolor="#0f1117",
        paper_bgcolor="#0f1117",
        font=dict(color="#E8F5E9"),
        margin=dict(l=10, r=20, t=50, b=30),
        height=max(300, len(df) * 40 + 100),
    )

    st.plotly_chart(fig, width="stretch")


def render_pair_chart(pair_df: pd.DataFrame):
    """파트너 조합 TOP 5 승률 수평 바 차트 (순위별 색상)"""
    df = pair_df.sort_values("승률_float", ascending=False).head(5).copy()
    df["조합"] = df["선수1"] + " & " + df["선수2"]

    # 순위 계산 (동률은 같은 순위)
    df["순위"] = df["승률_float"].rank(method="dense", ascending=False).astype(int)

    # 순위별 색상 (1위~5위)
    rank_colors = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32", 4: "#66BB6A", 5: "#42A5F5"}
    colors = [rank_colors.get(r, "#90A4AE") for r in df["순위"]]

    # plotly는 아래→위 순서로 표시
    df = df.sort_values("승률_float", ascending=True)
    colors = colors[::-1]

    fig = go.Figure(go.Bar(
        x=df["승률_float"],
        y=df["조합"],
        orientation="h",
        marker_color=colors,
        text=[f'{row["승률"]} ({int(row["경기수"])}경기)' for _, row in df.iterrows()],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "승률: %{x:.1f}%<br>"
            "경기수: %{customdata[0]}<br>"
            "승리: %{customdata[1]} | 패배: %{customdata[2]}"
            "<extra></extra>"
        ),
        customdata=df[["경기수", "승리", "패배"]].values,
    ))

    fig.update_layout(
        title=dict(text="파트너 조합 TOP 5", font=dict(color="#E8F5E9", size=18)),
        xaxis=dict(
            title="승률 (%)",
            gridcolor="#1e2a3a",
            color="#90A4AE",
            range=[0, 115],
        ),
        yaxis=dict(color="#E8F5E9"),
        plot_bgcolor="#0f1117",
        paper_bgcolor="#0f1117",
        font=dict(color="#E8F5E9"),
        margin=dict(l=10, r=10, t=50, b=30),
        height=280,
    )

    st.plotly_chart(fig, width="stretch")


def render_score_diff_chart(player_df: pd.DataFrame):
    """득실차 랭킹 바 차트"""
    df = player_df.sort_values("득실차", ascending=True)

    colors = ["#66BB6A" if v >= 0 else "#EF5350" for v in df["득실차"]]

    fig = go.Figure(go.Bar(
        x=df["득실차"],
        y=df["선수"],
        orientation="h",
        marker_color=colors,
        text=df["득실차"].apply(lambda x: f"+{int(x)}" if x >= 0 else str(int(x))),
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "득실차: %{x}<br>"
            "총득점: %{customdata[0]} | 총실점: %{customdata[1]}"
            "<extra></extra>"
        ),
        customdata=df[["총득점", "총실점"]].values,
    ))

    fig.update_layout(
        title=dict(text="득실차 랭킹", font=dict(color="#E8F5E9", size=18)),
        xaxis=dict(
            title="득실차",
            gridcolor="#1e2a3a",
            color="#90A4AE",
            zeroline=True,
            zerolinecolor="#90A4AE",
        ),
        yaxis=dict(color="#E8F5E9"),
        plot_bgcolor="#0f1117",
        paper_bgcolor="#0f1117",
        font=dict(color="#E8F5E9"),
        margin=dict(l=10, r=20, t=50, b=30),
        height=max(300, len(df) * 40 + 100),
    )

    st.plotly_chart(fig, width="stretch")


def render_dashboard():
    """대시보드 탭 전체 렌더링"""
    # 시즌 필터
    seasons = get_seasons()
    selected_season = st.selectbox("시즌 선택", seasons, key="dashboard_season")

    player_df = load_player_stats(selected_season)
    pair_df = load_pair_stats(selected_season)

    if player_df.empty:
        st.warning("선택한 시즌에 데이터가 없습니다.")
        return

    # KPI 카드
    render_kpi_cards(player_df)

    st.markdown("<br>", unsafe_allow_html=True)

    # 차트 2열 배치
    col_left, col_right = st.columns(2)

    with col_left:
        render_win_rate_chart(player_df)

    with col_right:
        render_pair_chart(pair_df)

    # 득실차 랭킹
    render_score_diff_chart(player_df)
