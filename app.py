import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# 1. Configuración de página
st.set_page_config(page_title="ARG News AI Monitor", layout="wide", page_icon="📰")

# --- CONFIGURACIÓN DE IA ---
API_TOKEN = st.secrets.get("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
headers_ai = {"Authorization": f"Bearer {API_TOKEN}"}

# --- CONFIGURACIÓN DE MEDIOS (Ajustada para mayor éxito) ---
SITES = {
    "Infobae": {"url": "https://www.infobae.com", "prefix": "https://www.infobae.com"},
    "Clarín": {"url": "https://www.clarin.com", "prefix": "https://www.clarin.com"},
    "Cronista": {"url": "https://www.cronista.com", "prefix": "https://www.cronista.com"},
    "La Nación": {"url": "https://www.lanacion.com.ar", "prefix": "https://www.lanacion.com.ar"},
    "BA Herald": {"url": "https://buenosairesherald.com", "prefix": ""},
    "Perfil": {"url": "https://www.perfil.com", "prefix": ""}
}

# --- TRADUCCIONES ---
LANG_PACK = {
    "en": {
        "title": "🇦🇷 ARG News AI Monitor",
        "subheader": "Real-time headlines and AI-generated summaries.",
        "refresh_btn": "Refresh News",
        "loading": "Loading...",
        "global_tab": "🔥 Global Hot Topics",
        "read_more": "Read full article",
        "ai_summary": "AI Summary",
        "no_text": "Article too short for AI to process.",
        "ai_busy": "AI is busy or loading. Please wait 20 seconds and try again.",
        "ai_error": "AI Error: Check if your Token is valid.",
        "no_news": "Could not find headlines for this site."
    },
    "ko": {
        "title": "🇦🇷 아르헨티나 뉴스 AI 모니터",
        "subheader": "실시간 헤드라인 및 AI 생성 요약.",
        "refresh_btn": "뉴스 새로고침",
        "loading": "로딩 중...",
        "global_tab": "🔥 글로벌 핫토픽",
        "read_more": "전체 기사 읽기",
        "ai_summary": "AI 요약",
        "no_text": "기사가 너무 짧아 요약할 수 없습니다.",
        "ai_busy": "AI가 사용 중이거나 로딩 중입니다. 20초 후에 다시 시도하세요.",
        "ai_error": "AI 오류: 토큰이 유효한지 확인하세요.",
        "no_news": "뉴스 헤드라인을 찾을 수 없습니다."
    }
}

# --- FUNCIONES CORE ---
def translate(text, lang):
    if not text: return ""
    try: return GoogleTranslator(target=lang).translate(text)
    except: return text

def query_ai(text):
    if not API_TOKEN: return "Missing Token"
    payload = {"inputs": text, "parameters": {"min_length": 40, "max_length": 140}}
    try:
        response = requests.post(API_URL, headers=headers_ai, json=payload, timeout=20)
        if response.status_code == 503: return "BUSY"
        if response.status_code == 401: return "TOKEN_ERROR"
        res = response.json()
        return res[0]['summary_text'] if isinstance(res, list) else None
    except: return None

@st.cache_data(ttl=600)
def get_headlines(site_name, url, prefix):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    news = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Estrategia agresiva: buscamos todos los links que parezcan noticias
        links = soup.find_all('a', href=True)
        for link in links:
            title = link.get_text().strip()
            href = link['href']
            # Filtros: títulos largos y evitar links internos (Secciones, Login, etc)
            if len(title) > 35 and not any(x in href for x in ['/autor/', '/tag/', '/usuario/']):
                full_url = href if href.startswith('http') else prefix + href
                if full_url not in [n['link'] for n in news]:
                    news.append({"title": title, "link": full_url})
            if len(news) == 5: break
        return news
    except: return []

@st.cache_data(ttl=3600)
def get_body(url):
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 60])
        return text[:3500] if len(text) > 200 else None
    except: return None

# --- INTERFAZ ---
c1, c2 = st.columns([0.8, 0.2])
with c2:
    lang_choice = st.selectbox("", ["🇺🇸 English", "🇰🇷 한국어"])
    lang = "en" if "English" in lang_choice else "ko"
t = LANG_PACK[lang]

with c1:
    st.title(t["title"])
    st.subheader(t["subheader"])

tabs = st.tabs([t["global_tab"]] + list(SITES.keys()))

# Tab Global
with tabs[0]:
    if st.button(t["refresh_btn"], key="gbl"): 
        st.cache_data.clear()
        st.rerun()
    
    global_news = []
    for name, info in SITES.items():
        h = get_headlines(name, info['url'], info['prefix'])
        if h: global_news.append({"medio": name, "item": h[0]})
    
    for i, item in enumerate(global_news[:5], 1):
        with st.expander(f"{i}. [{item['medio']}] {translate(item['item']['title'], lang)}"):
            st.write(f"🔗 [{t['read_more']}]({item['item']['link']})")

# Tabs Individuales
for i, (name, info) in enumerate(SITES.items(), 1):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=name):
            st.cache_data.clear()
            st.rerun()
        
        headlines = get_headlines(name, info['url'], info['prefix'])
        if not headlines:
            st.warning(t["no_news"])
        
        for idx, n in enumerate(headlines, 1):
            st.subheader(f"{idx}. {translate(n['title'], lang)}")
            st.caption(f"🔗 [{t['read_more']}]({n['link']})")
            
            if st.button(f"✨ {t['ai_summary']}", key=f"{name}_{idx}"):
                with st.spinner(t["loading"]):
                    body = get_body(n['link'])
                    if body:
                        summary = query_ai(body)
                        if summary == "BUSY": st.warning(t["ai_busy"])
                        elif summary == "TOKEN_ERROR": st.error(t["ai_error"])
                        elif summary: st.info(translate(summary, lang))
                        else: st.error(t["ai_error"])
                    else:
                        st.warning(t["no_text"])
            st.divider()
