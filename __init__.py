%%{ init: { 'flowchart': { 'curve': 'bumpX' } } }%%
flowchart LR
PROP[(Propostas)]
CONT[(Contratos)]
SIMU[(Simulações)]

PUBAMST("Público Amostrado")
PUBRED(Público Reduzido)

BOOKS[("Books NPM \n BC|BX|BVS")]
BOOKS1[(Books NPM)]

PERFOBS("Performance
            Observada")
PERFINF("Performance
            Inferida")

PERFINAL(""Performance \n Final)

subgraph ESTUDOS
PUB("Público Extraído")
VR("Variável Resposta")
end

subgraph INF[INFERÊNCIA DOS NEGADOS]
direction TB
PSV("Pré Seleção de Variáveis")
OHP("Otimização de Parâmetros")
TRAIN("Treinamento do Modelo")
INFINAL("Modelo de Inferência")
end

subgraph MER["MERIDIAN CRÉDITO IMOBILIÁRIO"]
direction TB
SVAR("Seleção de Variáveis")
OHPMER("Otimização de Parâmetros")
TRAINFINAL("Treinamento Final do \n Meridian Imob")
MERIDFIN("Modelo Meridian Final")
end




SIMU & PROP & CONT---->PUB

PUB--200K                         ---->PUBAMST-->PSV
PUB--"Safras \n Filtradas \n ~2MM"----->PUBRED-->INF


PROP--Aprovadas Itaú---->VR
CONT--"Itaú|Mercado"---->VR

VR--->INF
VR~~~INFINAL


BOOKS1-->MER
PSV~~~BOOKS1

INFINAL-->PERFOBS & PERFINF-->PERFINAL--->MER

PERFINAL~~~MERIDFIN
BOOKS---->INF


