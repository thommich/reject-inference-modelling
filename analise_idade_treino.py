"""Análise univariada e escolha de faixas de idade usando apenas treino.

O módulo nunca recebe uma base de teste para ajustar ou comparar cutpoints.
Quantis, árvore e taxas por faixa são refeitos dentro de cada dobra do treino.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from math import ceil, sqrt
from pathlib import Path
from statistics import NormalDist
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.tree import DecisionTreeClassifier


@dataclass(frozen=True)
class ConfigIdade:
    idade_col: str = "idade"
    target_col: str = "mau"
    safra_col: str | None = None
    ordem_safras: tuple[Any, ...] | None = None
    particao_col: str | None = None
    valor_treino: Any = None
    idade_min: float = 0
    idade_max: float = 120
    k_min: int = 2
    k_max: int = 6
    min_total: int = 1000
    min_performance: int = 850
    min_bons: int = 650
    min_maus: int = 100
    cobertura_minima: float = 0.80
    presenca_temporal_minima: float = 1.0
    desvio_relativo_maximo: float = 0.75
    cv_dobras: int = 5
    semente: int = 20261105

    def __post_init__(self) -> None:
        if self.idade_min >= self.idade_max or self.k_min < 2 or self.k_max < self.k_min:
            raise ValueError("Domínio de idade ou intervalo de números de faixas inválido.")
        if any(x < 0 for x in (self.min_total, self.min_performance,
                               self.min_bons, self.min_maus)):
            raise ValueError("Contagens mínimas não podem ser negativas.")
        if not (0 <= self.cobertura_minima <= 1 and
                0 <= self.presenca_temporal_minima <= 1 and
                self.desvio_relativo_maximo >= 0):
            raise ValueError("Limites de cobertura ou estabilidade inválidos.")
        if self.cv_dobras < 2:
            raise ValueError("cv_dobras precisa ser pelo menos 2.")
        if self.particao_col and self.valor_treino is None:
            raise ValueError("Informe valor_treino para verificar a partição.")
        if self.safra_col and not self.ordem_safras:
            raise ValueError("Informe ordem_safras em ordem cronológica.")


def preparar_treino(df_treino: pd.DataFrame, cfg: ConfigIdade) -> pd.DataFrame:
    """Valida que a entrada contém somente treino e classifica idades especiais."""
    if not isinstance(df_treino, pd.DataFrame) or df_treino.empty:
        raise ValueError("Forneça um DataFrame de treinamento não vazio.")
    exigidas = {cfg.idade_col, cfg.target_col}
    exigidas.update(c for c in (cfg.safra_col, cfg.particao_col) if c)
    faltantes = exigidas - set(df_treino.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes: {sorted(faltantes)}.")
    if cfg.particao_col and not df_treino[cfg.particao_col].eq(cfg.valor_treino).all():
        raise ValueError("A entrada contém linhas fora da partição de treinamento.")
    if cfg.safra_col:
        observado = set(df_treino[cfg.safra_col].dropna().unique())
        if df_treino[cfg.safra_col].isna().any() or observado != set(cfg.ordem_safras):
            raise ValueError("ordem_safras deve listar exatamente as safras do treino, sem nulos.")
    base = df_treino.copy().reset_index(drop=True)
    idade = pd.to_numeric(base[cfg.idade_col], errors="coerce")
    alvo = pd.to_numeric(base[cfg.target_col], errors="raise")
    if not alvo.dropna().isin([0, 1]).all() or alvo.eq(0).sum() < 2 or alvo.eq(1).sum() < 2:
        raise ValueError("O target do treino precisa conter bons e maus (0/1), com pelo menos dois de cada.")
    ausente = base[cfg.idade_col].isna()
    valida = idade.notna() & np.isfinite(idade) & idade.between(cfg.idade_min, cfg.idade_max)
    base["_idade_num"] = idade.where(valida)
    base["_idade_status"] = np.select(
        [ausente, ~valida], ["IDADE_AUSENTE", "IDADE_INVALIDA"], default="VALIDA")
    base["_target"] = alvo
    if base["_idade_status"].eq("VALIDA").sum() < cfg.k_min * 2:
        raise ValueError("Há poucas idades válidas para os cortes solicitados.")
    return base


def _wilson(maus: pd.Series, performance: pd.Series) -> tuple[pd.Series, pd.Series]:
    z = NormalDist().inv_cdf(0.975)
    n = performance.astype(float).replace(0, np.nan)
    p = maus / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    margem = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (centro - margem).clip(lower=0), (centro + margem).clip(upper=1)


def _bins_histograma(idade: pd.Series) -> int | np.ndarray:
    valores = idade.to_numpy(dtype=float)
    if np.all(np.isclose(valores, np.round(valores))) and valores.max() - valores.min() <= 120:
        return np.arange(int(valores.min()) - 0.5, int(valores.max()) + 1.5)
    return min(50, max(10, int(sqrt(len(valores)))))


def descrever_intervalos(cortes: tuple[float, ...], cfg: ConfigIdade) -> list[str]:
    limites = [float(cfg.idade_min), *cortes, float(cfg.idade_max)]
    return [
        f"[{limites[i]:g}, {limites[i + 1]:g}{']' if i == len(limites) - 2 else ')'}"
        for i in range(len(limites) - 1)
    ]


def resumo_qualidade(base: pd.DataFrame, cfg: ConfigIdade) -> pd.DataFrame:
    linhas = []
    for status, bloco in base.groupby("_idade_status", sort=False):
        perf = bloco["_target"].notna()
        linhas.append(dict(status=status, qtd_total=len(bloco),
                           qtd_performance=int(perf.sum()),
                           qtd_bons=int(bloco["_target"].eq(0).sum()),
                           qtd_maus=int(bloco["_target"].eq(1).sum()),
                           participacao=len(bloco) / len(base),
                           idade_min=bloco["_idade_num"].min(),
                           idade_max=bloco["_idade_num"].max()))
    return pd.DataFrame(linhas).sort_values("status").reset_index(drop=True)


def visualizar_exploracao(base: pd.DataFrame, cfg: ConfigIdade):
    """Distribuição, bad rate por idade e qualidade por safra."""
    validos = base.loc[base._idade_status.eq("VALIDA")].copy()
    validos["idade_inteira"] = np.floor(validos._idade_num).astype(int)
    anual = validos.groupby("idade_inteira").agg(
        qtd_total=("_target", "size"), qtd_performance=("_target", "count"),
        qtd_maus=("_target", lambda s: int(s.eq(1).sum()))).reset_index()
    anual["qtd_bons"] = anual.qtd_performance - anual.qtd_maus
    anual["bad_rate"] = anual.qtd_maus / anual.qtd_performance.replace(0, np.nan)
    anual["ic_inf"], anual["ic_sup"] = _wilson(anual.qtd_maus, anual.qtd_performance)
    tem_safra = cfg.safra_col is not None
    fig, axes = plt.subplots(1, 3 if tem_safra else 2,
                             figsize=(18 if tem_safra else 14, 4),
                             constrained_layout=True)
    axes[0].hist(validos._idade_num, bins=_bins_histograma(validos._idade_num),
                 color="#4878a8", edgecolor="white")
    axes[0].set(title="Distribuição de idade no treino", xlabel="Idade", ylabel="Registros")
    observaveis = anual.loc[anual.qtd_performance.gt(0)]
    axes[1].errorbar(observaveis.idade_inteira, observaveis.bad_rate,
                     yerr=[observaveis.bad_rate - observaveis.ic_inf,
                           observaveis.ic_sup - observaveis.bad_rate],
                     fmt="o-", markersize=3, linewidth=1, capsize=2, color="#bd5a38")
    axes[1].set(title="Bad rate por idade inteira (IC de Wilson)",
                xlabel="Idade", ylabel="Bad rate", ylim=(0, 1))
    if tem_safra:
        qualidade = base.groupby(
            [cfg.safra_col, "_idade_status"]).size().unstack(fill_value=0).reindex(
                cfg.ordem_safras, fill_value=0)
        qualidade = qualidade.div(qualidade.sum(axis=1), axis=0)
        cores = {"IDADE_AUSENTE": "#d8a35d", "IDADE_INVALIDA": "#b8b8b8",
                 "VALIDA": "#4878a8"}
        qualidade.plot(kind="bar", stacked=True, ax=axes[2],
                       color=[cores[c] for c in qualidade.columns])
        axes[2].set(title="Qualidade da idade por safra", xlabel="Safra",
                    ylabel="Participação", ylim=(0, 1))
        axes[2].tick_params(axis="x", rotation=45)
    return fig, anual


def ajustar_cortes(base_ajuste: pd.DataFrame, metodo: str, k: int,
                   cfg: ConfigIdade) -> tuple[float, ...]:
    """Ajusta cortes apenas nas linhas recebidas, inclusive dentro de cada dobra."""
    idade = base_ajuste.loc[base_ajuste._idade_status.eq("VALIDA"), "_idade_num"]
    if idade.nunique() < 2:
        return ()
    if metodo == "quantis":
        cortes = np.quantile(idade, np.arange(1, k) / k)
    elif metodo == "largura_igual":
        cortes = np.linspace(idade.min(), idade.max(), k + 1)[1:-1]
    elif metodo == "arvore":
        rotulados = base_ajuste.loc[
            base_ajuste._idade_status.eq("VALIDA") & base_ajuste._target.notna()]
        if rotulados._target.nunique() < 2 or len(rotulados) < 2 * cfg.min_total:
            return ()
        arvore = DecisionTreeClassifier(
            max_leaf_nodes=k, min_samples_leaf=max(2, cfg.min_total),
            random_state=cfg.semente)
        arvore.fit(rotulados[["_idade_num"]], rotulados["_target"].astype(int))
        cortes = arvore.tree_.threshold[arvore.tree_.feature >= 0]
    else:
        raise ValueError(f"Método desconhecido: {metodo}.")
    minimo, maximo = float(idade.min()), float(idade.max())
    return tuple(sorted({round(float(c), 6) for c in cortes if minimo < c < maximo}))


def aplicar_cortes(base: pd.DataFrame, cortes: tuple[float, ...]) -> pd.Series:
    """Aplica limites fixos; cutpoint pertence à faixa superior: [a, b)."""
    saida = base["_idade_status"].astype(object).copy()
    validos = base._idade_status.eq("VALIDA")
    indices = np.searchsorted(np.asarray(cortes, dtype=float),
                              base.loc[validos, "_idade_num"].to_numpy(), side="right")
    saida.loc[validos] = [f"F{i + 1:02d}" for i in indices]
    return saida


def _dobras(base: pd.DataFrame, cfg: ConfigIdade):
    if cfg.safra_col and len(cfg.ordem_safras) >= 2:
        safra = base[cfg.safra_col]
        for i in range(1, len(cfg.ordem_safras)):
            ajuste = np.flatnonzero(safra.isin(cfg.ordem_safras[:i]))
            avaliacao = np.flatnonzero(safra.eq(cfg.ordem_safras[i]))
            if len(ajuste) and len(avaliacao):
                yield ajuste, avaliacao
    else:
        n = min(cfg.cv_dobras, len(base))
        for ajuste, avaliacao in KFold(n_splits=n, shuffle=True,
                                      random_state=cfg.semente).split(base):
            yield ajuste, avaliacao


def _ganho_cv(base: pd.DataFrame, metodo: str, k: int,
              cfg: ConfigIdade) -> tuple[float, float, int]:
    ganhos = []
    for indices_ajuste, indices_avaliacao in _dobras(base, cfg):
        ajuste = base.iloc[indices_ajuste]
        avaliacao = base.iloc[indices_avaliacao]
        ajuste_rotulado = ajuste.loc[ajuste._target.notna()]
        avaliacao_rotulada = avaliacao.loc[avaliacao._target.notna()]
        if ajuste_rotulado._target.nunique() < 2 or avaliacao_rotulada.empty:
            continue
        cortes = ajustar_cortes(ajuste, metodo, k, cfg)
        if not cortes:
            continue
        faixa_ajuste = aplicar_cortes(ajuste_rotulado, cortes)
        faixa_avaliacao = aplicar_cortes(avaliacao_rotulada, cortes)
        taxas = ajuste_rotulado.assign(_faixa=faixa_ajuste).groupby("_faixa")._target.agg(
            ["sum", "count"])
        taxas = (taxas["sum"] + 0.5) / (taxas["count"] + 1.0)
        media = float((ajuste_rotulado._target.sum() + 0.5) /
                      (len(ajuste_rotulado) + 1.0))
        previsto = faixa_avaliacao.map(taxas).fillna(media).to_numpy(dtype=float)
        y = avaliacao_rotulada._target.to_numpy(dtype=float)
        previsto = np.clip(previsto, 1e-8, 1 - 1e-8)
        perda = -np.mean(y * np.log(previsto) + (1 - y) * np.log(1 - previsto))
        perda_base = -np.mean(y * np.log(media) + (1 - y) * np.log(1 - media))
        ganhos.append(float(perda_base - perda))
    if not ganhos:
        return np.nan, np.nan, 0
    # Com uma única dobra temporal não há estimativa de incerteza: a regra
    # de escolha posterior prefere a solução mais simples entre as viáveis.
    erro = (float(np.std(ganhos, ddof=1) / sqrt(len(ganhos)))
            if len(ganhos) >= 2 else np.inf)
    return float(np.mean(ganhos)), erro, len(ganhos)


def _avaliar_candidato(base: pd.DataFrame, cortes: tuple[float, ...],
                       cfg: ConfigIdade) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    faixa = aplicar_cortes(base, cortes)
    categorias = [f"F{i + 1:02d}" for i in range(len(cortes) + 1)]
    tabela = base.assign(faixa=faixa).groupby("faixa")._target.agg(
        qtd_total="size", qtd_performance="count",
        qtd_maus=lambda s: int(s.eq(1).sum())).reindex(categorias, fill_value=0)
    tabela["qtd_bons"] = tabela.qtd_performance - tabela.qtd_maus
    tabela["participacao"] = tabela.qtd_total / len(base)
    tabela["bad_rate"] = tabela.qtd_maus / tabela.qtd_performance.replace(0, np.nan)
    tabela["ic_inf"], tabela["ic_sup"] = _wilson(tabela.qtd_maus, tabela.qtd_performance)
    tabela = tabela.reset_index()
    tabela.insert(1, "intervalo", descrever_intervalos(cortes, cfg))
    contagens_ok = bool((
        tabela.qtd_total.ge(cfg.min_total)
        & tabela.qtd_performance.ge(cfg.min_performance)
        & tabela.qtd_bons.ge(cfg.min_bons)
        & tabela.qtd_maus.ge(cfg.min_maus)).all())
    cobertura = float(tabela.qtd_total.sum() / len(base))
    temporal = pd.DataFrame()
    desvio_maximo = np.nan
    presenca_minima = np.nan
    estavel = True
    if cfg.safra_col:
        grade = pd.MultiIndex.from_product(
            [cfg.ordem_safras, categorias], names=[cfg.safra_col, "faixa"])
        temporal = base.assign(faixa=faixa).groupby(
            [cfg.safra_col, "faixa"]).size().reindex(grade, fill_value=0).rename(
                "qtd_total").reset_index()
        totais = base.groupby(cfg.safra_col).size().rename("total_safra")
        temporal["participacao"] = (temporal.qtd_total /
                                      temporal[cfg.safra_col].map(totais))
        referencia = tabela.set_index("faixa").participacao
        temporal["desvio_relativo"] = (
            temporal.participacao / temporal.faixa.map(referencia) - 1).abs()
        desvio_maximo = float(temporal.desvio_relativo.max())
        presenca_minima = float(temporal.groupby("faixa").qtd_total.apply(
            lambda s: s.gt(0).mean()).min())
        estavel = (desvio_maximo <= cfg.desvio_relativo_maximo and
                   presenca_minima >= cfg.presenca_temporal_minima)
    return tabela, temporal, dict(contagens_ok=contagens_ok,
                                  cobertura=cobertura, estavel=estavel,
                                  desvio_relativo_maximo=desvio_maximo,
                                  presenca_minima=presenca_minima,
                                  menor_total=int(tabela.qtd_total.min()),
                                  menor_performance=int(tabela.qtd_performance.min()),
                                  menor_bons=int(tabela.qtd_bons.min()),
                                  menor_maus=int(tabela.qtd_maus.min()))


def comparar_esquemas(base: pd.DataFrame, cfg: ConfigIdade,
                      metodos: tuple[str, ...] = ("quantis", "largura_igual", "arvore")):
    """Compara alternativas e guarda tabelas por faixa sem acessar teste."""
    linhas = []
    detalhes = {}
    for metodo in metodos:
        for k in range(cfg.k_min, cfg.k_max + 1):
            cortes = ajustar_cortes(base, metodo, k, cfg)
            if not cortes:
                continue
            tabela, temporal, indicadores = _avaliar_candidato(base, cortes, cfg)
            ganho, erro, n_dobras = _ganho_cv(base, metodo, k, cfg)
            cid = f"{metodo}_k{k}"
            viavel = (indicadores["contagens_ok"] and
                      indicadores["cobertura"] >= cfg.cobertura_minima and
                      indicadores["estavel"] and n_dobras > 0)
            linhas.append(dict(candidato=cid, metodo=metodo, k_solicitado=k,
                               n_faixas=len(cortes) + 1, cortes=cortes,
                               viavel=viavel, ganho_logloss_cv=ganho,
                               erro_padrao_cv=erro, dobras_cv=n_dobras,
                               **indicadores))
            detalhes[cid] = {"faixas": tabela, "temporal": temporal, "cortes": cortes}
    if not linhas:
        raise ValueError("Nenhum esquema de cortes pôde ser ajustado no treino.")
    return pd.DataFrame(linhas).sort_values(
        ["viavel", "n_faixas", "candidato"], ascending=[False, True, True]
    ).reset_index(drop=True), detalhes


def escolher_esquema(comparacao: pd.DataFrame) -> pd.Series:
    """Escolhe a solução viável mais simples dentro de 1 EP do melhor ganho CV."""
    viaveis = comparacao.loc[comparacao.viavel & comparacao.ganho_logloss_cv.notna()]
    if viaveis.empty:
        raise ValueError("Nenhuma discretização passou nos limites; examine a tabela e revise a política.")
    melhor = viaveis.loc[viaveis.ganho_logloss_cv.idxmax()]
    tolerancia = melhor.erro_padrao_cv
    finalistas = viaveis.loc[
        viaveis.ganho_logloss_cv >= melhor.ganho_logloss_cv - tolerancia].copy()
    finalistas["_desvio"] = finalistas.desvio_relativo_maximo.fillna(0)
    return finalistas.sort_values(
        ["n_faixas", "_desvio", "ganho_logloss_cv", "candidato"],
        ascending=[True, True, False, True]).iloc[0].drop(labels="_desvio")


def visualizar_comparacao(comparacao: pd.DataFrame, escolhido: pd.Series):
    fig, ax = plt.subplots(figsize=(max(9, len(comparacao) * 0.5), 4),
                           constrained_layout=True)
    x = np.arange(len(comparacao))
    cores = np.where(comparacao.viavel, "#398a63", "#b8b8b8")
    ax.bar(x, comparacao.ganho_logloss_cv, color=cores)
    finitos = np.isfinite(comparacao.erro_padrao_cv)
    ax.errorbar(x[finitos], comparacao.loc[finitos, "ganho_logloss_cv"],
                yerr=comparacao.loc[finitos, "erro_padrao_cv"],
                fmt="none", color="black", capsize=2)
    selecionado = int(comparacao.index[comparacao.candidato.eq(escolhido.candidato)][0])
    ax.scatter([selecionado], [comparacao.loc[selecionado, "ganho_logloss_cv"]],
               marker="*", s=180, color="#d08b20", zorder=5)
    ax.set(xticks=x, xticklabels=comparacao.candidato, ylabel="Ganho de log-loss no CV",
           title="Verde: viável; estrela: escolhido")
    ax.tick_params(axis="x", rotation=75)
    ax.axhline(0, color="black", linewidth=0.8)
    return fig


def visualizar_escolhido(base: pd.DataFrame, cfg: ConfigIdade,
                         escolhido: pd.Series, detalhes: dict):
    """Mostra cortes na idade, volumes, bad rates e composição por safra."""
    info = detalhes[escolhido.candidato]
    cortes = info["cortes"]
    tabela = info["faixas"]
    temporal = info["temporal"]
    tem_safra = not temporal.empty
    fig, axes = plt.subplots(1, 3 if tem_safra else 2,
                             figsize=(17 if tem_safra else 12, 4),
                             constrained_layout=True)
    validos = base.loc[base._idade_status.eq("VALIDA"), "_idade_num"]
    axes[0].hist(validos, bins=_bins_histograma(validos),
                 color="#4878a8", edgecolor="white")
    for corte in cortes:
        axes[0].axvline(corte, color="#bd5a38", linestyle="--", linewidth=1.5)
    axes[0].set(title="Cortes sobre a distribuição do treino",
                xlabel="Idade", ylabel="Registros")
    x = np.arange(len(tabela))
    axes[1].bar(x, tabela.qtd_total, color="#4878a8", alpha=0.75)
    axes[1].set(xticks=x, xticklabels=tabela.faixa, title="Volume e bad rate por faixa",
                xlabel="Faixa", ylabel="Registros")
    risco = axes[1].twinx()
    risco.errorbar(x, tabela.bad_rate,
                   yerr=[tabela.bad_rate - tabela.ic_inf,
                         tabela.ic_sup - tabela.bad_rate],
                   fmt="o", color="#bd5a38", capsize=3)
    risco.set(ylabel="Bad rate", ylim=(0, 1))
    if tem_safra:
        matriz = temporal.pivot(index="faixa", columns=cfg.safra_col,
                                values="participacao").reindex(
                                    index=tabela.faixa, columns=cfg.ordem_safras)
        im = axes[2].imshow(matriz.to_numpy(), aspect="auto", cmap="Blues")
        axes[2].set(xticks=np.arange(len(matriz.columns)),
                    xticklabels=matriz.columns, yticks=np.arange(len(matriz.index)),
                    yticklabels=matriz.index, title="Participação por safra")
        fig.colorbar(im, ax=axes[2], label="Fração da safra")
    return fig


def especificacao_final(escolhido: pd.Series, cfg: ConfigIdade) -> dict:
    cortes = [float(x) for x in escolhido.cortes]
    intervalos = descrever_intervalos(tuple(cortes), cfg)
    return dict(variable=cfg.idade_col, target_used_only_in_training=cfg.target_col,
                cutpoints=cortes,
                interval_rule="[inferior, superior); última faixa inclui idade_max",
                bins=[{"label": f"F{i + 1:02d}", "interval": intervalo}
                      for i, intervalo in enumerate(intervalos)],
                missing_label="IDADE_AUSENTE", invalid_label="IDADE_INVALIDA",
                valid_domain=[cfg.idade_min, cfg.idade_max],
                selected_method=escolhido.metodo,
                requested_bins=int(escolhido.k_solicitado),
                actual_bins=int(escolhido.n_faixas),
                candidate_id=escolhido.candidato,
                training_only=True, config=asdict(cfg))


def salvar_especificacao(especificacao: dict, caminho: str | Path) -> Path:
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        raise FileExistsError(f"A especificação já existe: {destino}")
    destino.write_text(json.dumps(especificacao, ensure_ascii=False, indent=2,
                                  default=str) + "\n", encoding="utf-8")
    return destino
