"""Gerador sintético de registros para a etapa posterior de features.

Este módulo não é importado nem executado pela definição de cohorts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from exemplo_simulado import CONTAGENS, DIMENSOES, simular_perfis_agregados


FEATURES = [
    "bureau_score", "interno_score", "parceiro_score", "score_instavel",
    "historico_atrasos", "renda_estimada", "sinal_canal", "ruido", "constante",
]


def simular_base_features(seed: int = 20261026) -> pd.DataFrame:
    """Gera registros e features com as contagens exatas do cubo simulado."""
    atomico = simular_perfis_agregados(seed)
    rng = np.random.default_rng(seed + 1)
    indices = np.repeat(np.arange(len(atomico)), atomico["qtd_total"].to_numpy())
    base = atomico.iloc[indices][DIMENSOES].reset_index(drop=True)
    n = len(base)
    mau = np.empty(n, dtype=float)
    fim = 0
    for maus, perf, total in atomico[CONTAGENS].itertuples(index=False, name=None):
        inicio = fim
        fim += total
        valores = np.empty(total, dtype=float)
        valores[:maus] = 1
        valores[maus:perf] = 0
        valores[perf:] = np.nan
        rng.shuffle(valores)
        mau[inicio:fim] = valores
    base["mau"] = mau
    base.insert(0, "registro_id", np.arange(1, n + 1))
    taxa_perfil = atomico["qtd_maus"].div(atomico["qtd_performance"]).fillna(0).to_numpy()
    latente = np.where(np.isnan(mau), rng.binomial(1, taxa_perfil[indices]), mau)

    origem_b = base["origem"].eq("B").to_numpy()
    digital = base["canal"].eq("digital").to_numpy()
    rel_sim = base["relacionamento"].eq("sim").to_numpy()
    hist_longo = base["historico"].eq("longo").to_numpy()
    safra_final = base["safra"].eq("2025S1").to_numpy()
    desenvolvimento = base["amostra"].eq("desenvolvimento").to_numpy()

    def com_cobertura(valores: np.ndarray, prob: np.ndarray | float) -> np.ndarray:
        saida = np.asarray(valores, dtype=float).copy()
        saida[rng.random(n) >= prob] = np.nan
        return saida

    base["bureau_score"] = com_cobertura(
        rng.normal(latente * 0.9 + base["exposicao"].eq("alta").to_numpy() * 0.15, 1),
        0.94 - 0.35 * origem_b - 0.08 * safra_final)
    base["interno_score"] = com_cobertura(
        rng.normal(latente * np.where(rel_sim, 1.1, 0.2), 1),
        np.where(rel_sim, 0.96, 0.63))
    base["parceiro_score"] = com_cobertura(
        rng.normal(latente * np.where(origem_b, 1.25, 0.35)
                   * np.where(safra_final, 0.45, 1.0), 1),
        np.where(origem_b, 0.90, 0.48))
    base["score_instavel"] = com_cobertura(
        rng.normal(latente * np.where(desenvolvimento, 1.45, 0.20), 1),
        np.where(safra_final, 0.78, 0.95))
    base["historico_atrasos"] = com_cobertura(
        rng.poisson(0.7 + latente * np.where(hist_longo, 2.0, 0.45)),
        np.where(hist_longo, 0.94, 0.62))
    base["renda_estimada"] = com_cobertura(
        rng.lognormal(mean=10.0 + base["faixa_renda"].map(
            {"baixa": -0.5, "media": 0, "alta": 0.5}).to_numpy() - 0.25 * latente,
            sigma=0.4), 0.91)
    sinal = latente + rng.normal(0, 0.75, n)
    base["sinal_canal"] = pd.Categorical(np.where(
        sinal < 0.25, "baixo", np.where(sinal < 1.1, "medio", "alto")))
    base.loc[rng.random(n) >= np.where(digital, 0.91, 0.68), "sinal_canal"] = np.nan
    base["ruido"] = com_cobertura(rng.normal(0, 1, n), 0.98)
    base["constante"] = 1.0
    return base
