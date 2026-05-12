import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashplayerstats
import plotly.express as px
from pybaseball import batting_stats_range, pitching_stats_range
import nflreadpy as nfl
import sqlite3
import anthropic
import openai
import hashlib

from ai_coach import render_ai_coach_section, render_coach_roster_ai_report



# We need a virtual environment and to install all of our packages in it then activate it and run app

# cd ~/Desktop/Rylan_Project
# python3.10 -m venv sports_app_env
# source sports_app_env/bin/activate
# python -m pip install --upgrade pip setuptools wheel
# python -m pip install \
#   streamlit pandas nba_api pybaseball nflreadpy anthropic openai \
#   plotly Pillow requests "polars[rtcompat]"
# python -m pip install \
#   numba==0.60.0 llvmlite==0.43.0 onnxruntime rembg

# source sports_app_env/bin/activate
# python -m streamlit run my_stats_tracker.py



# -----------------------------------
# USER ID SYSTEM
# -----------------------------------

def get_user_id():
    """
    Returns the current user's ID from session state.
    Users set their own username/ID in the sidebar login widget.
    The ID is hashed to create a safe DB key prefix.
    """
    return st.session_state.get("user_id", None)


def user_table_key(base_key):
    """Namespace a DB table key with the current user's ID."""
    uid = get_user_id()
    if uid:
        safe = hashlib.md5(uid.encode()).hexdigest()[:12]
        return f"u_{safe}_{base_key}"
    return base_key

def render_user_sidebar():
    """Render the user login/ID widget in a collapsible sidebar section."""
    st.sidebar.markdown("---")

    with st.sidebar.expander("👤 User ID", expanded=not bool(get_user_id())):
        if get_user_id():
            st.success(f"Logged in as: **{st.session_state.user_id}**")

            if st.button("Switch User / Log Out"):
                for key in list(st.session_state.keys()):
                    if key not in ["page", "sport"]:
                        del st.session_state[key]
                st.session_state.user_id = None
                st.rerun()

        else:
            st.info("Enter a username to keep your stats separate from other users.")

            username_input = st.text_input(
                "Username",
                placeholder="e.g. john_doe",
                key="username_input"
            )

            if st.button("Set User ID"):
                if username_input.strip() == "":
                    st.error("Please enter a username.")
                else:
                    st.session_state.user_id = username_input.strip()

                    for tkey in list(TABLES.keys()):
                        if tkey in st.session_state:
                            del st.session_state[tkey]

                    st.rerun()

            st.caption(
                "⚠️ Anyone with the same username can access that data, so pick something unique."
            )


# -----------------------------------
# DATABASE & TABLES
# -----------------------------------

DB_PATH = "stats.db"

TABLES = {
    "my_games": ["Date","Opponent","Team Score","Opponent Score","Points","Rebounds","Assists","Steals","Blocks","Turnovers"],
    "my_baseball_games": ["Date","Opponent","Team Runs","Opponent Runs","At Bats","Hits","Runs","RBIs","Walks","Strikeouts","Doubles","Triples","Home Runs","Stolen Bases"],
    "my_pitching_games": ["Date","Opponent","Innings Pitched","Strikeouts","Walks","Hits Allowed","Earned Runs","Home Runs Allowed","Pitches Thrown","Result"],
    "my_football_games_qb": ["Date","Opponent","Team Score","Opponent Score","Completions","Attempts","Passing Yards","Passing TDs","Interceptions","Rushing Yards","Rushing TDs"],
    "my_football_games_rb": ["Date","Opponent","Team Score","Opponent Score","Carries","Rushing Yards","Rushing TDs","Receptions","Receiving Yards","Receiving TDs"],
    "my_football_games_wrte": ["Date","Opponent","Team Score","Opponent Score","Targets","Receptions","Receiving Yards","Receiving TDs","Rushing Yards","Rushing TDs"],
    "my_football_games_def": ["Date","Opponent","Team Score","Opponent Score","Tackles","Assists","Sacks","Interceptions","Passes Defended","Forced Fumbles","Fumble Recoveries"],
    "coach_roster_games": [
    "Sport","Player","Position","Date","Opponent","Team Score","Opponent Score",
    "Points","Rebounds","Assists","Steals","Blocks","Turnovers",
    "At Bats","Hits","Runs","RBIs","Walks","Strikeouts","Doubles","Triples","Home Runs","Stolen Bases",
    "Innings Pitched","Hits Allowed","Earned Runs","Home Runs Allowed","Pitches Thrown","Result",
    "Completions","Attempts","Passing Yards","Passing TDs","Interceptions",
    "Carries","Rushing Yards","Rushing TDs","Targets","Receptions","Receiving Yards","Receiving TDs",
    "Tackles","Assists_FB","Sacks","Passes Defended","Forced Fumbles","Fumble Recoveries"],
}


def save_to_db(key, df):
    """Save a DataFrame to the DB under a user-namespaced table name."""
    conn = sqlite3.connect(DB_PATH)
    df_copy = df.copy()
    if "Date" in df_copy.columns:
        df_copy["Date"] = pd.to_datetime(df_copy["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    db_key = user_table_key(key)
    df_copy.to_sql(db_key, conn, if_exists="replace", index=False)
    conn.close()


def load_from_db(key, columns):
    """Load a DataFrame from the DB using a user-namespaced table name."""
    conn = sqlite3.connect(DB_PATH)
    db_key = user_table_key(key)
    try:
        df = pd.read_sql(f'SELECT * FROM "{db_key}"', conn)
    except Exception:
        df = pd.DataFrame(columns=columns)
    conn.close()
    return df


# -----------------------------------
# PAGE SETUP
# -----------------------------------

st.set_page_config(page_title="My Stats Tracker", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "sport" not in st.session_state:
    st.session_state.sport = "Basketball"

if "user_id" not in st.session_state:
    st.session_state.user_id = None

page = st.session_state.page

# Render user sidebar on every page
render_user_sidebar()

if page == "My Stats Tracker":
    sport = st.sidebar.radio(
        "Choose a sport",
        ["Basketball", "Baseball", "Football"],
        index=["Basketball", "Baseball", "Football"].index(st.session_state.sport),
        key="sport_radio"
    )
    st.session_state.sport = sport

if page == "Trading Card":
    sport = st.sidebar.radio(
        "Choose a sport for your card",
        ["Basketball", "Baseball", "Football"],
        index=["Basketball", "Baseball", "Football"].index(st.session_state.sport),
        key="card_sport_radio"
    )
    st.session_state.sport = sport

if page == "Coaches View":
    st.sidebar.info("Coach dashboard: roster-wide stats, comps, and graphs")

# -----------------------------------
# GATE: Require user login to use the app
# -----------------------------------

if not get_user_id() and page != "Home":
    st.warning("⚠️ Please set a User ID in the sidebar to use this page.")
    st.stop()

# Load tables from DB for current user (after user is known)
for table_key, columns in TABLES.items():
    if table_key not in st.session_state:
        st.session_state[table_key] = load_from_db(table_key, columns)


# -----------------------------------
# DATA LOADERS
# -----------------------------------

@st.cache_data
def load_player_data(season):
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

    player_base = player_base[[
        "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION",
        "GP", "MIN", "W_PCT", "PTS", "REB", "AST", "STL", "BLK", "TOV"
    ]]

    player_advanced = player_advanced[["PLAYER_ID", "TS_PCT", "PIE"]]

    player_data = pd.merge(player_base, player_advanced, on="PLAYER_ID", how="inner")
    return player_data


@st.cache_data
def load_mlb_batting_data(year):
    start_dt = f"{year}-03-01"
    end_dt   = f"{year}-11-30"
    mlb = batting_stats_range(start_dt, end_dt).copy()

    rename_map = {}
    if "Tm" in mlb.columns: rename_map["Tm"] = "Team"
    if "BA" in mlb.columns: rename_map["BA"] = "AVG"
    mlb = mlb.rename(columns=rename_map)

    keep_cols = ["Name", "Team", "AVG", "OBP", "SLG", "OPS", "HR", "RBI", "SB", "PA"]
    missing = [c for c in keep_cols if c not in mlb.columns]
    if missing:
        raise ValueError(f"Missing MLB batting columns: {missing}")

    mlb = mlb[keep_cols].copy()
    mlb = mlb[mlb["PA"] != ""].copy()

    for col in ["AVG", "OBP", "SLG", "OPS", "HR", "RBI", "SB", "PA"]:
        mlb[col] = pd.to_numeric(mlb[col], errors="coerce")

    mlb = mlb[mlb["PA"] >= 20].dropna(subset=["AVG", "OBP", "SLG", "OPS"])
    return mlb.reset_index(drop=True)


@st.cache_data
def load_mlb_pitching_data(year):
    start_dt = f"{year}-03-01"
    end_dt   = f"{year}-11-30"
    mlb = pitching_stats_range(start_dt, end_dt).copy()

    rename_map = {}
    if "Tm" in mlb.columns: rename_map["Tm"] = "Team"
    if "SO" in mlb.columns: rename_map["SO"] = "K"
    mlb = mlb.rename(columns=rename_map)

    keep_cols = ["Name", "Team", "ERA", "WHIP", "IP", "K", "BB", "HR"]
    missing = [c for c in keep_cols if c not in mlb.columns]
    if missing:
        raise ValueError(f"Missing MLB pitching columns: {missing}")

    mlb = mlb[keep_cols].copy()
    for col in ["ERA", "WHIP", "IP", "K", "BB", "HR"]:
        mlb[col] = pd.to_numeric(mlb[col], errors="coerce")

    mlb = mlb[mlb["IP"] >= 10].dropna(subset=["ERA", "WHIP", "K", "BB"])
    mlb["K_PER_9"]  = (mlb["K"]  / mlb["IP"] * 9).round(2)
    mlb["BB_PER_9"] = (mlb["BB"] / mlb["IP"] * 9).round(2)
    return mlb.reset_index(drop=True)


@st.cache_data
def load_nfl_player_data(season):
    raw    = nfl.load_player_stats([season])
    weekly = raw.to_pandas()

    numeric_cols = [
        "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
        "carries", "rushing_yards", "rushing_tds", "receptions", "targets",
        "receiving_yards", "receiving_tds", "fantasy_points_ppr",
        "def_tackles_solo", "def_tackle_assists", "def_sacks", "def_fumbles_forced",
        "def_interceptions", "def_pass_defended", "def_fumbles"
    ]
    for col in numeric_cols:
        weekly[col] = pd.to_numeric(weekly.get(col, 0), errors="coerce").fillna(0)

    weekly["game_played"] = 1
    group_cols = [c for c in ["player_name", "team", "position"] if c in weekly.columns]
    agg_dict   = {col: "sum" for col in numeric_cols if col in weekly.columns}
    agg_dict["game_played"] = "sum"

    player_stats = weekly.groupby(group_cols, as_index=False).agg(agg_dict)
    player_stats = player_stats.rename(columns={"game_played": "games"})
    player_stats = player_stats[player_stats["games"] >= 4]
    return player_stats.reset_index(drop=True)


# -----------------------------------
# HOME PAGE
# -----------------------------------

if page == "Home":
    st.title("My Stats Tracker")

    # Show login prompt prominently if not logged in
    if not get_user_id():
        st.info("👤 **Get started:** Enter a username in the sidebar to track your personal stats.")
    else:
        st.success(f"Welcome back, **{st.session_state.user_id}**! Your stats are saved privately under your username.")

    st.write("Track your performance, see trends over time, and find your closest pro player match.")
    st.markdown("---")

    role = st.radio(
        "Who are you?",
        ["Player", "Coach"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if role == "Player":
        st.subheader("Choose a Tool")
    
        col1, col2, col3, col4 = st.columns(4)
    
        with col1:
            if st.button("🏀 Basketball", use_container_width=True):
                st.session_state.page = "My Stats Tracker"
                st.session_state.sport = "Basketball"
                st.rerun()
    
        with col2:
            if st.button("⚾ Baseball", use_container_width=True):
                st.session_state.page = "My Stats Tracker"
                st.session_state.sport = "Baseball"
                st.rerun()
    
        with col3:
            if st.button("🏈 Football", use_container_width=True):
                st.session_state.page = "My Stats Tracker"
                st.session_state.sport = "Football"
                st.rerun()
    
        with col4:
            if st.button("🃏 Trading Card", use_container_width=True):
                st.session_state.page = "Trading Card"
                st.rerun()
    
    elif role == "Coach":
        st.subheader("Coach Tools")
        st.write("View roster analytics, player comps, depth charts, and team trends.")
    
        if st.button("📋 Open Coaches View", use_container_width=True):
            st.session_state.page = "Coaches View"
            st.rerun()


# ===================================
# BASKETBALL PAGE
# ===================================

if page == "My Stats Tracker" and sport == "Basketball":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    st.title("🏀 Basketball Stats Tracker")
    st.write("Track your games, see trends, and find your closest NBA player match.")

    season = st.selectbox(
        "Choose NBA season for comparison",
        ["2022-23", "2023-24", "2024-25", "2025-26"],
        index=3
    )

    players = load_player_data(season)
    players = players[players["GP"] >= 40]
    players = players[players["MIN"] >= 20]
    players = players.reset_index(drop=True)
    players["W_PCT"]  = players["W_PCT"].round(3)
    players["TS_PCT"] = players["TS_PCT"].round(3)

    st.subheader("Add a Game")

    with st.form("my_stats_form"):
        st.subheader("Game Info")
        info1, info2, info3 = st.columns([1, 1.5, 1])

        with info1:
            game_date = st.date_input("Game Date")
        with info2:
            opponent = st.text_input("Opponent")
        with info3:
            s1, s2 = st.columns(2)
            with s1:
                team_score = st.number_input("My Team Score", min_value=0, step=1)
            with s2:
                opp_score = st.number_input("Opponent Score", min_value=0, step=1)

        st.subheader("My Stats")
        c1, c2, c3 = st.columns(3)
        with c1:
            my_pts = st.number_input("Points",   min_value=0, step=1)
            my_reb = st.number_input("Rebounds", min_value=0, step=1)
        with c2:
            my_ast = st.number_input("Assists",   min_value=0, step=1)
            my_stl = st.number_input("Steals",    min_value=0, step=1)
        with c3:
            my_blk = st.number_input("Blocks",    min_value=0, step=1)
            my_tov = st.number_input("Turnovers", min_value=0, step=1)

        submitted = st.form_submit_button("Add Game")

        if submitted:
            if opponent.strip() == "":
                st.error("Please enter an opponent.")
            else:
                new_game = pd.DataFrame([{
                    "Date": pd.to_datetime(game_date),
                    "Opponent": opponent,
                    "Team Score": team_score,
                    "Opponent Score": opp_score,
                    "Points": my_pts, "Rebounds": my_reb,
                    "Assists": my_ast, "Steals": my_stl,
                    "Blocks": my_blk, "Turnovers": my_tov
                }])
                st.session_state.my_games = pd.concat(
                    [st.session_state.my_games, new_game], ignore_index=True
                )
                save_to_db("my_games", st.session_state.my_games)
                st.success("Game added!")

    if len(st.session_state.my_games) == 0:
        st.info("No games entered yet. Add your first game above.")
    else:
        my_games = st.session_state.my_games.copy()
        my_games["Date"] = pd.to_datetime(my_games["Date"], errors="coerce")

        num_cols = ["Team Score", "Opponent Score", "Points", "Rebounds",
                    "Assists", "Steals", "Blocks", "Turnovers"]
        for col in num_cols:
            my_games[col] = pd.to_numeric(my_games[col], errors="coerce")
        my_games = my_games.dropna(subset=["Date"])
        my_games[num_cols] = my_games[num_cols].fillna(0)
        my_games = my_games.sort_values("Date").reset_index(drop=True)

        NBA_AVG_TEAM_PTS = 115.0
        my_games["Scoring Factor"] = (
            NBA_AVG_TEAM_PTS / my_games["Team Score"].replace(0, pd.NA)
        ).fillna(1.0).clip(lower=0.6, upper=4.5)

        my_games["NBA_EQ_PTS"] = my_games["Points"]   * my_games["Scoring Factor"]
        my_games["NBA_EQ_AST"] = my_games["Assists"]  * my_games["Scoring Factor"]
        my_games["NBA_EQ_REB"] = my_games["Rebounds"]  * (my_games["Scoring Factor"] ** 0.5)
        my_games["NBA_EQ_STL"] = my_games["Steals"]   * (my_games["Scoring Factor"] ** 0.3)
        my_games["NBA_EQ_BLK"] = my_games["Blocks"]   * (my_games["Scoring Factor"] ** 0.3)
        my_games["NBA_EQ_TOV"] = my_games["Turnovers"] * my_games["Scoring Factor"]

        comparison_mode = st.toggle("Use NBA-adjusted stats", value=False)

        if comparison_mode:
            display_label = "NBA-Adjusted"
            my_avg = pd.DataFrame([{
                "PTS": my_games["NBA_EQ_PTS"].mean(), "REB": my_games["NBA_EQ_REB"].mean(),
                "AST": my_games["NBA_EQ_AST"].mean(), "STL": my_games["NBA_EQ_STL"].mean(),
                "BLK": my_games["NBA_EQ_BLK"].mean(), "TOV": my_games["NBA_EQ_TOV"].mean()
            }]).round(2)
        else:
            display_label = "Raw"
            my_avg = pd.DataFrame([{
                "PTS": my_games["Points"].mean(),   "REB": my_games["Rebounds"].mean(),
                "AST": my_games["Assists"].mean(),  "STL": my_games["Steals"].mean(),
                "BLK": my_games["Blocks"].mean(),   "TOV": my_games["Turnovers"].mean()
            }]).round(2)

        st.metric("Games Tracked", len(my_games))
        st.subheader("My Average Stats")
        st.caption(f"Currently showing: {display_label} stats")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Points",   my_avg.loc[0, "PTS"])
            st.metric("Rebounds", my_avg.loc[0, "REB"])
        with c2:
            st.metric("Assists",  my_avg.loc[0, "AST"])
            st.metric("Steals",   my_avg.loc[0, "STL"])
        with c3:
            st.metric("Blocks",    my_avg.loc[0, "BLK"])
            st.metric("Turnovers", my_avg.loc[0, "TOV"])

        st.subheader("NBA Player Comparison")

        nba_compare = players[["PLAYER_NAME", "TEAM_ABBREVIATION",
                                "PTS", "REB", "AST", "STL", "BLK", "TOV"]].copy()
        nba_compare["DISTANCE"] = (
            (nba_compare["PTS"] - my_avg.loc[0, "PTS"]) ** 2 +
            (nba_compare["REB"] - my_avg.loc[0, "REB"]) ** 2 +
            (nba_compare["AST"] - my_avg.loc[0, "AST"]) ** 2 +
            (nba_compare["STL"] - my_avg.loc[0, "STL"]) ** 2 +
            (nba_compare["BLK"] - my_avg.loc[0, "BLK"]) ** 2 +
            (nba_compare["TOV"] - my_avg.loc[0, "TOV"]) ** 2
        ) ** 0.5

        top_matches = nba_compare.sort_values("DISTANCE").head(5).reset_index(drop=True)
        top_matches["Similarity Score"] = (1 / (1 + top_matches["DISTANCE"])).round(3)
        closest = top_matches.iloc[0]

        st.metric("Closest NBA Match", closest["PLAYER_NAME"])
        st.write("Team:", closest["TEAM_ABBREVIATION"])

        compare_cols = ["PTS", "REB", "AST", "STL", "BLK", "TOV"]
        comparison_df = pd.DataFrame({
            "Stat": compare_cols,
            "My Average": [my_avg.loc[0, c] for c in compare_cols],
            closest["PLAYER_NAME"]: [closest[c] for c in compare_cols]
        })
        st.dataframe(comparison_df, hide_index=True)

        st.write("Top 5 NBA matches:")
        st.dataframe(
            top_matches[["PLAYER_NAME", "TEAM_ABBREVIATION", "DISTANCE", "Similarity Score"]],
            hide_index=True
        )

        match_fig = px.bar(top_matches, x="Similarity Score", y="PLAYER_NAME",
                           orientation="h", title="Top NBA Player Matches")
        match_fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(match_fig, use_container_width=True)

        st.subheader("Performance Trends")
        trend_choice = st.selectbox(
            "Choose a stat to graph",
            ["Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"]
        )
        trend_fig = px.line(my_games, x="Date", y=trend_choice,
                            markers=True, hover_data=["Opponent"],
                            title=f"{trend_choice} Over Time")
        st.plotly_chart(trend_fig, use_container_width=True)

        render_ai_coach_section("Basketball", st.session_state.my_games) # NEW

        st.subheader("My Game Log")
        log_cols = ["Date", "Opponent", "Team Score", "Opponent Score",
                    "Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"]
        game_log = my_games[log_cols].copy()
        game_log["Date"] = game_log["Date"].dt.strftime("%Y-%m-%d")
        game_log.index = game_log.index + 1
        st.dataframe(game_log)

        st.subheader("Delete a Game")
        del_df = my_games.copy()
        del_df["Date_str"] = del_df["Date"].dt.strftime("%Y-%m-%d")
        del_df["Delete Label"] = (
            del_df["Date_str"] + " vs " + del_df["Opponent"] +
            " | PTS: " + del_df["Points"].astype(int).astype(str) +
            ", REB: " + del_df["Rebounds"].astype(int).astype(str) +
            ", AST: " + del_df["Assists"].astype(int).astype(str)
        )
        del_idx = st.selectbox(
            "Choose a game to delete",
            options=del_df.index,
            format_func=lambda i: del_df.loc[i, "Delete Label"],
            key="delete_bball_game"
        )
        if st.button("Delete Selected Game"):
            st.session_state.my_games = st.session_state.my_games.drop(
                st.session_state.my_games.index[del_idx]
            ).reset_index(drop=True)
            save_to_db("my_games", st.session_state.my_games)
            st.success("Game deleted.")
            st.rerun()


# ===================================
# BASEBALL PAGE
# ===================================

if page == "My Stats Tracker" and sport == "Baseball":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    st.title("⚾ Baseball Stats Tracker")
    st.write("Track your games, see trends, and find your closest MLB player match.")

    BASEBALL_COLUMNS = [
        "Date", "Opponent", "Team Runs", "Opponent Runs",
        "At Bats", "Hits", "Runs", "RBIs", "Walks", "Strikeouts",
        "Doubles", "Triples", "Home Runs", "Stolen Bases"
    ]
    PITCHING_COLUMNS = [
        "Date", "Opponent", "Innings Pitched", "Strikeouts", "Walks",
        "Hits Allowed", "Earned Runs", "Home Runs Allowed", "Pitches Thrown", "Result"
    ]

    hitting_tab, pitching_tab = st.tabs(["🏏 Hitting", "⚾ Pitching"])

    with hitting_tab:
        st.subheader("Add a Game")
 
        with st.form("my_baseball_form"):
            # Game info row
            info1, info2, info3, info4 = st.columns([1.2, 1.5, 1, 1])
            with info1:
                game_date = st.date_input("Game Date", key="baseball_date")
            with info2:
                opponent  = st.text_input("Opponent", key="baseball_opponent")
            with info3:
                team_runs = st.number_input("My Team Runs", min_value=0, step=1, key="team_runs")
            with info4:
                opp_runs  = st.number_input("Opp Runs",     min_value=0, step=1, key="opp_runs")
 
            st.markdown("**Hitting Stats**")
 
            # Row 1: plate appearances
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            with r1c1: at_bats    = st.number_input("At Bats",    min_value=0, step=1, key="bb_ab")
            with r1c2: hits       = st.number_input("Hits",       min_value=0, step=1, key="bb_h")
            with r1c3: walks      = st.number_input("Walks",      min_value=0, step=1, key="bb_bb")
            with r1c4: strikeouts = st.number_input("Strikeouts", min_value=0, step=1, key="bb_so")
 
            # Row 2: production
            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            with r2c1: runs       = st.number_input("Runs",       min_value=0, step=1, key="bb_r")
            with r2c2: rbis       = st.number_input("RBIs",       min_value=0, step=1, key="bb_rbi")
            with r2c3: home_runs  = st.number_input("Home Runs",  min_value=0, step=1, key="bb_hr")
            with r2c4: doubles = st.number_input("Doubles", min_value=0, step=1, key="bb_2b")
                 
            # Row 3: hit types
            r3c1, r3c2, r3c3, r3c4 = st.columns(4)
            with r3c1: triples = st.number_input("Triples", min_value=0, step=1, key="bb_3b")
            with r3c2: stolen_bases = st.number_input("Stolen Bases", min_value=0, step=1, key="bb_sb")
            with r3c3: st.empty()   # spacer
            with r3c4: st.empty()   # spacer

            submitted = st.form_submit_button("Add Hitting Game")
            if submitted:
                if opponent.strip() == "":
                    st.error("Please enter an opponent.")
                elif hits > at_bats:
                    st.error("Hits cannot exceed at bats.")
                elif doubles + triples + home_runs > hits:
                    st.error("Doubles + Triples + HRs cannot exceed total Hits.")
                else:
                    new_game = pd.DataFrame([{
                        "Date": pd.to_datetime(game_date), "Opponent": opponent,
                        "Team Runs": team_runs, "Opponent Runs": opp_runs,
                        "At Bats": at_bats, "Hits": hits, "Runs": runs, "RBIs": rbis,
                        "Walks": walks, "Strikeouts": strikeouts, "Doubles": doubles,
                        "Triples": triples, "Home Runs": home_runs, "Stolen Bases": stolen_bases
                    }])
                    st.session_state.my_baseball_games = pd.concat(
                        [st.session_state.my_baseball_games, new_game], ignore_index=True
                    )
                    save_to_db("my_baseball_games", st.session_state.my_baseball_games)
                    st.success("Game added!")

        if len(st.session_state.my_baseball_games) == 0:
            st.info("No hitting games entered yet.")
        else:
            baseball_games = st.session_state.my_baseball_games.copy()
            baseball_games["Date"] = pd.to_datetime(baseball_games["Date"], errors="coerce")

            h_num_cols = ["Team Runs", "Opponent Runs", "At Bats", "Hits", "Runs", "RBIs",
                          "Walks", "Strikeouts", "Doubles", "Triples", "Home Runs", "Stolen Bases"]
            for col in h_num_cols:
                baseball_games[col] = pd.to_numeric(baseball_games[col], errors="coerce")
            baseball_games = baseball_games.dropna(subset=["Date"])
            baseball_games[h_num_cols] = baseball_games[h_num_cols].fillna(0)
            baseball_games = baseball_games.sort_values("Date").reset_index(drop=True)

            total_games  = len(baseball_games)
            total_ab     = baseball_games["At Bats"].sum()
            total_hits   = baseball_games["Hits"].sum()
            total_walks  = baseball_games["Walks"].sum()
            total_doubles = baseball_games["Doubles"].sum()
            total_triples = baseball_games["Triples"].sum()
            total_hr     = baseball_games["Home Runs"].sum()
            total_rbi    = baseball_games["RBIs"].sum()
            total_sb     = baseball_games["Stolen Bases"].sum()
            singles      = max(total_hits - total_doubles - total_triples - total_hr, 0)
            total_bases  = singles + 2*total_doubles + 3*total_triples + 4*total_hr

            batting_avg = total_hits / total_ab if total_ab > 0 else 0
            obp = (total_hits + total_walks) / (total_ab + total_walks) if (total_ab + total_walks) > 0 else 0
            slg = total_bases / total_ab if total_ab > 0 else 0
            ops = obp + slg

            st.subheader("My Hitting Summary")
            top1, top2, top3 = st.columns(3)
            with top1:
                st.metric("Games Tracked", total_games)
                st.metric("Batting Average", round(batting_avg, 3))
            with top2:
                st.metric("OBP", round(obp, 3))
                st.metric("SLG", round(slg, 3))
            with top3:
                st.metric("OPS", round(ops, 3))

            st.subheader("Season Totals")
            t1, t2, t3 = st.columns(3)
            with t1: st.metric("Home Runs",    int(total_hr))
            with t2: st.metric("RBIs",         int(total_rbi))
            with t3: st.metric("Stolen Bases", int(total_sb))

            my_profile = {
                "AVG": batting_avg, "OBP": obp, "SLG": slg, "OPS": ops,
                "HR_PER_GAME":  total_hr  / total_games if total_games > 0 else 0,
                "RBI_PER_GAME": total_rbi / total_games if total_games > 0 else 0,
                "SB_PER_GAME":  total_sb  / total_games if total_games > 0 else 0
            }

            st.subheader("MLB Player Comparison")
            mlb_year = st.selectbox("Choose MLB season", [2023, 2024, 2025], index=2,
                                    key="mlb_hit_year")
            try:
                mlb_hitters = load_mlb_batting_data(mlb_year).copy()
                mlb_hitters["EST_G"] = (mlb_hitters["PA"] / 4.2).clip(lower=1)
                mlb_hitters["HR_PER_GAME"]  = mlb_hitters["HR"]  / mlb_hitters["EST_G"]
                mlb_hitters["RBI_PER_GAME"] = mlb_hitters["RBI"] / mlb_hitters["EST_G"]
                mlb_hitters["SB_PER_GAME"]  = mlb_hitters["SB"]  / mlb_hitters["EST_G"]

                mlb_hitters["DISTANCE"] = (
                    ((mlb_hitters["AVG"] - my_profile["AVG"]) / 0.030) ** 2 +
                    ((mlb_hitters["OBP"] - my_profile["OBP"]) / 0.040) ** 2 +
                    ((mlb_hitters["SLG"] - my_profile["SLG"]) / 0.060) ** 2 +
                    ((mlb_hitters["OPS"] - my_profile["OPS"]) / 0.090) ** 2 +
                    ((mlb_hitters["HR_PER_GAME"]  - my_profile["HR_PER_GAME"])  / 0.12) ** 2 +
                    ((mlb_hitters["RBI_PER_GAME"] - my_profile["RBI_PER_GAME"]) / 0.20) ** 2 +
                    ((mlb_hitters["SB_PER_GAME"]  - my_profile["SB_PER_GAME"])  / 0.10) ** 2
                ) ** 0.5

                mlb_hitters["Similarity Score"] = (1 / (1 + mlb_hitters["DISTANCE"])).round(3)
                top_matches  = mlb_hitters.sort_values("DISTANCE").head(5).reset_index(drop=True)
                closest_mlb  = top_matches.iloc[0]

                st.metric("Closest MLB Match", closest_mlb["Name"])
                st.write("Team:", closest_mlb["Team"])

                comparison_df = pd.DataFrame({
                    "Stat": ["AVG", "OBP", "SLG", "OPS", "HR/Game", "RBI/Game", "SB/Game"],
                    "My Profile": [round(my_profile[k], 3) for k in
                                   ["AVG", "OBP", "SLG", "OPS", "HR_PER_GAME", "RBI_PER_GAME", "SB_PER_GAME"]],
                    closest_mlb["Name"]: [
                        round(closest_mlb["AVG"], 3), round(closest_mlb["OBP"], 3),
                        round(closest_mlb["SLG"], 3), round(closest_mlb["OPS"], 3),
                        round(closest_mlb["HR_PER_GAME"], 3), round(closest_mlb["RBI_PER_GAME"], 3),
                        round(closest_mlb["SB_PER_GAME"], 3)
                    ]
                })
                st.dataframe(comparison_df, hide_index=True)
                st.write("Top 5 MLB matches:")
                st.dataframe(
                    top_matches[["Name", "Team", "AVG", "OBP", "SLG", "OPS", "Similarity Score"]],
                    hide_index=True
                )
                match_fig = px.bar(top_matches, x="Similarity Score", y="Name",
                                   orientation="h", title="Top MLB Hitter Matches")
                match_fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(match_fig, use_container_width=True)

            except Exception as e:
                st.warning(f"Could not load MLB hitting data: {e}")

            st.subheader("Performance Trends")
            trend_choice = st.selectbox(
                "Choose a stat",
                ["Hits", "Runs", "RBIs", "Walks", "Strikeouts", "Home Runs", "Stolen Bases"],
                key="baseball_trend"
            )
            trend_fig = px.line(baseball_games, x="Date", y=trend_choice,
                                markers=True, hover_data=["Opponent"],
                                title=f"{trend_choice} Over Time")
            st.plotly_chart(trend_fig, use_container_width=True)

            render_ai_coach_section("Baseball Hitting", st.session_state.my_baseball_games) # NEW

            st.subheader("My Game Log")
            h_log = baseball_games[BASEBALL_COLUMNS].copy()
            h_log["Date"] = h_log["Date"].dt.strftime("%Y-%m-%d")
            h_log.index = h_log.index + 1
            st.dataframe(h_log)

            st.subheader("Delete a Game")
            h_del_df = baseball_games.copy()
            h_del_df["Date_str"] = h_del_df["Date"].dt.strftime("%Y-%m-%d")
            h_del_df["Delete Label"] = (
                h_del_df["Date_str"] + " vs " + h_del_df["Opponent"] +
                " | H: " + h_del_df["Hits"].astype(int).astype(str) +
                ", RBI: " + h_del_df["RBIs"].astype(int).astype(str) +
                ", HR: " + h_del_df["Home Runs"].astype(int).astype(str)
            )
            h_del_idx = st.selectbox(
                "Choose a game to delete", options=h_del_df.index,
                format_func=lambda i: h_del_df.loc[i, "Delete Label"],
                key="delete_baseball_game"
            )
            if st.button("Delete Selected Hitting Game"):
                st.session_state.my_baseball_games = st.session_state.my_baseball_games.drop(
                    st.session_state.my_baseball_games.index[h_del_idx]
                ).reset_index(drop=True)
                save_to_db("my_baseball_games", st.session_state.my_baseball_games)
                st.success("Game deleted.")
                st.rerun()

    with pitching_tab:
        st.subheader("Add a Pitching Outing")

        with st.form("my_pitching_form"):
            st.subheader("Game Info")
            p_info1, p_info2, p_info3 = st.columns([1, 1.5, 1])
            with p_info1:
                p_date = st.date_input("Game Date", key="pitching_date")
            with p_info2:
                p_opponent = st.text_input("Opponent", key="pitching_opponent")
            with p_info3:
                p_result = st.selectbox("Result", ["W", "L", "ND"], key="pitching_result")

            st.subheader("My Pitching Stats")
            pc1, pc2, pc3, pc4 = st.columns(4)
            with pc1:
                p_ip = st.number_input("Innings Pitched", min_value=0.0, step=0.1,
                                       format="%.1f", key="p_ip")
                p_k  = st.number_input("Strikeouts", min_value=0, step=1, key="p_k")
            with pc2:
                p_bb = st.number_input("Walks",       min_value=0, step=1, key="p_bb")
                p_h  = st.number_input("Hits Allowed",min_value=0, step=1, key="p_h")
            with pc3:
                p_er = st.number_input("Earned Runs",      min_value=0, step=1, key="p_er")
                p_hr = st.number_input("Home Runs Allowed", min_value=0, step=1, key="p_hr")
            with pc4:
                p_pitches = st.number_input("Pitches Thrown", min_value=0, step=1, key="p_pitches")

            p_submitted = st.form_submit_button("Add Pitching Outing")
            if p_submitted:
                if p_opponent.strip() == "":
                    st.error("Please enter an opponent.")
                elif p_ip <= 0:
                    st.error("Innings Pitched must be greater than 0.")
                elif p_er > p_h:
                    st.error("Earned Runs cannot exceed Hits Allowed.")
                else:
                    new_outing = pd.DataFrame([{
                        "Date": pd.to_datetime(p_date), "Opponent": p_opponent,
                        "Innings Pitched": p_ip, "Strikeouts": p_k, "Walks": p_bb,
                        "Hits Allowed": p_h, "Earned Runs": p_er,
                        "Home Runs Allowed": p_hr, "Pitches Thrown": p_pitches,
                        "Result": p_result
                    }])
                    st.session_state.my_pitching_games = pd.concat(
                        [st.session_state.my_pitching_games, new_outing], ignore_index=True
                    )
                    save_to_db("my_pitching_games", st.session_state.my_pitching_games)
                    st.success("Pitching outing added!")

        if len(st.session_state.my_pitching_games) == 0:
            st.info("No pitching outings logged yet.")
        else:
            pitch_games = st.session_state.my_pitching_games.copy()
            pitch_games["Date"] = pd.to_datetime(pitch_games["Date"], errors="coerce")

            p_num_cols = ["Innings Pitched", "Strikeouts", "Walks",
                          "Hits Allowed", "Earned Runs", "Home Runs Allowed", "Pitches Thrown"]
            for col in p_num_cols:
                pitch_games[col] = pd.to_numeric(pitch_games[col], errors="coerce")
            pitch_games = pitch_games.dropna(subset=["Date"])
            pitch_games[p_num_cols] = pitch_games[p_num_cols].fillna(0)
            pitch_games = pitch_games.sort_values("Date").reset_index(drop=True)

            total_ip          = pitch_games["Innings Pitched"].sum()
            total_er          = pitch_games["Earned Runs"].sum()
            total_k           = pitch_games["Strikeouts"].sum()
            total_bb          = pitch_games["Walks"].sum()
            total_hits_all    = pitch_games["Hits Allowed"].sum()
            total_pitches     = pitch_games["Pitches Thrown"].sum()
            total_outings     = len(pitch_games)

            era      = (total_er / total_ip * 9)        if total_ip > 0 else 0
            whip     = (total_bb + total_hits_all) / total_ip if total_ip > 0 else 0
            k_per_9  = (total_k  / total_ip * 9)        if total_ip > 0 else 0
            bb_per_9 = (total_bb / total_ip * 9)        if total_ip > 0 else 0
            k_bb     = (total_k  / total_bb)            if total_bb > 0 else float("inf")
            avg_pitches = total_pitches / total_outings  if total_outings > 0 else 0

            st.subheader("My Pitching Summary")
            pm1, pm2, pm3 = st.columns(3)
            with pm1:
                st.metric("Outings", total_outings)
                st.metric("ERA",     round(era, 2))
            with pm2:
                st.metric("WHIP",  round(whip, 2))
                st.metric("K/9",   round(k_per_9, 1))
            with pm3:
                st.metric("BB/9",    round(bb_per_9, 1))
                st.metric("K/BB",    round(k_bb, 2) if k_bb != float("inf") else "∞")

            st.subheader("Season Pitching Totals")
            pt1, pt2, pt3, pt4 = st.columns(4)
            with pt1: st.metric("Innings Pitched", round(total_ip, 1))
            with pt2: st.metric("Strikeouts",      int(total_k))
            with pt3: st.metric("Walks",           int(total_bb))
            with pt4: st.metric("Avg Pitches/Outing", round(avg_pitches, 1))

            st.subheader("MLB Pitcher Comparison")
            mlb_pitch_year = st.selectbox("Choose MLB season", [2023, 2024, 2025],
                                          index=2, key="mlb_pitch_year")
            try:
                mlb_pitchers = load_mlb_pitching_data(mlb_pitch_year).copy()
                my_pitch_profile = {"ERA": era, "WHIP": whip, "K_PER_9": k_per_9, "BB_PER_9": bb_per_9}

                mlb_pitchers["DISTANCE"] = (
                    ((mlb_pitchers["ERA"]      - my_pitch_profile["ERA"])      / 1.0)  ** 2 +
                    ((mlb_pitchers["WHIP"]     - my_pitch_profile["WHIP"])     / 0.20) ** 2 +
                    ((mlb_pitchers["K_PER_9"]  - my_pitch_profile["K_PER_9"])  / 2.0)  ** 2 +
                    ((mlb_pitchers["BB_PER_9"] - my_pitch_profile["BB_PER_9"]) / 1.0)  ** 2
                ) ** 0.5

                mlb_pitchers["Similarity Score"] = (1 / (1 + mlb_pitchers["DISTANCE"])).round(3)
                top_pitch_matches = mlb_pitchers.sort_values("DISTANCE").head(5).reset_index(drop=True)
                closest_pitcher   = top_pitch_matches.iloc[0]

                st.metric("Closest MLB Pitcher Match", closest_pitcher["Name"])
                st.write("Team:", closest_pitcher["Team"])

                pitch_comparison_df = pd.DataFrame({
                    "Stat": ["ERA", "WHIP", "K/9", "BB/9"],
                    "My Profile": [round(era, 2), round(whip, 2), round(k_per_9, 1), round(bb_per_9, 1)],
                    closest_pitcher["Name"]: [
                        round(closest_pitcher["ERA"], 2), round(closest_pitcher["WHIP"], 2),
                        round(closest_pitcher["K_PER_9"], 1), round(closest_pitcher["BB_PER_9"], 1)
                    ]
                })
                st.dataframe(pitch_comparison_df, hide_index=True)
                st.write("Top 5 MLB pitcher matches:")
                st.dataframe(
                    top_pitch_matches[["Name", "Team", "ERA", "WHIP", "K_PER_9", "BB_PER_9", "Similarity Score"]],
                    hide_index=True
                )
                pitch_match_fig = px.bar(top_pitch_matches, x="Similarity Score", y="Name",
                                         orientation="h", title="Top MLB Pitcher Matches")
                pitch_match_fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(pitch_match_fig, use_container_width=True)

            except Exception as e:
                st.warning(f"Could not load MLB pitching data: {e}")

            st.subheader("Pitching Trends")
            p_trend_choice = st.selectbox(
                "Choose a stat",
                ["Innings Pitched", "Strikeouts", "Walks", "Hits Allowed",
                 "Earned Runs", "Home Runs Allowed", "Pitches Thrown"],
                key="pitching_trend"
            )
            p_trend_fig = px.line(pitch_games, x="Date", y=p_trend_choice,
                                  markers=True, hover_data=["Opponent", "Result"],
                                  title=f"{p_trend_choice} Over Time")
            st.plotly_chart(p_trend_fig, use_container_width=True)

            render_ai_coach_section("Baseball Pitching", st.session_state.my_pitching_games) # NEW

            st.subheader("My Pitching Game Log")
            p_log = pitch_games[PITCHING_COLUMNS].copy()
            p_log["Date"] = p_log["Date"].dt.strftime("%Y-%m-%d")
            p_log.index = p_log.index + 1
            st.dataframe(p_log)

            st.subheader("Delete a Pitching Outing")
            p_del_df = pitch_games.copy()
            p_del_df["Date_str"] = p_del_df["Date"].dt.strftime("%Y-%m-%d")
            p_del_df["Delete Label"] = (
                p_del_df["Date_str"] + " vs " + p_del_df["Opponent"] +
                " | IP: " + p_del_df["Innings Pitched"].astype(str) +
                ", K: "   + p_del_df["Strikeouts"].astype(int).astype(str) +
                ", ER: "  + p_del_df["Earned Runs"].astype(int).astype(str)
            )
            p_del_idx = st.selectbox(
                "Choose an outing to delete", options=p_del_df.index,
                format_func=lambda i: p_del_df.loc[i, "Delete Label"],
                key="delete_pitching_game"
            )
            if st.button("Delete Selected Pitching Outing"):
                st.session_state.my_pitching_games = st.session_state.my_pitching_games.drop(
                    st.session_state.my_pitching_games.index[p_del_idx]
                ).reset_index(drop=True)
                save_to_db("my_pitching_games", st.session_state.my_pitching_games)
                st.success("Outing deleted.")
                st.rerun()


# ===================================
# FOOTBALL PAGE
# ===================================

if page == "My Stats Tracker" and sport == "Football":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    st.title("🏈 Football Stats Tracker")
    st.write("Track your games, see trends, and find your closest NFL player match.")

    football_mode = st.selectbox(
        "Choose your position",
        ["QB", "RB", "WR/TE", "Defense"],
        key="football_mode_select"
    )

    mode_key_map = {"QB": "qb", "RB": "rb", "WR/TE": "wrte", "Defense": "def"}
    mode_key = mode_key_map[football_mode]

    FOOTBALL_MODE_COLUMNS = {
        "QB": ["Date", "Opponent", "Team Score", "Opponent Score",
               "Completions", "Attempts", "Passing Yards", "Passing TDs", "Interceptions",
               "Rushing Yards", "Rushing TDs"],
        "RB": ["Date", "Opponent", "Team Score", "Opponent Score",
               "Carries", "Rushing Yards", "Rushing TDs",
               "Receptions", "Receiving Yards", "Receiving TDs"],
        "WR/TE": ["Date", "Opponent", "Team Score", "Opponent Score",
                  "Targets", "Receptions", "Receiving Yards", "Receiving TDs",
                  "Rushing Yards", "Rushing TDs"],
        "Defense": ["Date", "Opponent", "Team Score", "Opponent Score",
                    "Tackles", "Assists", "Sacks", "Interceptions",
                    "Passes Defended", "Forced Fumbles", "Fumble Recoveries"]
    }

    FOOTBALL_COLUMNS = FOOTBALL_MODE_COLUMNS[football_mode]
    session_key = f"my_football_games_{mode_key}"
    db_key = f"my_football_games_{mode_key}"

    st.subheader(f"Add a {football_mode} Game")

    with st.form(f"my_football_form_{mode_key}"):
        st.subheader("Game Info")
        info1, info2, info3 = st.columns([1, 1.5, 1])
        with info1:
            game_date = st.date_input("Game Date", key=f"football_date_{mode_key}")
        with info2:
            opponent = st.text_input("Opponent", key=f"football_opponent_{mode_key}")
        with info3:
            s1, s2 = st.columns(2)
            with s1: team_score = st.number_input("My Team Score", min_value=0, step=1, key=f"football_team_score_{mode_key}")
            with s2: opp_score  = st.number_input("Opponent Score", min_value=0, step=1, key=f"football_opp_score_{mode_key}")

        st.subheader("My Stats")

        if football_mode == "QB":
            c1, c2, c3 = st.columns(3)
            with c1:
                completions = st.number_input("Completions", min_value=0, step=1, key="qb_completions")
                attempts    = st.number_input("Attempts",    min_value=0, step=1, key="qb_attempts")
            with c2:
                passing_yards = st.number_input("Passing Yards", min_value=0, step=1, key="qb_passing_yards")
                passing_tds   = st.number_input("Passing TDs",   min_value=0, step=1, key="qb_passing_tds")
                interceptions = st.number_input("Interceptions", min_value=0, step=1, key="qb_interceptions")
            with c3:
                rushing_yards = st.number_input("Rushing Yards", min_value=0, step=1, key="qb_rushing_yards")
                rushing_tds   = st.number_input("Rushing TDs",   min_value=0, step=1, key="qb_rushing_tds")

        elif football_mode == "RB":
            c1, c2, c3 = st.columns(3)
            with c1:
                carries       = st.number_input("Carries",       min_value=0, step=1, key="rb_carries")
                rushing_yards = st.number_input("Rushing Yards", min_value=0, step=1, key="rb_rushing_yards")
                rushing_tds   = st.number_input("Rushing TDs",   min_value=0, step=1, key="rb_rushing_tds")
            with c2:
                receptions     = st.number_input("Receptions",     min_value=0, step=1, key="rb_receptions")
                receiving_yards = st.number_input("Receiving Yards", min_value=0, step=1, key="rb_receiving_yards")
            with c3:
                receiving_tds = st.number_input("Receiving TDs", min_value=0, step=1, key="rb_receiving_tds")

        elif football_mode == "WR/TE":
            c1, c2, c3 = st.columns(3)
            with c1:
                targets    = st.number_input("Targets",    min_value=0, step=1, key="wr_targets")
                receptions = st.number_input("Receptions", min_value=0, step=1, key="wr_receptions")
            with c2:
                receiving_yards = st.number_input("Receiving Yards", min_value=0, step=1, key="wr_receiving_yards")
                receiving_tds   = st.number_input("Receiving TDs",   min_value=0, step=1, key="wr_receiving_tds")
            with c3:
                rushing_yards = st.number_input("Rushing Yards", min_value=0, step=1, key="wr_rushing_yards")
                rushing_tds   = st.number_input("Rushing TDs",   min_value=0, step=1, key="wr_rushing_tds")

        elif football_mode == "Defense":
            c1, c2, c3 = st.columns(3)
            with c1:
                tackles = st.number_input("Tackles", min_value=0, step=1, key="def_tackles")
                assists = st.number_input("Assists", min_value=0, step=1, key="def_assists")
            with c2:
                sacks         = st.number_input("Sacks",         min_value=0.0, step=0.5, key="def_sacks")
                interceptions = st.number_input("Interceptions", min_value=0,   step=1,   key="def_interceptions")
            with c3:
                passes_defended   = st.number_input("Passes Defended",  min_value=0, step=1, key="def_passes_defended")
                forced_fumbles    = st.number_input("Forced Fumbles",   min_value=0, step=1, key="def_forced_fumbles")
                fumble_recoveries = st.number_input("Fumble Recoveries",min_value=0, step=1, key="def_fumble_recoveries")

        submitted = st.form_submit_button(f"Add {football_mode} Game")

        if submitted:
            if opponent.strip() == "":
                st.error("Please enter an opponent.")
            else:
                error = False
                if football_mode == "QB" and completions > attempts:
                    st.error("Completions cannot exceed attempts.")
                    error = True
                if football_mode == "WR/TE" and receptions > targets:
                    st.error("Receptions cannot exceed targets.")
                    error = True

                if not error:
                    base = {
                        "Date": pd.to_datetime(game_date), "Opponent": opponent,
                        "Team Score": team_score, "Opponent Score": opp_score
                    }
                    if football_mode == "QB":
                        base.update({"Completions": completions, "Attempts": attempts,
                                     "Passing Yards": passing_yards, "Passing TDs": passing_tds,
                                     "Interceptions": interceptions, "Rushing Yards": rushing_yards,
                                     "Rushing TDs": rushing_tds})
                    elif football_mode == "RB":
                        base.update({"Carries": carries, "Rushing Yards": rushing_yards,
                                     "Rushing TDs": rushing_tds, "Receptions": receptions,
                                     "Receiving Yards": receiving_yards, "Receiving TDs": receiving_tds})
                    elif football_mode == "WR/TE":
                        base.update({"Targets": targets, "Receptions": receptions,
                                     "Receiving Yards": receiving_yards, "Receiving TDs": receiving_tds,
                                     "Rushing Yards": rushing_yards, "Rushing TDs": rushing_tds})
                    elif football_mode == "Defense":
                        base.update({"Tackles": tackles, "Assists": assists, "Sacks": sacks,
                                     "Interceptions": interceptions, "Passes Defended": passes_defended,
                                     "Forced Fumbles": forced_fumbles, "Fumble Recoveries": fumble_recoveries})

                    st.session_state[session_key] = pd.concat(
                        [st.session_state[session_key], pd.DataFrame([base])], ignore_index=True
                    )
                    save_to_db(db_key, st.session_state[session_key])
                    st.success(f"{football_mode} game added!")

    if len(st.session_state[session_key]) == 0:
        st.info(f"No {football_mode} games entered yet.")
    else:
        football_games = st.session_state[session_key].copy()
        football_games["Date"] = pd.to_datetime(football_games["Date"], errors="coerce")

        f_num_cols = [col for col in FOOTBALL_COLUMNS if col not in ["Date", "Opponent"]]
        for col in f_num_cols:
            football_games[col] = pd.to_numeric(football_games[col], errors="coerce")
        football_games = football_games.dropna(subset=["Date"])
        football_games[f_num_cols] = football_games[f_num_cols].fillna(0)
        football_games = football_games.sort_values("Date").reset_index(drop=True)

        total_games = len(football_games)
        st.subheader(f"My {football_mode} Summary")

        if football_mode == "QB":
            football_games["CMP_PCT"] = (
                football_games["Completions"] / football_games["Attempts"].replace(0, pd.NA)
            ).fillna(0)
            my_avg = pd.DataFrame([{
                "COMP": football_games["Completions"].mean(),
                "ATT": football_games["Attempts"].mean(),
                "CMP_PCT": football_games["CMP_PCT"].mean(),
                "PASS_YDS": football_games["Passing Yards"].mean(),
                "PASS_TD": football_games["Passing TDs"].mean(),
                "INT": football_games["Interceptions"].mean(),
                "RUSH_YDS": football_games["Rushing Yards"].mean(),
                "RUSH_TD": football_games["Rushing TDs"].mean()
            }]).round(2)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Games Tracked", total_games)
                st.metric("Pass Yards/Game", my_avg.loc[0, "PASS_YDS"])
                st.metric("Completion %", round(my_avg.loc[0, "CMP_PCT"] * 100, 1))
            with c2:
                st.metric("Pass TD/Game", my_avg.loc[0, "PASS_TD"])
                st.metric("INT/Game",     my_avg.loc[0, "INT"])
            with c3:
                st.metric("Rush Yards/Game", my_avg.loc[0, "RUSH_YDS"])
                st.metric("Rush TD/Game",    my_avg.loc[0, "RUSH_TD"])

        elif football_mode == "RB":
            my_avg = pd.DataFrame([{
                "CAR": football_games["Carries"].mean(),
                "RUSH_YDS": football_games["Rushing Yards"].mean(),
                "RUSH_TD": football_games["Rushing TDs"].mean(),
                "REC": football_games["Receptions"].mean(),
                "REC_YDS": football_games["Receiving Yards"].mean(),
                "REC_TD": football_games["Receiving TDs"].mean()
            }]).round(2)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Games Tracked", total_games)
                st.metric("Carries/Game",    my_avg.loc[0, "CAR"])
                st.metric("Rush Yards/Game", my_avg.loc[0, "RUSH_YDS"])
            with c2:
                st.metric("Rush TD/Game",    my_avg.loc[0, "RUSH_TD"])
                st.metric("Receptions/Game", my_avg.loc[0, "REC"])
            with c3:
                st.metric("Rec Yards/Game", my_avg.loc[0, "REC_YDS"])
                st.metric("Rec TD/Game",    my_avg.loc[0, "REC_TD"])

        elif football_mode == "WR/TE":
            football_games["CATCH_PCT"] = (
                football_games["Receptions"] / football_games["Targets"].replace(0, pd.NA)
            ).fillna(0)
            my_avg = pd.DataFrame([{
                "TGT": football_games["Targets"].mean(),
                "REC": football_games["Receptions"].mean(),
                "CATCH_PCT": football_games["CATCH_PCT"].mean(),
                "REC_YDS": football_games["Receiving Yards"].mean(),
                "REC_TD": football_games["Receiving TDs"].mean(),
                "RUSH_YDS": football_games["Rushing Yards"].mean(),
                "RUSH_TD": football_games["Rushing TDs"].mean()
            }]).round(2)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Games Tracked", total_games)
                st.metric("Targets/Game",    my_avg.loc[0, "TGT"])
                st.metric("Receptions/Game", my_avg.loc[0, "REC"])
            with c2:
                st.metric("Catch %",        round(my_avg.loc[0, "CATCH_PCT"] * 100, 1))
                st.metric("Rec Yards/Game", my_avg.loc[0, "REC_YDS"])
            with c3:
                st.metric("Rec TD/Game",    my_avg.loc[0, "REC_TD"])
                st.metric("Rush Yards/Game",my_avg.loc[0, "RUSH_YDS"])

        elif football_mode == "Defense":
            my_avg = pd.DataFrame([{
                "TACKLES": football_games["Tackles"].mean(),
                "ASSISTS": football_games["Assists"].mean(),
                "SACKS":   football_games["Sacks"].mean(),
                "INT":     football_games["Interceptions"].mean(),
                "PD":      football_games["Passes Defended"].mean(),
                "FF":      football_games["Forced Fumbles"].mean(),
                "FR":      football_games["Fumble Recoveries"].mean()
            }]).round(2)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Games Tracked", total_games)
                st.metric("Tackles/Game", my_avg.loc[0, "TACKLES"])
                st.metric("Assists/Game", my_avg.loc[0, "ASSISTS"])
            with c2:
                st.metric("Sacks/Game", my_avg.loc[0, "SACKS"])
                st.metric("INT/Game",   my_avg.loc[0, "INT"])
            with c3:
                st.metric("PD/Game", my_avg.loc[0, "PD"])
                st.metric("FF/Game", my_avg.loc[0, "FF"])

        st.subheader(f"NFL {football_mode} Comparison")
        nfl_season = st.selectbox(
            "Choose NFL season", [2023, 2024, 2025], index=2,
            key=f"nfl_season_{mode_key}"
        )

        try:
            nfl_players = load_nfl_player_data(nfl_season).copy()

            if football_mode == "QB":
                nfl_compare = nfl_players[nfl_players["position"] == "QB"].copy()
                nfl_compare["CMP_PCT"] = (
                    nfl_compare["completions"] / nfl_compare["attempts"].replace(0, pd.NA)
                ).fillna(0)
                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["passing_yards"] / nfl_compare["games"] - my_avg.loc[0, "PASS_YDS"]) / 45) ** 2 +
                    ((nfl_compare["passing_tds"]   / nfl_compare["games"] - my_avg.loc[0, "PASS_TD"])  / 0.9) ** 2 +
                    ((nfl_compare["passing_interceptions"] / nfl_compare["games"] - my_avg.loc[0, "INT"]) / 0.6) ** 2 +
                    ((nfl_compare["rushing_yards"] / nfl_compare["games"] - my_avg.loc[0, "RUSH_YDS"]) / 18) ** 2 +
                    ((nfl_compare["rushing_tds"]   / nfl_compare["games"] - my_avg.loc[0, "RUSH_TD"])  / 0.35) ** 2 +
                    ((nfl_compare["CMP_PCT"] - my_avg.loc[0, "CMP_PCT"]) / 0.08) ** 2
                ) ** 0.5
                stat_labels    = ["Pass Yards/G", "Pass TD/G", "INT/G", "Rush Yards/G", "Rush TD/G", "Cmp %"]
                my_profile_vals = [
                    my_avg.loc[0, "PASS_YDS"], my_avg.loc[0, "PASS_TD"], my_avg.loc[0, "INT"],
                    my_avg.loc[0, "RUSH_YDS"], my_avg.loc[0, "RUSH_TD"],
                    round(my_avg.loc[0, "CMP_PCT"] * 100, 1)
                ]
                def compare_table(row):
                    return [round(row["passing_yards"]/row["games"], 2),
                            round(row["passing_tds"]/row["games"], 2),
                            round(row["passing_interceptions"]/row["games"], 2),
                            round(row["rushing_yards"]/row["games"], 2),
                            round(row["rushing_tds"]/row["games"], 2),
                            round(row["CMP_PCT"]*100, 1)]

            elif football_mode == "RB":
                nfl_compare = nfl_players[nfl_players["position"] == "RB"].copy()
                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["carries"]         / nfl_compare["games"] - my_avg.loc[0, "CAR"])      / 4.0) ** 2 +
                    ((nfl_compare["rushing_yards"]   / nfl_compare["games"] - my_avg.loc[0, "RUSH_YDS"]) / 20)  ** 2 +
                    ((nfl_compare["rushing_tds"]     / nfl_compare["games"] - my_avg.loc[0, "RUSH_TD"])  / 0.4) ** 2 +
                    ((nfl_compare["receptions"]      / nfl_compare["games"] - my_avg.loc[0, "REC"])      / 2.0) ** 2 +
                    ((nfl_compare["receiving_yards"] / nfl_compare["games"] - my_avg.loc[0, "REC_YDS"])  / 18)  ** 2 +
                    ((nfl_compare["receiving_tds"]   / nfl_compare["games"] - my_avg.loc[0, "REC_TD"])   / 0.35)** 2
                ) ** 0.5
                stat_labels     = ["Carries/G", "Rush Yards/G", "Rush TD/G", "Receptions/G", "Rec Yards/G", "Rec TD/G"]
                my_profile_vals = [my_avg.loc[0, k] for k in ["CAR","RUSH_YDS","RUSH_TD","REC","REC_YDS","REC_TD"]]
                def compare_table(row):
                    return [round(row["carries"]/row["games"], 2),
                            round(row["rushing_yards"]/row["games"], 2),
                            round(row["rushing_tds"]/row["games"], 2),
                            round(row["receptions"]/row["games"], 2),
                            round(row["receiving_yards"]/row["games"], 2),
                            round(row["receiving_tds"]/row["games"], 2)]

            elif football_mode == "WR/TE":
                nfl_compare = nfl_players[nfl_players["position"].isin(["WR", "TE"])].copy()
                nfl_compare["CATCH_PCT"] = (
                    nfl_compare["receptions"] / nfl_compare["targets"].replace(0, pd.NA)
                ).fillna(0)
                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["targets"]         / nfl_compare["games"] - my_avg.loc[0, "TGT"])      / 2.5) ** 2 +
                    ((nfl_compare["receptions"]      / nfl_compare["games"] - my_avg.loc[0, "REC"])      / 2.0) ** 2 +
                    ((nfl_compare["receiving_yards"] / nfl_compare["games"] - my_avg.loc[0, "REC_YDS"])  / 20)  ** 2 +
                    ((nfl_compare["receiving_tds"]   / nfl_compare["games"] - my_avg.loc[0, "REC_TD"])   / 0.35)** 2 +
                    ((nfl_compare["rushing_yards"]   / nfl_compare["games"] - my_avg.loc[0, "RUSH_YDS"]) / 12)  ** 2 +
                    ((nfl_compare["CATCH_PCT"] - my_avg.loc[0, "CATCH_PCT"]) / 0.10) ** 2
                ) ** 0.5
                stat_labels     = ["Targets/G", "Receptions/G", "Rec Yards/G", "Rec TD/G", "Rush Yards/G", "Catch %"]
                my_profile_vals = [my_avg.loc[0, k] for k in ["TGT","REC","REC_YDS","REC_TD","RUSH_YDS"]] + \
                                  [round(my_avg.loc[0, "CATCH_PCT"] * 100, 1)]
                def compare_table(row):
                    return [round(row["targets"]/row["games"], 2),
                            round(row["receptions"]/row["games"], 2),
                            round(row["receiving_yards"]/row["games"], 2),
                            round(row["receiving_tds"]/row["games"], 2),
                            round(row["rushing_yards"]/row["games"], 2),
                            round(row["CATCH_PCT"]*100, 1)]

            elif football_mode == "Defense":
                def_positions = ["LB","ILB","OLB","MLB","CB","S","SS","FS","DB",
                                 "DE","DT","DL","EDGE","SAF","NT"]
                nfl_compare = nfl_players[nfl_players["position"].isin(def_positions)].copy()
                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["def_tackles_solo"]   / nfl_compare["games"] - my_avg.loc[0, "TACKLES"]) / 2.5) ** 2 +
                    ((nfl_compare["def_tackle_assists"] / nfl_compare["games"] - my_avg.loc[0, "ASSISTS"]) / 1.5) ** 2 +
                    ((nfl_compare["def_sacks"]          / nfl_compare["games"] - my_avg.loc[0, "SACKS"])   / 0.5) ** 2 +
                    ((nfl_compare["def_interceptions"]  / nfl_compare["games"] - my_avg.loc[0, "INT"])     / 0.25)** 2 +
                    ((nfl_compare["def_pass_defended"]  / nfl_compare["games"] - my_avg.loc[0, "PD"])      / 0.8) ** 2 +
                    ((nfl_compare["def_fumbles_forced"] / nfl_compare["games"] - my_avg.loc[0, "FF"])      / 0.25)** 2 +
                    ((nfl_compare["def_fumbles"]        / nfl_compare["games"] - my_avg.loc[0, "FR"])      / 0.25)** 2
                ) ** 0.5
                stat_labels     = ["Tackles/G","Assists/G","Sacks/G","INT/G","PD/G","FF/G","FR/G"]
                my_profile_vals = [my_avg.loc[0, k] for k in ["TACKLES","ASSISTS","SACKS","INT","PD","FF","FR"]]
                def compare_table(row):
                    return [round(row["def_tackles_solo"]/row["games"], 2),
                            round(row["def_tackle_assists"]/row["games"], 2),
                            round(row["def_sacks"]/row["games"], 2),
                            round(row["def_interceptions"]/row["games"], 2),
                            round(row["def_pass_defended"]/row["games"], 2),
                            round(row["def_fumbles_forced"]/row["games"], 2),
                            round(row["def_fumbles"]/row["games"], 2)]

            nfl_compare = nfl_compare[nfl_compare["games"] > 0].copy()
            nfl_compare["Similarity Score"] = (1 / (1 + nfl_compare["DISTANCE"])).round(3)
            top_matches  = nfl_compare.sort_values("DISTANCE").head(5).reset_index(drop=True)
            closest_nfl  = top_matches.iloc[0]

            st.metric("Closest NFL Match", closest_nfl["player_name"])
            st.write("Team:", closest_nfl["team"])
            st.write("Position:", closest_nfl["position"])

            st.dataframe(pd.DataFrame({
                "Stat": stat_labels,
                "My Profile": my_profile_vals,
                closest_nfl["player_name"]: compare_table(closest_nfl)
            }), hide_index=True)

            st.write("Top 5 NFL matches:")
            st.dataframe(
                top_matches[["player_name", "team", "position", "games", "Similarity Score"]],
                hide_index=True
            )
            match_fig = px.bar(top_matches, x="Similarity Score", y="player_name",
                               orientation="h", title=f"Top NFL {football_mode} Matches")
            match_fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(match_fig, use_container_width=True)

        except Exception as e:
            st.warning(f"Could not load NFL comparison data: {e}")

        st.subheader("Performance Trends")
        trend_options = {
            "QB": ["Passing Yards", "Passing TDs", "Interceptions", "Rushing Yards", "Rushing TDs"],
            "RB": ["Carries", "Rushing Yards", "Rushing TDs", "Receptions", "Receiving Yards", "Receiving TDs"],
            "WR/TE": ["Targets", "Receptions", "Receiving Yards", "Receiving TDs", "Rushing Yards", "Rushing TDs"],
            "Defense": ["Tackles", "Assists", "Sacks", "Interceptions", "Passes Defended",
                        "Forced Fumbles", "Fumble Recoveries"]
        }
        trend_choice = st.selectbox("Choose a stat", trend_options[football_mode],
                                    key=f"football_trend_{mode_key}")
        trend_fig = px.line(football_games, x="Date", y=trend_choice,
                            markers=True, hover_data=["Opponent"],
                            title=f"{trend_choice} Over Time")
        st.plotly_chart(trend_fig, use_container_width=True)

        render_ai_coach_section(f"Football {football_mode}", st.session_state[session_key]) # NEW
        

        st.subheader("My Game Log")
        f_log = football_games[FOOTBALL_COLUMNS].copy()
        f_log["Date"] = f_log["Date"].dt.strftime("%Y-%m-%d")
        f_log.index = f_log.index + 1
        st.dataframe(f_log)

        st.subheader("Delete a Game")
        f_del_df = football_games.copy()
        f_del_df["Date_str"] = f_del_df["Date"].dt.strftime("%Y-%m-%d")

        label_map = {
            "QB":      lambda r: f"{r['Date_str']} vs {r['Opponent']} | Pass: {int(r['Passing Yards'])}, TD: {int(r['Passing TDs'])}",
            "RB":      lambda r: f"{r['Date_str']} vs {r['Opponent']} | Rush: {int(r['Rushing Yards'])}, Rec: {int(r['Receiving Yards'])}",
            "WR/TE":   lambda r: f"{r['Date_str']} vs {r['Opponent']} | Rec: {int(r['Receiving Yards'])}, TD: {int(r['Receiving TDs'])}",
            "Defense": lambda r: f"{r['Date_str']} vs {r['Opponent']} | Tackles: {int(r['Tackles'])}, Sacks: {r['Sacks']}"
        }
        f_del_df["Delete Label"] = f_del_df.apply(label_map[football_mode], axis=1)

        f_del_idx = st.selectbox(
            f"Choose a {football_mode} game to delete",
            options=f_del_df.index,
            format_func=lambda i: f_del_df.loc[i, "Delete Label"],
            key=f"delete_football_game_{mode_key}"
        )
        if st.button(f"Delete Selected {football_mode} Game"):
            st.session_state[session_key] = st.session_state[session_key].drop(
                st.session_state[session_key].index[f_del_idx]
            ).reset_index(drop=True)
            save_to_db(db_key, st.session_state[session_key])
            st.success("Game deleted.")
            st.rerun()


# ===================================
# TRADING CARD PAGE
# ===================================

if page == "Trading Card":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    st.title("🃏 Trading Card Generator")
    st.write("Upload a photo and generate a realistic premium trading card with your real stats.")

    col1, col2 = st.columns(2)

    with col1:
        card_name = st.text_input("Your Name")
        card_team = st.text_input("Team")
        card_age = st.number_input("Your Age", min_value=10, max_value=80, value=25)

    with col2:
        card_sport = sport
        card_position = st.text_input("Position")
        card_number = st.text_input("Jersey Number")

    uploaded_photo = st.file_uploader("Upload your photo", type=["jpg", "jpeg", "png"])

    st.subheader("Your Saved Stats")
    st.caption("These will appear on your card automatically.")

    stat_lines = []

    if sport == "Basketball" and len(st.session_state.get("my_games", pd.DataFrame())) > 0:
        g = st.session_state.my_games.copy()

        for col in ["Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"]:
            g[col] = pd.to_numeric(g[col], errors="coerce")

        stat_lines = [
            f"PPG: {g['Points'].mean():.1f}",
            f"RPG: {g['Rebounds'].mean():.1f}",
            f"APG: {g['Assists'].mean():.1f}",
            f"SPG: {g['Steals'].mean():.1f}",
            f"BPG: {g['Blocks'].mean():.1f}",
            f"GP: {len(g)}"
        ]

    elif sport == "Baseball":
        hit = st.session_state.get("my_baseball_games", pd.DataFrame())
        pit = st.session_state.get("my_pitching_games", pd.DataFrame())

        if card_position.lower() in ["pitcher", "p", "sp", "rp", "cp"] and len(pit) > 0:
            pit = pit.copy()

            for col in ["Innings Pitched", "Strikeouts", "Walks", "Earned Runs", "Hits Allowed"]:
                pit[col] = pd.to_numeric(pit[col], errors="coerce")

            total_ip = pit["Innings Pitched"].sum()
            era = pit["Earned Runs"].sum() / total_ip * 9 if total_ip > 0 else 0
            whip = (pit["Walks"].sum() + pit["Hits Allowed"].sum()) / total_ip if total_ip > 0 else 0

            stat_lines = [
                f"ERA: {era:.2f}",
                f"WHIP: {whip:.2f}",
                f"K: {int(pit['Strikeouts'].sum())}",
                f"IP: {total_ip:.1f}",
                f"GP: {len(pit)}"
            ]

        elif len(hit) > 0:
            hit = hit.copy()

            for col in ["At Bats", "Hits", "Home Runs", "RBIs", "Stolen Bases", "Walks"]:
                hit[col] = pd.to_numeric(hit[col], errors="coerce")

            total_ab = hit["At Bats"].sum()
            total_hits = hit["Hits"].sum()
            avg = total_hits / total_ab if total_ab > 0 else 0

            stat_lines = [
                f"AVG: {avg:.3f}",
                f"HR: {int(hit['Home Runs'].sum())}",
                f"RBI: {int(hit['RBIs'].sum())}",
                f"SB: {int(hit['Stolen Bases'].sum())}",
                f"GP: {len(hit)}"
            ]

    elif sport == "Football":
        mode_key_map = {"QB": "qb", "RB": "rb", "WR/TE": "wrte", "Defense": "def"}
        pos_upper = card_position.upper()

        if pos_upper in mode_key_map:
            mk = mode_key_map[pos_upper]
        elif any(p in pos_upper for p in ["WR", "TE"]):
            mk = "wrte"
        elif any(p in pos_upper for p in ["LB", "CB", "S", "DE", "DT", "DB", "SAF"]):
            mk = "def"
        elif "RB" in pos_upper:
            mk = "rb"
        else:
            mk = "qb"

        fk = f"my_football_games_{mk}"
        fg = st.session_state.get(fk, pd.DataFrame())

        if len(fg) > 0:
            fg = fg.copy()

            if mk == "qb":
                for col in ["Passing Yards", "Passing TDs", "Interceptions", "Rushing Yards"]:
                    fg[col] = pd.to_numeric(fg[col], errors="coerce")

                stat_lines = [
                    f"PASS YDS/G: {fg['Passing Yards'].mean():.0f}",
                    f"PASS TD/G: {fg['Passing TDs'].mean():.1f}",
                    f"INT/G: {fg['Interceptions'].mean():.1f}",
                    f"RUSH YDS/G: {fg['Rushing Yards'].mean():.0f}",
                    f"GP: {len(fg)}"
                ]

            elif mk == "rb":
                for col in ["Rushing Yards", "Rushing TDs", "Receptions", "Receiving Yards"]:
                    fg[col] = pd.to_numeric(fg[col], errors="coerce")

                stat_lines = [
                    f"RUSH YDS/G: {fg['Rushing Yards'].mean():.0f}",
                    f"RUSH TD/G: {fg['Rushing TDs'].mean():.1f}",
                    f"REC/G: {fg['Receptions'].mean():.1f}",
                    f"REC YDS/G: {fg['Receiving Yards'].mean():.0f}",
                    f"GP: {len(fg)}"
                ]

            elif mk == "wrte":
                for col in ["Receiving Yards", "Receiving TDs", "Receptions", "Targets"]:
                    fg[col] = pd.to_numeric(fg[col], errors="coerce")

                stat_lines = [
                    f"REC YDS/G: {fg['Receiving Yards'].mean():.0f}",
                    f"REC TD/G: {fg['Receiving TDs'].mean():.1f}",
                    f"REC/G: {fg['Receptions'].mean():.1f}",
                    f"TGT/G: {fg['Targets'].mean():.1f}",
                    f"GP: {len(fg)}"
                ]

            elif mk == "def":
                for col in ["Tackles", "Sacks", "Interceptions"]:
                    fg[col] = pd.to_numeric(fg[col], errors="coerce")

                stat_lines = [
                    f"TACKLES/G: {fg['Tackles'].mean():.1f}",
                    f"SACKS/G: {fg['Sacks'].mean():.1f}",
                    f"INT/G: {fg['Interceptions'].mean():.1f}",
                    f"GP: {len(fg)}"
                ]

    if stat_lines:
        for s in stat_lines:
            st.write(s)
    else:
        st.info(f"No {sport} stats saved yet. You can still generate a card.")

    card_pro_match = None

    if sport == "Basketball" and len(st.session_state.get("my_games", pd.DataFrame())) > 0:
        try:
            g = st.session_state.my_games.copy()
            for col in ["Points","Rebounds","Assists","Steals","Blocks","Turnovers","Team Score"]:
                g[col] = pd.to_numeric(g[col], errors="coerce")
            NBA_AVG_TEAM_PTS = 115.0
            g["SF"] = (NBA_AVG_TEAM_PTS / g["Team Score"].replace(0, pd.NA)).fillna(1.0).clip(0.6, 4.5)
            my_avg_adj = {
                "PTS": (g["Points"]    * g["SF"]).mean(),
                "REB": (g["Rebounds"]  * g["SF"] ** 0.5).mean(),
                "AST": (g["Assists"]   * g["SF"]).mean(),
                "STL": (g["Steals"]    * g["SF"] ** 0.3).mean(),
                "BLK": (g["Blocks"]    * g["SF"] ** 0.3).mean(),
                "TOV": (g["Turnovers"] * g["SF"]).mean(),
            }
            nba_players = load_player_data("2025-26")
            nba_players = nba_players[nba_players["GP"] >= 40]
            nba_players = nba_players[nba_players["MIN"] >= 20].reset_index(drop=True)
            nba_players["DISTANCE"] = (
                (nba_players["PTS"] - my_avg_adj["PTS"]) ** 2 +
                (nba_players["REB"] - my_avg_adj["REB"]) ** 2 +
                (nba_players["AST"] - my_avg_adj["AST"]) ** 2 +
                (nba_players["STL"] - my_avg_adj["STL"]) ** 2 +
                (nba_players["BLK"] - my_avg_adj["BLK"]) ** 2 +
                (nba_players["TOV"] - my_avg_adj["TOV"]) ** 2
            ) ** 0.5
            best = nba_players.sort_values("DISTANCE").iloc[0]
            card_pro_match = f"{best['PLAYER_NAME']} ({best['TEAM_ABBREVIATION']})"
        except:
            pass

    elif sport == "Baseball":
        try:
            hit = st.session_state.get("my_baseball_games", pd.DataFrame())
            pit = st.session_state.get("my_pitching_games", pd.DataFrame())
            is_pitcher = card_position.lower() in ["pitcher","p","sp","rp","cp"]
            if is_pitcher and len(pit) > 0:
                for col in ["Innings Pitched","Strikeouts","Walks","Earned Runs","Hits Allowed"]:
                    pit[col] = pd.to_numeric(pit[col], errors="coerce")
                total_ip = pit["Innings Pitched"].sum()
                era  = pit["Earned Runs"].sum() / total_ip * 9 if total_ip > 0 else 0
                whip = (pit["Walks"].sum() + pit["Hits Allowed"].sum()) / total_ip if total_ip > 0 else 0
                k9   = pit["Strikeouts"].sum() / total_ip * 9 if total_ip > 0 else 0
                bb9  = pit["Walks"].sum() / total_ip * 9 if total_ip > 0 else 0
                mlb  = load_mlb_pitching_data(2025)
                mlb["DISTANCE"] = (
                    ((mlb["ERA"]      - era)  / 1.0)  ** 2 +
                    ((mlb["WHIP"]     - whip) / 0.20) ** 2 +
                    ((mlb["K_PER_9"]  - k9)   / 2.0)  ** 2 +
                    ((mlb["BB_PER_9"] - bb9)  / 1.0)  ** 2
                ) ** 0.5
                best = mlb.sort_values("DISTANCE").iloc[0]
                card_pro_match = f"{best['Name']} ({best['Team']})"
            elif not is_pitcher and len(hit) > 0:
                for col in ["At Bats","Hits","Home Runs","RBIs","Stolen Bases","Walks","Doubles","Triples"]:
                    hit[col] = pd.to_numeric(hit[col], errors="coerce")
                total_ab = hit["At Bats"].sum()
                total_h  = hit["Hits"].sum()
                total_w  = hit["Walks"].sum()
                singles  = max(total_h - hit["Doubles"].sum() - hit["Triples"].sum() - hit["Home Runs"].sum(), 0)
                slg_num  = singles + 2*hit["Doubles"].sum() + 3*hit["Triples"].sum() + 4*hit["Home Runs"].sum()
                avg = total_h / total_ab if total_ab > 0 else 0
                obp = (total_h + total_w) / (total_ab + total_w) if (total_ab + total_w) > 0 else 0
                slg = slg_num / total_ab if total_ab > 0 else 0
                ops = obp + slg
                n_g = len(hit)
                mlb = load_mlb_batting_data(2025)
                mlb["EST_G"]        = (mlb["PA"] / 4.2).clip(lower=1)
                mlb["HR_PER_GAME"]  = mlb["HR"]  / mlb["EST_G"]
                mlb["RBI_PER_GAME"] = mlb["RBI"] / mlb["EST_G"]
                mlb["SB_PER_GAME"]  = mlb["SB"]  / mlb["EST_G"]
                mlb["DISTANCE"] = (
                    ((mlb["AVG"] - avg) / 0.030) ** 2 +
                    ((mlb["OBP"] - obp) / 0.040) ** 2 +
                    ((mlb["SLG"] - slg) / 0.060) ** 2 +
                    ((mlb["OPS"] - ops) / 0.090) ** 2 +
                    ((mlb["HR_PER_GAME"]  - hit["Home Runs"].sum()/n_g) / 0.12) ** 2 +
                    ((mlb["RBI_PER_GAME"] - hit["RBIs"].sum()/n_g)      / 0.20) ** 2 +
                    ((mlb["SB_PER_GAME"]  - hit["Stolen Bases"].sum()/n_g) / 0.10) ** 2
                ) ** 0.5
                best = mlb.sort_values("DISTANCE").iloc[0]
                card_pro_match = f"{best['Name']} ({best['Team']})"
        except:
            pass

    elif sport == "Football":
        try:
            pos_upper = card_position.upper().strip()

            if pos_upper in ["QB", "QUARTERBACK"]:
                mk = "qb"
            elif pos_upper in ["RB", "RUNNING BACK", "HALFBACK"]:
                mk = "rb"
            elif any(p in pos_upper for p in ["WR", "TE", "WIDE RECEIVER", "RECEIVER", "TIGHT END"]):
                mk = "wrte"
            elif any(p in pos_upper for p in ["DEF", "DEFENSE", "LB", "CB", "S", "DE", "DT", "DB", "SAF", "EDGE"]):
                mk = "def"
            else:
                mk = "qb"

            fg = st.session_state.get(f"my_football_games_{mk}", pd.DataFrame())

            if len(fg) > 0:
                fg = fg.copy()
                nfl_players = load_nfl_player_data(2025)

                if mk == "qb":
                    for col in ["Completions", "Attempts", "Passing Yards", "Passing TDs", "Interceptions", "Rushing Yards", "Rushing TDs"]:
                        fg[col] = pd.to_numeric(fg[col], errors="coerce")

                    fg["CMP_PCT"] = (
                        fg["Completions"] / fg["Attempts"].replace(0, pd.NA)
                    ).fillna(0)

                    my_avg = pd.DataFrame([{
                        "CMP_PCT": fg["CMP_PCT"].mean(),
                        "PASS_YDS": fg["Passing Yards"].mean(),
                        "PASS_TD": fg["Passing TDs"].mean(),
                        "INT": fg["Interceptions"].mean(),
                        "RUSH_YDS": fg["Rushing Yards"].mean(),
                        "RUSH_TD": fg["Rushing TDs"].mean()
                    }])

                    nfl_c = nfl_players[nfl_players["position"] == "QB"].copy()

                    nfl_c["CMP_PCT"] = (
                        nfl_c["completions"] / nfl_c["attempts"].replace(0, pd.NA)
                    ).fillna(0)

                    nfl_c["DISTANCE"] = (
                        ((nfl_c["passing_yards"] / nfl_c["games"] - my_avg.loc[0, "PASS_YDS"]) / 45) ** 2 +
                        ((nfl_c["passing_tds"] / nfl_c["games"] - my_avg.loc[0, "PASS_TD"]) / 0.9) ** 2 +
                        ((nfl_c["passing_interceptions"] / nfl_c["games"] - my_avg.loc[0, "INT"]) / 0.6) ** 2 +
                        ((nfl_c["rushing_yards"] / nfl_c["games"] - my_avg.loc[0, "RUSH_YDS"]) / 18) ** 2 +
                        ((nfl_c["rushing_tds"] / nfl_c["games"] - my_avg.loc[0, "RUSH_TD"]) / 0.35) ** 2 +
                        ((nfl_c["CMP_PCT"] - my_avg.loc[0, "CMP_PCT"]) / 0.08) ** 2
                    ) ** 0.5

                elif mk == "rb":
                    for col in ["Carries", "Rushing Yards", "Rushing TDs", "Receptions", "Receiving Yards", "Receiving TDs"]:
                        fg[col] = pd.to_numeric(fg[col], errors="coerce")

                    my_avg = pd.DataFrame([{
                        "CAR": fg["Carries"].mean(),
                        "RUSH_YDS": fg["Rushing Yards"].mean(),
                        "RUSH_TD": fg["Rushing TDs"].mean(),
                        "REC": fg["Receptions"].mean(),
                        "REC_YDS": fg["Receiving Yards"].mean(),
                        "REC_TD": fg["Receiving TDs"].mean()
                    }])

                    nfl_c = nfl_players[nfl_players["position"] == "RB"].copy()

                    nfl_c["DISTANCE"] = (
                        ((nfl_c["carries"] / nfl_c["games"] - my_avg.loc[0, "CAR"]) / 4.0) ** 2 +
                        ((nfl_c["rushing_yards"] / nfl_c["games"] - my_avg.loc[0, "RUSH_YDS"]) / 20) ** 2 +
                        ((nfl_c["rushing_tds"] / nfl_c["games"] - my_avg.loc[0, "RUSH_TD"]) / 0.4) ** 2 +
                        ((nfl_c["receptions"] / nfl_c["games"] - my_avg.loc[0, "REC"]) / 2.0) ** 2 +
                        ((nfl_c["receiving_yards"] / nfl_c["games"] - my_avg.loc[0, "REC_YDS"]) / 18) ** 2 +
                        ((nfl_c["receiving_tds"] / nfl_c["games"] - my_avg.loc[0, "REC_TD"]) / 0.35) ** 2
                    ) ** 0.5

                elif mk == "wrte":
                    for col in ["Targets", "Receptions", "Receiving Yards", "Receiving TDs", "Rushing Yards", "Rushing TDs"]:
                        fg[col] = pd.to_numeric(fg[col], errors="coerce")

                    fg["CATCH_PCT"] = (
                        fg["Receptions"] / fg["Targets"].replace(0, pd.NA)
                    ).fillna(0)

                    my_avg = pd.DataFrame([{
                        "TGT": fg["Targets"].mean(),
                        "REC": fg["Receptions"].mean(),
                        "CATCH_PCT": fg["CATCH_PCT"].mean(),
                        "REC_YDS": fg["Receiving Yards"].mean(),
                        "REC_TD": fg["Receiving TDs"].mean(),
                        "RUSH_YDS": fg["Rushing Yards"].mean()
                    }])

                    nfl_c = nfl_players[nfl_players["position"].isin(["WR", "TE"])].copy()

                    nfl_c["CATCH_PCT"] = (
                        nfl_c["receptions"] / nfl_c["targets"].replace(0, pd.NA)
                    ).fillna(0)

                    nfl_c["DISTANCE"] = (
                        ((nfl_c["targets"] / nfl_c["games"] - my_avg.loc[0, "TGT"]) / 2.5) ** 2 +
                        ((nfl_c["receptions"] / nfl_c["games"] - my_avg.loc[0, "REC"]) / 2.0) ** 2 +
                        ((nfl_c["receiving_yards"] / nfl_c["games"] - my_avg.loc[0, "REC_YDS"]) / 20) ** 2 +
                        ((nfl_c["receiving_tds"] / nfl_c["games"] - my_avg.loc[0, "REC_TD"]) / 0.35) ** 2 +
                        ((nfl_c["rushing_yards"] / nfl_c["games"] - my_avg.loc[0, "RUSH_YDS"]) / 12) ** 2 +
                        ((nfl_c["CATCH_PCT"] - my_avg.loc[0, "CATCH_PCT"]) / 0.10) ** 2
                    ) ** 0.5

                elif mk == "def":
                    for col in ["Tackles", "Assists", "Sacks", "Interceptions", "Passes Defended", "Forced Fumbles", "Fumble Recoveries"]:
                        fg[col] = pd.to_numeric(fg[col], errors="coerce")

                    my_avg = pd.DataFrame([{
                        "TACKLES": fg["Tackles"].mean(),
                        "ASSISTS": fg["Assists"].mean(),
                        "SACKS": fg["Sacks"].mean(),
                        "INT": fg["Interceptions"].mean(),
                        "PD": fg["Passes Defended"].mean(),
                        "FF": fg["Forced Fumbles"].mean(),
                        "FR": fg["Fumble Recoveries"].mean()
                    }])

                    def_positions = ["LB", "ILB", "OLB", "MLB", "CB", "S", "SS", "FS", "DB", "DE", "DT", "DL", "EDGE", "SAF", "NT"]
                    nfl_c = nfl_players[nfl_players["position"].isin(def_positions)].copy()

                    nfl_c["DISTANCE"] = (
                        ((nfl_c["def_tackles_solo"] / nfl_c["games"] - my_avg.loc[0, "TACKLES"]) / 2.5) ** 2 +
                        ((nfl_c["def_tackle_assists"] / nfl_c["games"] - my_avg.loc[0, "ASSISTS"]) / 1.5) ** 2 +
                        ((nfl_c["def_sacks"] / nfl_c["games"] - my_avg.loc[0, "SACKS"]) / 0.5) ** 2 +
                        ((nfl_c["def_interceptions"] / nfl_c["games"] - my_avg.loc[0, "INT"]) / 0.25) ** 2 +
                        ((nfl_c["def_pass_defended"] / nfl_c["games"] - my_avg.loc[0, "PD"]) / 0.8) ** 2 +
                        ((nfl_c["def_fumbles_forced"] / nfl_c["games"] - my_avg.loc[0, "FF"]) / 0.25) ** 2 +
                        ((nfl_c["def_fumbles"] / nfl_c["games"] - my_avg.loc[0, "FR"]) / 0.25) ** 2
                    ) ** 0.5

                nfl_c = nfl_c[nfl_c["games"] > 0].copy()
                best = nfl_c.sort_values("DISTANCE").iloc[0]
                card_pro_match = f"{best['player_name']} ({best['team']})"

        except:
            pass

    if st.button("✨ Generate My Trading Card", use_container_width=True):
        if not card_name:
            st.error("Please enter your name.")
        elif not uploaded_photo:
            st.error("Please upload a photo.")
        else:
            import requests
            import openai
            import random
            from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
            from io import BytesIO
            from rembg import remove

            progress = st.progress(0)
            status = st.empty()

            with st.spinner("🃏 Generating your trading card..."):
                def safe_text(value, fallback=""):
                    value = str(value).strip()
                    return value if value else fallback

                def fit_font(draw_obj, text, font_path, max_width, start_size, min_size=16):
                    if font_path is None:
                        return ImageFont.load_default()
                    size = start_size
                    while size >= min_size:
                        font = ImageFont.truetype(font_path, size)
                        bbox = draw_obj.textbbox((0, 0), text, font=font)
                        width = bbox[2] - bbox[0]
                        if width <= max_width:
                            return font
                        size -= 2
                    return ImageFont.truetype(font_path, min_size)

                def add_subtle_noise(img, opacity=18):
                    W, H = img.size
                    noise = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    pixels = noise.load()
                    for _ in range(18000):
                        x = random.randint(0, W - 1)
                        y = random.randint(0, H - 1)
                        v = random.randint(180, 255)
                        a = random.randint(4, opacity)
                        pixels[x, y] = (v, v, v, a)
                    return Image.alpha_composite(img, noise)

                def add_vignette(img):
                    W, H = img.size
                    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    vdraw = ImageDraw.Draw(vignette)
                    for i in range(170):
                        alpha = int(i * 0.75)
                        vdraw.rounded_rectangle(
                            [(i, i), (W - i, H - i)],
                            radius=42,
                            outline=(0, 0, 0, max(0, 120 - alpha)),
                            width=3
                        )
                    return Image.alpha_composite(img, vignette)

                def crop_or_pad_to_card(img, size=(1024, 1024)):
                    return img.resize(size, Image.Resampling.LANCZOS)

                def jersey_number_badge(draw_obj, number, font_path, cx, cy, radius=50):
                    draw_obj.ellipse(
                        [(cx - radius, cy - radius), (cx + radius, cy + radius)],
                        fill=(6, 8, 20, 240),
                        outline=(255, 215, 0, 255),
                        width=4
                    )
                    draw_obj.ellipse(
                        [(cx - radius + 6, cy - radius + 6),
                         (cx + radius - 6, cy + radius - 6)],
                        outline=(255, 255, 255, 40),
                        width=2
                    )
                    num_text = f"#{number}" if number else "#0"
                    nfont = fit_font(draw_obj, num_text, font_path,
                                    max_width=radius * 2 - 16, start_size=36, min_size=18)
                    draw_obj.text((cx, cy), num_text, font=nfont,
                                  fill=(255, 215, 0), anchor="mm")

                photo_bytes = uploaded_photo.read()
                progress.progress(8)

                status.info("🎨 Creating card background...")

                team_clean = safe_text(card_team, "professional team")
                sport_clean = safe_text(card_sport, "sports")

                dalle_prompt = (
                    f"Realistic premium sports trading card background for a {sport_clean} player associated with {team_clean}. Authentic modern sports card aesthetic with realistic arena lighting, subtle team-inspired colors, premium printed-card texture,clean cinematic arena atmosphere with shallow depth of field, empty arena background with no athletes or spectators in focus, and elegant collectible-card framing. The composition should look like a real high-end sports card sold in stores. The main focus area should remain visually uncluttered for placing a player image later. The bottom portion should naturally support a player name and stats later. In the background there should be no people, no mascots, no readable text, no numbers, no scoreboards, no diagrams, no data panels, no statistics graphics, no UI elements, no infographics, no extra athletes. Not futuristic, not cyberpunk, not sci-fi.")

                openai_client = openai.OpenAI(api_key=st.secrets["OPENAI_KEY"])
                image_response = openai_client.images.generate(
                    model="dall-e-3",
                    prompt=dalle_prompt,
                    size="1024x1024",
                    quality="hd",
                    n=1
                )

                img_data = requests.get(image_response.data[0].url).content
                card_bg = Image.open(BytesIO(img_data)).convert("RGBA")
                card_bg = crop_or_pad_to_card(card_bg, (1024, 1024))

                progress.progress(38)

                status.info("✂️ Cutting out the player photo...")

                user_img = Image.open(BytesIO(photo_bytes)).convert("RGBA")
                removed_bg = remove(user_img)

                card_W, card_H = card_bg.size

                target_h = int(card_H * 0.81)
                ratio = target_h / removed_bg.height
                target_w = int(removed_bg.width * ratio)

                if target_w > int(card_W * 0.82):
                    target_w = int(card_W * 0.82)
                    ratio = target_w / removed_bg.width
                    target_h = int(removed_bg.height * ratio)

                cutout = removed_bg.resize((target_w, target_h), Image.Resampling.LANCZOS)

                paste_x = (card_W - target_w) // 2
                paste_y = int(card_H * 0.035)

                cutout = ImageEnhance.Contrast(cutout).enhance(1.05)
                cutout = ImageEnhance.Sharpness(cutout).enhance(1.10)
                cutout = ImageEnhance.Color(cutout).enhance(1.04)

                progress.progress(58)

                status.info("✨ Blending photo into the card...")

                glow = Image.new("RGBA", card_bg.size, (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow)
                glow_draw.ellipse(
                    (paste_x - 65, paste_y - 40,
                     paste_x + target_w + 65, paste_y + target_h + 45),
                    fill=(255, 255, 255, 32)
                )
                glow = glow.filter(ImageFilter.GaussianBlur(26))
                card_bg = Image.alpha_composite(card_bg, glow)

                shadow = Image.new("RGBA", card_bg.size, (0, 0, 0, 0))
                shadow.paste(cutout, (paste_x + 16, paste_y + 22), cutout)
                shadow = shadow.filter(ImageFilter.GaussianBlur(16))
                shadow_overlay = Image.new("RGBA", card_bg.size, (0, 0, 0, 0))
                shadow_overlay = Image.alpha_composite(shadow_overlay, shadow)
                card_bg = Image.alpha_composite(card_bg, shadow_overlay)

                card_bg.paste(cutout, (paste_x, paste_y), cutout)

                progress.progress(70)

                status.info("🏷️ Adding nameplate, stats, and card frame...")

                W, H = card_bg.size
                draw = ImageDraw.Draw(card_bg)

                panel_top = int(H * 0.735)
                font_path = "Inter-Regular.ttf"

                header_overlay = Image.new("RGBA", card_bg.size, (0, 0, 0, 0))
                hdraw = ImageDraw.Draw(header_overlay)
                hdraw.rounded_rectangle(
                    [(210, 58), (W - 210, 148)],
                    radius=28,
                    fill=(8, 10, 18, 230),
                    outline=(255, 255, 255, 70),
                    width=2
                )
                hdraw.rounded_rectangle(
                    [(270, 88), (W - 270, 100)],
                    radius=6,
                    fill=(255, 215, 0, 160)
                )
                header_text = f"{safe_text(card_team, 'TEAM').upper()}  •  {safe_text(card_sport, 'SPORT').upper()}"
                header_font = fit_font(
                    ImageDraw.Draw(card_bg), header_text, font_path,
                    max_width=W - 520, start_size=24, min_size=14
                )
                card_bg = Image.alpha_composite(card_bg, header_overlay)
                draw = ImageDraw.Draw(card_bg)
                draw.text((W // 2, 126), header_text, font=header_font,
                          fill=(220, 220, 230), anchor="mm")

                jersey_number_badge(draw, safe_text(card_number, "0"), font_path,
                                    cx=W - 72, cy=72, radius=50)

                panel = Image.new("RGBA", card_bg.size, (0, 0, 0, 0))
                pdraw = ImageDraw.Draw(panel)
                for y in range(panel_top - 22, H):
                    t = (y - (panel_top - 22)) / (H - (panel_top - 22))
                    alpha = int(120 + 125 * min(max(t, 0), 1))
                    pdraw.line([(0, y), (W, y)], fill=(6, 8, 22, alpha))
                pdraw.rounded_rectangle(
                    [(54, panel_top - 10), (W - 54, H - 58)],
                    radius=32,
                    fill=(8, 10, 28, 218),
                    outline=(255, 255, 255, 35),
                    width=2
                )
                card_bg = Image.alpha_composite(card_bg, panel)
                draw = ImageDraw.Draw(card_bg)

                shine = Image.new("RGBA", card_bg.size, (0, 0, 0, 0))
                sdraw = ImageDraw.Draw(shine)
                sdraw.polygon([(-160, 0), (60, 0), (W - 260, H), (W - 520, H)],
                              fill=(255, 255, 255, 24))
                sdraw.polygon([(W - 60, 0), (W + 160, 0), (420, H), (230, H)],
                              fill=(255, 255, 255, 12))
                card_bg = Image.alpha_composite(card_bg, shine)
                draw = ImageDraw.Draw(card_bg)

                try:
                    ImageFont.truetype(font_path, 20)
                except:
                    font_path = None

                name_text = safe_text(card_name, "PLAYER").upper()
                font_name = fit_font(draw, name_text, font_path,
                                     max_width=W - 260, start_size=48, min_size=28)
                name_y = panel_top + 34
                name_bbox = draw.textbbox((0, 0), name_text, font=font_name)
                name_w = name_bbox[2] - name_bbox[0]
                name_h = name_bbox[3] - name_bbox[1]
                pad_x, pad_y = 34, 13
                draw.rounded_rectangle(
                    [(W - name_w) // 2 - pad_x, name_y - name_h // 2 - pad_y,
                     (W + name_w) // 2 + pad_x, name_y + name_h // 2 + pad_y],
                    radius=16,
                    fill=(6, 8, 16, 235),
                    outline=(255, 215, 0, 145),
                    width=2
                )
                draw.text((W // 2 + 2, name_y + 2), name_text, font=font_name,
                          fill=(0, 0, 0, 170), anchor="mm")
                draw.text((W // 2, name_y), name_text, font=font_name,
                          fill=(255, 232, 95), anchor="mm")

                subtitle_text = (
                    f"{safe_text(card_position, 'ATHLETE').upper()}  ·  "
                    f"{safe_text(card_team, 'TEAM').upper()}  ·  "
                    f"#{safe_text(card_number, '0')}"
                )
                font_sub = fit_font(draw, subtitle_text, font_path,
                                    max_width=W - 130, start_size=29, min_size=16)
                sub_y = panel_top + 88
                draw.text((W // 2, sub_y), subtitle_text, font=font_sub,
                          fill=(226, 226, 238), anchor="mm")

                sep_y = panel_top + 117

                if stat_lines:
                    stats_y_val = sep_y + 58
                    stats_y_label = stats_y_val + 43
                    num_stats  = len(stat_lines)
                    left_margin  = 90
                    right_margin = 90
                    usable_w   = W - left_margin - right_margin
                    col_width  = usable_w // num_stats
                    box_h      = 88

                    for i, stat in enumerate(stat_lines):
                        x = left_margin + col_width * i + col_width // 2
                        parts = stat.split(":")
                        label = parts[0].strip().upper()
                        value = parts[1].strip() if len(parts) > 1 else stat

                        value_font = fit_font(draw, value, font_path,
                                             max_width=col_width - 26, start_size=38, min_size=19)
                        label_font = fit_font(draw, label, font_path,
                                             max_width=col_width - 20, start_size=19, min_size=11)

                        box_w  = col_width - 20
                        box_x1 = x - box_w // 2
                        box_y1 = stats_y_val - 38
                        box_x2 = x + box_w // 2
                        box_y2 = box_y1 + box_h

                        draw.rounded_rectangle(
                            [box_x1, box_y1, box_x2, box_y2],
                            radius=14,
                            fill=(14, 16, 34, 155),
                            outline=(255, 255, 255, 28),
                            width=1
                        )
                        draw.rounded_rectangle(
                            [box_x1 + 6, box_y1 + 5, box_x2 - 6, box_y1 + 11],
                            radius=8,
                            fill=(255, 255, 255, 20)
                        )
                        draw.text((x + 2, stats_y_val + 2), value, font=value_font,
                                  fill=(0, 0, 0, 140), anchor="mm")
                        draw.text((x, stats_y_val), value, font=value_font,
                                  fill=(255, 255, 255), anchor="mm")
                        draw.text((x, stats_y_label), label, font=label_font,
                                  fill=(184, 184, 215), anchor="mm")

                    if card_pro_match:
                        comp_text = f"PLAYS LIKE: {card_pro_match}"
                        comp_font = fit_font(
                            draw,
                            comp_text,
                            font_path,
                            max_width=W - 220,
                            start_size=20,
                            min_size=11
                        )

                        comp_y = sub_y + 34

                        draw.text(
                            (W // 2 + 1, comp_y + 1),
                            comp_text,
                            font=comp_font,
                            fill=(0, 0, 0, 170),
                            anchor="mm"
                        )

                        draw.text(
                            (W // 2, comp_y),
                            comp_text,
                            font=comp_font,
                            fill=(255, 215, 0),
                            anchor="mm"
                        )

                card_bg = add_subtle_noise(card_bg, opacity=14)
                card_bg = add_vignette(card_bg)
                draw = ImageDraw.Draw(card_bg)

                draw.rounded_rectangle([(12, 12), (W - 12, H - 12)],
                                       radius=36, outline=(255, 215, 0, 220), width=4)
                draw.rounded_rectangle([(24, 24), (W - 24, H - 24)],
                                       radius=28, outline=(255, 255, 255, 105), width=2)
                draw.rounded_rectangle([(38, 38), (W - 38, H - 38)],
                                       radius=20, outline=(0, 0, 0, 100), width=2)

                card_final = card_bg.convert("RGB")
                buf = BytesIO()
                card_final.save(buf, format="PNG")
                buf.seek(0)

                progress.progress(100)
                status.success("✅ Trading card complete!")

            st.subheader(f"🃏 {card_name}'s Trading Card")
            st.image(buf, width="stretch")
            st.download_button(
                "⬇️ Download Card",
                data=buf,
                file_name=f"{card_name}_card.png",
                mime="image/png"
            )
            st.success("Card generated!")


# ============================================================
# COACHES VIEW — REFORMED
# ============================================================
# HOW TO USE:
#   Replace everything from the line:
#       if page == "Coaches View":
#   all the way to the end of the file with this block.
#
# WHAT'S NEW:
#   - Persistent Roster: register players once, reuse forever
#   - Quick Game Entry: pick from roster dropdown, fill stats
#   - Team Game Entry: bulk-enter a full game for all players at once
#   - Dashboard: leaderboard, trends, win/loss record
#   - AI Team Report: whole-roster analysis, not just one player
#   - Player Comps & Depth Chart (unchanged logic, cleaner UI)
# ============================================================

if page == "Coaches View":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    # ── Header ──────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        border-radius: 16px;
        padding: 28px 32px 20px 32px;
        margin-bottom: 24px;
    ">
        <h1 style="color:#f0f9ff; margin:0; font-size:2rem; letter-spacing:-1px;">
            📋 Coaches Dashboard
        </h1>
        <p style="color:#93c5fd; margin:6px 0 0 0; font-size:1rem;">
            Build your roster once. Log every game in seconds. Let AI do the rest.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Constants & DB keys ─────────────────────────────────
    COACH_TABLE_KEY  = "coach_roster_games"
    ROSTER_TABLE_KEY = "coach_roster_players"
    coach_cols       = TABLES["coach_roster_games"]

    ROSTER_COLUMNS = ["Player", "Sport", "Position", "Jersey", "Notes"]

    SPORT_POSITIONS = {
        "Basketball":        ["PG", "SG", "SF", "PF", "C", "G", "Wing", "F"],
        "Baseball Hitting":  ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"],
        "Baseball Pitching": ["SP", "RP", "CL"],
        "Football":          ["QB", "RB", "FB", "WR", "TE",
                              "OT", "OG", "C",
                              "DE", "DT", "LB", "CB", "S", "K", "P"],
    }

    FB_SKILL  = {"QB"}
    FB_RB     = {"RB", "FB"}
    FB_WRTE   = {"WR", "TE"}
    FB_LINE_O = {"OT", "OG", "C"}
    FB_DEF    = {"DE", "DT", "LB", "CB", "S"}
    FB_SPEC   = {"K", "P"}

    def fb_stat_group(pos):
        if pos in FB_SKILL:   return "QB"
        if pos in FB_RB:      return "RB"
        if pos in FB_WRTE:    return "WRTE"
        if pos in FB_LINE_O:  return "OL"
        if pos in FB_DEF:     return "DEF"
        if pos in FB_SPEC:    return "SPEC"
        return "DEF"

    # ── Session state init ───────────────────────────────────
    if COACH_TABLE_KEY not in st.session_state:
        st.session_state[COACH_TABLE_KEY] = load_from_db(COACH_TABLE_KEY, coach_cols)

    if ROSTER_TABLE_KEY not in st.session_state:
        st.session_state[ROSTER_TABLE_KEY] = load_from_db(ROSTER_TABLE_KEY, ROSTER_COLUMNS)

    # ── Helper: clean game df ────────────────────────────────
    def clean_coach_df(df):
        df = df.copy()
        for col in coach_cols:
            if col not in df.columns:
                df[col] = pd.NA
        df = df[coach_cols]
        if len(df) > 0:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            text_cols = ["Sport", "Player", "Position", "Opponent", "Result"]
            for col in text_cols:
                df[col] = df[col].fillna("").astype(str)
            numeric_cols = [c for c in df.columns if c not in text_cols + ["Date"]]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df

    # ── Helper: roster lookup ────────────────────────────────
    def get_roster_df():
        df = st.session_state[ROSTER_TABLE_KEY].copy()
        for col in ROSTER_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[ROSTER_COLUMNS]

    def roster_players_for_sport(sport_name):
        df = get_roster_df()
        if len(df) == 0:
            return []
        filtered = df[df["Sport"] == sport_name]["Player"].dropna().unique().tolist()
        return sorted(filtered)

    def get_player_position(player_name):
        df = get_roster_df()
        row = df[df["Player"] == player_name]
        if len(row) == 0:
            return ""
        return str(row.iloc[0].get("Position", ""))

    # ── Helper: coach summary ────────────────────────────────
    def coach_summary(df):
        df = clean_coach_df(df)
        if len(df) == 0:
            return pd.DataFrame()
        rows = []
        for (sport_name, player, pos), g in df.groupby(["Sport", "Player", "Position"]):
            games = len(g)
            wins  = (g["Result"].str.upper() == "W").sum() if "Result" in g.columns else 0
            losses= (g["Result"].str.upper() == "L").sum() if "Result" in g.columns else 0
            row   = {"Sport": sport_name, "Player": player, "Position": pos,
                     "Games": games, "W": int(wins), "L": int(losses)}

            if sport_name == "Basketball":
                row.update({
                    "PTS/G": g["Points"].mean(), "REB/G": g["Rebounds"].mean(),
                    "AST/G": g["Assists"].mean(), "STL/G": g["Steals"].mean(),
                    "BLK/G": g["Blocks"].mean(),  "TOV/G": g["Turnovers"].mean(),
                    "Impact Score": (
                        g["Points"].mean() + 1.2*g["Rebounds"].mean()
                        + 1.5*g["Assists"].mean() + 2*g["Steals"].mean()
                        + 2*g["Blocks"].mean() - g["Turnovers"].mean()
                    )
                })
            elif sport_name == "Baseball Hitting":
                ab = g["At Bats"].sum(); hits = g["Hits"].sum(); walks = g["Walks"].sum()
                doubles = g["Doubles"].sum(); triples = g["Triples"].sum(); hr = g["Home Runs"].sum()
                singles = max(hits - doubles - triples - hr, 0)
                total_bases = singles + 2*doubles + 3*triples + 4*hr
                avg = hits/ab if ab > 0 else 0
                obp = (hits+walks)/(ab+walks) if (ab+walks) > 0 else 0
                slg = total_bases/ab if ab > 0 else 0
                row.update({
                    "AVG": avg, "OBP": obp, "SLG": slg, "OPS": obp+slg,
                    "HR": hr, "RBI": g["RBIs"].sum(), "SB": g["Stolen Bases"].sum(),
                    "Impact Score": (obp+slg)*100 + 2*hr + 0.5*g["RBIs"].sum() + 0.75*g["Stolen Bases"].sum()
                })
            elif sport_name == "Baseball Pitching":
                ip = g["Innings Pitched"].sum(); er = g["Earned Runs"].sum()
                k  = g["Strikeouts"].sum();      bb = g["Walks"].sum(); ha = g["Hits Allowed"].sum()
                era  = er/ip*9 if ip > 0 else 0
                whip = (bb+ha)/ip if ip > 0 else 0
                row.update({
                    "IP": ip, "ERA": era, "WHIP": whip,
                    "K/9": k/ip*9 if ip > 0 else 0,
                    "BB/9": bb/ip*9 if ip > 0 else 0,
                    "Impact Score": (k/ip*9 if ip > 0 else 0)*8 - era*4 - whip*10
                })
            elif sport_name == "Football":
                if pos == "QB":
                    row.update({
                        "Pass Yds/G": g["Passing Yards"].mean(),
                        "Pass TD/G":  g["Passing TDs"].mean(),
                        "INT/G":      g["Interceptions"].mean(),
                        "Rush Yds/G": g["Rushing Yards"].mean(),
                        "Cmp %": g["Completions"].sum()/g["Attempts"].sum()*100 if g["Attempts"].sum() > 0 else 0,
                        "Impact Score": (
                            g["Passing Yards"].mean()/10 + 6*g["Passing TDs"].mean()
                            - 4*g["Interceptions"].mean() + g["Rushing Yards"].mean()/10
                            + 6*g["Rushing TDs"].mean()
                        )
                    })
                elif pos == "RB":
                    row.update({
                        "Rush Yds/G": g["Rushing Yards"].mean(),
                        "Rush TD/G":  g["Rushing TDs"].mean(),
                        "Rec/G":      g["Receptions"].mean(),
                        "Rec Yds/G":  g["Receiving Yards"].mean(),
                        "Impact Score": (
                            g["Rushing Yards"].mean()/10 + g["Receiving Yards"].mean()/10
                            + 6*g["Rushing TDs"].mean() + 6*g["Receiving TDs"].mean()
                        )
                    })
                elif pos in ["WR", "TE", "WR/TE"]:
                    catch_pct = g["Receptions"].sum()/g["Targets"].sum()*100 if g["Targets"].sum() > 0 else 0
                    row.update({
                        "Targets/G": g["Targets"].mean(), "Rec/G": g["Receptions"].mean(),
                        "Rec Yds/G": g["Receiving Yards"].mean(),
                        "Rec TD/G":  g["Receiving TDs"].mean(), "Catch %": catch_pct,
                        "Impact Score": g["Receiving Yards"].mean()/10 + 6*g["Receiving TDs"].mean() + catch_pct*8
                    })
                else:
                    row.update({
                        "Tackles/G": g["Tackles"].mean(), "Sacks/G": g["Sacks"].mean(),
                        "INT/G":     g["Interceptions"].mean(), "PD/G": g["Passes Defended"].mean(),
                        "FF/G":      g["Forced Fumbles"].mean(),
                        "Impact Score": (
                            g["Tackles"].mean() + 4*g["Sacks"].mean()
                            + 5*g["Interceptions"].mean() + 2*g["Passes Defended"].mean()
                            + 4*g["Forced Fumbles"].mean()
                        )
                    })
            rows.append(row)

        out = pd.DataFrame(rows).fillna(0)
        num_cols = out.select_dtypes(include="number").columns
        out[num_cols] = out[num_cols].round(3)
        return out.sort_values("Impact Score", ascending=False).reset_index(drop=True)

    def find_coach_player_comp(profile, nba_season="2025-26", mlb_year=2025, nfl_season=2025):
        try:
            sport_name = profile["Sport"]
            pos        = profile["Position"]
            if sport_name == "Basketball":
                pros = load_player_data(nba_season)
                pros = pros[(pros["GP"] >= 20) & (pros["MIN"] >= 10)].copy()
                pros["DISTANCE"] = (
                    ((pros["PTS"] - profile.get("PTS/G", 0)) / 6) ** 2 +
                    ((pros["REB"] - profile.get("REB/G", 0)) / 3) ** 2 +
                    ((pros["AST"] - profile.get("AST/G", 0)) / 3) ** 2 +
                    ((pros["STL"] - profile.get("STL/G", 0)) / 1) ** 2 +
                    ((pros["BLK"] - profile.get("BLK/G", 0)) / 1) ** 2 +
                    ((pros["TOV"] - profile.get("TOV/G", 0)) / 2) ** 2
                ) ** 0.5
                pros["Similarity Score"] = (1/(1+pros["DISTANCE"])).round(3)
                return pros.sort_values("DISTANCE").head(5)[
                    ["PLAYER_NAME","TEAM_ABBREVIATION","PTS","REB","AST","Similarity Score"]
                ].rename(columns={"PLAYER_NAME":"Comp","TEAM_ABBREVIATION":"Team"})
            if sport_name == "Baseball Hitting":
                pros = load_mlb_batting_data(mlb_year).copy()
                pros["DISTANCE"] = (
                    ((pros["AVG"]-profile.get("AVG",0))/.035)**2 +
                    ((pros["OBP"]-profile.get("OBP",0))/.045)**2 +
                    ((pros["SLG"]-profile.get("SLG",0))/.070)**2 +
                    ((pros["OPS"]-profile.get("OPS",0))/.100)**2
                ) ** 0.5
                pros["Similarity Score"] = (1/(1+pros["DISTANCE"])).round(3)
                return pros.sort_values("DISTANCE").head(5)[
                    ["Name","Team","AVG","OBP","SLG","OPS","Similarity Score"]
                ].rename(columns={"Name":"Comp"})
            if sport_name == "Baseball Pitching":
                pros = load_mlb_pitching_data(mlb_year).copy()
                pros["DISTANCE"] = (
                    ((pros["ERA"]-profile.get("ERA",0))/1.0)**2 +
                    ((pros["WHIP"]-profile.get("WHIP",0))/.25)**2 +
                    ((pros["K_PER_9"]-profile.get("K/9",0))/2.5)**2 +
                    ((pros["BB_PER_9"]-profile.get("BB/9",0))/1.5)**2
                ) ** 0.5
                pros["Similarity Score"] = (1/(1+pros["DISTANCE"])).round(3)
                return pros.sort_values("DISTANCE").head(5)[
                    ["Name","Team","ERA","WHIP","K_PER_9","BB_PER_9","Similarity Score"]
                ].rename(columns={"Name":"Comp"})
            if sport_name == "Football":
                pros = load_nfl_player_data(nfl_season).copy()
                if pos == "QB":
                    pros = pros[pros["position"]=="QB"].copy()
                    pros["DISTANCE"] = (
                        ((pros["passing_yards"]/pros["games"]-profile.get("Pass Yds/G",0))/45)**2 +
                        ((pros["passing_tds"]/pros["games"]-profile.get("Pass TD/G",0))/.9)**2 +
                        ((pros["passing_interceptions"]/pros["games"]-profile.get("INT/G",0))/.6)**2
                    ) ** 0.5
                elif pos == "RB":
                    pros = pros[pros["position"]=="RB"].copy()
                    pros["DISTANCE"] = (
                        ((pros["rushing_yards"]/pros["games"]-profile.get("Rush Yds/G",0))/20)**2 +
                        ((pros["rushing_tds"]/pros["games"]-profile.get("Rush TD/G",0))/.5)**2 +
                        ((pros["receiving_yards"]/pros["games"]-profile.get("Rec Yds/G",0))/18)**2
                    ) ** 0.5
                elif pos in ["WR","TE","WR/TE"]:
                    pros = pros[pros["position"].isin(["WR","TE"])].copy()
                    pros["DISTANCE"] = (
                        ((pros["targets"]/pros["games"]-profile.get("Targets/G",0))/2.5)**2 +
                        ((pros["receptions"]/pros["games"]-profile.get("Rec/G",0))/2)**2 +
                        ((pros["receiving_yards"]/pros["games"]-profile.get("Rec Yds/G",0))/20)**2
                    ) ** 0.5
                else:
                    pros = pros[pros["position"].isin(["LB","ILB","OLB","MLB","CB","S","SS","FS","DB","DE","DT","DL","EDGE","SAF","NT"])].copy()
                    pros["DISTANCE"] = (
                        ((pros["def_tackles_solo"]/pros["games"]-profile.get("Tackles/G",0))/2.5)**2 +
                        ((pros["def_sacks"]/pros["games"]-profile.get("Sacks/G",0))/.5)**2 +
                        ((pros["def_interceptions"]/pros["games"]-profile.get("INT/G",0))/.3)**2
                    ) ** 0.5
                pros = pros[pros["games"]>0].copy()
                pros["Similarity Score"] = (1/(1+pros["DISTANCE"])).round(3)
                return pros.sort_values("DISTANCE").head(5)[
                    ["player_name","team","position","games","Similarity Score"]
                ].rename(columns={"player_name":"Comp","team":"Team","position":"Position"})
        except Exception as e:
            st.warning(f"Could not load pro comps: {e}")
        return pd.DataFrame()

    # ── TABS ─────────────────────────────────────────────────
    roster_tab, log_tab, dashboard_tab, comps_tab, depth_tab = st.tabs([
        "👥 Roster",
        "➕ Log Game",
        "📊 Dashboard",
        "🧬 Comps",
        "🧩 Depth Chart",
    ])

    # ════════════════════════════════════════════════════════
    # TAB 1 — ROSTER BUILDER
    # ════════════════════════════════════════════════════════
    with roster_tab:
        st.subheader("Your Roster")
        st.caption("Add players here once. They'll appear as dropdowns everywhere else.")

        roster_df = get_roster_df()

        # ── Add player form ──────────────────────────────────
        with st.expander("➕ Add a New Player", expanded=len(roster_df) == 0):
            with st.form("add_roster_player"):
                rc1, rc2, rc3, rc4 = st.columns(4)
                with rc1:
                    r_name    = st.text_input("Player Name")
                with rc2:
                    r_sport   = st.selectbox("Sport", list(SPORT_POSITIONS.keys()))
                with rc3:
                    r_pos     = st.selectbox("Position", SPORT_POSITIONS[list(SPORT_POSITIONS.keys())[0]])
                with rc4:
                    r_jersey  = st.text_input("Jersey #", value="")
                r_notes = st.text_input("Notes (optional)", placeholder="e.g. Captain, injured left knee")

                if st.form_submit_button("Add to Roster"):
                    # Update position options based on selected sport
                    if r_name.strip() == "":
                        st.error("Enter a player name.")
                    else:
                        new_player = pd.DataFrame([{
                            "Player": r_name.strip(),
                            "Sport":  r_sport,
                            "Position": r_pos,
                            "Jersey": r_jersey,
                            "Notes":  r_notes,
                        }])
                        existing = get_roster_df()
                        # Avoid exact duplicates
                        if ((existing["Player"] == r_name.strip()) & (existing["Sport"] == r_sport)).any():
                            st.warning(f"{r_name} is already on the {r_sport} roster.")
                        else:
                            st.session_state[ROSTER_TABLE_KEY] = pd.concat(
                                [existing, new_player], ignore_index=True
                            )
                            save_to_db(ROSTER_TABLE_KEY, st.session_state[ROSTER_TABLE_KEY])
                            st.success(f"Added {r_name} to roster.")
                            st.rerun()

        # ── Roster table ─────────────────────────────────────
        roster_df = get_roster_df()
        if len(roster_df) == 0:
            st.info("No players yet. Add your first player above.")
        else:
            # Show by sport
            for sport_name, group in roster_df.groupby("Sport"):
                st.markdown(f"#### {sport_name} — {len(group)} player{'s' if len(group)!=1 else ''}")

                # Styled roster cards
                cols = st.columns(min(4, len(group)))
                for i, (_, p) in enumerate(group.reset_index(drop=True).iterrows()):
                    with cols[i % len(cols)]:
                        jersey_display = f"#{p['Jersey']}" if str(p.get("Jersey","")).strip() else ""
                        notes_display  = f"<br><small style='color:#888;'>{p['Notes']}</small>" if str(p.get("Notes","")).strip() else ""
                        st.markdown(f"""
                        <div style="
                            border:1px solid #e2e8f0;
                            border-radius:12px;
                            padding:12px 14px;
                            margin-bottom:8px;
                            background:#f8fafc;
                        ">
                            <b style="font-size:15px;">{p['Player']}</b>
                            <span style="float:right;color:#64748b;font-size:13px;">{jersey_display}</span><br>
                            <span style="
                                background:#dbeafe;color:#1d4ed8;
                                border-radius:6px;padding:2px 8px;
                                font-size:12px;font-weight:600;
                            ">{p['Position']}</span>
                            {notes_display}
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("Edit or Remove Players")

            editable = roster_df.copy()
            edited_roster = st.data_editor(
                editable,
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="roster_editor",
            )
            if st.button("💾 Save Roster Changes"):
                st.session_state[ROSTER_TABLE_KEY] = edited_roster.dropna(subset=["Player"])
                save_to_db(ROSTER_TABLE_KEY, st.session_state[ROSTER_TABLE_KEY])
                st.success("Roster saved.")
                st.rerun()

    # ════════════════════════════════════════════════════════
    # TAB — TEAM GAME (bulk entry for a whole game at once)
    # ════════════════════════════════════════════════════════
    with log_tab:
        st.subheader("➕ Log Game")
        st.caption("Log a full game for multiple players at once. Players pre-filled from your roster.")

        if "team_game_save_confirmation" in st.session_state:
            conf = st.session_state.pop("team_game_save_confirmation")
            st.success(f"✅ Saved {conf['count']} player lines — {conf['sport']} vs {conf['opponent']} on {conf['date']}.")

        roster_df = get_roster_df()
        if len(roster_df) == 0:
            st.warning("Add players to your Roster first.")
        else:
            tg_sport = st.selectbox("Sport", list(SPORT_POSITIONS.keys()), key="tg_sport")
            sport_players_tg = roster_players_for_sport(tg_sport)

            gi1,gi2,gi3 = st.columns(3)
            with gi1: tg_date   = st.date_input("Game Date", key="tg_date")
            with gi2: tg_opp    = st.text_input("Opponent",  key="tg_opp")
            with gi3: tg_result = st.selectbox("Result", ["","W","L","T","ND"], key="tg_result")
            gs1,gs2 = st.columns(2)
            with gs1: tg_team_score = st.number_input("Team Score", min_value=0, step=1, key="tg_tscore")
            with gs2: tg_opp_score  = st.number_input("Opp Score",  min_value=0, step=1, key="tg_oscore")

            if not sport_players_tg:
                st.info(f"No {tg_sport} players on your roster yet.")
            else:
                st.markdown("---")
                st.markdown("**Enter stats for each player. Leave at 0 to skip.**")

                # Build stat columns per sport
                SPORT_STAT_COLS = {
                    "Basketball":        ["Points","Rebounds","Assists","Steals","Blocks","Turnovers"],
                    "Baseball Hitting":  ["At Bats","Hits","Runs","RBIs","Walks","Strikeouts","Doubles","Triples","Home Runs","Stolen Bases"],
                    "Baseball Pitching": ["Innings Pitched","Strikeouts","Walks","Hits Allowed","Earned Runs","Home Runs Allowed","Pitches Thrown"],
                    "Football":          ["Completions","Attempts","Passing Yards","Passing TDs","Interceptions",
                                          "Carries","Rushing Yards","Rushing TDs",
                                          "Targets","Receptions","Receiving Yards","Receiving TDs",
                                          "Tackles","Assists_FB","Sacks","Passes Defended","Forced Fumbles","Fumble Recoveries"],
                }
                stat_cols = SPORT_STAT_COLS.get(tg_sport, [])

                # Build prefilled df from roster
                prefilled_rows = []
                for pname in sport_players_tg:
                    row = {"Player": pname, "Position": get_player_position(pname)}
                    for sc in stat_cols:
                        row[sc] = 0
                    prefilled_rows.append(row)
                prefilled_df = pd.DataFrame(prefilled_rows)

                tg_editor = st.data_editor(
                    prefilled_df,
                    use_container_width=True,
                    hide_index=True,
                    num_rows="fixed",
                    disabled=["Player","Position"],
                    key="team_game_editor",
                )

                st.divider()
                if st.button("💾 Save Team Game", use_container_width=True):
                    if tg_opp.strip() == "":
                        st.error("Enter an opponent.")
                    else:
                        rows_to_add = []
                        for _, row in tg_editor.iterrows():
                            player_name = str(row.get("Player","")).strip()
                            if not player_name:
                                continue
                            new_row = {col: 0 for col in coach_cols}
                            new_row.update({
                                "Sport": tg_sport, "Player": player_name,
                                "Position": row.get("Position",""),
                                "Date": pd.to_datetime(tg_date), "Opponent": tg_opp,
                                "Team Score": tg_team_score, "Opponent Score": tg_opp_score,
                                "Result": tg_result,
                            })
                            for sc in stat_cols:
                                new_row[sc] = pd.to_numeric(row.get(sc, 0), errors="coerce") or 0
                            rows_to_add.append(new_row)

                        if rows_to_add:
                            st.session_state[COACH_TABLE_KEY] = pd.concat(
                                [st.session_state[COACH_TABLE_KEY], pd.DataFrame(rows_to_add)],
                                ignore_index=True,
                            )
                            save_to_db(COACH_TABLE_KEY, st.session_state[COACH_TABLE_KEY])
                            st.session_state["team_game_save_confirmation"] = {
                                "sport": tg_sport, "opponent": tg_opp,
                                "date": str(tg_date), "count": len(rows_to_add)
                            }
                            st.rerun()

    # ════════════════════════════════════════════════════════
    # TAB — DASHBOARD
    # ════════════════════════════════════════════════════════
    with dashboard_tab:
        coach_df = clean_coach_df(st.session_state[COACH_TABLE_KEY])
        if len(coach_df) == 0:
            st.info("No game data yet. Log some games first.")
        else:
            summary = coach_summary(coach_df)

            # ── Top-line metrics ─────────────────────────────
            k1,k2,k3,k4,k5 = st.columns(5)
            with k1: st.metric("Roster Size",      summary["Player"].nunique())
            with k2: st.metric("Games Logged",     len(coach_df))
            with k3: st.metric("Sports",           coach_df["Sport"].nunique())
            with k4:
                total_w = (coach_df["Result"].str.upper() == "W").sum()
                total_l = (coach_df["Result"].str.upper() == "L").sum()
                st.metric("Team W",  int(total_w))
            with k5:
                st.metric("Team L",  int(total_l))

            st.markdown("---")

            # ── Leaderboard ──────────────────────────────────
            st.subheader("🏆 Roster Leaderboard")
            sport_filter = st.selectbox(
                "Filter by sport",
                ["All"] + sorted(coach_df["Sport"].unique().tolist()),
                key="dash_sport_filter"
            )
            filtered_summary = summary if sport_filter == "All" else summary[summary["Sport"]==sport_filter]
            st.dataframe(filtered_summary, use_container_width=True, hide_index=True)

            st.download_button(
                "⬇️ Download Leaderboard CSV",
                data=filtered_summary.to_csv(index=False).encode("utf-8"),
                file_name="roster_leaderboard.csv", mime="text/csv",
            )

            leaders = filtered_summary.sort_values("Impact Score", ascending=False).head(12)
            fig = px.bar(leaders, x="Impact Score", y="Player", color="Sport",
                         orientation="h", title="Top Players by Impact Score",
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(yaxis=dict(autorange="reversed"), plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

            # ── Player trend explorer ────────────────────────
            st.markdown("---")
            st.subheader("📈 Player Trend Explorer")
            all_players = sorted(coach_df["Player"].unique())
            trend_player = st.selectbox("Player", all_players, key="dash_trend_player")
            player_games = coach_df[coach_df["Player"]==trend_player].sort_values("Date")
            possible_stats = [
                c for c in player_games.select_dtypes(include="number").columns
                if player_games[c].sum() != 0 and c not in ["Team Score","Opponent Score"]
            ]
            if possible_stats:
                trend_stat = st.selectbox("Stat", possible_stats, key="dash_trend_stat")
                trend_fig  = px.line(player_games, x="Date", y=trend_stat, markers=True,
                                     hover_data=["Opponent","Sport","Position"],
                                     title=f"{trend_player} — {trend_stat} Over Time")
                st.plotly_chart(trend_fig, use_container_width=True)

            # ── AI Team Report ───────────────────────────────
            st.markdown("---")
            st.subheader("🤖 AI Team Report")
            st.caption("Claude analyzes your whole roster and gives you a coaching breakdown.")

            ai_sport_filter = st.selectbox(
                "Generate report for sport",
                sorted(coach_df["Sport"].unique().tolist()),
                key="ai_team_sport"
            )

            if st.button("Generate AI Team Report", use_container_width=True):
                ai_summary = summary[summary["Sport"]==ai_sport_filter].copy()
                if len(ai_summary) == 0:
                    st.warning("No data for that sport.")
                else:
                    summary_text = ai_summary.to_string(index=False)
                    prompt = f"""You are an elite {ai_sport_filter} coach analyzing your full roster after reviewing season stats.

ROSTER SUMMARY:
{summary_text}

Write a sharp, honest team scouting report with these sections:

## 🌟 Team Strengths
What does this roster do well collectively? Back it with specific player names and numbers.

## ⚠️ Team Weaknesses
Where is the roster thin or underperforming? Be specific and honest.

## 🏆 Top 3 Players to Build Around
Name them, explain why using their stats, and describe the role each should play.

## 📋 Depth Concerns
Which positions or roles have no reliable backup? What's the biggest roster vulnerability?

## 🎯 This Season's Priority
One clear directive for the coaching staff — what should you focus on most to win more games?

Keep it under 400 words. Sound like a real coach, not a chatbot. Use player names and actual numbers."""

                    with st.spinner("Generating team report..."):
                        try:
                            import anthropic as _anthropic
                            client = _anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_KEY"])
                            report_text = ""
                            placeholder = st.empty()
                            with client.messages.stream(
                                model="claude-sonnet-4-6",
                                max_tokens=800,
                                messages=[{"role":"user","content":prompt}],
                            ) as stream:
                                for text in stream.text_stream:
                                    report_text += text
                                    placeholder.markdown(report_text)

                            st.download_button(
                                "📋 Download Team Report",
                                data=report_text,
                                file_name=f"team_report_{ai_sport_filter.lower().replace(' ','_')}.txt",
                                mime="text/plain",
                            )
                        except Exception as e:
                            st.error(f"Could not generate report: {e}")

    # ════════════════════════════════════════════════════════
    # TAB — PLAYER COMPS
    # ════════════════════════════════════════════════════════
    with comps_tab:
        coach_df = clean_coach_df(st.session_state[COACH_TABLE_KEY])
        summary  = coach_summary(coach_df)
        if len(summary) == 0:
            st.info("No roster data yet.")
        else:
            st.subheader("🧬 Player Comps")
            selected_player = st.selectbox("Choose player", summary["Player"].tolist(), key="comp_player")
            profile = summary[summary["Player"]==selected_player]
            if len(profile) > 0:
                profile = profile.iloc[0]
                p1,p2,p3 = st.columns(3)
                with p1: st.metric("Sport",        profile["Sport"])
                with p2: st.metric("Position",     profile["Position"])
                with p3: st.metric("Impact Score", round(profile.get("Impact Score",0),2))

                season_selectors = {}
                if profile["Sport"] == "Basketball":
                    season_selectors["nba"] = st.selectbox("NBA season",["2022-23","2023-24","2024-25","2025-26"],index=3,key="comp_nba")
                elif profile["Sport"] in ["Baseball Hitting","Baseball Pitching"]:
                    season_selectors["mlb"] = st.selectbox("MLB year",[2023,2024,2025],index=2,key="comp_mlb")
                elif profile["Sport"] == "Football":
                    season_selectors["nfl"] = st.selectbox("NFL season",[2023,2024,2025],index=2,key="comp_nfl")

                comps = find_coach_player_comp(
                    profile,
                    nba_season=season_selectors.get("nba","2025-26"),
                    mlb_year=season_selectors.get("mlb",2025),
                    nfl_season=season_selectors.get("nfl",2025),
                )
                if len(comps) > 0:
                    st.dataframe(comps, hide_index=True, use_container_width=True)
                    comp_fig = px.bar(comps, x="Similarity Score", y="Comp", orientation="h",
                                      title=f"Top Comps for {selected_player}")
                    comp_fig.update_layout(yaxis=dict(autorange="reversed"))
                    st.plotly_chart(comp_fig, use_container_width=True)

                # Individual AI scouting report
                render_coach_roster_ai_report(
                    profile["Sport"], selected_player,
                    coach_df[coach_df["Player"]==selected_player]
                )

    # ════════════════════════════════════════════════════════
    # TAB — DEPTH CHART
    # ════════════════════════════════════════════════════════
    with depth_tab:
        coach_df = clean_coach_df(st.session_state[COACH_TABLE_KEY])
        summary  = coach_summary(coach_df)

        if len(summary) == 0:
            st.info("No roster data yet.")
        else:
            st.subheader("🧩 Depth Chart")
            st.caption("Ranked by Impact Score within each position.")

            depth_sport = st.selectbox("Sport", sorted(summary["Sport"].unique()), key="depth_sport")
            depth_summary = summary[summary["Sport"]==depth_sport].copy()

            if profile["Sport"] == "Basketball":
                depth_nba = st.selectbox("NBA season",["2022-23","2023-24","2024-25","2025-26"],index=3,key="depth_nba")
            else:
                depth_nba = "2025-26"
            depth_mlb = 2025
            depth_nfl = 2025

            position_order = {
                "Basketball":        ["PG","SG","SF","PF","C","G","Wing","F"],
                "Baseball Hitting":  ["C","1B","2B","3B","SS","LF","CF","RF","DH"],
                "Baseball Pitching": ["SP","RP","CL"],
                "Football":          ["QB","RB","FB","WR","TE","OT","OG","C","DE","DT","LB","CB","S","K","P"],
            }
            ordered = [p for p in position_order.get(depth_sport,[]) if p in depth_summary["Position"].unique()]
            extras  = sorted([p for p in depth_summary["Position"].unique() if p not in ordered])

            for pos in ordered + extras:
                pos_players = (
                    depth_summary[depth_summary["Position"]==pos]
                    .sort_values("Impact Score", ascending=False)
                    .reset_index(drop=True)
                )
                st.markdown(f"### {pos}")
                card_cols = st.columns(min(3, max(1, len(pos_players))))

                for i, (_, player_row) in enumerate(pos_players.iterrows()):
                    with card_cols[i % len(card_cols)]:
                        try:
                            comps    = find_coach_player_comp(player_row, depth_nba, depth_mlb, depth_nfl)
                            top_comp = comps.iloc[0]["Comp"] if len(comps) > 0 else "—"
                        except:
                            top_comp = "—"

                        rank_color = ["#f59e0b","#94a3b8","#cd7c3a"][min(i,2)]
                        st.markdown(f"""
                        <div style="
                            border:2px solid {rank_color};
                            border-radius:14px;
                            padding:16px;
                            margin-bottom:10px;
                            background:#fafafa;
                        ">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <span style="
                                    background:{rank_color};color:white;
                                    border-radius:50%;width:28px;height:28px;
                                    display:inline-flex;align-items:center;justify-content:center;
                                    font-weight:700;font-size:13px;
                                ">#{i+1}</span>
                                <span style="font-size:13px;color:#64748b;">
                                    Impact: <b>{round(player_row['Impact Score'],1)}</b>
                                </span>
                            </div>
                            <h4 style="margin:8px 0 2px 0;">{player_row["Player"]}</h4>
                            <span style="
                                background:#dbeafe;color:#1d4ed8;
                                border-radius:6px;padding:2px 8px;
                                font-size:12px;font-weight:600;
                            ">{player_row["Position"]}</span>
                            <p style="margin:8px 0 0 0;font-size:13px;color:#475569;">
                                <b>Comp:</b> {top_comp}<br>
                                <b>Games:</b> {int(player_row["Games"])} &nbsp;
                                <b>W/L:</b> {int(player_row.get("W",0))}/{int(player_row.get("L",0))}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)