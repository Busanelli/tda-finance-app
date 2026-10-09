import numpy as np
import pandas as pd

from statsmodels.tsa.stattools import acf
from sklearn.metrics import mutual_info_score
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.neighbors import NearestNeighbors
from gtda.time_series import SingleTakensEmbedding
from gtda.homology import VietorisRipsPersistence
from scipy.stats import spearmanr

def compute_log_returns(prices):
    """
    Calcula retornos logarítmicos a partir dos preços.

    Fórmula:
        r_t = log(P_t / P_{t-1})
    """
    log_returns = np.log(prices / prices.shift(1))
    log_returns = log_returns.dropna(how="all")
    log_returns.index.name = "Date"

    return log_returns


def standardize_values(values):
    """
 Padroniza uma série por z-score, usada apenas na estimação dos parâmetros.
    """
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]

    if len(values) == 0:
        raise ValueError("Série vazia após remoção de NaN.")

    std = values.std(ddof=0)

    if std == 0:
        raise ValueError("Série com desvio-padrão zero.")

    return (values - values.mean()) / std


def compute_ami_curve(values, max_lag, n_bins=10):
    """
    Calcula a curva de informação mútua aproximada para diferentes lags.

    Antes do cálculo, a série contínua é discretizada em bins por quantis.
    """
    values = standardize_values(values)

    discretizer = KBinsDiscretizer(
        n_bins=n_bins,
        encode="ordinal",
        strategy="quantile",
    )

    discrete_values = discretizer.fit_transform(
        values.reshape(-1, 1)
    ).astype(int).ravel()

    records = []

    for lag in range(1, max_lag + 1):
        x = discrete_values[:-lag]
        y = discrete_values[lag:]

        ami = mutual_info_score(x, y)

        records.append(
            {
                "lag": lag,
                "ami": ami,
            }
        )

    return pd.DataFrame(records)


def find_first_local_minimum(curve_df, value_column):
    """
Retorna o primeiro mínimo local de uma curva.

Caso não exista mínimo local, usa o mínimo global como fallback.
    """
    values = curve_df[value_column].to_numpy()
    lags = curve_df["lag"].to_numpy()

    for i in range(1, len(values) - 1):
        previous_value = values[i - 1]
        current_value = values[i]
        next_value = values[i + 1]

        if current_value < previous_value and current_value < next_value:
            return int(lags[i]), "first_local_minimum"

    min_index = int(np.argmin(values))

    return int(lags[min_index]), "global_minimum_fallback"


def compute_acf_curve(values, max_lag):
    """
    Calcula a função de autocorrelação (ACF) para diferentes lags.
    """
    values = standardize_values(values)

    acf_values = acf(
        values,
        nlags=max_lag,
        fft=True,
        missing="raise",
    )

    records = []

    for lag in range(1, max_lag + 1):
        records.append(
            {
                "lag": lag,
                "acf": acf_values[lag],
            }
        )

    return pd.DataFrame(records)


def find_first_acf_below_threshold(acf_df, threshold=1 / np.e):
    """
    Retorna o primeiro lag em que a ACF fica abaixo do limiar.

    Caso nenhum lag satisfaça o critério, usa o menor valor de ACF como fallback.
    """
    below_threshold = acf_df[acf_df["acf"] <= threshold]

    if not below_threshold.empty:
        lag = below_threshold.iloc[0]["lag"]
        return int(lag), "first_below_threshold"

    min_index = acf_df["acf"].idxmin()
    lag = acf_df.loc[min_index, "lag"]

    return int(lag), "minimum_acf_fallback"


def takens_embedding(values, tau, dimension):
    """
    Cria uma matriz de embedding de Takens.

    Cada linha contém os valores [x_t, x_{t+tau}, ..., x_{t+(m-1)tau}].
    """
    values = np.asarray(values, dtype=float)

    n_vectors = len(values) - (dimension - 1) * tau

    if n_vectors <= 1:
        raise ValueError(
            "Série curta demais para o tau e a dimensão informados."
        )

    embedded = np.empty((n_vectors, dimension))

    for j in range(dimension):
        embedded[:, j] = values[j * tau: j * tau + n_vectors]

    return embedded


def false_nearest_neighbors_ratio(
    values,
    tau,
    dimension,
    rtol=10.0,
    atol=2.0,
):
    """
    Calcula a proporção de falsos vizinhos para uma dimensão.

    Compara os embeddings nas dimensões m e m+1.
    """
    values = standardize_values(values)

    embedding_m = takens_embedding(values, tau=tau, dimension=dimension)
    embedding_m1 = takens_embedding(values, tau=tau, dimension=dimension + 1)

    n_valid = embedding_m1.shape[0]
    embedding_m = embedding_m[:n_valid]

    if n_valid < 3:
        raise ValueError("Poucos pontos para calcular FNN.")

    nearest_neighbors = NearestNeighbors(n_neighbors=2)
    nearest_neighbors.fit(embedding_m)

    distances, indices = nearest_neighbors.kneighbors(embedding_m)

    nearest_distance_m = distances[:, 1]
    nearest_index = indices[:, 1]

    extra_coordinate_current = values[dimension * tau: dimension * tau + n_valid]
    extra_coordinate_neighbor = extra_coordinate_current[nearest_index]

    extra_distance = np.abs(
        extra_coordinate_current - extra_coordinate_neighbor
    )

    epsilon = 1e-12
    ratio_test = extra_distance / (nearest_distance_m + epsilon)

    distance_m1 = np.sqrt(nearest_distance_m ** 2 + extra_distance ** 2)

    false_neighbors = (
        (ratio_test > rtol)
        | (distance_m1 > atol)
    )

    return false_neighbors.mean()


def compute_fnn_curve(
    values,
    tau,
    min_dimension,
    max_dimension,
    threshold,
    rtol=10.0,
    atol=2.0,
):
    """
    Calcula a curva de falsos vizinhos (FNN) para diferentes dimensões de embedding.
    """
    records = []

    for dimension in range(min_dimension, max_dimension + 1):
        fnn_ratio = false_nearest_neighbors_ratio(
            values=values,
            tau=tau,
            dimension=dimension,
            rtol=rtol,
            atol=atol,
        )

        records.append(
            {
                "dimension": dimension,
                "fnn_ratio": fnn_ratio,
                "threshold": threshold,
            }
        )

    return pd.DataFrame(records)


def select_embedding_dimension(fnn_df, threshold):
    """
    Seleciona a dimensão de embedding a partir da curva FNN.

    Usa a primeira dimensão abaixo do limiar. Se o limiar não for atingido,
    usa o primeiro mínimo local; se necessário, recorre ao mínimo global.
    """
    below_threshold = fnn_df[fnn_df["fnn_ratio"] <= threshold]

    if not below_threshold.empty:
        dimension = below_threshold.iloc[0]["dimension"]
        return int(dimension), "first_below_threshold"

    values = fnn_df["fnn_ratio"].to_numpy()
    dimensions = fnn_df["dimension"].to_numpy()

    for i in range(1, len(values) - 1):
        previous_value = values[i - 1]
        current_value = values[i]
        next_value = values[i + 1]

        if current_value < previous_value and current_value < next_value:
            return int(dimensions[i]), "first_local_minimum"

    min_index = fnn_df["fnn_ratio"].idxmin()
    dimension = fnn_df.loc[min_index, "dimension"]

    return int(dimension), "global_minimum_fallback"


def estimate_parameters_for_asset(
    series,
    asset,
    max_lag,
    min_dimension,
    max_dimension,
    fnn_threshold,
    n_bins=10,
):
    """
    Estima tau e m para um ativo.

    Retorna os parâmetros finais e as curvas AMI, ACF e FNN usadas na estimação.
    """
    values = standardize_values(series.to_numpy(dtype=float))

    ami_df = compute_ami_curve(
        values=values,
        max_lag=max_lag,
        n_bins=n_bins,
    )
    tau_ami, tau_ami_rule = find_first_local_minimum(
        curve_df=ami_df,
        value_column="ami",
    )

    acf_df = compute_acf_curve(
        values=values,
        max_lag=max_lag,
    )
    tau_acf, tau_acf_rule = find_first_acf_below_threshold(acf_df)

    tau_final = tau_ami
    tau_final_rule = tau_ami_rule

    fnn_df = compute_fnn_curve(
        values=values,
        tau=tau_final,
        min_dimension=min_dimension,
        max_dimension=max_dimension,
        threshold=fnn_threshold,
    )
    m_fnn, m_fnn_rule = select_embedding_dimension(
        fnn_df=fnn_df,
        threshold=fnn_threshold,
    )

    m_final = m_fnn
    m_final_rule = m_fnn_rule

    ami_df.insert(0, "asset", asset)
    acf_df.insert(0, "asset", asset)
    fnn_df.insert(0, "asset", asset)

    parameter_record = {
        "asset": asset,
        "n_obs": len(values),

        "tau_ami": tau_ami,
        "tau_ami_rule": tau_ami_rule,

        "tau_acf": tau_acf,
        "tau_acf_rule": tau_acf_rule,

        "tau_final": tau_final,
        "tau_final_rule": tau_final_rule,

        "m_fnn": m_fnn,
        "m_fnn_rule": m_fnn_rule,

        "m_final": m_final,
        "m_final_rule": m_final_rule,

        "max_lag": max_lag,
        "min_dimension": min_dimension,
        "max_dimension": max_dimension,
        "fnn_threshold": fnn_threshold,
        "ami_n_bins": n_bins,
    }

    return parameter_record, ami_df, acf_df, fnn_df


def create_windows(series, window_size=60, step_size=5):
    """
    Cria janelas móveis normalizadas por z-score.

    Retorna uma lista de dicionários contendo:
    - window_id
    - reference_date
    - values
    """
    series = series.dropna()

    windows = []

    window_id = 0

    for start in range(
        0,
        len(series) - window_size + 1,
        step_size,
    ):
        end = start + window_size

        window = series.iloc[start:end]

        values = window.to_numpy(dtype=float)

        std = values.std(ddof=0)

        if std == 0:
            continue

        values_normalized = (
            values - values.mean()
        ) / std

        windows.append(
            {
                "window_id": window_id,
                "reference_date": window.index[-1],
                "values": values_normalized,
            }
        )

        window_id += 1

    return windows


def compute_persistence_diagram(
    values,
    tau,
    dimension,
):
    """
    Aplica embedding de Takens e calcula
    o diagrama de persistência em H1.
    """

    embedder = SingleTakensEmbedding(
        parameters_type="fixed",
        time_delay=tau,
        dimension=dimension,
        stride=1,
    )

    point_cloud = embedder.fit_transform(values)

    persistence = VietorisRipsPersistence(
        homology_dimensions=[1],
        n_jobs=-1,
    )

    diagram = persistence.fit_transform(
        point_cloud[np.newaxis, :, :]
    )[0]

    return diagram

def extract_tp_h1(diagram):
    """
    Calcula a persistência total em H1.
    """

    h1 = diagram[diagram[:, 2] == 1]

    if len(h1) == 0:
        return 0.0

    births = h1[:, 0]
    deaths = h1[:, 1]

    valid = (
        np.isfinite(births)
        & np.isfinite(deaths)
        & (deaths > births)
    )

    if not valid.any():
        return 0.0

    return float(
        (deaths[valid] - births[valid]).sum()
    )

def compute_tp_h1_series(
    series,
    tau,
    dimension,
    window_size=60,
    step_size=5,
):
    """
    Calcula a série temporal de TP_H1 para um ativo.
    """

    windows = create_windows(
        series,
        window_size=window_size,
        step_size=step_size,
    )

    records = []

    for window in windows:

        diagram = compute_persistence_diagram(
            values=window["values"],
            tau=tau,
            dimension=dimension,
        )

        tp_h1 = extract_tp_h1(diagram)

        records.append(
            {
                "window_id": window["window_id"],
                "reference_date": window["reference_date"],
                "tp_h1": tp_h1,
            }
        )

    return pd.DataFrame(records)

def compute_volatility_series(
    series,
    window_size=60,
    step_size=5,
):
    """
    Calcula a volatilidade dos retornos nas mesmas
    janelas usadas para TP_H1.
    """
    series = series.dropna()

    records = []

    window_id = 0

    for start in range(
        0,
        len(series) - window_size + 1,
        step_size,
    ):
        end = start + window_size

        window = series.iloc[start:end]

        volatility = float(window.std())

        records.append(
            {
                "window_id": window_id,
                "reference_date": window.index[-1],
                "volatility": volatility,
            }
        )

        window_id += 1

    return pd.DataFrame(records)

def align_topology_volatility(
    topology_df,
    volatility_df,
):
    """
    Alinha TP_H1 e volatilidade por janela e data de referência.
    """
    aligned = topology_df.merge(
        volatility_df,
        on=["window_id", "reference_date"],
        how="inner",
        validate="one_to_one",
    )

    aligned = aligned.dropna(
        subset=["tp_h1", "volatility"]
    )

    return aligned

def compute_spearman(aligned_df):
    """
    Calcula a correlação de Spearman entre
    TP_H1 e volatilidade.

    Retorna rho e p-value.
    """
    if len(aligned_df) < 2:
        raise ValueError(
            "Observações insuficientes para calcular Spearman."
        )

    rho, p_value = spearmanr(
        aligned_df["tp_h1"],
        aligned_df["volatility"],
    )

    return float(rho), float(p_value)

def analyze_asset(
    returns,
    asset,
    max_lag=15,
    min_dimension=2,
    max_dimension=6,
    fnn_threshold=0.01,
    n_bins=10,
    window_size=60,
    step_size=5,
):
    """
    Executa o pipeline completo de análise para um ativo.

    Retorna:
        tau;
        dimensão de embedding;
        série alinhada de TP_H1 e volatilidade;
        rho de Spearman;
        p-value.
    """

    parametros, _, _, _ = estimate_parameters_for_asset(
        series=returns,
        asset=asset,
        max_lag=max_lag,
        min_dimension=min_dimension,
        max_dimension=max_dimension,
        fnn_threshold=fnn_threshold,
        n_bins=n_bins,
    )

    tau = parametros["tau_final"]
    m = parametros["m_final"]

    topologia = compute_tp_h1_series(
        series=returns,
        tau=tau,
        dimension=m,
        window_size=window_size,
        step_size=step_size,
    )

    volatilidade = compute_volatility_series(
        series=returns,
        window_size=window_size,
        step_size=step_size,
    )

    resultado = align_topology_volatility(
        topology_df=topologia,
        volatility_df=volatilidade,
    )

    rho, p_value = compute_spearman(resultado)

    return {
        "tau": tau,
        "m": m,
        "results": resultado,
        "rho": rho,
        "p_value": p_value,
    }