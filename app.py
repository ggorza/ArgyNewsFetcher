import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import feedparser

# 1. Configuración de página
st.set_page_config(page_title="Argy News for SEASA Employees", layout="wide", page_icon="📰")

# --- CONFIGURACIÓN DE IA ---
API_TOKEN = st.secrets.get("HF_TOKEN", "")
API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-cnn"
headers_ai = {"Authorization": f"Bearer {API_TOKEN}"}

# --- MAPEO DE CATEGORÍAS (RSS Verificados) ---
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
        "TN": "https://tn.com.ar/rss/deportes/"
    },
    "TECH & BIZ": {
        "Infobae": "https://www.infobae.com/feeds/rss/tecno/",
        "Clarín": "https://www.clarin.com/rss/tecnologia/",
        "Ámbito": "https://www.ambito.com/rss/pages/negocios.xml",
        "TN": "https://tn.com.ar/rss/tecno/"
    }
}

SITES_INDIVIDUAL = {
    "Infobae": "https://www.infobae.com/feeds/rss/",
    "Clarín": "https://www.clarin.com/rss/lo-ultimo/",
    "TN": "https://tn.com.ar/rss.xml",
    "Ámbito": "https://www.ambito.com/rss/pages/home.xml",
    "La Nación": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml",
    "Perfil": "https://www.perfil.com/rss/ultimo-momento.xml"
}

# --- TRADUCCIONES ---
LANG_PACK = {
    "en": {
        "title": "Argy News for SEASA Employees",
        "subheader": "Top headlines and AI summaries, at a glance",
        "refresh_btn": "Force Reload Data",
        "loading": "Connecting to servers...",
        "read_more": "Read more",
        "ai_summary": "AI Summary",
        "no_text": "Content blocked or too short.",
        "tabs_cat": ["🔥 Politics", "💰 Economy", "⚽ Sports", "🚀 Tech & Biz"]
    },
    "ko": {
        "title": "SEASA 임직원을 위한 Argy News",
        "subheader": "주요 헤드라인과 AI 요약을 한눈에 확인하세요",
        "refresh_btn": "데이터 강제 새로고침",
        "loading": "서버 연결 중...",
        "read_more": "자세히 보기",
        "ai_summary": "AI 요약",
        "no_text": "콘텐츠가 차단되었거나 너무 짧습니다.",
        "tabs_cat": ["🔥 정치", "💰 경제", "⚽ 스포츠", "🚀 기술/비즈니스"]
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
        return f"AI_ERROR: {response.status_code}"
    except: return "CONNECTION_FAILED"

@st.cache_data(ttl=3600)
def get_body(url):
    # Simulamos un navegador real para evitar bloqueos en el cuerpo de la noticia
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(r.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 75])
        return text if len(text) > 300 else None
    except: return None

@st.cache_data(ttl=300)
def fetch_news_feed(rss_url):
    """Usa feedparser para procesar RSS de forma profesional"""
    try:
        # Feedparser es más resistente a bloqueos que requests directo
        feed = feedparser.parse(rss_url)
        results = []
        for entry in feed.entries[:5]: # Tomamos los primeros 5
            results.append({
                "title": entry.title,
                "link": entry.link
            })
        return results
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

cat_names = list(CATEGORIES_RSS.keys())
all_tabs = st.tabs(t["tabs_cat"] + list(SITES_INDIVIDUAL.keys()))

def render_news(idx, item, source, key_prefix):
    st.subheader(f"{idx}. {translate(item['title'], lang)}")
    st.caption(f"📰 {source} | 🔗 [{t['read_more']}]({item['link']})")
    if st.button(f"✨ {t['ai_summary']}", key=f"btn_{key_prefix}_{idx}"):
        with st.spinner(t["loading"]):
            txt = get_body(item['link'])
            if txt:
                en_txt = translate(txt, 'en')
                summary = query_ai_summarizer(en_txt)
                st.info(translate(summary, lang))
            else: st.warning(t["no_text"])
    st.divider()

# 1. Pestañas de Categorías (Politics, Economy, etc)
for i, cat in enumerate(cat_names):
    with all_tabs[i]:
        if st.button(t["refresh_btn"], key=f"re_{cat}"):
            st.cache_data.clear()
            st.rerun()
        
        with st.spinner(t["loading"]):
            found_news = []
            for source, url in CATEGORIES_RSS[cat].items():
                feed_data = fetch_news_feed(url)
                if feed_data:
                    # Traemos la mejor de cada diario para esa categoría
                    found_news.append({"source": source, "item": feed_data[0]})
            
            if not found_news:
                st.warning("All sources are currently blocking the request. Try refreshing in 1 minute.")
            else:
                for idx, entry in enumerate(found_news[:5], 1):
                    render_news(idx, entry['item'], entry['source'], cat)

# 2. Pestañas de Medios Individuales
for i, (name, rss_url) in enumerate(SITES_INDIVIDUAL.items(), len(cat_names)):
    with all_tabs[i]:
        if st.button(t["refresh_btn"], key=f"re_{name}"):
            st.cache_data.clear()
            st.rerun()
            
        with st.spinner(t["loading"]):
            news_list = fetch_news_feed(rss_url)
            if not news_list:
                st.error(f"⚠️ {name} is blocking access. Our engineers are working on a fix.")
            else:
                for idx, item in enumerate(news_list, 1):
                    render_news(idx, item, name, name)
