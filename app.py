import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.formula.api as smf
import os

# ==============================================================================
# CONFIGURAÇÃO VISUAL & CSS (CORREÇÃO DE CORES)
# ==============================================================================
st.set_page_config(
    page_title="Laboratório de Econometria Educacional",
    page_icon="🎓",
    layout="wide"
)

# CSS AVANÇADO: Garante contraste correto em Dark/Light Mode
st.markdown("""
    <style>
    /* CLASSE PARA CAIXAS DE TEXTO EXPLICATIVAS (Fundo claro, texto escuro OBRIGATÓRIO) */
    .academic-card {
        background-color: #f8f9fa;
        border-left: 5px solid #2c3e50;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        color: #1f1f1f !important; /* Texto preto forçado */
        font-family: 'Segoe UI', sans-serif;
    }
    
    .academic-title {
        font-weight: bold;
        font-size: 1.1em;
        color: #2c3e50 !important;
        margin-bottom: 5px;
        text-transform: uppercase;
    }
    
    .academic-text {
        font-size: 0.95em;
        line-height: 1.5;
        color: #333333 !important;
    }

    /* Ajuste das Métricas (st.metric) para não sumir texto */
    div[data-testid="stMetric"] {
        background-color: #eef1f6 !important;
        border: 1px solid #dcdcdc;
        color: #000000 !important;
    }
    div[data-testid="stMetricLabel"] p { color: #555555 !important; }
    div[data-testid="stMetricValue"] div { color: #000000 !important; }
    
    /* Tabelas */
    thead tr th:first-child { display:none }
    tbody th { display:none }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. MOTOR DE DADOS
# ==============================================================================
@st.cache_data
def carregar_dados(caminho_ou_arquivo):
    try:
        # Detecção inteligente da fonte (Caminho str ou Buffer uploaded)
        if isinstance(caminho_ou_arquivo, str):
            if caminho_ou_arquivo.endswith('.csv'):
                df_raw = pd.read_csv(caminho_ou_arquivo, header=None)
            else:
                df_raw = pd.read_excel(caminho_ou_arquivo, header=None, engine='openpyxl')
        else:
            if caminho_ou_arquivo.name.endswith('.csv'):
                df_raw = pd.read_csv(caminho_ou_arquivo, header=None)
            else:
                df_raw = pd.read_excel(caminho_ou_arquivo, header=None, engine='openpyxl')

        # 1. Localizar Cabeçalho
        row_header_idx = None
        for i, row in df_raw.iterrows():
            row_str = row.astype(str).str.cat()
            if "NOME COMPLETO" in row_str:
                row_header_idx = i
                break
        
        if row_header_idx is None: return None, None, "Cabeçalho 'NOME COMPLETO' não encontrado."

        # 2. Estruturar DataFrames
        df = df_raw.iloc[row_header_idx+1:].copy()
        df.columns = df_raw.iloc[row_header_idx]
        
        # Cross-Section (Dados Estáticos)
        cols_fixas = [c for c in df.columns if str(c) in ['Sala', 'NOME COMPLETO', 'Nota Final', 'Situação Final']]
        df_cross = df[cols_fixas].copy().rename(columns={
            'NOME COMPLETO': 'Aluno', 'Nota Final': 'Y_Nota', 'Situação Final': 'Status'
        })
        df_cross['Y_Nota'] = pd.to_numeric(df_cross['Y_Nota'], errors='coerce')
        df_cross = df_cross.dropna(subset=['Y_Nota', 'Aluno'])

        # Painel (Dados Dinâmicos)
        panel_data = []
        map_presenca = {'P': 1.0, '1/2': 0.5, 'A': 0.0, 'F': 0.0}
        map_hw = {'√': 1.0, '+/-': 0.5, 'N': 0.0}
        map_soft = {':-D': 1.0, ':-)': 1.0, ':-/': 0.5, ':-&': 0.0, ':-(': 0.0, 'nan': 0.0}

        for i, col in enumerate(df.columns):
            if str(col).strip() == 'P': # Âncora: Coluna Presença
                nome_aula = df_raw.iloc[row_header_idx-1, i] if row_header_idx > 0 else f"Aula_{i}"
                if pd.isna(nome_aula): nome_aula = f"Semana_{(i//5)+1}"
                
                sub = df.iloc[:, i-1:i+4].copy() # Pega bloco: Pre, P, Hw, CP, Bh
                sub.columns = ['Pre_Class', 'Presenca', 'Homework', 'Participacao', 'Comportamento']
                sub['Aluno'] = df['NOME COMPLETO']
                sub['Tempo'] = str(nome_aula).strip()
                panel_data.append(sub)

        df_panel = pd.concat(panel_data, ignore_index=True)
        df_panel['X_Presenca'] = df_panel['Presenca'].map(map_presenca).fillna(0)
        df_panel['X_Homework'] = df_panel['Homework'].map(map_hw).fillna(0)
        df_panel['X_Participacao'] = df_panel['Participacao'].astype(str).str.strip().map(map_soft).fillna(0)
        
        # Merge Final
        df_full = pd.merge(df_panel, df_cross[['Aluno', 'Y_Nota', 'Status']], on='Aluno', how='inner')
        
        return df_cross, df_full, None

    except Exception as e:
        return None, None, f"Erro: {str(e)}"

# ==============================================================================
# 2. CARREGAMENTO
# ==============================================================================
ARQUIVO_PADRAO = "Base anonimizada - Eric - PUC-SP.xlsx"
df_alunos, df_painel = None, None

if os.path.exists(ARQUIVO_PADRAO):
    df_alunos, df_painel, erro = carregar_dados(ARQUIVO_PADRAO)
    if erro: st.error(erro)
    else: st.sidebar.success("📂 Dados Locais Carregados")

if df_alunos is None:
    up = st.sidebar.file_uploader("Upload Planilha", type=['xlsx', 'csv'])
    if up: df_alunos, df_painel, erro = carregar_dados(up)

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
st.title("📊 Laboratório de Econometria: Determinantes do Sucesso")
st.markdown("---")

if df_alunos is not None:
    
    # --- HEADER KPI ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Amostra (N)", len(df_alunos))
    k2.metric("Média da Turma (Y)", f"{df_alunos['Y_Nota'].mean():.1f}")
    k3.metric("Taxa de Presença (X1)", f"{df_painel['X_Presenca'].mean():.0%}")
    k4.metric("Engajamento/Participação (X3)", f"{df_painel['X_Participacao'].mean():.0%}")

    # TABS
    tab_painel, tab_modelo, tab_simul = st.tabs([
        "📈 Dinâmica Longitudinal (Painel)", 
        "🧠 Modelo Econométrico (Análise)", 
        "🔮 Simulador de Notas"
    ])

    # ----------------------------------------------------------------------
    # TAB 1: PAINEL
    # ----------------------------------------------------------------------
    with tab_painel:
        st.markdown("""
        <div class="academic-card">
            <div class="academic-title">Conceito: A Heterogeneidade Individual</div>
            <div class="academic-text">
                Diferente de uma análise transversal simples (uma "foto" do final do semestre), 
                os <b>Dados em Painel</b> nos permitem ver o "filme" do aluno. 
                Abaixo, observe como a constância (Homework) e a intensidade (Participação) variam semana a semana.
                Alunos aprovados geralmente mantêm baixa variância no comportamento.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Gráfico
        trend = df_painel.groupby('Tempo')[['X_Participacao', 'X_Homework']].mean().reset_index()
        aluno_sel = st.selectbox("Raio-X do Aluno:", sorted(df_painel['Aluno'].unique()))
        dado_aluno = df_painel[df_painel['Aluno'] == aluno_sel]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend['Tempo'], y=trend['X_Participacao'], name='Média Turma', 
                                 line=dict(color='lightgray', dash='dash')))
        fig.add_trace(go.Scatter(x=dado_aluno['Tempo'], y=dado_aluno['X_Participacao'], name='Participação Aluno',
                                 line=dict(color='#2c3e50', width=3), mode='lines+markers'))
        fig.add_trace(go.Bar(x=dado_aluno['Tempo'], y=dado_aluno['X_Homework'], name='Entrega Homework',
                             marker_color='#18bc9c', opacity=0.3))
        
        fig.update_layout(title="Cronologia do Engajamento", yaxis_range=[0, 1.2])
        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------------------------------------
    # TAB 2: MODELO E CONCLUSÕES
    # ----------------------------------------------------------------------
    with tab_modelo:
        # Preparar dados (Between Effects)
        df_reg = df_painel.groupby('Aluno').agg({
            'Y_Nota': 'first', 'X_Presenca': 'mean', 
            'X_Homework': 'mean', 'X_Participacao': 'mean'
        }).reset_index()
        
        # Rodar OLS
        model = smf.ols("Y_Nota ~ X_Presenca + X_Homework + X_Participacao", df_reg).fit()
        r2 = model.rsquared
        params = model.params
        
        # Texto Dinâmico de Conclusão
        fator_mais_forte = params.drop('Intercept').idxmax()
        impacto_forte = params[fator_mais_forte]
        txt_fator = {
            'X_Presenca': 'a Presença em sala',
            'X_Homework': 'a entrega de Lição de Casa',
            'X_Participacao': 'a Participação ativa'
        }
        
        st.markdown(f"""
        <div class="academic-card">
            <div class="academic-title">🔎 Laudo Econométrico (Interpretação Automática)</div>
            <div class="academic-text">
                1. <b>Poder de Explicação (R²):</b> O modelo explica <b>{r2:.1%}</b> da variação das notas. 
                   Os outros {100-r2*100:.1f}% dependem de fatores não observados (inteligência inata, problemas pessoais, etc).<br><br>
                2. <b>Fator Crítico:</b> A variável que mais impacta a nota é <b>{txt_fator.get(fator_mais_forte, fator_mais_forte)}</b>. 
                   Manter esse índice em 100% adiciona isoladamente <b>{impacto_forte:.2f} pontos</b> na média final.<br><br>
                3. <b>Metodologia:</b> Como a Nota Final é estática, utilizamos o estimador <i>Between Effects</i>, 
                   comparando as médias de comportamento entre os alunos.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("Coeficientes Estimados")
            res_df = pd.DataFrame({
                'Impacto (Beta)': model.params,
                'P-Valor': model.pvalues
            })
            
            # Formatação Condicional Simples
            def style_sig(v):
                if v < 0.05: return 'color: green; font-weight: bold'
                return 'color: gray'
            
            st.dataframe(res_df.style.format("{:.4f}").map(style_sig, subset=['P-Valor']), use_container_width=True)
            st.caption("*P-Valor < 0.05 indica relevância estatística real.")
            
        with c2:
            st.subheader("Resíduos: Quem performou acima do esperado?")
            df_reg['Previsto'] = model.predict(df_reg)
            df_reg['Residuo'] = df_reg['Y_Nota'] - df_reg['Previsto']
            
            fig_res = px.scatter(df_reg, x='Previsto', y='Residuo', hover_name='Aluno',
                                 color='Residuo', color_continuous_scale='RdBu',
                                 labels={'Previsto': 'Nota Esperada pelo Modelo', 'Residuo': 'Desvio (Surpresa)'})
            fig_res.add_hline(y=0, line_dash="dash")
            st.plotly_chart(fig_res, use_container_width=True)

    # ----------------------------------------------------------------------
    # TAB 3: SIMULADOR
    # ----------------------------------------------------------------------
    with tab_simul:
        st.markdown("""
        <div class="academic-card">
            <div class="academic-title">Calculadora de Aprovação</div>
            <div class="academic-text">
                Use os sliders abaixo para simular o comportamento de um aluno hipotético. 
                O cálculo usa os coeficientes reais (Betas) obtidos na regressão da aba anterior.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col_s1, col_s2, col_s3 = st.columns(3)
        p_val = col_s1.slider("Presença (%)", 0, 100, 85) / 100
        h_val = col_s2.slider("Homework (%)", 0, 100, 70) / 100
        part_val = col_s3.slider("Participação (%)", 0, 100, 50) / 100
        
        nota_simulada = (params['Intercept'] + 
                         params.get('X_Presenca', 0)*p_val + 
                         params.get('X_Homework', 0)*h_val + 
                         params.get('X_Participacao', 0)*part_val)
        
        st.divider()
        c_res, c_graph = st.columns([1, 2])
        
        c_res.metric("Nota Projetada", f"{nota_simulada:.2f}", 
                     delta=f"{nota_simulada-6:.1f} vs Média 6.0")
        
        if nota_simulada >= 7:
            c_res.success("✅ PROVÁVEL APROVAÇÃO")
        elif nota_simulada >= 5:
            c_res.warning("⚠️ ZONA DE RISCO")
        else:
            c_res.error("❌ Risco Crítico de Reprovação")

else:
    st.info("Aguardando base de dados...")
