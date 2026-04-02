import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from datetime import datetime
from supabase import create_client, Client

# --- CONEXÃO SUPABASE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

# --- FUNÇÕES DE CATEGORIA ---
def palpite_categoria(nome):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome) if unicodedata.category(c) != 'Mn').upper().strip()
    
    # 1. BUSCA POR EXCEÇÃO (Contém a palavra chave)
    try:
        regras = supabase.table("excecoes_categorias").select("*").execute()
        for r in regras.data:
            if r['nome_produto'] in txt:
                return r['categoria_destino'], False
    except: pass

    # 2. REGRAS AUTOMÁTICAS
    if any(k in txt for k in ["CIGARRO", "PINE", "ROTHMANS"]): return "Tabacaria", False
    if any(k in txt for k in ["CERV", "HEINEKEN", "PITU", "SKOL"]): return "Bebidas Alcoólicas", False
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "CHOCOLATE"]): return "Bomboniere", False
    return "Mercearia", True

# --- PROCESSAMENTO ---
def processar_pdf(file):
    dados = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            linhas = (page.extract_text() or "").split('\n')
            for linha in linhas:
                valores = re.findall(r'\d+,\d{2}', linha)
                if len(valores) >= 4:
                    ean_m = re.search(r'\b\d{7,14}\b', linha)
                    if not ean_m: continue
                    n_bruto = linha.replace(ean_m.group(), "").strip()
                    nome_limpo = re.sub(r'\b\d{5,8}\b', '', n_bruto).replace('.','').strip()[:30].upper()
                    val = float(valores[-4].replace(',', '.'))
                    cat, fallback = palpite_categoria(nome_limpo)
                    dados.append({"Nome": nome_limpo, "Cat": cat, "Valor": val})
                    
                    # SALVA NO HISTÓRICO PARA O AUTOCOMPLETE
                    try:
                        supabase.table("historico_produtos").upsert({"nome_produto": nome_limpo}).execute()
                    except: pass
    return dados

# --- LOGIN ---
res_user = supabase.table("usuarios").select("*").execute()
config = {"usernames": {u['username']: {"name": u['name'], "password": u['password']} for u in res_user.data}}
auth = stauth.Authenticate(config, "cookie_name", "signature_key", expiry_days=30)

if not st.session_state.get("authentication_status"):
    auth.login(location='main')
else:
    st.sidebar.write(f"Usuário: {st.session_state['name']}")
    menu = st.sidebar.radio("Menu", ["Análise", "Exceções (Ajustar Categorias)"])
    auth.logout("Sair", "sidebar")

    if menu == "Análise":
        uroller = st.file_uploader("Subir PDF", type="pdf")
        if uroller:
            res = processar_pdf(uroller)
            st.table(pd.DataFrame(res))

    elif menu == "Exceções (Ajustar Categorias)":
        st.header("🛠️ Central de Exceções Inteligente")
        
        # BUSCA NOMES DO HISTÓRICO PARA SUGERIR
        res_h = supabase.table("historico_produtos").select("nome_produto").order("nome_produto").execute()
        sugestoes = [item['nome_produto'] for item in res_h.data]
        
        with st.form("form_inteligente"):
            st.info("Selecione um produto que já apareceu em PDFs anteriores:")
            nome_sel = st.selectbox("Produto Encontrado:", options=sugestoes)
            nova_cat = st.selectbox("Nova Categoria:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Mercearia"])
            
            if st.form_submit_button("Confirmar Mudança"):
                supabase.table("excecoes_categorias").upsert({"nome_produto": nome_sel, "categoria_destino": nova_cat}).execute()
                st.success(f"Feito! {nome_sel} agora é {nova_cat}")
                st.rerun()
