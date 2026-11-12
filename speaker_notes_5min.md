# Roteiro de Apresentação — Modelo de Longevidade (5 minutos)
**Evento:** Melhores do Ano • RT 2026  
**Duração estimada:** 5 minutos (~650 palavras a 130 palavras/min)

---

## 1. Abertura & Gancho (0:00 – 0:45)
> *[Olhe para a plateia; aponte brevemente para o título do slide]*

"Bom dia / Boa tarde a todos. Quando pensamos em modelagem de risco no Crédito PF, nossa intuição quase sempre começa pelo mesmo sinal: o atraso. O cliente começa a dar sinais de deterioração, atrasa uma parcela, entra em rolagem, e os nossos modelos tradicionais capturam esse comportamento.

Mas existe um risco relevante, estratégico e cada vez maior na nossa carteira em que **o atraso simplesmente não conta toda a história**. É sobre como nós resolvemos esse ponto cego — combinando dados inéditos, fronteira de Machine Learning e IA generativa — que eu quero falar com vocês hoje com o **Modelo de Longevidade**."

---

## 2. O Que Motivou? — Card da Esquerda (0:45 – 2:00)
> *[Direcione a atenção para o Card 1: "O QUE MOTIVOU?"]*

"Olhando para o card da esquerda: clientes de idade avançada representam uma parcela crescente do Crédito PF. E quando olhamos especificamente para o **Consignado INSS**, que é um produto de desconto direto em folha ou benefício, a dinâmica de perda funciona de um jeito completamente diferente da inadimplência convencional.

Vejam a linha do tempo no slide:
1. Quando ocorre o **óbito do titular**,
2. Há a **cessação imediata do benefício** junto ao INSS,
3. E isso gera a **interrupção abrupta do fluxo de pagamentos** para o banco.

O grande achado quando mergulhamos nos dados históricos foi contundente: **o óbito ocorre majoritariamente antes de qualquer sinal de atraso prévio**. Ou seja, para um modelo tradicional de crédito, esse cliente parecia perfeitamente saudável e adimplente até o momento em que o fluxo de caixa cessa de vez.

Não havia nenhum modelo interno olhando para esse fenômeno. A nossa grande oportunidade foi justamente criar uma **capacidade analítica inédita no Itaú Crédito PF**: sair de uma postura reativa e passar a **antecipar** esse risco para calibrar políticas de crédito mais assertivas e sustentáveis."

---

## 3. A Solução & Metodologia — Transição (2:00 – 3:00)
> *[Transição para o topo do Card 2: "PRINCIPAIS RESULTADOS"]*

"E como nós construímos essa solução? Passando para o card da direita, nós desenvolvemos o **primeiro modelo de longevidade do Itaú Crédito PF** — um modelo em LightGBM que estima a probabilidade de óbito em uma janela de 6 meses e traduz essa estimativa em **6 níveis de risco temporalmente estáveis e auditáveis**, prontos para consumo direto pelas políticas.

Para chegar nesse resultado, nós apoiamos o projeto em três pilares de inovação:
- **Primeiro, inovação em dados:** nós trouxemos e integramos fontes públicas externas até então inéditas no crédito — dados do **IBGE, IPEA e SUS** — enriquecendo a visão demográfica e epidemiológica da carteira.
- **Segundo, rigor metodológico na fronteira de ML:** o GBDT (LightGBM) é o estado da arte para dados tabulares há cerca de 10 anos, mas nós não paramos aí. Fomos o **primeiro projeto da área a construir um benchmark aplicando 10 modelos fundacionais tabulares** nos mesmos dados de desenvolvimento para desafiar a nossa performance.
- **E terceiro, IA como alavanca de produtividade** em todas as etapas do ciclo de desenvolvimento."

---

## 4. Principais Resultados & Impacto de Negócio (3:00 – 4:15)
> *[Aponte para o número 9,4× e o gráfico de barras no Card 2]*

"Os resultados comprovam a força dessa abordagem. O modelo atingiu performance de **nível estado da arte** para esse tipo de dado, superando inclusive os benchmarks da literatura científica.

Olhando para o gráfico no centro do card: entre o nível 1 (com taxa de óbito de **0,63%** em 6 meses) e o nível 6 (chegando a **5,92%**), nós alcançamos uma **separação de cerca de 9,4 vezes entre os extremos**, com uma escada monotônica limpa e altamente estável no tempo.

Na primeira aplicação prática avaliada, no **Consignado INSS**, o modelo provou um **valor duplo**: ele não só ordena com precisão o risco de óbito como também ajuda a ordenar o risco de inadimplência — e, acima de tudo, faz isso **antecipando o evento antes de qualquer atraso**.

E não é uma promessa de laboratório: o modelo **já está implementado em produção, rodando mensalmente**, e já abre caminho para novas frentes estratégicas na **visão cliente (Polaris)** e no **Gene do Aposentado**."

---

## 5. Legado para a RT & Fechamento (4:15 – 5:00)
> *[Aponte para a faixa inferior do Card 2: "ATIVOS RT"]*

"Por fim, por que essa iniciativa merece ser destaque no **Melhores do Ano da RT em 2026**?

Porque além de resolver um problema estratégico inédito, ela deixou bens públicos para toda a comunidade:
1. O **Book de Longevidade** já produtizado;
2. Um **pipeline democratizado de ingestão de dados externos** (IBGE, IPEA e SUS) pronto para qualquer outra modelagem da organização;
3. E um **framework reutilizável de avaliação de modelos fundacionais tabulares** como desafiantes.

O Modelo de Longevidade mostra, na prática, como transformar rigor científico, inteligência de dados e IA em uma solução pioneira, escalável e diretamente conectada ao resultado do negócio. Muito obrigado!"

---

## Dicas Rápidas de Entrega
- **Controle de tempo:** O marco de **2:00** deve coincidir exatamente com a sua passagem do Card 1 para o Card 2.
- **Ênfase vocal:** Dê uma pausa de 1 segundo antes de falar *"antes de qualquer sinal de atraso"* (Card 1) e antes de *"9,4 vezes"* (Card 2) — são as duas âncoras visuais que os jurados vão gravar.
