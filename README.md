# Painel de Econometria Educacional

> **Live Demo:** [Acesse o App aqui](https://painel-educacional-g2d7h9fdjunsqqrkqblfdg.streamlit.app/)

Projeto desenvolvido para aplicar conceitos de **Dados em Painel**  na gestão escolar. O objetivo é transformar planilhas de chamadas complexas em inteligência de dados, permitindo prever o desempenho do aluno com base em seu comportamento semanal.

## O Problema de Negócio

Professores geralmente têm "planilhas gigantes" onde as colunas crescem infinitamente para a direita (Aula 1, Aula 2, Aula 3...). Isso torna difícil:
1. Visualizar a **tendência** (o aluno está melhorando ou piorando?).
2. Entender o **peso** de cada comportamento (faltar impacta mais a nota do que não entregar lição?).

## A Solução Técnica

O app foi construído em **Python** utilizando **Streamlit** para o front-end. O diferencial técnico está no tratamento dos dados:

1.  **ETL Dinâmico:** O script não usa índices fixos. Ele varre a planilha Excel em busca de padrões (colunas "P" para Presença, "Hw" para Homework) e converte a estrutura de dados de **Wide** (uma linha por aluno, muitas colunas) para **Long/Panel** (várias linhas por aluno, coluna de tempo).
2.  **Econometria (Between Effects):**
    * Como a variável alvo (*Nota Final*) é estática (uma por semestre), não podemos usar Efeitos Fixos tradicionais.
    * Utilizei uma abordagem de regressão sobre as **médias individuais** para estimar os coeficientes ($\beta$) de cada comportamento.
3.  **Simulador:** Uso dos coeficientes treinados (`statsmodels`) para projetar a nota futura com base em inputs do usuário.

##  Stack Tecnológico

* **Front-end:** Streamlit
* **Manipulação de Dados:** Pandas & NumPy
* **Visualização:** Plotly (Interativo)
* **Estatística:** Statsmodels (OLS Regressions)

##  Estrutura do Projeto

* `app.py`: Aplicação principal contendo o ETL, a interface e a modelagem.
* `requirements.txt`: Dependências necessárias para o deploy no Streamlit Cloud.
* `dados/`: Base de dados anonimizada para testes locais.

---
*Projeto de código aberto para fins educacionais.*
