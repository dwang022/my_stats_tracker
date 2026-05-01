# NBA CHAMPION + MVP PREDICTOR

import streamlit as st # build app (tell student: this is what creates the website)
import pandas as pd # work with tables (like Excel in Python)
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashplayerstats # NBA stats (real data!)
import plotly.express as px # for better charts
from pybaseball import batting_stats_range

# NEW
import nflreadpy as nfl
# uv pip install nflreadpy


# -----------------------------------
# PAGE SETUP
# -----------------------------------

# # Set the page title and make the app wide
st.set_page_config(page_title="NBA Predictor", layout="wide")



# ----------- ADD THIS ----------------------
# PAGE NAVIGATION

# page = st.sidebar.radio(
#     "Go to page",
#     ["NBA Predictor", "My Stats Tracker"]
# )

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "sport" not in st.session_state:
    st.session_state.sport = "Basketball"

page = st.session_state.page

if page == "My Stats Tracker":
    sport = st.sidebar.radio(
        "Choose a sport",
        ["Basketball", "Baseball", "Football"] # NEW: add football
    )

# ------------------------------------------------




# -----------------------------------
# CHOOSE A SEASON
# -----------------------------------

# Teach: widgets create variables!
# This dropdown lets the user pick a season
season = st.selectbox(
    "Choose a season",
    ["2022-23", "2023-24", "2024-25", "2025-26"],
    index=3  # default is most recent
)


# -----------------------------------
# LOAD TEAM DATA
# -----------------------------------

# Teach: functions help organize code
# Teach: caching makes the app faster
@st.cache_data
def load_team_data(season):
    
    # Pull basic team stats (wins, points, etc.)
    team_base = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base"
    ).get_data_frames()[0]

    # Pull advanced stats (ratings)
    team_advanced = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced"
    ).get_data_frames()[0]

    # Keep only important columns (simplify data)
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

    # Merge = join tables together
    team_data = pd.merge(team_base, team_advanced, on="TEAM_ID", how="inner")

    return team_data




# -----------------------------------
# LOAD PLAYER DATA
# -----------------------------------

@st.cache_data
def load_player_data(season):
    
    # Base stats (box score stats)
    player_base = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Base"
    ).get_data_frames()[0]

    # Advanced stats (efficiency + impact)
    player_advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        per_mode_detailed="PerGame",
        measure_type_detailed_defense="Advanced"
    ).get_data_frames()[0]

    # Keep important columns only
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
            "PIE" # explain: overall impact stat
        ]
    ]

    # Merge base + advanced stats
    player_data = pd.merge(player_base, player_advanced, on="PLAYER_ID", how="inner")

    return player_data




# -----------------------------------
# LOAD THE DATA
# -----------------------------------

# Teach: calling functions runs them
teams = load_team_data(season)
players = load_player_data(season)


# -----------------------------------
# CLEAN THE DATA
# -----------------------------------

# Teach: filter data (like Excel filters)

# Remove players with low sample size
players = players[players["GP"] >= 40]

# Remove players who don’t play much
players = players[players["MIN"] >= 20]

# Reset index so tables look clean
players = players.reset_index(drop=True)
teams = teams.reset_index(drop=True)

# Round numbers so they look nicer
teams["W_PCT"] = teams["W_PCT"].round(3)
teams["OFF_RATING"] = teams["OFF_RATING"].round(2)
teams["DEF_RATING"] = teams["DEF_RATING"].round(2)
teams["NET_RATING"] = teams["NET_RATING"].round(2)
players["W_PCT"] = players["W_PCT"].round(3)
players["TS_PCT"] = players["TS_PCT"].round(3)


# -----------------------------------
# MAKE AN MVP SCORE
# -----------------------------------

# Teach: we are building a simple model
# Explain each term as you go!

players["MVP_SCORE"] = (
    players["PTS"] * 1.3 +      # scoring
    players["AST"] * 1.8 +      # playmaking
    players["REB"] * 0.8 +      # rebounding
    players["STL"] * 1.5 +      # defense
    players["BLK"] * 2.0 +      # defense
    players["TOV"] * -1.3 +     # turnovers are bad
    players["TS_PCT"] * 40 +    # efficiency
    players["W_PCT"] * 60 +     # team success
    players["PIE"] * 80         # overall impact
)

# Round scores
players["MVP_SCORE"] = players["MVP_SCORE"].round(2)

# Sort players from best to worst
players_ranked = players.sort_values("MVP_SCORE", ascending=False).reset_index(drop=True)



# -----------------------------------
# MAKE A CHAMPION SCORE
# -----------------------------------

# Teach: similar idea but for teams

teams["CHAMPION_SCORE"] = (
    teams["W_PCT"] * 60 +        # winning matters most
    teams["NET_RATING"] * 12 +   # dominance
    teams["OFF_RATING"] * 1.2 +  # offense
    teams["DEF_RATING"] * -1.5   # lower defense is better
)

teams["CHAMPION_SCORE"] = teams["CHAMPION_SCORE"].round(2)

# Rank teams
teams_ranked = teams.sort_values("CHAMPION_SCORE", ascending=False).reset_index(drop=True)



if page == "Home":
    st.title("My Sports Tracker")
    st.write("Choose a page or sport to start tracking your performance.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 NBA Predictor")
        st.write("See the predicted NBA champion and MVP using real NBA data.")
        if st.button("Go to NBA Predictor", use_container_width=True):
            st.session_state.page = "NBA Predictor"
            st.rerun()

    with col2:
        st.subheader("STATS Tracker")
        st.write("Track points, rebounds, assists, and compare to NBA players.")
        if st.button("Go to Basketball Tracker", use_container_width=True):
            st.session_state.page = "My Stats Tracker"
            st.session_state.sport = "Basketball"
            st.rerun()



# -------------------------- ADD THE PAGE & MOVE TITLE INSIDE ------------------------
if page == "NBA Predictor":
    
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()
    
    # Main title (first thing users see)
    st.title("NBA Champion + MVP Predictor")
    
    # Intro text (explain what the app does)
    st.write("This app uses real NBA data to predict the champion and MVP.")

    

    top_team = teams_ranked.iloc[0]
    top_player = players_ranked.iloc[0]
    
    # Columns layout (side-by-side UI)
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
    
    # Teach: sidebar = user controls
    st.sidebar.header("Filters")
    
    top_n_teams = st.sidebar.slider("Top teams to show", 5, 30, 10)
    top_n_players = st.sidebar.slider("Top players to show", 5, 50, 10)
    
    
    # -----------------------------------
    # SHOW TEAM TABLE
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
    
    # Start ranking at 1 instead of 0
    team_display.index = team_display.index + 1
    
    st.dataframe(team_display)
    
    
    
    # -----------------------------------
    # SHOW PLAYER TABLE
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
    
    st.dataframe(player_display)
    
    
    
    # -----------------------------------
    # MAKE CHARTS
    # -----------------------------------
    
    # Teach: charts help visualize rankings
    
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
    # Teach: scatter plots show relationships between variables
    # Here: offense vs defense, with size = wins and color = strength
    
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
    landscape_fig.update_yaxes(autorange="reversed")  # lower DEF rating is better
    st.plotly_chart(landscape_fig, use_container_width=True)

    
    
    # -----------------------------------
    # TEAM EXPLORER
    # -----------------------------------
    # Teach: selectbox lets users filter data interactively
    # Then we subset the dataframe to just that team
    
    st.subheader("Team Explorer")
    
    selected_team = st.selectbox("Choose a team", teams_ranked["TEAM_NAME"], key="team_explorer")
    
    one_team = teams_ranked[teams_ranked["TEAM_NAME"] == selected_team].copy()

    if len(one_team) > 0:
        one_team.index = one_team.index + 1
        one_team.index.name = "Rank"
        st.dataframe(one_team.drop(columns=["TEAM_ID"], errors="ignore"))

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
        st.dataframe(team_stat_compare, hide_index=True)
    
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
    
    # Teach: user selects a player → show details
    
    st.subheader("Player Explorer")
    
    selected_player = st.selectbox("Choose a player", players_ranked["PLAYER_NAME"])
    
    one_player = players_ranked[players_ranked["PLAYER_NAME"] == selected_player]
    
    one_player = one_player.drop(columns=["PLAYER_ID"], errors="ignore")
    
    # Fix index to match ranking
    one_player.index = one_player.index + 1
    one_player.index.name = "Rank"
    
    st.dataframe(one_player)
    
    
    
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
        ].head(10)
    )



# -----------------------------------
# MY STATS TRACKER PAGE
# -----------------------------------
if page == "My Stats Tracker" and sport == "Basketball":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()
    
    st.title("My Stats Tracker")
    st.write("Track your own games, see trends over time, and compare your averages to NBA players.")

# make sure to change -----------------------
    
    if "my_games" not in st.session_state:
        st.session_state.my_games = pd.DataFrame(columns=[
            "Date",
            "Opponent",
            "Team Score",
            "Opponent Score",
            "Points",
            "Rebounds",
            "Assists",
            "Steals",
            "Blocks",
            "Turnovers"
        ])

    # -----------------------------
    # ENTRY FORM
    # -----------------------------
    st.subheader("Add a Game")

    with st.form("my_stats_form"):
        st.subheader("Game Info")
    
        info1, info2, info3 = st.columns([1, 1.5, 1])
    
        with info1:
            game_date = st.date_input("Game Date")
    
        with info2:
            opponent = st.text_input("Opponent")
    
        with info3:
            score1, score2 = st.columns(2)
        
            with score1:
                team_score = st.number_input("My Team Score", min_value=0, step=1)
        
            with score2:
                opp_score = st.number_input("Opponent", min_value=0, step=1)
    
        st.subheader("My Stats")
    
        c1, c2, c3 = st.columns(3)
    
        with c1:
            my_pts = st.number_input("Points", min_value=0, step=1)
            my_reb = st.number_input("Rebounds", min_value=0, step=1)
    
        with c2:
            my_ast = st.number_input("Assists", min_value=0, step=1)
            my_stl = st.number_input("Steals", min_value=0, step=1)
    
        with c3:
            my_blk = st.number_input("Blocks", min_value=0, step=1)
            my_tov = st.number_input("Turnovers", min_value=0, step=1)
    
        submitted = st.form_submit_button("Add My Game")

        if submitted:
            if opponent.strip() == "":
                st.error("Please enter an opponent.")
            else:
                new_game = pd.DataFrame([{ # change!!!!!!!!!!
                    "Date": pd.to_datetime(game_date),
                    "Opponent": opponent,
                    "Team Score": team_score,
                    "Opponent Score": opp_score,
                    "Points": my_pts,
                    "Rebounds": my_reb,
                    "Assists": my_ast,
                    "Steals": my_stl,
                    "Blocks": my_blk,
                    "Turnovers": my_tov
                }]) 

                st.session_state.my_games = pd.concat(
                    [st.session_state.my_games, new_game],
                    ignore_index=True
                )

                st.success("Game added!")

    # -----------------------------
    # IF NO GAMES YET
    # -----------------------------
    if len(st.session_state.my_games) == 0:
        st.info("No games entered yet. Add your first game above.")
    else:
        my_games = st.session_state.my_games.copy()

        my_games["Date"] = pd.to_datetime(my_games["Date"], errors="coerce")

        numeric_cols = ["Team Score", "Opponent Score", "Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"] # change -----
        for col in numeric_cols:
            my_games[col] = pd.to_numeric(my_games[col], errors="coerce")

        my_games = my_games.dropna(subset=["Date"])
        my_games[numeric_cols] = my_games[numeric_cols].fillna(0)

        my_games = my_games.sort_values("Date").reset_index(drop=True)



        # -----------------------------
        # NBA NORMALIZATION (ADD HERE)
        # -----------------------------
        NBA_AVG_TEAM_PTS = 115.0
        
        my_games["Scoring Factor"] = NBA_AVG_TEAM_PTS / my_games["Team Score"].replace(0, pd.NA)
        my_games["Scoring Factor"] = my_games["Scoring Factor"].fillna(1.0)
        
        my_games["Scoring Factor"] = my_games["Scoring Factor"].clip(lower=0.6, upper=4.5)
        
        my_games["NBA_EQ_PTS"] = my_games["Points"] * my_games["Scoring Factor"]
        my_games["NBA_EQ_AST"] = my_games["Assists"] * my_games["Scoring Factor"]
        
        # optional gentler scaling
        my_games["NBA_EQ_REB"] = my_games["Rebounds"] * (my_games["Scoring Factor"] ** 0.5)
        my_games["NBA_EQ_STL"] = my_games["Steals"] * (my_games["Scoring Factor"] ** 0.3)
        my_games["NBA_EQ_BLK"] = my_games["Blocks"] * (my_games["Scoring Factor"] ** 0.3)
        my_games["NBA_EQ_TOV"] = my_games["Turnovers"] * my_games["Scoring Factor"]

        # -----------------------------
        # SUMMARY METRICS
        # -----------------------------

        comparison_mode = st.toggle("Use NBA-adjusted stats", value=False)
        
        if comparison_mode:
            display_label = "NBA-Adjusted"
            my_avg = pd.DataFrame([{
                "PTS": my_games["NBA_EQ_PTS"].mean(),
                "REB": my_games["NBA_EQ_REB"].mean(),
                "AST": my_games["NBA_EQ_AST"].mean(),
                "STL": my_games["NBA_EQ_STL"].mean(),
                "BLK": my_games["NBA_EQ_BLK"].mean(),
                "TOV": my_games["NBA_EQ_TOV"].mean()
            }]).round(2)
        else:
            display_label = "Raw"
            my_avg = pd.DataFrame([{
                "PTS": my_games["Points"].mean(),
                "REB": my_games["Rebounds"].mean(),
                "AST": my_games["Assists"].mean(),
                "STL": my_games["Steals"].mean(),
                "BLK": my_games["Blocks"].mean(),
                "TOV": my_games["Turnovers"].mean()
            }]).round(2)
        
        # my_avg = pd.DataFrame([{
        #     "PTS": my_games["Points"].mean(),
        #     "REB": my_games["Rebounds"].mean(),
        #     "AST": my_games["Assists"].mean(),
        #     "STL": my_games["Steals"].mean(),
        #     "BLK": my_games["Blocks"].mean(),
        #     "TOV": my_games["Turnovers"].mean()
        # }]).round(2)

        total_games = len(my_games)

        m1 = st.columns(1)[0]
        with m1:
            st.metric("Games Tracked", total_games)

        st.subheader("My Average Stats")
        st.caption(f"Currently showing: {display_label} stats")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Points", my_avg.loc[0, "PTS"])
            st.metric("Rebounds", my_avg.loc[0, "REB"])
        with c2:
            st.metric("Assists", my_avg.loc[0, "AST"])
            st.metric("Steals", my_avg.loc[0, "STL"])
        with c3:
            st.metric("Blocks", my_avg.loc[0, "BLK"])
            st.metric("Turnovers", my_avg.loc[0, "TOV"])

        # -----------------------------
        # NBA COMPARISON
        # -----------------------------
        # Teach: we measure similarity using distance (like in machine learning)
        # Smaller distance = more similar player
        # This is Euclidean distance (same idea used in clustering, KNN, etc.)
        
        st.subheader("NBA Player Comparison")

        compare_cols = ["PTS", "REB", "AST", "STL", "BLK", "TOV"]

        nba_compare = players[[
            "PLAYER_NAME",
            "TEAM_ABBREVIATION",
            "PTS",
            "REB",
            "AST",
            "STL",
            "BLK",
            "TOV"
        ]].copy()

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

        closest_nba = top_matches.iloc[0]

        st.metric("Closest NBA Match", closest_nba["PLAYER_NAME"])
        st.write("Team:", closest_nba["TEAM_ABBREVIATION"])
        st.write("This player has the most similar box score profile to your average game.")

        comparison_df = pd.DataFrame({
            "Stat": compare_cols,
            "My Average": [
                my_avg.loc[0, "PTS"],
                my_avg.loc[0, "REB"],
                my_avg.loc[0, "AST"],
                my_avg.loc[0, "STL"],
                my_avg.loc[0, "BLK"],
                my_avg.loc[0, "TOV"]
            ],
            closest_nba["PLAYER_NAME"]: [
                closest_nba["PTS"],
                closest_nba["REB"],
                closest_nba["AST"],
                closest_nba["STL"],
                closest_nba["BLK"],
                closest_nba["TOV"]
            ]
        })

        st.dataframe(comparison_df, hide_index=True)

        st.write("Top 5 NBA matches:")
        st.dataframe(
            top_matches[[
                "PLAYER_NAME",
                "TEAM_ABBREVIATION",
                "DISTANCE",
                "Similarity Score"
            ]],
            hide_index=True
        )

        match_fig = px.bar(
            top_matches,
            x="Similarity Score",
            y="PLAYER_NAME",
            orientation="h",
            title="Top NBA Player Matches"
        )
        match_fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(match_fig, use_container_width=True)


        # -----------------------------
        # TREND CHARTS
        # -----------------------------
        st.subheader("Performance Trends")

        trend_choice = st.selectbox(
            "Choose a stat to graph",
            ["Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"]
        )

        trend_fig = px.line(
            my_games,
            x="Date",
            y=trend_choice,
            markers=True,
            hover_data=["Opponent"],
            title=f"{trend_choice} Over Time"
        )
        st.plotly_chart(trend_fig, use_container_width=True)


        # -----------------------------
        # GAME LOG
        # -----------------------------

        download_cols = [
            "Date",
            "Opponent",
            "Team Score",
            "Opponent Score",
            "Points",
            "Rebounds",
            "Assists",
            "Steals",
            "Blocks",
            "Turnovers"
        ]
        
        st.subheader("My Game Log")

        game_log = my_games[download_cols].copy()
        game_log["Date"] = game_log["Date"].dt.strftime("%Y-%m-%d")
        game_log.index = game_log.index + 1

        st.dataframe(game_log)

        # -----------------------------
        # DELETE A GAME
        # -----------------------------
        st.subheader("Delete a Game")

        delete_options_df = my_games.copy()
        delete_options_df["Date_str"] = delete_options_df["Date"].dt.strftime("%Y-%m-%d")
        delete_options_df["Delete Label"] = (
            delete_options_df["Date_str"] + " vs " + delete_options_df["Opponent"] +
            " | PTS: " + delete_options_df["Points"].astype(int).astype(str) +
            ", REB: " + delete_options_df["Rebounds"].astype(int).astype(str) +
            ", AST: " + delete_options_df["Assists"].astype(int).astype(str)
        )

        delete_idx = st.selectbox(
            "Choose a game to delete",
            options=delete_options_df.index,
            format_func=lambda i: delete_options_df.loc[i, "Delete Label"],
            key="delete_game_select"
        )

        if st.button("Delete Selected Game"):
            st.session_state.my_games = st.session_state.my_games.drop(
                st.session_state.my_games.index[delete_idx]
            ).reset_index(drop=True)
            st.success("Game deleted.")
            st.rerun()

        # # -----------------------------
        # # DOWNLOAD + CLEAR
        # # -----------------------------
        # c1, c2 = st.columns(2)
        
        # with c1:
        #     # ✅ Only keep user-facing columns (clean output)
        #     download_cols = [
        #         "Date",
        #         "Opponent",
        #         "Team Score",
        #         "Opponent Score",
        #         "Points",
        #         "Rebounds",
        #         "Assists",
        #         "Steals",
        #         "Blocks",
        #         "Turnovers"
        #     ]
        
        #     download_df = my_games[download_cols].copy()
        #     download_df["Date"] = download_df["Date"].dt.strftime("%Y-%m-%d")
        
        #     st.download_button(
        #         label="Download My Game Log as CSV",
        #         data=download_df.to_csv(index=False),
        #         file_name="my_game_log.csv",
        #         mime="text/csv"
        #     )
        
        # with c2:
        #     if st.button("Clear My Games"):
        #         st.session_state.my_games = pd.DataFrame(columns=[
        #             "Date",
        #             "Opponent",
        #             "Team Score",
        #             "Opponent Score",
        #             "Points",
        #             "Rebounds",
        #             "Assists",
        #             "Steals",
        #             "Blocks",
        #             "Turnovers"
        #         ])
        #         st.success("Your saved game stats were cleared.")




if page == "My Stats Tracker" and sport == "Baseball":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    st.title("Baseball Stats Tracker")
    st.write("Track your baseball games, see trends, and compare your averages to MLB hitters.")

    BASEBALL_COLUMNS = [
        "Date",
        "Opponent",
        "Team Runs",
        "Opponent Runs",
        "At Bats",
        "Hits",
        "Runs",
        "RBIs",
        "Walks",
        "Strikeouts",
        "Doubles",
        "Triples",
        "Home Runs",
        "Stolen Bases"
    ]

    if "my_baseball_games" not in st.session_state:
        st.session_state.my_baseball_games = pd.DataFrame(columns=BASEBALL_COLUMNS)

    @st.cache_data
    def load_mlb_batting_data(year):
        start_dt = f"{year}-03-01"
        end_dt = f"{year}-11-30"
    
        mlb = batting_stats_range(start_dt, end_dt).copy()
    
        # Baseball Reference / pybaseball can return slightly different column names
        rename_map = {}
    
        if "Tm" in mlb.columns:
            rename_map["Tm"] = "Team"
        if "BA" in mlb.columns:
            rename_map["BA"] = "AVG"
    
        mlb = mlb.rename(columns=rename_map)
    
        # Optional: inspect columns once if debugging
        # st.write(mlb.columns.tolist())
    
        keep_cols = [
            "Name", "Team", "AVG", "OBP", "SLG", "OPS",
            "HR", "RBI", "SB", "PA"
        ]
    
        missing_cols = [col for col in keep_cols if col not in mlb.columns]
        if missing_cols:
            raise ValueError(f"Missing expected MLB columns: {missing_cols}. Found: {mlb.columns.tolist()}")
    
        mlb = mlb[keep_cols].copy()
    
        mlb = mlb[mlb["PA"] != ""].copy()
    
        numeric_cols = ["AVG", "OBP", "SLG", "OPS", "HR", "RBI", "SB", "PA"]
        for col in numeric_cols:
            mlb[col] = pd.to_numeric(mlb[col], errors="coerce")
    
        mlb = mlb[mlb["PA"] >= 20].copy()
        mlb = mlb.dropna(subset=["AVG", "OBP", "SLG", "OPS", "HR", "RBI", "SB"])
    
        return mlb.reset_index(drop=True)


    

    st.subheader("Add a Game")

    with st.form("my_baseball_form"):
        st.subheader("Game Info")

        info1, info2, info3 = st.columns([1, 1.5, 1])

        with info1:
            game_date = st.date_input("Game Date", key="baseball_date")

        with info2:
            opponent = st.text_input("Opponent", key="baseball_opponent")

        with info3:
            score1, score2 = st.columns(2)
            with score1:
                team_runs = st.number_input("My Team", min_value=0, step=1, key="team_runs")
            with score2:
                opp_runs = st.number_input("Opponent", min_value=0, step=1, key="opp_runs")

        st.subheader("My Hitting Stats")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            at_bats = st.number_input("At Bats", min_value=0, step=1, key="bb_ab")
            hits = st.number_input("Hits", min_value=0, step=1, key="bb_h")

        with c2:
            runs = st.number_input("Runs", min_value=0, step=1, key="bb_r")
            rbis = st.number_input("RBIs", min_value=0, step=1, key="bb_rbi")

        with c3:
            walks = st.number_input("Walks", min_value=0, step=1, key="bb_bb")
            strikeouts = st.number_input("Strikeouts", min_value=0, step=1, key="bb_so")

        with c4:
            doubles = st.number_input("Doubles", min_value=0, step=1, key="bb_2b")
            triples = st.number_input("Triples", min_value=0, step=1, key="bb_3b")
            home_runs = st.number_input("Home Runs", min_value=0, step=1, key="bb_hr")
            stolen_bases = st.number_input("Stolen Bases", min_value=0, step=1, key="bb_sb")

        submitted = st.form_submit_button("Add Baseball Game")

        if submitted:
            if opponent.strip() == "":
                st.error("Please enter an opponent.")
            elif hits > at_bats:
                st.error("Hits cannot be greater than at bats.")
            elif doubles + triples + home_runs > hits:
                st.error("Doubles + Triples + Home Runs cannot be greater than total Hits.")
            else:
                new_game = pd.DataFrame([{
                    "Date": pd.to_datetime(game_date),
                    "Opponent": opponent,
                    "Team Runs": team_runs,
                    "Opponent Runs": opp_runs,
                    "At Bats": at_bats,
                    "Hits": hits,
                    "Runs": runs,
                    "RBIs": rbis,
                    "Walks": walks,
                    "Strikeouts": strikeouts,
                    "Doubles": doubles,
                    "Triples": triples,
                    "Home Runs": home_runs,
                    "Stolen Bases": stolen_bases
                }])

                st.session_state.my_baseball_games = pd.concat(
                    [st.session_state.my_baseball_games, new_game],
                    ignore_index=True
                )

                st.success("Baseball game added!")

    if len(st.session_state.my_baseball_games) == 0:
        st.info("No baseball games entered yet. Add your first game above.")
    else:
        baseball_games = st.session_state.my_baseball_games.copy()

        baseball_games["Date"] = pd.to_datetime(baseball_games["Date"], errors="coerce")

        numeric_cols = [
            "Team Runs", "Opponent Runs", "At Bats", "Hits", "Runs", "RBIs",
            "Walks", "Strikeouts", "Doubles", "Triples", "Home Runs", "Stolen Bases"
        ]
        for col in numeric_cols:
            baseball_games[col] = pd.to_numeric(baseball_games[col], errors="coerce")

        baseball_games = baseball_games.dropna(subset=["Date"])
        baseball_games[numeric_cols] = baseball_games[numeric_cols].fillna(0)
        baseball_games = baseball_games.sort_values("Date").reset_index(drop=True)

        # -------- totals --------
        total_games = len(baseball_games)
        total_ab = baseball_games["At Bats"].sum()
        total_hits = baseball_games["Hits"].sum()
        total_walks = baseball_games["Walks"].sum()
        total_doubles = baseball_games["Doubles"].sum()
        total_triples = baseball_games["Triples"].sum()
        total_hr = baseball_games["Home Runs"].sum()
        total_rbi = baseball_games["RBIs"].sum()
        total_sb = baseball_games["Stolen Bases"].sum()

        singles = total_hits - total_doubles - total_triples - total_hr
        singles = max(singles, 0)
        total_bases = singles + 2 * total_doubles + 3 * total_triples + 4 * total_hr

        batting_avg = total_hits / total_ab if total_ab > 0 else 0
        obp = (total_hits + total_walks) / (total_ab + total_walks) if (total_ab + total_walks) > 0 else 0
        slg = total_bases / total_ab if total_ab > 0 else 0
        ops = obp + slg

        st.subheader("My Baseball Summary")

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
        with t1:
            st.metric("Home Runs", int(total_hr))
        with t2:
            st.metric("RBIs", int(total_rbi))
        with t3:
            st.metric("Stolen Bases", int(total_sb))

        # use per-game totals for counting stats so they compare better with MLB season totals scaled by games
        my_profile = {
            "AVG": batting_avg,
            "OBP": obp,
            "SLG": slg,
            "OPS": ops,
            "HR_PER_GAME": total_hr / total_games if total_games > 0 else 0,
            "RBI_PER_GAME": total_rbi / total_games if total_games > 0 else 0,
            "SB_PER_GAME": total_sb / total_games if total_games > 0 else 0
        }

        # -------- MLB comparison --------
        st.subheader("MLB Player Comparison")

        mlb_year = st.selectbox(
            "Choose MLB season for comparison",
            [2023, 2024, 2025, 2026],
            index=2
        )

        try:
            mlb_hitters = load_mlb_batting_data(mlb_year).copy()

            # estimate games played from PA to turn season totals into rough per-game values
            mlb_hitters["EST_G"] = (mlb_hitters["PA"] / 4.2).clip(lower=1)
            mlb_hitters["HR_PER_GAME"] = mlb_hitters["HR"] / mlb_hitters["EST_G"]
            mlb_hitters["RBI_PER_GAME"] = mlb_hitters["RBI"] / mlb_hitters["EST_G"]
            mlb_hitters["SB_PER_GAME"] = mlb_hitters["SB"] / mlb_hitters["EST_G"]

            # weighted distance: rate stats matter most
            mlb_hitters["DISTANCE"] = (
                ((mlb_hitters["AVG"] - my_profile["AVG"]) / 0.030) ** 2 +
                ((mlb_hitters["OBP"] - my_profile["OBP"]) / 0.040) ** 2 +
                ((mlb_hitters["SLG"] - my_profile["SLG"]) / 0.060) ** 2 +
                ((mlb_hitters["OPS"] - my_profile["OPS"]) / 0.090) ** 2 +
                ((mlb_hitters["HR_PER_GAME"] - my_profile["HR_PER_GAME"]) / 0.12) ** 2 +
                ((mlb_hitters["RBI_PER_GAME"] - my_profile["RBI_PER_GAME"]) / 0.20) ** 2 +
                ((mlb_hitters["SB_PER_GAME"] - my_profile["SB_PER_GAME"]) / 0.10) ** 2
            ) ** 0.5

            mlb_hitters["Similarity Score"] = (1 / (1 + mlb_hitters["DISTANCE"])).round(3)

            top_matches = mlb_hitters.sort_values("DISTANCE").head(5).reset_index(drop=True)
            closest_mlb = top_matches.iloc[0]

            st.metric("Closest MLB Match", closest_mlb["Name"])
            st.write("Team:", closest_mlb["Team"])
            st.caption("Comparison is based on AVG, OBP, SLG, OPS, HR/game, RBI/game, and SB/game.")

            comparison_df = pd.DataFrame({
                "Stat": ["AVG", "OBP", "SLG", "OPS", "HR/Game", "RBI/Game", "SB/Game"],
                "My Profile": [
                    round(my_profile["AVG"], 3),
                    round(my_profile["OBP"], 3),
                    round(my_profile["SLG"], 3),
                    round(my_profile["OPS"], 3),
                    round(my_profile["HR_PER_GAME"], 3),
                    round(my_profile["RBI_PER_GAME"], 3),
                    round(my_profile["SB_PER_GAME"], 3)
                ],
                closest_mlb["Name"]: [
                    round(closest_mlb["AVG"], 3),
                    round(closest_mlb["OBP"], 3),
                    round(closest_mlb["SLG"], 3),
                    round(closest_mlb["OPS"], 3),
                    round(closest_mlb["HR_PER_GAME"], 3),
                    round(closest_mlb["RBI_PER_GAME"], 3),
                    round(closest_mlb["SB_PER_GAME"], 3)
                ]
            })

            st.dataframe(comparison_df, hide_index=True)

            st.write("Top 5 MLB matches:")
            st.dataframe(
                top_matches[[
                    "Name", "Team", "AVG", "OBP", "SLG", "OPS",
                    "HR", "RBI", "SB", "Similarity Score"
                ]],
                hide_index=True
            )

            match_fig = px.bar(
                top_matches,
                x="Similarity Score",
                y="Name",
                orientation="h",
                title="Top MLB Player Matches"
            )
            match_fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(match_fig, use_container_width=True)

        except Exception as e:
            st.warning(f"Could not load MLB comparison data right now: {e}")

        # -------- trends --------
        st.subheader("Performance Trends")
        trend_choice = st.selectbox(
            "Choose a stat to graph",
            ["Hits", "Runs", "RBIs", "Walks", "Strikeouts", "Home Runs", "Stolen Bases"],
            key="baseball_trend_choice"
        )

        trend_fig = px.line(
            baseball_games,
            x="Date",
            y=trend_choice,
            markers=True,
            hover_data=["Opponent"],
            title=f"{trend_choice} Over Time"
        )
        st.plotly_chart(trend_fig, use_container_width=True)

        # -------- game log --------
        baseball_display_cols = [
            "Date", "Opponent", "Team Runs", "Opponent Runs", "At Bats", "Hits",
            "Runs", "RBIs", "Walks", "Strikeouts", "Doubles", "Triples",
            "Home Runs", "Stolen Bases"
        ]

        st.subheader("My Game Log")
        game_log = baseball_games[baseball_display_cols].copy()
        game_log["Date"] = game_log["Date"].dt.strftime("%Y-%m-%d")
        game_log.index = game_log.index + 1
        st.dataframe(game_log)

        
        # -------- delete a game --------
        st.subheader("Delete a Game")

        delete_options_df = baseball_games.copy()
        delete_options_df["Date_str"] = delete_options_df["Date"].dt.strftime("%Y-%m-%d")
        delete_options_df["Delete Label"] = (
            delete_options_df["Date_str"] + " vs " + delete_options_df["Opponent"] +
            " | H: " + delete_options_df["Hits"].astype(int).astype(str) +
            ", RBI: " + delete_options_df["RBIs"].astype(int).astype(str) +
            ", HR: " + delete_options_df["Home Runs"].astype(int).astype(str)
        )

        delete_idx = st.selectbox(
            "Choose a baseball game to delete",
            options=delete_options_df.index,
            format_func=lambda i: delete_options_df.loc[i, "Delete Label"],
            key="delete_baseball_game_select"
        )

        if st.button("Delete Selected Baseball Game"):
            st.session_state.my_baseball_games = st.session_state.my_baseball_games.drop(
                st.session_state.my_baseball_games.index[delete_idx]
            ).reset_index(drop=True)
            st.success("Baseball game deleted.")
            st.rerun()





# Footall (NEW)
# Footall (NEW)

@st.cache_data
def load_nfl_player_data(season):
    raw = nfl.load_player_stats([season])
    weekly = raw.to_pandas()

    numeric_cols = [
        "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
        "carries", "rushing_yards", "rushing_tds", "receptions", "targets",
        "receiving_yards", "receiving_tds", "fantasy_points_ppr",
        "def_tackles_solo", "def_tackle_assists", "def_sacks", "def_fumbles_forced",
        "def_interceptions", "def_pass_defended", "def_fumbles"
    ]

    for col in numeric_cols:
        if col in weekly.columns:
            weekly[col] = pd.to_numeric(weekly[col], errors="coerce").fillna(0)
        else:
            weekly[col] = 0

    weekly["game_played"] = 1

    group_cols = [c for c in ["player_name", "team", "position"] if c in weekly.columns]

    agg_dict = {col: "sum" for col in numeric_cols if col in weekly.columns}
    agg_dict["game_played"] = "sum"

    player_stats = weekly.groupby(group_cols, as_index=False).agg(agg_dict)
    player_stats = player_stats.rename(columns={"game_played": "games"})
    player_stats = player_stats[player_stats["games"] >= 4].copy()

    return player_stats.reset_index(drop=True)


if page == "My Stats Tracker" and sport == "Football":
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    st.title("Football Stats Tracker")
    st.write("Track your football games, see trends over time, and compare your averages to NFL players.")

    football_mode = st.selectbox(
        "Choose football role",
        ["QB", "RB", "WR/TE", "Defense"],
        key="football_mode_select"
    )

    mode_key_map = {
        "QB": "qb",
        "RB": "rb",
        "WR/TE": "wrte",
        "Defense": "def"
    }
    mode_key = mode_key_map[football_mode]

    FOOTBALL_MODE_COLUMNS = {
        "QB": [
            "Date", "Opponent", "Team Score", "Opponent Score",
            "Completions", "Attempts", "Passing Yards", "Passing TDs", "Interceptions",
            "Rushing Yards", "Rushing TDs"
        ],
        "RB": [
            "Date", "Opponent", "Team Score", "Opponent Score",
            "Carries", "Rushing Yards", "Rushing TDs",
            "Receptions", "Receiving Yards", "Receiving TDs"
        ],
        "WR/TE": [
            "Date", "Opponent", "Team Score", "Opponent Score",
            "Targets", "Receptions", "Receiving Yards", "Receiving TDs",
            "Rushing Yards", "Rushing TDs"
        ],
        "Defense": [
            "Date", "Opponent", "Team Score", "Opponent Score",
            "Tackles", "Assists", "Sacks", "Interceptions",
            "Passes Defended", "Forced Fumbles", "Fumble Recoveries"
        ]
    }

    session_key = f"my_football_games_{mode_key}"
    FOOTBALL_COLUMNS = FOOTBALL_MODE_COLUMNS[football_mode]

    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame(columns=FOOTBALL_COLUMNS)

    st.subheader(f"Add a {football_mode} Game")

    with st.form(f"my_football_form_{mode_key}"):
        st.subheader("Game Info")

        info1, info2, info3 = st.columns([1, 1.5, 1])

        with info1:
            game_date = st.date_input("Game Date", key=f"football_date_{mode_key}")

        with info2:
            opponent = st.text_input("Opponent", key=f"football_opponent_{mode_key}")

        with info3:
            score1, score2 = st.columns(2)
            with score1:
                team_score = st.number_input("My Team Score", min_value=0, step=1, key=f"football_team_score_{mode_key}")
            with score2:
                opp_score = st.number_input("Opponent Score", min_value=0, step=1, key=f"football_opp_score_{mode_key}")

        st.subheader("My Stats")

        if football_mode == "QB":
            c1, c2, c3 = st.columns(3)

            with c1:
                completions = st.number_input("Completions", min_value=0, step=1, key="qb_completions")
                attempts = st.number_input("Attempts", min_value=0, step=1, key="qb_attempts")

            with c2:
                passing_yards = st.number_input("Passing Yards", min_value=0, step=1, key="qb_passing_yards")
                passing_tds = st.number_input("Passing TDs", min_value=0, step=1, key="qb_passing_tds")
                interceptions = st.number_input("Interceptions", min_value=0, step=1, key="qb_interceptions")

            with c3:
                rushing_yards = st.number_input("Rushing Yards", min_value=0, step=1, key="qb_rushing_yards")
                rushing_tds = st.number_input("Rushing TDs", min_value=0, step=1, key="qb_rushing_tds")

        elif football_mode == "RB":
            c1, c2, c3 = st.columns(3)

            with c1:
                carries = st.number_input("Carries", min_value=0, step=1, key="rb_carries")
                rushing_yards = st.number_input("Rushing Yards", min_value=0, step=1, key="rb_rushing_yards")
                rushing_tds = st.number_input("Rushing TDs", min_value=0, step=1, key="rb_rushing_tds")

            with c2:
                receptions = st.number_input("Receptions", min_value=0, step=1, key="rb_receptions")
                receiving_yards = st.number_input("Receiving Yards", min_value=0, step=1, key="rb_receiving_yards")

            with c3:
                receiving_tds = st.number_input("Receiving TDs", min_value=0, step=1, key="rb_receiving_tds")

        elif football_mode == "WR/TE":
            c1, c2, c3 = st.columns(3)

            with c1:
                targets = st.number_input("Targets", min_value=0, step=1, key="wr_targets")
                receptions = st.number_input("Receptions", min_value=0, step=1, key="wr_receptions")

            with c2:
                receiving_yards = st.number_input("Receiving Yards", min_value=0, step=1, key="wr_receiving_yards")
                receiving_tds = st.number_input("Receiving TDs", min_value=0, step=1, key="wr_receiving_tds")

            with c3:
                rushing_yards = st.number_input("Rushing Yards", min_value=0, step=1, key="wr_rushing_yards")
                rushing_tds = st.number_input("Rushing TDs", min_value=0, step=1, key="wr_rushing_tds")

        elif football_mode == "Defense":
            c1, c2, c3 = st.columns(3)

            with c1:
                tackles = st.number_input("Tackles", min_value=0, step=1, key="def_tackles")
                assists = st.number_input("Assists", min_value=0, step=1, key="def_assists")

            with c2:
                sacks = st.number_input("Sacks", min_value=0.0, step=0.5, key="def_sacks")
                interceptions = st.number_input("Interceptions", min_value=0, step=1, key="def_interceptions")

            with c3:
                passes_defended = st.number_input("Passes Defended", min_value=0, step=1, key="def_passes_defended")
                forced_fumbles = st.number_input("Forced Fumbles", min_value=0, step=1, key="def_forced_fumbles")
                fumble_recoveries = st.number_input("Fumble Recoveries", min_value=0, step=1, key="def_fumble_recoveries")

        submitted = st.form_submit_button(f"Add {football_mode} Game")

        if submitted:
            if opponent.strip() == "":
                st.error("Please enter an opponent.")
            else:
                if football_mode == "QB":
                    if completions > attempts:
                        st.error("Completions cannot be greater than attempts.")
                    else:
                        new_game = pd.DataFrame([{
                            "Date": pd.to_datetime(game_date),
                            "Opponent": opponent,
                            "Team Score": team_score,
                            "Opponent Score": opp_score,
                            "Completions": completions,
                            "Attempts": attempts,
                            "Passing Yards": passing_yards,
                            "Passing TDs": passing_tds,
                            "Interceptions": interceptions,
                            "Rushing Yards": rushing_yards,
                            "Rushing TDs": rushing_tds
                        }])
                        st.session_state[session_key] = pd.concat(
                            [st.session_state[session_key], new_game],
                            ignore_index=True
                        )
                        st.success(f"{football_mode} game added!")

                elif football_mode == "RB":
                    if receptions > 30:
                        st.warning("That is a very high reception total, but the game was still added.")

                    new_game = pd.DataFrame([{
                        "Date": pd.to_datetime(game_date),
                        "Opponent": opponent,
                        "Team Score": team_score,
                        "Opponent Score": opp_score,
                        "Carries": carries,
                        "Rushing Yards": rushing_yards,
                        "Rushing TDs": rushing_tds,
                        "Receptions": receptions,
                        "Receiving Yards": receiving_yards,
                        "Receiving TDs": receiving_tds
                    }])
                    st.session_state[session_key] = pd.concat(
                        [st.session_state[session_key], new_game],
                        ignore_index=True
                    )
                    st.success(f"{football_mode} game added!")

                elif football_mode == "WR/TE":
                    if receptions > targets:
                        st.error("Receptions cannot be greater than targets.")
                    else:
                        new_game = pd.DataFrame([{
                            "Date": pd.to_datetime(game_date),
                            "Opponent": opponent,
                            "Team Score": team_score,
                            "Opponent Score": opp_score,
                            "Targets": targets,
                            "Receptions": receptions,
                            "Receiving Yards": receiving_yards,
                            "Receiving TDs": receiving_tds,
                            "Rushing Yards": rushing_yards,
                            "Rushing TDs": rushing_tds
                        }])
                        st.session_state[session_key] = pd.concat(
                            [st.session_state[session_key], new_game],
                            ignore_index=True
                        )
                        st.success(f"{football_mode} game added!")

                elif football_mode == "Defense":
                    new_game = pd.DataFrame([{
                        "Date": pd.to_datetime(game_date),
                        "Opponent": opponent,
                        "Team Score": team_score,
                        "Opponent Score": opp_score,
                        "Tackles": tackles,
                        "Assists": assists,
                        "Sacks": sacks,
                        "Interceptions": interceptions,
                        "Passes Defended": passes_defended,
                        "Forced Fumbles": forced_fumbles,
                        "Fumble Recoveries": fumble_recoveries
                    }])
                    st.session_state[session_key] = pd.concat(
                        [st.session_state[session_key], new_game],
                        ignore_index=True
                    )
                    st.success(f"{football_mode} game added!")

    if len(st.session_state[session_key]) == 0:
        st.info(f"No {football_mode} games entered yet. Add your first game above.")
    else:
        football_games = st.session_state[session_key].copy()
        football_games["Date"] = pd.to_datetime(football_games["Date"], errors="coerce")

        numeric_cols = [col for col in FOOTBALL_COLUMNS if col not in ["Date", "Opponent"]]
        for col in numeric_cols:
            football_games[col] = pd.to_numeric(football_games[col], errors="coerce")

        football_games = football_games.dropna(subset=["Date"])
        football_games[numeric_cols] = football_games[numeric_cols].fillna(0)
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
                st.metric("INT/Game", my_avg.loc[0, "INT"])
            with c3:
                st.metric("Rush Yards/Game", my_avg.loc[0, "RUSH_YDS"])
                st.metric("Rush TD/Game", my_avg.loc[0, "RUSH_TD"])

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
                st.metric("Carries/Game", my_avg.loc[0, "CAR"])
                st.metric("Rush Yards/Game", my_avg.loc[0, "RUSH_YDS"])
            with c2:
                st.metric("Rush TD/Game", my_avg.loc[0, "RUSH_TD"])
                st.metric("Receptions/Game", my_avg.loc[0, "REC"])
            with c3:
                st.metric("Rec Yards/Game", my_avg.loc[0, "REC_YDS"])
                st.metric("Rec TD/Game", my_avg.loc[0, "REC_TD"])

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
                st.metric("Targets/Game", my_avg.loc[0, "TGT"])
                st.metric("Receptions/Game", my_avg.loc[0, "REC"])
            with c2:
                st.metric("Catch %", round(my_avg.loc[0, "CATCH_PCT"] * 100, 1))
                st.metric("Rec Yards/Game", my_avg.loc[0, "REC_YDS"])
            with c3:
                st.metric("Rec TD/Game", my_avg.loc[0, "REC_TD"])
                st.metric("Rush Yards/Game", my_avg.loc[0, "RUSH_YDS"])

        elif football_mode == "Defense":
            my_avg = pd.DataFrame([{
                "TACKLES": football_games["Tackles"].mean(),
                "ASSISTS": football_games["Assists"].mean(),
                "SACKS": football_games["Sacks"].mean(),
                "INT": football_games["Interceptions"].mean(),
                "PD": football_games["Passes Defended"].mean(),
                "FF": football_games["Forced Fumbles"].mean(),
                "FR": football_games["Fumble Recoveries"].mean()
            }]).round(2)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Games Tracked", total_games)
                st.metric("Tackles/Game", my_avg.loc[0, "TACKLES"])
                st.metric("Assists/Game", my_avg.loc[0, "ASSISTS"])
            with c2:
                st.metric("Sacks/Game", my_avg.loc[0, "SACKS"])
                st.metric("INT/Game", my_avg.loc[0, "INT"])
            with c3:
                st.metric("PD/Game", my_avg.loc[0, "PD"])
                st.metric("FF/Game", my_avg.loc[0, "FF"])

        st.subheader(f"NFL {football_mode} Comparison")

        nfl_season = st.selectbox(
            "Choose NFL season for comparison",
            [2023, 2024, 2025],
            index=1,  # default to 2024 since 2025 may be incomplete
            key=f"nfl_season_select_{mode_key}"
        )

        try:
            nfl_players = load_nfl_player_data(nfl_season).copy()

            if football_mode == "QB":
                nfl_compare = nfl_players[nfl_players["position"] == "QB"].copy()
                nfl_compare = nfl_compare[nfl_compare["games"] > 0].copy()
                nfl_compare["CMP_PCT"] = (
                    nfl_compare["completions"] / nfl_compare["attempts"].replace(0, pd.NA)
                ).fillna(0)

                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["passing_yards"] / nfl_compare["games"] - my_avg.loc[0, "PASS_YDS"]) / 45) ** 2 +
                    ((nfl_compare["passing_tds"] / nfl_compare["games"] - my_avg.loc[0, "PASS_TD"]) / 0.9) ** 2 +
                    ((nfl_compare["passing_interceptions"] / nfl_compare["games"] - my_avg.loc[0, "INT"]) / 0.6) ** 2 +
                    ((nfl_compare["rushing_yards"] / nfl_compare["games"] - my_avg.loc[0, "RUSH_YDS"]) / 18) ** 2 +
                    ((nfl_compare["rushing_tds"] / nfl_compare["games"] - my_avg.loc[0, "RUSH_TD"]) / 0.35) ** 2 +
                    ((nfl_compare["CMP_PCT"] - my_avg.loc[0, "CMP_PCT"]) / 0.08) ** 2
                ) ** 0.5

                compare_table = lambda row: [
                    round(row["passing_yards"] / row["games"], 2),
                    round(row["passing_tds"] / row["games"], 2),
                    round(row["passing_interceptions"] / row["games"], 2),
                    round(row["rushing_yards"] / row["games"], 2),
                    round(row["rushing_tds"] / row["games"], 2),
                    round(row["CMP_PCT"] * 100, 1)
                ]

                stat_labels = ["Pass Yards/G", "Pass TD/G", "INT/G", "Rush Yards/G", "Rush TD/G", "Cmp %"]
                my_profile_vals = [
                    round(my_avg.loc[0, "PASS_YDS"], 2),
                    round(my_avg.loc[0, "PASS_TD"], 2),
                    round(my_avg.loc[0, "INT"], 2),
                    round(my_avg.loc[0, "RUSH_YDS"], 2),
                    round(my_avg.loc[0, "RUSH_TD"], 2),
                    round(my_avg.loc[0, "CMP_PCT"] * 100, 1)
                ]

            elif football_mode == "RB":
                nfl_compare = nfl_players[nfl_players["position"] == "RB"].copy()
                nfl_compare = nfl_compare[nfl_compare["games"] > 0].copy()

                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["carries"] / nfl_compare["games"] - my_avg.loc[0, "CAR"]) / 4.0) ** 2 +
                    ((nfl_compare["rushing_yards"] / nfl_compare["games"] - my_avg.loc[0, "RUSH_YDS"]) / 20) ** 2 +
                    ((nfl_compare["rushing_tds"] / nfl_compare["games"] - my_avg.loc[0, "RUSH_TD"]) / 0.4) ** 2 +
                    ((nfl_compare["receptions"] / nfl_compare["games"] - my_avg.loc[0, "REC"]) / 2.0) ** 2 +
                    ((nfl_compare["receiving_yards"] / nfl_compare["games"] - my_avg.loc[0, "REC_YDS"]) / 18) ** 2 +
                    ((nfl_compare["receiving_tds"] / nfl_compare["games"] - my_avg.loc[0, "REC_TD"]) / 0.35) ** 2
                ) ** 0.5

                compare_table = lambda row: [
                    round(row["carries"] / row["games"], 2),
                    round(row["rushing_yards"] / row["games"], 2),
                    round(row["rushing_tds"] / row["games"], 2),
                    round(row["receptions"] / row["games"], 2),
                    round(row["receiving_yards"] / row["games"], 2),
                    round(row["receiving_tds"] / row["games"], 2)
                ]

                stat_labels = ["Carries/G", "Rush Yards/G", "Rush TD/G", "Receptions/G", "Rec Yards/G", "Rec TD/G"]
                my_profile_vals = [
                    round(my_avg.loc[0, "CAR"], 2),
                    round(my_avg.loc[0, "RUSH_YDS"], 2),
                    round(my_avg.loc[0, "RUSH_TD"], 2),
                    round(my_avg.loc[0, "REC"], 2),
                    round(my_avg.loc[0, "REC_YDS"], 2),
                    round(my_avg.loc[0, "REC_TD"], 2)
                ]

            elif football_mode == "WR/TE":
                nfl_compare = nfl_players[nfl_players["position"].isin(["WR", "TE"])].copy()
                nfl_compare = nfl_compare[nfl_compare["games"] > 0].copy()
                nfl_compare["CATCH_PCT"] = (
                    nfl_compare["receptions"] / nfl_compare["targets"].replace(0, pd.NA)
                ).fillna(0)

                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["targets"] / nfl_compare["games"] - my_avg.loc[0, "TGT"]) / 2.5) ** 2 +
                    ((nfl_compare["receptions"] / nfl_compare["games"] - my_avg.loc[0, "REC"]) / 2.0) ** 2 +
                    ((nfl_compare["receiving_yards"] / nfl_compare["games"] - my_avg.loc[0, "REC_YDS"]) / 20) ** 2 +
                    ((nfl_compare["receiving_tds"] / nfl_compare["games"] - my_avg.loc[0, "REC_TD"]) / 0.35) ** 2 +
                    ((nfl_compare["rushing_yards"] / nfl_compare["games"] - my_avg.loc[0, "RUSH_YDS"]) / 12) ** 2 +
                    ((nfl_compare["CATCH_PCT"] - my_avg.loc[0, "CATCH_PCT"]) / 0.10) ** 2
                ) ** 0.5

                compare_table = lambda row: [
                    round(row["targets"] / row["games"], 2),
                    round(row["receptions"] / row["games"], 2),
                    round(row["receiving_yards"] / row["games"], 2),
                    round(row["receiving_tds"] / row["games"], 2),
                    round(row["rushing_yards"] / row["games"], 2),
                    round(row["CATCH_PCT"] * 100, 1)
                ]

                stat_labels = ["Targets/G", "Receptions/G", "Rec Yards/G", "Rec TD/G", "Rush Yards/G", "Catch %"]
                my_profile_vals = [
                    round(my_avg.loc[0, "TGT"], 2),
                    round(my_avg.loc[0, "REC"], 2),
                    round(my_avg.loc[0, "REC_YDS"], 2),
                    round(my_avg.loc[0, "REC_TD"], 2),
                    round(my_avg.loc[0, "RUSH_YDS"], 2),
                    round(my_avg.loc[0, "CATCH_PCT"] * 100, 1)
                ]

            elif football_mode == "Defense":
                defense_positions = ["LB", "ILB", "OLB", "MLB", "CB", "S", "SS", "FS", "DB", "DE", "DT", "DL", "EDGE", "SAF", "NT"]
                nfl_compare = nfl_players[nfl_players["position"].isin(defense_positions)].copy()
                nfl_compare = nfl_compare[nfl_compare["games"] > 0].copy()

                nfl_compare["DISTANCE"] = (
                    ((nfl_compare["def_tackles_solo"] / nfl_compare["games"] - my_avg.loc[0, "TACKLES"]) / 2.5) ** 2 +
                    ((nfl_compare["def_tackle_assists"] / nfl_compare["games"] - my_avg.loc[0, "ASSISTS"]) / 1.5) ** 2 +
                    ((nfl_compare["def_sacks"] / nfl_compare["games"] - my_avg.loc[0, "SACKS"]) / 0.5) ** 2 +
                    ((nfl_compare["def_interceptions"] / nfl_compare["games"] - my_avg.loc[0, "INT"]) / 0.25) ** 2 +
                    ((nfl_compare["def_pass_defended"] / nfl_compare["games"] - my_avg.loc[0, "PD"]) / 0.8) ** 2 +
                    ((nfl_compare["def_fumbles_forced"] / nfl_compare["games"] - my_avg.loc[0, "FF"]) / 0.25) ** 2 +
                    ((nfl_compare["def_fumbles"] / nfl_compare["games"] - my_avg.loc[0, "FR"]) / 0.25) ** 2
                ) ** 0.5

                compare_table = lambda row: [
                    round(row["def_tackles_solo"] / row["games"], 2),
                    round(row["def_tackle_assists"] / row["games"], 2),
                    round(row["def_sacks"] / row["games"], 2),
                    round(row["def_interceptions"] / row["games"], 2),
                    round(row["def_pass_defended"] / row["games"], 2),
                    round(row["def_fumbles_forced"] / row["games"], 2),
                    round(row["def_fumbles"] / row["games"], 2)
                ]

                stat_labels = ["Tackles/G", "Assists/G", "Sacks/G", "INT/G", "PD/G", "FF/G", "FR/G"]
                my_profile_vals = [
                    round(my_avg.loc[0, "TACKLES"], 2),
                    round(my_avg.loc[0, "ASSISTS"], 2),
                    round(my_avg.loc[0, "SACKS"], 2),
                    round(my_avg.loc[0, "INT"], 2),
                    round(my_avg.loc[0, "PD"], 2),
                    round(my_avg.loc[0, "FF"], 2),
                    round(my_avg.loc[0, "FR"], 2)
                ]

            nfl_compare["Similarity Score"] = (1 / (1 + nfl_compare["DISTANCE"])).round(3)

            top_matches = nfl_compare.sort_values("DISTANCE").head(5).reset_index(drop=True)
            closest_nfl = top_matches.iloc[0]

            st.metric("Closest NFL Match", closest_nfl["player_name"])
            st.write("Team:", closest_nfl["team"])          # fixed: was recent_team
            st.write("Position:", closest_nfl["position"])

            comparison_df = pd.DataFrame({
                "Stat": stat_labels,
                "My Profile": my_profile_vals,
                closest_nfl["player_name"]: compare_table(closest_nfl)
            })

            st.dataframe(comparison_df, hide_index=True)

            st.write("Top 5 NFL matches:")
            st.dataframe(
                top_matches[["player_name", "team", "position", "games", "Similarity Score"]],  # fixed: was recent_team
                hide_index=True
            )

            match_fig = px.bar(
                top_matches,
                x="Similarity Score",
                y="player_name",
                orientation="h",
                title=f"Top NFL {football_mode} Matches"
            )
            match_fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(match_fig, use_container_width=True)

        except Exception as e:
            st.warning(f"Could not load NFL comparison data right now: {e}")

        st.subheader("Performance Trends")

        if football_mode == "QB":
            trend_options = ["Passing Yards", "Passing TDs", "Interceptions", "Rushing Yards", "Rushing TDs"]
        elif football_mode == "RB":
            trend_options = ["Carries", "Rushing Yards", "Rushing TDs", "Receptions", "Receiving Yards", "Receiving TDs"]
        elif football_mode == "WR/TE":
            trend_options = ["Targets", "Receptions", "Receiving Yards", "Receiving TDs", "Rushing Yards", "Rushing TDs"]
        elif football_mode == "Defense":
            trend_options = ["Tackles", "Assists", "Sacks", "Interceptions", "Passes Defended", "Forced Fumbles", "Fumble Recoveries"]

        trend_choice = st.selectbox(
            "Choose a stat to graph",
            trend_options,
            key=f"football_trend_choice_{mode_key}"
        )

        trend_fig = px.line(
            football_games,
            x="Date",
            y=trend_choice,
            markers=True,
            hover_data=["Opponent"],
            title=f"{trend_choice} Over Time"
        )
        st.plotly_chart(trend_fig, use_container_width=True)

        st.subheader("My Game Log")
        game_log = football_games[FOOTBALL_COLUMNS].copy()
        game_log["Date"] = game_log["Date"].dt.strftime("%Y-%m-%d")
        game_log.index = game_log.index + 1
        st.dataframe(game_log)

        st.subheader("Delete a Game")

        delete_options_df = football_games.copy()
        delete_options_df["Date_str"] = delete_options_df["Date"].dt.strftime("%Y-%m-%d")

        if football_mode == "QB":
            delete_options_df["Delete Label"] = (
                delete_options_df["Date_str"] + " vs " + delete_options_df["Opponent"] +
                " | Pass: " + delete_options_df["Passing Yards"].astype(int).astype(str) +
                ", TD: " + delete_options_df["Passing TDs"].astype(int).astype(str)
            )
        elif football_mode == "RB":
            delete_options_df["Delete Label"] = (
                delete_options_df["Date_str"] + " vs " + delete_options_df["Opponent"] +
                " | Rush: " + delete_options_df["Rushing Yards"].astype(int).astype(str) +
                ", Rec: " + delete_options_df["Receiving Yards"].astype(int).astype(str)
            )
        elif football_mode == "WR/TE":
            delete_options_df["Delete Label"] = (
                delete_options_df["Date_str"] + " vs " + delete_options_df["Opponent"] +
                " | Rec: " + delete_options_df["Receiving Yards"].astype(int).astype(str) +
                ", TD: " + delete_options_df["Receiving TDs"].astype(int).astype(str)
            )
        elif football_mode == "Defense":
            delete_options_df["Delete Label"] = (
                delete_options_df["Date_str"] + " vs " + delete_options_df["Opponent"] +
                " | Tackles: " + delete_options_df["Tackles"].astype(int).astype(str) +
                ", Sacks: " + delete_options_df["Sacks"].astype(str)
            )

        delete_idx = st.selectbox(
            f"Choose a {football_mode} game to delete",
            options=delete_options_df.index,
            format_func=lambda i: delete_options_df.loc[i, "Delete Label"],
            key=f"delete_football_game_select_{mode_key}"
        )

        if st.button(f"Delete Selected {football_mode} Game"):
            st.session_state[session_key] = st.session_state[session_key].drop(
                st.session_state[session_key].index[delete_idx]
            ).reset_index(drop=True)
            st.success(f"{football_mode} game deleted.")
            st.rerun()