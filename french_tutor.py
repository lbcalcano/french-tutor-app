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
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_button"):
                if self.verify_credentials(username, password):
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        
        with tab2:
            new_username = st.text_input("Choose Username", key="reg_username")
            new_password = st.text_input("Choose Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
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

def main():
    st.set_page_config(page_title="French Tutor", page_icon="🇫🇷")
    
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
        st.header("Progress")
        total_words = len(tutor.words)
        completed = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] <= 2])
        perfect = len([w for w in st.session_state.word_stats if st.session_state.word_stats[w] == 1])
        
        # Calculate rating
        rating_percentage = (perfect / total_words * 100) if total_words > 0 else 0
        
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
        
        # Add hint button
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
            st.session_state.practice_mode = False
            st.session_state.current_word = None
            st.session_state.current_words = []
            st.rerun()

    st.markdown("<br><hr><div style='text-align: center; color: gray; font-size: 0.8em; padding: 20px;'>Developed by LBC Productions</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
