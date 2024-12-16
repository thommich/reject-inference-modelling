with pub_inicial as ( -- 1 linha por cpf9_espec, safra

    SELECT DISTINCT
        A.cpf9_espec
        ,A.cnpj_espec
        ,A.flag_pjampliada
        ,A.SAFRA_MOD
        ,A.SAFRA

        FROM tms_mdl_espec_mdl_prod_especialista as A
        WHERE TRIM(A.status_espec) = "Habilitado a Produzir"

), contratos as (

    SELECT DISTINCT
        pub_inicial.cpf9_espec
        ,pub_inicial.cnpj_espec
        ,pub_inicial.flag_pjampliada
        ,pub_inicial.safra
        ,pub_inicial.safra_mod
        ,A.num_contrato_atual
        ,A.data_operacao
        
        ,strftime('%Y', A.data_operacao)*100 + strftime('%m', A.data_operacao) AS SAFRA_CNTRT
        
        ,floor((julianday(date(SUBSTR(CAST(pub_inicial.safra_mod as TEXT),1,4)||'-'||
                                       SUBSTR(CAST(pub_inicial.safra_mod as TEXT),5,2)||'-01'))
                        - julianday(A.data_operacao,'start of month'))/30) AS defasagem_cntrt
        
        
        ,CASE WHEN A.flag_contrato_renegociado = 1 
			THEN strftime('%Y', A.data_operacao)*100 + strftime('%m', A.data_operacao)
            ELSE NULL
        END AS SAFRA_RENEG
    
        ,CASE WHEN A.flag_contrato_renegociado = 1 
            THEN floor((julianday(date(SUBSTR(CAST(pub_inicial.safra_mod as TEXT),1,4)||'-'||
                                       SUBSTR(CAST(pub_inicial.safra_mod as TEXT),5,2)||'-01'))
                         - julianday(A.data_operacao,'start of month'))/30)
            ELSE NULL
        END as defasagem_reneg        

        ,CASE WHEN A.data_quitacao_contrato IS NOT NULL 
			THEN strftime('%Y', A.data_quitacao_contrato)*100 + strftime('%m', A.data_quitacao_contrato)
            ELSE NULL
        END AS SAFRA_QUIT

        ,CASE WHEN A.data_quitacao_contrato IS NOT NULL 
            THEN floor((julianday(date(SUBSTR(CAST(pub_inicial.safra_mod as TEXT),1,4)||'-'||
                                      SUBSTR(CAST(pub_inicial.safra_mod as TEXT),5,2)||'-01'))
                        - julianday(A.data_quitacao_contrato,'start of month'))/30)
            ELSE NULL
        END as defasagem_quit

		,TRIM(A.politica_micro) as politica_micro
        ,A.idade
        ,A.saldo_bacen_pf
        ,A.plano

        ,A.data_quitacao_contrato
        ,A.mob_quit_contrato

        ,A.flag_contrato_renegociado
        ,A.status_fpd_reneg

        FROM pub_inicial
        LEFT JOIN HISTORICA_CONTRATOS as A
        ON CAST (pub_inicial.cnpj_espec as bigint) = CAST(A.cnpj_espec as bigint)
            AND pub_inicial.safra_mod >= A.safra
            
 --       ORDER BY pub_inicial.cnpj_espec, pub_inicial.safra, A.num_contrato_atual

)        
	SELECT DISTINCT
             contratos.cpf9_espec
            ,contratos.cnpj_espec
            ,contratos.safra
            
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_contratos_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_1m 
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.idade ELSE NULL END) as avg_idade_clientes_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.saldo_bacen_pf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.saldo_bacen_pf ELSE 0 END) as vlr_cntrts_sld_pos_bc_1m
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.plano ELSE NULL END) as avg_plano_cntrt_1m
            --,COUNT(DISTINCT (CASE WHEN defasagem_quit is NULL or defasagem_quit < 0 THEN contratos_quit.num_contrato_atual ELSE NULL END) as qtd_cntrts_em_aberto_1m
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.mob_quit_contrato ELSE NULL END) as avg_mob_quit_cntrt_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.flag_contrato_renegociado ELSE NULL END) as qtd_cntrt_reneg_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.status_fpd_reneg ELSE NULL END) as qtd_fpd_reneg_1m
            ,CAST(SUM(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.flag_contrato_renegociado ELSE NULL END) AS DOUBLE)/
                  COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.num_contrato_atual ELSE NULL END)) as pct_cntrts_reneg_1m
                  
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_contratos_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_3m 
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.idade ELSE NULL END) as avg_idade_clientes_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.saldo_bacen_pf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.saldo_bacen_pf ELSE 0 END) as vlr_cntrts_sld_pos_bc_3m
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.plano ELSE NULL END) as avg_plano_cntrt_3m
            --,COUNT(DISTINCT (CASE WHEN defasagem_quit is NULL or defasagem_quit < 0 THEN contratos_quit.num_contrato_atual ELSE NULL END) as qtd_cntrts_em_aberto_3m
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.mob_quit_contrato ELSE NULL END) as avg_mob_quit_cntrt_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.flag_contrato_renegociado ELSE NULL END) as qtd_cntrt_reneg_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.status_fpd_reneg ELSE NULL END) as qtd_fpd_reneg_3m
            ,CAST(SUM(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.flag_contrato_renegociado ELSE NULL END) AS DOUBLE)/
                  COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.num_contrato_atual ELSE NULL END)) as pct_cntrts_reneg_3m
                  
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_contratos_6m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_6m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_6m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_6m 
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.idade ELSE NULL END) as avg_idade_clientes_6m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.saldo_bacen_pf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_6m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.saldo_bacen_pf ELSE 0 END) as vlr_cntrts_sld_pos_bc_6m
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.plano ELSE NULL END) as avg_plano_cntrt_6m
            --,COUNT(DISTINCT (CASE WHEN defasagem_quit is NULL or defasagem_quit < 0 THEN contratos_quit.num_contrato_atual ELSE NULL END) as qtd_cntrts_em_aberto_6m
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.mob_quit_contrato ELSE NULL END) as avg_mob_quit_cntrt_6m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.flag_contrato_renegociado ELSE NULL END) as qtd_cntrt_reneg_6m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.status_fpd_reneg ELSE NULL END) as qtd_fpd_reneg_6m
            ,CAST(SUM(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.flag_contrato_renegociado ELSE NULL END) AS DOUBLE)/
                  COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.num_contrato_atual ELSE NULL END)) as pct_cntrts_reneg_6m
            
            FROM contratos 
            GROUP BY 1,2,3
            
            
            
 