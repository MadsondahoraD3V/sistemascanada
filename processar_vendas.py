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

# --- 2. ESTILO GLASS DARK (O VISUAL DO CANADA-BI) ---
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    /* Fundo Principal com Gradiente */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%) !important;
        color: #f8fafc;
    }

    /* Efeito de Vidro (Glassmorphism) nos Containers */
    div[data-testid="stForm"], .stExpander, .stTabs {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px !important;
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* Botões com efeito Glow e Hover */
    .stButton>button {
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.6);
        background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%);
    }

    /* Estilização da Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(2, 6, 23, 0.8) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Inputs, Selectbox e Multiselect */
    .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.07) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
    }

    /* Avisos e Infos no estilo Glass */
    .stAlert {
        background: rgba(59, 130, 246, 0.1) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        color: #93c5fd !important;
        border-radius: 12px;
    }

    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. MOTORES LÓGICOS (VENDAS E ESTOQUE) ---

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
    
    dicionario = {
        "Tabacaria": ["CIGARRO", "PINE", "ROTHMANS", "GIFT", "DUNHILL", "LUCKY"],
        "Bebidas Alcoólicas": ["CERV", "HEINEKEN", "PITU", "SKOL", "BRAHMA", "ANTARCTICA", "VINHO", "WHISKY"],
        "Bomboniere": ["TRIDENT", "DOCE", "BOMBOM", "FINI", "CHOCOLATE", "BALA", "HALLS", "BIS", "TAMPICO"],
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

auth = stauth.Authenticate(db_users, "canada_bi_v3", "sig_key_2024", expiry_days=30)

if not st.session_state.get("authentication_status"):
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🇨🇦 Canadá BI</h1>", unsafe_allow_html=True)
    auth.login(location='main')
else:
    st.sidebar.markdown(f"### Olá, <span style='color:#3b82f6'>{st.session_state['name']}</span>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegação", ["📊 Análise de Vendas", "⚙️ Inteligência de Dados"])
    auth.logout("Encerrar Sessão", "sidebar")

    if menu == "📊 Análise de Vendas":
        st.header("📊 Dashboard de Operações")
        file = st.file_uploader("📂 Subir PDF de Vendas Diárias", type="pdf")
        if file:
            with st.spinner("Decodificando arquivo..."):
                df = pd.DataFrame(processar_vendas_baguncado(file))
                st.dataframe(df, use_container_width=True)

    elif menu == "⚙️ Inteligência de Dados":
        st.header("⚙️ Central de Inteligência")
        
        tab_sync, tab_bulk = st.tabs(["📥 Sincronizar Estoque", "🔥 Atribuição em Massa"])

        with tab_sync:
            st.subheader("Atualizar Catálogo Base")
            pdf_est = st.file_uploader("PDF de Estoque (Lista Limpa)", type="pdf", key="sync_pdf")
            if pdf_est and st.button("🚀 Sincronizar Agora"):
                with st.spinner("Salvando nomes no banco..."):
                    with pdfplumber.open(pdf_est) as pdf:
                        for page in pdf.pages:
                            for linha in (page.extract_text() or "").split('\n'):
                                nome_p = limpar_linha_estoque(linha)
                                if len(nome_p) > 7:
                                    supabase.table("historico_produtos").upsert({"nome_produto": nome_p}, on_conflict="nome_produto").execute()
                    st.success("Estoque sincronizado!")

        with tab_bulk:
            st.subheader("🛠️ Movimentação em Lote")
            st.markdown("Selecione múltiplos produtos e mude a categoria de todos com um clique.")

            # Busca lista atualizada do histórico
            try:
                res_h = supabase.table("historico_produtos").select("nome_produto").order("nome_produto").execute()
                lista_sugestoes = [i['nome_produto'] for i in res_h.data]
            except: lista_sugestoes = []

            with st.form("form_bulk_move"):
                selecionados = st.multiselect("Pesquise e selecione os itens (Ex: TRELOSO):", options=lista_sugestoes)
                nova_cat = st.selectbox("Mover para:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Mercearia", "Higiene"])
                
                # O Aviso de Confirmação
                if selecionados:
                    st.info(f"⚠️ **Atenção:** Você marcou **{len(selecionados)}** itens para serem classificados como **{nova_cat}**.")
                
                btn_massa = st.form_submit_button("🔥 APLICAR EM TODOS")
                
                if btn_massa:
                    if not selecionados:
                        st.error("Nenhum item selecionado!")
                    else:
                        with st.spinner(f"Processando {len(selecionados)} itens..."):
                            batch = [{"nome_produto": p, "categoria_destino": nova_cat} for p in selecionados]
                            supabase.table("excecoes_categorias").upsert(batch, on_conflict="nome_produto").execute()
                            st.success(f"✅ Sucesso! {len(selecionados)} itens configurados como {nova_cat}.")
                            st.rerun()

        with st.expander("📋 Ver Regras Ativas"):
            regras = supabase.table("excecoes_categorias").select("*").execute()
            if regras.data:
                st.dataframe(pd.DataFrame(regras.data)[["nome_produto", "categoria_destino"]], use_container_width=True)
