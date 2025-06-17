import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import time
import datetime

# --- CONFIGURAÇÕES E SEGURANÇA ---
SITE_ID = "maqfiltros3.sharepoint.com,68b563be-e515-4193-9b5b-4dcf121342e8,347a1963-1db4-4613-8841-056a68baf7ec"
LIST_ID = "418a9527-5b59-432e-8d95-bad94ef6aed1"

ACCESS_TOKEN = st.secrets["SHAREPOINT_TOKEN"]

HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
st.set_page_config(layout='wide')

# --- FUNÇÕES DE DADOS COM CACHE ---

@st.cache_data(ttl=600) # Cache da requisição por 10 minutos
def fetch_sharepoint_data(_site_id, _list_id):
    """Apenas busca os dados brutos da API."""
    url = f"https://graph.microsoft.com/v1.0/sites/{_site_id}/lists/{_list_id}/items?expand=fields&$top=999"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status() # Lança um erro para status 4xx/5xx
        data = response.json()
        return [item["fields"] for item in data["value"]]
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar com a API do SharePoint: {e}")
        return None

@st.cache_data(ttl=600) # Cache do processamento também
def get_processed_dataframe():
    """Busca e processa todos os dados, retornando um DataFrame limpo."""
    items = fetch_sharepoint_data(SITE_ID, LIST_ID)
    if items is None:
        return pd.DataFrame()

    df = pd.DataFrame(items)

    FIELD_MAPPING = {
        "field_2": "Atividade", "field_3": "Cliente", "field_5": "Data de Emissão",
        "field_6": "Data de Início", "field_7": "Data de Término", "field_8": "Data Final",
        "field_9": "Data Início", "field_10": "Descrição da Atividade", "field_12": "Emissor",
        "field_16": "Nº Nota Fiscal", "field_17": "Qtd. Bombonas", "field_19": "Operador",
        "Equipe": "Equipe"
    }
    df = df.rename(columns=FIELD_MAPPING)

    for col in ["Data de Emissão", "Data de Início", "Data Final", "Data de Término"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.tz_localize(None)

    colaborador_para_equipe = {
        "Daniela": "Comercial", "Gilmar Couto": "Operação - Litoral Norte",
        "Edvalda Cerqueira": "Administrativo / Financeiro", "Icaro Conceição": "Operação - Salvador",
        "Moises de Jesus": "Operação - Salvador", "Vinicius Silva": "Operação - Salvador",
        "Jerri Oliveira": "Operação - Litoral Norte", "Adriano": "Operação - Industrial",
        "Paulo Cesar": "Administrativo / Financeiro", "Fábio Barreto": "Operação - Salvador",
        "Henrique Califano": "Técnico", "Anderson Dias": "Operação - Litoral Norte",
        "Moisés de Jesus": "Operação - Salvador", "Matheus Gusmão": "Operação - Salvador",
        "Diogo Bacelar": "Técnico", "Judson Cruz": "Operação - Salvador"
    }
    df["Equipe"] = df["Operador"].map(colaborador_para_equipe)
    df = df[df["Equipe"].notna()]
    
    hoje = pd.Timestamp.now().date()
    def definir_status_correto(row):
        if pd.notna(row['Data de Término']): return 'Concluída'
        if pd.notna(row['Data Final']):
            if row['Data Final'].date() < hoje: return 'Atrasada'
            else: return 'No Prazo'
        else: return 'Sem Vencimento'
    
    df['Status'] = df.apply(definir_status_correto, axis=1)
    
    return df

# --- LÓGICA PRINCIPAL DO APP ---
df_completo = get_processed_dataframe()

if df_completo.empty:
    st.warning("Não foi possível carregar os dados. Verifique a conexão ou o token de acesso.")
    st.stop()

# Lógica do Carrossel de Equipes
equipes = sorted(df_completo["Equipe"].dropna().unique().tolist())
intervalo_segundos = 15

if "equipe_index" not in st.session_state: st.session_state.equipe_index = 0
if "ultimo_update" not in st.session_state: st.session_state.ultimo_update = time.time()

if time.time() - st.session_state.ultimo_update > intervalo_segundos:
    st.session_state.equipe_index = (st.session_state.equipe_index + 1) % len(equipes)
    st.session_state.ultimo_update = time.time()
    st.rerun()

# --- EXIBIÇÃO DO DASHBOARD ---
equipe_atual = equipes[st.session_state.equipe_index]
df_equipe = df_completo[df_completo["Equipe"] == equipe_atual].copy()
equipe_proxima = equipes[(st.session_state.equipe_index + 1) % len(equipes)]

# Cálculos dos KPIs
total_abertas = df_equipe[df_equipe['Status'] != 'Concluída'].shape[0]
atividades_atrasadas = df_equipe[df_equipe['Status'] == 'Atrasada'].shape[0]
taxa_atraso = (atividades_atrasadas / total_abertas) * 100 if total_abertas > 0 else 0
atividades_no_prazo = df_equipe[df_equipe['Status'] == 'No Prazo'].shape[0]

# --- CABEÇALHO COMPACTO: Título e KPIs na mesma linha ---
col_header, colequipe, col_kpi1, col_kpi2, col_kpi3 = st.columns([4, 4, 1, 1, 1])
with col_header:
    st.header("Gestão à Vista: Atividades")
    
with colequipe:
    st.subheader(f"Equipe: {equipe_atual}")

with col_kpi1:
    st.metric("Abertas", f"{total_abertas}")
with col_kpi2:
    st.metric("No Prazo", f"{atividades_no_prazo}")
with col_kpi3:
    st.metric("Taxa de Atraso", f"{taxa_atraso:.2f}%", delta=f"{atividades_atrasadas} Atrasadas", delta_color="inverse")

# Contador do carrossel
tempo_restante = int(intervalo_segundos - (time.time() - st.session_state.ultimo_update))
st.caption(f"⏳ Próxima equipe: **{equipe_proxima}** em **{tempo_restante}s**...")
st.divider()


# Exibição dos Gráficos
col_graf1, col_graf2, col_graf3 = st.columns(3)

with col_graf1:
    st.subheader("Atividades por Tipo")
    df_status = df_equipe.groupby(['Atividade', 'Status']).size().reset_index(name='Quantidade')
    fig1 = px.bar(df_status, x='Quantidade', y='Atividade', color='Status', orientation='h',
                  category_orders={"Atividade": df_status.groupby('Atividade')['Quantidade'].sum().sort_values(ascending=True).index},
                  color_discrete_map={'Atrasada': '#EF553B', 'Concluída': '#00CC96', 'No Prazo': '#636EFA', 'Sem Vencimento': '#ABAAAA'}, height=450)
    fig1.update_layout(yaxis_title=None, xaxis_title="Quantidade", showlegend=False, legend_title_text='')
    st.plotly_chart(fig1, use_container_width=True)

with col_graf2:
    st.subheader("Operadores com Atrasos")
    df_op_atraso = df_equipe[df_equipe['Status'] == 'Atrasada']['Operador'].value_counts().reset_index().sort_values('count', ascending=False)
    if not df_op_atraso.empty:
        fig2 = px.bar(df_op_atraso, x='Operador', y='count', color_discrete_sequence=['#EF553B'], height=450)
        fig2.update_layout(xaxis_title=None, yaxis_title="Nº de Atividades Atrasadas")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.success("🎉 Nenhum operador com atividades em atraso!")

with col_graf3:
    st.subheader("Clientes com Atividades Abertas")
    df_abertas = df_equipe[df_equipe['Status'] != 'Concluída'].copy()
    df_clientes = df_abertas.dropna(subset=['Cliente'])
    if not df_clientes.empty:
        contagem_clientes = df_clientes['Cliente'].value_counts().reset_index()
        contagem_clientes.columns = ['Cliente', 'Quantidade']
        limite = 3
        contagem_agrupada = contagem_clientes.copy()
        contagem_agrupada['Cliente'] = contagem_agrupada.apply(lambda row: row['Cliente'] if row['Quantidade'] >= limite else 'Outros', axis=1)
        df_final = contagem_agrupada.groupby('Cliente')['Quantidade'].sum().reset_index()
        fig3 = px.pie(df_final, names='Cliente', values='Quantidade', hole=0.4)
        fig3.update_layout(showlegend=False)
        fig3.update_traces(textposition='inside', textinfo='percent+label', insidetextorientation='radial')
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Nenhuma atividade em aberto para esta equipe.")

st.rerun()
