import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.formula.api as smf
import os

# Configuração inicial da página
st.set_page_config(
    page_title="Dashboard de Performance Acadêmica",
    page_icon="",
    layout="wide"
)

def apply_custom_styles():
    """Aplica CSS customizado para corrigir problemas de contraste do Streamlit."""
    st.markdown("""
        <style>
        /* Card customizado para insights */
        .insight-box {
            background-color: #f8f9fa;
            border-left: 5px solid #2c3e50;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            color: #1f1f1f !important;
            font-family: 'Segoe UI', sans-serif;
        }
        
        .insight-title {
            font-weight: bold;
            font-size: 1.1em;
            color: #2c3e50 !important;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        
        /* Hack para forçar texto preto nas métricas (st.metric) em qualquer tema */
        div[data-testid="stMetric"] {
            background-color: #eef1f6 !important;
            border: 1px solid #dcdcdc;
            color: #000000 !important;
        }
        div[data-testid="stMetricLabel"] p { color: #555555 !important; }
        div[data-testid="stMetricValue"] div { color: #000000 !important; }
        
        /* Esconde indices de tabelas para limpar o visual */
        thead tr th:first-child { display:none }
        tbody th { display:none }
        </style>
    """, unsafe_allow_html=True)

# --- ETL e Processamento de Dados ---
@st.cache_data
def load_data(file_input):
    try:
        # Verifica se é path (string) ou buffer (upload)
        if isinstance(file_input, str):
            fn = pd.read_csv if file_input.endswith('.csv') else pd.read_excel
            df_raw = fn(file_input, header=None)
            if not file_input.endswith('.csv'): 
                df_raw = pd.read_excel(file_input, header=None, engine='openpyxl')
        else:
            fn = pd.read_csv if file_input.name.endswith('.csv') else pd.read_excel
            df_raw = fn(file_input, header=None) if file_input.name.endswith('.csv') else pd.read_excel(file_input, header=None, engine='openpyxl')

        # Procura a linha de cabeçalho real
        header_idx = df_raw[df_raw.apply(lambda x: x.astype(str).str.contains("NOME COMPLETO").any(), axis=1)].index
        
        if header_idx.empty:
            return None, None, "Erro: Cabeçalho não encontrado."
        
        idx = header_idx[0]
        
        # Slicing correto
        df = df_raw.iloc[idx+1:].copy()
        df.columns = df_raw.iloc[idx]
        
        # 1. Tratamento Cross-Section (Estático)
        cols_target = ['Sala', 'NOME COMPLETO', 'Nota Final', 'Situação Final']
        cols_found = [c for c in df.columns if str(c) in cols_target]
        
        df_cross = df[cols_found].copy().rename(columns={
            'NOME COMPLETO': 'Aluno', 'Nota Final': 'Y_Nota', 'Situação Final': 'Status'
        })
        
        # Limpeza básica
        df_cross['Y_Nota'] = pd.to_numeric(df_cross['Y_Nota'], errors='coerce')
        df_cross = df_cross.dropna(subset=['Y_Nota', 'Aluno'])

        # 2. Tratamento Painel (Dinâmico) - Onde a mágica acontece
        panel_list = []
        
        # Mapeamentos de regras de negócio
        rules = {
            'presenca': {'P': 1.0, '1/2': 0.5, 'A': 0.0, 'F': 0.0},
            'hw': {'√': 1.0, '+/-': 0.5, 'N': 0.0},
            'part': {':-D': 1.0, ':-)': 1.0, ':-/': 0.5, ':-&': 0.0, ':-(': 0.0, 'nan': 0.0}
        }

        # Itera colunas buscando blocos de aula
        for i, col in enumerate(df.columns):
            if str(col).strip() == 'P': # Anchor column
                # Tenta pegar o nome da aula na linha acima do header
                aula_name = df_raw.iloc[idx-1, i] if idx > 0 else f"Aula_{i}"
                if pd.isna(aula_name): aula_name = f"Semana_{(i//5)+1}"
                
                # Extrai o bloco de 5 colunas da semana
                chunk = df.iloc[:, i-1:i+4].copy()
                chunk.columns = ['Pre_Class', 'Presenca', 'Homework', 'Participacao', 'Comportamento']
                chunk['Aluno'] = df['NOME COMPLETO']
                chunk['Tempo'] = str(aula_name).strip()
                panel_list.append(chunk)

        df_panel = pd.concat(panel_list, ignore_index=True)
        
        # Aplica as regras numéricas
        df_panel['X_Presenca'] = df_panel['Presenca'].map(rules['presenca']).fillna(0)
        df_panel['X_Homework'] = df_panel['Homework'].map(rules['hw']).fillna(0)
        df_panel['X_Participacao'] = df_panel['Participacao'].astype(str).str.strip().map(rules['part']).fillna(0)
        
        # Join final para ter Y no painel
        df_full = pd.merge(df_panel, df_cross[['Aluno', 'Y_Nota', 'Status']], on='Aluno', how='inner')
        
        return df_cross, df_full, None

    except Exception as e:
        return None, None, f"Exception no parser: {str(e)}"

# --- Main App ---
if __name__ == "__main__":
    apply_custom_styles()
    
    # Setup de carregamento
    DEFAULT_FILE = "Base anonimizada - Eric - PUC-SP.xlsx"
    df_alunos, df_painel = None, None
    
    # Tenta carregar local primeiro (dev mode)
    if os.path.exists(DEFAULT_FILE):
        df_alunos, df_painel, err = load_data(DEFAULT_FILE)
        if err: 
            st.error(err)
        else:
            st.sidebar.success(f"Carregado: {DEFAULT_FILE}")
            
    # Fallback para upload
    if df_alunos is None:
        uploaded = st.sidebar.file_uploader("Selecione a planilha", type=['xlsx', 'csv'])
        if uploaded:
            df_alunos, df_painel, err = load_data(uploaded)

    # Renderiza UI se tiver dados
    st.title("📊 Análise de Performance: Fatores de Sucesso")
    st.markdown("---")

    if df_alunos is not None:
        # KPIs Topo
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("N (Alunos)", len(df_alunos))
        col2.metric("Média Nota (Y)", f"{df_alunos['Y_Nota'].mean():.1f}")
        col3.metric("Presença Média", f"{df_painel['X_Presenca'].mean():.0%}")
        col4.metric("Engajamento Médio", f"{df_painel['X_Participacao'].mean():.0%}")

        tabs = st.tabs(["Painel (Evolução)", "Análise Estatística", "Simulador (What-If)"])

        # Tab 1: Visão Temporal
        with tabs[0]:
            st.markdown("""
            <div class="insight-box">
                <div class="insight-title">Análise Longitudinal</div>
                Visualização da consistência do aluno ao longo do tempo. Alunos com alta variância nas entregas tendem a ter menor desempenho final.
            </div>
            """, unsafe_allow_html=True)
            
            # Agregações para o gráfico
            timeline = df_painel.groupby('Tempo')[['X_Participacao', 'X_Homework']].mean().reset_index()
            
            sel_aluno = st.selectbox("Filtrar Aluno:", sorted(df_painel['Aluno'].unique()))
            df_filtered = df_painel[df_painel['Aluno'] == sel_aluno]
            
            fig = go.Figure()
            # Média da turma (benchmark)
            fig.add_trace(go.Scatter(
                x=timeline['Tempo'], y=timeline['X_Participacao'], 
                name='Média Turma', line=dict(color='lightgray', dash='dash')
            ))
            # Aluno selecionado
            fig.add_trace(go.Scatter(
                x=df_filtered['Tempo'], y=df_filtered['X_Participacao'], 
                name='Participação Aluno', line=dict(color='#2c3e50', width=3), mode='lines+markers'
            ))
            # Barras de HW
            fig.add_trace(go.Bar(
                x=df_filtered['Tempo'], y=df_filtered['X_Homework'], 
                name='Entrega Homework', marker_color='#18bc9c', opacity=0.3
            ))
            
            fig.update_layout(title="Cronologia do Engajamento", yaxis_range=[0, 1.2], template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        # Tab 2: Regressão
        with tabs[1]:
            # Feature Engineering: Agrupando por aluno (Between Effects)
            df_model = df_painel.groupby('Aluno').agg({
                'Y_Nota': 'first', 
                'X_Presenca': 'mean', 
                'X_Homework': 'mean', 
                'X_Participacao': 'mean'
            }).reset_index()
            
            # Statsmodels OLS
            model = smf.ols("Y_Nota ~ X_Presenca + X_Homework + X_Participacao", df_model).fit()
            
            # Lógica simples para gerar insight textual
            betas = model.params.drop('Intercept')
            top_factor = betas.idxmax()
            factor_names = {
                'X_Presenca': 'Presença', 
                'X_Homework': 'Entregas (HW)', 
                'X_Participacao': 'Participação Ativa'
            }
            
            st.markdown(f"""
            <div class="insight-box">
                <div class="insight-title">Insights do Modelo</div>
                O modelo explica <b>{model.rsquared:.1%}</b> da variação de notas.<br>
                O fator mais determinante nesta turma é <b>{factor_names.get(top_factor, top_factor)}</b>, 
                adicionando ~{betas[top_factor]:.2f} pontos na nota final para quem mantém 100% de consistência.
            </div>
            """, unsafe_allow_html=True)
            
            c_table, c_chart = st.columns([1, 2])
            
            with c_table:
                st.subheader("Betas (Impacto)")
                res_df = pd.DataFrame({'Coef': model.params, 'P-Valor': model.pvalues})
                
                # Funçãozinha lambda para destacar p-valor < 0.05
                st.dataframe(
                    res_df.style.format("{:.4f}").map(
                        lambda v: 'color: green; font-weight: bold' if v < 0.05 else 'color: gray', 
                        subset=['P-Valor']
                    ), 
                    use_container_width=True
                )
                
            with c_chart:
                st.subheader("Análise de Resíduos")
                df_model['Previsto'] = model.predict(df_model)
                df_model['Residuo'] = df_model['Y_Nota'] - df_model['Previsto']
                
                fig_res = px.scatter(
                    df_model, x='Previsto', y='Residuo', hover_name='Aluno',
                    color='Residuo', color_continuous_scale='RdBu',
                    title="Quem performou fora do padrão?"
                )
                fig_res.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_res, use_container_width=True)

        # Tab 3: Calculadora
        with tabs[2]:
            st.markdown("#### Simulador de Aprovação")
            st.write("Ajuste os parâmetros para prever a nota final com base nos coeficientes históricos.")
            
            col_s1, col_s2, col_s3 = st.columns(3)
            p = col_s1.slider("Presença", 0, 100, 85) / 100
            h = col_s2.slider("Homework", 0, 100, 70) / 100
            part = col_s3.slider("Participação", 0, 100, 50) / 100
            
            # Predict manual usando os params do modelo
            score = (model.params['Intercept'] + 
                     model.params.get('X_Presenca', 0)*p + 
                     model.params.get('X_Homework', 0)*h + 
                     model.params.get('X_Participacao', 0)*part)
            
            st.divider()
            
            # Exibição do resultado
            cols = st.columns([1, 2])
            cols[0].metric("Nota Prevista", f"{score:.2f}")
            
            msg_box = cols[1].empty()
            if score >= 7:
                msg_box.success(" Aprovado com segurança")
            elif score >= 5:
                msg_box.warning(" Zona de Risco (Exame/Recuperação)")
            else:
                msg_box.error(" Risco de Reprovação")

    else:
        st.info("Por favor, carregue a base de dados para iniciar.")

