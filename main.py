import streamlit as st
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
import markdown
from api import google_api
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
import io
import PIL
# Replace this with your actual Google API key
GOOGLE_API_KEY = google_api

# Initialize recognizer and text-to-speech engine
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()

# Initialize session state for chat history if not already present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

def llm(text): 
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(text)
    return response.text

def process_image(image,text):

    genai.configure(api_key=GOOGLE_API_KEY)
    img = PIL.Image.open(image)

    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content([text,img])
    response.resolve()
    return "Response from vision model:"+response.text

def recognize_speech_from_microphone(listening_placeholder):
    with sr.Microphone() as source:
        listening_placeholder.info("Listening...")
        recognizer.adjust_for_ambient_noise(source) 
        try:
            audio = recognizer.record(source, duration=5)
            text = recognizer.recognize_google(audio)
            st.session_state.chat_history.append({"role": "user", "message": text})
            listening_placeholder.empty()
            return text
        except sr.UnknownValueError:
            listening_placeholder.error("Could not understand the audio")
        except sr.RequestError:
            listening_placeholder.error("Could not request results from the service")
        return None

def speak_text(text):
    if tts_engine._inLoop:
        tts_engine.endLoop()
    tts_engine.say(text)
    tts_engine.runAndWait()
    return

def process_file(uploaded_file,text):
    if uploaded_file is not None:
        file_type = uploaded_file.type
        if file_type == "text/csv":
            df = pd.read_csv(uploaded_file)
            return df.to_string()
        elif file_type == "application/pdf":
            pdf_text = ""
            pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            for page in pdf_document:
                pdf_text += page.get_text()
            return pdf_text
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc_text = ""
            doc = Document(io.BytesIO(uploaded_file.read()))
            for para in doc.paragraphs:
                doc_text += para.text + "\n"
            return doc_text
        elif file_type in ["image/jpeg", "image/png", "image/jpg"]:
                return process_image(uploaded_file,text)
        else:
            return "Unsupported file type."
    return ""

st.sidebar.title("Upload your files here")

uploaded_file = st.sidebar.file_uploader("You can also ask questions related to given files(if given)", type=["csv", "pdf", "docx", "jpg", "jpeg", "png"])
if uploaded_file:
    st.session_state.uploaded_file = uploaded_file

# Main content
st.title("Speech - to - Speech Chatbot")
st.write("Click the microphone button to start the conversation.")

if st.button("🎤 Start Conversation"):
    listening_placeholder = st.empty() 
    recognized_text = recognize_speech_from_microphone(listening_placeholder)
    if recognized_text:
        with st.spinner("Processing..."):
            file_data = process_file(st.session_state.uploaded_file,recognized_text) 
            combined_text = f"{recognized_text}\n\nFile Data:\n{file_data}" if file_data else recognized_text
            processed_text = llm(combined_text)
            st.session_state.chat_history.append({"role": "bot", "message": processed_text})

        # Display chat history
        st.subheader("Chat History")
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                st.chat_message("user").markdown(chat["message"])
            else:
                st.chat_message("assistant").markdown(chat["message"])

        processed_text = markdown.markdown(processed_text)
        speak_text(processed_text)
