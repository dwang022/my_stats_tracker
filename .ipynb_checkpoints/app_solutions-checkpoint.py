# ============================================
# LITTLE LEAGUE STREAMLIT DASHBOARD
# TEACHING VERSION WITH COMMENTS
# ============================================

# Import Streamlit for building the web app interface
import streamlit as st

# Import pandas for working with tables of data
import pandas as pd


# --------------------------------------------
# PAGE SETUP
# --------------------------------------------

# This controls the browser tab title and makes the app use a wide layout
# Good moment to explain: Streamlit apps can be styled a little with built-in options
st.set_page_config(page_title="Little League Dashboard", layout="wide")


# --------------------------------------------
# APP TITLE / INTRO
# --------------------------------------------

# Large page title
st.title("Little League Team Dashboard")

# st.write is the most flexible Streamlit output function
# It can show text, numbers, tables, charts, and more
st.write("Welcome to the team stats app!")

# Adds a visual separator line
st.divider()


# --------------------------------------------
# SAMPLE DATA
# --------------------------------------------

# Here we build a small dataset directly in Python
# Explain that in real apps, data might come from:
# - a CSV file
# - a database
# - an API
players = pd.DataFrame({
    "Player": ["Jake", "Mason", "Leo", "Ethan", "Noah"],
    "Team": ["Tigers", "Tigers", "Sharks", "Sharks", "Tigers"],
    "Hits": [12, 8, 15, 10, 6],
    "Runs": [9, 5, 11, 7, 4],
    "RBIs": [10, 6, 9, 8, 3]
})

# Show the full data table
# st.dataframe creates an interactive table users can scroll through
st.subheader("All Players")
st.dataframe(players)


# --------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------

# The sidebar is commonly used in Streamlit apps for filters and controls
# Good teaching point: dashboards often keep controls on the side
st.sidebar.header("Filters")

# Create a dropdown menu with the unique team names
# .unique() gets each team only once
team_choice = st.sidebar.selectbox(
    "Choose a Team",
    players["Team"].unique()
)

# Filter the dataframe based on the selected team
# This is normal pandas filtering
filtered_players = players[players["Team"] == team_choice]


# --------------------------------------------
# TEAM ROSTER SECTION
# --------------------------------------------

# Display only the players from the selected team
st.subheader(f"{team_choice} Roster")
st.dataframe(filtered_players)

# Another dropdown, now based only on players from the filtered team
player_choice = st.selectbox(
    "Choose a Player",
    filtered_players["Player"]
)

# Filter again to get only the selected player's row
player_row = filtered_players[filtered_players["Player"] == player_choice]

# Show the selected player's stats
st.subheader("Selected Player")
st.dataframe(player_row)


# --------------------------------------------
# TEAM SUMMARY METRICS
# --------------------------------------------

# st.columns lets us put content side-by-side
# Great for dashboard layout
col1, col2, col3 = st.columns(3)

# st.metric displays a highlighted summary number
# These are commonly used for KPIs in dashboards
col1.metric("Team Hits", int(filtered_players["Hits"].sum()))
col2.metric("Team Runs", int(filtered_players["Runs"].sum()))
col3.metric("Team RBIs", int(filtered_players["RBIs"].sum()))


# --------------------------------------------
# CHART SECTION
# --------------------------------------------

st.subheader("Team Performance Chart")

# Set the player names as the index so the chart labels look cleaner
chart_data = filtered_players.set_index("Player")[["Hits", "Runs", "RBIs"]]

# Streamlit can automatically make a bar chart from a dataframe
st.bar_chart(chart_data)


# --------------------------------------------
# LEADERBOARD SECTION
# --------------------------------------------

# Sort the full dataset by Hits from highest to lowest
# Good teaching point: apps often rank data to make it easier to compare
st.subheader("Leaderboard by Hits")
leaderboard = players.sort_values("Hits", ascending=False)

# Display the sorted leaderboard table
st.dataframe(leaderboard)

# Optional visual version of the leaderboard
st.subheader("Hits Leaderboard Chart")
st.bar_chart(leaderboard.set_index("Player")["Hits"])


# --------------------------------------------
# INPUT SECTION: ADD A NEW PLAYER
# --------------------------------------------

st.subheader("Add a New Player")

# Give users some guidance
st.info("Enter a new player's information below. This update is temporary and will not save after the app reruns.")

# Text box for the player's name
new_player = st.text_input("Player Name")

# Dropdown for team
# key is needed because we already used another selectbox with team names
new_team = st.selectbox(
    "New Player Team",
    players["Team"].unique(),
    key="new_team"
)

# Number inputs for stats
# min_value and max_value keep inputs reasonable
new_hits = st.number_input("Hits", min_value=0, max_value=50, value=0)
new_runs = st.number_input("Runs", min_value=0, max_value=50, value=0)
new_rbis = st.number_input("RBIs", min_value=0, max_value=50, value=0)

# Button creates an action
# Important teaching point: when the button is clicked, Streamlit reruns the app
if st.button("Add Player"):

    # .strip() removes spaces so blank input like "   " does not count
    if new_player.strip():

        # Create a one-row dataframe for the new player
        new_row = pd.DataFrame({
            "Player": [new_player],
            "Team": [new_team],
            "Hits": [new_hits],
            "Runs": [new_runs],
            "RBIs": [new_rbis]
        })

        # Combine the old table and the new row
        updated_players = pd.concat([players, new_row], ignore_index=True)

        # Show a success message
        st.success(f"{new_player} added successfully!")

        # Show the updated table
        st.subheader("Updated Player Table")
        st.dataframe(updated_players)

    else:
        # Warn the user if they forgot the player name
        st.warning("Please enter a player name.")


# --------------------------------------------
# DOWNLOAD BUTTON
# --------------------------------------------

# Convert the dataframe to CSV format
# .encode("utf-8") turns the text into bytes for downloading
csv = players.to_csv(index=False).encode("utf-8")

# download_button lets users export the data
# This is a nice real-world feature for dashboards
st.subheader("Download Data")
st.download_button(
    "Download Player Stats as CSV",
    csv,
    "players.csv",
    "text/csv"
)


# --------------------------------------------
# WRAP-UP NOTE FOR STUDENTS
# --------------------------------------------

# Nice closing message for the lesson
st.write("You just built a sports dashboard with Python and Streamlit.")


# ============================================
# TEACHING NOTES FOR YOU
# ============================================
#
# Main ideas to emphasize while teaching:
#
# 1. Streamlit apps are just Python scripts.
#    You do not need HTML, CSS, or JavaScript to get started.
#
# 2. Streamlit reruns the whole script top to bottom
#    every time a user changes a widget.
#
# 3. Widgets like selectbox, text_input, and button
#    create variables that we can use in Python logic.
#
# 4. A dashboard usually combines:
#    - filters
#    - tables
#    - metrics
#    - charts
#    - input forms
#
# 5. This app is not truly saving the new player permanently.
#    It only shows the updated table for that run.
#    Permanent saving would require:
#    - a CSV file update
#    - session_state
#    - or a database
#
# Good spots to pause and explain:
#
# - After st.dataframe(players):
#   "We loaded and displayed data."
#
# - After team filtering:
#   "The dropdown controls what appears on the page."
#
# - After metrics:
#   "Dashboards summarize the most important information first."
#
# - After the chart:
#   "Charts help us compare faster than raw tables."
#
# - After Add Player:
#   "Apps are not only for viewing data; they can collect it too."
#
# Great closing question for students:
# "What else could we add?"
# Possible answers:
# - batting average
# - pitching stats
# - standings
# - MVP score
# - player search
# - file upload


# What else should we add to this??