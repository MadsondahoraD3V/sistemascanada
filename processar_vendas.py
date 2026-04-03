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

# --- 2. ESTILO GLASS DARK E CONFIGURAÇÃO ---
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #020617 100%) !important;
        color: #f8fafc;
    }
    div[data-testid="stForm"], .stExpander, .stTabs, div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px !important;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .stButton>button {
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
        font-weight: bold;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.6);
    }
    [data-testid="stSidebar"] {
        background-color: rgba(2, 6, 23, 0.8) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.07) !important;
        border-radius: 8px !important;
    }
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. MOTORES LÓGICOS DE ALTA PERFORMANCE ---

def limpar_linha_estoque(linha):
    ignorar = ["MERCADINHO", "ENDEREÇO", "PAGINA", "ESTOQUE", "GESTÃO", "SMB STORE", "CNPJ", "TELEFONE", "CÓDIGO"]
    if any(p in linha.upper() for p in ignorar): return ""
    n = re.sub(r'\b\d{13,14}\b', '', linha)
    n = re.sub(r'^\s*\d{1,7}\s+', '', n)
    n = re.sub(r'[.\-/"\']', '', n)
    return n.strip().upper()

# NOVIDADE: Carrega as regras APENAS UMA VEZ para o sistema ficar 3x mais rápido
@st.cache_data(ttl=10) # Guarda na memória por 10 segundos
def carregar_regras_banco():
    try:
        res = supabase.table("excecoes_categorias").select("*").execute()
        return [(r['nome_produto'], r['categoria_destino']) for r in res.data]
    except:
        return []

def palpite_categoria(nome_bruto, regras_carregadas):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome_bruto) if unicodedata.category(c) != 'Mn').upper().strip()
    
    # 1. Checagem Inteligente de Exceções (Resolve o problema do Treloso cortado)
    for regra_nome, categoria_destino in regras_carregadas:
        # Se um começa com o outro, significa que é o mesmo produto (mesmo cortado no PDF)
        if txt.startswith(regra_nome) or regra_nome.startswith(txt):
            return categoria_destino, False
    
    # 2. Regras Padrões
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
    regras = carregar_regras_banco() # Puxa da memória rápida
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
                    cat, _ = palpite_categoria(n_limpo, regras)
                    dados.append({"Produto": n_limpo, "Categoria": cat, "Valor": val_unit})
    return dados

# --- 4. AUTENTICAÇÃO ---
try:
    res_user = supabase.table("usuarios").select("*").execute()
    db_users = {u['username']: {"name": u['name'], "password": u['password']} for u in res_user.data}
except:
    db_users = {"admin": {"name": "Admin", "password": "123"}}

config_auth = {"usernames": db_users}
auth = stauth.Authenticate(config_auth, "canada_bi_v3", "sig_key_2024", expiry_days=30)

if not st.session_state.get("authentication_status"):
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🇨🇦 Canadá BI</h1>", unsafe_allow_html=True)
    auth.login(location='main')
else:
    # Nomes e visual exatamente iguais aos prints antigos
    st.sidebar.markdown(f"### Bem-vindo(a), <br><span style='color:#3b82f6'>{st.session_state['name']}</span>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegação", ["Início", "Exceções e Permissões"])
    st.sidebar.markdown("---")
    auth.logout("Sair", "sidebar")

    if menu == "Início":
        st.header("📊 Dashboard de Operações")
        file = st.file_uploader("📂 Subir PDF de Vendas Diárias", type="pdf")
        
        if file:
            with st.spinner("Processando em alta velocidade..."):
                lista_dados = processar_vendas_baguncado(file)
                
                if lista_dados:
                    df = pd.DataFrame(lista_dados)
                    
                    # --- RESTAURAÇÃO DAS MÉTRICAS NO TOPO ---
                    total_vendas = df['Valor'].sum()
                    qtd_categorias = df['Categoria'].nunique()
                    media_item = df['Valor'].mean()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Total Vendido", f"R$ {total_vendas:,.2f}".replace(',','_').replace('.',',').replace('_','.'))
                    col2.metric("🏷️ Categorias", f"{qtd_categorias}")
                    col3.metric("📈 Média por Item", f"R$ {media_item:,.2f}".replace(',','_').replace('.',',').replace('_','.'))
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)

    elif menu == "Exceções e Permissões":
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
                    st.success("Estoque sincronizado! Autocomplete atualizado.")

        with tab_bulk:
            st.subheader("🛠️ Movimentação em Lote")
            st.write("Selecione múltiplos produtos e mude a categoria de todos de uma vez.")

            try:
                res_h = supabase.table("historico_produtos").select("nome_produto").order("nome_produto").execute()
                lista_sugestoes = [i['nome_produto'] for i in res_h.data]
            except: lista_sugestoes = []

            with st.form("form_bulk_move"):
                selecionados = st.multiselect("Pesquise e selecione (Ex: TRELOSO):", options=lista_sugestoes)
                nova_cat = st.selectbox("Mover para:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Mercearia", "Higiene"])
                
                if selecionados:
                    st.info(f"⚠️ **Atenção:** Você marcou **{len(selecionados)}** itens para **{nova_cat}**.")
                
                btn_massa = st.form_submit_button("🔥 APLICAR EM TODOS")
                
                if btn_massa:
                    if not selecionados:
                        st.error("Nenhum item selecionado!")
                    else:
                        with st.spinner(f"Processando {len(selecionados)} itens..."):
                            batch = [{"nome_produto": p, "categoria_destino": nova_cat} for p in selecionados]
                            supabase.table("excecoes_categorias").upsert(batch, on_conflict="nome_produto").execute()
                            # Limpa o cache para que a aba "Início" leia as novas regras instantaneamente
                            st.cache_data.clear()
                            st.success(f"✅ Sucesso! {len(selecionados)} itens configurados.")
                            st.rerun()

        with st.expander("📋 Ver Regras Ativas"):
            regras = supabase.table("excecoes_categorias").select("*").execute()
            if regras.data:
                st.dataframe(pd.DataFrame(regras.data)[["nome_produto", "categoria_destino"]], use_container_width=True)
