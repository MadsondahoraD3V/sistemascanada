import streamlit as st
import streamlit_authenticator as stauth
import pdfplumber
import re
import pandas as pd
import unicodedata
from datetime import datetime, date
import os
from supabase import create_client, Client

# ==========================================
# 1. CONEXÃO SUPABASE
# ==========================================
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# ==========================================
# 2. CONFIGURAÇÕES VISUAIS E CSS (INTOCADO)
# ==========================================
st.set_page_config(page_title="Canadá BI - Corporate", layout="wide")

st.markdown("""
    <style>
    header { visibility: hidden !important; display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    #MainMenu { visibility: hidden !important; display: none !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; max-width: 98% !important; }
    
    .stApp { background: radial-gradient(circle at top, #0f172a 0%, #020617 100%) !important; }
    
    [data-testid="stSidebar"] { 
        background-color: rgba(2, 6, 23, 0.7) !important; 
        border-right: 1px solid rgba(255,255,255,0.05) !important; 
        backdrop-filter: blur(12px) !important;
    }
    
    .stTextInput label p, .stPasswordInput label p, .stSelectbox label p, .stNumberInput label p, .stDateInput label p { 
        color: #e2e8f0 !important; font-weight: 600 !important; 
        font-size: clamp(11px, 1vw, 13px) !important; 
        letter-spacing: 0.5px;
    }
    
    .stTextInput input, .stPasswordInput input {
        background-color: rgba(15, 23, 42, 0.6) !important; color: #ffffff !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 8px !important;
        font-size: clamp(12px, 1vw, 14px) !important; padding: 8px 12px !important; min-height: 35px !important;
    }
    .stTextInput input:focus, .stPasswordInput input:focus {
        border-color: #38bdf8 !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.2) !important;
    }
    
    [data-testid="stFileUploadDropzone"] { background-color: rgba(15, 23, 42, 0.4) !important; }
    [data-testid="stFileUploader"] {
        background-color: rgba(15, 23, 42, 0.4) !important; border-radius: 12px; padding: 20px;
        border: 1px dashed rgba(56, 189, 248, 0.4) !important; backdrop-filter: blur(8px);
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploader"]:hover { border-color: #38bdf8 !important; background-color: rgba(15, 23, 42, 0.8) !important; }
    [data-testid="stFileUploaderDropzoneInstructions"] { display: none; }
    small { display: none !important; }
    
    div[role="radiogroup"] > label > div:first-of-type { display: none; }
    div[role="radiogroup"] > label {
        background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(255,255,255,0.05) !important; 
        border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; text-align: left; cursor: pointer;
        transition: all 0.3s ease; color: #94a3b8 !important; font-weight: 600; width: 100%; position: relative;
        font-size: clamp(11px, 1vw, 13px) !important;
    }
    div[role="radiogroup"] > label:hover, div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked) { 
        background: rgba(56, 189, 248, 0.1) !important; border-color: rgba(56, 189, 248, 0.3) !important; 
        color: #ffffff !important; transform: translateX(4px); box-shadow: -4px 0px 0px 0px #38bdf8;
    }
    div[role="radiogroup"] > label[data-baseweb="radio"] > div:last-child { width: 100%; }
    
    .stButton > button, .stDownloadButton > button {
        padding: 4px 12px !important; font-size: clamp(11px, 1vw, 13px) !important; font-weight: 700 !important; min-height: 32px !important; 
        border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.1) !important;
        background: rgba(15, 23, 42, 0.8) !important; color: #e2e8f0 !important; transition: all 0.3s ease;
        white-space: nowrap !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: rgba(56, 189, 248, 0.15) !important; border-color: #38bdf8 !important; color: #ffffff !important;
        transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }

    div[data-testid="column"]:nth-of-type(1) div[data-testid="stHorizontalBlock"] {
        gap: 0rem !important; align-items: center !important; margin-bottom: -15px !important;
    }
    
    .botao-categoria button {
        background-color: transparent !important; border: none !important; color: #94a3b8 !important;
        justify-content: flex-start !important; padding: 0px 4px !important; font-weight: 700 !important;
        box-shadow: none !important; min-height: 20px !important;
        transition: all 0.3s ease !important; width: 100% !important;
    }
    .botao-categoria button:hover { color: #38bdf8 !important; transform: translateX(3px); }
    .botao-categoria button div, .botao-categoria button p {
        white-space: nowrap !important; 
        font-size: clamp(10px, 1.1vw, 13px) !important; overflow: hidden !important; text-overflow: ellipsis !important; text-align: left !important;
    }

    [data-testid="stCheckbox"] { padding-top: 4px !important; }
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(56,189,248,0.5); }

    [data-testid="stExpander"] { background-color: rgba(15, 23, 42, 0.3) !important; border: 1px solid rgba(255,255,255,0.05) !important; border-radius: 8px !important; }
    [data-testid="stExpander"] p { color: #94a3b8 !important; font-weight: 600 !important; }
    
    .assinatura-master {
        position: fixed; bottom: 15px; left: 15px; background: rgba(2, 6, 23, 0.6); color: #64748b;
        padding: 8px 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); 
        z-index: 999999; backdrop-filter: blur(10px); pointer-events: none; white-space: nowrap;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); letter-spacing: 0.5px; text-align: left;
    }
    footer {visibility: hidden;}
    </style>
    
    <div class="assinatura-master">
        <span style="font-size: 10px; text-transform: uppercase;">Desenvolvido por <span style="color: #e0e7ff; font-weight: bold;">@madson_da_hora</span></span><br>
        <span style="font-size: 8px; color: #94a3b8; font-weight: normal;">Analista de dados & Programador</span>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. HTML GERADOR DE RELATÓRIOS (INTOCADO)
# ==========================================
CORES_CATEGORIAS = {
    "Tabacaria": {"bg": "rgba(30, 41, 59, 0.7)", "glow": "rgba(51, 65, 85, 0.4)", "border": "#475569"},
    "Bebidas Alcoólicas": {"bg": "rgba(30, 58, 138, 0.6)", "glow": "rgba(37, 99, 235, 0.3)", "border": "#3b82f6"},
    "Bomboniere": {"bg": "rgba(13, 148, 136, 0.6)", "glow": "rgba(20, 184, 166, 0.3)", "border": "#14b8a6"},
    "Sorvetes": {"bg": "rgba(219, 39, 119, 0.6)", "glow": "rgba(190, 24, 93, 0.3)", "border": "#db2777"},
    "Remédios": {"bg": "rgba(190, 18, 60, 0.6)", "glow": "rgba(225, 29, 72, 0.3)", "border": "#e11d48"},
    "Higiene": {"bg": "rgba(190, 18, 60, 0.6)", "glow": "rgba(225, 29, 72, 0.3)", "border": "#e11d48"},
    "Mercearia": {"bg": "rgba(3, 105, 161, 0.6)", "glow": "rgba(2, 132, 199, 0.3)", "border": "#0284c7"}
}

def formatar_moeda(valor):
    return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def gerar_html_interativo(df, periodo, total_geral, nome_arquivo):
    colunas_html = ""
    categorias_presentes = sorted(df['Cat'].unique())
    for i, cat in enumerate(categorias_presentes):
        paleta = CORES_CATEGORIAS.get(cat, {"bg": "rgba(30, 41, 59, 0.7)", "glow": "rgba(51, 65, 85, 0.4)", "border": "#475569"})
        itens_cat = df[df['Cat'] == cat]
        valor_cat = itens_cat['Valor'].sum()
        cards_html = "".join([f'<div class="cyber-card"><div class="card-title">{row["Nome"]}</div><div class="card-value">R$ {row["Valor"]:,.2f}</div></div>' for _, row in itens_cat.iterrows()])
        colunas_html += f"""
        <div class="coluna-categoria">
            <div class="accordion-header" style="background: {paleta['bg']}; box-shadow: 0 4px 15px {paleta['glow']}; border-color: {paleta['border']};" onclick="toggleAccordion('content-{i}')">
                <div style="display:flex; align-items:center;">
                    <input type="checkbox" checked class="cat-check" data-cat="{cat}" data-valor="{valor_cat}" onclick="event.stopPropagation();" onchange="recalcular()">
                    <span class="cat-title">{cat.upper()}</span>
                </div>
                <span class="cat-total">R$ {valor_cat:,.2f}</span>
            </div>
            <div id="content-{i}" class="accordion-content"><div class="content-inner">{cards_html}</div></div>
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Canadá BI - Relatório Oficial</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap" rel="stylesheet">
        <style>
            :root {{ --bg-main: #020617; --text-main: #f8fafc; --accent: #38bdf8; }}
            body {{ background: radial-gradient(circle at top, #0f172a 0%, #020617 100%); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding: 20px; padding-bottom: 60px; min-height: 100vh; }}
            ::-webkit-scrollbar {{ width: 5px; }}
            ::-webkit-scrollbar-track {{ background: transparent; }}
            ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.1); border-radius: 10px; }}
            .neon-bar {{ background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5); }}
            .neon-bar h3 {{ margin: 0; font-size: 10px; color: #94a3b8; letter-spacing: 2px; text-transform: uppercase; font-weight: 600; }}
            .neon-bar h1 {{ margin: 8px 0 0 0; font-size: 32px; font-weight: 900; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .container-cols {{ display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; align-items: flex-start; }}
            .coluna-categoria {{ flex: 1; min-width: 220px; max-width: 280px; display: flex; flex-direction: column; }}
            .accordion-header {{ padding: 12px 15px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; border: 1px solid; backdrop-filter: blur(8px); position: relative; z-index: 10; transition: transform 0.3s ease; }}
            .accordion-header:hover {{ transform: translateY(-2px); }}
            .cat-check {{ width: 14px; height: 14px; cursor: pointer; margin-right: 10px; accent-color: var(--accent); }}
            .cat-title {{ font-size: 10px; font-weight: 700; color: white; letter-spacing: 0.5px; }}
            .cat-total {{ font-size: 11px; font-weight: 700; color: white; background: rgba(0,0,0,0.3); padding: 3px 8px; border-radius: 4px; }}
            .accordion-content {{ max-height: 0px; overflow-y: auto; transition: max-height 0.5s cubic-bezier(0.4, 0, 0.2, 1); background-color: rgba(2, 6, 23, 0.6); border-radius: 0 0 8px 8px; margin-top: -4px; backdrop-filter: blur(10px); }}
            .accordion-content.show {{ max-height: 400px; border: 1px solid rgba(255,255,255,0.05); border-top: none; }}
            .content-inner {{ padding: 12px 8px; display: flex; flex-direction: column; gap: 6px; }}
            .cyber-card {{ background: rgba(255,255,255,0.02); padding: 10px; border-radius: 6px; border-left: 2px solid rgba(255,255,255,0.2); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.02); transition: all 0.2s; }}
            .cyber-card:hover {{ background: rgba(255,255,255,0.05); border-left-color: var(--accent); transform: translateX(2px); }}
            .card-title {{ font-size: 10px; color: #e2e8f0; max-width: 65%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .card-value {{ font-size: 11px; font-weight: 700; color: #ffffff; }}
            .assinatura-html {{ position: fixed; bottom: 15px; left: 15px; background: rgba(2, 6, 23, 0.8); color: #64748b; padding: 8px 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); z-index: 9999; backdrop-filter: blur(12px); box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: left; letter-spacing: 0.5px; }}
            .assinatura-html span {{ color: #e0e7ff; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="neon-bar">
            <h3>Caixa Total Selecionado</h3>
            <h1 id="display-total">R$ {total_geral:,.2f}</h1>
            <p style="color:#64748b; font-size:9px; margin-top:6px; margin-bottom:0px;">Período Auditado: {periodo}</p>
            <p style="color:#475569; font-size:8px; margin-top:2px;">Arquivo Origem: {nome_arquivo}</p>
        </div>
        <div class="container-cols">{colunas_html}</div>
        <div class="assinatura-html">
            <span style="font-size: 10px; text-transform: uppercase;">Desenvolvido por <span>@madson_da_hora</span></span><br>
            <span style="font-size: 8px; color: #94a3b8; font-weight: normal; text-transform: none;">Analista de dados & Programador</span>
        </div>
        <script>
            function toggleAccordion(id) {{ document.getElementById(id).classList.toggle("show"); }}
            function recalcular() {{
                let total = 0;
                document.querySelectorAll('.cat-check').forEach(check => {{ if (check.checked) total += parseFloat(check.getAttribute('data-valor')); }});
                document.getElementById('display-total').innerText = "R$ " + total.toLocaleString('pt-BR', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
            }}
        </script>
    </body>
    </html>"""

# ==========================================
# 4. MOTORES LÓGICOS (CÁLCULO DINÂMICO DE COLUNAS)
# ==========================================

def limpar_nome_produto(nome_bruto):
    nome = re.sub(r'\b\d{5,8}\b', '', nome_bruto) 
    nome = re.sub(r'\d{1,2}-[a-zA-Z]{3}(-\d{2,4})?', '', nome) 
    return nome.replace('.', '').replace('-', '').strip()[:25]

def limpar_linha_estoque(linha):
    ignorar = ["MERCADINHO", "ENDEREÇO", "PAGINA", "ESTOQUE", "GESTÃO", "SMB STORE", "CNPJ", "TELEFONE", "CÓDIGO"]
    if any(p in linha.upper() for p in ignorar): return ""
    n = re.sub(r'\b\d{13,14}\b', '', linha)
    n = re.sub(r'^\s*\d{1,7}\s+', '', n)
    n = re.sub(r'[.\-/"\']', '', n)
    return n.strip().upper()

@st.cache_data(ttl=10)
def carregar_regras_banco():
    try:
        res = supabase.table("excecoes_categorias").select("*").execute()
        regras = []
        stopwords = {"BISC", "BISCOITO", "BOMBOM", "PCT", "UND", "UN", "KG", "DE", "SABOR", "COM", "CHOCO", "CHOCOLATE", "MORANGO", "LATA", "GARRAFA", "PET", "ML", "GR", "G", "CAIXA", "CX", "AO", "LEITE"}
        for r in res.data:
            nome = r['nome_produto']
            cat = r['categoria_destino']
            palavras = {w for w in nome.split() if len(w) > 2 and w not in stopwords}
            regras.append((nome, palavras, cat))
        return regras
    except: return []

def palpite_categoria(nome_bruto, regras_carregadas):
    txt = ''.join(c for c in unicodedata.normalize('NFD', nome_bruto) if unicodedata.category(c) != 'Mn').upper()
    
    stopwords = {"BISC", "BISCOITO", "BOMBOM", "PCT", "UND", "UN", "KG", "DE", "SABOR", "COM", "CHOCO", "CHOCOLATE", "MORANGO", "LATA", "GARRAFA", "PET", "ML", "GR", "G", "CAIXA", "CX", "AO", "LEITE"}
    palavras_txt = {w for w in txt.split() if len(w) > 2 and w not in stopwords}
    
    for regra_nome, palavras_regra, cat_destino in regras_carregadas:
        if regra_nome in txt or txt in regra_nome: 
            return cat_destino, False
        if palavras_txt and palavras_regra:
            intersecao = palavras_txt.intersection(palavras_regra)
            if len(intersecao) >= 2 or (len(palavras_regra) == 1 and len(intersecao) == 1):
                return cat_destino, False

    excecoes_choque = [
        "BATATA DOCE", "ITALAKINHO", "DOCE DE LEITE", "ERVADOCE", "ERVA DOCE", "MARAGOGI DOCE", 
        "SHAMPOO", "CONDICIONADOR", "CREME SEDA", "KIT SEDA", "CENOURA", "CANETA BIC",
        "ABSORVENTE", "INFINITY", "EMBALAGEM", "BALANCA", "BALANÇA", "FERMENTO", "ALIMENTO", 
        "CONDIMENTO", "PIMENTO", "PEQUENO", "MENOS", "MORENO", "VENENO", "FENO", "PLENO", 
        "SERENO", "TERRENO", "CAMPINEIRO", "DEFINITIVO", "AFINIDADE", "SEDAN", "CIDADAO",
        "CIDADÃO", "GELATINA", "MACRO", "MICRO", "SAL GROSSO", "SALGROSSO", "MILHO DE PIPOCA",
        "CHOCOLATE EM PO", "CHOCOLATE EM PÓ", "COBERTURA"
    ]
    if any(k in txt for k in excecoes_choque): return "Mercearia", False
        
    if any(k in txt for k in ["CT ", "CIGARRO", "PINE", "TREVO", "ROTHMANS", "LUCKY", "FUMO", "SEDA", "GUNDANG", "GUDANG", "EIGHT", "VILA RICA", "ISQUEIRO", "BIC ", "FOSFORO", "MAXIMILIAM", "NISE", "CARTEIRA", "SMOKING", "LANDUS", "ENGLISHMAN", "MARSHAL"]): return "Tabacaria", False
    if any(k in txt for k in ["CERV", "HEINEKEN", "VINHO", "PITU", "SKOL", "BRAHMA", "51 ", "VODKA", "LOKAL", "BUDWEISER", "ITAIPAVA", "YPIOCA", "IMPERIO", "BEATS", "SPATEN", "CABARE", "CONHAQUE", "DREHER", "DEVASSA", "CACHACA", "CARANGUEJO", "CARANGUEIJO", "BLACK PRINCESS", "PETRA", "GIN "]): return "Bebidas Alcoólicas", False
    if any(k in txt for k in ["SORV", "PICOLE", "CREMOSIN", "DADA", "PIC ", "PIC STER", "SUNDAE", "KONE", "SKIMO", "GELAT", "STERBINHO", "ACAI"]): return "Sorvetes", False
    if any(k in txt for k in ["TRIDENT", "DOCE", "BOMBOM", "FINI", "HALLS", "CHICLETE", "CHOCOLATE", "JUJUBA", "PACOCA", "MOLEQUE", "BALA", "ICEKISS", "MENTOS", "CHICLE", "EMBARE", "FREEGELLS", "GOMETS", "BATOM", "SERENATA", "KITKAT", "CHOKREM", "OLHINHO", "PIRULITO", "PESCOCO DE GIRAFA", "DOCINHO", "PIPOCA", "PIPPOS", "TRELOSO", "KRO", "SALGADINHO", "SALG", "WAFER", "WAFFER", "TORRESMINHO", "BOKUS", "BIG-BIG", "BIG BIG", "CLISS", "HAPPY BOL"]): return "Bomboniere", False
    if any(k in txt for k in ["DIPIRONA", "DORFLEX", "AMOXICILINA", "TORSILAX", "ENO", "PARACETAMOL", "CIMEGRIPE", "NEOSALDINA", "NIMESULIDA", "NEOLEFRIN", "DICLOFENACO"]): return "Remédios", False

    mercearia_explicita = [
        "RACAO", "PAO", "PAES", "COENTRO", "QUEIJO", "LACTEA", "FEIJOADA", "SABAO", "MARGARINA", "MARG ",
        "MACARRAO", "MAC ", "FARINHA", "PIMENTAO", "LEITE", "OLEO", "CAFE", "OVO", "AMENDOIM", "BATATA", "BATATINHA",
        "BOLACHA", "REQUEIJAO", "LINGUICA", "LING ", "MISTURA", "CARNE", "ALHO", "SAZON", "LAMEN", "MIOJO",
        "NISSIM", "PAPEL", "SARDINHA", "DESINF", "SALSICHA", "BISCOITO", "IOGURTE", "ESCOVA", "LAMINA",
        "CREME", "EMPANADO", "CEBOLA", "GOMA", "FRANGO", "COXA", "HAMBURGUER", "MILHO",
        "AGUA SANIT", "SAL ", "BOTIJAO", "MOLHO", "MACAXEIRA", "BISTECA", "BRILHOTEX",
        "LIMPOL", "SABONETE", "REXONA", "AMACIANTE", "CALDO", "FLOCAO", "FLOKAO", "MAIZENA",
        "ESPONJA", "ESP ", "ACUCAR", "COLORAL", "FIGADO", "DANONE", "PEITO",
        "DUMEL", "NATVILLE", "TOMATE", "LIMAO", "ROSQUINHA", "AGUA OXIGENADA", "HASTES", "COTTON",
        "AGUA SCHIN", "KAPO", "REFRESCO", "AGUA MINERAL", "COCA", "AGUA DE COCO", "REFRIGERANTE", "DORE", "CC ORIG", "GUARANA",
        "FANTA", "SPRITE", "PEPSI", "ENERGETICO", "MONSTER", "RED BULL", "TANG", "FRISCO", "MID", "SUKITA", "KUAT", "FYS",
        "ACHOC", "NESCAU", "ARROZ", "AVEIA", "AZEITONA", "BANANA", "CATCHUP", "KETCHUP", "CHARQUE", "DOWNY", "YPÊ", "MINUANO",
        "ABSOLUTO", "ALICE", "SONHO", "JOHNSONS", "EVEN", "PROTEX", "ALBANY", "SIENE", "COLGATE", "SORRISO", "ORAL B", "SKALA",
        "PRESTOBARBA", "GILLETTE", "PROBAK", "HERBISSIMO", "COTONETE", "ALGODAO", "GAS ", "CARVAO", "GELO", "PILHA", "RAIOVAC",
        "VASSOURA", "VELA", "MUCILON", "CREMOGEMA", "CHIMICHURRI", "COMINHO", "OREGANO", "LOURO", "PIMENTA",
        "BISC ", "PANETONE", "TORRADA", "SASSAMI", "FILE", "MOELA", "CORACAO", "BACON", "PRESUNTO", "FIAMBRE",
        "BOLDO", "TEMPERO", "DETERGENTE", "DETERG ", 
        "POLPA", "FEIJAO", "DUETO", "TAMPICO", "OSSINHO", "PINCA", "PINÇAS", "COCOROTE", "LARANJA", "ACAFRAO", 
        "DEL VALLE", "ULTRA COLA", "MORTADELA", "ASA ", "TODYNHO", "TODDY", "CAMOMILA", "FRALDA", "FERMENTO", "RAPADURA", "GALINHA",
        "SEMPRE LIVRE", "CALABRESA", "VINAGRE", "SKINKA", "REMOVEDOR", "ESMALTE", "H2O", "MARACUJA", "ABACATE", "SODA", "COCO", "SUPER SIGMA", "CREAM CRACKER",
        "ENERGY", "MAGNETO", "ALCOOL", "BEB FRUIT", "BEB FRUT", "BICARBONATO", "BORRACHA", "ADIFLOR", "POWERADE", "ROLLON", "AVON", "MUSK", "SUKINHO", "VALE PRESENTE", "WHISKAS", "ITI "
    ]
    if any(k in txt for k in mercearia_explicita): return "Mercearia", False
    return "Mercearia", True

def processar_pdf(file):
    dados = []
    regras = carregar_regras_banco()
    file.seek(0)
    with pdfplumber.open(file) as pdf:
        txt_topo = (pdf.pages[0].extract_text() or "").upper()
        match_d = re.search(r'(\d{2}/\d{2}/\d{4})\s*[AÀaà]\s*(\d{2}/\d{2}/\d{4})', txt_topo)
        periodo = f"{match_d.group(1)} a {match_d.group(2)}" if match_d else "DATA DESCONHECIDA"
        
        # ---------------------------------------------------------
        # A MÁGICA ESTÁ AQUI: IDENTIFICAÇÃO DINÂMICA DA COLUNA!
        # Se o relatório tiver a coluna "LUCRO", o V.Bruto recua 4 casas.
        # Se NÃO tiver a coluna "LUCRO", o V.Bruto recua apenas 3 casas.
        # ---------------------------------------------------------
        if "LUCRO" in txt_topo:
            idx_bruto = -4
        else:
            idx_bruto = -3
        
        for page in pdf.pages:
            texto_limpo = (page.extract_text() or "").replace('"', '').replace('\r', '')
            linhas = texto_limpo.split('\n')
            for linha in linhas:
                if "TOTAL" in linha.upper() or "PÁGINA" in linha.upper(): continue
                try:
                    # Usando regex blindado para não quebrar em números altos como 1.250,00
                    valores = re.findall(r'(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}', linha)
                    if len(valores) >= 4:
                        ean_m = re.search(r'\b\d{7,14}\b', linha)
                        if not ean_m: continue
                        
                        str_sem_ean = linha.replace(ean_m.group(), "").strip()
                        partes = re.split(r'\s*\b\d+,\d{2}\b', str_sem_ean)
                        n_bruto = partes[0].strip()
                        n_bruto = re.sub(r'\s+(UN|KG|CX|PCT|L|ML|G|KIT|M|DZ|BD|FD)\b$', '', n_bruto, flags=re.IGNORECASE).strip()
                        
                        nome_limpo = limpar_nome_produto(n_bruto)
                        
                        # Extração perfeita removendo ponto de milhar antes da conta
                        v_bruto_str = valores[idx_bruto].replace('.', '').replace(',', '.')
                        val = float(v_bruto_str)
                        
                        cat, is_fallback = palpite_categoria(nome_limpo, regras)
                        dados.append({"Nome": nome_limpo, "Cat": cat, "Valor": val, "Fallback": is_fallback})
                except Exception as e: continue
    return dados, periodo

def consumir_cota(username):
    if username not in ["madson", "admin"]:
        res = supabase.table("usuarios").select("limite_pdf").eq("username", username).execute()
        if res.data:
            novo_limite = int(res.data[0]['limite_pdf']) - 1
            supabase.table("usuarios").update({"limite_pdf": novo_limite}).eq("username", username).execute()

# ==========================================
# 5. AUTENTICAÇÃO E ROTEAMENTO DE INTERFACE (INTOCADO)
# ==========================================
try:
    res_user = supabase.table("usuarios").select("*").execute()
    db_users = {u['username']: {"name": u['name'], "password": u['password']} for u in res_user.data}
    dados_logados = {u['username']: u for u in res_user.data}
except:
    db_users = {"admin": {"name": "Admin", "password": "123"}}
    dados_logados = {}

config_auth = {"usernames": db_users}
authenticator = stauth.Authenticate(config_auth, "canada_bi_v60", "auth_key_v60", expiry_days=30)

if not st.session_state.get("authentication_status"):
    st.markdown("""
        <style>
        .block-container { max-width: 400px !important; padding-top: 10vh !important; }
        </style>
        """, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🇨🇦 Canadá BI</h1>", unsafe_allow_html=True)
    authenticator.login(location='main')

elif st.session_state.get("authentication_status") is False:
    st.error("Credenciais inválidas. Verifique o seu login e senha.")

else:
    user_logado = st.session_state['username']
    info_usr = dados_logados.get(user_logado, {})
    is_admin = user_logado in ["madson", "admin"]
    
    if 'arquivo_carregado' not in st.session_state: st.session_state.arquivo_carregado = None
    if 'cat_expandida' not in st.session_state: st.session_state.cat_expandida = None

    st.sidebar.markdown(f"<h3 style='color:#ffffff; font-size:clamp(12px, 1.2vw, 15px); font-weight:700; margin-bottom: 12px;'>Olá, {st.session_state['name']}</h3>", unsafe_allow_html=True)
    
    css_bloqueio = ""
    if not is_admin:
        css_bloqueio += """
        div[role="radiogroup"] > label:nth-child(4) { opacity: 0.3 !important; filter: grayscale(100%) !important; cursor: not-allowed !important; pointer-events: auto !important; }
        div[role="radiogroup"] > label:nth-child(4):hover::after { content: "Acesso Exclusivo do Administrador."; position: absolute; top: 100%; left: 0%; width: 100%; background: #e11d48; color: white; padding: 5px 0; border-radius: 6px; font-size: 10px; text-align: center; z-index: 99999; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        """
        if not info_usr.get("acesso_lote"):
            css_bloqueio += """
            div[role="radiogroup"] > label:nth-child(2) { opacity: 0.3 !important; filter: grayscale(100%) !important; cursor: not-allowed !important; pointer-events: auto !important; }
            div[role="radiogroup"] > label:nth-child(2):hover::after { content: "Assinatura não contempla lotes."; position: absolute; top: 100%; left: 0%; width: 100%; background: #e11d48; color: white; padding: 5px 0; border-radius: 6px; font-size: 10px; text-align: center; z-index: 99999; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            """
        if not info_usr.get("acesso_excecoes"):
            css_bloqueio += """
            div[role="radiogroup"] > label:nth-child(3) { opacity: 0.3 !important; filter: grayscale(100%) !important; cursor: not-allowed !important; pointer-events: auto !important; }
            div[role="radiogroup"] > label:nth-child(3):hover::after { content: "Acesso Restrito. Contate Administrador."; position: absolute; top: 100%; left: 0%; width: 100%; background: #e11d48; color: white; padding: 5px 0; border-radius: 6px; font-size: 10px; text-align: center; z-index: 99999; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            """
    st.markdown(f"<style>{css_bloqueio}</style>", unsafe_allow_html=True)

    opcoes_menu = ["Análise de Relatório", "Gerar Multiplos Relatorios", "Exceções e Permissões", "Central de Permissões"]
    pagina = st.sidebar.radio("Navegação", opcoes_menu, label_visibility="collapsed")
    st.sidebar.markdown("---")
    
    if not is_admin:
        cota_atual = info_usr.get("limite_pdf", 0)
        validade = info_usr.get("dias_trial", 0)
        st.sidebar.markdown(f"<div style='background:rgba(255,255,255,0.02); padding:8px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);'><p style='color:#94a3b8; font-size:9px; margin:0;'>Uploads Restantes: <b style='color:#38bdf8; font-size:11px;'>{cota_atual}</b></p><p style='color:#94a3b8; font-size:9px; margin:4px 0 0 0;'>Dias de Acesso: <b style='color:#38bdf8; font-size:11px;'>{validade}</b></p></div>", unsafe_allow_html=True)

    authenticator.logout("Encerrar Sessão", "sidebar")

    if pagina == "Análise de Relatório":
        cota_usuario = info_usr.get("limite_pdf", 0)
        if cota_usuario <= 0 and not is_admin:
            st.error("Sem Cotas de Upload. Contate o Administrador.")
        else:
            if st.session_state.arquivo_carregado is None:
                st.markdown("<h2 style='color:#ffffff; font-size:clamp(18px, 2vw, 26px); font-weight:800; margin-top:-10px; letter-spacing:-0.5px;'>Análise de Relatório</h2>", unsafe_allow_html=True)
                file = st.file_uploader("Selecionar Novo Relatório", type="pdf", key="single")
                if file:
                    st.session_state.arquivo_carregado = file
                    consumir_cota(user_logado)
                    st.rerun()
            else:
                file = st.session_state.arquivo_carregado
                with st.spinner("Motor de Inteligência processando o arquivo..."):
                    dados, per = processar_pdf(file)
                df = pd.DataFrame(dados)
                total_bruto = df['Valor'].sum() if not df.empty else 0

                col_topo1, col_topo2, col_topo3 = st.columns([4.5, 3.0, 2.5])
                with col_topo1:
                    st.markdown("<h2 style='color:#ffffff; font-size:clamp(18px, 2vw, 24px); font-weight:800; margin-top:-10px; margin-bottom:0px; letter-spacing:-0.5px;'>Análise de Relatório</h2>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#64748b; font-size:clamp(9px, 1vw, 11px); margin-top:2px; margin-bottom:0px; text-transform:uppercase; letter-spacing:1px;'>Período Auditado: <b style='color:#38bdf8;'>{per}</b></p>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:#475569; font-size:9px; margin-top:0px; margin-bottom:0px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>Arquivo origem: <i>{file.name}</i></p>", unsafe_allow_html=True)
                with col_topo2:
                    if not df.empty:
                        html_rel = gerar_html_interativo(df, per, total_bruto, file.name)
                        nome_arquivo_html = f"RELATORIO DE {per.replace('/', '-').replace(' a ', '_a_')}.html"
                        st.download_button(label="📥 Baixar Relatório HTML", data=html_rel, file_name=nome_arquivo_html, mime="text/html", use_container_width=True)
                with col_topo3:
                    if st.button("🔄 Novo Upload", use_container_width=True):
                        st.session_state.arquivo_carregado = None
                        st.session_state.cat_expandida = None
                        st.rerun()

                st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin-top:10px; margin-bottom:15px;'>", unsafe_allow_html=True)
                
                col_filtros, col_total, col_detalhes = st.columns([3.5, 3.5, 5], gap="large")
                selecionadas = []
                categorias_pdf = sorted(df['Cat'].unique()) if not df.empty else []
                
                with col_filtros:
                    st.markdown("<h4 style='color:#94a3b8; font-size:10px; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px;'>Categorias</h4>", unsafe_allow_html=True)
                    for cat in categorias_pdf:
                        v = df[df['Cat'] == cat]['Valor'].sum()
                        c_chk, c_btn, c_val = st.columns([1, 6, 4])
                        with c_chk:
                            if st.checkbox("", value=True, key=f"chk_{cat}"): selecionadas.append(cat)
                        with c_btn:
                            st.markdown('<div class="botao-categoria">', unsafe_allow_html=True)
                            if st.button(cat, key=f"btn_{cat}", use_container_width=True): st.session_state.cat_expandida = cat
                            st.markdown('</div>', unsafe_allow_html=True)
                        with c_val:
                            st.markdown(f"<div style='padding-top:2px; color:#ffffff; font-weight:700; font-size:clamp(11px, 1.1vw, 13px); text-align:right; white-space:nowrap;'>{formatar_moeda(v)}</div>", unsafe_allow_html=True)

                with col_total:
                    st.markdown("<h4 style='color:#94a3b8; font-size:10px; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px;'>Resumo Financeiro</h4>", unsafe_allow_html=True)
                    soma_f = df[df['Cat'].isin(selecionadas)]['Valor'].sum() if not df.empty else 0
                    st.markdown(f'''
                    <style>
                    .caixa-bruto {{ background: rgba(30, 58, 138, 0.15); backdrop-filter: blur(10px); padding: 20px 15px; border-radius: 12px; text-align: center; border: 1px solid rgba(59, 130, 246, 0.3); box-shadow: 0 8px 20px -10px rgba(37, 99, 235, 0.2); transition: all 0.3s ease; }}
                    .caixa-bruto:hover {{ transform: translateY(-2px); box-shadow: 0 12px 25px -10px rgba(37, 99, 235, 0.4); border-color: #38bdf8; }}
                    </style>
                    <div class="caixa-bruto">
                        <p style="margin:0; color:#94a3b8; font-size:10px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase;">Caixa Total Bruto</p>
                        <h1 style="margin:8px 0 0 0; font-size:clamp(22px, 2.5vw, 30px); font-weight:900; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; white-space:nowrap;">{formatar_moeda(soma_f)}</h1>
                    </div>
                    ''', unsafe_allow_html=True)

                with col_detalhes:
                    st.markdown("<h4 style='color:#94a3b8; font-size:10px; margin-bottom:10px; text-transform:uppercase; letter-spacing:1px;'>Detalhamento do Relatório</h4>", unsafe_allow_html=True)
                    if st.session_state.cat_expandida and not df.empty:
                        cat_atual = st.session_state.cat_expandida
                        itens = df[df['Cat'] == cat_atual]
                        st.markdown("<style>.detalhe-panel { background:rgba(15, 23, 42, 0.6); backdrop-filter: blur(8px); padding:15px; border-radius:12px; border:1px solid rgba(255,255,255,0.05); box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease; } .detalhe-panel:hover { box-shadow: 0 10px 20px rgba(0,0,0,0.2); border-left: 2px solid #38bdf8; }</style>", unsafe_allow_html=True)
                        html_itens = f"<div class='detalhe-panel'><h5 style='color:#e2e8f0; margin:0 0 12px 0; font-size:13px; font-weight:700; letter-spacing:0.5px;'>{cat_atual.upper()}</h5><div style='max-height: 400px; overflow-y: auto; padding-right:8px;'>"
                        for _, row in itens.iterrows():
                            html_itens += f"<div style='display:flex; justify-content:space-between; border-bottom:1px solid rgba(255,255,255,0.03); padding:8px 0; transition: background 0.2s;' onmouseover=\"this.style.background='rgba(255,255,255,0.02)'\" onmouseout=\"this.style.background='transparent'\"><span style='color:#cbd5e1; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:70%; font-weight:500;'>{row['Nome']}</span><span style='color:#ffffff; font-size:12px; font-weight:700; white-space:nowrap;'>R$ {row['Valor']:,.2f}</span></div>"
                        html_itens += "</div></div>"
                        st.markdown(html_itens, unsafe_allow_html=True)
                    else:
                        st.markdown("""<div style="background:rgba(15, 23, 42, 0.4); padding:20px; border-radius:12px; text-align:center; border: 1px dashed rgba(255,255,255,0.1);"><p style="color:#64748b; font-size:11px; font-weight:500; margin:0;">Selecione uma categoria ao lado para inspecionar os itens.</p></div>""", unsafe_allow_html=True)

                st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin-top:15px; margin-bottom:20px;'>", unsafe_allow_html=True)
                
                with st.expander("🔎 Auditoria do Motor (Itens sem Regra Específica)"):
                    if not df.empty:
                        df_fallback = df[df['Fallback'] == True]
                        if not df_fallback.empty:
                            st.markdown("<p style='color:#94a3b8; font-size:11px;'>Os itens abaixo foram alocados em <b>Mercearia</b> por não acionarem nenhuma palavra-chave oficial.</p>", unsafe_allow_html=True)
                            st.dataframe(df_fallback[['Nome', 'Valor']], use_container_width=True, hide_index=True)
                        else:
                            st.success("Excelente! O motor reconheceu 100% dos itens lidos.")

    elif pagina == "Gerar Multiplos Relatorios":
        if not is_admin and not info_usr.get("acesso_lote"): pass
        else:
            st.markdown("<h2 style='color:#ffffff; font-size:clamp(18px, 2vw, 26px); font-weight:800; letter-spacing:-0.5px; margin-top:-10px;'>Processamento em Lote</h2>", unsafe_allow_html=True)
            st.info("🟢 Módulo ativado. Em breve, a função de múltiplos processamentos simultâneos estará disponível.")

    elif pagina == "Exceções e Permissões":
        if not is_admin and not info_usr.get("acesso_excecoes"): pass
        else:
            st.markdown("<h2 style='color:#ffffff; font-size:clamp(18px, 2vw, 26px); font-weight:800; margin-bottom: 20px; letter-spacing:-0.5px; margin-top:-10px;'>Inteligência e Catálogo</h2>", unsafe_allow_html=True)
            tab_sync, tab_bulk = st.tabs(["📥 Sincronizar Estoque Oficial", "🔥 Atribuição em Massa"])

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
                    selecionados = st.multiselect("Pesquise e selecione os itens (Ex: TRELOSO):", options=lista_sugestoes)
                    nova_cat = st.selectbox("Mover para:", ["Tabacaria", "Bebidas Alcoólicas", "Bomboniere", "Sorvetes", "Mercearia", "Higiene"])
                    
                    btn_massa = st.form_submit_button("🔥 APLICAR REGRA EM TODOS")
                    if btn_massa and selecionados:
                        with st.spinner(f"Processando..."):
                            batch = [{"nome_produto": p, "categoria_destino": nova_cat} for p in selecionados]
                            supabase.table("excecoes_categorias").upsert(batch, on_conflict="nome_produto").execute()
                            st.cache_data.clear()
                            st.success(f"✅ Itens configurados com sucesso.")
                            st.rerun()

    elif pagina == "Central de Permissões":
        if not is_admin: pass
        else:
            st.markdown("<h2 style='color:#ffffff; font-size:clamp(18px, 2vw, 26px); font-weight:800; margin-bottom: 20px; letter-spacing:-0.5px; margin-top:-10px;'>Painel de Administrador</h2>", unsafe_allow_html=True)
            
            tab_novo, tab_gerenciar = st.tabs(["👤 Adicionar Cliente", "⚙️ Gerenciar e Configurar Acessos"])
            
            with tab_novo:
                st.markdown("<div style='background:rgba(15, 23, 42, 0.6); padding:15px; border-radius:12px; border:1px solid rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                with st.form("form_novo_usuario"):
                    n_user = st.text_input("Usuário de login (sem espaços, ex: mercadinho)")
                    n_nome = st.text_input("Nome de Exibição (ex: Mercadinho do Zé)")
                    n_senha = st.text_input("Senha", type="password")
                    if st.form_submit_button("Criar Acesso ao Sistema"):
                        try:
                            supabase.table("usuarios").insert({"username": n_user, "name": n_nome, "password": n_senha, "limite_pdf": 15, "dias_trial": 30, "acesso_lote": False, "acesso_excecoes": False}).execute()
                            st.success(f"Cliente '{n_nome}' cadastrado com sucesso!")
                            st.rerun()
                        except:
                            st.error("Erro: Verifique se o usuário já existe.")
                st.markdown("</div>", unsafe_allow_html=True)

            with tab_gerenciar:
                for u in res_user.data:
                    if u['username'] in ["madson", "admin"]: continue
                    with st.expander(f"👤 {u['name']} (@{u['username']})"):
                        st.markdown("<p style='color:#94a3b8; font-size:11px; text-transform:uppercase;'>Configurações de Assinatura</p>", unsafe_allow_html=True)
                        c1, c2, c3, c4 = st.columns(4)
                        with c1: limite = st.number_input("Limite PDFs", value=u.get('limite_pdf', 10), key=f"l_{u['username']}")
                        with c2: trial = st.number_input("Dias de Acesso", value=u.get('dias_trial', 7), key=f"t_{u['username']}")
                        with c3:
                            st.markdown("<br>", unsafe_allow_html=True)
                            lote = st.checkbox("Módulo Lote", value=u.get('acesso_lote', False), key=f"b_{u['username']}")
                        with c4:
                            st.markdown("<br>", unsafe_allow_html=True)
                            excecoes = st.checkbox("Módulo Inteligência", value=u.get('acesso_excecoes', False), key=f"e_{u['username']}")
                        
                        st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:10px 0;'>", unsafe_allow_html=True)
                        nova_senha = st.text_input("Nova senha (deixe em branco para manter)", type="password", key=f"pw_{u['username']}")

                        col_salvar, col_apagar = st.columns([1, 1])
                        with col_salvar:
                            if st.button("💾 Salvar Permissões", key=f"btn_{u['username']}", use_container_width=True):
                                update_data = {"limite_pdf": limite, "dias_trial": trial, "acesso_lote": lote, "acesso_excecoes": excecoes}
                                if nova_senha: update_data["password"] = nova_senha
                                supabase.table("usuarios").update(update_data).eq("username", u['username']).execute()
                                st.success("Atualizado!")
                        with col_apagar:
                            if st.button("🗑️ Deletar Cliente", key=f"del_{u['username']}", type="primary", use_container_width=True):
                                supabase.table("usuarios").delete().eq("username", u['username']).execute()
                                st.warning("Deletado!")
                                st.rerun()
