import os
import sys
import streamlit as st
from streamlit.components.v1 import html

# ----------------------------------------
# Ensure project root is on path
# ----------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from core.agents.coordinator_agent import CoordinatorAgent
from core.auth.auth_manager import AuthManager

# ----------------------------------------
# Streamlit Page Config
# ----------------------------------------
st.set_page_config(
    page_title="AI Medical Interpreter",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------
# Custom CSS
# ----------------------------------------
st.markdown("""
<style>
    body {font-family: 'Segoe UI', sans-serif;}
    .main-header {
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        border-radius: 10px;
    }
    .role-header {
        font-size: 1.1rem; 
        font-weight: bold;
        margin-bottom: 0.3rem;
        color: #000;
    }
    .chat-card {
        padding: 1rem;
        margin: 0.8rem 0;
        border-radius: 10px;
        border: 1px solid #ddd;
        background-color: #fff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        font-size: 0.95rem;
        color: #000;
    }
    .doctor-msg {border-left: 5px solid #2196F3;}
    .patient-msg {border-left: 5px solid #4CAF50;}
    .translation {
        background: #fffae6;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        margin-top: 0.3rem;
        font-size: 0.95rem;
        color: #000;
    }
    .small-label {
        font-size: 0.8rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# Overlay Spinner HTML Template (Dynamic Animated)
# ----------------------------------------
loading_html = """
<div id="overlay">
  <div class="loader"></div>
  <p id="loading-text">Agentic mode on!</p>
</div>

<style>
#overlay {
  position: fixed;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: radial-gradient(circle at center, rgba(0,0,0,0.6), rgba(0,0,0,0.85));
  z-index: 9999;
  animation: fadein 0.3s ease-in-out;
}

@keyframes fadein {
  from {opacity: 0;}
  to {opacity: 1;}
}

.loader {
  border: 6px solid rgba(255,255,255,0.2);
  border-top: 6px solid #4facfe;
  border-radius: 50%;
  width: 70px;
  height: 70px;
  animation: spin 1s linear infinite, glow 1.5s ease-in-out infinite alternate;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes glow {
  from { box-shadow: 0 0 10px #4facfe; }
  to { box-shadow: 0 0 25px #00f2fe; }
}

#loading-text {
  color: white;
  font-size: 1.2rem;
  margin-top: 18px;
  letter-spacing: 0.5px;
  text-align: center;
  animation: textpulse 1.5s ease-in-out infinite;
}

@keyframes textpulse {
  0%,100% { opacity: 0.8; }
  50% { opacity: 1; }
}
</style>

<script>
document.addEventListener("DOMContentLoaded", function() {
  const texts = [
    "🤖 Asking agent...",
    "🧩 Getting context...",
    "🩺 Analyzing medical terms...",
    "🌐 Translating message...",
    "💡 Preparing response..."
  ];
  let i = 0;
  setInterval(() => {
    const el = document.getElementById("loading-text");
    if (el) {
      el.innerText = texts[i % texts.length];
      i++;
    }
  }, 400);
});
</script>
"""

# ----------------------------------------
# Initialize Auth Manager
# ----------------------------------------
auth = AuthManager()

if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

# ----------------------------------------
# LOGIN / REGISTER SCREEN
# ----------------------------------------
if st.session_state.user is None:
    st.title("🔒 Secure Access Portal")

    auth_mode = st.radio("Select mode:", ["Login", "Register"], horizontal=True)
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if auth_mode == "Login":
        if st.button("🔓 Login"):
            if auth.verify_user(username, password):
                st.session_state.user = username
                st.success(f"Welcome, {username}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
    else:
        if st.button("📝 Register"):
            if auth.user_exists(username):
                st.warning("Username already exists. Try another.")
            elif len(password) < 4:
                st.warning("Password too short. Use at least 4 characters.")
            else:
                success = auth.register_user(username, password)
                if success:
                    st.success("✅ Registration successful! Please log in.")
                else:
                    st.error("Registration failed. Try again.")

    st.stop()  # Halt further rendering until logged in

# ----------------------------------------
# Logged-in Header + Logout
# ----------------------------------------
st.sidebar.markdown(f"**👤 Logged in as:** `{st.session_state.user}`")
if st.sidebar.button("🚪 Logout"):
    st.session_state.user = None
    st.session_state.chat = []
    st.session_state.session_id = None
    st.session_state.summary_text = None
    st.success("Logged out successfully.")
    st.rerun()

# ----------------------------------------
# Header
# ----------------------------------------
st.markdown("""
<div class="main-header">
    <h1>🏥 MediKonnect AI</h1>
    <p>AI-powered, context-aware communication between clinicians and patients</p>
</div>
""", unsafe_allow_html=True)

# ----------------------------------------
# Init backend agents in session_state
# ----------------------------------------
if "coordinator" not in st.session_state:
    st.session_state.coordinator = CoordinatorAgent()

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "chat" not in st.session_state:
    st.session_state.chat = []

if "summary_text" not in st.session_state:
    st.session_state.summary_text = None

coordinator = st.session_state.coordinator

# ----------------------------------------
# Hindi Keyboard (Transliteration)
# ----------------------------------------
def enable_hindi_keyboard(textarea_dom_id: str):
    html(f"""
    <script src="https://www.google.com/inputtools/js/ln/1/ind2.js"></script>
    <script>
      function loadTransliteration() {{
        if (!window.google || !window.google.elements) {{
          return;
        }}
        var options = {{
          sourceLanguage: google.elements.transliteration.LanguageCode.ENGLISH,
          destinationLanguage: [google.elements.transliteration.LanguageCode.HINDI],
          shortcutKey: 'ctrl+g',
          transliterationEnabled: true
        }};
        var control = new google.elements.transliteration.TransliterationControl(options);
        control.makeTransliteratable(['{textarea_dom_id}']);
      }}
      if (window.google && window.google.load) {{
        google.load("elements", "1", {{ packages: "transliteration" }});
        google.setOnLoadCallback(loadTransliteration);
      }} else {{
        setTimeout(loadTransliteration, 1500);
      }}
    </script>
    """, height=0)

# ----------------------------------------
# Layout: Doctor | Conversation | Patient
# ----------------------------------------
col_left, col_mid, col_right = st.columns([3, 4, 3])

# Doctor Side
with col_left:
    st.subheader("👨‍⚕️ Doctor")
    st.markdown(
        '<div class="small-label">'
        'Type in English. The assistant will translate to Hindi for the patient with medical & cultural nuance.'
        '</div>',
        unsafe_allow_html=True
    )
    doctor_input = st.text_area(
        "Enter message (English):",
        key="doc_in",
        height=120,
        label_visibility="collapsed",
        placeholder="Ask a question or give instructions..."
    )
    if st.button("📤 Send as Doctor", key="doc_send", use_container_width=True):
        if doctor_input.strip():
            session_id = st.session_state.session_id
            placeholder = st.empty()
            placeholder.markdown(loading_html, unsafe_allow_html=True)
            try:
                result = coordinator.process_message(
                    text=doctor_input.strip(),
                    speaker="doctor",
                    session_id=session_id
                )
            finally:
                placeholder.empty()

            if result.get("blocked"):
                st.warning(f"⚠️ Message blocked for safety: {result.get('reason', 'Unsafe content detected.')}")
            else:
                if st.session_state.session_id is None:
                    st.session_state.session_id = result["session_id"]
                st.session_state.chat.append({
                    "role": "doctor",
                    "original": result["original_text"],
                    "translated": result["translation"],
                    "contexts": result["contexts"],
                    "intent_label": result.get("intent_label", ""),
                    "intent_conf": result.get("intent_confidence", 0)
                })
                st.rerun()

# Patient Side
with col_right:
    st.subheader("🧑‍🧍 Patient")
    st.markdown(
        '<div class="small-label">'
        'Type in Hindi (or phonetically and press Ctrl+G for Hindi transliteration).'
        '</div>',
        unsafe_allow_html=True
    )
    patient_input = st.text_area(
        "Enter message (Hindi):",
        key="pat_in",
        height=120,
        label_visibility="collapsed",
        placeholder="अपनी समस्या यहाँ लिखें..."
    )
    enable_hindi_keyboard("pat_in")
    if st.button("📤 Send as Patient", key="pat_send", use_container_width=True):
        if patient_input.strip():
            session_id = st.session_state.session_id
            placeholder = st.empty()
            placeholder.markdown(loading_html, unsafe_allow_html=True)
            try:
                result = coordinator.process_message(
                    text=patient_input.strip(),
                    speaker="patient",
                    session_id=session_id
                )
            finally:
                placeholder.empty()

            if result.get("blocked"):
                st.warning(f"⚠️ Message blocked for safety: {result.get('reason', 'Unsafe content detected.')}")
            else:
                if st.session_state.session_id is None:
                    st.session_state.session_id = result["session_id"]
                st.session_state.chat.append({
                    "role": "patient",
                    "original": result["original_text"],
                    "translated": result["translation"],
                    "contexts": result["contexts"],
                    "intent_label": result.get("intent_label", ""),
                    "intent_conf": result.get("intent_confidence", 0)
                })
                st.rerun()

# Conversation Center
with col_mid:
    st.subheader("💬 Conversation Flow")

    with st.container(height=550, border=True):
        if not st.session_state.chat:
            st.info("Start the conversation from either side to see translations and context here.")
        else:
            for msg in st.session_state.chat:
                role = msg["role"]
                role_class = "doctor-msg" if role == "doctor" else "patient-msg"
                role_label = "Doctor" if role == "doctor" else "Patient"
                translated = msg.get("translated", "")
                ctx = msg.get("contexts", {"medical": [], "cultural": []})
                intent_label = msg.get("intent_label", "")
                intent_conf = msg.get("intent_conf", 0)

                st.markdown(f"""
                <div class="chat-card {role_class}">
                    <div class="role-header">{role_label}</div>
                    <b>Original:</b><br>{msg['original']}<br>
                    <div class="translation"><b>Translated:</b> {translated}</div>
                    <div class="small-label"><i>Intent:</i> {intent_label} ({intent_conf:.2f})</div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("🔍 View retrieved medical & cultural context", expanded=False):
                    medical = ctx.get("medical", [])
                    cultural = ctx.get("cultural", [])
                    if not medical and not cultural:
                        st.write("No specific context retrieved for this message.")
                    else:
                        if medical:
                            st.markdown("**🩺 Medical Context:**")
                            for m in medical:
                                st.markdown(f"- {m}")
                        if cultural:
                            st.markdown("**🎭 Cultural Context:**")
                            for c in cultural:
                                st.markdown(f"- {c}")

# ----------------------------------------
# Sidebar: Session Manager + Summary
# ----------------------------------------
with st.sidebar:
    st.header("🗂️ Session Manager")

    current_session = st.session_state.get("session_id")
    if current_session:
        st.success(f"Active Session:\n{current_session}")
    else:
        st.info("No active session")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 New Session", use_container_width=True):
            new_session_id = coordinator.start_session()
            st.session_state.session_id = new_session_id
            st.session_state.chat = []
            st.session_state.summary_text = None
            st.success("Started new session.")
            st.rerun()

    with col2:
        if st.button("🛑 End Session", use_container_width=True):
            if st.session_state.session_id:
                coordinator.end_session(st.session_state.session_id)
                st.session_state.session_id = None
                st.session_state.chat = []
                st.session_state.summary_text = None
                st.warning("Session ended. Start a new one to continue.")
                st.rerun()
            else:
                st.info("No active session to end.")

    st.markdown("---")
    st.subheader("🧠 Conversation Summary")
    if st.button("Generate Summary", key="generate_summary_sidebar", use_container_width=True):
        if st.session_state.session_id:
            try:
                summary = coordinator.summarize_session(st.session_state.session_id)
                st.session_state.summary_text = summary
            except Exception as e:
                st.error(f"Failed to generate summary: {e}")
        else:
            st.warning("No active session to summarize.")
    if st.session_state.summary_text:
        st.write(st.session_state.summary_text)

# ----------------------------------------
# Footer note
# ----------------------------------------
st.caption("🔒 Demo medical interpreter. For real clinical use, ensure compliance and human oversight.")
