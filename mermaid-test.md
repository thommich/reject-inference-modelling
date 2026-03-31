---
config:
  theme: neutral  
  look: handDrawn
---

flowchart LR
        A@{ shape: doc, label: "Origem: .csv 
        (Base de Simulações de Financiamento de Veículos)" }

        MPERF["`**Marcação de Performance**
                Cruzamento com:
                - Focuault Contratação
                - Foucault PD Itau
                - Foucault PD Mercado`"]

        A ---> MPERF

        MPUB["`**Marcação dos Públicos**`"]

        MPERF ---> |"Remoção de 'maus na origem'"| MPUB

        subgraph AP ["`**Amostragem dos Públicos**`"]
            direction TB
            CI["Contratos Itaú"]
            PNCB["Prop. neg. contrato BC"]
            FVCB["Farol verml. contrato BC"]
            PNSC["Prop. neg. sem contrato"]
            FVSC["Farol verml. sem contrato"]
        
            AE["`**Amostras Empilhadas**`"]
        end        

        MPUB ---> |flag_contrato = 1| CI ---> |100%| AE
        MPUB ---> |flag_aprovada = 0 & performance| PNCB ---> |100%| AE
        MPUB ---> |flag_verde = 0 & performance| FVCB ---> |100%| AE
        MPUB ---> |flag_aprovada = 0 & sem peformance| PNSC ---> |30K/safra| AE
        MPUB ---> |flag_verde = 0 e sem performance| FVSC ---> |50K/safra| AE

        RD["`**Remoção de Duplicidades**
        Chave [CPF, safra]`"]

        AE ---> RD

        B@{ shape: cyl, label: "Base Final" }

        RD ---> B