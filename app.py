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

# --- CONFIGURACIÓN ESTRUCTURADA DE MEDIOS (Con Web Sections para evitar repeticiones) ---
SITES_CONFIG = {
    "Infobae": {
        "prefix": "https://www.infobae.com",
        "rss_home": "https://www.infobae.com/feeds/rss/",
        "categories": {
            "POLITICS": {"rss": "https://www.infobae.com/feeds/rss/politica/", "web": "https://www.infobae.com/politica/"},
            "ECONOMY": {"rss": "https://www.infobae.com/feeds/rss/economia/", "web": "https://www.infobae.com/economia/"},
            "SPORTS": {"rss": "https://www.infobae.com/feeds/rss/deportes/", "web": "https://www.infobae.com/deportes/"},
            "TECH & BIZ": {"rss": "https://www.infobae.com/feeds/rss/tecno/", "web": "https://www.infobae.com/tecno/"}
        }
    },
    "Clarín": {
        "prefix": "https://www.clarin.com",
        "rss_home": "https://www.clarin.com/rss/lo-ultimo/",
        "categories": {
            "POLITICS": {"rss": "https://www.clarin.com/rss/politica/", "web": "https://www.clarin.com/politica/"},
            "ECONOMY": {"rss": "https://www.clarin.com/rss/economia/", "web": "https://www.clarin.com/economia/"},
            "SPORTS": {"rss": "https://www.clarin.com/rss/deportes/", "web": "https://www.clarin.com/deportes/"},
            "TECH & BIZ": {"rss": "https://www.clarin.com/rss/tecnologia/", "web": "https://www.clarin.com/tecnologia/"}
        }
    },
    "TN": {
        "prefix": "https://tn.com.ar",
        "rss_home": "https://tn.com.ar/rss.xml",
        "categories": {
            "POLITICS": {"rss": "https://tn.com.ar/rss/politica/", "web": "https://tn.com.ar/politica/"},
            "ECONOMY": {"rss": "https://tn.com.ar/rss/economia/", "web": "https://tn.com.ar/economia/"},
            "SPORTS": {"rss": "https://tn.com.ar/rss/deportes/", "web": "https://tn.com.ar/deportes/"},
            "TECH & BIZ": {"rss": "https://tn.com.ar/rss/tecno/", "web": "https://tn.com.ar/tecno/"}
        }
    },
    "Ámbito": {
        "prefix": "https://www.ambito.com",
        "rss_home": "https://www.ambito.com/rss/pages/home.xml",
        "categories": {
            "ECONOMY": {"rss": "https://www.ambito.com/rss/pages/economia.xml", "web": "https://www.ambito.com/contenidos/economia.html"},
            "TECH & BIZ": {"rss": "https://www.ambito.com/rss/pages/negocios.xml", "web": "https://www.ambito.com/contenidos/negocios.html"}
        }
    },
    "La Nación": {
        "prefix": "https://www.lanacion.com.ar",
        "rss_home": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml",
        "categories": {
            "POLITICS": {"rss": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/politica/?outputType=xml", "web": "https://www.lanacion.com.ar/politica/"},
            "ECONOMY": {"rss": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml", "web": "https://www.lanacion.com.ar/economia/"},
            "SPORTS": {"rss": "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/deportes/?outputType=xml", "web": "https://www.lanacion.com.ar/deportes/"}
        }
    },
    "Perfil": {
        "prefix": "https://www.perfil.com",
        "rss_home": "https://www.perfil.com/rss/ultimo-momento.xml",
        "categories": {
            "POLITICS": {"rss": "https://www.perfil.com/rss/politica.xml", "web": "https://www.perfil.com/seccion/politica"},
            "SPORTS": {"rss": "https://www.perfil.com/rss/deportes.xml", "web": "https://www.perfil.com/seccion/deportes"}
        }
    }
}

# --- TRADUCCIONES ---
LANG_PACK = {
    "en": {
        "title": "Argy News for SEASA Employees",
        "subheader": "Top headlines and AI summaries, at a glance",
        "refresh_btn": "Full Data Reset",
        "loading": "Processing...",
        "read_more": "Read more",
        "ai_summary": "AI Summary",
        "no_text": "Text blocked or too short.",
        "tabs_cat": ["🔥 Politics", "💰 Economy", "⚽ Sports", "🚀 Tech & Biz"]
    },
    "ko": {
        "title": "SEASA 임직원을 위한 Argy News",
        "subheader": "카테고리별 주요 뉴스 5개를 한눈에 확인하세요",
        "refresh_btn": "전체 데이터 초기화",
        "loading": "처리 중...",
        "read_more": "자세히 보기",
        "ai_summary": "AI 요약",
        "no_text": "텍스트가 너무 짧습니다.",
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
def fetch_robust(url_rss, url_web, prefix):
    """Estrategia de Doble Vía para evitar repeticiones y bloqueos"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.google.com/'
    }
    
    # 1. Intentar RSS
    try:
        r = requests.get(url_rss, headers=headers, timeout=10)
        if r.status_code == 200:
            feed = feedparser.parse(r.content)
            if feed.entries:
                return [{"title": e.title, "link": e.link} for e in feed.entries[:5]]
    except: pass

    # 2. Intentar Web Scraping Directo de la SECCIÓN (No de la Home)
    try:
        r = requests.get(url_web, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            news = []
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
            found_count = 1
            for name, config in SITES_CONFIG.items():
                if cat in config["categories"]:
                    # Llamamos con URLs específicas de la categoría
                    news = fetch_robust(config["categories"][cat]["rss"], config["categories"][cat]["web"], config["prefix"])
                    if news:
                        render_news(found_count, news[0], name, cat)
                        found_count += 1
                if found_count > 5: break

# 2. Pestañas Individuales
for i, (name, config) in enumerate(SITES_CONFIG.items(), len(cat_keys)):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=f"re_{name}"):
            st.cache_data.clear()
            st.rerun()
        with st.spinner(t["loading"]):
            # Aquí usamos el RSS Home
            news_list = fetch_robust(config["rss_home"], config["prefix"], config["prefix"])
            if not news_list:
                st.error(f"⚠️ {name} connection issue. This site has high security.")
            else:
                for idx, item in enumerate(news_list, 1):
                    render_news(idx, item, name, name)
