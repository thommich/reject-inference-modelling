# Simulação e Pré-Análise
Os dados iniciais fornecidos durante a simulação são utilizados em uma avaliação prévia de risco do cliente em um processo denominado Pré Análise de Crédito, e o resultado desta análise influencia diretamente as condições da oferta de contratação disponível a cada cliente. O primeiro passo da pré análise utiliza como entrada somente o CPF do proponente e retorna um dos seguintes cenários:
    
    - Farol Vermelho: indicativo de um cliente com o qual o banco não possui interesse de negociar. Um cliente que se enquadra nessa categoria não terá acesso a nenhuma oferta de Financiamento de Veículo e o processo de simulação serrá interrompido imediatamente. Alguns dos principais motivos para um cliente ser classificado como Farol Vermelho são: ... . A regra completa de enquadramento no Farol Vermelho podem ser consultadas no documento em anexo.

    - Farol Verde: indicativo de um cliente que não possui atrelado ao seu documento nenhum dos filtros duros aplicados na regra do Farol Vermelho, conforme descrito acima. Para estes clientes, as demais informações fornecidas durante a simulação serão submetidas às regras determinadas pela Política de Crédito do produto para determinação das condições finais da sua oferta.

# Proposta
Os clientes classificados como Farol Verde durante a pré análise podem ajustar as condições da sua oferta (valor de entrada pretendido, quantidade de parcelas totais...) e gerar então uma proposta de contratação do produto. Neste caso, de posse das informações necessárias e confirmada a intenção de contratação, o Banco realiza um processo mais minucioso de análise de crédito do cliente podendo então aceitar ou rejeitar a proposta de contratação do produto. 
Existe também a possibilidade de um cliente ser classificado como Farol Verde na etapa de pré análise e não seguir para a etapa de proposta. Isto pode acontecer por diversos motivos: seja porque não houve interesse nas condições da oferta disponível, seja porque decidiu realizar outra simulação com dados diferentes da anterior, ou até mesmo por estar realizando a simulação com intenções mais especulativas... O fato é que estes clientes representam uma fatia representativa do público que percorre a jornada de contratação do produto de Financiamento de Veículos.

# Contrato
Os clientes aprovados na análise de crédito final devem fornecer a documentação final necessária e, mediante assinatura de um contrato com o Banco, concluem a jornada de aquisição do produto com sucesso.
É interessante notar que, da mesma maneira que acontece na etapa de proposta, na etapa de contratação sempre há clientes que mesmo tendo sua proposta aprovada na etapa anterior acabam não concluindo a contratação do produto com o Banco Itaú.


No diagrama abaixo podemos observar uma média mensal da volumetria de clientes que passam por cada etapa da jornada do produto. O cálculo da média mensal restringiu-se somente as referências utilizadas durante o desenvolvimento do modelo.


# Público de Desenvolvimento do Modelo
Partindo do público total submetido a etapa de pré análise (todos os clientes que realizaram simulação de financiamento em qualquer dos canais disponíveis), e baseados nas etapas da Jornada de Contratação do produto descrita acima dividimos o público total em 9 grupos, levando em conta os seguintes 3 fatores:

    - Farol da pré análise: verde ou vermelho;
    - Proposta de contratação no Itaú: sem proposta, proposta aprovada ou proposta negada;
    - Contratação do produto: sem contrato, contrato no Itaú, contrato em outra instituição;

Ao avaliarmos a contratação do produto, utilizamos a base de dados do SCR para identificar clientes que realizaram contratação especificamente de Financiamento de Veículos em alguma outra instituição financeira que não o Banco Itaú. Estes clientes são de especial interesse em nossas análises haja vista a possibilidade de aferirmos a performance do contrato ainda que o mesmo não tenha sido firmado conosco, permitindo o cálculo da variável resposta do modelo (conforme discutido aqui) e forncendo informações muito ricas especialmente acerca dos não-correntistas.

O gráfico abaixo traz a volumetria dos 9 grupos de clientes da pré-análise ao longo das referências de desenvolvimento do modelo.


O público de desenvolvimento do modelo consiste em uma subamostragem de 4 dos 9 grupos identificados. Excluindo os grupos onde não se verifica contratação do produto (que impossibilita o cálculo da variável resposta e, portanto, impossibilita o uso na modelagem conforme aqui proposta), foram utilizados os seguintes critérios de amostragem:
    -
    -
    -
    -

O gráfico abaixo ilustra as voumetrias e a segmentação do público de desenvolvimento em cada uma das referências utilizadas.


O código utilizado para construção do público de desenvolvimento pode ser consultado e replicado através deste notebook.


# Ausência de Modelo de Inferência de Negados
Quando se trata de modelagem de risco de crédito para concessão de produtos financeiros (denominados geralmente "Application Scoring Models") é comum observarmos o desenvolvimento de um modelo auxiliar com o intuito de inferir a variável resposta para clientes que tiveram o crédito negado nas referências de desenvolvimento. Estes clientes não efetuaram a contratação do produto, fato que torna impossível a análise de janela de performance que é indispensável para o cáculo da variável resposta. A introdução de clientes negados nos modelos de risco de crédito é encorajada com o objetivo de controlar o viés de seleção gerado a partir da análise histórica dos dados somente de clientes aprovados, o que acaba gerando uma distribuição de dados distorcida, considerando-se que não é representativa da população que o modelo deverá escorar após treinado.
Ao analisarmos as características do público do modelo Gallardo percebemos no grupo de clientes FAROL VERMELHO | SEM PROPOSTA | CONTRATO BC as características básicas necessárias para substituição de uma inferência de negados, haja vista a negativa de concessão de crédito para estes clientes aliada à existência de um contrato de produto que possibilita a análise da janela de performance. O modelo Gallardo, portanto, foi desenvolvido sem a utilização do modelo auxiliar de inferência de negados, usando como motivador a ideia de que adicionando o grupo de clientes citado ao conjunto de dados de desenvolvimento do modelo é possível anular o viés de seleção.


FAROL VERM  | SEM PROPOSTA | SEM CONTRATO
**FAROL VERM  | SEM PROPOSTA | CONTRATO BC**
FAROL VERDE | SEM PROPOSTA | SEM CONTRATO
FAROL VERDE | SEM PROPOSTA | CONTRATO BC
FAROL VERDE | PROPOSTA NEGADA | SEM CONTRATO
**FAROL VERDE | PROPOSTA NEGADA | CONTRATO BC**
FAROL VERDE | PROPOSTA APROVADA | SEM CONTRATO
FAROL VERDE | PROPOSTA APROVADA | CONTRATO BC
**FAROL VERDE | PROPOSTA APROVADA | CONTRATO ITAÚ**
