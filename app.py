import streamlit as st
import sqlite3
import feedparser
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from fpdf import FPDF
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIGURACIÓN INICIAL Y UI
# ==========================================
st.set_page_config(page_title="BESS-PV SPAIN INTELLIGENCE HUB", layout="wide")
st.title("🔋 BESS-PV SPAIN INTELLIGENCE HUB")
st.markdown("Centro de inteligencia estratégica para proyectos de FV y Almacenamiento.")

# Configurar API de Gemini (Debe guardarse en st.secrets)
API_KEY = st.secrets.get("GEMINI_API_KEY", "TU_API_KEY_AQUI")
genai.configure(api_key=API_KEY)
modelo_ia = genai.GenerativeModel('gemini-1.5-pro')

# ==========================================
# BASE DE DATOS LOCAL (SQLite - Histórico 60 días)
# ==========================================
def init_db():
    conn = sqlite3.connect('bess_intelligence.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY, date TEXT, title TEXT, source TEXT, link TEXT, content TEXT, ai_analysis TEXT)''')
    # Limpiar noticias con más de 60 días de antigüedad
    cutoff_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    c.execute("DELETE FROM news WHERE date < ?", (cutoff_date,))
    conn.commit()
    return conn

conn = init_db()

# ==========================================
# MÓDULO DE RECOLECCIÓN (RSS Y SCRAPING)
# ==========================================
KEYWORDS = ["BESS", "Almacenamiento", "Fotovoltaica", "Hibridación", "Peajes", "Servicios de Ajuste", "RD"]

def fetch_rss_feeds():
    # Fuentes sectoriales gratuitas
    feeds = {
        "PV Magazine España": "https://www.pv-magazine.es/feed/",
        "El Periódico de la Energía": "https://elperiodicodelaenergia.com/feed/",
        "Energías Renovables": "https://www.energias-renovables.com/rss/renovables.xml"
    }
    
    recolectado = []
    for source, url in feeds.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # Últimas 5 noticias por fuente
                # Filtrar por palabras clave
                if any(kw.lower() in entry.title.lower() or kw.lower() in entry.description.lower() for kw in KEYWORDS):
                    recolectado.append({
                        "date": datetime.now().strftime('%Y-%m-%d'),
                        "title": entry.title,
                        "source": source,
                        "link": entry.link,
                        "content": entry.description
                    })
        except Exception as e:
            continue
    return recolectado

# ==========================================
# CEREBRO DE ANÁLISIS CRÍTICO (Gemini)
# ==========================================
def generar_analisis_ia(texto_noticia):
    prompt = f"""
    Actúa como un Arquitecto de Software Senior y un Ingeniero Energético experto en el mercado español (FV + BESS).
    Analiza la siguiente noticia o conjunto de noticias del sector:
    "{texto_noticia}"
    
    Debes estructurar tu respuesta en un lenguaje técnico-ejecutivo con los siguientes puntos:
    1. Análisis Crítico Neutral: Compara enfoques y da una opinión técnica realista sin sesgos comerciales.
    2. Análisis Regulatorio: Identifica posibles impactos directos en el CAPEX y OPEX de los proyectos.
    3. Espejo Internacional: Compara esta situación con mercados líderes (Australia, UK, California). Explica qué ocurrió allí en situaciones similares (canibalización, saturación de servicios de ajuste) y predice el impacto en España.
    """
    try:
        response = modelo_ia.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error de la IA: {str(e)}"

# ==========================================
# VISUALIZACIÓN DE GRÁFICAS (Plotly - ESIOS Simulado)
# ==========================================
def mostrar_dashboard_mercado():
    st.subheader("📈 Mercado: Evolución de Precios y Curva de Pato")
    st.markdown("*(Integración con API pública de ESIOS)*")
    
    # Simulación de datos para Plotly (Curva de pato)
    horas = list(range(24))
    precios = [45, 42, 40, 38, 38, 40, 50, 70, 65, 40, 10, 0, 0, 0, 5, 20, 60, 120, 140, 110, 90, 75, 60, 50]
    df = pd.DataFrame({"Hora": horas, "Precio Marginal OMIE (€/MWh)": precios})
    
    fig = px.line(df, x="Hora", y="Precio Marginal OMIE (€/MWh)", 
                  title="Tendencia diaria (Efecto Canibalización FV)",
                  markers=True, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# EXPORTACIÓN A PDF (Informes Técnicos)
# ==========================================
def exportar_pdf(titulo, contenido):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="REPORTE DE INTELIGENCIA ESTRATÉGICA BESS-PV", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=f"Título: {titulo}\n\nAnálisis:\n{contenido}".encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# INTERFAZ DE USUARIO (UI)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Principal", "📰 Histórico (60 días)", "⚙️ Panel de Control"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Última Inteligencia de Mercado")
        if st.button("🔄 Ejecutar Extracción y Análisis Ahora"):
            with st.spinner("Extrayendo datos de RSS, BOE, y ESIOS..."):
                noticias = fetch_rss_feeds()
                for n in noticias:
                    analisis = generar_analisis_ia(n['content'])
                    # Guardar en SQLite
                    c = conn.cursor()
                    c.execute("INSERT INTO news (date, title, source, link, content, ai_analysis) VALUES (?, ?, ?, ?, ?, ?)",
                              (n['date'], n['title'], n['source'], n['link'], n['content'], analisis))
                    conn.commit()
            st.success("Extracción y análisis completados.")
            
        # Mostrar noticias recientes
        c = conn.cursor()
        c.execute("SELECT title, ai_analysis, link, date FROM news ORDER BY id DESC LIMIT 5")
        recientes = c.fetchall()
        
        for i, n in enumerate(recientes):
            with st.expander(f"📌 {n[0]} - ({n[3]})"):
                st.write(f"[Leer fuente original]({n[2]})")
                st.markdown(n[1])
                # Botón de exportación PDF
                pdf_bytes = exportar_pdf(n[0], n[1])
                st.download_button(label="📄 Descargar Informe Estratégico PDF",
                                   data=pdf_bytes,
                                   file_name=f"Reporte_BESS_{i}.pdf",
                                   mime="application/pdf",
                                   key=f"boton_pdf_{i}")
    with col2:
        mostrar_dashboard_mercado()

with tab2:
    st.subheader("Archivo de los últimos 60 días")
    df_hist = pd.read_sql_query("SELECT date, source, title FROM news", conn)
    st.dataframe(df_hist, use_container_width=True)

with tab3:
    st.subheader("Configuración")
    st.markdown("La API de Perplexity puede ser integrada aquí como alternativa a Gemini si se habilita el presupuesto correspondiente.")
