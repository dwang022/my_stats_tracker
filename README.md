\usepackage{hyperref}
\section*{AI Sports Stats Tracker \& Trading Card Generator}

An interactive full-stack-style sports analytics application built with Python and Streamlit that allows users to:

\begin{itemize}
    \item Track and analyze basketball, football, and baseball statistics
    \item Compare performances to real professional athletes using similarity algorithms
    \item Generate AI-powered custom sports trading cards
    \item Create downloadable personalized player cards with dynamic stats and pro comparisons
\end{itemize}

\section*{Features}

\subsection*{Sports Stat Tracking}
\begin{itemize}
    \item Basketball stat tracking and analytics
    \item Football stat tracking and player comparison
    \item Baseball stat tracking
    \item Game logging and performance summaries
\end{itemize}

\subsection*{Pro Player Comparison Engine}
Uses weighted statistical similarity formulas to compare user performance against real professional athletes:
\begin{itemize}
    \item NBA player comparisons
    \item NFL player comparisons
    \item Position-specific football comparisons
\end{itemize}

\subsection*{AI Trading Card Generator}
Generate custom AI-enhanced sports trading cards featuring:
\begin{itemize}
    \item Personalized stats
    \item Player images with automatic background removal
    \item AI-generated stadium/card backgrounds using DALL·E 3
    \item Dynamic pro-player comparisons
    \item Team-inspired visual themes
    \item Downloadable high-resolution card output
\end{itemize}

\section*{Sample Trading Card}

\begin{center}
    \includegraphics[width=0.45\textwidth]{sample_card.png}
\end{center}

\section*{Tech Stack}

\subsection*{Frontend}
\begin{itemize}
    \item Streamlit
\end{itemize}

\subsection*{Backend / Data}
\begin{itemize}
    \item Python
    \item Pandas
    \item SQLite
\end{itemize}

\subsection*{APIs \& AI}
\begin{itemize}
    \item OpenAI API (DALL·E 3)
    \item Anthropic API
\end{itemize}

\subsection*{Computer Vision / Imaging}
\begin{itemize}
    \item Pillow (PIL)
    \item rembg
    \item onnxruntime
\end{itemize}

\subsection*{Sports Data}
\begin{itemize}
    \item nba\_api
    \item nflreadpy
    \item pybaseball
\end{itemize}

\section*{How It Works}

\subsection*{Trading Card Pipeline}
\begin{enumerate}
    \item User uploads player image
    \item Background is removed using rembg
    \item DALL·E 3 generates a custom sports-card-style background
    \item Player stats and pro comparisons are calculated
    \item PIL composites the final trading card
    \item User downloads the completed card
\end{enumerate}


\section*{Future Improvements}

\begin{itemize}
    \item User authentication
    \item Cloud database integration (Supabase/PostgreSQL)
    \item Persistent user accounts
    \item Mobile-friendly redesign
    \item Build out a coaches view
    \item Custom trading card rarity systems
\end{itemize}
