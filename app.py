import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# 1. Configuración de página - Actualizado con el nuevo nombre
st.set_page_config(page_title="Argy News for SEASA Employees", layout="wide", page_icon="📰")

# --- CONFIGURACIÓN DE IA ---
API_TOKEN = st.secrets.get("HF_TOKEN", "")
API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-cnn"
headers_ai = {"Authorization": f"Bearer {API_TOKEN}"}

# --- CONFIGURACIÓN DE MEDIOS ---
SITES = {
    "Infobae": {"url": "https://www.infobae.com", "rss": "https://www.infobae.com/feeds/rss/", "prefix": "https://www.infobae.com"},
    "Clarín": {"url": "https://www.clarin.com", "rss": "https://www.clarin.com/rss/lo-ultimo/", "prefix": "https://www.clarin.com"},
    "Cronista": {"url": "https://www.cronista.com", "rss": "https://www.cronista.com/feeds/noticias.rss", "prefix": "https://www.cronista.com"},
    "La Nación": {"url": "https://www.lanacion.com.ar", "rss": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml", "prefix": "https://www.lanacion.com.ar"},
    "BA Herald": {"url": "https://buenosairesherald.com", "rss": "https://buenosairesherald.com/feed", "prefix": ""},
    "Perfil": {"url": "https://www.perfil.com", "rss": "https://www.perfil.com/rss/ultimo-momento.xml", "prefix": ""}
}

# --- DICCIONARIO DE IDIOMAS (Actualizado con tu pedido) ---
LANG_PACK = {
    "en": {
        "title": "Argy News for SEASA Employees",
        "subheader": "Top 5 news from each newspaper, at a glance",
        "refresh_btn": "Refresh News",
        "loading": "Processing AI summary...",
        "global_tab": "🔥 Global Hot Topics",
        "read_more": "Read full article",
        "ai_summary": "AI Summary",
        "no_text": "Article text too short for AI.",
        "no_news": "Could not find headlines."
    },
    "ko": {
        "title": "SEASA 임직원을 위한 Argy News",
        "subheader": "각 신문사별 주요 뉴스 5개를 한눈에 확인하세요",
        "refresh_btn": "뉴스 새로고침",
        "loading": "AI 요약 처리 중...",
        "global_tab": "🔥 글로벌 핫토픽",
        "read_more": "전체 기사 읽기",
        "ai_summary": "AI 요약",
        "no_text": "텍스트가 너무 짧습니다.",
        "no_news": "뉴스를 찾을 수 없습니다."
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
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('summary_text', "Error: Unexpected format")
        return f"TECH_ERROR: Code {response.status_code}"
    except: return "CONNECTION_FAILED"

@st.cache_data(ttl=3600)
def get_body(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 80])
        return text if len(text) > 300 else None
    except: return None

@st.cache_data(ttl=300)
def get_headlines(site_name, info):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    news = []
    # Primero intentamos RSS por estabilidad (especialmente para Cronista)
    try:
        r = requests.get(info['rss'], headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, features="xml")
        items = soup.find_all('item', limit=5)
        for item in items:
            title = item.title.text.strip()
            link = item.link.text.strip()
            if title and link:
                news.append({"title": title, "link": link})
    except: pass

    # Si el RSS falla, vamos al scraping tradicional
    if not news:
        try:
            r = requests.get(info['url'], headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all(['a'], href=True)
            for link in links:
                title = link.get_text().strip()
                href = link['href']
                if len(title) > 40 and not any(x in href.lower() for x in ['/autor/', '/tag/', '/usuario/', 'newsletter']):
                    full_url = href if href.startswith('http') else info['prefix'] + href
                    if full_url not in [n['link'] for n in news]:
                        news.append({"title": title, "link": full_url})
                if len(news) == 5: break
        except: pass
    return news

# --- INTERFAZ ---
c1, c2 = st.columns([0.8, 0.2])
with c2:
    lang_choice = st.selectbox("", ["🇺🇸 English", "🇰🇷 한국어"], label_visibility="collapsed")
    lang = "en" if "English" in lang_choice else "ko"
t = LANG_PACK[lang]

with c1:
    st.title(t["title"])
    st.subheader(t["subheader"])

tabs = st.tabs([t["global_tab"]] + list(SITES.keys()))

def display_news_item(idx, news_obj, source_name, tab_key):
    st.subheader(f"{idx}. {translate(news_obj['title'], lang)}")
    st.caption(f"📰 {source_name} | 🔗 [{t['read_more']}]({news_obj['link']})")
    if st.button(f"✨ {t['ai_summary']}", key=f"ai_{tab_key}_{idx}"):
        with st.spinner(t["loading"]):
            body_es = get_body(news_obj['link'])
            if body_es:
                body_en = translate(body_es, 'en')
                summary_en = query_ai_summarizer(body_en)
                if "TECH_ERROR" in summary_en:
                    st.error(summary_en)
                else:
                    st.info(translate(summary_en, lang))
            else:
                st.warning(t["no_text"])
    st.divider()

# TAB GLOBAL
with tabs[0]:
    if st.button(t["refresh_btn"], key="btn_gbl"): 
        st.cache_data.clear()
        st.rerun()
    with st.spinner(t["loading"]):
        global_news = []
        for name, info in SITES.items():
            h = get_headlines(name, info)
            if h: global_news.append({"source": name, "item": h[0]})
        for i, entry in enumerate(global_news[:6], 1):
            display_news_item(i, entry['item'], entry['source'], "global")

# TABS INDIVIDUALES
for i, (name, info) in enumerate(SITES.items(), 1):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=name):
            st.cache_data.clear()
            st.rerun()
        headlines = get_headlines(name, info)
        if not headlines:
            st.warning(t["no_news"])
        else:
            for idx, n in enumerate(headlines, 1):
                display_news_item(idx, n, name, name)
