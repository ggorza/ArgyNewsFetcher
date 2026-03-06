import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# --- CONFIGURACIÓN DE IA (HUGGING FACE) ---
# Tu token ya está integrado aquí
API_TOKEN = st.secrets["HF_TOKEN"]
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
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def query_ai_summarizer(text):
    payload = {"inputs": text, "parameters": {"min_length": 40, "max_length": 120}}
    try:
        response = requests.post(API_URL, headers=headers_ai, json=payload, timeout=20)
        # Hugging Face a veces tarda en cargar el modelo, manejamos el error 503
        if response.status_code == 503:
            return "Model is loading, please try again in 20 seconds."
        
        result = response.json()
        if isinstance(result, list) and 'summary_text' in result[0]:
            return result[0]['summary_text']
    except:
        return None
    return None

@st.cache_data(ttl=3600)
def extract_article_text(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        # Filtramos párrafos muy cortos que suelen ser publicidad
        full_text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 60])
        return full_text[:4000] 
    except:
        return None

@st.cache_data(ttl=300)
def scrape_headlines(url, link_prefix):
    headers = {'User-Agent': 'Mozilla/5.0'}
    news_data = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        tags = soup.find_all(['h1', 'h2', 'h3'], limit=25)
        for tag in tags:
            a_tag = tag.find('a', href=True)
            if a_tag:
                title = a_tag.get_text().strip()
                link = a_tag['href']
                if not link.startswith('http'):
                    link = link_prefix + link
                if len(title) > 25:
                    news_data.append({"title": title, "link": link})
                    if len(news_data) == 5: break
        return news_data
    except:
        return []

# --- INTERFAZ ---
st.set_page_config(page_title="ARG News AI Monitor", layout="wide")

# Selector de idioma arriba a la derecha
col_title, col_lang = st.columns([0.8, 0.2
