"""Verificações da segunda fase sobre registros coerentes com o cubo."""

import unittest
import hashlib
import json

import numpy as np
import pandas as pd

from analise_cohorts import CriteriosElegibilidade, analisar_cubo
from avaliacao_features import CriteriosFeature, avaliar_features
from test_analise_cohorts import TOTALIZADO, cubo_exemplo


def base_individual_do_cubo(cubo):
    dimensoes = ["faixa", "origem", "safra", "amostra"]
    atomico = cubo.loc[cubo[dimensoes].ne(TOTALIZADO).all(axis=1)]
    linhas = []
    for linha in atomico.itertuples(index=False):
        perfil = dict(zip(cubo.columns, linha))
        target = ([1.0] * perfil["maus"]
                  + [0.0] * (perfil["perf"] - perfil["maus"])
                  + [np.nan] * (perfil["total"] - perfil["perf"]))
        for mau in target:
            linhas.append({**{c: perfil[c] for c in dimensoes}, "mau": mau,
                           "sinal": 0.0 if pd.isna(mau) else mau,
                           "classe": "alto" if mau == 1 else "baixo",
                           "constante": 1.0})
    return pd.DataFrame(linhas)


class AvaliacaoFeaturesTest(unittest.TestCase):
    def setUp(self):
        self.cubo = cubo_exemplo(com_amostra=True)
        self.diagnostico = analisar_cubo(
            self.cubo, col_safra="safra", col_amostra="amostra",
            marcador_total=TOTALIZADO,
            criterios=CriteriosElegibilidade(20, 15, 5, 2, 0.8))
        self.dados = base_individual_do_cubo(self.cubo)
        self.criterios = CriteriosFeature(
            minimo_avaliavel=30, minimo_bons=15, minimo_maus=2,
            cobertura_minima=0.8, auc_ci_inferior_min=0.55,
            iv_minimo_categorica=0.02)
        grupos = self.diagnostico.cohort_detail.loc[
            self.diagnostico.cohort_detail.combination_id.eq(1)]
        self.catalogo = {
            "catalog_version": "teste-v1",
            "input_hash": self.diagnostico.input_hash,
            "primary_combination_id": 1,
            "supplementary_combination_ids": [],
            "cohorts": [{"combination_id": 1, "cohort_key": chave}
                        for chave in grupos.cohort_key],
        }
        self.catalogo["catalog_hash"] = hashlib.sha256(json.dumps(
            self.catalogo, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def test_auc_iv_categorica_e_constante(self):
        r = avaliar_features(self.dados, self.diagnostico,
            ["sinal", "classe", "constante"], catalogo=self.catalogo,
            combinacoes=[1],
            criterios=self.criterios)
        self.assertEqual(len(r.feature_summary), 3)
        resumo = r.feature_summary.set_index("feature")
        self.assertTrue(resumo.loc["sinal", "passa_todos_grupos"])
        self.assertAlmostEqual(resumo.loc["sinal", "auc_min"], 1)
        self.assertTrue(resumo.loc["classe", "passa_todos_grupos"])
        self.assertGreater(resumo.loc["classe", "iv_limite_inf_min"], 0)
        self.assertFalse(resumo.loc["constante", "passa_todos_grupos"])
        self.assertTrue(pd.isna(resumo.loc["constante", "auc_min"]))
        self.assertEqual(len(r.feature_temporal), 3 * 2 * 2 * 3)

    def test_base_de_features_precisa_conciliar_com_cubo(self):
        errado = self.dados.iloc[1:].copy()
        with self.assertRaisesRegex(ValueError, "difere do cubo"):
            avaliar_features(errado, self.diagnostico, ["sinal"],
                             catalogo=self.catalogo, combinacoes=[1],
                             criterios=self.criterios)

    def test_exige_catalogo_valido(self):
        with self.assertRaisesRegex(ValueError, "catálogo congelado"):
            avaliar_features(self.dados, self.diagnostico, ["sinal"],
                             criterios=self.criterios)
        alterado = dict(self.catalogo, primary_combination_id=2)
        with self.assertRaisesRegex(ValueError, "Hash do catálogo"):
            avaliar_features(self.dados, self.diagnostico, ["sinal"],
                             catalogo=alterado, criterios=self.criterios)


if __name__ == "__main__":
    unittest.main()
