import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
import os
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime, timedelta

# Configurazione
load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

st.set_page_config(page_title="Radar Party 2024", layout="wide")

# --- LOGICA DI ACCESSO ---
st.title("🏆 Pagelle di Capodanno")
amici = ["Marco", "Giulia", "Alberto", "Elena", "Pietro"]
categorie = ["Romantico", "Pazzo", "Puzzolente", "Simpatico", "Elegante"]

votante = st.sidebar.text_input("Inserisci il tuo Nome per accedere", placeholder="Es. Alberto")

if not votante:
    st.warning("👈 Inserisci il tuo nome nella barra laterale per iniziare!")
    st.stop()

# --- CONTROLLO VOTI EFFETTUATI ---
# Filtriamo i voti delle ultime 24 ore
limite_tempo = (datetime.now() - timedelta(hours=24)).isoformat()
res_voti_utente = supabase.table("voti").select("*").eq("votante", votante).gt("created_at", limite_tempo).execute()
df_utente = pd.DataFrame(res_voti_utente.data)

totale_voti_necessari = len(amici) * len(categorie)
ha_votato_tutto = len(df_utente) >= totale_voti_necessari

# --- SEZIONE 1: INVIO VOTI ---
with st.expander("📝 Inserisci/Modifica i tuoi Voti", expanded=not ha_votato_tutto):
    amico_scelto = st.selectbox("Chi vuoi votare?", amici)
    nuovi_voti = {}
    for cat in categorie:
        nuovi_voti[cat] = st.slider(f"{cat}", 1, 10, 5, key=f"s_{amico_scelto}_{cat}")

    if st.button("Salva Voti 🚀"):
        for cat, punteggio in nuovi_voti.items():
            data = {"votante": votante, "amico_votato": amico_scelto, "categoria": cat, "punteggio": punteggio}
            supabase.table("voti").upsert(data, on_conflict="votante,amico_votato,categoria").execute()
        st.success("Voti salvati! Aggiorna la pagina per vedere i progressi.")
        st.rerun()

# --- SEZIONE 2: RISULTATI (Blind Reveal) ---
st.divider()
if not ha_votato_tutto:
    st.error(f"🔒 Risultati bloccati! Hai completato {len(df_utente)} su {totale_voti_necessari} voti.")
    st.info("Devi votare TUTTI gli amici in TUTTE le categorie per vedere i grafici.")
else:
    st.balloons()
    st.success("✅ Sei un grande! Ecco i risultati globali (Ultime 24h):")

    amico_stats = st.selectbox("Visualizza il profilo di:", amici)

    # Recupero medie globali delle ultime 24h
    res_global = supabase.table("voti").select("*").eq("amico_votato", amico_stats).gt("created_at",
                                                                                       limite_tempo).execute()
    df_global = pd.DataFrame(res_global.data)

    if not df_global.empty:
        medie = df_global.groupby("categoria")["punteggio"].mean().reindex(categorie).fillna(0)

        # Grafico Radar
        fig = go.Figure(go.Scatterpolar(r=medie.values, theta=medie.index, fill='toself', line_color='orange'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), showlegend=False)
        st.plotly_chart(fig)

        # AI INSIGHT (Gemini)
        if st.button(f"Chiedi all'AI un commento su {amico_stats}"):
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"Scrivi una breve descrizione ironica e divertente (max 2 righe) per un amico che ha queste statistiche medie: {medie.to_dict()}. Sii molto scherzoso per una festa di Capodanno."
            response = model.generate_content(prompt)
            st.info(f"🤖 **L'AI dice:** {response.text}")