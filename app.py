import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# 1. CONFIGURACIÓN DE PÁGINA (DEBE SER LA PRIMERA LÍNEA)
st.set_page_config(page_title="ARG News AI Monitor", layout="wide", page_icon="📰")

# --- CONFIGURACIÓN DE IA (HUGGING FACE) ---
# Se busca el token en los Secrets de Streamlit Cloud
API_TOKEN = st.secrets.get("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
headers_ai = {"Authorization": f"Bearer {API_TOKEN}"}

# --- CONFIGURACIÓN DE MEDIOS ---
SITES = {
    "Infobae": {"url": "https://www.infobae.com", "prefix": "https://www.infobae.com"},
    "Clarín": {"url": "https://www.clarin.com", "prefix": "https://www.clarin.com"},
    "Cronista": {"url": "https://www.cronista.com", "prefix": "https://www.cronista.com"},
    "La Nación": {"url": "https://www.lanacion.com.ar", "prefix": "https://www.lanacion.com.ar"},
    "BA Herald": {"url": "https://buenosairesherald.com", "prefix": ""},
    "Perfil": {"url": "https://www.perfil.com", "prefix": ""}
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
        "read_more": "Read full article",
        "ai_summary": "AI Summary",
        "error_ai": "AI Summarization unavailable.",
        "no_text": "Article text too short for AI.",
        "ai_busy": "AI is loading. Try again in 20s.",
        "token_error": "AI Error: Check if your Token is valid in Secrets!",
        "no_news": "Could not find headlines."
    },
    "ko": {
        "title": "🇦🇷 아르헨티나 뉴스 AI 모니터",
        "subheader": "실시간 헤드라인 및 AI 생성 요약.",
        "refresh_btn": "뉴스 새로고침",
        "loading_scraping": "헤드라인을 가져오는 중...",
        "loading_ai": "AI가 요약하는 중입니다...",
        "global_tab": "🔥 글로벌 핫토픽",
        "read_more": "전체 기사 읽기",
        "ai_summary": "AI 요약",
        "error_ai": "AI 요약 서비스를 사용할 수 없습니다.",
        "no_text": "텍스트가 너무 짧습니다.",
        "ai_busy": "AI가 로딩 중입니다. 20초 후 다시 시도하세요.",
        "token_error": "AI 오류: Secrets의 토큰이 유효한지 확인하세요!",
        "no_news": "뉴스를 찾을 수 없습니다."
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
    if not API_TOKEN: return "TOKEN_ERROR"
    # Limpieza básica para evitar errores de envío
    clean_text = text.replace("\n", " ").strip()[:3000]
    payload = {"inputs": clean_text, "parameters": {"min_length": 50, "max_length": 150}}
    
    try:
        response = requests.post(API_URL, headers=headers_ai, json=payload, timeout=30)
        
        if response.status_code == 503: return "BUSY"
        if response.status_code == 401: return "TOKEN_ERROR"
        
        result = response.json()
        if isinstance(result, list) and 'summary_text' in result[0]:
            return result[0]['summary_text']
        return None
    except:
        return None

@st.cache_data(ttl=3600)
def extract_article_text(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        full_text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 60])
        return full_text if len(full_text) > 200 else None
    except:
        return None

@st.cache_data(ttl=300)
def scrape_headlines(url, prefix):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    news_data = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Estrategia amplia: buscamos links con texto largo (titulares)
        links = soup.find_all('a', href=True)
        for link in links:
            title = link.get_text().strip()
            href = link['href']
            
            # Filtros para evitar links basura y duplicados
            if len(title) > 35 and not any(x in href for x in ['/autor/', '/tag/', '/usuario/']):
                full_url = href if href.startswith('http') else prefix + href
                if full_url not in [n['link'] for n in news_data]:
                    news_data.append({"title": title, "link": full_url})
                    if len(news_data) == 5: break
        return news_data
    except:
        return []

# --- INTERFAZ ---

# Selector de idioma
col_title, col_lang = st.columns([0.8, 0.2])
with col_lang:
    lang_choice = st.selectbox("", ["🇺🇸 English", "🇰🇷 한국어"], label_visibility="collapsed")
    lang_code = "en" if "English" in lang_choice else "ko"

t = LANG_PACK[lang_code]

with col_title:
    st.title(t["title"])
    st.subheader(t["subheader"])

# Ribbon (Tabs)
tabs = st.tabs([t["global_tab"]] + list(SITES.keys()))

# 1. Pestaña Global
with tabs[0]:
    if st.button(t["refresh_btn"], key="btn_global"):
        st.cache_data.clear()
        st.rerun()
    
    with st.spinner(t["loading_scraping"]):
        global_hot = []
        for name, data in SITES.items():
            h = scrape_headlines(data["url"], data["prefix"])
            if h: global_hot.append({"medio": name, "news": h[0]})
        
        for i, item in enumerate(global_hot[:5], 1):
            with st.expander(f"{i}. [{item['medio']}] {translate_text(item['news']['title'], lang_code)}"):
                st.write(f"🔗 [{t['read_more']}]({item['news']['link']})")

# 2. Pestañas de Medios Individuales
for i, (name, data) in enumerate(SITES.items(), 1):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=f"btn_{name}"):
            st.cache_data.clear()
            st.rerun()
            
        st.header(f"{name}")
        headlines = scrape_headlines(data["url"], data["prefix"])
        
        if not headlines:
            st.warning(t["no_news"])
        
        for idx, news in enumerate(headlines, 1):
            st.subheader(f"{idx}. {translate_text(news['title'], lang_code)}")
            st.caption(f"🔗 [{t['read_more']}]({news['link']})")
            
            if st.button(f"✨ {t['ai_summary']}", key=f"sum_{name}_{idx}"):
                with st.spinner(t["loading_ai"]):
                    text = extract_article_text(news['link'])
                    if text:
                        raw_summary = query_ai_summarizer(text)
                        if raw_summary == "BUSY":
                            st.warning(t["ai_busy"])
                        elif raw_summary == "TOKEN_ERROR":
                            st.error(t["token_error"])
                        elif raw_summary:
                            st.info(translate_text(raw_summary, lang_code))
                        else:
                            st.error(t["error_ai"])
                    else:
                        st.warning(t["no_text"])
            st.divider()
