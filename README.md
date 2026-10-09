# TDA Finance App

Explore a dinâmica topológica de séries financeiras de forma simples e visual.

O **TDA Finance App** permite selecionar até quatro ativos, escolher um período de interesse e acompanhar a evolução da **persistência total em H₁ ($TP_{H_1}$)** em comparação com a volatilidade dos retornos.

## Acesse o app

>  **[Abrir TDA Finance App](https://tda-finance-app.streamlit.app/)**

O aplicativo utiliza dados do Yahoo Finance e executa automaticamente o pipeline de análise para os ativos e períodos selecionados.

## O que o app mostra

Para cada ativo, são apresentados:

- evolução temporal de $TP_{H_1}$;
- volatilidade dos retornos;
- comparação visual entre as duas séries padronizadas;
- correlação de Spearman entre $TP_{H_1}$ e volatilidade;
- p-value associado;
- parâmetros $\tau$ e $m$ utilizados na reconstrução do espaço de estados.

O objetivo não é prever preços, mas explorar se mudanças na estrutura topológica das séries apresentam relações com medidas tradicionais de instabilidade financeira.

## Como funciona

O usuário escolhe os ativos e o período de interesse. A partir disso, o app:

**preços → retornos logarítmicos → reconstrução de Takens → janelas temporais → homologia persistente → $TP_{H_1}$ → volatilidade → Spearman**

Os parâmetros de reconstrução são estimados automaticamente para cada ativo.

## Sobre o período de análise

Por se tratar de uma ferramenta visual, o app exige um histórico mínimo de dados para garantir uma leitura temporal útil de $TP_{H_1}$.

Séries muito curtas produzem poucas janelas e tornam a comparação temporal pouco informativa. Por isso, a interface recomenda períodos de pelo menos dois anos e realiza uma validação interna da quantidade de observações disponíveis.

Análises mais curtas, alterações de parâmetros e reproduções mais completas da metodologia podem ser feitas diretamente pelo pipeline do projeto.

## Sobre o projeto

Este aplicativo é uma versão interativa e simplificada de um trabalho desenvolvido com **Análise Topológica de Dados (TDA)** aplicada a séries temporais financeiras.

A proposta desta versão é transformar o pipeline analítico em uma ferramenta exploratória acessível, preservando os principais elementos da metodologia sem reproduzir toda a infraestrutura experimental utilizada no estudo original.

Para detalhes sobre decisões metodológicas, parâmetros e implementação, consulte:

**[TECHNICAL_NOTES.md](TECHNICAL_NOTES.md)**

## Tecnologias

`Python` · `Streamlit` · `pandas` · `NumPy` · `SciPy` · `scikit-learn` · `statsmodels` · `giotto-tda` · `Matplotlib` · `yfinance`