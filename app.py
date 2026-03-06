import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# 1. Configuración de página
st.set_page_config(page_title="Argy News for SEASA Employees", layout="wide", page_icon="📰")

# --- CONFIGURACIÓN DE IA ---
API_TOKEN = st.secrets.get("HF_TOKEN", "")
API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-cnn"
headers_ai = {"Authorization": f"Bearer {API_TOKEN}"}

# --- MAPEO DE CATEGORÍAS Y RSS ---
# Definimos los feeds específicos para cada sección
CATEGORIES_RSS = {
    "POLITICS": {
        "Infobae": "https://www.infobae.com/feeds/rss/politica/",
        "Clarín": "https://www.clarin.com/rss/politica/",
        "La Nación": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/politica/?outputType=xml",
        "TN": "https://tn.com.ar/rss/politica/",
        "Perfil": "https://www.perfil.com/rss/politica.xml"
    },
    "ECONOMY": {
        "Infobae": "https://www.infobae.com/feeds/rss/economia/",
        "Clarín": "https://www.clarin.com/rss/economia/",
        "Ámbito": "https://www.ambito.com/rss/pages/economia.xml",
        "La Nación": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml",
        "TN": "https://tn.com.ar/rss/economia/"
    },
    "SPORTS": {
        "Infobae": "https://www.infobae.com/feeds/rss/deportes/",
        "Clarín": "https://www.clarin.com/rss/deportes/",
        "La Nación": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/deportes/?outputType=xml",
        "TN": "https://tn.com.ar/rss/deportes/",
        "Perfil": "https://www.perfil.com/rss/deportes.xml"
    },
    "TECH & BUSINESS": {
        "Infobae": "https://www.infobae.com/feeds/rss/tecno/",
        "Clarín": "https://www.clarin.com/rss/tecnologia/",
        "Ámbito": "https://www.ambito.com/rss/pages/negocios.xml",
        "TN": "https://tn.com.ar/rss/tecno/",
        "La Nación": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/tecnologia/?outputType=xml"
    }
}

SITES_GENERAL = {
    "Infobae": {"url": "https://www.infobae.com", "rss": "https://www.infobae.com/feeds/rss/", "prefix": "https://www.infobae.com"},
    "Clarín": {"url": "https://www.clarin.com", "rss": "https://www.clarin.com/rss/lo-ultimo/", "prefix": "https://www.clarin.com"},
    "TN": {"url": "https://tn.com.ar", "rss": "https://tn.com.ar/rss.xml", "prefix": "https://tn.com.ar"},
    "Ámbito": {"url": "https://www.ambito.com", "rss": "https://www.ambito.com/rss/pages/home.xml", "prefix": ""},
    "La Nación": {"url": "https://www.lanacion.com.ar", "rss": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml", "prefix": "https://www.lanacion.com.ar"},
    "BA Herald": {"url": "https://buenosairesherald.com", "rss": "https://buenosairesherald.com/feed", "prefix": ""},
    "Perfil": {"url": "https://www.perfil.com", "rss": "https://www.perfil.com/rss/ultimo-momento.xml", "prefix": ""}
}

# --- TRADUCCIONES ---
LANG_PACK = {
    "en": {
        "title": "Argy News for SEASA Employees",
        "subheader": "Top 5 news from each category, at a glance",
        "refresh_btn": "Refresh News",
        "loading": "AI is processing...",
        "read_more": "Read more",
        "ai_summary": "AI Summary",
        "no_text": "Text too short.",
        "tabs_cat": ["🔥 Politics", "💰 Economy", "⚽ Sports", "🚀 Tech & Biz"]
    },
    "ko": {
        "title": "SEASA 임직원을 위한 Argy News",
        "subheader": "카테고리별 주요 뉴스 5개를 한눈에 확인하세요",
        "refresh_btn": "뉴스 새로고침",
        "loading": "AI 처리 중...",
        "read_more": "자세히 보기",
        "ai_summary": "AI 요약",
        "no_text": "텍스트가 너무 짧습니다.",
        "tabs_cat": ["🔥 정치", "💰 경제", "⚽ 스포츠", "🚀 기술 및 비즈니스"]
    }
}

# --- FUNCIONES ---

def translate(text, target_lang):
    if not text or len(text) < 3: return text
    try: return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except: return text

def query_ai_summarizer(text_en):
    if not API_TOKEN: return "ERROR: No token found"
    clean_text = text_en.replace("\n", " ").strip()[:2500]
    payload = {"inputs": clean_text, "parameters": {"min_length": 40, "max_length": 140}, "options": {"wait_for_model": True}}
    try:
        response = requests.post(API_URL, headers=headers_ai, json=payload, timeout=40)
        if response.status_code == 200:
            result = response.json()
            return result[0].get('summary_text', "Error")
        return f"TECH_ERROR: {response.status_code}"
    except: return "CONNECTION_FAILED"

@st.cache_data(ttl=3600)
def get_body(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 80])
        return text if len(text) > 300 else None
    except: return None

@st.cache_data(ttl=300)
def get_headlines_from_rss(rss_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(rss_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, features="xml")
        items = soup.find_all('item', limit=3) # Tomamos los primeros para asegurar relevancia
        return [{"title": i.title.text.strip(), "link": i.link.text.strip()} for i in items if i.title and i.link]
    except: return []

# --- INTERFAZ ---
c1, c2 = st.columns([0.8, 0.2])
with c2:
    lang_choice = st.selectbox("", ["🇺🇸 English", "🇰🇷 한국어"], label_visibility="collapsed")
    lang = "en" if "English" in lang_choice else "ko"
t = LANG_PACK[lang]

with c1:
    st.title(t["title"])
    st.subheader(t["subheader"])

# Definimos las pestañas: Categorías primero, luego diarios individuales
cat_list = list(CATEGORIES_RSS.keys())
tabs = st.tabs(t["tabs_cat"] + list(SITES_GENERAL.keys()))

def display_news_item(idx, news_obj, source_name, tab_key):
    st.subheader(f"{idx}. {translate(news_obj['title'], lang)}")
    st.caption(f"📰 {source_name} | 🔗 [{t['read_more']}]({news_obj['link']})")
    if st.button(f"✨ {t['ai_summary']}", key=f"ai_{tab_key}_{idx}"):
        with st.spinner(t["loading"]):
            body_es = get_body(news_obj['link'])
            if body_es:
                body_en = translate(body_es, 'en')
                summary_en = query_ai_summarizer(body_en)
                st.info(translate(summary_en, lang))
            else: st.warning(t["no_text"])
    st.divider()

# --- LÓGICA DE CATEGORÍAS (TABS 0 a 3) ---
for i, cat_name in enumerate(cat_list):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=f"ref_{cat_name}"):
            st.cache_data.clear()
            st.rerun()
        
        with st.spinner(t["loading"]):
            cat_news = []
            for site, rss in CATEGORIES_RSS[cat_name].items():
                h = get_headlines_from_rss(rss)
                if h: cat_news.append({"source": site, "item": h[0]})
            
            # Mostramos las 5 más relevantes (una de cada diario)
            for idx, entry in enumerate(cat_news[:5], 1):
                display_news_item(idx, entry['item'], entry['source'], cat_name)

# --- LÓGICA DE DIARIOS INDIVIDUALES (RESTO DE TABS) ---
for i, (name, info) in enumerate(SITES_GENERAL.items(), len(cat_list)):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=f"ref_{name}"):
            st.cache_data.clear()
            st.rerun()
        
        with st.spinner(t["loading"]):
            headlines = get_headlines_from_rss(info['rss'])
            if not headlines: st.warning("No news found.")
            else:
                for idx, n in enumerate(headlines, 1):
                    display_news_item(idx, n, name, name)
