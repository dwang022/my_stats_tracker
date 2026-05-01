import streamlit as st
import pandas as pd

st.set_page_config(page_title = "Little League App", layout = "wide")

st.title("Little League Team App")
st.write("Welcome to our app!")

st.divider()

players = pd.DataFrame({
    "Player": ["Rylan", "Roman Anthony", "Aaron Judge", "Julio Rodriguez", "Shohei Ohtani"],
    "OPS": [1.500, 1.089, 1.150, 0.978, 1.085],
    "Batting Average": [0.720, 0.325, 0.350, 0.289, 0.275],
    "WAR": [10000, 11.4, 15.8, 8.9, 20.5],
    "Team": ["Giants", "Red Sox", "Yankees", "Mariners", "Dodgers"]})

st.subheader("Players Data")
st.dataframe(players)


st.sidebar.header("Filters")
team_choice = st.sidebar.selectbox(
    "Choose a Team",
    players["Team"].unique()
)

filtered_players = players[players["Team"] == team_choice]

st.subheader(f"{team_choice} Roster")
st.dataframe(filtered_players)

# Chart at the bottom
st.subheader(f"{team_choice} OPS Chart")

chart_data = filtered_players.set_index("Player")[["OPS"]]
st.bar_chart(chart_data)



# Charts









    