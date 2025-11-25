import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
import re

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Analytics Educacional: Painel & Econometria",
    page_icon="🎓",
    layout="wide"
)

# Estilização CSS customizada
st.markdown("""
    <style>
    .big-font { font-size:18px !important; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. MOTOR DE ETL (EXTRAÇÃO E TRATAMENTO)
# ==============================================================================
@st.cache_data
def carregar_e_processar_dados(file):
    try:
        # Detecta se é CSV ou Excel
        if file.name.endswith('.csv'):
            df_raw = pd.read_csv(file, header=None) # Ler sem header para processar manualmente
        else:
            df_raw = pd.read_excel(file, header=None)
            
        # --- 1.1 Identificação da Estrutura ---
        # A linha 0 geralmente tem "Aula 1", "Aula 2"...
        # A linha 1 tem "Pre-Class", "P", "Hw"...
        
        # Encontrar onde começam os dados reais (pula metadados iniciais)
        # Vamos assumir que a linha com "NOME COMPLETO" ou "Num" define o cabeçalho real
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
        
        # Identificar colunas fixas (Metadados do Aluno)
        cols_fixas = [c for c in df.columns if str(c) in ['Sala', 'Num', 'NOME COMPLETO', 'Nota Final', 'Situação Final']]
        df_cross = df[cols_fixas].copy()
        df_cross = df_cross.rename(columns={'NOME COMPLETO': 'Aluno', 'Nota Final': 'Y_Nota', 'Situação Final': 'Status'})
        
        # Limpeza da variável alvo (Y)
        df_cross['Y_Nota'] = pd.to_numeric(df_cross['Y_Nota'], errors='coerce')
        df_cross = df_cross.dropna(subset=['Y_Nota', 'Aluno']) # Remove linhas vazias
        
        # --- 1.2 Transformação para Formato Longo (Panel Data) ---
        # A estratégia é iterar sobre as colunas que repetem padrões de aula
        panel_data = []
        
        # Mapeamento de valores qualitativos para quantitativos
        map_presenca = {'P': 1.0, '1/2': 0.5, 'A': 0.0, 'F': 0.0}
        map_hw = {'√': 1.0, '+/-': 0.5, 'N': 0.0, 'X': 0.0}
        # Comportamento/Participação: Simplificando emojis
        map_soft = {
            ':-D': 1.0, ':-)': 1.0, # Bom
            ':-/': 0.5, ':-|': 0.5, # Médio
            ':-&': 0.0, ':-(': 0.0, # Ruim
            'nan': 0.0
        }

        # Iterar sobre colunas para achar blocos de aulas
        # O padrão é: Pre-Class, P, Hw, CP, Bh
        col_names = list(df.columns)
        
        # Varredura inteligente: Procura onde tem "P" (Presença) e assume o bloco
        for i, col in enumerate(col_names):
            if str(col).strip() == 'P': 
                # Se achou 'P', assume que o bloco é [Pre-Class (i-1), P (i), Hw (i+1), CP (i+2), Bh (i+3)]
                try:
                    # Tenta pegar o nome da aula da linha superior do dataframe original (row_header_idx - 1)
                    # Se não der, cria um sequencial
                    nome_aula_raw = df_raw.iloc[row_header_idx-1, i] if row_header_idx > 0 else f"Aula_{i}"
                    if pd.isna(nome_aula_raw): nome_aula_raw = f"Periodo_{i}"
                    
                    sub_df = df.iloc[:, i-1:i+4].copy()
                    sub_df.columns = ['Pre_Class', 'Presenca', 'Homework', 'Participacao', 'Comportamento']
                    sub_df['Aluno'] = df['NOME COMPLETO']
                    sub_df['Tempo'] = str(nome_aula_raw).strip()
                    sub_df['Tempo_ID'] = i # Para ordenação
                    
                    panel_data.append(sub_df)
                except Exception as e:
                    continue # Fim das colunas ou erro de index

        if not panel_data:
            return None, None, "Não foi possível estruturar o Painel de Dados."

        df_panel = pd.concat(panel_data, ignore_index=True)
        
        # Aplicar Mapeamentos Numéricos
        df_panel['X_Presenca'] = df_panel['Presenca'].map(map_presenca).fillna(0)
        df_panel['X_Homework'] = df_panel['Homework'].map(map_hw).fillna(0)
        
        # Tratamento especial para Participação (Emojis)
        # Vamos converter tudo para string primeiro, remover espaços e mapear
        df_panel['Participacao'] = df_panel['Participacao'].astype(str).str.strip()
        df_panel['X_Participacao'] = df_panel['Participacao'].map(map_soft)
        # Fallback: Se não mapeou e não é nan, tenta heurística ou zera
        df_panel['X_Participacao'] = df_panel['X_Participacao'].fillna(0)

        # Merge do Y (Nota Final) no Painel (para referência)
        df_full = pd.merge(df_panel, df_cross[['Aluno', 'Y_Nota']], on='Aluno', how='inner')
        
        return df_cross, df_full, None

    except Exception as e:
        return None, None, f"Erro crítico no processamento: {str(e)}"

# ==============================================================================
# 2. INTERFACE E ANALYTICS
# ==============================================================================

st.title("📊 Painel de Controle Pedagógico")
st.markdown("Uma abordagem econométrica para gestão de sala de aula.")

# Upload
uploaded_file = st.sidebar.file_uploader("Carregar Base (.xlsx ou .csv)", type=['xlsx', 'csv'])

if uploaded_file:
    df_alunos, df_painel, erro = carregar_e_processar_dados(uploaded_file)
    
    if erro:
        st.error(erro)
    else:
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
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Visão Longitudinal (Painel)", "🧮 Modelagem Econométrica", "🔮 Simulador", "📋 Dados Brutos"])

        # --- TAB 1: VISÃO LONGITUDINAL (Onde o Painel Brilha) ---
        with tab1:
            st.markdown("### A Evolução do Aluno no Tempo")
            st.caption("Diferente da média simples, aqui observamos a consistência do aluno ao longo do semestre (Conceito de Série Temporal).")
            
            # Agrupar por tempo para ver a tendência da turma
            trend_turma = df_painel.groupby('Tempo')[['X_Presenca', 'X_Homework', 'X_Participacao']].mean().reset_index()
            
            # Seleção de Aluno para Comparar
            alunos_lista = sorted(df_painel['Aluno'].unique())
            aluno_foco = st.selectbox("Selecione um aluno para comparar com a média:", alunos_lista)
            
            df_aluno = df_painel[df_painel['Aluno'] == aluno_foco]
            
            # Gráfico Combinado
            fig = go.Figure()
            
            # Linha da Turma (Média)
            fig.add_trace(go.Scatter(x=trend_turma['Tempo'], y=trend_turma['X_Participacao'], 
                                     name='Média da Turma (Participação)',
                                     line=dict(color='gray', width=2, dash='dot')))
            
            # Linha do Aluno
            fig.add_trace(go.Scatter(x=df_aluno['Tempo'], y=df_aluno['X_Participacao'], 
                                     name=f'{aluno_foco} (Participação)',
                                     line=dict(color='blue', width=4),
                                     mode='lines+markers'))
            
            fig.update_layout(title="Trajetória de Engajamento: Indivíduo vs. Coletivo",
                              yaxis_title="Índice de Engajamento (0 a 1)",
                              yaxis_range=[-0.1, 1.1])
            st.plotly_chart(fig, use_container_width=True)
            
            # Heatmap de consistência
            st.subheader("Mapa de Calor: Consistência de Entregas (Homework)")
            pivot_hw = df_painel.pivot_table(index='Aluno', columns='Tempo', values='X_Homework', fill_value=0)
            fig_heat = px.imshow(pivot_hw, color_continuous_scale='RdBu', aspect="auto")
            st.plotly_chart(fig_heat, use_container_width=True)

        # --- TAB 2: ECONOMETRIA (Between Effects) ---
        with tab2:
            st.markdown("### Modelagem dos Determinantes do Desempenho")
            st.info("""
            **Nota Metodológica:** Como a variável dependente (Nota Final) é invariante no tempo (uma por aluno), 
            utilizamos uma abordagem **Between Effects** (Médias por Indivíduo). 
            Isso estima o impacto do comportamento *médio* do aluno sobre sua nota final.
            """)
            
            # Preparar dados para Regressão (Agregando o Painel)
            df_reg = df_painel.groupby('Aluno').agg({
                'X_Presenca': 'mean',
                'X_Homework': 'mean',
                'X_Participacao': 'mean',
                'Y_Nota': 'first' # A nota é a mesma para todas as linhas do aluno
            }).reset_index()
            
            # Regressão Múltipla (OLS)
            results = smf.ols('Y_Nota ~ X_Presenca + X_Homework + X_Participacao', data=df_reg).fit()
            
            col_res1, col_res2 = st.columns(2)
            
            with col_res1:
                st.write("#### Resultados Estatísticos")
                # Criar tabela bonita de coeficientes
                coefs = pd.DataFrame({
                    'Coeficiente': results.params,
                    'Erro Padrão': results.bse,
                    'P-Valor': results.pvalues,
                    'Impacto (0-10)': results.params  # Impacto direto na nota
                })
                st.dataframe(coefs.style.format("{:.4f}").background_gradient(cmap="Greens", subset=['P-Valor']), use_container_width=True)
                
                r2 = results.rsquared
                st.metric("R² (Poder Explicativo)", f"{r2:.1%}", 
                          help="Quanto da variação nas notas é explicada pelo modelo.")

            with col_res2:
                st.write("#### Interpretação Econômica")
                beta_part = results.params.get('X_Participacao', 0)
                beta_pres = results.params.get('X_Presenca', 0)
                
                st.markdown(f"""
                * **Participação é chave?** Um aumento de 10% na média de participação gera um aumento estimado de **{beta_part*0.1:.2f} pontos** na nota final.
                * **Presença importa?** Faltar 10% das aulas reduz a nota esperada em **{abs(beta_pres*0.1):.2f} pontos**.
                * **Intercepto:** Se um aluno não fizer nada (zero em tudo), a nota prevista é **{results.params['Intercept']:.2f}**.
                """)

        # --- TAB 3: SIMULADOR (What-If) ---
        with tab3:
            st.markdown("### 🔮 Simulador de Notas")
            st.write("Com base no modelo treinado, qual seria a nota de um aluno com o seguinte perfil?")
            
            c_sim1, c_sim2, c_sim3 = st.columns(3)
            with c_sim1:
                s_pres = st.slider("Presença (%)", 0, 100, 80) / 100
            with c_sim2:
                s_hw = st.slider("Entregas de Homework (%)", 0, 100, 70) / 100
            with c_sim3:
                s_part = st.slider("Nível de Participação (%)", 0, 100, 50) / 100
            
            # Cálculo da Previsão
            params = results.params
            nota_prevista = (params['Intercept'] + 
                             params.get('X_Presenca', 0) * s_pres + 
                             params.get('X_Homework', 0) * s_hw + 
                             params.get('X_Participacao', 0) * s_part)
            
            # Gauge Chart
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = nota_prevista,
                title = {'text': "Nota Prevista"},
                gauge = {'axis': {'range': [0, 10]},
                         'bar': {'color': "#2c3e50"},
                         'steps': [
                             {'range': [0, 5], 'color': "#ffadad"},
                             {'range': [5, 7], 'color': "#ffd6a5"},
                             {'range': [7, 10], 'color': "#caffbf"}],
                         'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 7}}
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)

        with tab4:
            st.dataframe(df_painel)

else:
    st.info("Aguardando upload do arquivo de dados...")
    # Cria um botão para baixar um template CSV se necessário
    # (Código omitido para brevidade, mas seria uma boa prática)
