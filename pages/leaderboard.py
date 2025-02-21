import streamlit as st
from french_tutor import FrenchTutor
import pandas as pd

st.set_page_config(
    page_title="French Tutor - Leaderboard",
    page_icon="🏆",
    layout="wide"
)

# Add navigation menu in sidebar
with st.sidebar:
    selected = st.selectbox(
        "📚 Navigation",
        options=["🎮 Practice", "🏆 Leaderboard", "📊 History"],
        index=1,  # Default to Leaderboard
        key="nav_select"
    )
    
    if selected != "🏆 Leaderboard":
        if selected == "🎮 Practice":
            st.switch_page("french_tutor.py")
        else:  # History
            st.switch_page("pages/history.py")

st.title("🏆 French Masters Leaderboard")

tutor = FrenchTutor()
leaderboard = tutor.get_leaderboard()

if leaderboard:
    df = pd.DataFrame(leaderboard)
    
    # Add medal emojis for top 3
    if len(df) > 0:
        df['Rank'] = range(1, len(df) + 1)
        df['Rank'] = df['Rank'].apply(lambda x: 
            "🥇 " + str(x) if x == 1 else
            "🥈 " + str(x) if x == 2 else
            "🥉 " + str(x) if x == 3 else
            "👏 " + str(x)
        )
    
    st.dataframe(
        df,
        column_config={
            "Rank": st.column_config.TextColumn("Rank", width=70),
            "Username": st.column_config.TextColumn("User", width=150),
            "Words Mastered": st.column_config.NumberColumn("Mastered", width=100),
            "Total Progress": st.column_config.TextColumn("Progress", width=100),
            "Rating": st.column_config.TextColumn("Rating", width=100)
        },
        hide_index=True
    ) 