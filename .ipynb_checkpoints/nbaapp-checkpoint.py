import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, leaguedashplayerstats
import plotly.express as px
from pybaseball import batting_stats_range


# 4/23
# - fix line 582 bball page
# - review/build baseball page
# - football page
# - migrate NBA tracker to a new app & rebrand this app

# later: add pitching to baseball page, build coaches view, add development tips + other customizations, build AI bot for playercards


# Page title
st.set_page_config(page_title="NBA Predictor", layout="wide")



# Page navigation
if "page" not in st.session_state:
    st.session_state.page = "Home"

if "sport" not in st.session_state:
    st.session_state.sport = "Basketball"

page = st.session_state.page

if page == "My Stats Tracker":
    sport = st.sidebar.radio(
        "Choose a sport",
        ["Basketball", "Baseball"]
    )



season = st.selectbox(
    "Choose a season",
    ["2022-23", "2023-24", "2024-25", "2025-26"],
    index = 3)


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




# Load Player Data

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



teams = load_team_data(season)
players = load_player_data(season)


# Data Cleaning
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


# Make Champion Score

teams["CHAMPION_SCORE"] = (
    teams["W_PCT"] * 60 +        # winning matters most
    teams["NET_RATING"] * 12 +   # dominance
    teams["OFF_RATING"] * 1.2 +  # offense
    teams["DEF_RATING"] * -1.5   # lower defense is better
)

teams["CHAMPION_SCORE"] = teams["CHAMPION_SCORE"].round(2)

teams_ranked = teams.sort_values("CHAMPION_SCORE", ascending=False).reset_index(drop=True)


# Make MVP Score

players["MVP_SCORE"] = (
    players["PTS"] * 1.3 +      # scoring
    players["AST"] * 1.8 +      # playmaking
    players["REB"] * 0.8 +      # rebounding
    players["STL"] * 1.5 +      # defense
    players["BLK"] * 2.3 +      # defense
    players["TOV"] * -1.3 +     # turnovers are bad
    players["TS_PCT"] * 40 +    # efficiency
    players["W_PCT"] * 50 +     # team success
    players["PIE"] * 80         # overall impact
)

# Round scores
players["MVP_SCORE"] = players["MVP_SCORE"].round(2)

# Sort players from best to worst
players_ranked = players.sort_values("MVP_SCORE", ascending=False).reset_index(drop=True)




# Add Home Page

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




# Display Results

if page == "NBA Predictor":

    # Back button
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    # Main title
    st.title("NBA Champion + MVP Predictor")
    
    # Intro text
    st.write("This app uses real NBA data to predict the champion and MVP.")
    
    
    
    top_team = teams_ranked.iloc[0]
    top_player = players_ranked.iloc[0]
    
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
    
    
    st.sidebar.header("Filters")
    
    top_n_teams = st.sidebar.slider("Top teams to show", 5, 30, 10)
    top_n_players = st.sidebar.slider("Top players to show", 5, 50, 10)
    
    
    # Show the team table
    
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
    
    
    
    # Charts
    
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


    # Scatterplot
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
    
    # Team Explorer
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
        
    # PLAYER EXPLORER
        
    st.subheader("Player Explorer")
    
    selected_player = st.selectbox("Choose a player", players_ranked["PLAYER_NAME"])
    
    one_player = players_ranked[players_ranked["PLAYER_NAME"] == selected_player]
    
    one_player = one_player.drop(columns=["PLAYER_ID"], errors="ignore")
    
    # Fix index to match ranking
    one_player.index = one_player.index + 1
    one_player.index.name = "Rank"
    
    st.dataframe(one_player)



    # Custom MVP Formula Builder

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




if page == "My Stats Tracker" and sport == "Basketball":

    # Back button
    if st.button("⬅ Back to Home"):
        st.session_state.page = "Home"
        st.rerun()

    
    st.title("My Stats Tracker")
    st.write("Track your own games, see trends over time, and compare your averages to NBA players.")


    # Add team and opponent score
    
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


    

    # Entry Form
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
                new_game = pd.DataFrame([{
                    "Date": pd.to_datetime(game_date),
                    "Opponent": opponent,
                    "Team Score": team_score,        # NEW
                    "Opponent Score": opp_score,     # NEW
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



    # IF NO GAMES YET
    if len(st.session_state.my_games) == 0:
        comparison_mode = st.toggle("Use NBA-adjusted stats", key="comparison_mode", value=False)

        st.info("No games entered yet. Add your first game above.")
    else:
        my_games = st.session_state.my_games.copy()

        my_games["Date"] = pd.to_datetime(my_games["Date"], errors="coerce")

        numeric_cols = ["Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"]
        for col in numeric_cols:
            my_games[col] = pd.to_numeric(my_games[col], errors="coerce")

        my_games = my_games.dropna(subset=["Date"])
        my_games[numeric_cols] = my_games[numeric_cols].fillna(0)

        my_games = my_games.sort_values("Date").reset_index(drop=True)



        # Put in new average calculations

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


        comparison_mode = st.toggle("Use NBA-adjusted stats", key="comparison_mode", value=False)

        
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


        total_games = len(my_games)

        m1 = st.columns(1)[0]
        with m1:
            st.metric("Games Tracked", total_games)

        st.subheader("My Average Stats")
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

        

        # NBA Player Comp
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


        

    







    
        
            
    
    
    
        
        
    
    
    
        
    
    
    
    
        
        
        
        
        
        
        
    
    
    
    
    
    
    
    
