import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from datetime import datetime, date
import time
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÕES DE CONEXÃO (SUPABASE)
# ==========================================
# Certifique-se de ter configurado SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ==========================================
# 2. CONFIGURAÇÕES VISUAIS (INTERFACE PREMIUM)
# ==========================================
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    header { visibility: hidden !important; }
    .stApp { background: radial-gradient(circle at top, #0f172a 0%, #020617 100%) !important; }
    [data-testid="stSidebar"] { background-color: rgba(2, 6, 23, 0.7) !important; backdrop-filter: blur(12px) !important; }
    .assinatura-master { position: fixed; bottom: 15px; left: 15px; background: rgba(2, 6, 23, 0.6); color: #64748b; padding: 8px 14px; border-radius: 12px; z-index: 9999; font-size: 10px; }
    </style>
    <div class="assinatura-master">Desenvolvido por <b>@madson_da_hora</b></div>
""", unsafe_allow_html=True)

# ==========================================
# 3. FUNÇÕES DE BANCO DE DADOS
# ==========================================
def carregar_usuarios():
    # Busca usuários da tabela no Supabase [cite: 44]
    res = supabase.table("usuarios").select("*").execute()
    usuarios_db = res.data
    config = {"usernames": {}}
    for u in usuarios_db:
        config["usernames"][u["username"]] = {"name": u["name"], "password": u["password"]}
    return config, usuarios_db

def registrar_log_db(usuario, arquivo, periodo):
    # Salva logs diretamente na nuvem [cite: 47]
    supabase.table("logs_atividades").insert({
        "usuario": usuario, "arquivo": arquivo, "periodo": periodo
    }).execute()

def consumir_cota_db(username):
    if username != "madson":
        # Chama a função SQL que criamos no Supabase
        supabase.rpc("decrement_quota", {"row_id": username}).execute()

# ==========================================
# 4. MOTOR DE CATEGORIZAÇÃO (COM EXCEÇÕES)
# ==========================================
def palpite_categoria(nome):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome) if unicodedata.category(c) != 'Mn').upper()
    
    # PRIORIDADE 1: Verificar se o dono definiu uma regra manual (Ex: Treloso) [cite: 153]
    try:
        excecao = supabase.table("excecoes_categorias").select("categoria_destino").eq("nome_produto", txt).execute()
        if excecao.data:
            return excecao.data[0]["categoria_destino"], False
    except:
        pass

    # PRIORIDADE 2: Regras Automáticas [cite: 50, 51, 52]
    if any(k in txt for k in ["CIGARRO", "PINE", "ROTHMANS", "FUMO", "ISQUEIRO"]): return "Tabacaria", False
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA"]): return "Bebidas Alcoólicas", False
    if any(k in txt for k in ["SORV", "PICOLE", "ACAI"]): return "Sorvetes", False
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "CHOCOLATE", "BALA"]): return "Bomboniere", False
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "ENO", "PARACETAMOL"]): return "Remédios", False
    
    return "Mercearia", True

# ==========================================
# 5. PROCESSAMENTO DE PDF E LOGIN
# ==========================================
# (Mantenha aqui as suas funções limpar_nome_produto e processar_pdf originais)
def limpar_nome_produto(nome_bruto):
    nome = re.sub(r'\b\d{5,8}\b', '', nome_bruto) [cite: 48]
    return nome.replace('.', '').replace('-', '').strip()[:22]

def processar_pdf(file):
    dados = []
    file.seek(0)
    with pdfplumber.open(file) as pdf:
        txt_topo = (pdf.pages[0].extract_text() or "")
        match_d = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', txt_topo)
        periodo = f"{match_d.group(1)} a {match_d.group(2)}" if match_d else "DATA DESCONHECIDA" [cite: 58]
        for page in pdf.pages:
            linhas = (page.extract_text() or "").split('\n')
            for linha in linhas:
                valores = re.findall(r'\d+,\d{2}', linha)
                if len(valores) >= 4:
                    ean_m = re.search(r'\b\d{7,14}\b', linha)
                    if not ean_m: continue
                    n_bruto = linha.replace(ean_m.group(), "").strip()
                    nome_limpo = limpar_nome_produto(n_bruto)
                    val = float(valores[-4].replace(',', '.'))
                    cat, is_fallback = palpite_categoria(nome_limpo)
                    dados.append({"Nome": nome_limpo, "Cat": cat, "Valor": val, "Fallback": is_fallback})
    return dados, periodo

# --- AUTENTICAÇÃO ---
config_auth, usuarios_completos = carregar_usuarios()
authenticator = stauth.Authenticate(config_auth, "canada_bi_v2", "auth_key_v2", expiry_days=30)

if not st.session_state.get("authentication_status"):
    authenticator.login(location='main')
else:
    user_logado = st.session_state['username']
    st.sidebar.write(f"Olá, {st.session_state['name']}")
    
    pagina = st.sidebar.radio("Navegação", ["Análise", "Exceções e Permissões"])
    authenticator.logout("Sair", "sidebar")

    if pagina == "Análise":
        file = st.file_uploader("Enviar PDF", type="pdf")
        if file:
            dados, per = processar_pdf(file)
            df = pd.DataFrame(dados)
            st.write(f"### Período: {per}")
            st.dataframe(df)
            registrar_log_db(user_logado, file.name, per)
            consumir_cota_db(user_logado)

    elif pagina == "Exceções e Permissões":
        st.header("🛠️ Ajustar Categorias (Vontade do Cliente)")
        with st.form("nova_excecao"):
            nome_p = st.text_input("Nome do Produto no PDF (Ex: TRELOSO)")
            destino = st.selectbox("Forçar Categoria:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Remédios", "Mercearia"])
            if st.form_submit_button("Salvar Regra"):
                supabase.table("excecoes_categorias").upsert({"nome_produto": nome_p.upper().strip(), "categoria_destino": destino}).execute()
                st.success("Regra aplicada!")
                st.rerun()
        
        # Listar Exceções
        st.write("---")
        regras = supabase.table("excecoes_categorias").select("*").execute()
        for r in regras.data:
            c1, c2 = st.columns([8, 2])
            c1.write(f"**{r['nome_produto']}** -> {r['categoria_destino']}")
            if c2.button("🗑️", key=r['id']):
                supabase.table("excecoes_categorias").delete().eq("id", r['id']).execute()
                st.rerun()
