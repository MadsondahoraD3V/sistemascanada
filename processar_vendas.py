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

# --- 3. MOTORES LÓGICOS DE ALTA PRECISÃO ---

def limpar_linha_estoque(linha):
    ignorar = ["MERCADINHO", "ENDEREÇO", "PAGINA", "ESTOQUE", "GESTÃO", "SMB STORE", "CNPJ", "TELEFONE", "CÓDIGO"]
    if any(p in linha.upper() for p in ignorar): return ""
    n = re.sub(r'\b\d{13,14}\b', '', linha)
    n = re.sub(r'^\s*\d{1,7}\s+', '', n)
    n = re.sub(r'[.\-/"\']', '', n)
    return n.strip().upper()

# Cache para alta velocidade - Guarda as regras formatadas na memória
@st.cache_data(ttl=10)
def carregar_regras_banco():
    try:
        res = supabase.table("excecoes_categorias").select("*").execute()
        regras = []
        for r in res.data:
            nome = r['nome_produto']
            cat = r['categoria_destino']
            palavras = set(nome.split())
            regras.append((nome, palavras, cat))
        return regras
    except: return []

def palpite_categoria(nome_bruto, regras_carregadas):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome_bruto) if unicodedata.category(c) != 'Mn').upper().strip()
    
    # 1. BUSCA INTELIGENTE NAS EXCEÇÕES (Evita conflitos de nomes longos x curtos)
    # Ignora palavras comuns para focar na "Marca" do produto (ex: foca em TRELOSO, ignora BISC)
    stopwords = {"BISC", "BISCOITO", "BOMBOM", "PCT", "UND", "UN", "KG", "DE", "SABOR", "COM", "CHOCO", "CHOCOLATE", "MORANGO", "LATA", "GARRAFA", "PET", "ML", "GR", "G", "CAIXA", "CX", "AO", "LEITE"}
    
    palavras_txt = [w for w in txt.split() if w not in stopwords and len(w) > 2]
    
    for regra_nome, palavras_regra, categoria_destino in regras_carregadas:
        if regra_nome in txt or txt in regra_nome:
            return categoria_destino, False
        
        # Se o PDF e a Regra compartilharem uma palavra FORTE (ex: TRELOSO), ele obedece a exceção!
        for p in palavras_txt:
            if p in palavras_regra:
                return categoria_destino, False

    # 2. DICIONÁRIO DE REGEX (Usa \b para não confundir 'BIS' com 'BISCOITO')
    dicionario_regex = {
        "Tabacaria": [r"\bCIGARRO", r"\bPINE\b", r"\bROTHMANS", r"\bGIFT\b", r"\bDUNHILL", r"\bLUCKY\b"],
        "Bebidas Alcoólicas": [r"\bCERV", r"\bHEINEKEN", r"\bPITU\b", r"\bSKOL", r"\bBRAHMA", r"\bANTARCTICA", r"\bVINHO", r"\bWHISKY", r"\bVODKA", r"\bICE\b", r"\bCOROTE\b"],
        "Bomboniere": [r"\bTRIDENT\b", r"\bDOCE\b", r"\bBOMBOM", r"\bFINI\b", r"\bCHOC\w*", r"\bBALA\b", r"\bHALLS\b", r"\bBIS\b", r"\bTAMPICO\b"],
        "Sorvetes": [r"\bSORV", r"\bPICOLE", r"\BACAI\b", r"\bKIBON\b"],
        "Higiene": [r"\bSABONETE\b", r"\bSHAMPOO\b", r"\bCREME\b", r"\bDENTAL\b", r"\bFRALDA\b", r"\bPAPEL\b", r"\bABSORVENTE\b"]
    }
    
    for cat, padroes in dicionario_regex.items():
        for p in padroes:
            if re.search(p, txt):
                return cat, False
                
    return "Mercearia", True

def processar_vendas_baguncado(file):
    dados = []
    regras = carregar_regras_banco()
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

# --- 4. AUTENTICAÇÃO E DADOS DE USUÁRIOS ---
try:
    res_user = supabase.table("usuarios").select("*").execute()
    db_users = {u['username']: {"name": u['name'], "password": u['password']} for u in res_user.data}
    dados_logados = {u['username']: u for u in res_user.data}
except:
    db_users = {"admin": {"name": "Admin", "password": "123"}}
    dados_logados = {}

config_auth = {"usernames": db_users}
auth = stauth.Authenticate(config_auth, "canada_bi_v3", "sig_key_2024", expiry_days=30)

if not st.session_state.get("authentication_status"):
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🇨🇦 Canadá BI</h1>", unsafe_allow_html=True)
    auth.login(location='main')
else:
    # --- MENU OFICIAL COM CONTROLE DE PERMISSÕES ---
    username_atual = st.session_state["username"]
    info_usuario = dados_logados.get(username_atual, {})
    
    st.sidebar.markdown(f"### Bem-vindo(a), <br><span style='color:#3b82f6'>{st.session_state['name']}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    opcoes_menu = ["Início", "Relatórios em Lote", "Exceções e Permissões", "Central de Permissões"]
    menu = st.sidebar.radio("Navegação", opcoes_menu)
    
    st.sidebar.markdown("---")
    auth.logout("Sair", "sidebar")

    # --- ABA: INÍCIO ---
    if menu == "Início":
        st.header("📊 Dashboard de Operações")
        file = st.file_uploader("📂 Subir PDF de Vendas Diárias", type="pdf")
        
        if file:
            with st.spinner("Processando dados (Modo Rápido ativado)..."):
                lista_dados = processar_vendas_baguncado(file)
                if lista_dados:
                    df = pd.DataFrame(lista_dados)
                    
                    total_vendas = df['Valor'].sum()
                    qtd_categorias = df['Categoria'].nunique()
                    media_item = df['Valor'].mean()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 Total Vendido", f"R$ {total_vendas:,.2f}".replace(',','_').replace('.',',').replace('_','.'))
                    col2.metric("🏷️ Categorias", f"{qtd_categorias}")
                    col3.metric("📈 Média por Item", f"R$ {media_item:,.2f}".replace(',','_').replace('.',',').replace('_','.'))
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.dataframe(df, use_container_width=True)

    # --- ABA: RELATÓRIOS EM LOTE ---
    elif menu == "Relatórios em Lote":
        st.header("📂 Análise em Lote")
        if info_usuario.get("acesso_lote") == True or username_atual == "madson" or username_atual == "admin":
            st.info("🟢 Módulo Lote: Permissão concedida. Insira os arquivos.")
            # Interface de múltiplos uploads viria aqui
        else:
            st.error("🔒 Acesso Bloqueado. Seu perfil não tem permissão para usar este módulo. Contate o administrador.")

    # --- ABA: EXCEÇÕES ---
    elif menu == "Exceções e Permissões":
        st.header("⚙️ Central de Inteligência e Estoque")
        tab_sync, tab_bulk = st.tabs(["📥 Sincronizar Estoque", "🔥 Atribuição em Massa"])

        with tab_sync:
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
            try:
                res_h = supabase.table("historico_produtos").select("nome_produto").order("nome_produto").execute()
                lista_sugestoes = [i['nome_produto'] for i in res_h.data]
            except: lista_sugestoes = []

            with st.form("form_bulk_move"):
                selecionados = st.multiselect("Pesquise e selecione (Ex: TRELOSO):", options=lista_sugestoes)
                nova_cat = st.selectbox("Mover para:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Mercearia", "Higiene"])
                
                btn_massa = st.form_submit_button("🔥 APLICAR EM TODOS")
                if btn_massa and selecionados:
                    with st.spinner(f"Processando..."):
                        batch = [{"nome_produto": p, "categoria_destino": nova_cat} for p in selecionados]
                        supabase.table("excecoes_categorias").upsert(batch, on_conflict="nome_produto").execute()
                        st.cache_data.clear() # OBRIGA O SISTEMA A LER AS NOVAS REGRAS NA HORA
                        st.success(f"✅ Itens configurados com sucesso.")
                        st.rerun()

    # --- ABA: CENTRAL DE PERMISSÕES (ADMIN) ---
    elif menu == "Central de Permissões":
        st.header("🔐 Controle Total de Acessos")
        
        tab_novo, tab_gerenciar = st.tabs(["👤 Novo Cliente", "⚙️ Gerenciar Limites"])
        
        with tab_novo:
            with st.form("novo_user"):
                st.subheader("Criar Login")
                n_user = st.text_input("Usuário (ex: mercadinho)")
                n_nome = st.text_input("Nome de Exibição")
                n_senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Acesso"):
                    try:
                        supabase.table("usuarios").insert({"username": n_user, "name": n_nome, "password": n_senha, "limite_pdf": 10, "dias_trial": 7, "acesso_lote": False}).execute()
                        st.success("Cliente cadastrado com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao cadastrar. Detalhe: {e}")

        with tab_gerenciar:
            st.subheader("Painel de Controle")
            for u in res_user.data:
                with st.expander(f"🔧 {u['name']} (@{u['username']})"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        limite = st.number_input("Limite de PDFs", value=u.get('limite_pdf', 10), key=f"l_{u['username']}")
                    with c2:
                        trial = st.number_input("Dias de Trial", value=u.get('dias_trial', 7), key=f"t_{u['username']}")
                    with c3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        lote = st.checkbox("Liberar Relatório Lote", value=u.get('acesso_lote', False), key=f"b_{u['username']}")
                    
                    if st.button("Salvar Permissões", key=f"btn_{u['username']}"):
                        supabase.table("usuarios").update({
                            "limite_pdf": limite,
                            "dias_trial": trial,
                            "acesso_lote": lote
                        }).eq("username", u['username']).execute()
                        st.success("Regras aplicadas!")
