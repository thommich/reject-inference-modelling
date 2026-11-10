# 🎙️ Guia do Apresentador: Validação de Distribuição de Modelos (Visão Executiva)

**Apresentador:** Thomás Santos  
**Área:** Squad de Modelagem – Produtos Parcelados (Itaú Unibanco)  
**Tempo total:** 20 a 30 minutos (sendo **20 a 22 min de fala** + **8 a 10 min de perguntas/debate**)  
**Público-alvo:** Liderança Executiva, Gerentes de Modelagem, Riscos e Tecnologia  

---

## ⏱️ Grade de Minutagem Sugerida (20 a 30 minutos)

| Slide | Tema Central | Minutagem | Acumulado |
| :---: | :--- | :---: | :---: |
| **1** | Abertura & Propósito do Encontro | 1,5 min | 1,5 min |
| **2** | O Processo Atual (Artesanal e Disperso) | 2,5 min | 4,0 min |
| **3** | As Dores e o Risco de Negócio | 3,0 min | 7,0 min |
| **4** | A Mudança de Paradigma: Fluxo Manual vs. Agêntico | 3,0 min | 10,0 min |
| **5** | Os Game Changers (Arquitetura de Conhecimento) | 2,5 min | 12,5 min |
| **6** | Casos Reais: A IA na Prática (Justificado, Irregular, Circunstancial) | 4,5 min | 17,0 min |
| **7** | Ganhos Quantitativos & Eficiência Operacional | 2,0 min | 19,0 min |
| **8** | O Produto (Skill, Automação, Roadmap & Governança) | 3,5 min | 22,5 min |
| **9** | Conclusão, Convite e Q&A | 5 a 8 min | **25 a 30 min** |

---

## 🎯 Mensagem Central ("The One Thing")
> *"Hoje, liberar uma rodada de modelo exige horas de caça manual a dados dispersos e depende da intuição de quem analisa. Criamos uma Skill de IA no AletheIA que reduz essa validação de 3 horas para 15 minutos, investiga a causa raiz e transforma o aprendizado de cada caso em patrimônio permanente do banco."*

---

# 📋 Roteiro Slide a Slide com Speaker Notes

---

### Slide 1: Abertura (`$ cat visao-executiva.txt`)
*Visual: Terminal limpo com o título "🎯 Skill de Validação de Distribuição de Modelos".*

* **Tempo:** 1m30s
* **Objetivo:** Estabelecer o contexto de negócio imediato, o escopo da modelagem de Produtos Parcelados e a promessa da reunião.
* **Pontos de Atenção:** Transmita segurança e foco em valor prático. Evite jargões técnicos de cara; foque na responsabilidade do "OK de distribuição".

#### 🗣️ Roteiro de Fala Sugerido:
> *"Bom dia a todos. Obrigado pela presença.  
> Como vocês sabem, aqui na modelagem de Produtos Parcelados, a cada nova rodada dos nossos modelos de crédito, temos um momento crítico de decisão: o **OK de distribuição**.  
> Esse momento responde a uma única pergunta de alto impacto: 'Podemos liberar com segurança este score para os sistemas transacionais e de esteira de crédito do banco?'  
> Hoje, quero apresentar uma virada de chave no modo como respondemos a essa pergunta: a **Skill de Validação de Distribuição de Modelos**, desenvolvida sobre a nossa esteira de IA agêntica. Nosso objetivo nos próximos 20 minutos é mostrar como transformamos um processo que era demorado, reativo e individual em uma capacidade automatizada, rápida e institucional do time."*

* **Transição para o Slide 2:** *"Para entendermos o valor dessa solução, vale lembrar como essa rotina acontece hoje na vida real."*

---

### Slide 2: O Processo (`$ ./validacao-manual.sh`)
*Visual: Fluxo sequencial (Dashboards -> Acha Métrica -> Queries ad hoc -> Compara score/GH) levando a 3 desfechos (Resolve, Afunila, Inconclusivo).*

* **Tempo:** 2m30s
* **Objetivo:** Mostrar a fricção e o caráter "artesanal" do processo manual sem desmerecer o time técnico.
* **Pontos-chave:**
  - O trajeto é sempre o mesmo, mas a complexidade explode nas variáveis.
  - Dependência excessiva de quem está rodando a análise.
  - O resultado é incerto: muitas vezes consome horas e continua inconclusivo.

#### 🗣️ Roteiro de Fala Sugerido:
> *"Vejam como funciona hoje: sai a rodada do modelo. O analista entra nos dashboards de observabilidade e monitoramento. Ele bate o olho e identifica, por exemplo, que uma métrica ou um KS de uma variável acendeu um farol amarelo.  
> A partir daí, começa o trabalho braçal investigativo: ele abre o ambiente de banco de dados, escreve queries SQL ad hoc, puxa históricos temporais para comparar a curva de score, o GH (Grau de Homogeneidade) e o comportamento das variáveis explicativas.  
> E qual é o desfecho? Depende da sorte e de quem está na cadeira:  
> - Em alguns casos, a causa salta aos olhos e ele **resolve**.  
> - Em outros, ele **afunila** os suspeitos — sabe que o problema está num determinado book, mas não crava o porquê.  
> - E não raro, após 3 ou 4 horas mergulhado em queries, o status é **inconclusivo**. O prazo de distribuição está estourando e a pressão sobre a decisão só aumenta."*

* **Transição para o Slide 3:** *"Esse processo gera três dores muito claras que impactam diretamente o risco e a produtividade da nossa área."*

---

### Slide 3: As Dores (`$ ./as-dores.sh`)
*Visual: 3 blocos de impacto (Risco de erro, Validação lenta, Saber volátil) com destaque inferior sobre a verdadeira natureza do gargalo.*

* **Tempo:** 3m00s
* **Objetivo:** Conectar o problema operacional com o risco financeiro e a perda de capital intelectual.
* **Pontos-chave:**
  - **Risco de Erro:** Score com defeito contamina concessão, limite e provisionamento.
  - **Validação Lenta:** Fricção recorrente em toda rodada.
  - **Saber Volátil:** Se o analista sai da cadeira ou muda de squad, o histórico de investigações vai embora com ele.
  - **O Gargalo:** O problema não é saber analisar dados; é testar as centenas de hipóteses possíveis no contexto de dezenas de modelos diferentes.

#### 🗣️ Roteiro de Fala Sugerido:
> *"Quero destacar essas três dimensões:  
> 1. **Risco de Erro:** Modelos de risco definem quem recebe crédito, qual a taxa e qual o limite. Se liberamos um score com anomalia não detectada, o erro se propaga por toda a esteira do banco. O custo de um falso positivo ou negativo aqui é altíssimo.  
> 2. **Validação Lenta:** Toda rodada consome horas preciosas de cientistas e analistas seniores caçando tabelas, logs e bases dispersas.  
> 3. **Saber Volátil:** Talvez a dor mais invisível e danosa. Quando alguém resolve um desvio complexo de um book de variáveis, esse aprendizado fica na cabeça dele ou numa anotação perdida no Teams. Na rodada seguinte, se outra pessoa estiver no plantão, ela começa a investigação exatamente do zero.  
> Por isso trouxemos essa constatação em destaque: **o gargalo nunca foi a capacidade analítica da equipe; o gargalo é o tempo necessário para cruzar dezenas de possibilidades dentro da particularidade de cada modelo**."*

* **Transição para o Slide 4:** *"Foi aí que decidimos mudar a abordagem. Não queríamos apenas um dashboard a mais. Queríamos um fluxo agêntico."*

---

### Slide 4: A Alternativa: Um Fluxo Agêntico (`$ diff -u antes.txt agora.txt`)
*Visual: Tabela comparativa "Antes (Manual)" vs. "Dimensão" vs. "Agora (Agêntico)".*

* **Tempo:** 3m00s
* **Objetivo:** Deixar cristalino o salto de maturidade e eficiência em cada uma das cinco dimensões.
* **Pontos-chave:**
  - **Agilidade:** De horas dispersas para parecer em minutos.
  - **Consistência:** Método padrão e uniforme em toda rodada.
  - **Profundidade:** O agente não para no primeiro sintoma; ele escava a causa raiz.
  - **Colaboração:** Cada investigação retroalimenta a base de conhecimento do time.
  - **Rastreabilidade:** Auditoria facilitada com trilha reprodutível de evidências.

#### 🗣️ Roteiro de Fala Sugerido:
> *"Aqui está a essência da mudança: a pergunta continua exatamente a mesma — 'Posso distribuir esta rodada?'. Mas a forma de responder mudou em cinco dimensões estruturais:  
> - Em **Agilidade**, saímos da caça manual de dados para um parecer pronto, consolidado em minutos e num único ponto de acesso.  
> - Em **Consistência**, eliminamos o viés pessoal: não importa se é o analista júnior ou o especialista sênior, a esteira executa o mesmo checklist rigoroso e abrangente.  
> - Em **Profundidade**, o humano sob pressão de tempo tende a parar no primeiro suspeito que encontra. O agente testa sistematicamente a cadeia completa até cravar a causa raiz.  
> - Em **Colaboração**, saímos do conhecimento preso em silos para um mapa compartilhado: cada incidente documentado enriquece a inteligência coletiva.  
> - E em **Rastreabilidade**, geramos uma trilha de evidências 100% auditável. Se o comitê ou a auditoria perguntar daqui a seis meses por que distribuímos aquela safra, temos cada query e evidência registrada."*

* **Transição para o Slide 5:** *"Mas como isso funciona por baixo do capô? Quais são os pilares que tornam isso possível?"*

---

### Slide 5: Os Game Changers (`$ ./game-changers.sh`)
*Visual: 4 pilares tecnológicos e conceituais (Mapa por modelo, Conhecimento Acumulado, Sincronização, Auditabilidade).*

* **Tempo:** 2m30s
* **Objetivo:** Explicar a sustentabilidade da solução: ela melhora com o tempo e cria efeito de rede.
* **Pontos-chave:**
  - **Mapa por Modelo:** Cada modelo tem seu 'DNA' cadastrado (fontes, métricas de corte, limites de tolerância).
  - **Análise Cruzada:** Se um book de variáveis quebrou no modelo A, o agente já alerta os modelos B e C que usam a mesma fonte.
  - **Sincronização:** Single Source of Truth atualizada.
  - **Efeito Composto:** 'Quanto mais o time usa, mais inteligente a capacidade fica.'

#### 🗣️ Roteiro de Fala Sugerido:
> *"Quatro alavancas sustentam essa inteligência:  
> Primeiro, o **Mapa por Modelo**. Não aplicamos uma regra genérica para tudo. Cada modelo tem sua base de conhecimento com suas variáveis-chave, históricos e sensibilidades particulares.  
> Segundo, o **Conhecimento Acumulado com Análise Cruzada**. Modelos de crédito frequentemente compartilham books upstream (como bureau, cadastro ou transacional). Se um book apresentou anomalia na rodada do modelo X, o agente automaticamente correlaciona e antecipa o diagnóstico quando o modelo Y é acionado.  
> Terceiro, a **Sincronização**: garantimos que todo o time consuma a versão mais atualizada das regras de validação e playbooks, sem versões conflitantes em máquinas locais.  
> E quarto, a **Auditabilidade** nativa: cada parecer carrega os logs e as saídas que sustentaram a recomendação.  
> Como colocamos no rodapé: essa é uma ferramenta com efeito de rede positivo — quanto mais investigações realizamos, mais rica fica a base."*

* **Transição para o Slide 6:** *"Para comprovar que isso não é apenas teoria, quero mostrar três casos reais de produção que enfrentamos recentemente e como a solução reagiu."*

---

### Slide 6: Casos Reais – Três Tipos de Desvio, Três Decisões (`$ casos reais`)
*Visual: Tabela com 3 estudos de caso reais: Amarelo (Justificado), Gallardo (Irregular) e Bordô (Circunstancial).*

* **Tempo:** 4m30s ⭐ *(Slide de maior peso para validação executiva)*
* **Objetivo:** Provar precisão analítica e discernimento do fluxo: ele não se limita a 'passar tudo' ou 'travar tudo'; ele diferencia ruído, erro grave e contingência de negócio.

#### 🗣️ Roteiro de Fala Sugerido:
> *"Esse slide é o coração da entrega técnica. Aqui temos três cenários reais com naturezas de desvio totalmente distintas:  
> 
> 1. **Caso 1: Desvio Justificado (Modelo Amarelo - out/2025)**  
>    - **Sintoma:** Acendeu um farol amarelo de KS em um book específico de variáveis.  
>    - **Investigação da Skill:** O agente detectou que todas as variáveis daquele book se moveram simultaneamente. Cruzando com o histórico, identificou que o book havia publicado uma atualização programada no dia anterior.  
>    - **Diagnóstico:** Causa benigna. Era um comportamento perfeitamente esperado pós-atualização de fonte de dados.  
>    - **Decisão:** **DISTRIBUIR** com segurança, evitando horas de pânico desnecessário.  
> 
> 2. **Caso 2: Desvio Irregular (Modelo Gallardo - ago/2026)**  
>    - **Sintoma:** Um aumento súbito de volumetria: o público saltou de 250 milhões para 443 milhões de registros (quase o dobro).  
>    - **Investigação da Skill:** As métricas estatísticas de distribuição de score e GH pareciam normais à primeira vista. Mas o agente aprofundou e identificou que as linhas duplicadas divergiam em exatamente uma única coluna.  
>    - **Diagnóstico:** Erro na fonte! A base recebida da Serasa estava com duplicidade massiva de registros.  
>    - **Decisão:** **NÃO DISTRIBUIR**. Essa detecção evitou que uma base corrompida fosse ingerida pelos sistemas do banco.  
> 
> 3. **Caso 3: Desvio Circunstancial (Modelo Bordô - out/2025)**  
>    - **Sintoma:** Farol amarelo de KS numa variável de bureau.  
>    - **Investigação da Skill:** A curva de score e o GH estavam intactos. O agente descobriu que uma origem de dados havia regredido a referência temporal em relação ao mês anterior.  
>    - **Diagnóstico:** O book do Bacen havia sido congelado deliberadamente pela engenharia corporativa porque a atualização estava desbalanceando outros modelos.  
>    - **Decisão:** **DISTRIBUIR COM RESSALVA**. O modelo pôde operar com conhecimento explícito e documentado do congelamento temporário da fonte.  
> 
> Isso demonstra que a ferramenta tem **critério executivo**: ela entende contexto de negócio e governança de dados."*

* **Transição para o Slide 7:** *"Vistos os casos reais, vamos consolidar o que a área e o banco ganham com isso."*

---

### Slide 7: O Que o Time Ganha (`$ ./impacto.sh`)
*Visual: 4 quadrantes (Velocidade, Memória, Colaboração, Qualidade) com métrica de redução de tempo em destaque.*

* **Tempo:** 2m00s
* **Objetivo:** Apresentar a síntese de ROI e impacto no dia a dia da gerência.
* **Pontos-chave:**
  - **Velocidade:** Validação de **3 horas reduzida para 15 minutos** (ganho de ~90% em tempo de ciclo).
  - **Memória:** Fim do retrabalho e retenção do aprendizado.
  - **Colaboração:** Alinhamento total do time na mesma fonte de verdade.
  - **Qualidade:** Investigação exaustiva e repetível.
  - **Impacto no Banco:** Decisões seguras e risco mitigado de exposição regulatória/creditícia.

#### 🗣️ Roteiro de Fala Sugerido:
> *"Sintetizando em números e ganhos operacionais:  
> - **Velocidade:** O ciclo que antes demandava cerca de 3 horas por modelo agora é executado em cerca de 15 minutos. Isso libera tempo nobre dos nossos cientistas para modelagem, calibragem e estratégia de crédito.  
> - **Memória:** Criamos um histórico perpétuo. As dúvidas resolvidas hoje evitam o retrabalho do próximo mês.  
> - **Colaboração:** Todo mundo — analistas, gestores e áreas parceiras — enxerga o mesmo diagnóstico sob as mesmas evidências.  
> - **Qualidade:** Substituímos o improviso de queries soltas por um protocolo sistemático de conferência.  
> O resultado final é previsibilidade, velocidade na esteira de crédito e uma barreira adicional contra o vazamento de score defeituoso para produção."*

* **Transição para o Slide 8:** *"Agora, quero apresentar como esse produto foi construído, onde estamos hoje e para onde vamos."*

---

### Slide 8: O Produto, a POC e o Futuro (`$ ./o-produto.sh`)
*Visual: Arquitetura em 3 colunas (Skill no AletheIA, POC de Automação, O Futuro).*  
*(Nota do Apresentador: As imagens de apoio detalham a interface no AletheIA, os relatórios gerados e a proposta de arquitetura governada).*

* **Tempo:** 3m30s
* **Objetivo:** Mostrar pragmatismo na entrega: o que já funciona hoje, como foi testado e o plano transparente de escala e governança corporativa.
* **Pontos-chave por coluna:**
  1. **Skill no AletheIA:** Uso interativo pelo analista via prompt integrado ao ecossistema interno de IA.
  2. **POC de Automação:** Agendamento batch no AWS SageMaker gerando relatórios automáticos em portal.
  3. **Transparência Arquitetural:** A POC atual usou conta consumer/agendamento pontual para validação de hipótese; o próximo passo é a transição para esteira oficial e governada com TI.
  4. **O Futuro:** Expansão para outros modelos (Renda, Ratings) e extensão para books de variáveis/tabelas-chave (como esteiras do Foucault).

#### 🗣️ Roteiro de Fala Sugerido:
> *"Hoje temos essa solução materializada em duas frentes complementares:  
> 
> **1. A Skill no AletheIA (Uso Interativo):**  
> O analista de modelagem pode simplesmente clonar a skill, iniciar a sessão no AletheIA — que é o nosso ambiente corporativo de agentes de IA — e solicitar a validação de um modelo específico. O agente executa os testes, investiga os livros de regras e entrega o parecer na hora.  
> 
> **2. A POC de Automação (Execução Agendada):**  
> Para ir além do acionamento manual, construímos uma POC de agendamento no SageMaker. Assim que uma rodada recente é identificada, a validação roda de forma programada e publica automaticamente o relatório analítico no nosso portal de relatórios, com faróis e gráficos de apoio.  
> 
> **Avanço Governança & Futuro:**  
> Quero ser muito transparente sobre arquitetura: a POC cumpriu seu papel de validar o valor de negócio utilizando agendamento e credenciais locais. Agora, já estamos em conversas com as equipes de **Tecnologia e Dados** para portar essa esteira para uma arquitetura plenamente governada, segura e integrada aos pipelines oficiais do banco.  
> 
> Além disso, vemos dois caminhos claros de escala:  
> - **Disseminação:** Cadastrar todos os modelos da nossa gerência e estender a solução para superintendências irmãs, como as de modelos de Renda e Ratings.  
> - **Extensão de Escopo:** Aplicar essa mesma lógica de validação agêntica para books de variáveis e tabelas-chave independentes de score, como as esteiras do Foucault."*

* **Transição para o Slide 9:** *"Chegamos à nossa conclusão e próximos passos."*

---

### Slide 9: Conclusão & Abertura para Discussão (`$ exit`)
*Visual: Mensagem de encerramento, contatos de Thomás Santos (Squad de Modelagem - Produtos Parcelados) e chamada para diálogo.*

* **Tempo:** 1m30s (+ tempo restante para Q&A)
* **Objetivo:** Fazer o call to action executivo: aprovação do direcionamento, apoio para a parceria com TI e abertura para perguntas.

#### 🗣️ Roteiro de Fala Sugerido:
> *"Para fechar: provamos que é possível sair de uma rotina reativa e morosa de 3 horas para uma validação em minutos, ganhando segurança de crédito e auditabilidade.  
> Nosso próximo marco é consolidar a parceria com Tecnologia para oficializar a arquitetura e expandir o cadastro de modelos da superintendência.  
> Gostaria muito de ouvir a percepção de vocês: isso faz sentido para as prioridades estratégicas da área? Onde vocês enxergam as maiores oportunidades de sinergia?  
> Muito obrigado, e abro agora para perguntas e comentários."*

---

# 🛡️ Guia de Respostas a Perguntas Difíceis (Executive FAQ)

Esteja preparado para estas perguntas comuns de gestores e superintendentes:

### 1. "O agente de IA decide sozinho se o modelo vai pra produção?"
> **Sua Resposta:** *"Não. O agente atua estritamente como um copiloto investigativo de alta performance. Ele faz toda a varredura pesada, cruza métricas e emite um **parecer fundamentado com trilha de evidências**. A decisão do 'OK de distribuição' permanece com o modelador responsável (Human-in-the-loop). O que eliminamos foi o trabalho cego de caça a dados, não a supervisão humana."*

### 2. "Existe risco do agente ter 'alucinações' e justificar um erro real como se fosse falso positivo?"
> **Sua Resposta:** *"Essa foi nossa principal preocupação no design. A skill não faz inferência criativa livre. Ela executa rotinas analíticas determinísticas em código (queries, testes de hipóteses estatísticas, verificações de integridade de schema e logs de atualização de fontes). O LLM é usado para orquestrar o raciocínio investigativo e sintetizar o relatório. Além disso, cada afirmação do parecer aponta diretamente para o dado bruto reproduzível no portal."*

### 3. "Quanto custa rodar isso e qual o consumo de tokens/infra?"
> **Sua Resposta:** *"O custo é marginal. Cada rodada de validação leva cerca de 15 minutos e consome poucas chamadas de agente, o que representa centavos por execução. Comparado ao custo-hora de um cientista de dados sênior gastando 3 horas por rodada em dezenas de modelos no mês — sem contar o risco de sinistro de crédito por vazamento de score anômalo —, o ROI é imediato e descomunal."*

### 4. "Sobre a arquitetura: a POC usou credencial pessoal no SageMaker. Isso não fere a política de segurança?"
> **Sua Resposta:** *"Exatamente por isso fizemos questão de sinalizar esse ponto com total clareza no slide 8. Trata-se de um ambiente de prototipação rápida para validação de hipótese de valor (POC). O próximo passo formal — que já está em alinhamento com Tecnologia e Governança de TI — é migrar para uma role de serviço corporativa (IAM governado), esteira CI/CD oficial e infraestrutura homologada pelo banco."*

### 5. "Podemos levar isso para as gerências de Renda, Cartões ou Ratings amanhã?"
> **Sua Resposta:** *"A estrutura da skill foi concebida de forma modular e desacoplada do modelo específico. O motor de validação e a lógica de investigação de desvios funcionam para qualquer modelo de crédito. O que precisamos para cada nova área é apenas cadastrar o 'Mapa do Modelo' (metadados, fontes de dados e thresholds de KS/PSI). O onboarding de uma nova gerência é rápido e pretendemos conduzir esse rollout em ondas."*

---

## 💡 Dicas de Postura e Oratória para Thomás
1. **Controle o Ritmo:** Não corra no slide 6 (Casos Reais). Ele é a prova cabal de que você entende o negócio e que a solução funciona de verdade. Dedique pelo menos 4 a 5 minutos nele.
2. **Postura Parceria vs. Crítica:** Ao falar do processo manual (slides 2 e 3), nunca soe como se os analistas fizessem um trabalho ruim. Deixe claro que a equipe é excelente, mas o ferramental tradicional é limitado.
3. **Vocabulário Itaú:** Use os termos nativos com naturalidade: *score, GH, KS, books, Serasa, Bacen, AletheIA, Foucault, Produtos Parcelados*.
4. **Fechamento de Olho no Relógio:** Aos 20 minutos de apresentação, vá para o slide 9 para garantir pelo menos 8 a 10 minutos de debate com os executivos. É no debate que os patrocínios para a fase governada são conquistados.
