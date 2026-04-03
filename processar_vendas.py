import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from supabase import create_client, Client

# --- 1. CONEXÃO SUPABASE ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. CONFIGURAÇÃO VISUAL (ESTILO GLASS DARK) ---
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    /* Fundo Gradiente Deep Dark */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%);
        color: #e2e8f0;
    }

    /* Efeito Glassmorphism nos Cards/Forms */
    div[data-testid="stForm"], .stExpander, div.stChatMessage {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px !important;
        padding: 20px;
    }

    /* Botões Customizados com Hover */
    .stButton>button {
        background: linear-gradient(90deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        transition: all 0.3s ease;
        font-weight: 600;
        width: 100%;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        border: none;
        color: white;
    }

    /* Inputs e Selectbox */
    .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 8px;
    }

    /* Esconder Header Original */
    header {visibility: hidden;}
    
    /* Tabelas com Hover */
    .styled-table {
        width: 100%;
        border-collapse: collapse;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. MOTORES LÓGICOS ---

def limpar_linha_estoque(linha):
    ignorar = ["MERCADINHO", "ENDEREÇO", "PAGINA", "ESTOQUE", "GESTÃO", "SMB STORE", "CNPJ", "TELEFONE", "CÓDIGO"]
    if any(p in linha.upper() for p in ignorar): return ""
    n = re.sub(r'\b\d{13,14}\b', '', linha)
    n = re.sub(r'^\s*\d{1,7}\s+', '', n)
    n = re.sub(r'[.\-/"\']', '', n)
    return n.strip().upper()

def palpite_categoria(nome_bruto):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome_bruto) if unicodedata.category(c) != 'Mn').upper().strip()
    try:
        regras = supabase.table("excecoes_categorias").select("*").execute()
        for r in regras.data:
            if r['nome_produto'] in txt:
                return r['categoria_destino'], False
    except: pass
    
    # Regras Inteligentes
    dicionario = {
        "Tabacaria": ["CIGARRO", "PINE", "ROTHMANS", "GIFT", "DUNHILL", "LUCKY"],
        "Bebidas Alcoólicas": ["CERV", "HEINEKEN", "PITU", "SKOL", "BRAHMA", "ANTARCTICA", "VINHO", "WHISKY"],
        "Bomboniere": ["TRIDENT", "DOCE", "BOMBOM", "FINI", "CHOCOLATE", "BALA", "HALLS", "BIS"],
        "Sorvetes": ["SORV", "PICOLE", "ACAI"]
    }
    for cat, keywords in dicionario.items():
        if any(k in txt for k in keywords): return cat, False
    return "Mercearia", True

def processar_vendas_baguncado(file):
    dados = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            linhas = (page.extract_text() or "").split('\n')
            for l in linhas:
                valores = re.findall(r'\d+,\d{2}', l)
                if len(valores) >= 4:
                    ean_m = re.search(r'\b\d{7,14}\b', l)
                    n_limpo = l.replace(ean_m.group(), "") if ean_m else l
                    n_limpo = re.sub(r'\b\d{4,8}\b', '', n_limpo).strip()[:35].upper()
                    val_unit = float(valores[-4].replace(',', '.'))
                    cat, _ = palpite_categoria(n_limpo)
                    dados.append({"Produto": n_limpo, "Categoria": cat, "Valor": val_unit})
    return dados

# --- 4. AUTENTICAÇÃO ---
try:
    res_user = supabase.table("usuarios").select("*").execute()
    db_users = {u['username']: {"name": u['name'], "password": u['password']} for u in res_user.data}
except:
    db_users = {"admin": {"name": "Admin", "password": "123"}}

auth = stauth.Authenticate(db_users, "canada_bi_cookie", "signature_key", expiry_days=30)

if not st.session_state.get("authentication_status"):
    st.markdown("<h1 style='text-align: center;'>🇨🇦 Canadá BI</h1>", unsafe_allow_html=True)
    auth.login(location='main')
else:
    st.sidebar.markdown(f"### Bem-vindo, <br><span style='color:#3b82f6'>{st.session_state['name']}</span>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegação", ["📊 Análise de Vendas", "⚙️ Inteligência de Dados"])
    auth.logout("Sair", "sidebar")

    if menu == "📊 Análise de Vendas":
        st.header("📊 Dashboard de Vendas")
        file = st.file_uploader("Arraste o PDF de vendas diárias aqui", type="pdf")
        if file:
            with st.spinner("Processando dados..."):
                df = pd.DataFrame(processar_vendas_baguncado(file))
                st.dataframe(df, use_container_width=True)

    elif menu == "⚙️ Inteligência de Dados":
        st.header("⚙️ Central de Configurações")
        
        tab1, tab2 = st.tabs(["🧬 Alimentar Catálogo", "🛠️ Edição em Massa"])

        with tab1:
            st.subheader("Sincronizar Estoque Geral")
            pdf_est = st.file_uploader("Subir PDF de Estoque (Limpo)", type="pdf")
            if pdf_est:
                if st.button("🚀 Iniciar Sincronização"):
                    with st.spinner("Lendo catálogo oficial..."):
                        with pdfplumber.open(pdf_est) as pdf:
                            for page in pdf.pages:
                                for linha in (page.extract_text() or "").split('\n'):
                                    nome_p = limpar_linha_estoque(linha)
                                    if len(nome_p) > 7:
                                        supabase.table("historico_produtos").upsert({"nome_produto": nome_p}, on_conflict="nome_produto").execute()
                        st.success("Estoque sincronizado!")

        with tab2:
            st.subheader("Atribuição de Categorias em Massa")
            st.write("Selecione vários itens (ex: todos os Trelosos) e mova-os de uma vez.")

            try:
                res_h = supabase.table("historico_produtos").select("nome_produto").order("nome_produto").execute()
                lista_sugestoes = [i['nome_produto'] for i in res_h.data]
            except: lista_sugestoes = []

            with st.form("form_bulk"):
                selecionados = st.multiselect("Produtos selecionados:", options=lista_sugestoes)
                nova_cat = st.selectbox("Mover para a categoria:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Mercearia", "Higiene"])
                
                # O aviso que você pediu:
                if selecionados:
                    st.info(f"💡 Você selecionou **{len(selecionados)}** produtos para serem movidos para **{nova_cat}**.")

                btn_salvar = st.form_submit_button("🔥 Confirmar e Mover Agora")
                
                if btn_salvar:
                    if not selecionados:
                        st.error("Por favor, selecione ao menos um item.")
                    else:
                        with st.spinner("Atualizando banco de dados..."):
                            batch = [{"nome_produto": p, "categoria_destino": nova_cat} for p in selecionados]
                            supabase.table("excecoes_categorias").upsert(batch, on_conflict="nome_produto").execute()
                            st.success(f"✅ Sucesso! {len(selecionados)} itens movidos para {nova_cat}.")
                            st.rerun()
