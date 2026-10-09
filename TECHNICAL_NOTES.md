# Technical Notes

Este documento reúne as principais decisões técnicas do **TDA Finance App**.

Para a fundamentação metodológica completa e discussão dos resultados, consulte:

- [Pipeline completo](https://github.com/Busanelli/tda-finance-pipeline)
- [TCC](https://github.com/Busanelli/tda-finance-pipeline/blob/main/docs/tcc-tda-series-financeiras.pdf)

## Estrutura do projeto

```text
tda-finance-app/
├── app.py
├── README.md
├── TECHNICAL_NOTES.md
├── requirements.txt
└── src/
    ├── data.py
    ├── analysis.py
    └── visualization.py
```
`app.py`: interface e controle do fluxo da aplicação.

`data.py`: download, validação e recorte dos dados.

`analysis.py`: processamento estatístico e topológico.

`visualization.py`: gráficos e tabela de resultados.

## Fluxo da análise
O aplicativo executa, para cada ativo:

preços → retornos logarítmicos → estimação de $\tau$ e $m$ → reconstrução de Takens → janelas móveis → homologia persistente em $H_1$ → $TP_{H_1}$ → volatilidade → correlação de Spearman

Principais parâmetros:

janela = 60 observações

passo = 5 observações

homologia = $H_1$

$\tau$ e $m$ são estimados individualmente para cada ativo utilizando AMI, ACF e FNN.
A volatilidade é calculada a partir dos retornos originais da janela.

As séries de $TP_{H_1}$ e volatilidade são padronizadas exclusivamente para permitir sua comparação visual no mesmo gráfico. O coeficiente de Spearman e seu respectivo p-valor são calculados a partir das séries de $TP_{H_1}$ e volatilidade antes dessa padronização.

## Limites do aplicativo
*Máximo de 4 ativos*

O limite é uma decisão de interface e desempenho.
O objetivo do app é permitir comparação visual rápida, e não substituir o pipeline experimental completo.

*Mínimo de 504 observações*

O aplicativo exige pelo menos 504 observações válidas por ativo no período selecionado.
Esse valor não representa um limiar teórico de AMI, FNN ou homologia persistente.
Foi definido empiricamente durante o desenvolvimento porque, com janela de 60 observações e passo 5, produz aproximadamente 89 janelas de análise, oferecendo densidade temporal suficiente para a proposta visual do aplicativo.
Por isso, a interface recomenda aproximadamente dois anos de histórico, mas a validação real considera o número de observações disponíveis.

*Máximo de 10 anos*

O limite máximo foi adotado para controlar o tempo de processamento e preservar a legibilidade das visualizações.
Não é uma limitação metodológica do pipeline.

*Diferenças em relação ao pipeline completo*

O aplicativo foi deliberadamente simplificado para uso interativo.

A principal diferença é a remoção da análise com surrogates, que no estudo original é utilizada para construir referências de comparação para $TP_{H_1}$.
Essa etapa exige grande quantidade de cálculos adicionais de homologia persistente e não foi incluída no fluxo interativo.

Também foram removidos:
- arquivos intermediários de auditoria;
- geração de tabelas, figuras e arquivos auxiliares utilizados na análise e documentação dos experimentos;
- análises comparativas entre ativos;
- etapas voltadas à reprodução integral do estudo.

Esses recursos permanecem disponíveis no pipeline completo.
## Limitações

O aplicativo deve ser utilizado como ferramenta exploratória.

Os resultados:
- dependem do período selecionado;
- dependem dos parâmetros de reconstrução e janelamento;
- podem variar significativamente entre ativos;
- não estabelecem causalidade;
- não constituem previsão de preços ou recomendação de investimento.

A ausência de surrogates também significa que o aplicativo não realiza a mesma avaliação de referência utilizada no pipeline experimental.

## Execução local
## Execução local

O projeto foi desenvolvido e testado com **Python 3.11**.

Versões mais recentes do Python podem apresentar incompatibilidades com algumas dependências, especialmente `giotto-tda`.

Para executar localmente:

**Linux/macOS**

```bash
python3.11 -m venv .venv_app
source .venv_app/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

**Windows (PowerShell)** 

```powershell
py -3.11 -m venv .venv_app
.venv_app\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
``` 
