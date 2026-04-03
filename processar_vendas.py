import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from supabase import create_client, Client

# --- 1. CONEXÃO SUPABASE ---
# Certifique-se de que as chaves estão nos Secrets do Streamlit
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")
st.markdown("""
    <style>
    header {visibility: hidden;}
    .stApp {background-color: #0e1117; color: white;}
    </style>
""", unsafe_allow_html=True)

# --- 3. MOTORES DE LIMPEZA E LÓGICA ---

def limpar_linha_estoque(linha):
    """Limpa linhas do PDF de Estoque (o arquivo 'limpo')"""
    # Palavras que indicam cabeçalho ou lixo que devem ser ignoradas
    ignorar = ["MERCADINHO", "ENDEREÇO", "PAGINA", "ESTOQUE", "GESTÃO", "SMB STORE", "CNPJ", "TELEFONE", "CÓDIGO"]
    if any(palavra in linha.upper() for palavra in ignorar):
        return ""
    
    # Remove EANs (13-14 dígitos) e códigos internos (1-7 dígitos no início da linha)
    n = re.sub(r'\b\d{13,14}\b', '', linha)
    n = re.sub(r'^\s*\d{1,7}\s+', '', n)
    # Remove caracteres especiais e espaços extras
    n = re.sub(r'[.\-/"\']', '', n)
    return n.strip().upper()

def palpite_categoria(nome_bruto):
    """Motor lógico para PDFs de Venda (o arquivo 'bagunçado')"""
    # Normalização (remove acentos)
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome_bruto) if unicodedata.category(c) != 'Mn').upper().strip()
    
    # 1º: Tenta buscar na tabela de EXCEÇÕES (Regras que você criou manualmente)
    try:
        regras = supabase.table("excecoes_categorias").select("*").execute()
        for r in regras.data:
            if r['nome_produto'] in txt:
                return r['categoria_destino'], False
    except: pass

    # 2º: Regras Genéricas Automáticas
    if any(k in txt for k in ["CIGARRO", "PINE", "ROTHMANS", "GIFT"]): return "Tabacaria", False
    if any(k in txt for k in ["CERV", "HEINEKEN", "PITU", "SKOL", "BRAHMA", "ANTARCTICA", "WINE", "VINHO"]): return "Bebidas Alcoólicas", False
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "CHOCOLATE", "BALA", "HALLS"]): return "Bomboniere", False
    if any(k in txt for k in ["SORV", "PICOLE", "ACAI"]): return "Sorvetes", False
    if any(k in txt for k in ["SABONETE", "SHAMPOO", "CREME", "DENTAL", "FRALDA"]): return "Higiene", False
    
    return "Mercearia", True # Categoria padrão se nada for encontrado

# --- 4. PROCESSAMENTO DE ARQUIVOS ---

def processar_vendas_baguncado(file):
    """Lê o PDF de vendas real e extrai produtos e valores"""
    dados = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            linhas = (page.extract_text() or "").split('\n')
            for l in linhas:
                valores = re.findall(r'\d+,\d{2}', l)
                if len(valores) >= 4:
                    # Tenta limpar o nome removendo o código de barras (7 a 14 dígitos)
                    ean_m = re.search(r'\b\d{7,14}\b', l)
                    n_limpo = l.replace(ean_m.group(), "") if ean_m else l
                    # Remove códigos curtos residuais e limita o tamanho do nome
                    n_limpo = re.sub(r'\b\d{4,8}\b', '', n_limpo).strip()[:35].upper()
                    
                    val_unit = float(valores[-4].replace(',', '.'))
                    cat, _ = palpite_categoria(n_limpo)
                    dados.append({"Produto": n_limpo, "Categoria": cat, "Valor": val_unit})
    return dados

# --- 5. AUTENTICAÇÃO E INTERFACE ---

try:
    res_user = supabase.table("usuarios").select("*").execute()
    db_users = {u['username']: {"name": u['name'], "password": u['password']} for u in res_user.data}
except:
    db_users = {"admin": {"name": "Admin", "password": "123"}} # Fallback de emergência

config = {"usernames": db_users}
auth = stauth.Authenticate(config, "canada_bi_cookie", "signature_key", expiry_days=30)

if not st.session_state.get("authentication_status"):
    st.title("🇨🇦 Canadá BI - Login")
    auth.login(location='main')
elif st.session_state["authentication_status"] is False:
    st.error("Usuário ou senha incorretos")
    auth.login(location='main')
else:
    # --- LOGADO COM SUCESSO ---
    st.sidebar.title(f"Olá, {st.session_state['name']}")
    menu = st.sidebar.radio("Navegação", ["📊 Análise de Vendas", "⚙️ Configurações e Inteligência"])
    auth.logout("Sair do Sistema", "sidebar")

    if menu == "📊 Análise de Vendas":
        st.header("📊 Processamento de Vendas")
        file_vendas = st.file_uploader("Subir PDF de Vendas (Arquivo Diário)", type="pdf")
        
        if file_vendas:
            with st.spinner("Analisando PDF..."):
                lista_final = processar_vendas_baguncado(file_vendas)
                df = pd.DataFrame(lista_final)
                st.success("Análise concluída!")
                st.dataframe(df, use_container_width=True)

    elif menu == "⚙️ Configurações e Inteligência":
        st.header("⚙️ Central de Inteligência do Sistema")
        
        col_sync, col_regra = st.columns(2)
        
        with col_sync:
            st.subheader("🧬 Sincronizar Estoque")
            st.write("Ensine ao sistema todos os produtos que o mercado possui.")
            pdf_est = st.file_uploader("Subir PDF de Estoque/Catálogo (Limpo)", type="pdf", key="sync_est")
            
            if pdf_est:
                with st.spinner("Alimentando memória do Autocomplete..."):
                    with pdfplumber.open(pdf_est) as pdf:
                        for page in pdf.pages:
                            for linha in (page.extract_text() or "").split('\n'):
                                nome_p = limpar_linha_estoque(linha)
                                if len(nome_p) > 7:
                                    try:
                                        # 'on_conflict' evita o erro de duplicidade (PGRST23505)
                                        supabase.table("historico_produtos").upsert(
                                            {"nome_produto": nome_p}, 
                                            on_conflict="nome_produto"
                                        ).execute()
                                    except: continue
                    st.success("Estoque sincronizado com sucesso!")

        with col_regra:
            st.subheader("🛠️ Criar Regra de Categoria")
            st.write("Defina para qual categoria um produto deve ir.")
            
            # Busca a lista de sugestões que veio do estoque sincronizado
            try:
                res_h = supabase.table("historico_produtos").select("nome_produto").order("nome_produto").execute()
                lista_sugestoes = [item['nome_produto'] for item in res_h.data]
            except:
                lista_sugestoes = ["Suba o PDF de estoque primeiro"]

            with st.form("form_regra"):
                escolha = st.selectbox("Selecione o Produto:", options=lista_sugestoes)
                nova_cat = st.selectbox("Mover para:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Mercearia", "Higiene"])
                
                if st.form_submit_button("Salvar Exceção"):
                    supabase.table("excecoes_categorias").upsert({
                        "nome_produto": escolha, 
                        "categoria_destino": nova_cat
                    }).execute()
                    st.success(f"Regra Criada: {escolha} agora é {nova_cat}!")
                    st.rerun()
