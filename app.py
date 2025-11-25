import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.formula.api as smf
import os

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA E CSS (CORREÇÃO DE CORES)
# ==============================================================================
st.set_page_config(
    page_title="Analytics Educacional: Painel & Econometria",
    page_icon="🎓",
    layout="wide"
)

# CORREÇÃO CSS:
# 1. Força cor preta (color: #000000) dentro dos blocos claros (.stMetric).
# 2. Ajusta o contraste para funcionar bem tanto no Light quanto no Dark mode.
st.markdown("""
    <style>
    /* Estilo para as métricas (st.metric) */
    div[data-testid="stMetric"] {
        background-color: #f0f2f6 !important;
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        padding: 10px;
        color: #000000 !important; /* Força texto preto */
    }
    
    /* Força a cor do título e valor da métrica para preto */
    div[data-testid="stMetricLabel"] p {
        color: #31333F !important; /* Cinza escuro */
    }
    div[data-testid="stMetricValue"] div {
        color: #000000 !important; /* Preto absoluto */
    }

    /* Estilo para mensagens de erro/sucesso personalizadas */
    .stAlert {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. MOTOR DE ETL (COM SUPORTE A CARREGAMENTO AUTOMÁTICO)
# ==============================================================================
@st.cache_data
def carregar_e_processar_dados(file_input):
    try:
        # Lógica para detectar se é arquivo (upload) ou caminho (string)
        if isinstance(file_input, str):
            filename = file_input
            # Se for string (caminho local), usa engine openpyxl para xlsx
            if filename.endswith('.csv'):
                df_raw = pd.read_csv(filename, header=None)
            else:
                df_raw = pd.read_excel(filename, header=None, engine='openpyxl')
        else:
            filename = file_input.name
            if filename.endswith('.csv'):
                df_raw = pd.read_csv(file_input, header=None)
            else:
                df_raw = pd.read_excel(file_input, header=None, engine='openpyxl')
            
        # --- 1.1 Identificação da Estrutura ---
        row_header_idx = None
        for i, row in df_raw.iterrows():
            row_str = row.astype(str).str.cat()
            if "NOME COMPLETO" in row_str or "Nome Planilha" in row_str:
                row_header_idx = i
                break
        
        if row_header_idx is None:
            return None, None, "Não foi possível identificar o cabeçalho (procurei por 'NOME COMPLETO')."

        # Definir DataFrames com cabeçalho correto
        df = df_raw.iloc[row_header_idx+1:].copy()
        df.columns = df_raw.iloc[row_header_idx]
        
        # Identificar colunas fixas
        cols_fixas = [c for c in df.columns if str(c) in ['Sala', 'Num', 'NOME COMPLETO', 'Nota Final', 'Situação Final']]
        df_cross = df[cols_fixas].copy()
        df_cross = df_cross.rename(columns={'NOME COMPLETO': 'Aluno', 'Nota Final': 'Y_Nota', 'Situação Final': 'Status'})
        
        # Limpeza da variável alvo (Y)
        df_cross['Y_Nota'] = pd.to_numeric(df_cross['Y_Nota'], errors='coerce')
        df_cross = df_cross.dropna(subset=['Y_Nota', 'Aluno'])
        
        # --- 1.2 Transformação para Formato Longo (Panel Data) ---
        panel_data = []
        
        # Mapeamentos
        map_presenca = {'P': 1.0, '1/2': 0.5, 'A': 0.0, 'F': 0.0}
        map_hw = {'√': 1.0, '+/-': 0.5, 'N': 0.0, 'X': 0.0}
        map_soft = {':-D': 1.0, ':-)': 1.0, ':-/': 0.5, ':-|': 0.5, ':-&': 0.0, ':-(': 0.0, 'nan': 0.0}

        col_names = list(df.columns)
        
        for i, col in enumerate(col_names):
            if str(col).strip() == 'P': 
                try:
                    nome_aula_raw = df_raw.iloc[row_header_idx-1, i] if row_header_idx > 0 else f"Aula_{i}"
                    if pd.isna(nome_aula_raw): nome_aula_raw = f"Periodo_{i}"
                    
                    sub_df = df.iloc[:, i-1:i+4].copy()
                    sub_df.columns = ['Pre_Class', 'Presenca', 'Homework', 'Participacao', 'Comportamento']
                    sub_df['Aluno'] = df['NOME COMPLETO']
                    sub_df['Tempo'] = str(nome_aula_raw).strip()
                    sub_df['Tempo_ID'] = i 
                    
                    panel_data.append(sub_df)
                except Exception:
                    continue

        if not panel_data:
            return None, None, "Não foi possível estruturar o Painel de Dados."

        df_panel = pd.concat(panel_data, ignore_index=True)
        
        # Aplicar Mapeamentos
        df_panel['X_Presenca'] = df_panel['Presenca'].map(map_presenca).fillna(0)
        df_panel['X_Homework'] = df_panel['Homework'].map(map_hw).fillna(0)
        df_panel['Participacao'] = df_panel['Participacao'].astype(str).str.strip()
        df_panel['X_Participacao'] = df_panel['Participacao'].map(map_soft).fillna(0)

        df_full = pd.merge(df_panel, df_cross[['Aluno', 'Y_Nota']], on='Aluno', how='inner')
        
        return df_cross, df_full, None

    except Exception as e:
        return None, None, f"Erro crítico no processamento: {str(e)}"

# ==============================================================================
# 2. LÓGICA DE CARREGAMENTO (AUTOMÁTICO OU MANUAL)
# ==============================================================================

# Define o nome do arquivo padrão no repositório
ARQUIVO_PADRAO = "Base anonimizada - Eric - PUC-SP.xlsx"

df_alunos = None
df_painel = None
erro_msg = None
carregou_automatico = False

# Tenta carregar automaticamente
if os.path.exists(ARQUIVO_PADRAO):
    with st.spinner(f"Carregando base de dados: {ARQUIVO_PADRAO}..."):
        df_alunos, df_painel, erro_msg = carregar_e_processar_dados(ARQUIVO_PADRAO)
        if df_alunos is not None:
            carregou_automatico = True
            st.success("✅ Dados carregados automaticamente do repositório.")

# ==============================================================================
# 3. INTERFACE PRINCIPAL
# ==============================================================================

st.title("📊 Painel de Controle Pedagógico")
st.markdown("Uma abordagem econométrica para gestão de sala de aula.")

# Se não carregou automático, mostra o uploader
if not carregou_automatico:
    if erro_msg: st.warning(f"Tentativa de carga automática falhou: {erro_msg}")
    uploaded_file = st.sidebar.file_uploader("Carregar Base Manualmente (.xlsx)", type=['xlsx', 'csv'])
    if uploaded_file:
        df_alunos, df_painel, erro_msg = carregar_e_processar_dados(uploaded_file)

# Se temos dados (seja auto ou manual), renderiza o app
if df_alunos is not None and df_painel is not None:
    
    # Sidebar filtros
    turmas = sorted(list(set(df_alunos.get('Sala', ['Única']))))
    filtro_turma = st.sidebar.multiselect("Filtrar Turma", turmas, default=turmas)
    
    # KPI Bar
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Alunos", len(df_alunos))
    col2.metric("Média Geral", f"{df_alunos['Y_Nota'].mean():.2f}")
    col3.metric("Taxa Presença", f"{df_painel['X_Presenca'].mean():.1%}")
    col4.metric("Entrega HW", f"{df_painel['X_Homework'].mean():.1%}")

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Visão Longitudinal", "🧮 Modelagem", "🔮 Simulador", "📋 Dados Brutos"])

    # --- TAB 1: VISÃO LONGITUDINAL ---
    with tab1:
        st.markdown("### A Evolução do Aluno no Tempo")
        trend_turma = df_painel.groupby('Tempo')[['X_Presenca', 'X_Homework', 'X_Participacao']].mean().reset_index()
        alunos_lista = sorted(df_painel['Aluno'].unique())
        aluno_foco = st.selectbox("Selecione um aluno:", alunos_lista)
        df_aluno = df_painel[df_painel['Aluno'] == aluno_foco]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend_turma['Tempo'], y=trend_turma['X_Participacao'], 
                                 name='Média Turma', line=dict(color='gray', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=df_aluno['Tempo'], y=df_aluno['X_Participacao'], 
                                 name=f'{aluno_foco}', line=dict(color='blue', width=4), mode='lines+markers'))
        
        fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 2: ECONOMETRIA ---
    with tab2:
        st.markdown("### Modelagem dos Determinantes")
        df_reg = df_painel.groupby('Aluno').agg({
            'X_Presenca': 'mean', 'X_Homework': 'mean', 'X_Participacao': 'mean', 'Y_Nota': 'first'
        }).reset_index()
        
        results = smf.ols('Y_Nota ~ X_Presenca + X_Homework + X_Participacao', data=df_reg).fit()
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.write("#### Resultados Estatísticos")
            coefs = pd.DataFrame({
                'Coeficiente': results.params,
                'P-Valor': results.pvalues
            })
            
            # Função de destaque sem matplotlib
            def destacar_significancia(val):
                if val < 0.05:
                    return 'background-color: #d4edda; color: #155724; font-weight: bold'
                return 'color: #6c757d'

            st.dataframe(coefs.style.format("{:.4f}").map(destacar_significancia, subset=['P-Valor']), use_container_width=True)
            st.metric("R² (Poder Explicativo)", f"{results.rsquared:.1%}")

        with col_res2:
            st.write("#### Interpretação")
            st.info(f"""
            - **Base:** Nota média esperada (Intercepto): {results.params['Intercept']:.2f}
            - **Impacto Participação:** {results.params.get('X_Participacao', 0):.2f} (para 100% partic.)
            - **Impacto Homework:** {results.params.get('X_Homework', 0):.2f} (para 100% entregas)
            """)

    # --- TAB 3: SIMULADOR ---
    with tab3:
        st.markdown("### 🔮 Simulador")
        c1, c2, c3 = st.columns(3)
        s_pres = c1.slider("Presença", 0.0, 1.0, 0.8)
        s_hw = c2.slider("Homework", 0.0, 1.0, 0.7)
        s_part = c3.slider("Participação", 0.0, 1.0, 0.5)
        
        prev = (results.params['Intercept'] + 
                results.params.get('X_Presenca', 0) * s_pres + 
                results.params.get('X_Homework', 0) * s_hw + 
                results.params.get('X_Participacao', 0) * s_part)
        
        st.metric("Nota Prevista", f"{prev:.2f}")

    with tab4:
        st.dataframe(df_painel)

else:
    if not erro_msg:
        st.info("👋 Bem-vindo! Se o carregamento automático falhou, use o menu lateral.")
