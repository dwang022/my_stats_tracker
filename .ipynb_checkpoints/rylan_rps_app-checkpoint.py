import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="Rylan Player Score Dashboard",
    page_icon="⚾",
    layout="wide"
)

# DATA SOURCES
BATTING_STATS_URL = "https://drive.google.com/uc?export=download&id=1bTKGlowoa6BVkHgzQKuW107anXydXXzf"
FIELDING_STATS_URL = "https://drive.google.com/uc?export=download&id=1GTRCJ2I2bLO0plUBGeDKR4G6sR11Ghze"
PITCHING_STATS_URL = "https://drive.google.com/uc?export=download&id=1B4N42kzC-UsMrN3chLWENnV6IcjeHG0d"


# HELPER FUNCTIONS
def safe_round_df(df, digits=3):
    df = df.copy()
    num_cols = df.select_dtypes(include="number").columns
    df[num_cols] = df[num_cols].round(digits)
    return df


def to_csv_download(df):
    return safe_round_df(df).to_csv(index=False).encode("utf-8")


def add_percentile(df):
    df = df.copy()
    df["rps_percentile"] = df["rps"].rank(pct=True) * 100
    return df


def make_horizontal_bar_chart(df, x_col, y_col, title=""):
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(f"{x_col}:N", axis=alt.Axis(labelAngle=0, title="Component")),
            y=alt.Y(f"{y_col}:Q", title="Contribution"),
            tooltip=[x_col, y_col]
        )
        .properties(title=title, height=350)
    )
    return chart


# LOAD BATTERS
@st.cache_data
def load_batters():
    batting_df = pd.read_csv(BATTING_STATS_URL)
    fielding_df = pd.read_csv(FIELDING_STATS_URL)

    fielding_df = fielding_df[["id", "total_runs"]].rename(
        columns={"id": "player_id", "total_runs": "fielding_run_value"}
    )

    batter_df = pd.merge(batting_df, fielding_df, on="player_id", how="left")
    batter_df = batter_df.fillna(0)

    batter_df["rps"] = (
        16.7 * batter_df["on_base_plus_slg"]
        + 0.4 * batter_df["home_run"]
        + 11 * batter_df["on_base_percent"]
        + 11 * batter_df["batting_avg"]
        - 0.08 * batter_df["b_gnd_into_dp"]
        + 0.5 * batter_df["fielding_run_value"]
    )

    batter_df["rps_rank"] = batter_df["rps"].rank(method="dense", ascending=False).astype(int)
    batter_df = add_percentile(batter_df)

    return batter_df.sort_values("rps", ascending=False).reset_index(drop=True)


# LOAD PITCHERS
@st.cache_data
def load_pitchers():
    pitching_df = pd.read_csv(PITCHING_STATS_URL)

    pitching_df["innings_pitched"] = (
        (pitching_df["p_formatted_ip"] // 1)
        + (pitching_df["p_formatted_ip"] % 1) * 10 / 3
    )

    pitching_df["walk_hit_ip"] = (
        pitching_df["walk"] + pitching_df["hit"]
    ) / pitching_df["innings_pitched"]

    pitching_df["rps"] = (
        -35 * pitching_df["walk_hit_ip"]
        + 4.9 * pitching_df["k_percent"]
        - 4 * pitching_df["bb_percent"]
        - 5 * pitching_df["babip"]
        - 5 * pitching_df["p_era"]
        + 1.7 * pitching_df["p_gnd_into_dp"]
        - 0.4 * pitching_df["barrel_batted_rate"]
        - 0.1 * pitching_df["hard_hit_percent"]
    ) / 83 * 33

    pitching_df["rps_rank"] = pitching_df["rps"].rank(method="dense", ascending=False).astype(int)
    pitching_df = add_percentile(pitching_df)

    return pitching_df.sort_values("rps", ascending=False).reset_index(drop=True)


batters = load_batters()
pitchers = load_pitchers()

BATTER_COLS = [
    "last_name, first_name",
    "rps_rank",
    "rps",
    "on_base_plus_slg",
    "on_base_percent",
    "batting_avg",
    "home_run",
    "b_gnd_into_dp",
    "fielding_run_value",
    "rps_percentile"
]

PITCHER_COLS = [
    "last_name, first_name",
    "rps_rank",
    "rps",
    "walk_hit_ip",
    "k_percent",
    "bb_percent",
    "p_era",
    "babip",
    "p_gnd_into_dp",
    "barrel_batted_rate",
    "hard_hit_percent",
    "rps_percentile"
]

# HEADER
st.title("⚾ Rylan Player Score Dashboard")
st.caption("Player rankings using the Rylan Player Score formulas.")

with st.expander("Show RPS formulas"):
    st.markdown("""
**Batters**

RPS = 16.7×OPS + 0.4×HR + 11×OBP + 11×AVG − 0.08×GIDP + 0.5×Fielding Run Value

**Pitchers**

RPS = ((−35×WHIP) + (4.9×K%) − (4×BB%) − (5×BABIP) − (5×ERA)
+ (1.7×GIDP induced) − (0.4×Barrel%) − (0.1×Hard-Hit%)) / 83 × 33
""")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Top Batter", batters.iloc[0]["last_name, first_name"], f"{batters.iloc[0]['rps']:.2f}")
c2.metric("Top Pitcher", pitchers.iloc[0]["last_name, first_name"], f"{pitchers.iloc[0]['rps']:.2f}")
c3.metric("Total Batters", len(batters))
c4.metric("Total Pitchers", len(pitchers))

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Batters", "Pitchers", "Compare Players"])

# BATTERS TAB
with tab1:
    st.subheader("Top Batters")

    col1, col2 = st.columns([1, 3])
    top_n_b = col1.slider("Top N", 10, min(100, len(batters)), 25, key="batter_slider")
    search_b = col2.text_input("Search batter", key="batter_search")

    df_b = batters.copy()
    if search_b:
        df_b = df_b[df_b["last_name, first_name"].str.contains(search_b, case=False, na=False)]

    display_b = df_b.head(top_n_b)

    st.dataframe(
        safe_round_df(display_b[BATTER_COLS]),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download batter CSV",
        data=to_csv_download(display_b[BATTER_COLS]),
        file_name="batter_rps.csv",
        mime="text/csv",
        key="download_batters"
    )

    st.markdown("### Batter Profile")
    batter_options = df_b["last_name, first_name"].tolist()
    player_b = st.selectbox("Select batter", batter_options, key="batter_select")

    row = df_b[df_b["last_name, first_name"] == player_b].iloc[0]

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("RPS", f"{row['rps']:.2f}")
    p2.metric("Rank", int(row["rps_rank"]))
    p3.metric("Percentile", f"{row['rps_percentile']:.1f}")
    p4.metric("OPS", f"{row['on_base_plus_slg']:.3f}")
    p5.metric("AVG", f"{row['batting_avg']:.3f}")

    breakdown_b = pd.DataFrame({
        "Metric": ["OPS", "HR", "OBP", "AVG", "GIDP", "Fielding"],
        "Contribution": [
            16.7 * row["on_base_plus_slg"],
            0.4 * row["home_run"],
            11 * row["on_base_percent"],
            11 * row["batting_avg"],
            -0.08 * row["b_gnd_into_dp"],
            0.5 * row["fielding_run_value"]
        ]
    })

    st.altair_chart(
        make_horizontal_bar_chart(breakdown_b, "Metric", "Contribution", "Batter RPS Breakdown"),
        use_container_width=True
    )

# PITCHERS TAB
with tab2:
    st.subheader("Top Pitchers")

    col1, col2 = st.columns([1, 3])
    top_n_p = col1.slider("Top N", 10, min(100, len(pitchers)), 25, key="pitcher_slider")
    search_p = col2.text_input("Search pitcher", key="pitcher_search")

    df_p = pitchers.copy()
    if search_p:
        df_p = df_p[df_p["last_name, first_name"].str.contains(search_p, case=False, na=False)]

    display_p = df_p.head(top_n_p)

    st.dataframe(
        safe_round_df(display_p[PITCHER_COLS]),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download pitcher CSV",
        data=to_csv_download(display_p[PITCHER_COLS]),
        file_name="pitcher_rps.csv",
        mime="text/csv",
        key="download_pitchers"
    )

    st.markdown("### Pitcher Profile")
    pitcher_options = df_p["last_name, first_name"].tolist()
    player_p = st.selectbox("Select pitcher", pitcher_options, key="pitcher_select")

    row = df_p[df_p["last_name, first_name"] == player_p].iloc[0]

    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("RPS", f"{row['rps']:.2f}")
    p2.metric("Rank", int(row["rps_rank"]))
    p3.metric("Percentile", f"{row['rps_percentile']:.1f}")
    p4.metric("WHIP", f"{row['walk_hit_ip']:.3f}")
    p5.metric("ERA", f"{row['p_era']:.2f}")

    breakdown_p = pd.DataFrame({
        "Metric": ["WHIP", "K%", "BB%", "BABIP", "ERA", "GIDP", "Barrel%", "HardHit%"],
        "Contribution": [
            -35 * row["walk_hit_ip"],
            4.9 * row["k_percent"],
            -4 * row["bb_percent"],
            -5 * row["babip"],
            -5 * row["p_era"],
            1.7 * row["p_gnd_into_dp"],
            -0.4 * row["barrel_batted_rate"],
            -0.1 * row["hard_hit_percent"]
        ]
    })

    st.altair_chart(
        make_horizontal_bar_chart(breakdown_p, "Metric", "Contribution", "Pitcher RPS Breakdown"),
        use_container_width=True
    )

# COMPARE TAB
with tab3:
    st.subheader("Compare Players")

    c1, c2 = st.columns(2)

    batters_compare = c1.multiselect(
        "Batters",
        batters["last_name, first_name"].tolist(),
        default=batters["last_name, first_name"].head(5).tolist(),
        key="batters_compare"
    )

    pitchers_compare = c2.multiselect(
        "Pitchers",
        pitchers["last_name, first_name"].tolist(),
        default=pitchers["last_name, first_name"].head(5).tolist(),
        key="pitchers_compare"
    )

    if batters_compare:
        st.markdown("### Batter Comparison")
        st.dataframe(
            safe_round_df(
                batters[batters["last_name, first_name"].isin(batters_compare)][BATTER_COLS]
            ),
            use_container_width=True,
            hide_index=True
        )

    if pitchers_compare:
        st.markdown("### Pitcher Comparison")
        st.dataframe(
            safe_round_df(
                pitchers[pitchers["last_name, first_name"].isin(pitchers_compare)][PITCHER_COLS]
            ),
            use_container_width=True,
            hide_index=True
        )

st.markdown("---")
st.caption("Built from the same Google Drive CSV sources and formulas used in Rylan's notebook.")
