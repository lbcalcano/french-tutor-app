import streamlit as st
from french_tutor import FrenchTutor

st.set_page_config(
    page_title="French Tutor - History",
    page_icon="📊",
    layout="wide"
)

# Add navigation
with st.sidebar:
    st.write("📚 Navigation")
    if st.button("🎮 Practice", use_container_width=True):
        st.switch_page("french_tutor.py")
    if st.button("🏆 Leaderboard", use_container_width=True):
        st.switch_page("pages/leaderboard.py")
    if st.button("📊 History", use_container_width=True):
        st.switch_page("pages/history.py")

st.title("📊 Practice History")

tutor = FrenchTutor()
if 'username' in st.session_state:
    history = tutor.get_session_history(st.session_state.username)
    if history:
        df = pd.DataFrame(history)
        st.dataframe(
            df,
            column_config={
                "Date": st.column_config.TextColumn("Date", width=150),
                "Words Attempted": st.column_config.NumberColumn("Attempted", width=100),
                "Words Correct": st.column_config.NumberColumn("Correct", width=100),
                "Perfect Words": st.column_config.NumberColumn("Perfect", width=100),
                "Rating": st.column_config.TextColumn("Rating", width=100)
            },
            hide_index=True
        )
    else:
        st.info("No practice sessions yet. Start practicing to see your history!")
else:
    st.warning("Please log in to view your practice history") 