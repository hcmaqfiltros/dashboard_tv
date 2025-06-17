import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from streamlit_plotly_events import plotly_events
import plotly.graph_objects as go
import time
import datetime
from streamlit_autorefresh import st_autorefresh

# === CONFIGURAÇÕES ===
SITE_ID = "maqfiltros3.sharepoint.com,68b563be-e515-4193-9b5b-4dcf121342e8,347a1963-1db4-4613-8841-056a68baf7ec"
LIST_ID = "418a9527-5b59-432e-8d95-bad94ef6aed1"
ACCESS_TOKEN = st.secrets["SHAREPOINT_TOKEN"]

HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
st.set_page_config(layout='wide')

# === CACHE DA REQUISIÇÃO (evita múltiplos acessos à API)
@st.cache_data(ttl=600)
def get_sharepoint_items(site_id, list_id):
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields&$top=999"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    items = [item["fields"] for item in data["value"]]
    return pd.DataFrame(items)


# === CARREGAMENTO E RENOMEAÇÃO
FIELD_MAPPING = {
    "field_2": "Atividade",
    "field_3": "Cliente",
    "field_5": "Data de Emissão",
    "field_6": "Data de Início",
    "field_7": "Data de Término",
    "field_8": "Data Final",
    "field_9": "Data Início",
    "field_10": "Descrição da Atividade",
    "field_12": "Emissor",
    "field_16": "Nº Nota Fiscal",
    "field_17": "Qtd. Bombonas",
    "field_19": "Operador",
    "Equipe": "Equipe"
}

df = get_sharepoint_items(SITE_ID, LIST_ID).rename(columns=FIELD_MAPPING)

for col in ["Data de Emissão", "Data de Início", "Data Final", "Data Início", "Data de Término"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.tz_localize(None)


colaborador_para_equipe = {
    "Daniela": "Comercial",
    "Gilmar Couto": "Operação - Litoral Norte",
    "Edvalda Cerqueira": "Administrativo / Financeiro",
    "Icaro Conceição": "Operação - Salvador",
    "Moises de Jesus": "Operação - Salvador",
    "Vinicius Silva": "Operação - Salvador",
    "Jerri Oliveira": "Operação - Litoral Norte",
    "Adriano": "Operação - Industrial",
    "Paulo Cesar": "Administrativo / Financeiro",
    "Fábio Barreto": "Operação - Salvador",
    "Henrique Califano": "Técnico",
    "Anderson Dias": "Operação - Litoral Norte",
    "Moisés de Jesus": "Operação - Salvador",
    "Matheus Gusmão": "Operação - Salvador",
    "Diogo Bacelar": "Técnico",
    "Judson Cruz": "Operação - Salvador"
}
df["Equipe"] = df["Operador"].map(colaborador_para_equipe)

df = df[df["Equipe"].notna()]


# Lista de equipes
equipes = sorted(df["Equipe"].dropna().unique().tolist())
intervalo_segundos = 60  # tempo entre troca de equipes

# Inicializa estados da sessão
if "equipe_index" not in st.session_state:
    st.session_state.equipe_index = 0
if "ultimo_update" not in st.session_state:
    st.session_state.ultimo_update = datetime.datetime.now()

# Verifica tempo desde a última atualização
agora = datetime.datetime.now()
tempo_passado = (agora - st.session_state.ultimo_update).total_seconds()

# Se passou do tempo, troca a equipe
if tempo_passado >= intervalo_segundos:
    st.session_state.equipe_index = (st.session_state.equipe_index + 1) % len(equipes)
    st.session_state.ultimo_update = agora
    st.rerun()

st.title("Gestão a Vista: Acompanhamento das Atividades")


hoje = pd.Timestamp.now().date()

# --- LÓGICA DE STATUS COM A COMPARAÇÃO CORRIGIDA ---
def definir_status_correto(row):
    # Regra 1: Se tem data de término, está Concluída.
    if pd.notna(row['Data de Término']):
        return 'Concluída'
    
    # Se não foi concluída, avaliamos pela data de vencimento ('Data Final')
    if pd.notna(row['Data Final']):
        # 2. Garantimos que ambos os lados da comparação são do tipo 'date'.
        if row['Data Final'].date() < hoje:
            return 'Atrasada'
        else:
            return 'No Prazo'
    else:
        return 'Sem Vencimento'

df['Status'] = df.apply(definir_status_correto, axis=1)

# Equipe atual e próxima
equipe_atual = equipes[st.session_state.equipe_index]
equipe_proxima = equipes[(st.session_state.equipe_index + 1) % len(equipes)]
df_equipe = df[df["Equipe"] == equipe_atual].copy()

st.markdown(f"## Equipe Atual: **{equipe_atual}**")
st.markdown(f"⏳ Mudando para a próxima equipe (**{equipe_proxima}**) em **{int(intervalo_segundos - tempo_passado)}s**...")



# Cálculos
total_atividades = df_equipe.shape[0]
atividades_atrasadas = df_equipe[df_equipe['Status'] == 'Atrasada'].shape[0]
taxa_atraso = (atividades_atrasadas / (total_atividades - df_equipe[df_equipe['Status'] == 'Concluída'].shape[0])) * 100 if (total_atividades - df_equipe[df_equipe['Status'] == 'Concluída'].shape[0]) > 0 else 0
atividades_no_prazo = df_equipe[df_equipe['Status'] == 'No Prazo'].shape[0]

st.subheader("Indicadores Chave de Performance")
col1, col2, col3 = st.columns(3)
col1.metric("Atividades Abertas (Total)", f"{atividades_atrasadas + atividades_no_prazo}")
col2.metric("Atividades No Prazo", f"{atividades_no_prazo}")
col3.metric("Taxa de Atividades em Atraso", f"{taxa_atraso:.2f}%", delta=f"{atividades_atrasadas} Atrasadas", delta_color="inverse")

st.divider()

col_graf1, col_graf2, col_graf3 = st.columns(3)

# --- 1. Gráfico 1: Atividades por Tipo e Status ---
with col_graf1:
    df_status = df_equipe.groupby(['Atividade', 'Status']).size().reset_index(name='Quantidade')
    fig1 = px.bar(df_status, x='Quantidade', y='Atividade', color='Status', orientation='h', title='Distribuição de Atividades por Status',
                    category_orders={"Atividade": df_status.groupby('Atividade')['Quantidade'].sum().sort_values(ascending=True).index},
                    color_discrete_map={
                        'Atrasada': '#EF553B', 'Concluída': '#00CC96',
                        'No Prazo': '#636EFA', 'Sem Vencimento': '#ABAAAA'
                    }, height=450)
    fig1.update_layout(yaxis_title=None, xaxis_title="Quantidade")
    st.plotly_chart(fig1, use_container_width=True)

# --- 2. Gráfico 2: Operadores × Atividades Atrasadas ---
with col_graf2:
    df_op_atraso = df_equipe[df_equipe['Status'] == 'Atrasada']['Operador'].value_counts().reset_index().sort_values('count', ascending=False)
    
    if not df_op_atraso.empty:
        fig2 = px.bar(df_op_atraso, x='Operador', y='count', title='Ranking de Atividades Atrasadas por Operador', color_discrete_sequence=['#EF553B'], height=450)
        fig2.update_layout(xaxis_title=None, yaxis_title="Nº de Atividades Atrasadas")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.success("🎉 Nenhum operador com atividades em atraso!")

with col_graf3:
    
    df_abertas = df_equipe[df_equipe['Status'] != 'Concluída'].copy()
    df_clientes = df_abertas.dropna(subset=['Cliente'])

    # Contamos quantas atividades cada cliente possui
    contagem_clientes = df_clientes['Cliente'].value_counts().reset_index()
    contagem_clientes.columns = ['Cliente', 'Quantidade']
    
    limite = 3
    
    contagem_agrupada = contagem_clientes.copy()
    contagem_agrupada['Cliente'] = contagem_agrupada.apply(
        lambda row: row['Cliente'] if row['Quantidade'] >= limite else 'Outros',
        axis=1
    )
    df_final = contagem_agrupada.groupby('Cliente')['Quantidade'].sum().reset_index()

    

    fig = px.pie(df_final,
                 names='Cliente',          # A coluna com os nomes das fatias
                 values='Quantidade',      # A coluna com os valores (tamanhos)
                 title='Clientes com Atividades em Aberto')                 # Efeito de gráfico de rosca (donut chart)

    # Melhorando a visualização dos rótulos
    fig.update_layout(showlegend=False)
    fig.update_traces(textposition='inside', textinfo='percent+label',
                      insidetextorientation='radial')


    # --- 4. Exibição no Streamlit ---
    st.plotly_chart(fig, use_container_width=True)
    
# Redesenha automaticamente a cada segundo
st.rerun()
