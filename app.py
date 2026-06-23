import streamlit as st
from groq import Groq
from serpapi import GoogleSearch  
import datetime
import pytz
import PyPDF2
import re  
import os
import time
import asyncio
import io  
import edge_tts  
from audio_recorder_streamlit import audio_recorder

# Set up the browser page title
st.set_page_config(page_title="Nova AI", page_icon="🤖", layout="wide")
st.title("🤖 Nova: My Personal AI Assistant")

# --- 📌 STICKY CHAT INPUT PINNING WRAPPER ---
st.markdown("""
    <style>
        div[data-testid="stHorizontalBlock"] {
            position: fixed !important;
            bottom: 20px !important;
            left: 58% !important;
            transform: translateX(-50%) !important;
            width: 55% !important;
            background-color: #141821 !important;
            padding: 10px 20px !important;
            border-radius: 16px !important;
            border: 1px solid #262730 !important;
            box-shadow: 0px -4px 25px rgba(0, 0, 0, 0.8) !important;
            z-index: 99999 !important;
        }
        .stChatElementContainer, .stChatMessageContainer, div[data-testid="stChatMessageContainer"] {
            margin-bottom: 130px !important;
        }
        div[data-testid="stColumn"] {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# Fetch API Keys securely from st.secrets
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    SERP_API_KEY = st.secrets["SERP_API_KEY"]
except Exception:
    st.error("Please configure GROQ_API_KEY and SERP_API_KEY in your Streamlit Advanced Settings Secrets!")
    st.stop()

# 🎙️ CLOUD-SAFE VOICE GENERATOR
def speak_to_browser(text):
    try:
        clean_audio_text = re.sub(r'[^\x00-\x7F]+', '', text)
        clean_audio_text = clean_audio_text.replace('*', '').replace('#', '').strip()
        
        if clean_audio_text:
            voice_model = "en-US-EmmaNeural"
            
            async def generate_speech_stream():
                communicate = edge_tts.Communicate(clean_audio_text, voice_model)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                return audio_data
            
            raw_bytes = asyncio.run(generate_speech_stream())
            if raw_bytes:
                st.audio(raw_bytes, format="audio/mp3", autoplay=True)
    except Exception:
        pass

# 🌐 STABLE NEWS SEARCH
def search_the_internet(query):
    try:
        search = GoogleSearch({
            "q": query,
            "tbm": "nws",  
            "hl": "en",    
            "gl": "in",    
            "api_key": SERP_API_KEY
        })
        results = search.get_dict().get("news_results", [])
        if not results:
            return "No recent breaking news headlines discovered."
            
        summary = []
        for r in results[:3]:  
            summary.append(f"- [{r.get('source', 'News Feed')}]: {r.get('title')} -> {r.get('snippet')}")
        return "\n".join(summary)
    except Exception as e:
        return f"The live search stream is busy: {str(e)}"

# Setup timezones for file generation
india_tz = pytz.timezone('Asia/Kolkata')
current_time_obj = datetime.datetime.now(india_tz)
local_time = current_time_obj.strftime("%I:%M %p on %A, %B %d, %Y")
current_year_month = current_time_obj.strftime("%B %Y")

# Initialize messages bank early
if "messages" not in st.session_state:
    st.session_state.messages = []
if "full_document_text" not in st.session_state:
    st.session_state.full_document_text = ""
if "voice_queue" not in st.session_state:
    st.session_state.voice_queue = None

# 📂 SIDEBAR PANEL CONTROL
with st.sidebar:
    st.header("📂 Document Processor")
    st.caption("Upload a PDF to let Nova read it.")
    uploaded_file = st.file_uploader("Drag & Drop File Here", type=["pdf", "txt"], key="pdf_uploader")
    
    if uploaded_file is not None and not st.session_state.full_document_text:
        try:
            with st.spinner("Processing file... please wait."):
                extracted_text = ""
                if uploaded_file.type == "application/pdf":
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    num_pages = min(len(pdf_reader.pages), 500)
                    
                    for i in range(num_pages):
                        page = pdf_reader.pages[i]
                        text = page.extract_text()
                        if text:
                            extracted_text += text + "\n"
                else:
                    extracted_text = uploaded_file.read().decode("utf-8")
                    
                st.session_state.full_document_text = extracted_text
                st.success(f"✅ Document securely indexed into internal memory!")
        except Exception as e:
            st.error(f"Error reading file: {e}")
            
    if uploaded_file is None:
        st.session_state.full_document_text = ""

    # 🧹 WORKSPACE CLEANER
    st.markdown("---")
    st.subheader("🧹 Workspace Cleaner")
    st.caption("Instantly erase current active states.")
    
    if st.button("Clear Chat History", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.full_document_text = ""
        st.session_state.voice_queue = None
        st.success("Chat logs safely wiped!")
        time.sleep(0.5)
        st.rerun()

    # 💾 CONVERSATION SAVER INTEGRATION BLOCK
    st.markdown("---")
    st.header("💾 Conversation Exporter")
    st.caption("Download your chat history cleanly.")
    
    if len(st.session_state.messages) > 0:
        chat_export_string = f"--- NOVA AI CHAT LOG GENERATED ON {local_time.upper()} ---\n\n"
        
        for msg in st.session_state.messages:
            if msg["role"] != "system":
                clean_text_segment = str(msg["content"]).split("\n\n[")
                speaker_tag = "SAYON (USER)" if msg["role"] == "user" else "NOVA (ASSISTANT)"
                chat_export_string += f"[{speaker_tag}]: {clean_text_segment}\n\n"
        
        st.download_button(
            label="⬇️ Download Chat Log (.txt)",
            data=chat_export_string,
            file_name=f"nova_chat_log_{current_time_obj.strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain"
        )
    else:
        st.info("Start chatting to enable downloading! 🔥")

# 🧠 CORE SYSTEM PROFILE
system_prompt = {
    "role": "system", 
    "content": (
        "Your name is Nova. You are an ultra-smart, emotionally expressive personal AI assistant created by Sayon. "
        "You have complete real-time access to live information via the provided background contexts. "
        "Speak like an enthusiastic, caring friend! Use fun, appropriate emojis (🌟, 🙌, 🤖) "
        "to emphasize your emotional mood. Keep your answers brief, conversational, and energetic."
    )
}

# Display older messages cleanly + Play the freshest audio message on rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        raw_text = str(message["content"])
        clean_display = raw_text.split("\n\n[")
        st.markdown(clean_display)

# If a fresh answer was just added to session history, play it here!
if st.session_state.voice_queue:
    speak_to_browser(st.session_state.voice_queue)
    st.session_state.voice_queue = None  # Reset queue so it doesn't loop forever

# --- 🎤 MICROPHONE INPUT INTERFACE ---
st.markdown("---")
col1, col2 = st.columns([0.90, 0.10], vertical_alignment="bottom")

with col1:
    user_input = st.chat_input("Ask Nova anything...")

with col2:
    audio_bytes = audio_recorder(text="", recording_color="#e74c3c", neutral_color="#95a5a6", icon_size="2x")

if audio_bytes and ("last_audio" not in st.session_state or st.session_state["last_audio"] != audio_bytes):
    st.session_state["last_audio"] = audio_bytes
    with st.spinner("Transcribing voice query..."):
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "voice.wav"
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file
            )
            if transcription.text.strip():
                user_input = transcription.text
        except Exception as e:
            st.error(f"Voice Engine Error: {e}")

# Process Input Responses (Both typed and spoken text)
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    
    cleaned_input = user_input.replace('"', '').replace("'", "").lower().strip()
    context_addon = ""
    
    if st.session_state.full_document_text:
        keywords = [w for w in cleaned_input.split() if len(w) > 4]
        matched_paragraphs = []
        paragraphs = st.session_state.full_document_text.split("\n")
        for para in paragraphs:
            if any(kw in para.lower() for kw in keywords) and len(para.strip()) > 10:
                matched_paragraphs.append(para.strip())
                if len(matched_paragraphs) >= 5: 
                    break
        relevant_context = "\n".join(matched_paragraphs) if matched_paragraphs else st.session_state.full_document_text[:2000]
        context_addon += f"\n\n[Relevant Document Snippet]:\n{relevant_context}"
    
    if any(w in cleaned_input for w in ["time", "date", "clock"]):
        context_addon += f"\n\n[System Time]: {local_time}"
        
    if any(w in cleaned_input for w in ["news", "search", "latest", "who is", "crypto", "price", "today", "india", "world", "global", "weather", "bengal", "suti"]):
        with st.chat_message("assistant"):
            st.caption("🔍 *Checking live information networks...*")
        clean_search = cleaned_input.replace("followed by", "").replace('"', '').replace('?', '')
