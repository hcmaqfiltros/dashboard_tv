import streamlit as st
import plotly.graph_objects as go

def card_metric(titulo, valor, cor):
    st.markdown(f"""
    <div style="background-color:{cor};padding:15px;border-radius:8px;text-align:center;color:white;">
        <h4>{titulo}</h4>
        <h2>{valor}</h2>
    </div>
    """, unsafe_allow_html=True)

def barra_progresso(intervalo_segundos, tempo_restante):
    tempo_restante_pct = tempo_restante / intervalo_segundos
    st.progress(tempo_restante_pct)

def desempenho_colaborador(df_para_exibir, status_esperados):
    df_colab = df_para_exibir.groupby(["Operador", "Status"]).size().unstack(fill_value=0)
    df_colab["Total"] = df_colab.sum(axis=1)
    for col in status_esperados:
        if col not in df_colab.columns:
            df_colab[col] = 0
        df_colab[col] = (df_colab[col] / df_colab["Total"]) * 100

    fig_colab = go.Figure()
    cores_status = {
        'Concluída': '#00CC96', 'No Prazo': '#D3D3D3',
        'Próximo do Vencimento': '#FFD700', 'Atrasada': '#EF553B'
    }

    for status in status_esperados:
        fig_colab.add_trace(go.Bar(
            y=df_colab.index, x=df_colab[status], orientation='h',
            name=status, marker_color=cores_status[status],
            text=df_colab[status].apply(lambda x: f'{x:.0f}%'),
            textposition='inside'
        ))

    fig_colab.update_layout(barmode='stack', height=500)
    st.plotly_chart(fig_colab, use_container_width=True)
