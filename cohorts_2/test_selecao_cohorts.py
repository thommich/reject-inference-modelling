"""Contrato da seleção sequencial, inclusive uso com outras dimensões."""

import copy
from itertools import combinations, product
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from analise_cohorts import CriteriosElegibilidade, analisar_cubo
from definir_cohorts import executar_definicao
from selecao_cohorts import selecionar_cohorts
from test_analise_cohorts import TOTALIZADO, cubo_exemplo


def politica_teste():
    return {
        "catalog_version": "teste-generico-v1",
        "status": "demonstracao",
        "total_marker": TOTALIZADO,
        "col_safra": "safra",
        "col_amostra": "amostra",
        "development_sample": "desenvolvimento",
        "dimensions": {
            "faixa": {"approved": True, "rationale": "Categoria sintética."},
            "origem": {"approved": True, "rationale": "Canal sintético."},
        },
        "cohort_minimums": {"qtd_total": 50, "qtd_performance": 40,
                            "qtd_bons": 5, "qtd_maus": 2},
        "sample_minimums": {"qtd_total": 20, "qtd_performance": 15,
                            "qtd_bons": 2, "qtd_maus": 1},
        "minimum_eligible_coverage": 0.8,
        "minimum_profile_coverage": 0.8,
        "temporal": {"required": True, "minimum_presence_fraction": 1.0,
                     "maximum_relative_share_shift": 0.75,
                     "minimum_bad_for_risk_signal": 1},
        "priority_profiles": [
            {"id": "origem_B", "conditions": {"origem": "B"}},
        ],
        "maximum_supplementary": 1,
    }


class SelecaoCohortsTest(unittest.TestCase):
    def setUp(self):
        self.cubo = cubo_exemplo(com_amostra=True)
        self.politica = politica_teste()
        self.criterios = CriteriosElegibilidade(50, 40, 5, 2, 0.8)

    def analisar(self, cubo):
        return analisar_cubo(cubo, caracteristicas=list(self.politica["dimensions"]),
                             col_safra="safra", col_amostra="amostra",
                             marcador_total=TOTALIZADO, criterios=self.criterios)

    def test_n_variavel_e_catalogo_reproduzivel(self):
        diagnostico = self.analisar(self.cubo)
        resultado = selecionar_cohorts(self.cubo, diagnostico, self.politica)
        self.assertEqual(set(resultado.decisions.combination_id), {1, 2, 3})
        self.assertEqual(resultado.catalog["total_population"],
                         int(self.cubo.iloc[0]["total"]))
        self.assertEqual(sum(c["qtd_total"] for c in resultado.catalog["cohorts"]
                             if c["role"] == "principal") +
                         resultado.catalog["fallback"]["qtd_total"],
                         resultado.catalog["total_population"])
        embaralhado = self.cubo.sample(frac=1, random_state=9).reset_index(drop=True)
        novamente = selecionar_cohorts(embaralhado, self.analisar(embaralhado),
                                       self.politica)
        self.assertEqual(resultado.catalog["catalog_hash"],
                         novamente.catalog["catalog_hash"])
        self.assertEqual(set(diagnostico.cohort_detail.cohort_key),
                         set(self.analisar(embaralhado).cohort_detail.cohort_key))

    def test_relevancia_e_perfil_sao_configuraveis(self):
        politica = copy.deepcopy(self.politica)
        politica["dimensions"]["origem"]["approved"] = False
        with self.assertRaisesRegex(ValueError, "Nenhuma combinação"):
            # Um perfil exige origem, mas a dimensão não foi aprovada.
            politica["dimensions"]["faixa"]["approved"] = False
            selecionar_cohorts(self.cubo, self.analisar(self.cubo), politica)
        politica = copy.deepcopy(self.politica)
        politica["priority_profiles"][0]["conditions"] = {"outra": "B"}
        with self.assertRaisesRegex(ValueError, "Perfil prioritário inválido"):
            selecionar_cohorts(self.cubo, self.analisar(self.cubo), politica)
        politica = copy.deepcopy(self.politica)
        politica["dimensions"]["origem"]["approved"] = False
        with self.assertRaisesRegex(ValueError, "Perfis prioritários sem cobertura"):
            selecionar_cohorts(self.cubo, self.analisar(self.cubo), politica)

    def test_execucao_csv_com_duas_dimensoes(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            cubo_csv = raiz / "entrada.csv"
            politica_json = raiz / "regras.json"
            self.cubo.to_csv(cubo_csv, index=False)
            politica_json.write_text(json.dumps(self.politica), encoding="utf-8")
            arquivos = executar_definicao(cubo_csv, politica_json, raiz / "saida")
            catalogo = json.loads(arquivos["catalogo_cohorts"].read_text(encoding="utf-8"))
            self.assertEqual(catalogo["dimensions"], ["faixa", "origem"])
            self.assertEqual(len(pd.read_csv(arquivos["decisions"])), 3)
            novamente = executar_definicao(cubo_csv, politica_json, raiz / "saida")
            self.assertEqual(arquivos, novamente)
            politica_alterada = copy.deepcopy(self.politica)
            politica_alterada["maximum_supplementary"] = 0
            politica_json.write_text(json.dumps(politica_alterada), encoding="utf-8")
            with self.assertRaises(FileExistsError):
                executar_definicao(cubo_csv, politica_json, raiz / "saida")

    def test_tres_dimensoes_sem_safra_ou_amostra(self):
        dimensoes = ["faixa cliente", "origem", "regiao"]
        atomico = pd.DataFrame(list(product(["A", "B"], repeat=3)),
                               columns=dimensoes)
        atomico["maus"] = 5
        atomico["perf"] = 50
        atomico["total"] = 60
        partes = []
        for k in range(len(dimensoes) + 1):
            for cols in combinations(dimensoes, k):
                bloco = (atomico.groupby(list(cols), as_index=False)[
                    ["maus", "perf", "total"]].sum() if cols else
                    pd.DataFrame([atomico[["maus", "perf", "total"]].sum()]))
                for col in dimensoes:
                    if col not in cols:
                        bloco[col] = TOTALIZADO
                partes.append(bloco[dimensoes + ["maus", "perf", "total"]])
        cubo = pd.concat(partes, ignore_index=True)
        politica = copy.deepcopy(self.politica)
        politica["dimensions"] = {c: {"approved": True, "rationale": "Sintética."}
                                  for c in dimensoes}
        politica["col_safra"] = None
        politica["col_amostra"] = None
        politica["temporal"]["required"] = False
        politica["priority_profiles"] = [
            {"id": "regiao_B", "conditions": {"regiao": "B"}}]
        diagnostico = analisar_cubo(cubo, caracteristicas=dimensoes,
                                     marcador_total=TOTALIZADO,
                                     criterios=self.criterios)
        resultado = selecionar_cohorts(cubo, diagnostico, politica)
        self.assertEqual(len(resultado.decisions), 7)
        self.assertIn("faixa cliente", resultado.catalog["dimensions"])
        self.assertEqual(resultado.catalog["total_population"], 480)
        self.assertTrue(all(c["risk_signal_status"] == "nao_avaliado"
                            for c in resultado.catalog["cohorts"]))

    def test_apenas_amostra(self):
        cubo = cubo_exemplo(com_safra=False, com_amostra=True)
        politica = copy.deepcopy(self.politica)
        politica["col_safra"] = None
        politica["temporal"]["required"] = False
        diagnostico = analisar_cubo(
            cubo, caracteristicas=list(politica["dimensions"]),
            col_amostra="amostra", marcador_total=TOTALIZADO,
            criterios=self.criterios)
        self.assertFalse(diagnostico.cohort_partition.empty)
        resultado = selecionar_cohorts(cubo, diagnostico, politica)
        self.assertEqual(len(resultado.decisions), 3)


if __name__ == "__main__":
    unittest.main()
