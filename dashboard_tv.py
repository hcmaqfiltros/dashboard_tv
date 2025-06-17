import streamlit as st
import time

equipes = ["Equipe A", "Equipe B", "Equipe C"]
intervalo_segundos = 30  # tempo de exibição por equipe

# Index atual da equipe salvo na sessão
if "equipe_index" not in st.session_state:
    st.session_state.equipe_index = 0

# Equipe atual
equipe_atual = equipes[st.session_state.equipe_index]

# Exibição
st.title(f"📺 Gestão à Vista - {equipe_atual}")
st.markdown(f"Atualizando a cada {intervalo_segundos} segundos...")

# Mostra dados da equipe atual aqui
# st.dataframe(df[df["Equipe"] == equipe_atual])

# Espera e roda novamente trocando equipe
time.sleep(intervalo_segundos)
st.session_state.equipe_index = (st.session_state.equipe_index + 1) % len(equipes)
st.experimental_rerun()
