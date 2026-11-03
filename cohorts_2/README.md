# Definição sequencial de cohorts a partir de um cubo Pandas

Use Python 3.10+ com as dependências de `requirements.txt`.

`analisar_cubo` recebe **um DataFrame já agregado em formato de cubo**. Não lê
registros individuais nem constrói o cubo. Cada linha representa uma célula
observada ou uma totalização do cubo. `selecionar_cohorts` recebe esse cubo,
o diagnóstico e uma política JSON. A seleção usa somente dimensões de
segmentação, contagens, estabilidade e sinais descritivos de bad rate. Nenhuma
feature candidata participa da definição do catálogo.

## Contrato de entrada

As primeiras colunas são dimensões de segmentação. Opcionalmente, uma delas
pode ser `safra` e outra `amostra`. **As últimas três colunas**, nesta ordem,
devem conter:

1. Quantidade de maus (`target = 1`).
2. Quantidade com performance disponível (`target = 0` ou `1`).
3. Quantidade total, incluindo target ausente.

O cubo deve incluir o total geral e os rollups de todas as combinações de
N características analisadas (2^N - 1 combinações não vazias). Se usar
`safra` ou `amostra`, inclua também os rollups correspondentes, inclusive a
interseção safra × amostra. Em cada célula deve valer
`0 <= maus <= performance <= total`. As contagens das células de uma
partição devem reproduzir as três contagens do total geral.

Por padrão, `NaN`/`None` identifica uma dimensão totalizada. Caso haja
categorias genuinamente nulas, use **outro marcador exclusivo** nas células
totalizadoras, por exemplo `"<TOTAL>"`, e passe `marcador_total="<TOTAL>"`.
Sem essa distinção, um nulo real e um subtotal SQL são indistinguíveis.

## Uso

```python
from analise_cohorts import CriteriosElegibilidade, analisar_cubo

# df_cubo já é um pandas.DataFrame; as últimas colunas são
# ["qtd_maus", "qtd_performance", "qtd_total"].
resultado = analisar_cubo(
    df_cubo,
    col_safra="safra",        # omita se não houver dimensão temporal
    col_amostra="amostra",    # omita se não houver divisão de amostras
    marcador_total="<TOTAL>",
    criterios=CriteriosElegibilidade(
        minimo_total=1000,
        minimo_performance=500,
        minimo_bons=100,
        minimo_maus=30,
        cobertura_minima=0.80,
    ),
)

ranking = resultado.combination_summary
grupos = resultado.cohort_detail
evolucao = resultado.cohort_temporal
incrementos = resultado.combination_comparison

print(ranking[["ranking", "combination_id", "combinacao", "qtd_grupos",
               "cobertura_elegivel", "instabilidade_participacao_pp",
               "fronteira_pareto"]].head(20))
```

Se todas as primeiras colunas forem características, `caracteristicas` é
inferido automaticamente. Também é possível fornecê-lo explicitamente para
definir a ordem dos bits do `combination_id`. Esse identificador é a chave de
ligação entre as tabelas; o rótulo textual é apenas para leitura.

Para uma execução completa com **qualquer N**, crie uma política JSON com uma
entrada em `dimensions` para cada característica, na mesma ordem das colunas
do cubo. `politica_cohorts_simulada.json` mostra o esquema e os limites da
demonstração. Consulte `GUIA_POLITICA_COHORTS.md` para a explicação de cada
campo. Ajuste justificativas, limites, perfis prioritários e versão
antes de usar outros dados. `status: "demonstracao"` identifica explicitamente
o exemplo sintético; aprovação real das dimensões depende de revisão de
negócio. `development_sample` define a única amostra cujo V pode desempatar
opções equivalentes; as bad rates das demais amostras ficam descritivas.

```bash
python definir_cohorts.py --cubo caminho/para/cubo.csv \
    --politica caminho/para/politica.json --saida caminho/para/saidas
```

A saída é criada em `saidas/<catalog_version>/`. Repetir a execução com
conteúdo idêntico é permitido; tentar sobrescrever a mesma versão com dados,
política ou código divergente gera erro. Para uma mudança deliberada, publique
uma nova `catalog_version`.

## Saídas e critérios

- `combination_summary`: uma linha por subconjunto não vazio de
  características (255 linhas para oito características). Mostra grupos
  observados, suficiência amostral, cobertura, dispersão do bad rate, V de
  Cramér, IV, ganho sobre o melhor subconjunto imediato, estabilidade e
  fronteira de Pareto. O ranking põe primeiro as combinações viáveis e depois
  ordena por cobertura, estabilidade da participação e complexidade; V é
  apenas desempate. `viavel_global` exige ao menos dois
  grupos elegíveis e a cobertura mínima configurada no total geral; quando há
  `col_amostra`, `viavel_amostras` exige isso em **cada** amostra e `viavel`
  exige ambos. Sem `col_amostra`, `viavel` equivale a `viavel_global`.
- `cohort_detail`: uma linha por grupo observado em cada combinação, com
  volumes, bons, maus, performance ausente, participação no público total,
  bad rate, diferença para a bad rate geral em pontos percentuais, intervalo
  de Wilson e elegibilidade. Dimensões fora da combinação mantêm o marcador
  de totalização. `cohort_key` é estável mesmo que a ordem das linhas do cubo
  mude; `grupo_id` permanece uma chave curta dentro da combinação.
- `cohort_temporal`: grupo × safra, se `col_safra` for informado. A
  participação usa o total da safra e a bad rate relativa usa a bad rate da
  própria safra. A estabilidade da participação considera zero quando um
  grupo desaparece em determinada safra.
- `cohort_partition`: grade completa cohort × amostra × safra, ou cohort ×
  amostra quando não há safra. Células ausentes têm contagem zero e
  `presente=False`; as contagens conciliam com os rollups do cubo.
- `combination_comparison`: uma linha para cada relação entre uma combinação
  e um de seus subconjuntos imediatos, com variação de V, cobertura e número
  de grupos.
- `decisions`: decisão para **cada** combinação, com motivos de exclusão,
  cobertura estável, quantidade de cohorts aptos, ganho marginal de público
  e dimensões, e papel no catálogo.
- `catalog_cohorts` e `catalogo_cohorts.json`: cohorts selecionados, partição
  principal, combinações suplementares sobrepostas, reserva para grupos não
  aptos, política aplicada, hashes e proveniência. Só a partição principal
  atribui cada registro a exatamente um cohort ou à reserva. O catálogo
  registra a cobertura de cada perfil prioritário e não é emitido se algum
  ficar abaixo do mínimo da política.

Todas as bad rates, participações e coberturas são frações entre 0 e 1; campos
com sufixo `_pp` estão em **pontos percentuais**. Bad rate e medidas de risco
usam `qtd_performance` como denominador. As medidas de risco da combinação
consideram somente grupos elegíveis, ponderados pela quantidade com
performance disponível. O IV usa suavização de 0,5 por grupo para evitar
logaritmos indefinidos quando há zero bons ou maus. A fronteira de Pareto
maximiza cobertura e minimiza instabilidade da participação, número de grupos
e número de características, entre as combinações viáveis. A bad rate e o V
permanecem diagnósticos complementares. Quando há poucos maus em uma partição,
o catálogo marca o sinal de risco como inconclusivo.

Se `col_amostra` for informado, o resumo também traz o menor e maior V e a
menor cobertura elegível entre as amostras. Essas medidas usam os mesmos
critérios mínimos em cada amostra e ajudam a detectar dependência de uma
partição específica. Elas não substituem uma validação temporal final.

## Segunda fase: qualidade e poder preditivo das features

`avaliacao_features.py` recebe uma base por registro com as mesmas dimensões
do cubo, `safra`, `amostra`, target 0/1/NaN e colunas de features. A função
`avaliar_features` exige um `catalogo_cohorts.json` íntegro: usa somente os
IDs e cohorts aprovados na etapa 1, sem escolher combinações com base no
ranking ou nos resultados das features. Antes de avaliá-las, confere as
contagens de **todos** os grupos da combinação com o cubo; depois restringe
as métricas aos cohorts catalogados. `combinacoes` é opcional e só pode ser
um subconjunto dos IDs do catálogo.

```python
import json
from avaliacao_features import CriteriosFeature, avaliar_features

with open("saidas/versao/catalogo_cohorts.json", encoding="utf-8") as arquivo:
    catalogo = json.load(arquivo)

piloto = avaliar_features(
    dados_features,       # uma linha por registro, inclusive target ausente
    resultado,            # saída de analisar_cubo(df_cubo, ...)
    features=["bureau_score", "interno_score", "sinal_canal"],
    catalogo=catalogo,    # congelado antes da avaliação das features
    combinacoes=None,     # opcional; subconjunto dos IDs catalogados
    criterios=CriteriosFeature(
        minimo_avaliavel=500, minimo_bons=300, minimo_maus=70,
        cobertura_minima=0.65, auc_ci_inferior_min=0.55,
        iv_minimo_categorica=0.02,
    ),
)
```

As quatro tabelas dessa fase são:

- `feature_detail`: feature × cohort × amostra, com cobertura, missing,
  bons/maus avaliáveis, AUC, intervalo aproximado da AUC, IV, limite inferior
  do IV e marcação de aprovação.
- `feature_temporal`: as mesmas métricas por safra.
- `feature_summary`: comparação de cada feature entre cohorts na validação,
  incluindo menor cobertura, menor limite inferior de AUC/IV, dispersão
  temporal, diferença média validação menos desenvolvimento e quantos grupos
  atendem aos critérios.
- `combination_feature_summary`: número de features aprovadas em **todos** os
  cohorts, variação média de cobertura e AUC entre grupos e concordância
  média de Spearman dos rankings de IV entre cohorts no desenvolvimento.

Para features numéricas, a direção da AUC e os cortes de quantis usados no
IV são fixados na amostra de desenvolvimento e reaplicados na validação. A
aprovação exige cobertura e eventos suficientes, além de limite inferior do
intervalo aproximado da AUC acima do mínimo configurado. Para categóricas, a
aprovação usa o limite inferior da distribuição posterior do IV, obtido por
200 sorteios Dirichlet com suavização de 0,5. Missing é um bin explícito no
IV. AUC de feature constante ou de uma classe de target ausente fica nula.

## Exemplo simulado da primeira fase

`exemplo_simulado.py` gera um cubo reproduzível com oito características
(duas com três categorias), três safras e duas amostras. A dimensão `garantia`
tem uma categoria realmente nula, distinta de `<TOTAL>`. O comando executa
somente a definição de cohorts:

```bash
python exemplo_simulado.py
```

Os resultados novos ficam em
`exemplo_simulado/etapa1/simulado-20261026-v3/`. Os dez CSVs já presentes
diretamente em `exemplo_simulado/` são um registro da execução anterior e
não são sobrescritos. Use `--seed` e `--saida` para outra realização; altere
também a versão da política quando o conteúdo mudar. Com a semente padrão,
o total tem 309.362 registros, 262.974 com performance e 56.356 maus. As
255 combinações são avaliadas; 231 passam pelos limites de viabilidade da
política sintética. Nenhum desses números recomenda cohorts reais.

O gerador de registros e nove features sintéticas da etapa posterior está em
`exemplo_features_simulado.py` e não é importado pela execução da etapa 1.

## Execução dos testes

Com Pandas e NumPy instalados:

```bash
python -m unittest -v test_analise_cohorts.py test_selecao_cohorts.py test_avaliacao_features.py
```
