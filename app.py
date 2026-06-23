import streamlit as st
from groq import Groq
from serpapi import GoogleSearch  
import datetime
import pytz
import PyPDF2
import re  
import os
import threading
import time
import asyncio
import io  
import edge_tts  
import streamlit as st
import base64
# 🎤 Microphone recording library
from audio_recorder_streamlit import audio_recorder

# Initialize audio playback driver smoothly
try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.mixer.init()
except Exception:
    pass

# Set up the browser page title
st.set_page_config(page_title="Nova AI", page_icon="🤖", layout="wide")
st.title("🤖 Nova: My Personal AI Assistant")

st.markdown("""
    <style>
        /* Target and anchor the exact horizontal container block row layout */
        div[data-testid="stHorizontalBlock"] {
            position: fixed !important;
            bottom: 20px !important;
            left: 55% !important;
            transform: translateX(-50%) !important;
            width: 60% !important;
            background-color: #0e1117 !important;
            padding: 10px 20px !important;
            border-radius: 16px !important;
            border: 1px solid #262730 !important;
            box-shadow: 0px -4px 20px rgba(0, 0, 0, 0.5) !important;
            z-index: 99999 !important;
        }
        
        /* Forces the main chat background scroll wrapper to yield clearance workspace */
        .stChatElementContainer, .stChatMessageContainer {
            margin-bottom: 110px !important;
        }
        
        /* Adjust column vertical alignment to sit neatly on the baseline axis */
        div[data-testid="stColumn"] {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# Groq API client config
api_key = "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"
client = Groq(api_key=api_key)

# 🎙️ HIGH-SPEED NATIVE IN-MEMORY AUDIO GENERATOR
def speak_in_background(text):
    def run_voice():
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
                    audio_stream = io.BytesIO(raw_bytes)
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                    
                    pygame.mixer.music.load(audio_stream)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.01)
                    pygame.mixer.music.unload()
        except Exception:
            pass
            
    threading.Thread(target=run_voice, daemon=True).start()

# 🌐 STABLE NEWS SEARCH
def search_the_internet(query):
    try:
        serp_api_key = "fcddb822699fdd81fd526e0de6973885393bffaf3aee8cae3da38ef6a3e26ba2" 
        search = GoogleSearch({
            "q": query,
            "tbm": "nws",  
            "hl": "en",    
            "gl": "in",    
            "api_key": serp_api_key
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

# 📂 SIDEBAR PANEL CONTROL
with st.sidebar:
    st.header("📂 Document Processor")
    st.caption("Upload a PDF to let Nova read it.")
    uploaded_file = st.file_uploader("Drag & Drop File Here", type=["pdf", "txt"])
    
    if "full_document_text" not in st.session_state:
        st.session_state.full_document_text = ""
        st.session_state.doc_loaded = False

    if uploaded_file is not None and not st.session_state.doc_loaded:
        try:
            st.warning("Processing file... please wait.")
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
            st.session_state.doc_loaded = True
            st.success(f"✅ Document securely indexed into internal memory!")
        except Exception as e:
            st.error(f"Error reading file: {e}")
            
    if uploaded_file is None:
        st.session_state.full_document_text = ""
        st.session_state.doc_loaded = False

    # 🧹 Workspace Cleaner Button
    st.markdown("---")
    st.subheader("🧹 Workspace Cleaner")
    st.caption("Instantly erase current active states.")
    
    if st.button("Clear Chat History", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.full_document_text = ""
        st.session_state.doc_loaded = False
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
                clean_text_segment = str(msg["content"]).split("\n\n[")[0]
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

# Display older messages cleanly
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        raw_text = str(message["content"])
        clean_display = raw_text.split("\n\n[")[0]
        st.markdown(clean_display)

# --- 🎤 MICROPHONE INPUT INTERFACE ---
st.markdown("---")
col1, col2 = st.columns([0.90, 0.10], vertical_alignment="bottom")

with col1:
    user_input = st.chat_input("Ask Nova anything...")

with col2:
    # Places a beautifully rendered, clickable microphone icon next to your chatbox
    audio_bytes = audio_recorder(text="", recording_color="#e74c3c", neutral_color="#95a5a6", icon_size="2x")

# Handle Voice Transcription using Groq's high-speed Whisper engine
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
# Process Input Responses (Both typed and spoken text)
if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    
    cleaned_input = user_input.replace('"', '').replace("'", "").lower().strip()
    context_addon = ""
    
    # 1. Dynamic Chunk-Matching Logic
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
    
    # 2. Check for Time/Date (Changed to independent 'if' for smooth processing fallback)
    if any(w in cleaned_input for w in ["time", "date", "clock"]):
        context_addon += f"\n\n[System Time]: {local_time}"
        
    # 3. Smart Triggers for news searching (Changed to independent 'if' to unlock text inputs)
    if any(w in cleaned_input for w in ["news", "search", "latest", "who is", "crypto", "price", "today", "india", "world", "global", "weather", "bengal", "suti"]):
        with st.chat_message("assistant"):
            st.caption("🔍 *Checking live information networks...*")
        clean_search = cleaned_input.replace("followed by", "").replace('"', '').replace('?', '')
        if len(clean_search.split()) <= 3 and any(k in clean_search for k in ["india", "news"]):
            search_query = f"{clean_search} {current_year_month}"
        else:
            search_query = clean_search
            
        live_news = search_the_internet(search_query)
        context_addon += f"\n\n[Live Search Network Context]:\n{live_news}"

    # Build history layout payload safely
    messages_payload = [system_prompt]
    for msg in st.session_state.messages:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})
        
    full_user_content = f"{user_input}{context_addon}"
    messages_payload.append({"role": "user", "content": full_user_content})
    st.session_state.messages.append({"role": "user", "content": full_user_content})

    # Call Groq API and stream response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages_payload,
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    clean_ui_render = full_response.split("\n\n[")[0]
                    response_placeholder.markdown(clean_ui_render + "▌")
            
            final_clean_ui = full_response.split("\n\n[")[0]
            response_placeholder.markdown(final_clean_ui)
            
            st.session_state.messages.append({"role": "assistant", "content": final_clean_ui})
            speak_in_background(final_clean_ui)
            st.rerun()
            
        except Exception as e:
            st.error(f"Nova's thinking core encountered an error: {e}")
