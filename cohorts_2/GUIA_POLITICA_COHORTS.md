# Guia de preenchimento da política de cohorts

Este documento explica o arquivo JSON consumido por `definir_cohorts.py`. A
política controla a **primeira etapa**, que define cohorts a partir de um cubo
agregado. Ela não contém nomes, limites ou resultados de features candidatas.
O arquivo `politica_cohorts_simulada.json` é um exemplo preenchido com oito
características sintéticas. O mesmo formato serve para qualquer **N ≥ 1**
características: o programa avalia todas as `2^N − 1` combinações não vazias.

## Antes de preencher

- O CSV de entrada precisa ter as dimensões de segmentação e, se existirem,
  as colunas auxiliares de safra e amostra. **As últimas três colunas**, nessa
  ordem, são quantidade de maus, quantidade com performance conhecida e
  quantidade total. Seus nomes podem variar; a ordem não pode.
- O cubo deve conter total geral, células atômicas e totalizações necessárias
  para todas as combinações, safras e amostras informadas. Em cada célula,
  `0 ≤ maus ≤ performance ≤ total`.
- Use JSON válido: aspas duplas nas chaves e textos, `true`/`false` para
  booleanos, `null` para nulo e ponto como separador decimal. JSON não aceita
  comentários.
- Escolha os limites e perfis prioritários **antes** de consultar o desempenho
  de features candidatas. A justificativa estrutural de uma dimensão deve
  refletir sua definição e disponibilidade no momento em que o cohort será
  atribuído.

## Campos da raiz

| Campo | Tipo | Preenchimento e efeito |
| --- | --- | --- |
| `catalog_version` | Texto não vazio | Nome da versão do catálogo e da pasta de saída. Use um identificador novo quando mudar o cubo, a política ou o código. A execução recusa sobrescrever a mesma versão com conteúdo diferente. Prefira letras, números, `-` e `_`; não use barras ou caminhos. |
| `status` | Texto não vazio | Rótulo copiado para o catálogo, como `"demonstracao"` ou `"rascunho"`. O código **não** interpreta esse texto como aprovação de negócio nem impede uso posterior. |
| `total_marker` | Valor de categoria, geralmente texto | Valor exclusivo que identifica uma dimensão **totalizada** no cubo, por exemplo `"<TOTAL>"`. Se omitido ou `null`, o programa usa valores nulos como totalizações. Se nulo for uma categoria real, escolha um marcador diferente e reserve-o apenas para totalizações. |
| `col_safra` | Nome de coluna ou `null` | Coluna auxiliar de tempo, excluída das combinações. Use `null` ou omita quando não houver safras. Se informada, o cubo precisa dos rollups por safra. |
| `col_amostra` | Nome de coluna ou `null` | Coluna auxiliar da divisão de amostras, excluída das combinações. Use `null` ou omita se não houver essa divisão. Se informada, o cubo precisa dos rollups por amostra; quando houver safra, também dos recortes safra × amostra. |
| `development_sample` | Valor de amostra, opcional | Valor existente em `col_amostra` que identifica desenvolvimento. Só o V de Cramér dessa amostra pode desempatar combinações principais equivalentes após cobertura e simplicidade. Se omitido, não há esse desempate por risco. Se informado mas ausente do cubo, a execução falha. Sem `col_amostra`, o campo não tem efeito. |
| `dimensions` | Objeto com N entradas | Declara cada característica de segmentação e sua revisão estrutural. Veja a seção seguinte. |
| `cohort_minimums` | Objeto com quatro inteiros | Limites de volume e eventos usados no diagnóstico geral e na viabilidade das combinações por amostra. Veja “Limites de contagem”. |
| `sample_minimums` | Objeto com quatro inteiros | Limites adicionais exigidos de **cada cohort selecionável em cada amostra**, somando suas safras. É obrigatório no JSON atual mesmo quando `col_amostra` é `null`; nesse caso não afeta a seleção. |
| `minimum_eligible_coverage` | Número de 0 a 1 | Fração mínima do público total em cohorts elegíveis. O diagnóstico aplica o valor ao total e a cada amostra; a seleção também o aplica à cobertura por cohorts que passaram nos limites e na estabilidade. `0.8` significa 80%. |
| `minimum_profile_coverage` | Número de 0 a 1 | Fração mínima exigida **para cada** perfil em `priority_profiles` no conjunto final de combinações. Se algum perfil ficar abaixo do limite, o catálogo não é emitido. `0.8` significa 80%, não 0,8 ponto percentual. |
| `temporal` | Objeto | Configura a estabilidade da composição e a indicação de suficiência do sinal de risco. Veja “Estabilidade temporal”. |
| `priority_profiles` | Lista de objetos | Perfis cuja cobertura deve ser preservada. Pode ser vazia, mas assim não há proteção explícita de perfis minoritários. Veja “Perfis prioritários”. |
| `maximum_supplementary` | Inteiro não negativo | Número máximo de **combinações** suplementares além da principal. `0` mantém só a partição principal. Não é o número máximo de cohorts. |

### `dimensions`: uma entrada por característica

As chaves desse objeto são os **nomes exatos das colunas** de segmentação no
CSV, excluindo `col_safra` e `col_amostra`. Inclua todas as N dimensões que
serão analisadas. A ordem das chaves fixa a posição dos bits do
`combination_id`; alterá-la muda os IDs e exige uma nova versão do catálogo.
A ordem física das colunas no CSV pode ser diferente, desde que os nomes
correspondam e as três contagens permaneçam no fim.

Cada dimensão contém:

| Subcampo | Tipo | Preenchimento e efeito |
| --- | --- | --- |
| `approved` | Booleano | `true` permite que combinações contendo essa dimensão sejam candidatas à seleção; `false` exclui essas combinações da escolha. **Todas** continuam no diagnóstico das `2^N − 1` combinações. |
| `rationale` | Texto não vazio | Justificativa estrutural registrada na política. Preencha mesmo se `approved` for `false`. Descreva significado, disponibilidade na data da decisão, regras de categorização e motivo da aprovação ou rejeição. O programa exige texto, mas não verifica se a justificativa de negócio é suficiente. |

Exemplo de uma entrada:

```json
"origem": {
  "approved": true,
  "rationale": "Origem conhecida antes da decisão; categorias e tratamento de ausentes documentados."
}
```

### `cohort_minimums` e `sample_minimums`: limites de contagem

Os dois objetos usam as mesmas quatro chaves, com **inteiros não negativos**:

| Chave | O que conta |
| --- | --- |
| `qtd_total` | Todos os registros, inclusive os que não têm performance conhecida. |
| `qtd_performance` | Registros com target conhecido, bom ou mau. Mesmo se configurado como zero, o diagnóstico exige ao menos um para que a bad rate tenha denominador. |
| `qtd_bons` | Registros com target bom: `qtd_performance − qtd_maus`. |
| `qtd_maus` | Registros com target mau. |

`cohort_minimums` define `elegivel` para cada grupo no total geral. Quando há
`col_amostra`, o diagnóstico reaplica **esses mesmos limites absolutos** aos
grupos de cada amostra para decidir se a combinação é viável nessa amostra.
A combinação precisa de pelo menos dois grupos elegíveis e da cobertura
`minimum_eligible_coverage` no geral e em cada amostra.

`sample_minimums` é outra verificação: cada cohort que poderá entrar no
catálogo deve atingir seus quatro limites **individualmente em cada amostra**.
As contagens dessa verificação são somadas ao longo das safras. Ela não exige
os limites em cada safra separadamente. Se as duas amostras tiverem tamanhos
diferentes, escolha os limites considerando essa divisão; a política simulada
usa os mesmos números nos dois objetos apenas para demonstrar o fluxo.

### `temporal`: estabilidade e sinal de risco

| Subcampo | Tipo | Preenchimento e efeito |
| --- | --- | --- |
| `required` | Booleano | Se `true`, a estabilidade temporal é requisito para cada cohort selecionável e `col_safra` precisa estar informado. Se `false`, os indicadores temporais podem ser calculados, mas não barram a seleção. Sem safra, use `false`. |
| `minimum_presence_fraction` | Número de 0 a 1 | Fração mínima de recortes em que o cohort precisa ter `qtd_total > 0`. Com safra e amostra, os recortes são as células amostra × safra. `1.0` exige presença em todas. |
| `maximum_relative_share_shift` | Número ≥ 0 | Maior desvio relativo permitido entre a participação do cohort em cada recorte e sua participação no total geral. A fórmula é `abs(participacao_do_recorte / participacao_geral − 1)`. Por exemplo, `0.75` permite de 25% a 175% da participação geral; **não** representa 75 pontos percentuais. |
| `minimum_bad_for_risk_signal` | Inteiro | Mínimo de maus em **cada recorte da tabela por amostra** para rotular o sinal de risco como `avaliavel` no catálogo. Abaixo disso, o rótulo é `inconclusivo`. Esse campo **não barra a seleção** nem altera a bad rate; sem `col_amostra`, o rótulo atual é `nao_avaliado`. |

Os limites de presença e desvio são usados como filtros apenas se
`required=true`. Um cohort pode ter volume suficiente no total e, ainda
assim, falhar por desaparecer ou mudar muito de participação entre períodos.
O limite de maus para o *rótulo* do sinal de risco é distinto dos mínimos de
elegibilidade.

### `priority_profiles`: cobertura de perfis específicos

Cada item da lista tem:

| Subcampo | Tipo | Preenchimento e efeito |
| --- | --- | --- |
| `id` | Texto único | Nome estável para identificar o perfil nas decisões e no catálogo. IDs repetidos são rejeitados. |
| `conditions` | Objeto não vazio | Pares `"dimensão": valor` que definem o perfil. Todos os nomes precisam existir em `dimensions`. Várias condições formam uma **interseção**: o registro deve satisfazer todas. Os valores precisam corresponder às categorias lidas do CSV. |

Exemplo: `{"origem": "B", "regiao": "interior"}` representa a interseção
entre origem B e região interior. Use `null` para uma categoria genuinamente
ausente, desde que `total_marker` seja diferente de nulo. O perfil precisa
existir nas células atômicas do cubo; caso contrário, a execução falha.

Uma combinação só recebe crédito por proteger o perfil se incluir **todas**
as dimensões de `conditions` e tiver cohorts aptos que o cubram. A cobertura
é `população do perfil coberta / população total do perfil`, calculada pela
união das células atômicas; a mesma pessoa não é contada duas vezes quando
combinações se sobrepõem. Cada perfil deve atingir
`minimum_profile_coverage`.

### `maximum_supplementary`: como entram combinações adicionais

Após os filtros, o programa escolhe uma combinação **principal** considerando,
nessa ordem, quantidade e cobertura dos perfis prioritários, cobertura geral,
menor número de grupos, menor número de dimensões e, somente como desempate
final, V de Cramér da amostra de desenvolvimento quando disponível. Depois
adiciona até `maximum_supplementary` combinações que tragam cobertura
adicional de perfis, dimensões novas ou população adicional.

Os cohorts suplementares **podem se sobrepor** aos da principal. Somente a
principal define uma atribuição exclusiva para cada registro. Folhas não
aptas da principal são identificadas na `fallback` (reserva), que não é
marcada como apta para modelagem. O catálogo registra o ganho marginal de
cada combinação selecionada.

## Exemplo mínimo com três características

O bloco abaixo mostra a **estrutura** para outro cubo. Substitua nomes,
categorias, justificativas e limites pelos do seu caso; a categoria
`"parceiro"` precisa existir na coluna `origem` do CSV para que o exemplo
rode.

```json
{
  "catalog_version": "meu-cubo-v1",
  "status": "rascunho",
  "total_marker": "<TOTAL>",
  "col_safra": null,
  "col_amostra": null,
  "dimensions": {
    "porte": {
      "approved": true,
      "rationale": "Definição e disponibilidade do porte antes da decisão."
    },
    "origem": {
      "approved": true,
      "rationale": "Origem conhecida antes da decisão; categorias documentadas."
    },
    "regiao": {
      "approved": true,
      "rationale": "Região disponível e categorização estável."
    }
  },
  "cohort_minimums": {
    "qtd_total": 100,
    "qtd_performance": 80,
    "qtd_bons": 50,
    "qtd_maus": 10
  },
  "sample_minimums": {
    "qtd_total": 100,
    "qtd_performance": 80,
    "qtd_bons": 50,
    "qtd_maus": 10
  },
  "minimum_eligible_coverage": 0.8,
  "minimum_profile_coverage": 0.8,
  "temporal": {
    "required": false,
    "minimum_presence_fraction": 1.0,
    "maximum_relative_share_shift": 0.75,
    "minimum_bad_for_risk_signal": 10
  },
  "priority_profiles": [
    {
      "id": "origem_parceiro",
      "conditions": {"origem": "parceiro"}
    }
  ],
  "maximum_supplementary": 2
}
```

Com três características, são avaliadas `2^3 − 1 = 7` combinações. Com oito,
`2^8 − 1 = 255`. Os números acima são apenas ilustrativos: limites excessivos
podem deixar nenhuma combinação admissível ou impedir a cobertura do perfil.

## Execução e conferência

```bash
python definir_cohorts.py --cubo dados/cubo.csv --politica dados/politica.json --saida saidas
```

Confira, na pasta `saidas/<catalog_version>/`:

1. `decisions.csv`: uma decisão e seus motivos para cada uma das
   `2^N − 1` combinações;
2. `catalogo_cohorts.json`: versão, hashes, combinação principal,
   suplementares, reserva e cobertura de cada perfil prioritário;
3. `cohort_detail.csv` e `cohort_partition.csv`: contagens, elegibilidade e
   presença por recorte para investigar exclusões.

Se uma execução precisar mudar, revise a política, atribua uma **nova**
`catalog_version` e preserve o catálogo anterior. O texto de `status` e
`approved=true` não substituem a revisão de negócio das definições.
