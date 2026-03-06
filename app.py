import streamlit as st
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

def get_infobae_news():
    url = "https://www.infobae.com"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    news_list = []
    # Buscamos los contenedores de las noticias principales
    # Nota: Los selectores pueden variar si Infobae cambia su diseño
    headlines = soup.find_all(['h1', 'h2'], limit=10) 
    
    for item in headlines:
        title = item.get_text().strip()
        if len(title) > 20: # Filtro básico para evitar ruido
            news_list.append(title)
            if len(news_list) == 5:
                break
    return news_list

def translate(text, lang):
    try:
        return GoogleTranslator(source='auto', target=lang).translate(text)
    except:
        return "Translation Error"

# --- Interfaz de Streamlit ---
st.set_page_config(page_title="Infobae News Translator", page_icon="📰")
st.title("📰 Infobae: Top 5 Headlines")
st.subheader("Traducción automática a Inglés y Coreano")

if st.button('Actualizar Noticias'):
    with st.spinner('Scrapeando y traduciendo...'):
        headlines = get_infobae_news()
        
        for i, news in enumerate(headlines, 1):
            st.markdown(f"### {i}. {news}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("**English**")
                st.write(translate(news, 'en'))
            
            with col2:
                st.success("**Korean (한국어)**")
                st.write(translate(news, 'ko'))
            st.divider()
else:
    st.write("Presioná el botón para obtener las noticias del momento.")