import logging
import yfinance as yf
import pandas as pd

logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def ticker_existe(ticker):
    """
    Verifica se o ticker possui dados disponíveis no Yahoo Finance.
    """
    dados = yf.download(
        ticker,
        period="5d",
        auto_adjust=False,
        progress=False,
    )

    return not dados.empty


def normalizar_ticker(ticker):
    """
    Normaliza e valida um ticker informado pelo usuário.

    Regras:
    - remove espaços nas extremidades;
    - converte para maiúsculas;
    - testa o ticker informado;
    - caso não seja encontrado e não possua sufixo de mercado,
      testa novamente acrescentando '.SA'.

    Retorna:
        ticker válido, se encontrado;
        None, caso contrário.
    """
    ticker = ticker.strip().upper()

    if not ticker:
        return None

    if ticker_existe(ticker):
        return ticker

    if "." not in ticker:
        ticker_sa = f"{ticker}.SA"

        if ticker_existe(ticker_sa):
            return ticker_sa

    return None


def baixar_historico(ticker):
    """
    Baixa todo o histórico disponível do ativo.
    """
    dados = yf.download(
        ticker,
        period="max",
        auto_adjust=False,
        progress=False,
    )

    if dados.empty:
        return None

    return dados


def validar_observacoes(df, coluna="Adj Close", minimo=504):
    """
    Conta as observações válidas e verifica
    se a série atende ao mínimo exigido.

    Retorna:
        quantidade de observações válidas;
        True/False para a validação.
    """
    n_obs = df[coluna].dropna().shape[0]

    return n_obs, n_obs >= minimo


def obter_periodo_disponivel(df):
    """
    Retorna a primeira e a última data disponíveis.
    """
    return df.index.min(), df.index.max()


def obter_periodo_comum(dados):
    """
    Determina o intervalo comum entre os ativos baixados.

    dados deve ser um dicionário no formato:
    {
        "PETR4.SA": df_petr4,
        "AAPL": df_aapl,
    }
    """
    periodos = [
        obter_periodo_disponivel(df)
        for df in dados.values()
    ]

    inicio_comum = max(inicio for inicio, _ in periodos)
    fim_comum = min(fim for _, fim in periodos)

    if inicio_comum > fim_comum:
        return None

    return inicio_comum, fim_comum

def recortar_periodo(df, inicio, fim):
    """
    Recorta o DataFrame para o intervalo informado.

    O início e o fim são considerados inclusivos.
    """
    return df.loc[inicio:fim].copy()


def validar_observacoes(df, coluna="Adj Close", minimo=504):
    """
    Conta as observações válidas e verifica
    se a série atende ao mínimo exigido.
    """
    n_obs = df[coluna].dropna().shape[0]
    return n_obs, n_obs >= minimo


