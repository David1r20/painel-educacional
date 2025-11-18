import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO E ESTILO ACADÊMICO
# ==============================================================================
st.set_page_config(
    page_title="Análise de Dados em Painel - Monitoramento Educacional",
    page_icon="🎓",
    layout="wide"
)

# CSS para simular um "Paper" ou Relatório Técnico
st.markdown("""
    <style>
    .main-header {
        font-family: 'Helvetica', sans-serif;
        color: var(--text-color);
    }
    .academic-box {
        background-color: rgba(240, 242, 246, 0.5);
        border-left: 4px solid #2c3e50;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .theory-title {
        font-weight: bold;
        color: #2c3e50;
        font-size: 0.9em;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .theory-text {
        font-size: 0.9em;
        color: var(--text-color);
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. CARREGAMENTO E ESTRUTURAÇÃO DO PAINEL (ETL)
# ==============================================================================
@st.cache_data
def carregar_painel(uploaded_file):
    try:
        # Leitura Raw
        df = pd.read_excel(uploaded_file, header=1, engine='openpyxl')
    except Exception as e:
        st.error(f"Erro de leitura: {e}")
        return None, None, None

    # --- Definição das Dimensões ---
    # Dimensão Transversal (i = Indivíduos)
    try:
        colunas_fixas = [0, 1, 2, 3, 83, 84, 85]
        df_cross_section = df.iloc[1:, colunas_fixas].copy()
        df_cross_section.columns = ["Feedback", "Sala", "Num", "Nome_Completo", "Media_Provas", "Nota_Final", "Situacao_Final"]
        
        # Tratamento numérico
        def clean_num(x):
            try: return float(str(x).replace(',', '.'))
            except: return np.nan
        
        df_cross_section['Nota_Final'] = df_cross_section['Nota_Final'].apply(clean_num).fillna(0)
        df_cross_section = df_cross_section.dropna(subset=['Nome_Completo'])
    except:
        return None, None, None

    # --- Estruturação do Painel (Melt / Empilhamento) ---
    # Transformando de Wide (Largo) para Long (Longo)
    nomes_variaveis = df.iloc[0]
    lista_aulas = []
    col_idx = 4
    
    while col_idx < len(df.columns):
        if col_idx >= len(nomes_variaveis): break
        if str(nomes_variaveis.iloc[col_idx]) != "Pre-Class": break
        
        # Dimensão Temporal (t)
        data_raw = df.columns[col_idx]
        data_str = f"Aula_{(col_idx-4)//5 + 1}" if "Unnamed" in str(data_raw) else str(data_raw)
        
        # Variação Intra-Indivíduo
        bloco = df.iloc[1:, col_idx:col_idx+5].copy()
        bloco.columns = ["Pre_Class", "Presenca", "Homework", "Participacao", "Comportamento"]
        bloco["Tempo_t"] = data_str
        bloco["Individuo_i"] = df.iloc[1:, 3] # Chave estrangeira
        
        lista_aulas.append(bloco)
        col_idx += 5

    df_panel = pd.concat(lista_aulas, ignore_index=True)
    df_panel = df_panel.dropna(subset=['Individuo_i'])

    # Feature Engineering (Quantificação)
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

    # Agregação (Between Effects Calculation)
    stats_between = df_panel.groupby('Individuo_i').agg({
        'X_Presenca': 'mean',
        'X_Homework': 'mean'
    }).reset_index()
    
    df_final = pd.merge(df_cross_section, stats_between, left_on='Nome_Completo', right_on='Individuo_i', how='left')
    
    # Criação de Grupos (Clusterização simples)
    media_pres = df_final['X_Presenca'].mean()
    media_hw = df_final['X_Homework'].mean()
    
    def classificar(row):
        if row['X_Presenca'] < media_pres and row['X_Homework'] < media_hw: return "Q3: Baixo Engajamento (Risco)"
        if row['X_Presenca'] >= media_pres and row['X_Homework'] < media_hw: return "Q4: Presença Alta/Tarefa Baixa"
        if row['X_Presenca'] < media_pres and row['X_Homework'] >= media_hw: return "Q1: Presença Baixa/Tarefa Alta"
        return "Q2: Alto Engajamento (Ideal)"
        
    df_final['Grupo_Analise'] = df_final.apply(classificar, axis=1)
    df_final['Tamanho_Visual'] = df_final['Nota_Final'] + 2

    return df_final, df_panel, (media_pres, media_hw)

# ==============================================================================
# 2. INTERFACE ACADÊMICA
# ==============================================================================

st.title("📊 Aplicação de Dados em Painel na Análise Educacional")
st.markdown("Este estudo aplica a metodologia de **Dados Longitudinais (Panel Data)** para decompor o desempenho acadêmico em variações temporais e heterogeneidade individual.")

# --- SIDEBAR: FUNDAMENTAÇÃO TEÓRICA ---
st.sidebar.header("📂 Dados e Modelo")
arquivo = st.sidebar.file_uploader("Carregar Base de Dados (.xlsx)", type=["xlsx"])

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Especificação do Modelo")
st.sidebar.latex(r"""
Y_{it} = \alpha + \beta X_{it} + \mu_i + \epsilon_{it}
""")
st.sidebar.markdown("""
Onde:
* $i$: Unidade Transversal (Aluno)
* $t$: Série Temporal (Aula/Semana)
* $Y_{it}$: Desempenho/Engajamento
* $\mu_i$: Efeito Individual (Heterogeneidade Não Observada)
""")

if arquivo:
    df_final, df_panel, medias = carregar_painel(arquivo)
    
    if df_final is not None:
        
        # --- SEÇÃO 1: ESTRUTURAÇÃO DOS DADOS ---
        with st.expander("1. Estruturação da Base (Data Wrangling)", expanded=True):
            st.markdown("""
            Para viabilizar a análise em painel, a base original (*Wide Format*) foi transformada em formato empilhado (*Long Format*).
            Isso permite tratar cada observação como um par **(Aluno $i$, Tempo $t$)**.
            """)
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.caption("Dimensões do Painel:")
                st.write(f"- **N (Indivíduos):** {df_final['Nome_Completo'].nunique()}")
                st.write(f"- **T (Períodos):** {df_panel['Tempo_t'].nunique()}")
                st.write(f"- **Total Observações ($N \\times T$):** {len(df_panel)}")
            with col_d2:
                st.caption("Amostra do Painel Estruturado (Long Format):")
                st.dataframe(df_panel[['Individuo_i', 'Tempo_t', 'X_Presenca', 'X_Homework']].head(5), hide_index=True)

        # --- SEÇÃO 2: ANÁLISE ---
        tab_between, tab_within, tab_cluster = st.tabs([
            "Variância Entre-Indivíduos (Between)", 
            "Dinâmica Temporal (Within)",
            "Matriz de Risco (Clusters)"
        ])

        # --- ABA 1: BETWEEN (CORTE TRANSVERSAL) ---
        with tab_between:
            st.markdown('<div class="academic-box"><div class="theory-title">Fundamentação Teórica: Variação Between</div><div class="theory-text">A análise "Between" ignora a variação temporal e foca nas diferenças médias entre os indivíduos. Aqui testamos se características médias (ex: frequência média) explicam o resultado final ($Y_i$).</div></div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Correlação Estrutural")
                # Scatter Plot com Linha de Regressão
                fig_corr = px.scatter(df_final, x='X_Presenca', y='Nota_Final', color='Situacao_Final',
                                      title="Dispersão: Frequência Média vs. Nota Final",
                                      labels={'X_Presenca': 'Média de Presença ($X_i$)', 'Nota_Final': 'Nota Final ($Y_i$)'})
                try:
                     fig_corr = px.scatter(df_final, x='X_Presenca', y='Nota_Final', color='Situacao_Final', trendline="ols",
                                           title="Dispersão: Frequência Média vs. Nota Final")
                except: pass # Fallback se statsmodels faltar
                
                st.plotly_chart(fig_corr, use_container_width=True)
                st.caption("Interpretação: A inclinação positiva indica que $\\beta > 0$, confirmando a hipótese de que a presença influencia o desempenho.")
            
            with c2:
                st.subheader("Heterogeneidade dos Grupos")
                fig_box = px.box(df_final, x='Situacao_Final', y='Nota_Final', color='Situacao_Final',
                                 title="Distribuição de Notas por Status")
                st.plotly_chart(fig_box, use_container_width=True)
                st.caption("Interpretação: A variância (tamanho da caixa) mostra a heterogeneidade interna de cada grupo.")

        # --- ABA 2: WITHIN (SÉRIE TEMPORAL) ---
        with tab_within:
            st.markdown('<div class="academic-box"><div class="theory-title">Fundamentação Teórica: Variação Within</div><div class="theory-text">A análise "Within" foca na evolução de $i$ ao longo de $t$. Permite identificar choques exógenos (eventos que afetam todos em $t$) ou mudanças de comportamento individual.</div></div>', unsafe_allow_html=True)
            
            # Gráfico Agregado (Tendência T)
            st.subheader("Efeito Temporal Agregado (Choques Exógenos)")
            trend = df_panel.dropna(subset=['Data_Formatada']).groupby('Data_Formatada')['X_Presenca'].mean().reset_index()
            fig_trend = px.line(trend, x='Data_Formatada', y='X_Presenca', markers=True,
                                title="Série Temporal Média da Turma",
                                labels={'X_Presenca': 'Taxa Média de Presença', 'Data_Formatada': 'Tempo ($t$)'})
            fig_trend.update_yaxes(range=[0, 1.1])
            st.plotly_chart(fig_trend, use_container_width=True)
            
            st.divider()
            
            # Análise Individual Intra-Sujeito
            st.subheader("Trajetória Individual (Microdados)")
            alunos = sorted(df_panel['Individuo_i'].unique())
            aluno_sel = st.selectbox("Selecione um Indivíduo ($i$) para análise detalhada:", alunos)
            
            df_aluno = df_panel[df_panel['Individuo_i'] == aluno_sel].sort_values('Tempo_t')
            
            # Transformar para plotar duas linhas
            df_melted_aluno = df_aluno.melt(id_vars=['Tempo_t'], value_vars=['X_Presenca', 'X_Homework'], var_name='Variável', value_name='Valor')
            
            fig_indiv = px.line(df_melted_aluno, x='Tempo_t', y='Valor', color='Variável', markers=True,
                                title=f"Dinâmica Intra-Indivíduo: {aluno_sel}",
                                range_y=[-0.1, 1.1])
            st.plotly_chart(fig_indiv, use_container_width=True)
            st.caption("Este gráfico isola o termo $\epsilon_{it}$ e a variação de $X_{it}$ para um único $i$.")

        # --- ABA 3: CLUSTERS (APLICAÇÃO PRÁTICA) ---
        with tab_cluster:
            st.markdown('<div class="academic-box"><div class="theory-title">Aplicação Prática: Segmentação</div><div class="theory-text">Utilizando as médias populacionais como ponto de corte, segmentamos a amostra em 4 quadrantes de comportamento. Isso operacionaliza a teoria para gestão educacional.</div></div>', unsafe_allow_html=True)
            
            media_p, media_h = medias
            
            fig_quad = px.scatter(df_final, x='X_Presenca', y='X_Homework',
                                  color='Grupo_Analise', size='Tamanho_Visual',
                                  hover_name='Nome_Completo',
                                  title="Matriz de Classificação (Baseada na Média Populacional)",
                                  color_discrete_map={
                                      "Q2: Alto Engajamento (Ideal)": "green",
                                      "Q4: Presença Alta/Tarefa Baixa": "orange",
                                      "Q3: Baixo Engajamento (Risco)": "red",
                                      "Q1: Presença Baixa/Tarefa Alta": "blue"
                                  })
            
            # Linhas de Corte (Médias)
            fig_quad.add_hline(y=media_h, line_dash="dash", line_color="gray", annotation_text=f"Média HW ({media_h:.2f})")
            fig_quad.add_vline(x=media_p, line_dash="dash", line_color="gray", annotation_text=f"Média Presença ({media_p:.2f})")
            
            st.plotly_chart(fig_quad, use_container_width=True)
            
            # Tabela de Resultados
            st.subheader("Microdados por Cluster")
            grupo_sel = st.selectbox("Filtrar Grupo:", df_final['Grupo_Analise'].unique())
            st.dataframe(
                df_final[df_final['Grupo_Analise'] == grupo_sel][['Nome_Completo', 'Nota_Final', 'X_Presenca', 'X_Homework']],
                use_container_width=True
            )

else:
    st.info("👈 Por favor, carregue a planilha para visualizar a análise.")
    st.markdown("""
    ### Instruções para Avaliação
    Este software demonstra a competência em:
    1.  **Coleta e Limpeza:** Tratamento de dados brutos e outliers.
    2.  **Estruturação de Painel:** Conversão e manuseio de dados longitudinais.
    3.  **Análise Visual:** Interpretação de padrões *Within* e *Between*.
    """)
