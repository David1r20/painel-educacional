
🎓 Sistema de Inteligência Educacional: Análise de Dados em Painel
> Projeto Acadêmico de Análise Quantitativa e Monitoramento de Retenção Escolar.
> 
Este projeto aplica metodologias de Dados Longitudinais (Panel Data) e Econometria para analisar o desempenho de alunos, identificar riscos de evasão e mensurar o impacto causal de variáveis comportamentais (Presença, Lição de Casa e Participação) sobre o resultado final.

📋 Sobre o Projeto
O objetivo deste software é transformar dados brutos de diários de classe (formato Excel) em inteligência pedagógica acionável. Diferente de dashboards tradicionais que olham apenas para a média final, este sistema decompõe a variância dos dados em duas dimensões fundamentais da teoria de Painel:
 * Dimensão Transversal (Between): Comparação entre indivíduos (Quem performa melhor?).
 * Dimensão Temporal (Within): Dinâmica intra-indivíduo (Como o esforço varia ao longo do tempo?).
Principais Funcionalidades
 * ETL Automatizado: Conversão de dados Wide Format (planilha padrão) para Long Format (estrutura de painel balanceado).
 * Modelagem Econométrica: Estimação de Pooled OLS e Regressão Logística (Logit) para cálculo de probabilidade de aprovação.
 * Análise de Resíduos: Identificação de alunos com "Dificuldade de Aprendizagem" (nota real muito abaixo da prevista pelo modelo).
 * Gestão de Risco: Segmentação de alunos em clusters (ex: "Turistas" vs "Alunos em Risco Crítico").
 * Dossiê Individual: Visão microanalítica do histórico do aluno.
🛠️ Tecnologias e Bibliotecas
O projeto foi desenvolvido em Python utilizando as seguintes bibliotecas para Ciência de Dados:
 * Streamlit: Framework para construção da aplicação web interativa.
 * Pandas: Manipulação e estruturação do Painel (Data Wrangling).
 * Plotly Express/Graph Objects: Visualização de dados interativa e multivariada.
 * Statsmodels: Cálculos econométricos rigorosos (OLS, Logit, AIC, BIC, P-valor).
 * Scikit-Learn: Métricas de avaliação de modelos e eficiência.
 * OpenPyXL: Leitura robusta de arquivos Excel (.xlsx).
📊 Metodologia Aplicada
1. Estruturação dos Dados
A base original continha 14 colunas de datas (aulas) dispostas horizontalmente. Foi aplicado um algoritmo de melting para empilhar as observações, gerando um dataset onde:

2. Especificação do Modelo (OLS)
Para determinar os vetores de influência na nota final, utilizamos a seguinte especificação linear:
Onde:
 * \beta_x: Coeficientes de impacto marginal (ceteris paribus).
 * \epsilon_{i}: Termo de erro (fatores não observados).
3. Análise de Probabilidade (Logit)
Transformamos a variável dependente em binária (1= Aprovado, 0= Reprovado) para estimar a chance percentual de sucesso de cada aluno:
🚀 Como Executar o Projeto
Pré-requisitos
Certifique-se de ter o Python 3.8+ instalado.
Passo a Passo
 * Clone o repositório:
   git clone https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
cd SEU-REPOSITORIO

 * Instale as dependências:
   Crie um arquivo requirements.txt (se não houver) com o conteúdo abaixo e instale:
   pip install -r requirements.txt

   Conteúdo do requirements.txt:
   streamlit
pandas
plotly
openpyxl
statsmodels
scikit-learn

 * Adicione a Base de Dados:
   Coloque o arquivo Excel na raiz do projeto com o nome:
   Base anonimizada - Eric - PUC-SP.xlsx
   (O sistema carregará automaticamente. Caso tenha outro nome, use o botão de upload na interface).
 * Execute a aplicação:
   streamlit run app.py

 * Acesse:
   O navegador abrirá automaticamente no endereço http://localhost:8501.
📂 Estrutura de Arquivos
📂 painel-educacional
├── 📄 app.py                # Código principal da aplicação (Front & Back)
├── 📄 requirements.txt      # Lista de bibliotecas necessárias
├── 📄 README.md             # Documentação do projeto
└── 📊 Base anonimizada...   # Arquivo de dados (Excel)

📈 Resultados Obtidos (Exemplo)
Com a base de dados de teste, o modelo alcançou:
 * R² (Poder Explicativo): ~73.1%
 * Significância: Todas as variáveis (Presença, Tarefa, Participação) apresentaram P-valor < 0.01.
 * Insight Chave: A variável Participação demonstrou ter o maior coeficiente de impacto (\beta \approx 6.17), indicando que soft skills e interação em sala são preditores mais fortes de sucesso do que apenas a presença física.
