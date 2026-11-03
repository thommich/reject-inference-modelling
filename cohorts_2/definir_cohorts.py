"""Executa a etapa 1 para um cubo CSV e uma política JSON com N dimensões."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from analise_cohorts import CriteriosElegibilidade, analisar_cubo
from selecao_cohorts import selecionar_cohorts


def _gravar_versao(caminho: Path, conteudo: bytes) -> None:
    if caminho.exists():
        if caminho.read_bytes() != conteudo:
            raise FileExistsError(f"Versão já existe com outro conteúdo: {caminho}")
        return
    caminho.write_bytes(conteudo)


def executar_definicao(cubo_csv: Path, politica_json: Path, pasta_saida: Path) -> dict[str, Path]:
    politica = json.loads(politica_json.read_text(encoding="utf-8"))
    cubo = pd.read_csv(cubo_csv)
    limites = politica["cohort_minimums"]
    diagnostico = analisar_cubo(
        cubo, caracteristicas=list(politica["dimensions"]),
        col_safra=politica.get("col_safra"), col_amostra=politica.get("col_amostra"),
        marcador_total=politica.get("total_marker"),
        criterios=CriteriosElegibilidade(
            minimo_total=limites["qtd_total"],
            minimo_performance=limites["qtd_performance"],
            minimo_bons=limites["qtd_bons"],
            minimo_maus=limites["qtd_maus"],
            cobertura_minima=politica["minimum_eligible_coverage"]))
    fontes = [Path(__file__).with_name(n) for n in
              ("analise_cohorts.py", "selecao_cohorts.py", "definir_cohorts.py")]
    proveniencia = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes}
    selecao = selecionar_cohorts(cubo, diagnostico, politica, proveniencia=proveniencia)
    destino = pasta_saida / politica["catalog_version"]
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = {}
    for nome in ("combination_summary", "cohort_detail", "cohort_temporal",
                 "combination_comparison", "cohort_partition"):
        caminho = destino / f"{nome}.csv"
        _gravar_versao(caminho, getattr(diagnostico, nome).to_csv(
            index=False).encode("utf-8-sig"))
        arquivos[nome] = caminho
    for nome, tabela in (("decisions", selecao.decisions),
                         ("catalog_cohorts", selecao.catalog_cohorts)):
        caminho = destino / f"{nome}.csv"
        _gravar_versao(caminho, tabela.to_csv(index=False).encode("utf-8-sig"))
        arquivos[nome] = caminho
    caminho = destino / "catalogo_cohorts.json"
    _gravar_versao(caminho, (json.dumps(
        selecao.catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    arquivos["catalogo_cohorts"] = caminho
    return arquivos


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cubo", type=Path, required=True)
    parser.add_argument("--politica", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    for nome, caminho in executar_definicao(args.cubo, args.politica, args.saida).items():
        print(f"{nome}: {caminho}")
