import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from auth import get_access_token
from data import get_processed_dataframe
from utils import CORES_EQUIPES, MESES_EM_PORTUGUES, get_cor_desempenho
import time
import streamlit.components.v1 as components

# Configuração inicial
st.set_page_config(layout='wide')

# Dados
access_token = get_access_token()
df_completo = get_processed_dataframe(access_token)

if df_completo.empty:
    st.warning("Nenhum dado disponível para exibição.")
    st.stop()

# Cores definidas para os status
CORES_STATUS = {
    "Concluída": "#00CC96",
    "No Prazo": "#D3D3D3",
    "Próximo do Vencimento": "#FFD700",
    "Atrasada": "#EF553B"
}

# Filtro Principal
hoje = pd.Timestamp.now().date()
df_filtrado = df_completo[(df_completo['Data Final'].dt.month == hoje.month) & (df_completo['Data Final'].dt.year == hoje.year) | (df_completo['Status'] == 'Atrasada')]

# Carrossel automático
equipes = ['Visão Geral'] + sorted(df_filtrado['Equipe'].unique())
intervalo_segundos = 15

if 'index_equipe' not in st.session_state:
    st.session_state.index_equipe = 0
    st.session_state.ultimo_update = time.time()

if time.time() - st.session_state.ultimo_update > intervalo_segundos:
    st.session_state.index_equipe = (st.session_state.index_equipe + 1) % len(equipes)
    st.session_state.ultimo_update = time.time()
    st.rerun()

equipe_atual = equipes[st.session_state.index_equipe]
equipe_proxima = equipes[(st.session_state.index_equipe + 1) % len(equipes)]
titulo_equipe = equipe_atual

# Cálculo de KPIs
total_exibido = len(df_filtrado[df_filtrado['Equipe'] == equipe_atual]) if equipe_atual != 'Visão Geral' else len(df_filtrado)
atividades_concluidas = len(df_filtrado[(df_filtrado['Status'] == 'Concluída') & ((df_filtrado['Equipe'] == equipe_atual) | (equipe_atual == 'Visão Geral'))])
atividades_no_prazo = len(df_filtrado[(df_filtrado['Status'] == 'No Prazo') & ((df_filtrado['Equipe'] == equipe_atual) | (equipe_atual == 'Visão Geral'))])

if total_exibido > 0:
    taxa_desempenho = ((atividades_concluidas + atividades_no_prazo) / total_exibido) * 100
else:
    taxa_desempenho = 100.0

numero_do_mes = hoje.month
nome_do_mes = MESES_EM_PORTUGUES[numero_do_mes]
ano_atual = hoje.year

# Cabeçalho mais limpo e organizado
col_equipe, col_desempenho, col_info = st.columns([4, 3, 3])

with col_equipe:
    cor_fundo = CORES_EQUIPES.get(equipe_atual, "#262730")
    html_bloco_colorido = f"""
    <div style="background-color:{cor_fundo}; padding:12px; border-radius:8px; text-align:center;">
        <h2 style="color:white; margin:0;">{titulo_equipe}</h2>
    </div>"""
    st.markdown(html_bloco_colorido, unsafe_allow_html=True)

with col_desempenho:
    cor_desempenho = get_cor_desempenho(taxa_desempenho)
    html_gauge = f"""<div style="background-color:{cor_desempenho}; padding:12px; border-radius:8px; text-align:center;">
        <h2 style="color:white; margin:0;">Desempenho: {taxa_desempenho:.0f}%</h2>
    </div>
    """
    st.markdown(html_gauge, unsafe_allow_html=True)

with col_info:
    st.caption(f"📅 **Período:** {nome_do_mes} de {ano_atual}")
    st.caption(f"🔄 **Próxima equipe:** {equipe_proxima} em {int(intervalo_segundos - (time.time() - st.session_state.ultimo_update))} segundos")
    st.caption(f"📌 **Equipe:** {st.session_state.index_equipe} / {len(equipes)}")

st.divider()

# Mantendo distribuição em 3 colunas
if equipe_atual == 'Visão Geral':
    col1, col2, col3 = st.columns(3)

    with col1:
        df_percentual = pd.crosstab(df_filtrado['Equipe'], df_filtrado['Status'], normalize='index') * 100
        status_order = ['Concluída', 'Próximo do Vencimento', 'Atrasada']
        fig1 = go.Figure()
        for status in status_order:
            pattern_shape = "/" if status == "Atrasada" else ""
            fig1.add_trace(go.Bar(y=df_percentual.index, x=df_percentual[status], name=status, orientation='h', marker_color=CORES_STATUS[status], marker_pattern_shape=pattern_shape))
        fig1.update_layout(title='Distribuição Percentual das Atividades por Equipe', barmode='stack', legend=dict(orientation="h", y=-0.5, x=0.5, xanchor='center'))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        df_absoluto = pd.crosstab(df_filtrado['Equipe'], df_filtrado['Status'])
        fig2 = go.Figure()
        for status in status_order:
            pattern_shape = "/" if status == "Atrasada" else ""
            fig2.add_trace(go.Bar(x=df_absoluto.index, y=df_absoluto[status], name=status, marker_color=CORES_STATUS[status], marker_pattern_shape=pattern_shape))
        fig2.update_layout(title='Número Absoluto das Atividades por Equipe', barmode='stack', legend=dict(orientation="h", y=-0.5, x=0.5, xanchor='center'))
        st.plotly_chart(fig2, use_container_width=True)

    with col3:
        st.subheader("Detalhamento por Cliente")
        tabela_cliente = pd.crosstab(df_filtrado['Cliente'], df_filtrado['Status'])
        st.dataframe(tabela_cliente)
else:
    cole1, cole2, cole3 = st.columns(3)

    with cole1:
        df_tipo_pct = pd.crosstab(
        df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Atividade"],
        df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Status"],
        normalize="index"
    ) * 100

        status_esperados = ['Concluída', 'No Prazo', 'Próximo do Vencimento', 'Atrasada']
        
        for status in status_esperados:
            if status not in df_tipo_pct.columns:
                df_tipo_pct[status] = 0
        df_tipo_pct = df_tipo_pct[status_esperados]  # Reordena

        fig1 = go.Figure()
        for status in status_esperados:
            fig1.add_trace(go.Bar(
                y=df_tipo_pct.index,
                x=df_tipo_pct[status],
                name=status,
                orientation='h',
                text=df_tipo_pct[status].apply(lambda x: f'{x:.0f}%' if x > 0 else ''),
                textposition='auto',
                marker_color=CORES_STATUS[status],
                marker_pattern_shape='/' if status == 'Atrasada' else ''
            ))

        fig1.update_layout(
            title='Tipo de Atividade por Status (%)',
            barmode='stack',
            legend=dict(orientation='h', y=-0.2, x=0.5, xanchor='center')
        )
        st.plotly_chart(fig1, use_container_width=True)

        df_colab_atividade = pd.crosstab(
        df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Operador"],
        df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Atividade"]
        )

        fig2 = go.Figure()
        for atividade in df_colab_atividade.columns:
            fig2.add_trace(go.Bar(
                x=df_colab_atividade.index,
                y=df_colab_atividade[atividade],
                name=atividade,
                text=df_colab_atividade[atividade],
                textposition='auto',
                orientation='v'
            ))

        fig2.update_layout(
            title='Colaboradores x Tipo de Atividade',
            barmode='stack',
            legend=dict(orientation='h', y=-0.2, x=0.5, xanchor='center')
        )
        st.plotly_chart(fig2, use_container_width=True)
    with cole2:
        df_operador_pct = pd.crosstab(
            df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Operador"],
            df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Status"],
            normalize="index"
        ) * 100

        for status in status_esperados:
            if status not in df_operador_pct.columns:
                df_operador_pct[status] = 0
        df_operador_pct = df_operador_pct[status_esperados]

        fig3 = go.Figure()
        for status in status_esperados:
            fig3.add_trace(go.Bar(
                y=df_operador_pct.index,
                x=df_operador_pct[status],
                name=status,
                orientation='h',
                text=df_operador_pct[status].apply(lambda x: f'{x:.0f}%' if x > 0 else ''),
                textposition='inside',
                marker_color=CORES_STATUS[status],
                marker_pattern_shape='/' if status == 'Atrasada' else ''
            ))

        fig3.update_layout(
            title='Operadores x Status das Atividades (%)',
            barmode='stack',
            legend=dict(orientation='h', y=-0.5, x=0.5, xanchor='center')
        )
        st.plotly_chart(fig3, use_container_width=True)

        df_operador_abs = pd.crosstab(
            df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Operador"],
            df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Status"]
        )

        for status in status_esperados:
            if status not in df_operador_abs.columns:
                df_operador_abs[status] = 0
        df_operador_abs = df_operador_abs[status_esperados]

        fig4 = go.Figure()
        for status in status_esperados:
            fig4.add_trace(go.Bar(
                x=df_operador_abs.index,
                y=df_operador_abs[status],
                name=status,
                orientation='v',
                text=df_operador_abs[status],
                textposition='auto',
                marker_color=CORES_STATUS[status],
                marker_pattern_shape='/' if status == 'Atrasada' else ''
            ))

        fig4.update_layout(
            title='Operadores x Status das Atividades (Absoluto)',
            barmode='stack',
            legend=dict(orientation='h', y=-0.5, x=0.5, xanchor='center')
        )
        st.plotly_chart(fig4, use_container_width=True)
    with cole3:
        st.subheader("Detalhamento por Cliente")

        tabela_cliente = pd.crosstab(
            df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Cliente"],
            df_filtrado[df_filtrado["Equipe"] == equipe_atual]["Status"]
        )

        for status in status_esperados:
            if status not in tabela_cliente.columns:
                tabela_cliente[status] = 0
        tabela_cliente = tabela_cliente[status_esperados]
        tabela_cliente = tabela_cliente.sort_values(by='Atrasada', ascending=False)

        # Aplica o CSS e exibe a tabela com altura igual às outras colunas
        st.markdown('<div class="dataframe-container">', unsafe_allow_html=True)
        st.dataframe(tabela_cliente.style.format(precision=0))
        st.markdown('</div>', unsafe_allow_html=True)


st.rerun()