import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Configuração da Página
st.set_page_config(
    page_title="Inteligência Educacional - PUC-SP",
    page_icon="🎓",
    layout="wide"
)

# ==============================================================================
# 1. FUNÇÃO DE CARREGAMENTO E ETL (COM CACHE)
# ==============================================================================
@st.cache_data
def carregar_dados(uploaded_file):
    # Lê o arquivo (header=1 é crucial para pegar as datas)
    try:
        df = pd.read_csv(uploaded_file, header=1)
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
        return None, None

    # --- ETL ALUNOS ---
    # Índices fixos baseados na estrutura enviada
    colunas_notas = [0, 1, 2, 3, 83, 84, 85]
    # Verifica se os índices existem para evitar erro de out-of-bounds
    if df.shape[1] < 86:
        st.error("O arquivo parece não ter a estrutura de colunas esperada.")
        return None, None
        
    df_alunos = df.iloc[1:, colunas_notas].copy()
    df_alunos.columns = ["Feedback", "Sala", "Num", "Nome_Completo", "Media_Provas", "Nota_Final", "Situacao_Final"]

    def limpar_numero(x):
        try: return float(str(x).replace(',', '.'))
        except: return np.nan

    df_alunos['Nota_Final'] = df_alunos['Nota_Final'].apply(limpar_numero)
    df_alunos = df_alunos.dropna(subset=['Nome_Completo'])

    # --- ETL DIÁRIO (PAINEL) ---
    nomes_variaveis = df.iloc[0]
    lista_aulas = []
    col_idx = 4

    while col_idx < len(df.columns):
        if col_idx >= len(nomes_variaveis) or nomes_variaveis.iloc[col_idx] != "Pre-Class":
            break
        
        data_cabecalho = df.columns[col_idx]
        if "Unnamed" in str(data_cabecalho):
            data_cabecalho = f"Aula_{(col_idx-4)//5 + 1}"
            
        bloco = df.iloc[1:, col_idx:col_idx+5].copy()
        bloco.columns = ["Pre_Class", "Presenca", "Homework", "Participacao", "Comportamento"]
        bloco["Data_Original"] = data_cabecalho
        bloco["Nome_Completo"] = df.iloc[1:, 3]
        
        lista_aulas.append(bloco)
        col_idx += 5

    if not lista_aulas:
        st.warning("Nenhuma aula encontrada na estrutura do arquivo.")
        return None, None

    df_diario = pd.concat(lista_aulas, ignore_index=True)
    df_diario = df_diario.dropna(subset=['Nome_Completo'])

    # Mapeamentos
    mapa_presenca = {'P': 1.0, '1/2': 0.5, 'A': 0.0}
    mapa_homework = {'√': 1.0, '+/-': 0.5, 'N': 0.0}
    df_diario['Score_Presenca'] = df_diario['Presenca'].map(mapa_presenca)
    df_diario['Score_Homework'] = df_diario['Homework'].map(mapa_homework)

    # Datas
    meses_pt = {'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'mai': 'May', 'jun': 'Jun',
                'jul': 'Jul', 'ago': 'Aug', 'set': 'Sep', 'out': 'Oct', 'nov': 'Nov', 'dez': 'Dec'}
    
    def parse_data(d):
        if 'Aula' in str(d): return None
        try:
            partes = str(d).split('-')
            if len(partes) == 3:
                dia, mes, ano = partes
                mes = mes.replace('.', '')
                mes_en = meses_pt.get(mes, mes)
                return pd.to_datetime(f"{dia}-{mes_en}-{ano}", format="%d-%b-%Y")
        except: return None

    df_diario['Data'] = df_diario['Data_Original'].apply(parse_data)

    # Merge Final
    stats = df_diario.groupby('Nome_Completo').agg({
        'Score_Presenca': 'mean',
        'Score_Homework': 'mean'
    }).reset_index()
    
    df_final = pd.merge(df_alunos, stats, on='Nome_Completo', how='left')
    
    return df_final, df_diario

# ==============================================================================
# 2. INTERFACE DO USUÁRIO
# ==============================================================================

st.title("🎓 Dashboard de Retenção de Alunos")
st.markdown("Análise estratégica de Presença, Engajamento e Comportamento.")

# Sidebar para Upload
st.sidebar.header("📂 Dados")
arquivo = st.sidebar.file_uploader("Carregar planilha (CSV)", type=["csv"])

if arquivo is not None:
    df_final, df_diario = carregar_dados(arquivo)
    
    if df_final is not None:
        # --- KPIs Iniciais ---
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        media_geral = df_final['Nota_Final'].mean()
        presenca_geral = df_final['Score_Presenca'].mean()
        hw_geral = df_final['Score_Homework'].mean()
        reprovados = len(df_final[df_final['Situacao_Final'] == 'Reprovado'])
        
        col1.metric("Média de Notas", f"{media_geral:.2f}")
        col2.metric("Presença Média", f"{presenca_geral:.1%}")
        col3.metric("Entrega de Tarefas", f"{hw_geral:.1%}")
        col4.metric("Total Reprovados", f"{reprovados}", delta_color="inverse")
        st.divider()

        # --- ABAS DE ANÁLISE ---
        tab1, tab2, tab3 = st.tabs(["📈 Engajamento & Tempo", "⚠️ Risco & Estratégia", "😊 Comportamento"])

        # --- ABA 1: TEMPO ---
        with tab1:
            st.subheader("Evolução Temporal")
            col_t1, col_t2 = st.columns([2, 1])
            
            with col_t1:
                # Gráfico 1: Série Temporal Presença
                trend = df_diario.dropna(subset=['Data']).groupby('Data')['Score_Presenca'].mean().reset_index()
                fig_trend = px.line(trend, x='Data', y='Score_Presenca', markers=True, 
                                    title='Evolução da Presença da Turma',
                                    labels={'Score_Presenca': 'Taxa de Presença'})
                fig_trend.update_yaxes(range=[0, 1.1])
                st.plotly_chart(fig_trend, use_container_width=True)
                
                with st.expander("💡 Análise Pedagógica"):
                    st.info("Quedas bruscas na linha indicam datas críticas (feriados ou conteúdo difícil). "
                            "Observe se a curva recupera no final do semestre (resiliência).")

            with col_t2:
                # Gráfico: Curva de Desistência (Gap Homework)
                df_timeline = pd.merge(df_diario, df_final[['Nome_Completo', 'Situacao_Final']], on='Nome_Completo')
                df_timeline = df_timeline.dropna(subset=['Data'])
                # Filtrar só status principais para limpar o gráfico
                df_foco = df_timeline[df_timeline['Situacao_Final'].isin(['Aprovado', 'Reprovado'])]
                timeline_hw = df_foco.groupby(['Data', 'Situacao_Final'])['Score_Homework'].mean().reset_index()
                
                fig_drop = px.line(timeline_hw, x='Data', y='Score_Homework', color='Situacao_Final',
                                   title='Gap de Tarefas (Aprov vs Reprov)',
                                   color_discrete_map={'Aprovado': 'green', 'Reprovado': 'red'})
                st.plotly_chart(fig_drop, use_container_width=True)
                
                with st.expander("💡 O Gap da Desistência"):
                    st.warning("Se as linhas se separam cedo (ex: semana 2), a intervenção precisa ser imediata. "
                               "Reprovados costumam parar de entregar tarefas muito antes de faltar.")

        # --- ABA 2: RISCO ---
        with tab2:
            st.subheader("Matriz de Risco e Desempenho")
            
            # Gráfico Quadrantes (O mais importante)
            media_pres = df_final['Score_Presenca'].mean()
            media_hw = df_final['Score_Homework'].mean()
            
            fig_quad = px.scatter(df_final, x='Score_Presenca', y='Score_Homework',
                                  color='Situacao_Final', size='Nota_Final',
                                  hover_name='Nome_Completo',
                                  title='Quadrantes de Engajamento (Passe o mouse para ver o aluno)',
                                  labels={'Score_Presenca': 'Presença', 'Score_Homework': 'Entrega de Lição'},
                                  color_discrete_sequence=px.colors.qualitative.Bold)
            
            # Linhas de Média
            fig_quad.add_hline(y=media_hw, line_dash="dash", line_color="gray", annotation_text="Média Homework")
            fig_quad.add_vline(x=media_pres, line_dash="dash", line_color="gray", annotation_text="Média Presença")
            
            # Anotações dos Quadrantes
            fig_quad.add_annotation(x=0.1, y=0.9, text="ZONA DE RISCO", showarrow=False, font=dict(color="red"))
            fig_quad.add_annotation(x=0.9, y=0.1, text="O TURISTA", showarrow=False, font=dict(color="orange"))
            fig_quad.add_annotation(x=0.9, y=0.9, text="ALUNO IDEAL", showarrow=False, font=dict(color="green"))
            
            st.plotly_chart(fig_quad, use_container_width=True)
            
            with st.expander("🔍 Quem é o 'Turista'?"):
                st.write("""
                **O Turista (Quadrante Inferior Direito):** Vai à aula, mas não entrega lição.
                É o aluno mais fácil de recuperar, pois já está presente fisicamente. 
                Basta aumentar a cobrança de atividades.
                """)

            col_r1, col_r2 = st.columns(2)
            
            with col_r1:
                # Correlação
                fig_corr = px.scatter(df_final, x='Score_Presenca', y='Nota_Final', color='Situacao_Final',
                                      trendline="ols", title="Correlação: Presença vs Nota")
                st.plotly_chart(fig_corr, use_container_width=True)
            
            with col_r2:
                # Boxplot
                fig_box = px.box(df_final, x='Situacao_Final', y='Nota_Final', color='Situacao_Final',
                                 title="Distribuição de Notas por Status")
                st.plotly_chart(fig_box, use_container_width=True)

        # --- ABA 3: COMPORTAMENTO ---
        with tab3:
            st.subheader("Análise Comportamental (Emojis)")
            
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                # Barras de Emojis
                contagem_part = df_diario['Participacao'].value_counts().reset_index()
                contagem_part.columns = ['Emoji', 'Contagem']
                fig_bar = px.bar(contagem_part, x='Emoji', y='Contagem', color='Emoji',
                                 title="Clima da Sala (Total Interações)")
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with col_c2:
                # Heatmap
                cruzamento = pd.merge(df_diario[['Nome_Completo', 'Participacao']], 
                                      df_final[['Nome_Completo', 'Situacao_Final']], on='Nome_Completo')
                
                # Crosstab normalizada
                heatmap_data = pd.crosstab(cruzamento['Situacao_Final'], cruzamento['Participacao'], normalize='index')
                
                fig_heat = px.imshow(heatmap_data, text_auto=".1%", aspect="auto",
                                     color_continuous_scale="Reds",
                                     title="Heatmap: Probabilidade de Reprovação por Emoji")
                st.plotly_chart(fig_heat, use_container_width=True)
                
                with st.expander("💡 Interpretação do Heatmap"):
                    st.info("Verifique a linha 'Reprovado'. Se a coluna ':-/' (Tédio) estiver mais escura (alta %), "
                            "significa que o desinteresse manifesto é um forte previsor de reprovação.")

else:
    st.info("Por favor, faça o upload do arquivo CSV na barra lateral para iniciar a análise.")
    st.markdown("""
    **Formato esperado:** Arquivo CSV exportado da planilha Eric - PUC-SP.
    O sistema identificará automaticamente as colunas de notas e datas.
    """)