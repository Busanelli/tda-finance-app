import streamlit as st
import pandas as pd
from src.analysis import (
    compute_log_returns,
    analyze_asset,
)

from src.data import (
    normalizar_ticker,
    baixar_historico,
    validar_observacoes,
    obter_periodo_comum,
    recortar_periodo,
)

from src.visualization import (
    plot_topology_volatility,
    build_summary_table,
)

st.set_page_config(
    page_title="TDA Finance App",
    layout="wide",
)

st.title("TDA Finance App")


# -----------------------------
# Estado da seleção
# -----------------------------

if "ativos" not in st.session_state:
    st.session_state.ativos = []

if "selecao_concluida" not in st.session_state:
    st.session_state.selecao_concluida = False

if not st.session_state.selecao_concluida:

    # -----------------------------
    # Entrada
    # -----------------------------

    with st.form("form_ticker", clear_on_submit=False):

        entrada = st.text_input(
            "Digite o ticker do ativo",
            placeholder="Ex.: PETR4.SA, AAPL, BTC-USD",
        )

        adicionar = st.form_submit_button("Adicionar")


    if adicionar:

        if len(st.session_state.ativos) >= 4:
            st.warning("Limite de 4 ativos atingido.")

        else:
            ticker = normalizar_ticker(entrada)

            if ticker is None:
                st.error(
                    "Ativo não identificado. "
                    "Verifique o ticker no Yahoo Finance e tente novamente."
                )

            elif ticker in st.session_state.ativos:
                st.info("Esse ativo já foi adicionado.")

            else:
                st.session_state.ativos.append(ticker)
                st.rerun()


    # -----------------------------
    # Ativos selecionados
    # -----------------------------

    if st.session_state.ativos:

        st.subheader("Ativos selecionados")

        for ticker in st.session_state.ativos:

            col_ticker, col_remover = st.columns([8, 1])

            with col_ticker:
                st.write(ticker)

            with col_remover:
                if st.button("×", key=f"remover_{ticker}"):
                    st.session_state.ativos.remove(ticker)
                    st.rerun()

# -----------------------------
# Concluir Seleção
# -----------------------------
if not st.session_state.selecao_concluida:
    if st.session_state.ativos:
    
        if st.button("Concluir seleção", type="primary"):
        
            dados = {}
    
            with st.spinner("Carregando dados dos ativos..."):
            
                for ticker in st.session_state.ativos:
                    df = baixar_historico(ticker)
    
                    if df is not None:
                        dados[ticker] = df
    
                periodo_comum = obter_periodo_comum(dados)
    
            if periodo_comum is None:
                st.error(
                    "Não há período comum entre os ativos selecionados. "
                    "Remova ou substitua um ativo para continuar."
                )
    
            else:
                st.session_state.dados = dados
                st.session_state.periodo_comum = periodo_comum
                st.session_state.selecao_concluida = True
                st.rerun()

# -----------------------------
# Limpar interface
# -----------------------------

if st.session_state.selecao_concluida:

    st.write(
        "**Ativos selecionados:** "
        + ", ".join(st.session_state.ativos)
    )

    if st.button("Alterar seleção"):

        st.session_state.selecao_concluida = False

        st.session_state.pop("dados", None)
        st.session_state.pop("periodo_comum", None)
        st.session_state.pop("periodo_selecionado", None)

        st.rerun()

periodo_valido = False

# -----------------------------
# Selecionar o período
# -----------------------------

if "periodo_comum" in st.session_state:

    dados = st.session_state.dados
    inicio_comum, fim_comum = st.session_state.periodo_comum

    st.write(
    f"**Período disponível em comum:** "
    f"{inicio_comum.strftime('%m/%Y')} — "
    f"{fim_comum.strftime('%m/%Y')}"
)

    st.divider()

    dados = st.session_state.dados
    inicio_comum, fim_comum = st.session_state.periodo_comum

    # Verifica se o histórico comum inteiro possui
    # observações suficientes para todos os ativos
    historico_comum_valido = True

    for ticker, df in dados.items():

        df_comum = recortar_periodo(
            df,
            inicio_comum,
            fim_comum,
        )

        n_obs, valido = validar_observacoes(df_comum)

        if not valido:
            historico_comum_valido = False

    if not historico_comum_valido:

        st.error(
            "Histórico comum insuficiente para análise."
        )

    else:

        st.write("### Selecione o período para análise")

        st.caption(
            "Recomenda-se um intervalo de pelo menos 2 anos. "
            "Dependendo do calendário do ativo, pode ser necessário "
            "ampliar o período."
        )

        # Cria uma opção para cada mês existente
        meses = pd.date_range(
            start=inicio_comum.to_period("M").to_timestamp(),
            end=fim_comum.to_period("M").to_timestamp(),
            freq="MS",
        )

        # Valor inicial: últimos 10 anos ou todo o período,
        # caso haja menos de 10 anos disponíveis
        if len(meses) > 121:
            inicio_padrao = meses[-121]
        else:
            inicio_padrao = meses[0]

        fim_padrao = meses[-1]

        inicio_selecionado, fim_selecionado = st.select_slider(
            "Período",
            options=meses,
            value=(inicio_padrao, fim_padrao),
            format_func=lambda data: data.strftime("%m/%Y"),
        )

        # Considera os meses completos
        inicio_real = inicio_selecionado.to_period("M").start_time
        fim_real = fim_selecionado.to_period("M").end_time

        # Duração aproximada em meses
        duracao_meses = (
            (fim_selecionado.year - inicio_selecionado.year) * 12
            + fim_selecionado.month
            - inicio_selecionado.month
            )

        periodo_valido = True

        # Máximo de 10 anos
        if duracao_meses > 120:
            st.warning(
                "O período selecionado não pode ultrapassar 10 anos."
            )
            periodo_valido = False

        # Menos de 2 anos: aviso, não é a trava real
        elif duracao_meses < 24:
            st.warning(
                "Recomenda-se selecionar pelo menos 2 anos de histórico."
            )

        # Validação real: 504 observações por ativo
        observacoes_insuficientes = []

        for ticker, df in dados.items():

            df_periodo = recortar_periodo(
                df,
                inicio_real,
                fim_real,
            )

            n_obs, valido = validar_observacoes(df_periodo)

            if not valido:
                observacoes_insuficientes.append(
                    (ticker, n_obs)
                )

        if observacoes_insuficientes:

            periodo_valido = False

            st.error(
                "Período insuficiente para análise. "
                "Amplie o intervalo selecionado para continuar."
            )

            for ticker, n_obs in observacoes_insuficientes:
                st.write(
                    f"**{ticker}:** {n_obs} observações válidas "
                    f"(mínimo: 504)"
                )

        if periodo_valido:

            st.session_state.periodo_selecionado = (
                inicio_real,
                fim_real,
            )

            st.write(
                f"**Período selecionado:** "
                f"{inicio_selecionado.strftime('%m/%Y')} — "
                f"{fim_selecionado.strftime('%m/%Y')}"
            )


# -----------------------------
# Executar análise
# -----------------------------

if periodo_valido:

    st.session_state.periodo_selecionado = (
        inicio_real,
        fim_real,
    )

    st.write(
        f"**Período selecionado:** "
        f"{inicio_selecionado.strftime('%m/%Y')} — "
        f"{fim_selecionado.strftime('%m/%Y')}"
    )

    if st.button("Executar análise", type="primary"):

        resultados = {}

        for ticker in st.session_state.ativos:

            with st.spinner(f"Analisando {ticker}..."):

                df = dados[ticker]

                df_periodo = recortar_periodo(
                    df,
                    inicio_real,
                    fim_real,
                )

                retornos = compute_log_returns(
                    df_periodo["Adj Close"]
                ).squeeze()

                resultados[ticker] = analyze_asset(
                    returns=retornos,
                    asset=ticker,
                )

        st.session_state.resultados = resultados

        st.success("Análise concluída.")

# -----------------------------
# Exibir dados
# -----------------------------

if "resultados" in st.session_state:

    resultados = st.session_state.resultados

    for ticker, analise in resultados.items():

        fig = plot_topology_volatility(
            results=analise["results"],
            asset=ticker,
        )

        st.pyplot(fig)

    tabela = build_summary_table(resultados)

    st.subheader("Resumo da análise")
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
    )

    with st.expander("Como interpretar estes resultados?"):

        st.markdown(
            """
            - **$TP_{H_1}$ padronizado:** representa a evolução da persistência
              das estruturas topológicas identificadas nas janelas da série.

            - **Volatilidade padronizada:** representa a intensidade das
              variações dos retornos no mesmo período.

            - **Spearman ρ**: indica a direção e a intensidade da associação monotônica entre $TP_{H_1}$ e volatilidade. Valores próximos de +1 indicam associação positiva forte, próximos de −1 indicam associação negativa forte e próximos de 0 indicam pouca ou nenhuma associação monotônica.

            - **p-value**: indica a evidência estatística associada ao coeficiente de Spearman. Valores menores sugerem maior evidência contra a hipótese de ausência de associação monotônica.

            - **τ e m:** são os parâmetros utilizados na reconstrução do
              espaço de estados por embedding de Takens.

            As séries são padronizadas apenas para facilitar a comparação visual.
            
            Correlação não implica causalidade.
            """
        )  