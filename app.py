import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA & ESTILO (DESIGN SYSTEM)
# ==============================================================================
st.set_page_config(
    page_title="Sistema de Inteligência Educacional",
    page_icon="🎓",
    layout="wide"
)

# CSS Profissional para Layout de Cards
st.markdown("""
    <style>
    /* Fundo geral mais limpo */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Estilo dos Cartões (Gráficos e Métricas) */
    .dashboard-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    
    /* Títulos das Métricas */
    .metric-label {
        font-size: 14px;
        color: #666;
        margin-bottom: 5px;
    }
    
    .metric-value {
        font-size: 26px;
        font-weight: bold;
        color: #333;
    }
    
    /* Nota Técnica discreta */
    .tech-note {
        font-size: 12px;
        color: #888;
        background-color: #f1f3f5;
        padding: 8px;
        border-radius: 6px;
        margin-top: 10px;
        border-left: 3px solid #4dabf7;
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. CARREGAMENTO E TRATAMENTO (Mantendo a lógica robusta)
# ==============================================================================
@st.cache_data
def carregar_dados(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file, header=1, engine='openpyxl')
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return None, None, None

    # --- ETL Alunos ---
    try:
        colunas_notas = [0, 1, 2, 3, 83, 84, 85]
        df_alunos = df.iloc[1:, colunas_notas].copy()
        df_alunos.columns = ["Feedback", "Sala", "Num", "Nome_Completo", "Media_Provas", "Nota_Final", "Situacao_Final"]
        
        def limpar_num(x):
            try: return float(str(x).replace(',', '.'))
            except: return np.nan
            
        df_alunos['Nota_Final'] = df_alunos['Nota_Final'].apply(limpar_num).fillna(0)
        df_alunos = df_alunos.dropna(subset=['Nome_Completo'])
    except:
        st.error("Erro na estrutura das colunas. Verifique o arquivo.")
        return None, None, None

    # --- ETL Painel Temporal ---
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
        bloco["Data_Original"] = data_str
        bloco["Nome_Completo"] = df.iloc[1:, 3]
        
        lista_aulas.append(bloco)
        col_idx += 5

    df_diario = pd.concat(lista_aulas, ignore_index=True)
    df_diario = df_diario.dropna(subset=['Nome_Completo'])

    mapa_presenca = {'P': 1.0, '1/2': 0.5, 'A': 0.0}
    mapa_homework = {'√': 1.0, '+/-': 0.5, 'N': 0.0}
    
    df_diario['Score_Presenca'] = df_diario['Presenca'].map(mapa_presenca)
    df_diario['Score_Homework'] = df_diario['Homework'].map(mapa_homework)

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

    stats = df_diario.groupby('Nome_Completo').agg({
        'Score_Presenca': 'mean',
        'Score_Homework': 'mean'
    }).reset_index()
    
    df_final = pd.merge(df_alunos, stats, on='Nome_Completo', how='left')
    
    media_pres = df_final['Score_Presenca'].mean()
    media_hw = df_final['Score_Homework'].mean()
    
    def classificar_aluno(row):
        if row['Score_Presenca'] < media_pres and row['Score_Homework'] < media_hw:
            return "🔴 Risco Crítico"
        elif row['Score_Presenca'] >= media_pres and row['Score_Homework'] < media_hw:
            return "🟠 Turista"
        elif row['Score_Presenca'] < media_pres and row['Score_Homework'] >= media_hw:
            return "🔵 Autodidata"
        else:
            return "🟢 Ideal"
            
    df_final['Categoria_Risco'] = df_final.apply(classificar_aluno, axis=1)
    df_final['Tamanho'] = df_final['Nota_Final'] + 2

    return df_final, df_diario, (media_pres, media_hw)

# ==============================================================================
# 2. INTERFACE (LAYOUT OTIMIZADO)
# ==============================================================================

st.title("🎓 Monitorização e Retenção")
st.markdown("**Abordagem Baseada em Dados em Painel**")

st.sidebar.header("📂 Configuração")
arquivo = st.sidebar.file_uploader("Carregar Excel (.xlsx)", type=["xlsx"])

st.sidebar.markdown("---")
with st.sidebar.expander("📘 Sobre a Metodologia"):
    st.markdown("""
    Este painel utiliza a estrutura de **Longitudinal Data (Painel)**:
    1. **Análise Within (Intra):** Acompanha a variação do aluno ao longo do tempo.
    2. **Análise Between (Entre):** Compara o aluno com a média da turma.
    """)

if arquivo:
    df_final, df_diario, medias = carregar_dados(arquivo)
    
    if df_final is not None:
        # --- BLOCO DE KPIs (Topo) ---
        # Usando container para agrupar visualmente
        with st.container():
            k1, k2, k3, k4 = st.columns(4)
            
            def card_metrica(col, titulo, valor, cor="black"):
                col.markdown(f"""
                <div class="dashboard-card" style="text-align: center; padding: 15px;">
                    <div class="metric-label">{titulo}</div>
                    <div class="metric-value" style="color: {cor}">{valor}</div>
                </div>
                """, unsafe_allow_html=True)

            card_metrica(k1, "Média Global (Nota)", f"{df_final['Nota_Final'].mean():.1f}")
            card_metrica(k2, "Presença Média", f"{df_final['Score_Presenca'].mean():.1%}")
            card_metrica(k3, "Entrega de Tarefas", f"{df_final['Score_Homework'].mean():.1%}")
            
            n_risco = len(df_final[df_final['Categoria_Risco'] == '🔴 Risco Crítico'])
            card_metrica(k4, "Alunos em Risco", f"{n_risco}", cor="#d32f2f")

        # --- ABAS ---
        tab1, tab2, tab3 = st.tabs(["📊 Diagnóstico Geral", "🎯 Gestão de Risco", "👤 Visão do Aluno"])

        # ======================================================================
        # ABA 1: DIAGNÓSTICO (LAYOUT MELHORADO)
        # ======================================================================
        with tab1:
            # LINHA 1: Série Temporal (Ocupa largura total para melhor visualização)
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.subheader("⏳ Dinâmica Temporal da Turma")
            
            trend = df_diario.dropna(subset=['Data']).groupby('Data')['Score_Presenca'].mean().reset_index()
            fig_trend = px.line(trend, x='Data', y='Score_Presenca', markers=True,
                                labels={'Score_Presenca': 'Taxa de Presença', 'Data': 'Semana'},
                                height=350) # Altura fixa controlada
            fig_trend.update_layout(margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_trend, use_container_width=True)
            
            st.markdown('<div class="tech-note"><b>Dimensão Temporal (t):</b> Identifica choques comuns a todos (ex: queda geral na semana de provas).</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # LINHA 2: Correlação e Clima (Lado a Lado 50/50)
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                st.subheader("📉 Frequência vs. Resultado")
                fig_corr = px.scatter(df_final, x='Score_Presenca', y='Nota_Final', color='Situacao_Final',
                                      height=350)
                fig_corr.update_layout(margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_corr, use_container_width=True)
                st.markdown('<div class="tech-note"><b>Dimensão Transversal (i):</b> Correlação estrutural entre comportamento e nota.</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with c2:
                st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
                st.subheader("😊 Clima de Sala (Emojis)")
                part_counts = df_diario['Participacao'].value_counts().reset_index()
                part_counts.columns = ['Emoji', 'Contagem']
                fig_bar = px.bar(part_counts, x='Emoji', y='Contagem', color='Emoji',
                                 color_discrete_map={':-D': '#66c2a5', ':-/': '#fc8d62', ':-&': '#d53e4f'},
                                 height=350)
                fig_bar.update_layout(margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_bar, use_container_width=True)
                st.markdown('<div class="tech-note"><b>Qualitativo:</b> Indicador antecedente de desengajamento.</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        # ======================================================================
        # ABA 2: GESTÃO DE RISCO
        # ======================================================================
        with tab2:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            st.subheader("🎯 Matriz Estratégica de Intervenção")
            
            media_pres, media_hw = medias
            
            fig_quad = px.scatter(df_final, x='Score_Presenca', y='Score_Homework',
                                  color='Categoria_Risco', size='Tamanho',
                                  hover_name='Nome_Completo',
                                  color_discrete_map={"🟢 Ideal": "green", "🟠 Turista": "orange", "🔴 Risco Crítico": "red", "🔵 Autodidata": "blue"},
                                  height=500) # Gráfico maior pois é o principal
            
            # Linhas de Corte
            fig_quad.add_hline(y=media_hw, line_dash="dash", line_color="gray", annotation_text="Média Tarefas")
            fig_quad.add_vline(x=media_pres, line_dash="dash", line_color="gray", annotation_text="Média Presença")
            fig_quad.update_layout(margin=dict(l=20, r=20, t=30, b=20))
            
            st.plotly_chart(fig_quad, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Lista de Ação
            st.markdown("### 📋 Gerar Lista de Chamada")
            col_sel, col_down = st.columns([2, 1])
            
            with col_sel:
                filtro = st.selectbox("Selecione o Grupo:", ["🔴 Risco Crítico", "🟠 Turista", "🔵 Autodidata", "🟢 Ideal"])
            
            df_filtrado = df_final[df_final['Categoria_Risco'] == filtro][['Nome_Completo', 'Nota_Final', 'Score_Presenca', 'Score_Homework', 'Situacao_Final']]
            
            # Formatação visual da tabela
            df_display = df_filtrado.copy()
            df_display['Score_Presenca'] = df_display['Score_Presenca'].map('{:.0%}'.format)
            df_display['Score_Homework'] = df_display['Score_Homework'].map('{:.0%}'.format)
            df_display['Nota_Final'] = df_display['Nota_Final'].map('{:.1f}'.format)

            st.dataframe(df_display, use_container_width=True)

        # ======================================================================
        # ABA 3: VISÃO DO ALUNO
        # ======================================================================
        with tab3:
            st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
            alunos_lista = sorted(df_final['Nome_Completo'].unique())
            aluno = st.selectbox("Pesquisar Aluno:", options=alunos_lista)
            
            if aluno:
                dados_aluno = df_final[df_final['Nome_Completo'] == aluno].iloc[0]
                historico = df_diario[df_diario['Nome_Completo'] == aluno].sort_values('Data_Original')
                
                # Mini-KPIs do Aluno
                ka, kb, kc, kd = st.columns(4)
                ka.metric("Status", dados_aluno['Situacao_Final'])
                kb.metric("Nota", f"{dados_aluno['Nota_Final']:.1f}")
                kc.metric("Presença", f"{dados_aluno['Score_Presenca']:.0%}")
                kd.metric("Tarefas", f"{dados_aluno['Score_Homework']:.0%}")
                
                st.divider()
                
                # Gráfico de Evolução Individual
                st.subheader(f"Histórico: {aluno}")
                hist_melt = historico.melt(id_vars=['Data_Original'], value_vars=['Score_Presenca', 'Score_Homework'], 
                                         var_name='Indicador', value_name='Valor')
                
                fig_hist = px.bar(hist_melt, x='Data_Original', y='Valor', color='Indicador', barmode='group',
                                  height=400)
                fig_hist.update_layout(xaxis_title="Data da Aula", yaxis_title="Pontuação (0-1)")
                st.plotly_chart(fig_hist, use_container_width=True)
                st.markdown('<div class="tech-note">Análise Intra-Indivíduo (Within): Mostra a consistência do esforço ao longo do tempo.</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

else:
    # Tela de Boas-Vindas Limpa
    st.info("👈 Comece carregando a planilha Excel na barra lateral.")
    st.markdown("""
    <div class="dashboard-card">
        <h3>Bem-vindo ao Sistema de Retenção</h3>
        <p>Esta ferramenta transforma listas de chamadas em inteligência estratégica.</p>
        <ul>
            <li><b>Diagnóstico:</b> Entenda a saúde geral da turma.</li>
            <li><b>Ação:</b> Identifique alunos 'Turistas' ou em 'Risco Crítico'.</li>
            <li><b>Individual:</b> Analise o histórico detalhado para reuniões de pais.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
