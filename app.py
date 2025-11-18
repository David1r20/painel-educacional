import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf

# ==============================================================================
# CONFIGURAÇÃO ACADÊMICA
# ==============================================================================
st.set_page_config(
    page_title="Análise Econométrica Educacional",
    page_icon="🎓",
    layout="wide"
)

st.markdown("""
    <style>
    /* CORREÇÃO DE LEITURA: Forçar cor escura no texto dentro das caixas brancas */
    .academic-box {
        background-color: #f8f9fa; /* Fundo Claro (Papel) */
        color: #31333F;            /* Texto Escuro (Obrigatório) */
        border-left: 4px solid #2c3e50;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .theory-title {
        font-weight: bold; 
        color: #2c3e50; /* Azul Escuro */
        font-size: 1em; 
        text-transform: uppercase;
    }
    
    .theory-text {
        font-size: 0.95em; 
        color: #31333F; /* Cinza Escuro para leitura */
        font-style: italic;
    }
    
    .metric-container {
        text-align: center; 
        padding: 10px; 
        border: 1px solid #eee; 
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. ETL AVANÇADO
# ==============================================================================
@st.cache_data
def carregar_dados_completo(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, header=1, engine='openpyxl')
    except:
        return None, None, None

    # --- Dimensão Transversal ---
    try:
        colunas_fixas = [0, 1, 2, 3, 83, 84, 85]
        df_cross = df.iloc[1:, colunas_fixas].copy()
        df_cross.columns = ["Feedback", "Sala", "Num", "Nome_Completo", "Media_Provas", "Nota_Final", "Situacao_Final"]
        
        # Limpeza e Criação da Variável Binária (Dummy de Aprovação)
        df_cross['Nota_Final'] = pd.to_numeric(df_cross['Nota_Final'], errors='coerce').fillna(0)
        # Cria a variável binária: 1 se Aprovado, 0 se Reprovado/Outros
        df_cross['Aprovado_Bin'] = np.where(df_cross['Situacao_Final'] == 'Aprovado', 1, 0)
        df_cross = df_cross.dropna(subset=['Nome_Completo'])
    except:
        return None, None, None

    # --- Dimensão Temporal (Painel) ---
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
    # Mapeamento de Comportamento (Proxy de Soft Skills)
    mapa_part = {':-D': 1.0, ':-/': 0.5, ':-&': 0.0, ':-(': 0.0}
    
    df_panel['X_Presenca'] = df_panel['Presenca'].map(mapa_pres)
    df_panel['X_Homework'] = df_panel['Homework'].map(mapa_hw)
    df_panel['X_Participacao'] = df_panel['Participacao'].map(mapa_part).fillna(0.5) # Neutro se vazio

    # Consolidação (Between Effects)
    stats_between = df_panel.groupby('Individuo_i').agg({
        'X_Presenca': 'mean',
        'X_Homework': 'mean',
        'X_Participacao': 'mean'
    }).reset_index()
    
    df_final = pd.merge(df_cross, stats_between, left_on='Nome_Completo', right_on='Individuo_i', how='left')
    
    return df_final, df_panel

# ==============================================================================
# 2. INTERFACE
# ==============================================================================

st.title("📊 Estudo Econométrico: Determinantes do Desempenho")
st.markdown("Aplicação de modelos de **Painel**, **Regressão Logística** e **Análise de Resíduos**.")

arquivo = st.sidebar.file_uploader("Carregar Dados (.xlsx)", type=["xlsx"])

if arquivo:
    df_final, df_panel = carregar_dados_completo(arquivo)
    
    if df_final is not None:
        
        # KPI Section
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("N (Amostra)", len(df_final))
        k2.metric("Média Nota", f"{df_final['Nota_Final'].mean():.2f}")
        k3.metric("Taxa Aprovação", f"{df_final['Aprovado_Bin'].mean():.1%}")
        k4.metric("Presença Média", f"{df_final['X_Presenca'].mean():.1%}")

        tab_modelos, tab_eficiencia, tab_prob, tab_individual = st.tabs([
            "📉 Modelagem & Testes (PDF)", 
            "🔍 Análise de Eficiência (Resíduos)",
            "🎲 Probabilidade (Logit)",
            "👤 Dossiê do Aluno"
        ])

        # ----------------------------------------------------------------------
        # ABA 1: MODELAGEM ECONOMÉTRICA RIGOROSA
        # ----------------------------------------------------------------------
        with tab_modelos:
            # CAIXA DE TEORIA (Agora com texto preto forçado)
            st.markdown("""
            <div class="academic-box">
                <div class="theory-title">Fundamentação: Comparação de Modelos</div>
                <div class="theory-text">
                    Comparamos o modelo linear simples com modelos que controlam variáveis comportamentais. 
                    Utilizamos métricas (AIC, BIC, R²) citadas na literatura de Séries Temporais para selecionar o melhor ajuste.
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Preparação dos dados para regressão (Remover NaNs)
            colunas_modelo = ['Nota_Final', 'X_Presenca', 'X_Homework', 'X_Participacao', 'Aprovado_Bin']
            df_reg = df_final[colunas_modelo].dropna()
            
            col_m1, col_m2 = st.columns([1, 2])
            
            with col_m1:
                st.subheader("Especificações")
                st.info("Modelo 1: Apenas Presença")
                st.info("Modelo 2: Presença + Homework")
                st.info("Modelo 3: Modelo Completo (+ Participação)")
                
                # Rodar Modelos
                mod1 = smf.ols("Nota_Final ~ X_Presenca", data=df_reg).fit()
                mod2 = smf.ols("Nota_Final ~ X_Presenca + X_Homework", data=df_reg).fit()
                mod3 = smf.ols("Nota_Final ~ X_Presenca + X_Homework + X_Participacao", data=df_reg).fit()
                
                # Tabela de Comparação
                res_table = pd.DataFrame({
                    'Modelo': ['1. Simples', '2. Intermediário', '3. Completo'],
                    'R-quadrado': [mod1.rsquared, mod2.rsquared, mod3.rsquared],
                    'AIC': [mod1.aic, mod2.aic, mod3.aic],
                    'BIC': [mod1.bic, mod2.bic, mod3.bic]
                })
                
                st.write("### Critérios de Informação")
                st.dataframe(res_table.style.format({'R-quadrado': '{:.2%}', 'AIC': '{:.1f}', 'BIC': '{:.1f}'}), hide_index=True)
                st.caption("*AIC/BIC menores indicam melhores modelos (Parsimônia).*")

            with col_m2:
                st.subheader("Resultados do Modelo Completo (OLS)")
                st.write(mod3.summary())
                
                st.markdown("""
                **Interpretação dos Coeficientes ($\beta$):**
                * **X_Presenca:** O impacto marginal de estar presente na nota final.
                * **X_Participacao:** Mede o efeito das *Soft Skills* (Emojis) no resultado, controlando pela presença.
                * **P>|t|:** Se for menor que 0.05, a variável é estatisticamente significante.
                """)

        # ----------------------------------------------------------------------
        # ABA 2: ANÁLISE DE EFICIÊNCIA (RESÍDUOS / ALFA)
        # ----------------------------------------------------------------------
        with tab_eficiencia:
            st.markdown("""
            <div class="academic-box">
                <div class="theory-title">Conceito: Efeitos Individuais Não Observados ($\mu_i$)</div>
                <div class="theory-text">
                    Ao analisar os resíduos da regressão ($Y - \hat{Y}$), identificamos se o aluno está performando 
                    acima ou abaixo do esperado dado o seu comportamento observável.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Calcular Resíduos do Modelo Completo
            # Usamos o modelo 3 treinado na aba anterior
            df_final['Nota_Prevista'] = mod3.predict(df_final)
            df_final['Residuo'] = df_final['Nota_Final'] - df_final['Nota_Prevista']
            
            # Classificação baseada no resíduo
            def classificar_eficiencia(res):
                if res > 1.5: return "Superou Expectativa (Overperformer)"
                if res < -1.5: return "Abaixo da Expectativa (Alerta Pedagógico)"
                return "Dentro do Esperado"
                
            df_final['Status_Eficiencia'] = df_final['Residuo'].apply(classificar_eficiencia)
            
            # Gráfico de Resíduos
            fig_res = px.scatter(df_final, x='Nota_Prevista', y='Residuo', 
                                 color='Status_Eficiencia', hover_name='Nome_Completo',
                                 title="Análise de Resíduos: Quem surpreende e quem preocupa?",
                                 color_discrete_map={
                                     "Superou Expectativa (Overperformer)": "green",
                                     "Dentro do Esperado": "gray",
                                     "Abaixo da Expectativa (Alerta Pedagógico)": "red"
                                 })
            fig_res.add_hline(y=0, line_dash="dash", line_color="black")
            st.plotly_chart(fig_res, use_container_width=True)
            
            # Tabela de Alerta
            st.subheader("🚨 Lista de Alerta: Dificuldade de Aprendizagem?")
            st.markdown("Estes alunos têm presença e tarefas entregues, mas a nota é muito menor que a prevista pelo modelo. Pode indicar dificuldade cognitiva ou problemas externos.")
            alerta_df = df_final[df_final['Status_Eficiencia'] == "Abaixo da Expectativa (Alerta Pedagógico)"]
            st.dataframe(alerta_df[['Nome_Completo', 'Nota_Final', 'Nota_Prevista', 'Residuo', 'X_Presenca']], use_container_width=True)

        # ----------------------------------------------------------------------
        # ABA 3: PROBABILIDADE (LOGIT)
        # ----------------------------------------------------------------------
        with tab_prob:
            st.markdown("""
            <div class="academic-box">
                <div class="theory-title">Modelagem: Regressão Logística (Logit)</div>
                <div class="theory-text">
                    Em vez de prever a nota exata, estimamos a <b>Probabilidade de Aprovação</b> ($P(Y=1|X)$). 
                    Isso transforma a análise em gestão de risco binária.
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Modelo Logit
            try:
                # Agora df_reg TEM a coluna 'Aprovado_Bin'
                modelo_logit = smf.logit("Aprovado_Bin ~ X_Presenca + X_Homework", data=df_reg).fit(disp=0)
                df_final['Probabilidade_Aprovacao'] = modelo_logit.predict(df_final)
                
                c_prob1, c_prob2 = st.columns(2)
                
                with c_prob1:
                    fig_hist_prob = px.histogram(df_final, x='Probabilidade_Aprovacao', nbins=20,
                                                 title="Histograma: Risco da Turma",
                                                 labels={'Probabilidade_Aprovacao': 'Chance de Aprovação'},
                                                 color_discrete_sequence=['#17a2b8'])
                    st.plotly_chart(fig_hist_prob, use_container_width=True)
                    
                with c_prob2:
                    st.subheader("Zona de Perigo (Probabilidade < 50%)")
                    perigo = df_final[df_final['Probabilidade_Aprovacao'] < 0.5].sort_values('Probabilidade_Aprovacao')
                    
                    st.write(f"Foram identificados **{len(perigo)}** alunos com chance de reprovação maior que 50%.")
                    
                    # Tabela formatada
                    show_perigo = perigo[['Nome_Completo', 'Probabilidade_Aprovacao', 'X_Presenca']]
                    show_perigo['Probabilidade_Aprovacao'] = show_perigo['Probabilidade_Aprovacao'].map('{:.1%}'.format)
                    show_perigo['X_Presenca'] = show_perigo['X_Presenca'].map('{:.1%}'.format)
                    
                    st.dataframe(show_perigo, use_container_width=True)
                    
            except Exception as e:
                st.error(f"Erro ao rodar Logit: {e}")

        # ----------------------------------------------------------------------
        # ABA 4: INDIVIDUAL (COM CÁLCULOS)
        # ----------------------------------------------------------------------
        with tab_individual:
            st.header("Dossiê Analítico Individual")
            aluno_sel = st.selectbox("Pesquisar:", sorted(df_final['Nome_Completo'].unique()))
            
            if aluno_sel:
                dado = df_final[df_final['Nome_Completo'] == aluno_sel].iloc[0]
                
                # Cards com cálculos
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Nota Real", f"{dado['Nota_Final']:.1f}")
                c2.metric("Nota Esperada (Modelo)", f"{dado['Nota_Prevista']:.1f}", 
                          delta=f"{dado['Residuo']:.1f}", delta_color="normal")
                
                prob_val = dado.get('Probabilidade_Aprovacao', 0)
                c3.metric("Chance de Aprovação", f"{prob_val:.1%}")
                
                eff_label = dado['Status_Eficiencia']
                # Ajuste cor do delta para Eficiência
                c4.metric("Diagnóstico de Eficiência", eff_label, 
                          delta_color="off" if "Dentro" in eff_label else "inverse")
                
                st.divider()
                
                # Gráfico Radar (Spider Plot) - Visualização Multivariada
                # Normalizando para escala 0-10 para comparar
                categories = ['Presença', 'Homework', 'Participação', 'Nota Final']
                values = [
                    dado['X_Presenca'] * 10, 
                    dado['X_Homework'] * 10, 
                    dado['X_Participacao'] * 10, 
                    dado['Nota_Final']
                ]
                
                # Média da Turma para Comparação
                avg_values = [
                    df_final['X_Presenca'].mean() * 10,
                    df_final['X_Homework'].mean() * 10,
                    df_final['X_Participacao'].mean() * 10,
                    df_final['Nota_Final'].mean()
                ]
                
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name=aluno_sel))
                fig_radar.add_trace(go.Scatterpolar(r=avg_values, theta=categories, name='Média da Turma', line=dict(dash='dash', color='gray')))
                
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), title="Perfil Multivariado vs Média")
                st.plotly_chart(fig_radar, use_container_width=True)

else:
    st.info("👈 Aguardando base de dados.")
