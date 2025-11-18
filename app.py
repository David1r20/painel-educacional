import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Sistema de Inteligência Educacional",
    page_icon="🎓",
    layout="wide"
)

# Estilo CSS para deixar mais profissional
st.markdown("""
    <style>
    .metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; margin: 10px 0;}
    .risk-alert {color: #d32f2f; font-weight: bold;}
    .opportunity-alert {color: #f57c00; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. CARREGAMENTO E TRATAMENTO DE DADOS (ROBUSTO)
# ==============================================================================
@st.cache_data
def carregar_dados(uploaded_file):
    try:
        # Lê o Excel forçando a engine openpyxl
        df = pd.read_excel(uploaded_file, header=1, engine='openpyxl')
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None, None, None

    # --- 1. Tabela de Alunos (Notas e Status) ---
    # Seleciona colunas pela posição (metadados + notas finais)
    try:
        colunas_notas = [0, 1, 2, 3, 83, 84, 85]
        df_alunos = df.iloc[1:, colunas_notas].copy()
        df_alunos.columns = ["Feedback", "Sala", "Num", "Nome_Completo", "Media_Provas", "Nota_Final", "Situacao_Final"]
        
        # Limpeza numérica
        def limpar_num(x):
            try: return float(str(x).replace(',', '.'))
            except: return np.nan
            
        df_alunos['Nota_Final'] = df_alunos['Nota_Final'].apply(limpar_num).fillna(0) # Preenche vazio com 0 para não quebrar gráfico
        df_alunos = df_alunos.dropna(subset=['Nome_Completo'])
    except:
        st.error("Erro na estrutura das colunas de Notas. Verifique o arquivo.")
        return None, None, None

    # --- 2. Tabela Diária (Painel: Aluno x Data) ---
    nomes_variaveis = df.iloc[0]
    lista_aulas = []
    col_idx = 4
    
    while col_idx < len(df.columns):
        # Segurança: para se acabar as colunas ou não for mais aula
        if col_idx >= len(nomes_variaveis): break
        if str(nomes_variaveis.iloc[col_idx]) != "Pre-Class": break
        
        # Identifica Data
        data_raw = df.columns[col_idx]
        data_str = f"Aula_{(col_idx-4)//5 + 1}" if "Unnamed" in str(data_raw) else str(data_raw)
        
        # Extrai bloco
        bloco = df.iloc[1:, col_idx:col_idx+5].copy()
        bloco.columns = ["Pre_Class", "Presenca", "Homework", "Participacao", "Comportamento"]
        bloco["Data_Original"] = data_str
        bloco["Nome_Completo"] = df.iloc[1:, 3]
        
        lista_aulas.append(bloco)
        col_idx += 5

    if not lista_aulas:
        st.error("Não foi possível identificar as aulas (colunas 'Pre-Class').")
        return None, None, None

    df_diario = pd.concat(lista_aulas, ignore_index=True)
    df_diario = df_diario.dropna(subset=['Nome_Completo'])

    # --- 3. Feature Engineering (Cálculos) ---
    mapa_presenca = {'P': 1.0, '1/2': 0.5, 'A': 0.0}
    mapa_homework = {'√': 1.0, '+/-': 0.5, 'N': 0.0}
    
    df_diario['Score_Presenca'] = df_diario['Presenca'].map(mapa_presenca)
    df_diario['Score_Homework'] = df_diario['Homework'].map(mapa_homework)

    # Tratamento de Datas (PT-BR)
    meses = {'fev': 'Feb', 'mar': 'Mar', 'abr': 'Apr', 'mai': 'May', 'jun': 'Jun', 
             'jul': 'Jul', 'ago': 'Aug', 'set': 'Sep', 'out': 'Oct', 'nov': 'Nov', 'dez': 'Dec'}
    
    def converter_data(d):
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

    df_diario['Data'] = df_diario['Data_Original'].apply(converter_data)

    # --- 4. Consolidação Final ---
    stats = df_diario.groupby('Nome_Completo').agg({
        'Score_Presenca': 'mean',
        'Score_Homework': 'mean'
    }).reset_index()
    
    df_final = pd.merge(df_alunos, stats, on='Nome_Completo', how='left')
    
    # Segmentação de Risco (Quadrantes)
    media_pres = df_final['Score_Presenca'].mean()
    media_hw = df_final['Score_Homework'].mean()
    
    def classificar_aluno(row):
        if row['Score_Presenca'] < media_pres and row['Score_Homework'] < media_hw:
            return "🔴 Risco Crítico"
        elif row['Score_Presenca'] >= media_pres and row['Score_Homework'] < media_hw:
            return "🟠 Turista (Vai mas não faz)"
        elif row['Score_Presenca'] < media_pres and row['Score_Homework'] >= media_hw:
            return "🔵 Autodidata"
        else:
            return "🟢 Ideal"
            
    df_final['Categoria_Risco'] = df_final.apply(classificar_aluno, axis=1)

    return df_final, df_diario, (media_pres, media_hw)

# ==============================================================================
# 2. INTERFACE DO USUÁRIO
# ==============================================================================

st.title("🎓 Inteligência Educacional & Gestão de Risco")
st.markdown("Transformando dados brutos em **estratégias de retenção de alunos**.")

# --- Sidebar ---
st.sidebar.header("📂 Carregar Dados")
arquivo = st.sidebar.file_uploader("Faça upload da planilha Excel (.xlsx)", type=["xlsx"])

st.sidebar.markdown("---")
st.sidebar.info("Desenvolvido para análise pedagógica baseada em evidências.")

if arquivo:
    df_final, df_diario, medias = carregar_dados(arquivo)
    
    if df_final is not None:
        # --- KPIs ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Média Geral da Turma", f"{df_final['Nota_Final'].mean():.2f}")
        col2.metric("Frequência Média", f"{df_final['Score_Presenca'].mean():.1%}")
        col3.metric("Entrega de Tarefas", f"{df_final['Score_Homework'].mean():.1%}")
        
        n_risco = len(df_final[df_final['Categoria_Risco'] == "🔴 Risco Crítico"])
        col4.metric("Alunos em Risco Crítico", f"{n_risco}", delta_color="inverse")
        
        # --- ABAS PRINCIPAIS ---
        tab_visao, tab_acao, tab_aluno = st.tabs([
            "📊 Visão Macro (Diagnóstico)", 
            "🎯 Ação & Listas de Risco (Útil)", 
            "👤 Raio-X do Aluno (Individual)"
        ])

        # ----------------------------------------------------------------------
        # ABA 1: VISÃO MACRO
        # ----------------------------------------------------------------------
        with tab_visao:
            st.subheader("Diagnóstico da Turma")
            
            c1, c2 = st.columns([2, 1])
            with c1:
                # Gráfico Temporal
                trend = df_diario.dropna(subset=['Data']).groupby('Data')['Score_Presenca'].mean().reset_index()
                fig_trend = px.line(trend, x='Data', y='Score_Presenca', markers=True,
                                    title='Evolução do Engajamento (Presença)', 
                                    labels={'Score_Presenca': 'Presença'})
                fig_trend.update_yaxes(range=[0, 1.1])
                st.plotly_chart(fig_trend, use_container_width=True)
            
            with c2:
                # Correlação
                fig_corr = px.scatter(df_final, x='Score_Presenca', y='Nota_Final', 
                                      color='Situacao_Final', title="Presença define a Nota?")
                st.plotly_chart(fig_corr, use_container_width=True)
                st.caption("Nota: Pontos no canto inferior esquerdo indicam que faltas levam à reprovação.")

            # Análise de Comportamento
            st.subheader("Clima de Sala de Aula")
            part_counts = df_diario['Participacao'].value_counts().reset_index()
            part_counts.columns = ['Emoji', 'Contagem']
            
            fig_bar = px.bar(part_counts, x='Emoji', y='Contagem', color='Emoji', 
                             title="Como os alunos reagem em aula?",
                             color_discrete_map={':-D': '#66c2a5', ':-/': '#fc8d62', ':-&': '#d53e4f'})
            st.plotly_chart(fig_bar, use_container_width=True)

        # ----------------------------------------------------------------------
        # ABA 2: AÇÃO & LISTAS (A PARTE "ÚTIL" DE GESTÃO)
        # ----------------------------------------------------------------------
        with tab_acao:
            st.header("🎯 Painel de Intervenção Pedagógica")
            st.markdown("Use esta aba para identificar **quem** precisa de ajuda imediata.")
            
            # Gráfico Quadrantes
            media_pres, media_hw = medias
            
            # Adiciona coluna de tamanho para o gráfico (bolinhas maiores para notas maiores)
            df_final['Tamanho'] = df_final['Nota_Final'] + 1

            fig_quad = px.scatter(df_final, x='Score_Presenca', y='Score_Homework',
                                  color='Categoria_Risco', 
                                  size='Tamanho',
                                  hover_name='Nome_Completo',
                                  hover_data={'Nota_Final':':.1f', 'Tamanho':False},
                                  title='Matriz Estratégica: Onde estão seus alunos?',
                                  color_discrete_map={
                                      "🟢 Ideal": "green",
                                      "🟠 Turista (Vai mas não faz)": "orange",
                                      "🔴 Risco Crítico": "red",
                                      "🔵 Autodidata": "blue"
                                  })
            
            # Linhas de corte
            fig_quad.add_hline(y=media_hw, line_dash="dash", line_color="grey", annotation_text="Média Tarefas")
            fig_quad.add_vline(x=media_pres, line_dash="dash", line_color="grey", annotation_text="Média Presença")
            st.plotly_chart(fig_quad, use_container_width=True)

            # --- GERADOR DE LISTAS ---
            st.divider()
            st.subheader("📋 Listas de Chamada para Ação")
            
            filtro = st.selectbox("Selecione o Grupo para Gerar Lista:", 
                                  ["🔴 Risco Crítico", "🟠 Turista (Vai mas não faz)", "🔵 Autodidata", "🟢 Ideal"])
            
            # Filtra o DataFrame
            df_filtrado = df_final[df_final['Categoria_Risco'] == filtro][['Nome_Completo', 'Nota_Final', 'Score_Presenca', 'Score_Homework', 'Situacao_Final']]
            
            # Formata para exibição
            df_display = df_filtrado.copy()
            df_display['Score_Presenca'] = df_display['Score_Presenca'].map('{:.0%}'.format)
            df_display['Score_Homework'] = df_display['Score_Homework'].map('{:.0%}'.format)
            df_display['Nota_Final'] = df_display['Nota_Final'].map('{:.1f}'.format)
            
            st.write(f"**Encontrados {len(df_filtrado)} alunos neste grupo.**")
            st.dataframe(df_display, use_container_width=True)
            
            if not df_filtrado.empty:
                st.download_button("📥 Baixar Lista em Excel", 
                                   data=df_filtrado.to_csv(index=False).encode('utf-8'),
                                   file_name=f"lista_alunos_{filtro.split()[1]}.csv",
                                   mime="text/csv")

        # ----------------------------------------------------------------------
        # ABA 3: RAIO-X DO ALUNO (INDIVIDUAL)
        # ----------------------------------------------------------------------
        with tab_aluno:
            st.subheader("Dossiê Individual do Aluno")
            
            alunos_lista = df_final['Nome_Completo'].unique()
            aluno_selecionado = st.selectbox("Pesquisar Aluno:", options=alunos_lista)
            
            if aluno_selecionado:
                # Dados do Aluno
                dados_aluno = df_final[df_final['Nome_Completo'] == aluno_selecionado].iloc[0]
                historico_aluno = df_diario[df_diario['Nome_Completo'] == aluno_selecionado].sort_values('Data_Original')
                
                # Cards de Resumo
                ca, cb, cc, cd = st.columns(4)
                ca.metric("Situação Atual", dados_aluno['Situacao_Final'])
                cb.metric("Nota Final", f"{dados_aluno['Nota_Final']:.1f}")
                cc.metric("Presença", f"{dados_aluno['Score_Presenca']:.1%}")
                cd.metric("Tarefas", f"{dados_aluno['Score_Homework']:.1%}")
                
                st.divider()
                
                # Gráfico Comparativo: Aluno vs Média da Turma (Homework)
                c_g1, c_g2 = st.columns(2)
                
                with c_g1:
                    st.markdown("**Histórico de Presença e Tarefas**")
                    # Prepara dados para gráfico de barras agrupado
                    hist_melt = historico_aluno.melt(id_vars=['Data_Original'], 
                                                   value_vars=['Score_Presenca', 'Score_Homework'],
                                                   var_name='Métrica', value_name='Valor')
                    
                    fig_hist = px.bar(hist_melt, x='Data_Original', y='Valor', color='Métrica', barmode='group',
                                      title="Evolução Aula a Aula", height=350)
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                with c_g2:
                    st.markdown("**Comportamento em Sala (Emojis)**")
                    if not historico_aluno.empty:
                        counts = historico_aluno['Participacao'].value_counts()
                        fig_pie = px.pie(values=counts.values, names=counts.index, 
                                         title="Perfil de Participação", height=350, hole=0.4)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.info("Sem dados de participação.")

else:
    st.info("👈 Aguardando upload do arquivo Excel na barra lateral.")
    st.markdown("""
    ### Como usar esta ferramenta:
    1. Exporte sua planilha de controle para **Excel (.xlsx)**.
    2. Arraste o arquivo para a barra lateral.
    3. Navegue nas abas para identificar **quem precisa de ajuda**.
    """)
