import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# --- CONFIGURACIÓN DE IA (HUGGING FACE) ---
# Ahora la app es segura: no hay claves a la vista.
try:
    API_TOKEN = st.secrets["HF_TOKEN"]
except:
    st.error("Error: Key 'HF_TOKEN' not found in Secrets. Please check your Streamlit Cloud settings.")
    st.stop()

API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
headers_ai = {"Authorization": f"Bearer {API_TOKEN}"}

# --- CONFIGURACIÓN DE MEDIOS ---
SITES = {
    "Infobae": {"url": "https://www.infobae.com", "link_prefix": "https://www.infobae.com"},
    "Clarín": {"url": "https://www.clarin.com", "link_prefix": ""},
    "Cronista": {"url": "https://www.cronista.com", "link_prefix": ""},
    "La Nación": {"url": "https://www.lanacion.com.ar", "link_prefix": "https://www.lanacion.com.ar"},
    "BA Herald": {"url": "https://buenosairesherald.com", "link_prefix": ""},
    "Perfil": {"url": "https://www.perfil.com", "link_prefix": ""}
}

# --- DICCIONARIO DE IDIOMAS DE LA APP ---
LANG_PACK = {
    "en": {
        "title": "🇦🇷 ARG News AI Monitor",
        "subheader": "Real-time headlines and AI-generated summaries.",
        "refresh_btn": "Refresh News",
        "loading_scraping": "Scraping headlines...",
        "loading_ai": "AI is reading and summarizing...",
        "global_tab": "🔥 Global Hot Topics",
        "source": "Source",
        "read_more": "Read full article",
        "ai_summary": "AI Summary",
        "error_ai": "AI Summarization temporarily unavailable.",
        "no_text": "Could not extract enough text to summarize."
    },
    "ko": {
        "title": "🇦🇷 아르헨티나 뉴스 AI 모니터",
        "subheader": "실시간 헤드라인 및 AI 생성 요약.",
        "refresh_btn": "뉴스 새로고침",
        "loading_scraping": "헤드라인을 가져오는 중...",
        "loading_ai": "AI가 요약하는 중입니다...",
        "global_tab": "🔥 글로벌 핫토픽",
        "source": "출처",
        "read_more": "전체 기사 읽기",
        "ai_summary": "AI 요약",
        "error_ai": "AI 요약 서비스를 사용할 수 없습니다.",
        "no_text": "텍스트를 충분히 추출할 수 없습니다."
    }
}

# --- FUNCIONES ---

def translate_text(text, target_lang):
    if not text or len(text) < 2: return text
    try:
        # 'auto' detecta el idioma original y lo pasa al elegido
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def query_ai_summarizer(text):
    payload = {"inputs": text, "parameters": {"min_length": 50, "max_length": 130}}
    try:
        response = requests.post(API_URL, headers=headers_ai, json=payload, timeout=25)
        
        # Si el modelo está "durmiendo", Hugging Face devuelve un 503
        if response.status_code == 503:
            return "Wait a moment... AI model is loading. Try again in 20 seconds."
            
        result = response.json()
        if isinstance(result, list) and 'summary_text' in result[0]:
            return result[0]['summary_text']
    except Exception as e:
        return None
    return None

@st.cache_data(ttl=3600)
def extract_article_text(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
