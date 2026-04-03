import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from supabase import create_client, Client

# --- CONEXÃO SUPABASE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")
st.markdown("<style>header {visibility: hidden;} .stApp {background: #0f172a; color: white;}</style>", unsafe_allow_html=True)

# --- MOTOR LÓGICO (O "TANQUE DE GUERRA" PARA VENDAS BAGUNÇADAS) ---
def palpite_categoria(nome_bruto):
    # Limpeza profunda para o PDF de venda bagunçado
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome_bruto) if unicodedata.category(c) != 'Mn').upper().strip()
    
    # 1. BUSCA POR EXCEÇÃO MANUAL (Prioridade)
    try:
        regras = supabase.table("excecoes_categorias").select("*").execute()
        for r in regras.data:
            if r['nome_produto'] in txt:
                return r['categoria_destino'], False
    except: pass

    # 2. REGRAS AUTOMÁTICAS (Dicionário padrão)
    if any(k in txt for k in ["CIGARRO", "PINE", "ROTHMANS"]): return "Tabacaria", False
    if any(k in txt for k in ["CERV", "HEINEKEN", "PITU", "SKOL", "BRAHMA", "ANTARCTICA"]): return "Bebidas Alcoólicas", False
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "CHOCOLATE", "BALA"]): return "Bomboniere", False
    if any(k in txt for k in ["SORV", "PICOLE", "ACAI"]): return "Sorvetes", False
    
    return "Mercearia", True

# --- FUNÇÃO DE LIMPEZA PARA O PDF DE ESTOQUE (LIMPO) ---
def limpar_linha_estoque(linha):
    # Remove EANs de 13-14 dígitos e códigos internos de até 6 dígitos
    n = re.sub(r'\b\d{13,14}\b', '', linha)
    n = re.sub(r'^\s*\d{1,7}\s+', '', n)
    return n.strip().upper()

# --- PROCESSAMENTO DE VENDAS (O BAGUNÇADO) ---
def processar_vendas(file):
    dados = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            linhas = (page.extract_text() or "").split('\n')
            for l in linhas:
                valores = re.findall(r'\d+,\d{2}', l)
                if len(valores) >= 4:
                    # Tenta capturar o nome ignorando o código de barras
                    ean_m = re.search(r'\b\d{7,14}\b', l)
                    n_limpo = l.replace(ean_m.group(), "") if ean_m else l
                    n_limpo = re.sub(r'\b\d{5,8}\b', '', n_limpo).strip()[:30].upper()
                    
                    val = float(valores[-4].replace(',', '.'))
                    cat, is_fallback = palpite_categoria(n_limpo)
                    dados.append({"Produto": n_limpo, "Categoria": cat, "Valor": val})
    return dados

# --- LOGIN E NAVEGAÇÃO ---
res_user = supabase.table("usuarios").select("*").execute()
config = {"usernames": {u['username']: {"name": u['name'], "password": u['password']} for u in res_user.data}}
auth = stauth.Authenticate(config, "canada_session", "signature_key", expiry_days=30)

if not st.session_state.get("authentication_status"):
    auth.login(location='main')
else:
    st.sidebar.title(f"Bem-vindo, {st.session_state['name']}")
    aba = st.sidebar.radio("Navegação", ["📊 Análise de Vendas", "⚙️ Configurações e Exceções"])
    auth.logout("Sair", "sidebar")

    if aba == "📊 Análise de Vendas":
        st.header("Análise de Vendas (PDF Bagunçado)")
        file = st.file_uploader("Subir PDF de Vendas", type="pdf")
        if file:
            res = processar_vendas(file)
            st.dataframe(pd.DataFrame(res), use_container_width=True)

    elif aba == "⚙️ Configurações e Exceções":
        st.header("⚙️ Central de Inteligência")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🧬 Sincronizar Estoque")
            st.write("Use os PDFs de 'Estoque Geral' para ensinar novos nomes ao sistema.")
            pdf_est = st.file_uploader("PDF de Estoque (Limpo)", type="pdf", key="est")
            if pdf_est:
                with st.spinner("Sincronizando nomes..."):
                    with pdfplumber.open(pdf_est) as pdf:
                        for p in pdf.pages:
                            for l in (p.extract_text() or "").split('\n'):
                                nome_e = limpar_linha_estoque(l)
                                if len(nome_e) > 5:
                                    supabase.table("historico_produtos").upsert({"nome_produto": nome_e}).execute()
                    st.success("Estoque sincronizado com sucesso!")

        with col2:
            st.subheader("🛠️ Criar Regra de Categoria")
            res_h = supabase.table("historico_produtos").select("nome_produto").order("nome_produto").execute()
            lista_sugestoes = [i['nome_produto'] for i in res_h.data]
            
            with st.form("excecao_form"):
                prod_sel = st.selectbox("Escolha o Produto (Autocomplete):", options=lista_sugestoes)
                cat_dest = st.selectbox("Mover para:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Mercearia"])
                if st.form_submit_button("Salvar Regra"):
                    supabase.table("excecoes_categorias").upsert({"nome_produto": prod_sel, "categoria_destino": cat_dest}).execute()
                    st.success(f"Regra salva: {prod_sel} agora é {cat_dest}")
                    st.rerun()
