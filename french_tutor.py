import os
import sqlite3
import hashlib
import time
from datetime import datetime
import streamlit as st
import csv
import random
import json
from gtts import gTTS
import tempfile
import base64
import pandas as pd

class FrenchTutor:
    def __init__(self):
        self.setup_db()
        self.load_words()
        self.check_authentication()
        
        if 'word_stats' not in st.session_state:
            st.session_state.word_stats = self.load_progress()
            
    def setup_db(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "french_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Create progress table
            c.execute('''
                CREATE TABLE IF NOT EXISTS progress
                (user_id TEXT,
                 word TEXT,
                 attempts INTEGER,
                 last_practiced TEXT,
                 PRIMARY KEY (user_id, word))
            ''')
            
            # Create sessions table
            c.execute('''
                CREATE TABLE IF NOT EXISTS sessions
                (user_id TEXT PRIMARY KEY,
                 current_words TEXT,
                 word_count INTEGER,
                 last_updated TEXT)
            ''')
            
            # Create session history table
            c.execute('''
                CREATE TABLE IF NOT EXISTS session_history
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id TEXT,
                 session_date TEXT,
                 words_attempted INTEGER,
                 words_correct INTEGER,
                 perfect_words INTEGER,
                 rating REAL)
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Could not setup database: {str(e)}")

    def check_authentication(self):
        if 'username' not in st.session_state:
            self.show_login()
        
    def show_login(self):
        st.markdown("### 🇫🇷 French Tutor Login")
        
        # Add guest login button with warning
        st.warning("⚠️ Guest progress will be lost when you close the browser", icon="⚠️")
        if st.button("👤 Continue as Guest", use_container_width=True):
            guest_id = f"guest_{int(time.time())}"
            st.session_state.username = guest_id
            st.rerun()
        
        st.write("---")
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            username = st.text_input(
                "Username", 
                key="login_username",
                autocomplete="off",  # Prevent autocomplete
                help="Username is case-sensitive"
            ).strip()  # Remove any whitespace
            
            password = st.text_input(
                "Password", 
                type="password",
                key="login_password",
                autocomplete="off"  # Prevent autocomplete
            ).strip()  # Remove any whitespace
            
            if st.button("Login", key="login_button"):
                if self.verify_credentials(username, password):
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with tab2:
            new_username = st.text_input(
                "Choose Username",
                key="reg_username",
                autocomplete="off"
            ).strip()
            
            new_password = st.text_input(
                "Choose Password",
                type="password",
                key="reg_password",
                autocomplete="off"
            ).strip()
            
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="reg_confirm",
                autocomplete="off"
            ).strip()
            
            if st.button("Register", key="register_button"):
                if self.register_user(new_username, new_password, confirm_password):
                    st.success("Registration successful! Please login.")
                    time.sleep(2)
                    st.rerun()

    def verify_credentials(self, username, password):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "users.db")
            
            if not os.path.exists(db_path):
                st.error("No users database found")
                return False
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
            result = c.fetchone()
            
            if not result:
                return False
            
            stored_hash = result[0]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            conn.close()
            return stored_hash == password_hash
            
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            return False

    def register_user(self, username, password, confirm_password):
        try:
            if not username or not password:
                st.error("Username and password are required")
                return False
            
            if password != confirm_password:
                st.error("Passwords do not match")
                return False
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "users.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            c.execute('''
                CREATE TABLE IF NOT EXISTS users
                (username TEXT PRIMARY KEY,
                 password_hash TEXT,
                 created_at TEXT)
            ''')
            
            c.execute('SELECT username FROM users WHERE username = ?', (username,))
            if c.fetchone():
                st.error("Username already exists")
                conn.close()
                return False
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            c.execute('''
                INSERT INTO users (username, password_hash, created_at)
                VALUES (?, ?, ?)
            ''', (username, password_hash, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            st.error(f"Registration failed: {str(e)}")
            return False

    def load_progress(self):
        try:
            if 'username' not in st.session_state:
                return {}
                
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "french_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            c.execute('SELECT word, attempts FROM progress WHERE user_id = ?', 
                     (st.session_state.username,))
            results = c.fetchall()
            
            conn.close()
            
            return {word: attempts for word, attempts in results}
            
        except Exception as e:
            st.error(f"Could not load progress: {str(e)}")
            return {}

    def save_progress(self):
        try:
            if 'username' not in st.session_state:
                return
                
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "french_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            for word, attempts in st.session_state.word_stats.items():
                c.execute('''
                    INSERT OR REPLACE INTO progress 
                    (user_id, word, attempts, last_practiced)
                    VALUES (?, ?, ?, ?)
                ''', (st.session_state.username, word, attempts, 
                     datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Could not save progress: {str(e)}")

    def load_words(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(script_dir, 'french_words.csv')
            
            with open(csv_path, 'r') as file:
                reader = csv.DictReader(file)
                self.words = [(row['spanish'], row['french']) for row in reader]
        except Exception as e:
            st.error(f"Could not load words: {str(e)}")
            self.words = [("hola", "bonjour")]

    def speak_word(self, word):
        """Generate speech for the French word"""
        try:
            tts = gTTS(text=word, lang='fr')  # Use French language
            audio_bytes = tempfile.NamedTemporaryFile(suffix='.mp3')
            tts.save(audio_bytes.name)
            
            with open(audio_bytes.name, 'rb') as f:
                audio_data = f.read()
            
            audio_bytes.close()
            return audio_data
            
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
            return None

    def is_admin(self, username):
        """Check if user is admin"""
        return username == "admin"  # You can modify this to include more admin users

    def get_user_stats(self):
        """Get statistics for all users"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            users_db = os.path.join(script_dir, "users.db")
            progress_db = os.path.join(script_dir, "french_progress.db")
            
            users_conn = sqlite3.connect(users_db)
            progress_conn = sqlite3.connect(progress_db)
            
            uc = users_conn.cursor()
            pc = progress_conn.cursor()
            
            # Get registered users
            uc.execute('SELECT username, created_at FROM users')
            registered_users = uc.fetchall()
            
            # Get all users' progress
            pc.execute('''
                SELECT user_id, COUNT(DISTINCT word) as words_practiced,
                       COUNT(CASE WHEN attempts = 1 THEN 1 END) as perfect_words,
                       MAX(last_practiced) as last_active
                FROM progress
                GROUP BY user_id
            ''')
            progress_data = pc.fetchall()
            
            # Combine the data
            user_stats = []
            guest_count = 0
            
            for user_id, words, perfect, last_active in progress_data:
                is_guest = user_id.startswith('guest_')
                if is_guest:
                    guest_count += 1
                
                # Calculate rating based on total words in list
                rating = (perfect / len(self.words) * 100) if len(self.words) > 0 else 0
                remaining = len(self.words) - words
                
                user_stats.append({
                    'Username': user_id,
                    'Type': 'Guest' if is_guest else 'Registered',
                    'Words Practiced': words,
                    'Perfect Words': perfect,
                    'Remaining Words': remaining,
                    'Rating': f"{rating:.1f}%",
                    'Last Active': datetime.fromisoformat(last_active).strftime('%Y-%m-%d %H:%M')
                })
            
            users_conn.close()
            progress_conn.close()
            
            return {
                'user_stats': user_stats,
                'total_registered': len(registered_users),
                'total_guests': guest_count
            }
            
        except Exception as e:
            st.error(f"Could not get user statistics: {str(e)}")
            return None

    def save_session_history(self):
        try:
            if 'username' not in st.session_state:
                return
                
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "french_progress.db")
            
            # Calculate session stats
            words_attempted = len(st.session_state.current_words)
            words_correct = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] <= 2])
            perfect_words = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] == 1])
            rating = (perfect_words / len(self.words) * 100) if len(self.words) > 0 else 0
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT INTO session_history 
                (user_id, session_date, words_attempted, words_correct, perfect_words, rating)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (st.session_state.username, datetime.now().isoformat(), 
                 words_attempted, words_correct, perfect_words, rating))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Could not save session history: {str(e)}")

    def get_session_history(self, username):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, "french_progress.db")
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT session_date, words_attempted, words_correct, perfect_words, rating
                FROM session_history
                WHERE user_id = ?
                ORDER BY session_date DESC
            ''', (username,))
            
            results = c.fetchall()
            conn.close()
            
            return [{
                'Date': datetime.fromisoformat(date).strftime('%Y-%m-%d %H:%M'),
                'Words Attempted': attempted,
                'Words Correct': correct,
                'Perfect Words': perfect,
                'Rating': f"{rating:.1f}%"
            } for date, attempted, correct, perfect, rating in results]
            
        except Exception as e:
            st.error(f"Could not get session history: {str(e)}")
            return []

def main():
    st.set_page_config(
        page_title="French Tutor",
        page_icon="🇫🇷",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        },
        layout="wide"
    )
    
    # Initialize app
    tutor = FrenchTutor()
    
    # Initialize session state variables
    if 'current_word' not in st.session_state:
        st.session_state.current_word = None
    if 'current_words' not in st.session_state:
        st.session_state.current_words = []
    if 'word_count' not in st.session_state:
        st.session_state.word_count = 0
    if 'current_audio' not in st.session_state:
        st.session_state.current_audio = None
    
    if 'username' in st.session_state:
        st.title("🇫🇷 French Tutor")
    
    # Add mobile instructions
    if st.session_state.get('first_visit', True):
        st.info("📱 On mobile devices: Tap 'Play Word' to hear the pronunciation. Make sure your sound is on!")
        st.session_state.first_visit = False
    
    if 'username' not in st.session_state:
        return
        
    # Sidebar with statistics
    with st.sidebar:
        # Add logout button at the top
        if 'username' in st.session_state:
            if st.button("🚪 Logout", key="logout_button"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
        st.header("Progress")
        total_words = len(tutor.words)
        completed = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] <= 2])
        perfect = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] == 1])
        
        # Calculate rating based on total words in list
        rating_percentage = (perfect / total_words * 100) if total_words > 0 else 0
        remaining_words = total_words - len(st.session_state.word_stats)
        
        # Display rating with appropriate emoji
        if rating_percentage >= 90:
            rating_emoji = "🏆"
        elif rating_percentage >= 80:
            rating_emoji = "🥇"
        elif rating_percentage >= 70:
            rating_emoji = "🥈"
        elif rating_percentage >= 60:
            rating_emoji = "🥉"
        else:
            rating_emoji = "📚"
            
        st.write(f"📊 Rating: {rating_emoji} {rating_percentage:.1f}%")
        st.write(f"📚 Total words: {total_words}")
        st.write(f"✅ Completed: {completed}")
        st.write(f"⭐ Perfect first try: {perfect}")
        st.write(f"📝 Remaining: {remaining_words}")
        
        # Add progress bar
        st.progress(rating_percentage / 100)
        
        # Add rating explanation
        with st.expander("About Rating"):
            st.write("""
            - 🏆 90-100%: Master
            - 🥇 80-89%: Expert
            - 🥈 70-79%: Advanced
            - 🥉 60-69%: Intermediate
            - 📚 0-59%: Learning
            
            Only words answered correctly on first try count towards your rating.
            """)

    # Add admin dashboard
    if tutor.is_admin(st.session_state.username):
        st.write("---")
        st.subheader("👑 Admin Dashboard")
        
        stats = tutor.get_user_stats()
        if stats:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Users", stats['total_registered'] + stats['total_guests'])
            with col2:
                st.metric("Registered Users", stats['total_registered'])
            with col3:
                st.metric("Guest Users", stats['total_guests'])
            
            st.write("---")
            st.write("User Details:")
            
            # Create DataFrame for user stats
            df = pd.DataFrame(stats['user_stats'])
            
            # Sort by Rating (descending)
            df['Rating'] = df['Rating'].str.rstrip('%').astype(float)
            df = df.sort_values('Rating', ascending=False)
            df['Rating'] = df['Rating'].apply(lambda x: f"{x:.1f}%")
            
            # Display the DataFrame
            st.dataframe(
                df,
                column_config={
                    "Username": st.column_config.TextColumn("User", width=150),
                    "Type": st.column_config.TextColumn("Type", width=100),
                    "Words Practiced": st.column_config.NumberColumn("Words", width=80),
                    "Perfect Words": st.column_config.NumberColumn("Perfect", width=80),
                    "Remaining Words": st.column_config.NumberColumn("Remaining Words", width=100),
                    "Rating": st.column_config.TextColumn("Rating", width=100),
                    "Last Active": st.column_config.TextColumn("Last Active", width=150)
                },
                hide_index=True
            )

    # Main practice area
    if 'practice_mode' not in st.session_state:
        st.session_state.practice_mode = False
    
    if not st.session_state.practice_mode:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start New Practice"):
                available_words = [w for w in tutor.words if w[0] not in st.session_state.word_stats]
                st.session_state.current_words = random.sample(
                    available_words,
                    len(available_words)
                )
                st.session_state.practice_mode = True
                st.session_state.word_count = 0
                st.rerun()
        
        with col2:
            if st.button("Practice Wrong Words"):
                wrong_words = [w for w in tutor.words if w[0] in st.session_state.word_stats 
                             and st.session_state.word_stats[w[0]] > 1]
                if wrong_words:
                    st.session_state.current_words = random.sample(
                        wrong_words,
                        len(wrong_words)
                    )
                    st.session_state.practice_mode = True
                    st.session_state.word_count = 0
                    st.rerun()
                else:
                    st.warning("No words to practice!")
    
    else:  # Practice mode
        if not st.session_state.current_words:
            st.session_state.practice_mode = False
            st.rerun()
            
        if st.session_state.current_word is None:
            st.session_state.current_word = st.session_state.current_words[st.session_state.word_count]
            st.session_state.attempts = 0
            st.session_state.current_audio = None
            st.session_state.show_hint = False
            
        # Display progress
        total_practice_words = len(st.session_state.current_words)
        st.write(f"Word {st.session_state.word_count + 1} of {total_practice_words}")
        
        # Display Spanish word
        st.markdown(f"### 🇪🇸 Spanish: {st.session_state.current_word[0]}")
        
        # Only show hint button after first wrong attempt
        if st.session_state.attempts == 1:
            if st.button("💡 Hint (Listen to French pronunciation)"):
                st.session_state.show_hint = True
                st.session_state.current_audio = tutor.speak_word(st.session_state.current_word[1])
                st.rerun()
        
        # Only show audio after wrong attempt or hint
        if (st.session_state.attempts > 0 or st.session_state.get('show_hint', False)) and st.session_state.current_audio is not None:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown("### 🔊")
            with col2:
                audio_html = f'''
                    <audio controls>
                        <source src="data:audio/mpeg;base64,{base64.b64encode(st.session_state.current_audio).decode()}" type="audio/mpeg">
                    </audio>
                    '''
                st.components.v1.html(audio_html, height=50)
        
        # Word input form
        with st.form(key=f"word_form_{st.session_state.word_count}_{st.session_state.attempts}"):
            user_input = st.text_input("Type the French word:", 
                                     key=f"word_input_{st.session_state.word_count}_{st.session_state.attempts}",
                                     value="").strip().lower()
            submit_button = st.form_submit_button("Submit")
            
            if submit_button:
                if user_input == st.session_state.current_word[1].lower():
                    st.success("✨ Correct!")
                    st.session_state.word_stats[st.session_state.current_word[0]] = st.session_state.attempts + 1
                    tutor.save_progress()
                    time.sleep(2)
                    st.session_state.word_count += 1
                    st.session_state.current_word = None
                    st.session_state.current_audio = None
                    st.session_state.show_hint = False
                    st.rerun()
                else:
                    st.session_state.attempts += 1
                    if st.session_state.attempts == 1:
                        st.error("❌ Incorrect. Try once more!")
                        st.session_state.current_audio = tutor.speak_word(st.session_state.current_word[1])
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Incorrect. The correct word is: {st.session_state.current_word[1]}")
                        st.session_state.word_stats[st.session_state.current_word[0]] = st.session_state.attempts
                        tutor.save_progress()
                        time.sleep(3)
                        st.session_state.word_count += 1
                        st.session_state.current_word = None
                        st.session_state.current_audio = None
                        st.session_state.show_hint = False
                        st.rerun()
        
        if st.button("Quit Practice"):
            tutor.save_session_history()
            st.session_state.practice_mode = False
            st.session_state.current_word = None
            st.session_state.current_words = []
            st.rerun()

    # Show session history
    st.write("---")
    st.subheader("📊 Practice History")
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

    st.markdown("<br><hr><div style='text-align: center; color: gray; font-size: 0.8em; padding: 20px;'>Developed by LBC Productions</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
