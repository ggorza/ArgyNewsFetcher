import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
import pandas as pd

# Configuración de los medios y sus selectores básicos
SITES = {
    "Infobae": "https://www.infobae.com",
    "Clarín": "https://www.clarin.com",
    "Cronista": "https://www.cronista.com",
    "La Nación": "https://www.lanacion.com.ar",
    "BA Herald": "https://buenosairesherald.com",
    "Perfil": "https://www.perfil.com"
}

def translate_text(text, lang):
    try:
        return GoogleTranslator(source='auto', target=lang).translate(text)
    except:
        return "Error en traducción"

@st.cache_data(ttl=600) # Guarda los resultados por 10 min para que sea veloz
def scrape_news(site_name, url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = []
        
        # Selectores genéricos que funcionan en la mayoría de estos sitios
        # Buscamos h1, h2 y h3 que suelen ser los títulos
        tags = soup.find_all(['h1', 'h2', 'h3'], limit=15)
        
        for tag in tags:
            title = tag.get_text().strip()
            if len(title) > 25: # Evitamos menús o textos cortos
                headlines.append(title)
                if len(headlines) == 5: break
        return headlines
    except:
        return ["No se pudo cargar la información de este sitio."]

# --- Interfaz ---
st.set_page_config(page_title="Monitor de Noticias ARG", layout="wide")
st.title("🇦🇷 Monitor de Medios en Tiempo Real")

# El "Ribbon" de selección
opciones = ["Resumen Global 🔥"] + list(SITES.keys())
seleccion = st.tabs(opciones)

# Lógica para el Resumen Global
with seleccion[0]:
    st.header("Top 5 Noticias del Momento (Todos los medios)")
    all_news = []
    with st.spinner('Analizando todos los medios...'):
        for name, url in SITES.items():
            titles = scrape_news(name, url)
            # El primero de cada medio es el más importante (score alto)
            if titles:
                all_news.append({"medio": name, "titulo": titles[0]})
    
    # Mostramos las 5 primeras (una de cada uno de los primeros 5 medios)
    for i, item in enumerate(all_news[:5], 1):
        with st.expander(f"{i}. [{item['medio']}] {item['titulo']}"):
            col1, col2 = st.columns(2)
            col1.write(f"**English:**\n{translate_text(item['titulo'], 'en')}")
            col2.write(f"**Korean:**\n{translate_text(item['titulo'], 'ko')}")

# Lógica para cada medio individual
for i, (name, url) in enumerate(SITES.items(), 1):
    with seleccion[i]:
        st.header(f"Noticias destacadas de {name}")
        titles = scrape_news(name, url)
        
        for idx, t in enumerate(titles, 1):
            st.subheader(f"{idx}. {t}")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"🇬🇧 {translate_text(t, 'en')}")
            with c2:
                st.success(f"🇰🇷 {translate_text(t, 'ko')}")
            st.divider()
