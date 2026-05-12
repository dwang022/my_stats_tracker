# AI Sports Stats Tracker & Trading Card Generator

An interactive full-stack-style sports analytics application built with Python and Streamlit that allows users to:

- Track and analyze basketball, football, and baseball statistics
- Compare performances to real professional athletes using similarity algorithms
- Generate AI-powered coaching insights and scouting reports
- Create downloadable AI-generated sports trading cards
- Manage roster-wide analytics through a dedicated Coaches View dashboard

---

# Try It Out

🔗 Live App: [Try the App Here](https://mystatstracker.streamlit.app/)

---

# Features

## Multi-Sport Stat Tracking

Track and analyze performance across multiple sports:

### Basketball
- Points, rebounds, assists, steals, blocks, turnovers
- Performance trend graphs
- NBA-adjusted stat normalization

### Football
- Position-specific tracking:
  - QB
  - RB
  - WR/TE
  - Defense
- NFL comparison engine
- Position-based analytics

### Baseball
- Hitting analytics
- Pitching analytics
- Advanced batting and pitching metrics
- MLB player comparisons

---

# Coaches View Dashboard

A roster-wide analytics dashboard built for coaches and trainers.

Features include:

- Team game entry system
- Multi-player stat tracking
- Position-specific stat forms
- Roster performance summaries
- Team leaderboards
- Performance trend visualizations
- Athlete comparison tools
- AI-generated roster analysis

Designed to simulate a lightweight sports analytics platform for youth, high school, and club sports organizations.

---

# AI Coaching System

Integrated AI coaching tools powered by Anthropic and OpenAI APIs.

Features include:

- Personalized player feedback
- AI-generated performance analysis
- Strengths and weaknesses summaries
- Development recommendations
- Training suggestions
- Team-level roster reports
- Automated coaching insights from tracked stats

The AI system dynamically adapts its analysis based on:
- Sport
- Position
- Statistical trends
- Recent performance history

---

# Pro Player Comparison Engine

Uses weighted statistical similarity formulas to compare user performance against real professional athletes.

### Supported Comparisons

- NBA player comparisons
- MLB hitter comparisons
- MLB pitcher comparisons
- NFL position-specific comparisons

The system calculates similarity scores using normalized statistical distance metrics.

---

# AI Trading Card Generator

Generate custom AI-enhanced sports trading cards featuring:

- Personalized stats
- Player images with automatic background removal
- AI-generated sports-card-style backgrounds using DALL·E 3
- Dynamic performance-based card themes
- Pro-player comparison integration
- Team-inspired visual aesthetics
- Downloadable high-resolution cards

### Card Features

- Dynamic rarity-style themes
- AI-generated premium backgrounds
- Automatic player cutouts
- Stat overlays
- Personalized layouts
- Position and team customization

---

# Sample Trading Card

![Sample Card](sample_card.png)

---

# Tech Stack

## Frontend

- Streamlit

## Backend / Data

- Python
- Pandas
- SQLite

## APIs & AI

- OpenAI API (DALL·E 3)
- Anthropic API

## Computer Vision / Imaging

- Pillow (PIL)
- rembg
- onnxruntime

## Sports Data

- nba_api
- nflreadpy
- pybaseball

---

# How It Works

## Trading Card Pipeline

1. User uploads player image
2. Background is removed using rembg
3. DALL·E 3 generates a custom sports-card-style background
4. Player stats and pro comparisons are calculated
5. Dynamic card themes are generated from performance data
6. PIL composites the final trading card
7. User downloads the completed card

---

# User System

The app includes a lightweight user ID system that:

- Separates player data by user
- Stores persistent stat history locally
- Supports coach/team workflows
- Allows multiple users to use the same deployed app independently

---

# Future Improvements

- Full authentication system
- Cloud database integration (Supabase/PostgreSQL)
- Team and organization accounts
- Mobile-friendly redesign
- Live in-game stat tracking
- AI-generated training plans
- AI scouting reports
- Social sharing and highlight generation
