"""
ai_coach.py  —  Drop-in AI Coach module for my_stats_tracker.py
================================================================
SETUP
-----
1.  Copy this file into the same folder as my_stats_tracker.py
2.  Add to your secrets.toml (or Streamlit Cloud secrets):
        ANTHROPIC_KEY = "sk-ant-..."
3.  In my_stats_tracker.py, add near the top (after your other imports):
        from ai_coach import render_ai_coach_section
4.  Call it inside each sport page — see "WHERE TO PASTE" comments below.

WHERE TO PASTE
--------------
Basketball page  (after the "Performance Trends" section):
    render_ai_coach_section("Basketball", st.session_state.my_games)

Baseball hitting page (after trend chart):
    render_ai_coach_section("Baseball Hitting", st.session_state.my_baseball_games)

Baseball pitching page (after trend chart):
    render_ai_coach_section("Baseball Pitching", st.session_state.my_pitching_games)

Football page (after trend chart, inside the football_games block):
    render_ai_coach_section(f"Football {football_mode}", st.session_state[session_key])

Coaches View — comps_tab (after the bar chart):
    if profile is not None:
        render_ai_coach_section(profile["Sport"], coach_df[coach_df["Player"] == selected_player])
"""

import streamlit as st
import anthropic
import pandas as pd
import json


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client():
    """Return an Anthropic client using the key stored in st.secrets."""
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_KEY"])


def _recent_games(df: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    """Return the n most recent rows, sorted by Date descending."""
    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date", ascending=False)
    return df.head(n)


def _df_to_text(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a compact readable string for the prompt."""
    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    # Drop columns that are all zero or all empty to keep prompt tight
    num_cols = df.select_dtypes(include="number").columns
    zero_cols = [c for c in num_cols if df[c].sum() == 0]
    df = df.drop(columns=zero_cols, errors="ignore")
    return df.to_string(index=False)


def _compute_averages(df: pd.DataFrame) -> dict:
    """Return a dict of column -> mean for numeric columns."""
    num = df.select_dtypes(include="number")
    return {col: round(float(num[col].mean()), 2) for col in num.columns if num[col].sum() != 0}


def _trend_direction(df: pd.DataFrame, col: str) -> str:
    """Return 'improving', 'declining', or 'stable' for a stat over recent games."""
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values("Date")
    if col not in df.columns or len(df) < 4:
        return "stable"
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(series) < 4:
        return "stable"
    first_half = series.iloc[: len(series) // 2].mean()
    second_half = series.iloc[len(series) // 2 :].mean()
    if first_half == 0:
        return "stable"
    pct = (second_half - first_half) / abs(first_half)
    if pct > 0.08:
        return "improving"
    if pct < -0.08:
        return "declining"
    return "stable"


# ---------------------------------------------------------------------------
# Sport-specific prompt builders
# ---------------------------------------------------------------------------

def _build_prompt(sport: str, recent_df: pd.DataFrame, averages: dict, trends: dict) -> str:
    game_log_text = _df_to_text(recent_df)
    averages_text = json.dumps(averages, indent=2)
    trends_text   = json.dumps(trends,   indent=2)

    base = f"""You are an elite sports performance coach with decades of experience developing athletes at every level — youth, high school, college, and professional.

A player has shared their recent {sport} game logs with you. Your job is to give them a sharp, personalized coaching report — the kind of insight a real coach gives in a 1-on-1 session, not generic advice.

RECENT GAME LOG (last 8 games):
{game_log_text}

SEASON AVERAGES:
{averages_text}

STAT TRENDS (improving / stable / declining):
{trends_text}

---
Write a coaching report with EXACTLY these four sections. Use plain language the player can act on TODAY.

## 🔥 What's Working
2-3 specific strengths backed by their actual numbers. Be precise — mention the stat values.

## ⚠️ Areas to Address
2-3 specific weaknesses or concerning trends. Don't sugarcoat. Reference the actual numbers and what they signal tactically.

## 📈 This Week's Focus
One single, concrete priority for their next practice or game. Make it actionable and specific to their data — not generic advice like "work on defense."

## 💡 Pro Insight
One advanced observation a typical coach would miss — a pattern in the data, a correlation between two stats, or a nuance about their game style that reveals something meaningful about how they play.

Keep the total report under 350 words. Be direct. Sound like a coach who has studied their film, not a chatbot."""

    return base


def _build_coach_roster_prompt(sport: str, player: str, recent_df: pd.DataFrame, averages: dict, trends: dict) -> str:
    game_log_text = _df_to_text(recent_df)
    averages_text = json.dumps(averages, indent=2)
    trends_text   = json.dumps(trends,   indent=2)

    return f"""You are an elite {sport} coach evaluating a player on your roster for a team performance report.

PLAYER: {player}
SPORT: {sport}

RECENT GAME LOG (last 8 games):
{game_log_text}

SEASON AVERAGES:
{averages_text}

STAT TRENDS (improving / stable / declining):
{trends_text}

---
Write a concise scouting-style coaching report with EXACTLY these sections:

## 📋 Player Summary
One paragraph. Who is this player? What kind of player do the numbers show? Mention their best and worst stats by value.

## ✅ Strengths
2 bullet points. Specific, number-backed.

## 🔧 Development Areas
2 bullet points. Honest assessment. Reference the actual numbers.

## 🏆 Role Recommendation
Based purely on the stats, what role should this player fill? (e.g. "primary scorer", "defensive stopper", "depth piece", "featured back") Explain in 1-2 sentences.

Under 250 words. Sound like a coach writing a scouting report, not a chatbot."""


# ---------------------------------------------------------------------------
# Public render functions
# ---------------------------------------------------------------------------

def render_ai_coach_section(sport: str, df: pd.DataFrame, player_name: str = None):
    """
    Render the AI Coach section for a player's own stats page.

    Parameters
    ----------
    sport       : e.g. "Basketball", "Baseball Hitting", "Football QB"
    df          : The player's game log DataFrame
    player_name : Optional — shown in the header if provided
    """
    st.markdown("---")
    st.subheader("🤖 AI Coach Report")

    if df is None or len(df) < 2:
        st.info("Log at least 2 games to unlock your personalized AI coaching report.")
        return

    label = f"Get My AI Coaching Report ({sport})"
    if player_name:
        label = f"Get AI Coaching Report for {player_name}"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(
            "Claude analyzes your last 8 games, spots trends, and gives you the same "
            "feedback a real coach would give in a 1-on-1 session."
        )
    with col2:
        generate = st.button(label, use_container_width=True, key=f"ai_coach_{sport}_{player_name or 'self'}")

    if not generate:
        return

    recent = _recent_games(df, n=8)
    averages = _compute_averages(recent)

    # Compute trends for the most meaningful stats per sport
    trend_cols_map = {
        "Basketball":        ["Points", "Rebounds", "Assists", "Steals", "Blocks", "Turnovers"],
        "Baseball Hitting":  ["Hits", "Home Runs", "RBIs", "Walks", "Strikeouts", "Stolen Bases"],
        "Baseball Pitching": ["Innings Pitched", "Strikeouts", "Walks", "Earned Runs", "Hits Allowed"],
        "Football QB":       ["Passing Yards", "Passing TDs", "Interceptions", "Rushing Yards"],
        "Football RB":       ["Rushing Yards", "Rushing TDs", "Receptions", "Receiving Yards"],
        "Football WR/TE":    ["Receiving Yards", "Receiving TDs", "Receptions", "Targets"],
        "Football Defense":  ["Tackles", "Sacks", "Interceptions", "Passes Defended"],
        # Coach roster sports
        "Baseball Hitting":  ["Hits", "Home Runs", "RBIs", "Walks", "Strikeouts"],
        "Baseball Pitching": ["Innings Pitched", "Strikeouts", "Walks", "Earned Runs"],
        "Football":          ["Passing Yards", "Rushing Yards", "Receiving Yards", "Tackles", "Sacks"],
    }

    trend_cols = trend_cols_map.get(sport, list(averages.keys())[:6])
    trends = {
        col: _trend_direction(recent, col)
        for col in trend_cols
        if col in recent.columns
    }

    prompt = _build_prompt(sport, recent, averages, trends)

    with st.spinner("Coach is reviewing your film..."):
        try:
            client = _get_client()
            report_text = ""

            # Stream the response for a more dynamic feel
            report_placeholder = st.empty()
            
            
            with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=700,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    report_text += text
                    report_placeholder.markdown(report_text)

        except Exception as e:
            st.error(f"Could not generate report: {e}")
            return

    # Copy button
    st.download_button(
        label="📋 Download Report",
        data=report_text,
        file_name=f"coaching_report_{sport.replace(' ', '_').lower()}.txt",
        mime="text/plain",
    )

    # Trend badges below the report
    st.markdown("#### Stat Trends")
    badge_cols = st.columns(min(len(trends), 4))
    icons = {"improving": "📈", "declining": "📉", "stable": "➡️"}
    colors = {"improving": "green", "declining": "red", "stable": "gray"}

    for i, (stat, direction) in enumerate(trends.items()):
        with badge_cols[i % len(badge_cols)]:
            st.markdown(
                f"""<div style="
                    border-radius: 10px;
                    padding: 8px 12px;
                    background: #f0f2f6;
                    text-align: center;
                    margin-bottom: 6px;
                ">
                <span style="font-size: 18px;">{icons[direction]}</span><br>
                <b style="font-size: 12px; color: {colors[direction]};">{direction.upper()}</b><br>
                <span style="font-size: 11px; color: #555;">{stat}</span>
                </div>""",
                unsafe_allow_html=True,
            )


def render_coach_roster_ai_report(sport: str, player: str, df: pd.DataFrame):
    """
    Roster-level AI report for the Coaches View — scouting-style.
    Call this inside the comps_tab or depth_chart_tab after showing comps.

    Parameters
    ----------
    sport  : e.g. "Basketball", "Baseball Hitting", "Football"
    player : player name string
    df     : filtered DataFrame for just this player's games
    """
    st.markdown("---")
    st.subheader(f"🤖 AI Scouting Report — {player}")

    if df is None or len(df) < 2:
        st.info("Need at least 2 logged games to generate a scouting report.")
        return

    if st.button(f"Generate Scouting Report for {player}", key=f"scout_{sport}_{player}"):
        recent   = _recent_games(df, n=8)
        averages = _compute_averages(recent)

        trend_cols = list(averages.keys())[:7]
        trends = {
            col: _trend_direction(recent, col)
            for col in trend_cols
            if col in recent.columns
        }

        prompt = _build_coach_roster_prompt(sport, player, recent, averages, trends)

        with st.spinner(f"Generating scouting report for {player}..."):
            try:
                client = _get_client()
                report_text = ""
                placeholder = st.empty()

                with client.messages.stream(
                    model="claude-sonnet-4-6",
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    for text in stream.text_stream:
                        report_text += text
                        placeholder.markdown(report_text)

            except Exception as e:
                st.error(f"Could not generate scouting report: {e}")
