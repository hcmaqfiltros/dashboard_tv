import requests
import streamlit as st

@st.cache_data(ttl=3500)
def get_access_token():
    tenant_id = st.secrets["TENANT_ID"]
    client_id = st.secrets["CLIENT_ID"]
    client_secret = st.secrets["CLIENT_SECRET"]

    url_token = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    body = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    token_request = requests.post(url_token, data=body)

    if token_request.status_code != 200:
        st.error(f"Falha ao obter token: {token_request.json().get('error_description')}")
        return None
        
    token_data = token_request.json()
    return token_data.get("access_token")
