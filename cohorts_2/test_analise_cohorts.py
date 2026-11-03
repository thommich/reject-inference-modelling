"""Testes do contrato do cubo, sem dados individuais."""

from itertools import combinations, product
import unittest

import pandas as pd

from analise_cohorts import CriteriosElegibilidade, analisar_cubo


TOTALIZADO = "<TOTAL>"


def cubo_exemplo(com_safra=True, com_amostra=False):
    dimensoes = ["faixa", "origem"] + (["safra"] if com_safra else []) + (["amostra"] if com_amostra else [])
    linhas = []
    for faixa, origem, safra in product(["baixa", "media", "alta"], ["A", "B"], ["2024", "2025"]):
        n = 100 + 10 * ["baixa", "media", "alta"].index(faixa)
        perf = n - 10
        maus = 5 + 10 * ["baixa", "media", "alta"].index(faixa) + 3 * (origem == "B") + 2 * (safra == "2025")
        linhas.append(dict(faixa=faixa, origem=origem, safra=safra,
                           maus=maus, perf=perf, total=n))
    atomico = pd.DataFrame(linhas)
    if not com_safra:
        atomico = atomico.groupby(["faixa", "origem"], as_index=False)[["maus", "perf", "total"]].sum()
    if com_amostra:
        primeira = atomico.copy()
        segunda = atomico.copy()
        for col in ["maus", "perf", "total"]:
            primeira[col] = atomico[col] // 2
            segunda[col] = atomico[col] - primeira[col]
        primeira["amostra"] = "desenvolvimento"
        segunda["amostra"] = "validacao"
        atomico = pd.concat([primeira, segunda], ignore_index=True)
    partes = []
    for k in range(len(dimensoes) + 1):
        for cols in combinations(dimensoes, k):
            if cols:
                parte = atomico.groupby(list(cols), as_index=False)[["maus", "perf", "total"]].sum()
            else:
                parte = pd.DataFrame([atomico[["maus", "perf", "total"]].sum()])
            for col in dimensoes:
                if col not in cols:
                    parte[col] = TOTALIZADO
            partes.append(parte[dimensoes + ["maus", "perf", "total"]])
    return pd.concat(partes, ignore_index=True)


class AnaliseCuboTest(unittest.TestCase):
    def setUp(self):
        self.criterios = CriteriosElegibilidade(
            minimo_total=100, minimo_performance=90, minimo_bons=10,
            minimo_maus=5, cobertura_minima=0.8)

    def test_multicategoria_e_temporal(self):
        r = analisar_cubo(cubo_exemplo(), col_safra="safra",
                         marcador_total=TOTALIZADO, criterios=self.criterios)
        self.assertEqual(len(r.combination_summary), 3)
        self.assertEqual(len(r.cohort_detail), 3 + 2 + 6)
        self.assertEqual(len(r.cohort_temporal), (3 + 2 + 6) * 2)
        self.assertEqual(len(r.combination_comparison), 2)
        faixa = r.combination_summary.set_index("combinacao").loc["faixa"]
        self.assertEqual(faixa["qtd_grupos"], 3)
        self.assertAlmostEqual(faixa["cobertura_elegivel"], 1)
        self.assertGreater(faixa["v_cramer"], 0)
        self.assertGreaterEqual(faixa["persistencia_sinal"], 0)
        detalhe = r.cohort_detail.query("combinacao == 'faixa'")
        self.assertTrue((detalhe["qtd_sem_performance"] > 0).all())
        self.assertTrue((detalhe["bad_rate"] == detalhe["qtd_maus"] / detalhe["qtd_performance"]).all())

    def test_sem_safra_e_inconsistencia(self):
        cubo = cubo_exemplo(com_safra=False)
        r = analisar_cubo(cubo, marcador_total=TOTALIZADO, criterios=self.criterios)
        self.assertTrue(r.cohort_temporal.empty)
        self.assertEqual(r.combination_summary["ganho_v_melhor_subset"].notna().sum(), 1)
        cubo.loc[cubo["faixa"].eq("baixa") & cubo["origem"].eq(TOTALIZADO), "perf"] += 1
        with self.assertRaisesRegex(ValueError, "incompleta ou inconsistente"):
            analisar_cubo(cubo, marcador_total=TOTALIZADO, criterios=self.criterios)

    def test_denominador_zero_e_limites(self):
        cubo = pd.DataFrame([
            [TOTALIZADO, 2, 8, 10],
            ["A", 2, 8, 8],
            ["B", 0, 0, 2],
        ], columns=["segmento", "maus", "perf", "total"])
        r = analisar_cubo(cubo, marcador_total=TOTALIZADO,
                         criterios=CriteriosElegibilidade(0, 0, 0, 0, 0))
        b = r.cohort_detail.set_index("segmento").loc["B"]
        self.assertTrue(pd.isna(b["bad_rate"]))
        self.assertFalse(b["elegivel"])
        self.assertAlmostEqual(r.cohort_detail["participacao"].sum(), 1)

    def test_amostras(self):
        r = analisar_cubo(cubo_exemplo(com_amostra=True), col_safra="safra",
                         col_amostra="amostra", marcador_total=TOTALIZADO,
                         criterios=CriteriosElegibilidade(50, 40, 5, 2, 0.8))
        self.assertTrue(r.combination_summary["qtd_amostras_avaliadas"].eq(2).all())
        self.assertTrue(r.combination_summary["v_min_amostras"].notna().all())
        self.assertTrue((r.combination_summary["viavel"] == (
            r.combination_summary["viavel_global"]
            & r.combination_summary["viavel_amostras"])).all())

    def test_oito_caracteristicas(self):
        colunas = [f"flag_{i}" for i in range(8)]
        atomico = pd.DataFrame(list(product([0, 1], repeat=8)), columns=colunas)
        atomico["maus"] = 10 + atomico[colunas].sum(axis=1)
        atomico["perf"] = 90
        atomico["total"] = 100
        partes = []
        for k in range(9):
            for cols in combinations(colunas, k):
                if cols:
                    bloco = atomico.groupby(list(cols), as_index=False)[["maus", "perf", "total"]].sum()
                else:
                    bloco = pd.DataFrame([atomico[["maus", "perf", "total"]].sum()])
                for col in colunas:
                    if col not in cols:
                        bloco[col] = TOTALIZADO
                partes.append(bloco[colunas + ["maus", "perf", "total"]])
        cubo = pd.concat(partes, ignore_index=True)
        r = analisar_cubo(cubo, marcador_total=TOTALIZADO,
                         criterios=CriteriosElegibilidade(1, 1, 1, 1, 0.8))
        self.assertEqual(len(r.combination_summary), 255)
        self.assertEqual(len(r.cohort_detail), 6560)


if __name__ == "__main__":
    unittest.main()
