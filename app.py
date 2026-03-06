import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import time

# --- CONFIGURACIÓN DE IA (HUGGING FACE) ---
# REEMPLAZA ESTO con tu token real de Hugging Face
# Ejemplo: API_TOKEN = "hf_xxxxx..."
API_TOKEN = "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" 

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

# --- DICCIONARIO DE IDIOMAS DE LA APP (i18n) ---
LANG_PACK = {
    "en": {
        "title": "🇦🇷 ARG News AI Monitor",
        "subheader": "Real-time headlines and AI-generated summaries.",
        "refresh_btn": "Refresh News",
        "loading_scraping": "Scraping headlines...",
        "loading_ai": "AI is reading and summarizing (this takes a few seconds)...",
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
        "loading_ai": "AI가 읽고 요약하는 중입니다 (몇 초 정도 걸립니다)...",
        "global_tab": "🔥 글로벌 핫토픽",
        "source": "출처",
        "read_more": "전체 기사 읽기",
        "ai_summary": "AI 요약",
        "error_ai": "AI 요약 서비스를 일시적으로 사용할 수 없습니다.",
        "no_text": "요약할 텍스트를 충분히 추출할 수 없습니다."
    }
}

# --- FUNCIONES CORE ---

def translate_text(text, target_lang):
    if not text or len(text) < 2: return text
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

# IA: Summarization Function
def query_ai_summarizer(text):
    payload = {
        "inputs": text,
        "parameters": {"min_length": 30, "max_length": 100}
    }
    response = requests.post(API_URL, headers=headers_ai, json=payload)
    result = response.json()
    if isinstance(result, list) and 'summary_text' in result[0]:
        return result[0]['summary_text']
    return None

# Scraping: Extract full article text from a URL
@st.cache_data(ttl=3600) # Cachear cuerpo de noticia por 1 hora
def extract_article_text(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Buscamos párrafos (<p>). Los diarios suelen poner el cuerpo en etiquetas p.
        paragraphs = soup.find_all('p')
        full_text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 50])
        # Limitamos el texto para no saturar la API (máx ~1000 palabras)
        return full_text[:4000] 
    except:
        return None

# Scraping: Get top 5 headlines and their links
@st.cache_data(ttl=600) # Cachear portadas por 10 min
def scrape_headlines(url, link_prefix):
    headers = {'User-Agent': 'Mozilla/5.0'}
    news_data = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Selectores genéricos de enlaces h1, h2, h3
        tags = soup.find_all(['h1', 'h2', 'h3'], limit=20)
        
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

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="ARG News AI Monitor", layout="wide", page_icon="📰")

# Selector de idioma arriba a la derecha
col_title, col_lang = st.columns([0.85, 0.15])

with col_lang:
    lang_choice = st.selectbox("", ["🇺🇸 EN", "🇰🇷 KO"], label_visibility="collapsed")
    lang_code = "en" if "EN" in lang_choice else "ko"

t = LANG_PACK[lang_code] # Ataljo para textos

# Títulos traducidos
with col_title:
    st.title(t["title"])
    st.subheader(t["subheader"])

# Pestañas
opciones_tabs = [t["global_tab"]] + list(SITES.keys())
tabs = st.tabs(opciones_tabs)

# Lógica Global (Simplificada: solo títulos traducidos para velocidad)
with tabs[0]:
    if st.button(t["refresh_btn"], key="global_btn"):
        st.experimental_rerun()
        
    global_headlines = []
    with st.spinner(t["loading_scraping"]):
        for name, data in SITES.items():
            titles = scrape_headlines(data["url"], data["link_prefix"])
            if titles:
                global_headlines.append({"medio": name, "title": titles[0]["title"], "link": titles[0]["link"]})
    
    for i, item in enumerate(global_headlines[:5], 1):
        with st.expander(f"{i}. [{item['medio']}] {translate_text(item['title'], lang_code)}"):
            st.write(f"[{t['read_more']}]({item['link']})")

# Lógica Individual (Con IA y Resumen)
for i, (name, data) in enumerate(SITES.items(), 1):
    with tabs[i]:
        st.header(f"{name}")
        
        headlines_data = scrape_headlines(data["url"], data["link_prefix"])
        
        for idx, news in enumerate(headlines_data, 1):
            # Título traducido
            translated_title = translate_text(news['title'], lang_code)
            st.subheader(f"{idx}. {translated_title}")
            st.caption(f"{t['source']}: {name} | [{t['read_more']}]({news['link']})")
            
            # Botón único por noticia para activar la IA
            summary_key = f"sum_{name}_{idx}"
            if st.button(f"✨ {t['ai_summary']}", key=summary_key):
                with st.spinner(t["loading_ai"]):
                    # 1. Extraer cuerpo
                    article_text = extract_article_text(news['link'])
                    
                    if article_text and len(article_text) > 200:
                        # 2. IA Resume (en inglés)
                        english_summary = query_ai_summarizer(article_text)
                        
                        if english_summary:
                            # 3. Traducir resumen
                            final_summary = translate_text(english_summary, lang_code)
                            st.info(f"**{t['ai_summary']}**: {final_summary}")
                        else:
                            st.error(t["error_ai"])
                    else:
                        st.warning(t["no_text"])
            st.divider()
