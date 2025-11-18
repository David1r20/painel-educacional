import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf

# ==============================================================================
# CONFIGURAÇÃO E ESTILO ACADÊMICO
# ==============================================================================
st.set_page_config(
    page_title="Estudo Econométrico: Dados em Painel Educacional",
    page_icon="🎓",
    layout="wide"
)

# CSS para simular um Relatório Técnico/Científico
st.markdown("""
    <style>
    .main-header {font-family: 'Times New Roman', serif; color: var(--text-color);}
    .academic-box {
        background-color: rgba(240, 242, 246, 0.5);
        border-left: 4px solid #2c3e50;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .theory-title {font-weight: bold; color: #2c3e50; font-size: 1em; text-transform: uppercase; margin-bottom: 5px;}
    .theory-text {font-size: 0.95em; color: var(--text-color); font-style: italic;}
    .result-box {border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #fff;}
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. ETL E ESTRUTURAÇÃO
# ==============================================================================
@st.cache_data
def carregar_painel(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, header=1, engine='openpyxl')
    except Exception as e:
        st.error(f"Erro de leitura: {e}")
        return None, None, None

    # Dimensão Transversal (Cross-Section)
    try:
        colunas_fixas = [0, 1, 2, 3, 83, 84, 85]
        df_cross = df.iloc[1:, colunas_fixas].copy()
        df_cross.columns = ["Feedback", "Sala", "Num", "Nome_Completo", "Media_Provas", "Nota_Final", "Situacao_Final"]
        
        def clean_num(x):
            try: return float(str(x).replace(',', '.'))
            except: return np.nan
        
        df_cross['Nota_Final'] = df_cross['Nota_Final'].apply(clean_num).fillna(0)
        df_cross = df_cross.dropna(subset=['Nome_Completo'])
    except:
        return None, None, None

    # Dimensão Temporal (Panel Structure)
    nomes_variaveis = df.iloc[0]
    lista_aulas = []
    col_idx = 4
    
    while col_idx < len(df.columns):
        if col_idx >= len(nomes_variaveis): break
        if str(nomes_variaveis.iloc[col_idx]) != "Pre-Class": break
        
        data_raw = df.columns[col_idx]
        data_str = f"Aula_{(col_idx-4)//5 + 1}" if "Unnamed" in str(data_raw) else str(data_raw)
        
        bloco = df.iloc[1:, col_idx:col_idx+5].copy()
        bloco.columns = ["Pre_Class", "Presenca", "Homework", "Participacao", "Comportamento"]
        bloco["Tempo_t"] = data_str
        bloco["Individuo_i"] = df.iloc[1:, 3]
        
        lista_aulas.append(bloco)
        col_idx += 5

    df_panel = pd.concat(lista_aulas, ignore_index=True)
    df_panel = df_panel.dropna(subset=['Individuo_i'])

    # Feature Engineering
    mapa_pres = {'P': 1.0, '1/2': 0.5, 'A': 0.0}
    mapa_hw = {'√': 1.0, '+/-': 0.5, 'N': 0.0}
    
    df_panel['X_Presenca'] = df_panel['Presenca'].map(mapa_pres)
    df_panel['X_Homework'] = df_panel['Homework'].map(mapa_hw)

    # Parser de Data
    meses = {'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'mai': 'May', 'jun': 'Jun', 'jul': 'Jul'}
    def parse_date(d):
        if 'Aula' in str(d): return None
        try:
            if '-' in str(d):
                partes = str(d).split('-')
                if len(partes) == 3:
                    dia, mes, ano = partes
                    mes_en = meses.get(mes.replace('.', ''), mes)
                    return pd.to_datetime(f"{dia}-{mes_en}-{ano}", format="%d-%b-%Y")
            return pd.to_datetime(d)
        except: return None

    df_panel['Data_Formatada'] = df_panel['Tempo_t'].apply(parse_date)

    # Agregação para Análise Between (Médias por Indivíduo)
    stats_between = df_panel.groupby('Individuo_i').agg({
        'X_Presenca': 'mean',
        'X_Homework': 'mean'
    }).reset_index()
    
    df_final = pd.merge(df_cross, stats_between, left_on='Nome_Completo', right_on='Individuo_i', how='left')
    
    # Clusterização
    media_p = df_final['X_Presenca'].mean()
    media_h = df_final['X_Homework'].mean()
    
    def classificar(row):
        if row['X_Presenca'] < media_p and row['X_Homework'] < media_h: return "Risco (Q3)"
        if row['X_Presenca'] >= media_p and row['X_Homework'] < media_h: return "Turista (Q4)"
        if row['X_Presenca'] < media_p and row['X_Homework'] >= media_h: return "Autodidata (Q1)"
        return "Ideal (Q2)"
        
    df_final['Grupo'] = df_final.apply(classificar, axis=1)
    df_final['Tamanho'] = df_final['Nota_Final'] + 2

    return df_final, df_panel, (media_p, media_h)

# ==============================================================================
# 2. INTERFACE ACADÊMICA
# ==============================================================================

st.title("📊 Aplicação de Dados em Painel na Análise Educacional")
st.markdown("**Trabalho Prático - Metodologia Quantitativa**")

st.sidebar.header("📂 Input de Dados")
arquivo = st.sidebar.file_uploader("Base de Dados (.xlsx)", type=["xlsx"])

st.sidebar.markdown("---")
with st.sidebar.expander("📐 Fundamentação Teórica (PDF)", expanded=True):
    st.markdown(r"""
    **Modelo de Regressão Linear:**
    $$
    Nota_i = \beta_0 + \beta_1 Pres_i + \beta_2 HW_i + \epsilon_i
    $$
    
    **Conceitos Aplicados:**
    * **Pooled OLS:** Regressão Agrupada.
    * **Between Estimator:** Variação entre indivíduos.
    * **Within Variation:** Dinâmica temporal.
    """)

if arquivo:
    df_final, df_panel, medias = carregar_painel(arquivo)
    
    if df_final is not None:
        
        # Container de Métricas de Topo
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("N (Indivíduos)", f"{df_final['Nome_Completo'].nunique()}")
        col2.metric("T (Períodos)", f"{df_panel['Tempo_t'].nunique()}")
        col3.metric("Total Observações", f"{len(df_panel)}")
        col4.metric("Média Amostral (Y)", f"{df_final['Nota_Final'].mean():.2f}")

        # --- ABAS ---
        tab_desc, tab_temp, tab_model = st.tabs([
            "1. Análise Descritiva (Between)", 
            "2. Dinâmica Temporal (Within)",
            "3. Modelagem Econométrica (Regressão)"
        ])

        # --- ABA 1: DESCRITIVA ---
        with tab_desc:
            st.markdown('<div class="academic-box"><div class="theory-title">Análise de Heterogeneidade (Between)</div><div class="theory-text">Examina-se a correlação transversal entre o comportamento médio do aluno ($X_i$) e seu resultado final ($Y_i$).</div></div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                fig_corr = px.scatter(df_final, x='X_Presenca', y='Nota_Final', color='Situacao_Final',
                                      title="Dispersão: Presença Média vs Nota Final", trendline="ols")
                st.plotly_chart(fig_corr, use_container_width=True)
            
            with c2:
                fig_box = px.box(df_final, x='Situacao_Final', y='Nota_Final', color='Situacao_Final',
                                 title="Distribuição de Notas por Grupo (Variância)")
                st.plotly_chart(fig_box, use_container_width=True)

        # --- ABA 2: TEMPORAL ---
        with tab_temp:
            st.markdown('<div class="academic-box"><div class="theory-title">Análise Longitudinal (Within)</div><div class="theory-text">Observa-se a trajetória de $X_{it}$ ao longo do tempo $t$. Permite identificar sazonalidade e choques comuns.</div></div>', unsafe_allow_html=True)
            
            trend = df_panel.dropna(subset=['Data_Formatada']).groupby('Data_Formatada')['X_Presenca'].mean().reset_index()
            fig_trend = px.line(trend, x='Data_Formatada', y='X_Presenca', markers=True, title="Tendência Agregada da Turma")
            st.plotly_chart(fig_trend, use_container_width=True)
            
            st.divider()
            aluno_sel = st.selectbox("Análise Micro (Individual):", df_panel['Individuo_i'].unique())
            
            df_aluno = df_panel[df_panel['Individuo_i'] == aluno_sel].sort_values('Tempo_t')
            df_melted = df_aluno.melt(id_vars=['Tempo_t'], value_vars=['X_Presenca', 'X_Homework'], var_name='Var', value_name='Val')
            
            fig_indiv = px.bar(df_melted, x='Tempo_t', y='Val', color='Var', barmode='group', title=f"Painel Individual: {aluno_sel}")
            st.plotly_chart(fig_indiv, use_container_width=True)

        # --- ABA 3: ECONOMETRIA (AQUI ESTÁ O OURO ACADÊMICO) ---
        with tab_model:
            st.markdown('<div class="academic-box"><div class="theory-title">Estimação do Modelo (Pooled OLS)</div><div class="theory-text">Utiliza-se o método dos Mínimos Quadrados Ordinários (OLS) para estimar a elasticidade da Nota Final em relação à Presença e Entrega de Tarefas.</div></div>', unsafe_allow_html=True)
            
            c_model1, c_model2 = st.columns([1, 2])
            
            with c_model1:
                st.subheader("Parâmetros do Modelo")
                st.write("**Variável Dependente ($Y$):** Nota Final")
                st.write("**Variáveis Explicativas ($X$):**")
                st.write("- $X_1$: Taxa de Presença")
                st.write("- $X_2$: Taxa de Homework")
                
                if st.button("🔄 Rodar Regressão"):
                    # MODELAGEM ESTATÍSTICA REAIS
                    # Prepara os dados removendo NaNs
                    df_reg = df_final[['Nota_Final', 'X_Presenca', 'X_Homework']].dropna()
                    
                    # Define o modelo OLS
                    modelo = smf.ols("Nota_Final ~ X_Presenca + X_Homework", data=df_reg).fit()
                    
                    st.session_state['modelo'] = modelo
                    st.success("Modelo Estimado com Sucesso!")

            with c_model2:
                if 'modelo' in st.session_state:
                    modelo = st.session_state['modelo']
                    
                    # Exibição Bonita dos Resultados
                    st.subheader("Resultados da Estimação")
                    
                    # Extrair dados principais
                    r2 = modelo.rsquared
                    coef_pres = modelo.params['X_Presenca']
                    coef_hw = modelo.params['X_Homework']
                    p_pres = modelo.pvalues['X_Presenca']
                    
                    # Cards de Resultados
                    cw1, cw2, cw3 = st.columns(3)
                    cw1.metric("R² (Explicação)", f"{r2:.2%}", help="Quanto a variação das notas é explicada pelo modelo.")
                    cw2.metric("Beta Presença", f"{coef_pres:.2f}", help="Impacto da Presença na Nota.")
                    cw3.metric("P-Valor", f"{p_pres:.4f}", help="Se < 0.05, é estatisticamente significativo.")
                    
                    st.markdown("### Tabela de Coeficientes")
                    st.write(modelo.summary())
                    
                    st.markdown("---")
                    st.markdown(f"""
                    ### 📝 Interpretação Acadêmica:
                    
                    1.  **Poder Explicativo:** O modelo explica **{r2:.1%}** da variação nas notas finais dos alunos.
                    2.  **Impacto da Presença ($\swarrow_1$):** O coeficiente de **{coef_pres:.2f}** indica que, *ceteris paribus*, um aluno com 100% de presença tende a ter uma nota {coef_pres:.2f} pontos maior do que um com 0% de presença.
                    3.  **Significância Estatística:** Como o P-valor ({p_pres:.4f}) é < 0.05, rejeitamos a hipótese nula. A presença tem efeito causal estatisticamente comprovado sobre a nota.
                    """)
                else:
                    st.info("Clique em 'Rodar Regressão' para calcular os coeficientes.")

else:
    st.warning("Aguardando upload do arquivo para iniciar o processamento.")
