"""Gera um cubo sintético e executa somente a definição de cohorts.

Os parâmetros servem apenas à demonstração. Nenhuma observação individual ou
dado real é lido. A análise propriamente dita recebe o DataFrame `cubo`.
"""

from __future__ import annotations

import argparse
import hashlib
from itertools import combinations, product
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analise_cohorts import CriteriosElegibilidade, analisar_cubo
from selecao_cohorts import selecionar_cohorts


MARCADOR_TOTAL = "<TOTAL>"
CARACTERISTICAS = [
    "faixa_renda", "exposicao", "origem", "relacionamento",
    "canal", "garantia", "historico", "regiao",
]
SAFRAS = ["2024S1", "2024S2", "2025S1"]
AMOSTRAS = ["desenvolvimento", "validacao"]
DIMENSOES = CARACTERISTICAS + ["safra", "amostra"]
CONTAGENS = ["qtd_maus", "qtd_performance", "qtd_total"]


def simular_perfis_agregados(seed: int = 20261026) -> pd.DataFrame:
    """Cria contagens mutuamente exclusivas em todas as dimensões.

    `garantia=None` é uma categoria real ausente; `<TOTAL>` é reservado para
    totalizações. O número de maus é sorteado só entre os casos com
    performance disponível, mantendo 0 <= maus <= performance <= total.
    """
    rng = np.random.default_rng(seed)
    dominios = [
        ["baixa", "media", "alta"],
        ["baixa", "media", "alta"],
        ["A", "B"],
        ["sim", "nao"],
        ["digital", "presencial"],
        ["sim", None],
        ["curto", "longo"],
        ["metropolitana", "interior"],
        SAFRAS,
        AMOSTRAS,
    ]
    linhas = []
    for valores in product(*dominios):
        perfil = dict(zip(DIMENSOES, valores))
        total = int(rng.poisson(70) + 20)
        prob_perf = (0.91 - 0.05 * (perfil["origem"] == "B")
                     - 0.04 * (perfil["canal"] == "digital")
                     - 0.03 * (perfil["garantia"] is None))
        performance = int(rng.binomial(total, prob_perf))
        logit = (
            -2.5
            + {"baixa": 0.55, "media": 0.2, "alta": -0.1}[perfil["faixa_renda"]]
            + {"baixa": -0.3, "media": 0.2, "alta": 0.7}[perfil["exposicao"]]
            + 0.30 * (perfil["origem"] == "B")
            + 0.15 * (perfil["relacionamento"] == "nao")
            + 0.10 * (perfil["canal"] == "digital")
            + 0.20 * (perfil["garantia"] is None)
            + 0.30 * (perfil["historico"] == "curto")
            + 0.10 * (perfil["regiao"] == "interior")
            + {"2024S1": 0.0, "2024S2": 0.08, "2025S1": 0.16}[perfil["safra"]]
            + 0.04 * (perfil["amostra"] == "validacao")
            + 0.25 * (perfil["faixa_renda"] == "baixa"
                      and perfil["exposicao"] == "alta")
        )
        prob_mau = 1 / (1 + np.exp(-logit))
        perfil.update(qtd_maus=int(rng.binomial(performance, prob_mau)),
                      qtd_performance=performance, qtd_total=total)
        linhas.append(perfil)

    return pd.DataFrame(linhas)


def simular_cubo(seed: int = 20261026) -> pd.DataFrame:
    """Cria o cubo completo usado na primeira fase."""
    atomico = simular_perfis_agregados(seed)
    partes = []
    for k in range(len(DIMENSOES) + 1):
        for presentes in combinations(DIMENSOES, k):
            if presentes:
                bloco = atomico.groupby(list(presentes), dropna=False,
                                        as_index=False)[CONTAGENS].sum()
            else:
                bloco = pd.DataFrame([atomico[CONTAGENS].sum()])
            for dimensao in DIMENSOES:
                if dimensao not in presentes:
                    bloco[dimensao] = MARCADOR_TOTAL
            partes.append(bloco[DIMENSOES + CONTAGENS])
    return pd.concat(partes, ignore_index=True)


def executar_exemplo(pasta_saida: Path, seed: int = 20261026) -> dict[str, Path]:
    politica_path = Path(__file__).with_name("politica_cohorts_simulada.json")
    politica = json.loads(politica_path.read_text(encoding="utf-8"))
    destino = pasta_saida / "etapa1" / politica["catalog_version"]
    destino.mkdir(parents=True, exist_ok=True)
    cubo = simular_cubo(seed)
    arquivo_cubo = destino / "cubo_simulado.csv"
    _gravar_se_igual(arquivo_cubo, cubo.to_csv(index=False).encode("utf-8-sig"))
    cubo_lido = pd.read_csv(arquivo_cubo)
    limites = politica["cohort_minimums"]
    diagnostico = analisar_cubo(
        cubo_lido,
        caracteristicas=list(politica["dimensions"]),
        col_safra=politica["col_safra"],
        col_amostra=politica["col_amostra"],
        marcador_total=politica["total_marker"],
        criterios=CriteriosElegibilidade(
            minimo_total=limites["qtd_total"],
            minimo_performance=limites["qtd_performance"],
            minimo_bons=limites["qtd_bons"],
            minimo_maus=limites["qtd_maus"],
            cobertura_minima=politica["minimum_eligible_coverage"],
        ),
    )
    fontes = [Path(__file__).with_name(n) for n in
              ("analise_cohorts.py", "selecao_cohorts.py", "exemplo_simulado.py")]
    proveniencia = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes}
    selecao = selecionar_cohorts(cubo_lido, diagnostico, politica, proveniencia=proveniencia)
    arquivos = {"cubo_simulado": arquivo_cubo}
    for nome in ("combination_summary", "cohort_detail", "cohort_temporal",
                 "combination_comparison", "cohort_partition"):
        caminho = destino / f"{nome}.csv"
        _gravar_se_igual(caminho, getattr(diagnostico, nome).to_csv(
            index=False).encode("utf-8-sig"))
        arquivos[nome] = caminho
    for nome, tabela in (("decisions", selecao.decisions),
                         ("catalog_cohorts", selecao.catalog_cohorts)):
        caminho = destino / f"{nome}.csv"
        _gravar_se_igual(caminho, tabela.to_csv(index=False).encode("utf-8-sig"))
        arquivos[nome] = caminho
    catalogo_path = destino / "catalogo_cohorts.json"
    _gravar_se_igual(catalogo_path, (json.dumps(
        selecao.catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    arquivos["catalogo_cohorts"] = catalogo_path
    return arquivos


def _gravar_se_igual(caminho: Path, conteudo: bytes) -> None:
    """Protege a versão congelada contra sobrescrita divergente."""
    if caminho.exists():
        if caminho.read_bytes() != conteudo:
            raise FileExistsError(f"Versão já existe com outro conteúdo: {caminho}")
        return
    caminho.write_bytes(conteudo)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=Path("exemplo_simulado"),
                        help="Pasta raiz para a saída versionada da etapa 1.")
    parser.add_argument("--seed", type=int, default=20261026)
    args = parser.parse_args()
    for nome, caminho in executar_exemplo(args.saida, args.seed).items():
        print(f"{nome}: {caminho}")
