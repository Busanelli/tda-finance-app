import pandas as pd
import matplotlib.pyplot as plt


def standardize_series(series):
    """
    Padroniza uma série por z-score para comparação visual.
    """
    std = series.std()

    if std == 0:
        return series * 0

    return (series - series.mean()) / std


def plot_topology_volatility(results, asset):
    """
    Plota TP_H1 e volatilidade padronizados ao longo do tempo.
    """
    df = results.copy()

    df["tp_h1_z"] = standardize_series(df["tp_h1"])
    df["volatility_z"] = standardize_series(df["volatility"])

    fig, ax = plt.subplots(figsize=(10, 3))

    ax.plot(
        df["reference_date"],
        df["tp_h1_z"],
        label="TP_H1 padronizado",
    )

    ax.plot(
        df["reference_date"],
        df["volatility_z"],
        label="Volatilidade padronizada",
    )

    ax.set_title(asset)
    ax.set_xlabel("Data")
    ax.set_ylabel("Valor padronizado")
    ax.legend()

    fig.tight_layout()

    return fig

def build_summary_table(resultados):
    """
    Cria tabela-resumo dos resultados por ativo.
    """
    records = []

    for asset, analise in resultados.items():
        records.append(
            {
                "Ativo": asset,
                "Spearman ρ": analise["rho"],
                "p-value": analise["p_value"],
                "τ": analise["tau"],
                "m": analise["m"],
            }
        )

    return pd.DataFrame(records)