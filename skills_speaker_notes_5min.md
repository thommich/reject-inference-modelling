# Roteiro de Apresentação (5 min) — Fluxos Agênticos para Diagnóstico
**Melhores do Ano · RT 2026**
**Tempo total:** 5 minutos (~650 palavras, ritmo natural de ~130 palavras/min)

---

## 1. Abertura e Gancho (`0:00 – 0:45`)
*(Aponte para o título do slide)*

> "Bom dia / boa tarde, pessoal. O projeto que a gente traz para o Melhores do Ano é o **Fluxos Agênticos para Diagnóstico** — uma iniciativa que muda a forma como o Crédito PF investiga, valida e explica seus modelos em produção.
>
> Para começar, queria fazer uma provocação rápida para quem trabalha com modelos aqui na RT: **quantas vezes nós já investigamos exatamente o mesmo desvio de monitoramento do zero?** Ou quantas vezes alguém precisou parar tudo por horas só para montar um pipeline e responder por que o score de um cliente ou a distribuição de um GH mudou?
>
> Foi olhando para esse trabalho repetitivo que o projeto nasceu."

---

## 2. Card 1 — `O QUE MOTIVOU?` (`0:45 – 2:15`)
*(Direcione o olhar para o card da esquerda: título e as duas dores numeradas)*

> "Olhando aqui para o primeiro card: **diagnosticar modelos sempre foi um trabalho artesanal.** Lento, refeito à mão a cada rodada e muito dependente do conhecimento tácito de poucos especialistas do time. Quando um especialista não estava disponível ou mudava de escopo, o histórico daquele modelo praticamente ia junto.
>
> Na rotina de Crédito PF, isso aparecia em **duas dores constantes**:
>
> - **A primeira é a Validação de Distribuição** — responder *'podemos liberar este score ou GH para as áreas do banco?'*. Cada desvio apontado pelo monitoramento exigia abrir tabelas, cruzar dashboards, olhar código e justificar tudo manualmente — **toda vez**, mesmo quando a causa era recorrente.
> - **A segunda é a Explicabilidade** — responder *'por que o modelo tomou essa decisão para este cliente, ou por que houve migração de rating/GH nessa população?'*. Responder isso exigia montar artesanalmente um pipeline inteiro de análise.
>
> *(Aponte para o medalhão `KB` e para o bloco `A OPORTUNIDADE` na base do card)*
>
> A nossa **oportunidade** foi clara: e se, em vez de só automatizar código, a gente criasse **fluxos agênticos** onde cada investigação alimenta uma **Base de Conhecimento coletiva (a nossa KB)**? Assim a gente acelera a operação hoje e transforma conhecimento tácito em um ativo permanente do time."

---

## 3. Card 2 (Topo) — A Solução e o Ganho de Velocidade (`2:15 – 3:30`)
*(Mova para o card da direita: título e comparativo de barras `≈12×`)*

> "É isso que entrega o segundo card. Nós desenvolvemos **duas skills agênticas complementares** que rodam direto no nosso ambiente analítico no **SageMaker**, integradas ao **AletheIA**, cobrindo o ciclo ponta a ponta: detectar, justificar e explicar.
>
> 1. A **Skill de Validação de Distribuição** conduz o analista de forma conversacional pelo caminho **hipótese → evidência → parecer**. Ela usa um mapa compartilhado dos modelos — tabelas, dashboards, código, pipelines — e *playbooks* reutilizáveis por tipo de desvio, que aprendem e se auto-corrigem a cada uso.
> 2. Já a **Skill de Explicabilidade** parte de uma simples frase em linguagem natural e entrega uma **análise SHAP completa**, já interpretada por IA e em formato de relatório pronto — tanto para explicar um cliente individual quanto para explicar migrações de GH de uma safra inteira.
>
> O impacto imediato na ponta aparece nesse número: investigações de validação que chegavam a tomar **até 3 horas** nos casos mais trabalhosos hoje são concluídas em **cerca de 15 minutos** — **aproximadamente 12 vezes mais rápido**, com uma análise consolidada e muito mais robusta."

---

## 4. Card 2 (Base) — Governança, Democratização e Escala (`3:30 – 4:30`)
*(Aponte para os 3 chips de qualidade e para o banner `≈15 MODELOS`)*

> "Mas tão importante quanto a velocidade é a mudança de patamar em três frentes:
>
> - Primeiro, **Governança (`AUDITÁVEL`)**: saímos de decisões tácitas para pareceres padronizados e auditáveis, com todas as fontes, métodos e evidências rastreáveis que apontam a causa-raiz do desvio.
> - Segundo, **Agilidade (`SOB DEMANDA`)**: uma frase gera o relatório completo de SHAP + IA, transformando horas de preparação em uma execução guiada.
> - Terceiro, **Escala no time (`DEMOCRATIZADO`)**: qualquer analista ou cientista da área consegue rodar um diagnóstico profundo, sem depender da agenda de quem criou o modelo.
>
> E o efeito composto já é real: o nosso acervo coletivo já cobre **cerca de 15 modelos do portfólio**, disseminando causas recorrentes *cross-modelo* que antes ficavam restritas a poucos especialistas."

---

## 5. Fechamento — Por que Merece Ser Destaque em 2026 (`4:30 – 5:00`)
*(Aponte para a linha `ATIVOS RT` no rodapé do card da direita)*

> "Para fechar: por que essa iniciativa merece ser destaque em 2026?
>
> Porque ela não entrega apenas um ganho pontual — ela deixa **três ativos vivos para a RT** (*Skill de Validação, Skill de Explicabilidade e a KB de diagnóstico*) e inaugura um novo modo de trabalhar com IA agêntica aplicada direto na nossa operação no SageMaker.
>
> É uma solução que combina **produtividade**, **governança de risco** e **inteligência coletiva**: quanto mais o time usa, mais inteligente o diagnóstico do banco fica. Muito obrigado!"

---

## Guia Rápido de Tempo (Cola de Bolso)
| Tempo | Bloco | Âncora Visual no Slide |
| :--- | :--- | :--- |
| `0:00 – 0:45` | **Abertura e Gancho** | Título do slide |
| `0:45 – 2:15` | **Card 1 — Motivação** | `1` Validação · `2` Explicabilidade → Medalhão `KB` + `A OPORTUNIDADE` |
| `2:15 – 3:30` | **Card 2 — Solução e Velocidade** | Subtítulo SageMaker/AletheIA + `≈12×` (`até 3 h` → `~15 min`) |
| `3:30 – 4:30` | **Card 2 — Qualidade e Escala** | Chips `AUDITÁVEL` · `SOB DEMANDA` · `DEMOCRATIZADO` + `≈15 MODELOS` |
| `4:30 – 5:00` | **Fechamento (Por que merece vencer)** | Rodapé `ATIVOS RT` (`Skill Validação` · `Skill Explicabilidade` · `KB`) |
