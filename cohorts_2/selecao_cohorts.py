"""Seleção estrutural de cohorts a partir de um cubo; não lê features candidatas."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

import numpy as np
import pandas as pd

from analise_cohorts import ResultadoAnalise, _mascara_total, _risco, chave_cohort, hash_cubo


@dataclass
class ResultadoSelecao:
    decisions: pd.DataFrame
    catalog: dict[str, Any]
    catalog_cohorts: pd.DataFrame


def _normalizar(valor: Any) -> Any:
    if isinstance(valor, np.generic):
        valor = valor.item()
    if isinstance(valor, (tuple, list)):
        return [_normalizar(v) for v in valor]
    if isinstance(valor, dict):
        return {str(k): _normalizar(v) for k, v in valor.items()}
    if pd.isna(valor):
        return None
    if isinstance(valor, (str, int, float, bool)):
        return valor
    return str(valor)


def _limites_ok(bloco: pd.DataFrame, limites: Mapping[str, int]) -> bool:
    contagens = bloco[["qtd_total", "qtd_performance", "qtd_bons", "qtd_maus"]].sum()
    return all(int(contagens[c]) >= int(limites[c]) for c in contagens.index)


def selecionar_cohorts(
    cubo: pd.DataFrame,
    diagnostico: ResultadoAnalise,
    politica: Mapping[str, Any],
    *,
    proveniencia: Mapping[str, str] | None = None,
) -> ResultadoSelecao:
    """Decide sobre todas as 2**N-1 combinações, sem consultar features.

    A política deve declarar as N dimensões na mesma ordem do diagnóstico.
    Cohorts suplementares podem se sobrepor; somente a partição principal é
    uma atribuição exclusiva, com reserva para folhas não elegíveis.
    """
    resumo = diagnostico.combination_summary
    detalhe = diagnostico.cohort_detail
    dimensoes = list(detalhe.columns[:detalhe.columns.get_loc("combination_id")])
    metadados = politica["dimensions"]
    if list(metadados) != dimensoes:
        raise ValueError("A ordem das dimensões da política difere do diagnóstico.")
    if len(resumo) != 2 ** len(dimensoes) - 1 or set(resumo.combination_id) != set(
            range(1, 2 ** len(dimensoes))):
        raise ValueError("O diagnóstico não contém todas as combinações esperadas.")
    input_hash = hash_cubo(cubo)
    if diagnostico.input_hash is not None and diagnostico.input_hash != input_hash:
        raise ValueError("O cubo difere do usado no diagnóstico.")
    if diagnostico.criteria is not None:
        limites = politica["cohort_minimums"]
        esperado = (limites["qtd_total"], limites["qtd_performance"],
                    limites["qtd_bons"], limites["qtd_maus"],
                    politica["minimum_eligible_coverage"])
        observado = (diagnostico.criteria.minimo_total,
                     diagnostico.criteria.minimo_performance,
                     diagnostico.criteria.minimo_bons,
                     diagnostico.criteria.minimo_maus,
                     diagnostico.criteria.cobertura_minima)
        if esperado != observado:
            raise ValueError("A política difere dos critérios usados no diagnóstico.")
    if not politica.get("catalog_version") or not politica.get("status"):
        raise ValueError("A política precisa de versão e status.")
    if any(not item.get("rationale") for item in metadados.values()):
        raise ValueError("Cada dimensão precisa de justificativa estrutural.")
    perfis = politica.get("priority_profiles", [])
    if len({p["id"] for p in perfis}) != len(perfis):
        raise ValueError("IDs de perfis prioritários duplicados.")
    for perfil in perfis:
        if not perfil.get("conditions") or not set(perfil["conditions"]) <= set(dimensoes):
            raise ValueError(f"Perfil prioritário inválido: {perfil['id']}.")

    marcador = politica.get("total_marker")
    auxiliares = [c for c in (politica.get("col_safra"), politica.get("col_amostra")) if c]
    flags = pd.DataFrame({c: ~_mascara_total(cubo[c], marcador)
                          for c in dimensoes + auxiliares})
    atomico = cubo.loc[flags[dimensoes].all(axis=1) & ~flags[auxiliares].any(axis=1)].copy()
    if atomico.empty:
        raise ValueError("Faltam células atômicas com safras/amostras totalizadas.")
    total_col = cubo.columns[-1]
    total_geral = int(cubo.loc[~flags.any(axis=1), total_col].iloc[0])
    if int(atomico[total_col].sum()) != total_geral:
        raise ValueError("Células atômicas não conciliam com o total geral.")
    atomico = atomico.reset_index(drop=True)
    pesos = atomico[total_col].to_numpy(dtype=int)

    perfil_atoms: dict[str, set[int]] = {}
    for perfil in perfis:
        condicao = pd.Series(True, index=atomico.index)
        for c, valor in perfil["conditions"].items():
            condicao &= atomico[c].isna() if valor is None else atomico[c].eq(valor)
        indices = set(atomico.index[condicao])
        if not indices:
            raise ValueError(f"Perfil prioritário não encontrado: {perfil['id']}.")
        perfil_atoms[perfil["id"]] = indices

    limites_amostra = politica["sample_minimums"]
    temporal = politica.get("temporal", {})
    cobertura_minima = float(politica["minimum_eligible_coverage"])
    limite_perfil = float(politica["minimum_profile_coverage"])
    if not 0 <= cobertura_minima <= 1 or not 0 <= limite_perfil <= 1:
        raise ValueError("Coberturas mínimas devem estar entre zero e um.")
    amostra_col = politica.get("col_amostra")
    safra_col = politica.get("col_safra")
    if temporal.get("required", False) and not safra_col:
        raise ValueError("Estabilidade temporal exige uma coluna de safra.")
    if temporal.get("required", False) and not (
            0 <= float(temporal["minimum_presence_fraction"]) <= 1
            and float(temporal["maximum_relative_share_shift"]) >= 0):
        raise ValueError("Limites de estabilidade temporal inválidos.")
    if any(not isinstance(v, int) or v < 0 for v in limites_amostra.values()):
        raise ValueError("Limites por amostra devem ser inteiros não negativos.")
    particao = diagnostico.cohort_partition
    if amostra_col and (particao is None or particao.empty):
        raise ValueError("Falta diagnóstico por cohort e amostra.")
    if (amostra_col and politica.get("development_sample") is not None
            and not particao[amostra_col].eq(politica["development_sample"]).any()):
        raise ValueError("A amostra de desenvolvimento não existe no cubo.")

    registros: list[dict[str, Any]] = []
    atoms_por_combo: dict[int, set[int]] = {}
    perfil_atoms_por_combo: dict[int, dict[str, set[int]]] = {}
    chaves_por_combo: dict[int, set[str]] = {}
    estabilidade_por_chave: dict[str, bool] = {}

    for linha in resumo.itertuples(index=False):
        cid = int(linha.combination_id)
        cols = list(linha.caracteristicas)
        estrutural = all(bool(metadados[c].get("approved")) for c in cols)
        grupos = detalhe.loc[detalhe.combination_id.eq(cid)]
        aptas: set[str] = set()
        for _, grupo in grupos.iterrows():
            chave = grupo["cohort_key"]
            if not grupo["elegivel"]:
                estabilidade_por_chave[chave] = False
                continue
            estavel = True
            if amostra_col and particao is not None and not particao.empty:
                bloco = particao.loc[particao.cohort_key.eq(chave)]
                for _, fatia in bloco.groupby(amostra_col, dropna=False):
                    if not _limites_ok(fatia, limites_amostra):
                        estavel = False
                if safra_col and temporal.get("required", False):
                    presenca_minima = float(temporal["minimum_presence_fraction"])
                    if float(bloco.presente.mean()) < presenca_minima:
                        estavel = False
                    desvio = (bloco.participacao_particao / grupo["participacao"] - 1).abs()
                    if desvio.max() > float(temporal["maximum_relative_share_shift"]):
                        estavel = False
            elif safra_col and temporal.get("required", False):
                bloco = diagnostico.cohort_temporal.loc[
                    diagnostico.cohort_temporal.cohort_key.eq(chave)]
                n_safras = cubo.loc[
                    flags[safra_col] & ~flags[[c for c in dimensoes + auxiliares if c != safra_col]].any(axis=1),
                    safra_col].nunique(dropna=False)
                if len(bloco) / n_safras < float(temporal["minimum_presence_fraction"]):
                    estavel = False
                desvio = (bloco.participacao_safra / grupo["participacao"] - 1).abs()
                if desvio.max() > float(temporal["maximum_relative_share_shift"]):
                    estavel = False
            estabilidade_por_chave[chave] = estavel
            if estavel:
                aptas.add(chave)
        chaves_por_combo[cid] = aptas
        chaves_atomicas = [chave_cohort(cid, valores)
                           for valores in atomico[cols].itertuples(index=False, name=None)]
        cobertos = {i for i, chave in enumerate(chaves_atomicas) if chave in aptas}
        atoms_por_combo[cid] = cobertos
        cobertura = sum(pesos[i] for i in cobertos) / total_geral
        por_perfil: dict[str, set[int]] = {}
        for perfil in perfis:
            pid = perfil["id"]
            por_perfil[pid] = (cobertos & perfil_atoms[pid]
                              if set(perfil["conditions"]) <= set(cols) else set())
        perfil_atoms_por_combo[cid] = por_perfil
        perfis_cobertos = sum(
            sum(pesos[i] for i in por_perfil[p["id"]]) /
            sum(pesos[i] for i in perfil_atoms[p["id"]]) >= limite_perfil
            for p in perfis)
        motivos = []
        if not linha.viavel:
            motivos.append("viabilidade_global_ou_amostras")
        if not estrutural:
            motivos.append("relevancia_estrutural")
        if len(aptas) < 2:
            motivos.append("menos_de_dois_cohorts_estaveis")
        if cobertura < cobertura_minima:
            motivos.append("cobertura_estavel")
        risco_desenvolvimento = np.nan
        if amostra_col and politica.get("development_sample") is not None:
            bloco_dev = particao.loc[
                particao.combination_id.eq(cid)
                & particao[amostra_col].eq(politica["development_sample"])
                & particao.cohort_key.isin(aptas)]
            if not bloco_dev.empty:
                agregado = bloco_dev.groupby("cohort_key", as_index=False)[
                    ["qtd_performance", "qtd_maus"]].sum()
                agregado["elegivel"] = True
                risco_desenvolvimento = _risco(agregado)["v_cramer"]
        registros.append(dict(combination_id=cid, combinacao=linha.combinacao,
                              qtd_caracteristicas=len(cols), qtd_grupos=linha.qtd_grupos,
                              qtd_cohorts_aptos=len(aptas), cobertura_estavel=cobertura,
                              perfis_prioritarios_cobertos=perfis_cobertos,
                              estrutural=estrutural, admissivel=not motivos,
                              motivo_exclusao=";".join(motivos),
                              v_cramer_diagnostico=linha.v_cramer,
                              v_cramer_desenvolvimento=risco_desenvolvimento,
                              papel="rejeitada" if motivos else "candidata"))

    decisoes = pd.DataFrame(registros).sort_values("combination_id").reset_index(drop=True)
    admissiveis = decisoes.loc[decisoes.admissivel]
    if admissiveis.empty:
        raise ValueError("Nenhuma combinação atende à política; revise os limites antes de congelar.")
    por_id = resumo.set_index("combination_id")
    def peso(indices: set[int]) -> int:
        return int(sum(pesos[i] for i in indices))
    def pontuacao_principal(cid: int) -> tuple:
        r = decisoes.set_index("combination_id").loc[cid]
        cobertura_perfis = sum(
            peso(perfil_atoms_por_combo[cid][p["id"]]) /
            peso(perfil_atoms[p["id"]]) for p in perfis)
        risco = r.v_cramer_desenvolvimento
        return (int(r.perfis_prioritarios_cobertos), cobertura_perfis,
                float(r.cobertura_estavel), -int(r.qtd_grupos),
                -int(r.qtd_caracteristicas),
                float(risco) if pd.notna(risco) else -1, -cid)
    principal = max((int(cid) for cid in admissiveis.combination_id),
                    key=pontuacao_principal)
    selecionados = [principal]
    covered = set(atoms_por_combo[principal])
    perfis_cobertos_atoms = {
        p["id"]: set(perfil_atoms_por_combo[principal][p["id"]]) for p in perfis}
    dims_selected = set(por_id.loc[principal, "caracteristicas"])
    max_suplementares = int(politica.get("maximum_supplementary", 0))
    if max_suplementares < 0:
        raise ValueError("maximum_supplementary não pode ser negativo.")
    for _ in range(max_suplementares):
        opcoes = []
        for cid in admissiveis.combination_id:
            cid = int(cid)
            if cid in selecionados:
                continue
            novas_dimensoes = set(por_id.loc[cid, "caracteristicas"]) - dims_selected
            ganhos_perfis = sum(
                peso(perfil_atoms_por_combo[cid][p["id"]] - perfis_cobertos_atoms[p["id"]])
                for p in perfis)
            ganho_populacao = peso(atoms_por_combo[cid] - covered)
            if not novas_dimensoes and not ganhos_perfis and not ganho_populacao:
                continue
            r = decisoes.set_index("combination_id").loc[cid]
            opcoes.append(((ganhos_perfis, len(novas_dimensoes), ganho_populacao,
                            -int(r.qtd_grupos), -int(r.qtd_caracteristicas), -cid), cid))
        if not opcoes:
            break
        _, cid = max(opcoes)
        selecionados.append(cid)
        covered |= atoms_por_combo[cid]
        for p in perfis:
            perfis_cobertos_atoms[p["id"]] |= perfil_atoms_por_combo[cid][p["id"]]
        dims_selected |= set(por_id.loc[cid, "caracteristicas"])

    decisoes.loc[decisoes.combination_id.eq(principal), "papel"] = "principal"
    decisoes.loc[decisoes.combination_id.isin(selecionados[1:]), "papel"] = "suplementar"
    trilha = []
    uniao_populacao: set[int] = set()
    uniao_perfis = {p["id"]: set() for p in perfis}
    uniao_dimensoes: set[str] = set()
    for cid in selecionados:
        novas_dimensoes = sorted(set(por_id.loc[cid, "caracteristicas"]) - uniao_dimensoes)
        ganho_populacao = peso(atoms_por_combo[cid] - uniao_populacao)
        ganho_perfis = {
            p["id"]: peso(perfil_atoms_por_combo[cid][p["id"]] - uniao_perfis[p["id"]])
            for p in perfis}
        trilha.append(dict(combination_id=cid, role="principal" if cid == principal
                           else "suplementar", new_dimensions=novas_dimensoes,
                           marginal_population=ganho_populacao,
                           marginal_priority_population=ganho_perfis))
        idx = decisoes.index[decisoes.combination_id.eq(cid)][0]
        decisoes.loc[idx, "marginal_population"] = ganho_populacao
        decisoes.loc[idx, "new_dimensions"] = ",".join(novas_dimensoes)
        decisoes.loc[idx, "marginal_priority_population"] = sum(ganho_perfis.values())
        uniao_populacao |= atoms_por_combo[cid]
        uniao_dimensoes |= set(por_id.loc[cid, "caracteristicas"])
        for p in perfis:
            uniao_perfis[p["id"]] |= perfil_atoms_por_combo[cid][p["id"]]
    decisoes["marginal_population"] = decisoes["marginal_population"].fillna(0).astype(int)
    decisoes["marginal_priority_population"] = (
        decisoes["marginal_priority_population"].fillna(0).astype(int))
    decisoes["new_dimensions"] = decisoes["new_dimensions"].fillna("")
    cobertura_perfis_final = {
        p["id"]: dict(covered_population=peso(uniao_perfis[p["id"]]),
                      total_population=peso(perfil_atoms[p["id"]]),
                      coverage=peso(uniao_perfis[p["id"]]) / peso(perfil_atoms[p["id"]]))
        for p in perfis}
    pendentes = [pid for pid, valor in cobertura_perfis_final.items()
                 if valor["coverage"] < limite_perfil]
    if pendentes:
        raise ValueError("Perfis prioritários sem cobertura mínima: " + ", ".join(pendentes))
    catalog_rows = []
    for cid in selecionados:
        cols = list(por_id.loc[cid, "caracteristicas"])
        for _, row in detalhe.loc[detalhe.combination_id.eq(cid)].iterrows():
            if row["cohort_key"] not in chaves_por_combo[cid]:
                continue
            risco_particao = (particao.loc[particao.cohort_key.eq(row["cohort_key"])]
                              if particao is not None and not particao.empty else pd.DataFrame())
            minimo_risco = int(temporal.get("minimum_bad_for_risk_signal", 0))
            sinal_risco = ("nao_avaliado" if risco_particao.empty else
                           "avaliavel" if risco_particao.qtd_maus.ge(minimo_risco).all()
                           else "inconclusivo")
            item = dict(combination_id=cid, cohort_key=row["cohort_key"],
                        role="principal" if cid == principal else "suplementar",
                        grupo_id=int(row["grupo_id"]),
                        values={c: _normalizar(row[c]) for c in cols},
                        qtd_total=int(row["qtd_total"]),
                        qtd_performance=int(row["qtd_performance"]),
                        qtd_bons=int(row["qtd_bons"]), qtd_maus=int(row["qtd_maus"]),
                        risk_signal_status=sinal_risco)
            catalog_rows.append(item)
    reserva = detalhe.loc[detalhe.combination_id.eq(principal)
                          & ~detalhe.cohort_key.isin(chaves_por_combo[principal])]
    fallback = dict(cohort_key=f"reserva-{principal}",
                    source_cohort_keys=sorted(reserva.cohort_key.tolist()),
                    qtd_total=int(reserva.qtd_total.sum()),
                    qtd_performance=int(reserva.qtd_performance.sum()),
                    qtd_bons=int(reserva.qtd_bons.sum()),
                    qtd_maus=int(reserva.qtd_maus.sum()),
                    modeling_eligible=False)
    if sum(r["qtd_total"] for r in catalog_rows if r["role"] == "principal") + fallback["qtd_total"] != total_geral:
        raise AssertionError("A partição principal não cobre o total geral.")
    catalog = dict(schema_version=1, catalog_version=politica["catalog_version"],
                   status=politica["status"], dimensions=dimensoes,
                   primary_combination_id=principal,
                   supplementary_combination_ids=selecionados[1:],
                   selected_combinations=[
                       dict(combination_id=cid,
                            dimensions=list(por_id.loc[cid, "caracteristicas"]),
                            role="principal" if cid == principal else "suplementar")
                       for cid in selecionados],
                   total_population=total_geral, input_hash=input_hash,
                   policy_hash=hashlib.sha256(json.dumps(
                       _normalizar(dict(politica)), sort_keys=True,
                       ensure_ascii=False).encode("utf-8")).hexdigest(),
                   provenance=dict(proveniencia or {}), cohorts=catalog_rows,
                   fallback=fallback, priority_profile_coverage=cobertura_perfis_final,
                   selection_trace=trilha,
                   decision_rule="perfis, cobertura, estabilidade, simplicidade; V do desenvolvimento apenas desempate")
    catalog["catalog_hash"] = hashlib.sha256(json.dumps(
        catalog, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return ResultadoSelecao(decisoes, catalog, pd.DataFrame(catalog_rows))
