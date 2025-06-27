import requests
import pandas as pd
import streamlit as st

@st.cache_data(ttl=600)
def fetch_sharepoint_data(_site_id, _list_id, _access_token):
    headers = {"Authorization": f"Bearer {_access_token}"}
    url = f"https://graph.microsoft.com/v1.0/sites/{_site_id}/lists/{_list_id}/items?expand=fields&$top=999"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [item["fields"] for item in response.json()["value"]]

@st.cache_data(ttl=600)
def get_processed_dataframe(access_token):
    site_id = st.secrets["SITE_ID"]
    list_id = st.secrets["LIST_ID"]
    items = fetch_sharepoint_data(site_id, list_id, access_token)
    df = pd.DataFrame(items)

    FIELD_MAPPING = {
        "field_2": "Atividade",
        "field_3": "Cliente",
        "field_6": "Data de Início",
        "field_7": "Data de Término",
        "field_8": "Data Final",
        "field_19": "Operador"
    }
    df = df.rename(columns=FIELD_MAPPING)

    for col in ["Data de Início", "Data Final", "Data de Término"]:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.tz_localize(None)

    colaborador_para_equipe = { "Daniela": "Comercial", "Gilmar Couto": "Operação - Litoral Norte", "Edvalda Cerqueira": "Administrativo / Financeiro", "Icaro Conceição": "Operação - Salvador", "Moises de Jesus": "Operação - Salvador", "Vinicius Silva": "Operação - Salvador", "Jerri Oliveira": "Operação - Litoral Norte", "Adriano": "Operação - Industrial", "Paulo Cesar": "Administrativo / Financeiro", "Fábio Barreto": "Operação - Salvador", "Henrique Califano": "Técnico", "Anderson Dias": "Operação - Litoral Norte", "Moisés de Jesus": "Operação - Salvador", "Matheus Gusmão": "Operação - Salvador", "Diogo Bacelar": "Técnico", "Judson Cruz": "Operação - Salvador" }
    df["Equipe"] = df["Operador"].map(colaborador_para_equipe)
    df.dropna(subset=["Equipe"], inplace=True)

    hoje = pd.Timestamp.now().date()

    def definir_status_correto(row):
        if pd.notna(row['Data de Término']):
            return 'Concluída'
        if pd.notna(row['Data Final']):
            vencimento = row['Data Final'].date()
            if vencimento < hoje:
                return 'Atrasada'
            elif (vencimento - hoje).days <= 3:
                return 'Próximo do Vencimento'
            return 'No Prazo'
        return 'Sem Vencimento'

    df['Status'] = df.apply(definir_status_correto, axis=1)
    return df
