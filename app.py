import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import feedparser

# 1. Configuración de página - Indispensable
st.set_page_config(page_title="Argy News for SEASA Employees", layout="wide", page_icon="📰")

# --- CONFIGURACIÓN DE IA ---
API_TOKEN = st.secrets.get("HF_TOKEN", "")
API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-cnn"
headers_ai = {"Authorization": f"Bearer {API_TOKEN}"}

# --- CONFIGURACIÓN DE MEDIOS ---
SITES_CONFIG = {
    "Infobae": {
        "home": "https://www.infobae.com",
        "rss": "https://www.infobae.com/feeds/rss/",
        "prefix": "https://www.infobae.com",
        "categories": {
            "POLITICS": "https://www.infobae.com/feeds/rss/politica/",
            "ECONOMY": "https://www.infobae.com/feeds/rss/economia/",
            "SPORTS": "https://www.infobae.com/feeds/rss/deportes/",
            "TECH & BIZ": "https://www.infobae.com/feeds/rss/tecno/"
        }
    },
    "Clarín": {
        "home": "https://www.clarin.com",
        "rss": "https://www.clarin.com/rss/lo-ultimo/",
        "prefix": "https://www.clarin.com",
        "categories": {
            "POLITICS": "https://www.clarin.com/rss/politica/",
            "ECONOMY": "https://www.clarin.com/rss/economia/",
            "SPORTS": "https://www.clarin.com/rss/deportes/",
            "TECH & BIZ": "https://www.clarin.com/rss/tecnologia/"
        }
    },
    "TN": {
        "home": "https://tn.com.ar",
        "rss": "https://tn.com.ar/rss.xml",
        "prefix": "https://tn.com.ar",
        "categories": {
            "POLITICS": "https://tn.com.ar/rss/politica/",
            "ECONOMY": "https://tn.com.ar/rss/economia/",
            "SPORTS": "https://tn.com.ar/rss/deportes/",
            "TECH & BIZ": "https://tn.com.ar/rss/tecno/"
        }
    },
    "Ámbito": {
        "home": "https://www.ambito.com",
        "rss": "https://www.ambito.com/rss/pages/home.xml",
        "prefix": "",
        "categories": {
            "ECONOMY": "https://www.ambito.com/rss/pages/economia.xml",
            "TECH & BIZ": "https://www.ambito.com/rss/pages/negocios.xml"
        }
    },
    "La Nación": {
        "home": "https://www.lanacion.com.ar",
        "rss": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml",
        "prefix": "https://www.lanacion.com.ar",
        "categories": {
            "POLITICS": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/politica/?outputType=xml",
            "ECONOMY": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml",
            "SPORTS": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/deportes/?outputType=xml"
        }
    },
    "Perfil": {
        "home": "https://www.perfil.com",
        "rss": "https://www.perfil.com/rss/ultimo-momento.xml",
        "prefix": "",
        "categories": {
            "POLITICS": "https://www.perfil.com/rss/politica.xml",
            "SPORTS": "https://www.perfil.com/rss/deportes.xml"
        }
    }
}

# --- TRADUCCIONES ---
LANG_PACK = {
    "en": {
        "title": "Argy News for SEASA Employees",
        "subheader": "Top 5 news from each newspaper, at a glance",
        "refresh_btn": "Full Data Reset",
        "loading": "Connecting...",
        "read_more": "Read more",
        "ai_summary": "AI Summary",
        "no_text": "Content blocked or too short.",
        "tabs_cat": ["🔥 Politics", "💰 Economy", "⚽ Sports", "🚀 Tech & Biz"]
    },
    "ko": {
        "title": "SEASA 임직원을 위한 Argy News",
        "subheader": "카테고리별 주요 뉴스를 한눈에 확인하세요",
        "refresh_btn": "전체 데이터 초기화",
        "loading": "연결 중...",
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

@st.cache_data(ttl=300)
def super_fetch(url, prefix, is_rss=True):
    """Fetcher robusto que alterna entre RSS y Scraping Directo"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    # 1. Intentar RSS con feedparser sobre un Request manual
    if is_rss:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                feed = feedparser.parse(r.content)
                if feed.entries:
                    return [{"title": e.title, "link": e.link} for e in feed.entries[:5]]
        except: pass

    # 2. Fallback a Scraping Directo (Lo que andaba antes)
    try:
        target_url = url if not is_rss else prefix # Si el RSS falla, vamos a la Home
        r = requests.get(target_url, headers=headers, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            news = []
            # Buscamos links con texto largo en h1, h2, h3
            for tag in soup.find_all(['h1', 'h2', 'h3', 'a'], href=True):
                a_tag = tag if tag.name == 'a' else tag.find('a', href=True)
                if not a_tag: continue
                title = a_tag.get_text().strip()
                href = a_tag['href']
                if len(title) > 35 and not any(x in href.lower() for x in ['/autor/', '/tag/', '/usuario/']):
                    full_url = href if href.startswith('http') else prefix + href
                    if full_url not in [n['link'] for n in news]:
                        news.append({"title": title, "link": full_url})
                    if len(news) == 5: break
            return news
    except: return []
    return []

@st.cache_data(ttl=3600)
def get_body(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 80])
        return text if len(text) > 300 else None
    except: return None

# --- INTERFAZ ---
c1, c2 = st.columns([0.8, 0.2])
with c2:
    lang_choice = st.selectbox("", ["🇺🇸 English", "🇰🇷 한국어"], label_visibility="collapsed")
    lang = "en" if "English" in lang_choice else "ko"
t = LANG_PACK[lang]

with c1:
    st.title(t["title"])
    st.subheader(t["subheader"])

cat_keys = ["POLITICS", "ECONOMY", "SPORTS", "TECH & BIZ"]
tabs = st.tabs(t["tabs_cat"] + list(SITES_CONFIG.keys()))

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

# 1. Pestañas de Categorías
for i, cat in enumerate(cat_keys):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=f"re_{cat}"):
            st.cache_data.clear()
            st.rerun()
        with st.spinner(t["loading"]):
            cat_data = []
            for name, config in SITES_CONFIG.items():
                if cat in config["categories"]:
                    news = super_fetch(config["categories"][cat], config["prefix"])
                    if news: cat_data.append({"source": name, "item": news[0]})
            for idx, entry in enumerate(cat_data[:5], 1):
                render_news(idx, entry['item'], entry['source'], cat)

# 2. Pestañas Individuales
for i, (name, config) in enumerate(SITES_CONFIG.items(), len(cat_keys)):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=f"re_{name}"):
            st.cache_data.clear()
            st.rerun()
        with st.spinner(t["loading"]):
            news_list = super_fetch(config["rss"], config["prefix"])
            if not news_list:
                st.error(f"⚠️ {name} connection issue. Try resetting data.")
            else:
                for idx, item in enumerate(news_list, 1):
                    render_news(idx, item, name, name)
