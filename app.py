import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

# 1. Configuración de página
st.set_page_config(page_title="ARG News AI Monitor", layout="wide", page_icon="📰")

# --- CONFIGURACIÓN DE IA (URL ACTUALIZADA) ---
API_TOKEN = st.secrets.get("HF_TOKEN", "")

# Usamos el nuevo endpoint "router" que solicita Hugging Face
API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-cnn"
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

# --- TRADUCCIONES ---
LANG_PACK = {
    "en": {
        "title": "🇦🇷 ARG News AI Monitor",
        "subheader": "Real-time headlines and AI-generated summaries.",
        "refresh_btn": "Refresh News",
        "loading": "Processing...",
        "global_tab": "🔥 Global Hot Topics",
        "read_more": "Read full article",
        "ai_summary": "AI Summary",
        "no_text": "Article text too short for AI.",
        "no_news": "Could not find headlines."
    },
    "ko": {
        "title": "🇦🇷 아르헨티나 뉴스 AI 모니터",
        "subheader": "실시간 헤드라인 및 AI 생성 요약.",
        "refresh_btn": "뉴스 새로고침",
        "loading": "처리 중...",
        "global_tab": "🔥 글로벌 핫토픽",
        "read_more": "전체 기사 읽기",
        "ai_summary": "AI 요약",
        "no_text": "텍스트가 너무 짧습니다.",
        "no_news": "뉴스를 찾을 수 없습니다."
    }
}

# --- FUNCIONES ---

def translate(text, lang):
    if not text: return ""
    try: return GoogleTranslator(target=lang).translate(text)
    except: return text

def query_ai_summarizer(text):
    if not API_TOKEN: return "ERROR: No token found in Secrets"
    
    clean_text = text.replace("\n", " ").strip()[:3000]
    payload = {
        "inputs": clean_text, 
        "parameters": {"min_length": 50, "max_length": 150},
        "options": {"wait_for_model": True} # Obliga a esperar si el modelo está cargando
    }
    
    try:
        response = requests.post(API_URL, headers=headers_ai, json=payload, timeout=40)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('summary_text', "Unexpected result format")
            return "Could not generate summary."
        
        # Si sigue fallando, mostramos el error técnico para saber qué pasa
        return f"TECH_ERROR: Code {response.status_code} - {response.text}"
        
    except Exception as e:
        return f"CONNECTION_FAILED: {str(e)}"

@st.cache_data(ttl=3600)
def get_body(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 70])
        return text if len(text) > 300 else None
    except:
        return None

@st.cache_data(ttl=300)
def get_headlines(url, prefix):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    news = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = soup.find_all('a', href=True)
        for link in links:
            title = link.get_text().strip()
            href = link['href']
            # Filtro para títulos relevantes
            if len(title) > 45 and not any(x in href for x in ['/autor/', '/tag/', '/usuario/', 'newsletter']):
                full_url = href if href.startswith('http') else prefix + href
                if full_url not in [n['link'] for n in news]:
                    news.append({"title": title, "link": full_url})
            if len(news) == 5: break
        return news
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

tabs = st.tabs([t["global_tab"]] + list(SITES.keys()))

# Tab Global
with tabs[0]:
    if st.button(t["refresh_btn"], key="gbl"): 
        st.cache_data.clear()
        st.rerun()
    with st.spinner(t["loading"]):
        global_news = []
        for name, info in SITES.items():
            h = get_headlines(info['url'], info['prefix'])
            if h:
                with st.expander(f"[{name}] {translate(h[0]['title'], lang)}"):
                    st.write(f"🔗 [{t['read_more']}]({h[0]['link']})")

# Tabs Individuales
for i, (name, info) in enumerate(SITES.items(), 1):
    with tabs[i]:
        if st.button(t["refresh_btn"], key=name):
            st.cache_data.clear()
            st.rerun()
        
        headlines = get_headlines(info['url'], info['prefix'])
        if not headlines:
            st.warning(t["no_news"])
        
        for idx, n in enumerate(headlines, 1):
            st.subheader(f"{idx}. {translate(n['title'], lang)}")
            st.caption(f"🔗 [{t['read_more']}]({n['link']})")
            
            if st.button(f"✨ {t['ai_summary']}", key=f"{name}_{idx}"):
                with st.spinner(t["loading"]):
                    body = get_body(n['link'])
                    if body:
                        res = query_ai_summarizer(body)
                        if "TECH_ERROR" in res or "CONNECTION" in res:
                            st.error(res)
                        else:
                            st.info(translate(res, lang))
                    else:
                        st.warning(t["no_text"])
            st.divider()
