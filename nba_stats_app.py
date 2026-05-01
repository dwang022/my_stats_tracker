import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashplayerstats
import plotly.express as px

# -----------------------------------
# PAGE SETUP
# -----------------------------------
st.set_page_config(page_title="NBA Champion + MVP Predictor", layout="wide")

st.title("NBA Champion + MVP Predictor")
st.write("This app uses real NBA data to predict the NBA champion and MVP.")

# -----------------------------------
# CHOOSE A SEASON
# -----------------------------------
season = st.selectbox(
    "Choose a season",
    ["2022-23", "2023-24", "2024-25", "2025-26"],
    index=3
)

# -----------------------------------
# LOAD TEAM DATA
# -----------------------------------
@st.cache_data
def load_team_data(season: str) -> pd.DataFrame:
    team_base = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base"
    ).get_data_frames()[0]

    team_advanced = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced"
    ).get_data_frames()[0]

    team_base = team_base[
        [
            "TEAM_ID",
            "TEAM_NAME",
            "GP",
            "W",
            "L",
            "W_PCT",
            "PTS",
            "REB",
            "AST"
        ]
    ]

    team_advanced = team_advanced[
        [
            "TEAM_ID",
            "OFF_RATING",
            "DEF_RATING",
            "NET_RATING"
        ]
    ]

    team_data = pd.merge(team_base, team_advanced, on="TEAM_ID", how="inner")
    return team_data


# -----------------------------------
# LOAD PLAYER DATA
# -----------------------------------
@st.cache_data
def load_player_data(season: str) -> pd.DataFrame:
    player_base = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base"
    ).get_data_frames()[0]

    player_advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced"
    ).get_data_frames()[0]

    player_base = player_base[
        [
            "PLAYER_ID",
            "PLAYER_NAME",
            "TEAM_ABBREVIATION",
            "GP",
            "MIN",
            "W_PCT",
            "PTS",
            "REB",
            "AST",
            "STL",
            "BLK",
            "TOV"
        ]
    ]

    player_advanced = player_advanced[
        [
            "PLAYER_ID",
            "TS_PCT",
            "PIE"
        ]
    ]

    player_data = pd.merge(player_base, player_advanced, on="PLAYER_ID", how="inner")
    return player_data


# -----------------------------------
# LOAD + CLEAN DATA
# -----------------------------------
with st.spinner("Loading NBA data..."):
    teams = load_team_data(season)
    players = load_player_data(season)

players = players[players["GP"] >= 40]
players = players[players["MIN"] >= 20]

players = players.reset_index(drop=True)
teams = teams.reset_index(drop=True)

teams["W_PCT"] = teams["W_PCT"].round(3)
teams["OFF_RATING"] = teams["OFF_RATING"].round(2)
teams["DEF_RATING"] = teams["DEF_RATING"].round(2)
teams["NET_RATING"] = teams["NET_RATING"].round(2)

players["W_PCT"] = players["W_PCT"].round(3)
players["TS_PCT"] = players["TS_PCT"].round(3)

# -----------------------------------
# MVP SCORE
# -----------------------------------
players["MVP_SCORE"] = (
    players["PTS"] * 1.3 +
    players["AST"] * 1.8 +
    players["REB"] * 0.8 +
    players["STL"] * 1.5 +
    players["BLK"] * 2.0 +
    players["TOV"] * -1.3 +
    players["TS_PCT"] * 40 +
    players["W_PCT"] * 60 +
    players["PIE"] * 80
).round(2)

players_ranked = players.sort_values("MVP_SCORE", ascending=False).reset_index(drop=True)

# -----------------------------------
# CHAMPION SCORE
# -----------------------------------
teams["CHAMPION_SCORE"] = (
    teams["W_PCT"] * 60 +
    teams["NET_RATING"] * 12 +
    teams["OFF_RATING"] * 1.2 +
    teams["DEF_RATING"] * -1.5
).round(2)

teams_ranked = teams.sort_values("CHAMPION_SCORE", ascending=False).reset_index(drop=True)

top_team = teams_ranked.iloc[0]
top_player = players_ranked.iloc[0]

# -----------------------------------
# TOP PREDICTIONS
# -----------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Predicted NBA Champion")
    st.metric("Team", top_team["TEAM_NAME"])
    st.write("Wins:", int(top_team["W"]))
    st.write("Win %:", top_team["W_PCT"])
    st.write("Net Rating:", top_team["NET_RATING"])
    st.write("Champion Score:", top_team["CHAMPION_SCORE"])

with col2:
    st.subheader("Predicted MVP")
    st.metric("Player", top_player["PLAYER_NAME"])
    st.write("Team:", top_player["TEAM_ABBREVIATION"])
    st.write("PPG:", top_player["PTS"])
    st.write("TS%:", top_player["TS_PCT"])
    st.write("MVP Score:", top_player["MVP_SCORE"])

# -----------------------------------
# SIDEBAR FILTERS
# -----------------------------------
st.sidebar.header("Filters")
top_n_teams = st.sidebar.slider("Top teams to show", 5, 30, 10)
top_n_players = st.sidebar.slider("Top players to show", 5, 50, 10)

# -----------------------------------
# TEAM RANKINGS
# -----------------------------------
st.subheader("Team Rankings")

team_display = teams_ranked[
    [
        "TEAM_NAME",
        "W",
        "L",
        "W_PCT",
        "PTS",
        "REB",
        "AST",
        "OFF_RATING",
        "DEF_RATING",
        "NET_RATING",
        "CHAMPION_SCORE"
    ]
].head(top_n_teams).reset_index(drop=True)

team_display.index = team_display.index + 1
st.dataframe(team_display, use_container_width=True)

# -----------------------------------
# MVP RANKINGS
# -----------------------------------
st.subheader("MVP Rankings")

player_display = players_ranked[
    [
        "PLAYER_NAME",
        "TEAM_ABBREVIATION",
        "GP",
        "MIN",
        "PTS",
        "REB",
        "AST",
        "STL",
        "BLK",
        "TOV",
        "TS_PCT",
        "PIE",
        "W_PCT",
        "MVP_SCORE"
    ]
].head(top_n_players).reset_index(drop=True)

player_display.index = player_display.index + 1
st.dataframe(player_display, use_container_width=True)

# -----------------------------------
# CHARTS
# -----------------------------------
st.subheader("Champion Score Chart")

team_chart_df = teams_ranked.head(top_n_teams)

fig = px.bar(
    team_chart_df,
    x="CHAMPION_SCORE",
    y="TEAM_NAME",
    orientation="h",
    title="Top Teams by Champion Score"
)
fig.update_layout(yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, use_container_width=True)

st.subheader("MVP Score Chart")

player_chart_df = players_ranked.head(top_n_players)

fig2 = px.bar(
    player_chart_df,
    x="MVP_SCORE",
    y="PLAYER_NAME",
    orientation="h",
    title="Top MVP Candidates"
)
fig2.update_layout(yaxis=dict(autorange="reversed"))
st.plotly_chart(fig2, use_container_width=True)

# -----------------------------------
# ADVANCED CHAMPIONSHIP LANDSCAPE
# -----------------------------------
st.subheader("Advanced Championship Landscape")

landscape_fig = px.scatter(
    teams_ranked,
    x="OFF_RATING",
    y="DEF_RATING",
    size="W",
    color="CHAMPION_SCORE",
    hover_name="TEAM_NAME",
    text="TEAM_NAME",
    title="Team Contender Map: Offense vs Defense",
    labels={
        "OFF_RATING": "Offensive Rating",
        "DEF_RATING": "Defensive Rating (lower is better)"
    }
)

landscape_fig.update_traces(textposition="top center")
landscape_fig.update_yaxes(autorange="reversed")
st.plotly_chart(landscape_fig, use_container_width=True)

# -----------------------------------
# TEAM EXPLORER
# -----------------------------------
st.subheader("Team Explorer")

selected_team = st.selectbox("Choose a team", teams_ranked["TEAM_NAME"], key="team_explorer")
one_team = teams_ranked[teams_ranked["TEAM_NAME"] == selected_team].copy()

if len(one_team) > 0:
    one_team.index = one_team.index + 1
    one_team.index.name = "Rank"
    st.dataframe(one_team.drop(columns=["TEAM_ID"], errors="ignore"), use_container_width=True)

    team_stat_compare = pd.DataFrame({
        "Stat": ["PTS", "REB", "AST", "OFF_RATING", "DEF_RATING", "NET_RATING"],
        "Team Value": [
            one_team.iloc[0]["PTS"],
            one_team.iloc[0]["REB"],
            one_team.iloc[0]["AST"],
            one_team.iloc[0]["OFF_RATING"],
            one_team.iloc[0]["DEF_RATING"],
            one_team.iloc[0]["NET_RATING"]
        ],
        "League Average": [
            teams["PTS"].mean(),
            teams["REB"].mean(),
            teams["AST"].mean(),
            teams["OFF_RATING"].mean(),
            teams["DEF_RATING"].mean(),
            teams["NET_RATING"].mean()
        ]
    }).round(2)

    st.write("How this team compares to league average:")
    st.dataframe(team_stat_compare, hide_index=True, use_container_width=True)

    team_compare_fig = px.bar(
        team_stat_compare,
        x="Stat",
        y=["Team Value", "League Average"],
        barmode="group",
        title=f"{selected_team} vs League Average"
    )
    st.plotly_chart(team_compare_fig, use_container_width=True)

# -----------------------------------
# PLAYER EXPLORER
# -----------------------------------
st.subheader("Player Explorer")

selected_player = st.selectbox("Choose a player", players_ranked["PLAYER_NAME"], key="player_explorer")
one_player = players_ranked[players_ranked["PLAYER_NAME"] == selected_player].copy()
one_player = one_player.drop(columns=["PLAYER_ID"], errors="ignore")

one_player.index = one_player.index + 1
one_player.index.name = "Rank"

st.dataframe(one_player, use_container_width=True)

# -----------------------------------
# CUSTOM MVP MODEL
# -----------------------------------
st.subheader("Build Your Own MVP Formula")
st.write("Use the sliders to create your own MVP model and see who rises to the top.")

mvp_col1, mvp_col2, mvp_col3 = st.columns(3)

with mvp_col1:
    wt_pts = st.slider("Points weight", 0.0, 5.0, 1.3, 0.1)
    wt_ast = st.slider("Assists weight", 0.0, 5.0, 1.8, 0.1)
    wt_reb = st.slider("Rebounds weight", 0.0, 5.0, 0.8, 0.1)

with mvp_col2:
    wt_stl = st.slider("Steals weight", 0.0, 5.0, 1.5, 0.1)
    wt_blk = st.slider("Blocks weight", 0.0, 5.0, 2.0, 0.1)
    wt_tov = st.slider("Turnovers penalty", -5.0, 0.0, -1.3, 0.1)

with mvp_col3:
    wt_ts = st.slider("TS% weight", 0.0, 100.0, 40.0, 1.0)
    wt_wpct = st.slider("Win % weight", 0.0, 100.0, 60.0, 1.0)
    wt_pie = st.slider("PIE weight", 0.0, 150.0, 80.0, 1.0)

custom_players = players.copy()

custom_players["CUSTOM_MVP_SCORE"] = (
    custom_players["PTS"] * wt_pts +
    custom_players["AST"] * wt_ast +
    custom_players["REB"] * wt_reb +
    custom_players["STL"] * wt_stl +
    custom_players["BLK"] * wt_blk +
    custom_players["TOV"] * wt_tov +
    custom_players["TS_PCT"] * wt_ts +
    custom_players["W_PCT"] * wt_wpct +
    custom_players["PIE"] * wt_pie
).round(2)

custom_players_ranked = custom_players.sort_values("CUSTOM_MVP_SCORE", ascending=False).reset_index(drop=True)
custom_players_ranked.index = custom_players_ranked.index + 1

st.write("Top 10 players using your custom formula:")
st.dataframe(
    custom_players_ranked[
        [
            "PLAYER_NAME",
            "TEAM_ABBREVIATION",
            "PTS",
            "REB",
            "AST",
            "TS_PCT",
            "PIE",
            "W_PCT",
            "CUSTOM_MVP_SCORE"
        ]
    ].head(10),
    use_container_width=True
)