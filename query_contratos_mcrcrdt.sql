with pub_inicial as ( -- 1 linha por cpf9_espec, safra

    SELECT DISTINCT
        A.cpf_espec
        ,A.cnpj_espec
        ,A.flag_pjampliada
        ,A.SAFRA_MOD
        ,A.SAFRA

        FROM workspace db.tms_mdl_espec_mdl_prod_especialista as A
        WHERE TRIM(A.status_espec) = "Habilitado a Produzir"

), contratos as ( -- 1 linha por num_contrato

    SELECT DISTINCT
        pub_inicial.cpf9_espec
        ,pub_inicial.cnpj_espec
        ,pub_inicial.flag_pjampliada
        ,pub_inicial.safra
        ,pub_inicial.safra_mod
        
        ,A.num_contrato_atual

        ,CASE WHEN A.flag_contrato_renegociado = 0 
            THEN EXTRACT(YEAR FROM A.data_operacao)*100 + EXTRACT(MONTH FROM data_operacao)
            ELSE NULL 
        END AS SAFRA_CNTRT

        ,CASE WHEN A.flag_contrato_renegociado = 0 
            THEN date_diff("month",
                    parse_datetime(cast(EXTRACT(YEAR FROM A.data_operacao)*100 +
                                        EXTRACT (MONTH FROM A.data_operacao) AS VARCHAR(6)) || '01', 'yyyyMMdd'),
                    parse_datetime(cast(pub_inicial.safra_mod AS VARCHAR(6)) || '01', 'yyyyMMdd')) 
            ELSE NULL
        END AS defasagem_cntrt

        ,CASE WHEN A.flag_contrato_renegociado = 1 
            THEN EXTRACT(YEAR FROM A.data_operacao)*100 + EXTRACT(MONTH FROM data_operacao)
            ELSE NULL 
        END AS SAFRA_RENEG
    
        ,CASE WHEN A.flag_contrato_renegociado = 1 
            THEN date_diff("month",
                    parse_datetime(cast(EXTRACT(YEAR FROM A.data_operacao)*100 + 
                                        EXTRACT (MONTH FROM A.data_operacao) AS VARCHAR(6))||'01', 'yyyyMMdd'),
                    parse_datetime(cast(pub_inicial.safra_mod AS VARCHAR(6)) || '01', 'yyyyMMdd'))
            ELSE NULL
        END as defasagem_reneg

        ,CASE WHEN A.data_quitacao_contrato IS NOT NULL 
            THEN EXTRACT(YEAR FROM A.data_quitacao_contrato)*100 + EXTRACT(MONTH FROM data_quitacao_contrato)
            ELSE NULL 
        END AS SAFRA_QUIT
    
        ,CASE WHEN A.data_quitacao_contrato IS NOT NULL 
            THEN date_diff("month",
                    parse_datetime(cast(EXTRACT(YEAR FROM A.data_quitacao_contrato)*100 + 
                                        EXTRACT (MONTH FROM A.data_quitacao_contrato) AS VARCHAR(6))||'01', 'yyyyMMdd'),
                    parse_datetime(cast(pub_inicial.safra_mod AS VARCHAR(6)) || '01', 'yyyyMMdd'))
            ELSE NULL
        END as defasagem_quit

        ,TRIM(A.politica_micro) as politica_micro
        ,A.idade
        ,A.saldo_bacen_pf
        ,A.plano

        ,A.data_quitacao_contrato
        ,A.mob_quit_contrato

        ,A.flag_contrato_renegociado
        ,A.status_fpd_renegs

        FROM pub_inicial
        LEFT JOIN HISTORICA_CONTRATOS as A
        ON CAST (pub_inicial.cnpj_espec as bigint) = CAST(A.cnpj_espec as bigint)
            AND pub_inicial.safra_mod >= A.safra
        
), contratos_cntrt as ( -- 1 linha por num_contrato

    SELECT DISTINCT
        contratos.cpf9_espec
        ,contratos.cnpj_espec
        ,contratos.flag_pjampliada
        ,contratos.safra
        ,contratos.defasagem_cntrt AS defasagem
        ,contratos.num_contrato_atual

        ,TRIM(contratos_cntrt.politica_micro) as politica_micro
        ,contratos_cntrt.idade
        ,contratos_cntrt.saldo_bacen_pf
        ,contratos_cntrt.plano

        FROM contratos
        JOIN CONTRATOS as contratos_cntrt
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_cntrt.cnpj_espec as bigint)
            AND CAST (contratos.num_contrato_atual as bigint) = CAST(contratos_cntrt.num_contrato_atual as bigint)
            AND contratos.safra_mod >= contratos_cntrt.safra_cntrt
            AND contratos_cntrt.defasagem_cntrt < 6
        
), contratos_quit as ( -- 1 linha por num_contrato

    SELECT DISTINCT
        contratos.cpf9_espec
        ,contratos.cnpj_espec
        ,contratos.flag_pjampliada
        ,contratos.safra
        ,contratos.defasagem_quit AS defasagem
        ,contratos.num_contrato_atual

        ,contratos_quit.data_quitacao_contrato
        ,contratos_quit.mob_quit_contrato

        FROM contratos
        JOIN CONTRATOS as contratos_quit
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_quit.cnpj_espec as bigint)
            AND CAST (contratos.cpf9_espec as bigint) = CAST(contratos_quit.cpf9_espec as bigint)
            AND contratos.safra_mod >= contratos_quit.safra_quit
            AND contratos_quit.defasagem_quit < 6


), contratos_reneg as ( -- 1 linha por num_contrato

    SELECT DISTINCT
        contratos.cpf9_espec
        ,contratos.cnpj_espec
        ,contratos.flag_pjampliada
        ,contratos.safra
        ,contratos.defasagem_reneg AS defasagem
        ,contratos.num_contrato_atual

        ,contratos_reneg.flag_contrato_renegociado
        ,contratos_reneg.status_fpd_renegs

        FROM contratos
        LEFT JOIN CONTRATOS as contratos_reneg
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_reneg.cnpj_espec as bigint)
            AND CAST (contratos.cpf9_espec as bigint) = CAST(contratos_reneg.cpf9_espec as bigint)
            AND contratos.safra_mod >= contratos_reneg.safra_reneg
            AND contratos_reneg.defasagem_reneg < 6
        WHERE contratos_reneg.SAFRA_reneg IS NOT NULL

), contratos_6m as ( -- 1 linha por espec, safra

        SELECT DISTINCT
             contratos.cpf9_espec
            ,contratos.cnpj_espec
            ,contratos.safra
            
            ,COUNT(DISTINCT COALESCE(contratos_cntrt.num_contrato_atual,
                                    contratos_quit.num_contrato_atual,
                                    contratos_reneg.num_contrato_atual)) as qtd_contratos_6m

            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_6m
            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_6m
            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_6m 
            ,AVG(contratos_cntrt.idade) as avg_idade_clientes_6m
            ,SUM(CASE WHEN contratos_cntrt.saldo_bacenpf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_6m
            ,SUM(contratos_cntrt.saldo_bacenpf) as vlr_cntrts_sld_pos_bc_6m
            ,AVG(contratos_cntrt.plano) as avg_plano_cntrt_6m

            ,SUM(CASE WHEN contratos_quit.data_quitacao_contrato IS NULL THEN 1 ELSE 0 END) as qtd_cntrts_em_aberto_6m
            ,AVG(contratos_quit.mob_quit_contrato) as avg_mob_quit_cntrt_6m
            
            ,SUM(contratos_reneg.flag_contrato_renegociado) as qtd_cntrt_reneg_6m
            ,SUM(contratos_reneg.status_fpd_renegs) as qtd_fpd_reneg_6m
            ,CAST(SUM(contratos_reneg.flag_contrato_renegociado) AS DOUBLE)/
                  COUNT(DISTINCT COALESCE(contratos_cntrt.num_contrato_atual,
                                          contratos_quit.num_contrato_atual,
                                          contratos_reneg.num_contrato_atual)) as pct_cntrts_reneg_6m
            
            FROM contratos 
            LEFT JOIN contratos_cntrt
            ON contratos.cpf9_espec = contratos_cntrt.cpf9_espec
                AND contratos.cnpj_espec = contratos_cntrt.cnpj_espec
                AND contratos.safra = contratos_cntrt.safra
                AND contratos.num_contrato_atual = contratos_cntrt.num_contrato_atual
                AND contratos_cntrt.defasagem < 6

            LEFT JOIN contratos_quit
            ON contratos.cpf9_espec = contratos_quit.cpf9_espec
                AND contratos.cnpj_espec = contratos_quit.cnpj_espec
                AND contratos.safra = contratos_quit.safra
                AND contratos.num_contrato_atual = contratos_quit.num_contrato_atual
                AND contratos_quit.defasagem < 6

            LEFT JOIN contratos_reneg
            ON contratos.cpf9_espec = contratos_reneg.cpf9_espec
                AND contratos.cnpj_espec = contratos_reneg.cnpj_espec
                AND contratos.safra = contratos_reneg.safra
                AND contratos.num_contrato_atual = contratos_reneg.num_contrato_atual
                AND contratos_reneg.defasagem < 6

            GROUP BY 1,2,3

), contratos_3m as ( -- 1 linha por espec, safra

        SELECT DISTINCT
             contratos.cpf9_espec
            ,contratos.cnpj_espec
            ,contratos.safra
            
            ,COUNT(DISTINCT COALESCE(contratos_cntrt.num_contrato_atual,
                                    contratos_quit.num_contrato_atual,
                                    contratos_reneg.num_contrato_atual)) as qtd_contratos_3m

            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_3m
            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_3m
            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_3m 
            ,AVG(contratos_cntrt.idade) as avg_idade_clientes_3m
            ,SUM(CASE WHEN contratos_cntrt.saldo_bacenpf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_3m
            ,SUM(contratos_cntrt.saldo_bacenpf) as vlr_cntrts_sld_pos_bc_3m
            ,AVG(contratos_cntrt.plano) as avg_plano_cntrt_3m

            ,SUM(CASE WHEN contratos_quit.data_quitacao_contrato IS NULL THEN 1 ELSE 0 END) as qtd_cntrts_em_aberto_3m
            ,AVG(contratos_quit.mob_quit_contrato) as avg_mob_quit_cntrt_3m
            
            ,SUM(contratos_reneg.flag_contrato_renegociado) as qtd_cntrt_reneg_3m
            ,SUM(contratos_reneg.status_fpd_renegs) as qtd_fpd_reneg_3m
            ,CAST(SUM(contratos_reneg.flag_contrato_renegociado) AS DOUBLE)/
                  COUNT(DISTINCT COALESCE(contratos_cntrt.num_contrato_atual,
                                          contratos_quit.num_contrato_atual,
                                          contratos_reneg.num_contrato_atual)) as pct_cntrts_reneg_3m
            
            FROM contratos 
            LEFT JOIN contratos_cntrt
            ON contratos.cpf9_espec = contratos_cntrt.cpf9_espec
                AND contratos.cnpj_espec = contratos_cntrt.cnpj_espec
                AND contratos.safra = contratos_cntrt.safra
                AND contratos.num_contrato_atual = contratos_cntrt.num_contrato_atual
                AND contratos_cntrt.defasagem < 3

            LEFT JOIN contratos_quit
            ON contratos.cpf9_espec = contratos_quit.cpf9_espec
                AND contratos.cnpj_espec = contratos_quit.cnpj_espec
                AND contratos.safra = contratos_quit.safra
                AND contratos.num_contrato_atual = contratos_quit.num_contrato_atual
                AND contratos_quit.defasagem < 3

            LEFT JOIN contratos_reneg
            ON contratos.cpf9_espec = contratos_reneg.cpf9_espec
                AND contratos.cnpj_espec = contratos_reneg.cnpj_espec
                AND contratos.safra = contratos_reneg.safra
                AND contratos.num_contrato_atual = contratos_reneg.num_contrato_atual
                AND contratos_reneg.defasagem < 3

            GROUP BY 1,2,3

), contratos_1m as ( -- 1 linha por espec, safra

        SELECT DISTINCT
             contratos.cpf9_espec
            ,contratos.cnpj_espec
            ,contratos.safra
            
            ,COUNT(DISTINCT COALESCE(contratos_cntrt.num_contrato_atual,
                                    contratos_quit.num_contrato_atual,
                                    contratos_reneg.num_contrato_atual)) as qtd_contratos_1m

            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_1m
            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_1m
            ,SUM(CASE WHEN contratos_cntrt.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_1m 
            ,AVG(contratos_cntrt.idade) as avg_idade_clientes_1m
            ,SUM(CASE WHEN contratos_cntrt.saldo_bacenpf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_1m
            ,SUM(contratos_cntrt.saldo_bacenpf) as vlr_cntrts_sld_pos_bc_1m
            ,AVG(contratos_cntrt.plano) as avg_plano_cntrt_1m

            ,SUM(CASE WHEN contratos_quit.data_quitacao_contrato IS NULL THEN 1 ELSE 0 END) as qtd_cntrts_em_aberto_1m
            ,AVG(contratos_quit.mob_quit_contrato) as avg_mob_quit_cntrt_1m
            
            ,SUM(contratos_reneg.flag_contrato_renegociado) as qtd_cntrt_reneg_1m
            ,SUM(contratos_reneg.status_fpd_renegs) as qtd_fpd_reneg_1m
            ,CAST(SUM(contratos_reneg.flag_contrato_renegociado) AS DOUBLE)/
                  COUNT(DISTINCT COALESCE(contratos_cntrt.num_contrato_atual,
                                          contratos_quit.num_contrato_atual,
                                          contratos_reneg.num_contrato_atual)) as pct_cntrts_reneg_1m
            
            FROM contratos 
            LEFT JOIN contratos_cntrt
            ON contratos.cpf9_espec = contratos_cntrt.cpf9_espec
                AND contratos.cnpj_espec = contratos_cntrt.cnpj_espec
                AND contratos.safra = contratos_cntrt.safra
                AND contratos.num_contrato_atual = contratos_cntrt.num_contrato_atual
                AND contratos_cntrt.defasagem < 1

            LEFT JOIN contratos_quit
            ON contratos.cpf9_espec = contratos_quit.cpf9_espec
                AND contratos.cnpj_espec = contratos_quit.cnpj_espec
                AND contratos.safra = contratos_quit.safra
                AND contratos.num_contrato_atual = contratos_quit.num_contrato_atual
                AND contratos_quit.defasagem < 1

            LEFT JOIN contratos_reneg
            ON contratos.cpf9_espec = contratos_reneg.cpf9_espec
                AND contratos.cnpj_espec = contratos_reneg.cnpj_espec
                AND contratos.safra = contratos_reneg.safra
                AND contratos.num_contrato_atual = contratos_reneg.num_contrato_atual
                AND contratos_reneg.defasagem < 1

            GROUP BY 1,2,3

) -- 1 linha por espec, safra

    SELECT 
    
        pub_inicial.*

        ,contratos_1m.qtd_contratos_1m
        ,contratos_1m.qtd_cntrt_novo_1m
        ,contratos_1m.qtd_cntrt_renov_int_1m
        ,contratos_1m.qtd_cntrt_renov_merc_1m
        ,contratos_1m.avg_idade_clientes_1m
        ,contratos_1m.qtd_cntrts_sld_pos_bc_1m
        ,contratos_1m.vlr_cntrts_sld_pos_bc_1m
        ,contratos_1m.avg_plano_cntrt_1m        
        ,contratos_1m.qtd_cntrts_em_aberto_1m
        ,contratos_1m.avg_mob_quit_cntrt_1m
        ,contratos_1m.qtd_cntrt_reneg_1m
        ,contratos_1m.qtd_fpd_reneg_1m
        ,contratos_1m.pct_cntrts_reneg_1m

        ,contratos_3m.qtd_contratos_3m
        ,contratos_3m.qtd_cntrt_novo_3m
        ,contratos_3m.qtd_cntrt_renov_int_3m
        ,contratos_3m.qtd_cntrt_renov_merc_3m
        ,contratos_3m.avg_idade_clientes_3m
        ,contratos_3m.qtd_cntrts_sld_pos_bc_3m
        ,contratos_3m.vlr_cntrts_sld_pos_bc_3m
        ,contratos_3m.avg_plano_cntrt_3m        
        ,contratos_3m.qtd_cntrts_em_aberto_3m
        ,contratos_3m.avg_mob_quit_cntrt_3m
        ,contratos_3m.qtd_cntrt_reneg_3m
        ,contratos_3m.qtd_fpd_reneg_3m
        ,contratos_3m.pct_cntrts_reneg_3m

        ,contratos_6m.qtd_contratos_6m
        ,contratos_6m.qtd_cntrt_novo_6m
        ,contratos_6m.qtd_cntrt_renov_int_6m
        ,contratos_6m.qtd_cntrt_renov_merc_6m
        ,contratos_6m.avg_idade_clientes_6m
        ,contratos_6m.qtd_cntrts_sld_pos_bc_6m
        ,contratos_6m.vlr_cntrts_sld_pos_bc_6m
        ,contratos_6m.avg_plano_cntrt_6m        
        ,contratos_6m.qtd_cntrts_em_aberto_6m
        ,contratos_6m.avg_mob_quit_cntrt_6m
        ,contratos_6m.qtd_cntrt_reneg_6m
        ,contratos_6m.qtd_fpd_reneg_6m
        ,contratos_6m.pct_cntrts_reneg_6m

        ,CAST(contratos_3m.qtd_contratos_3m as DOUBLE)/contratos_6m.qtd_contratos_6m as rz_qtd_contratos_3m6m
        ,CAST(contratos_1m.qtd_contratos_1m as DOUBLE)/contratos_6m.qtd_contratos_6m as rz_qtd_contratos_1m6m
        ,CAST(contratos_1m.qtd_contratos_1m as DOUBLE)/contratos_3m.qtd_contratos_3m as rz_qtd_contratos_1m3m

    FROM pub_inicial
    LEFT JOIN contratos_6m
    ON  pub_inicial.cpf9_espec = contratos_6m.cpf9_espec
        and pub_inicial.cnpj_espec = contratos_6m.cnpj_espec
        and pub_inicial.safra = contratos_6m.safra

    LEFT JOIN contratos_3m
    ON  pub_inicial.cpf9_espec = contratos_3m.cpf9_espec
        and pub_inicial.cnpj_espec = contratos_3m.cnpj_espec
        and pub_inicial.safra = contratos_3m.safra

    LEFT JOIN contratos_1m
    ON  pub_inicial.cpf9_espec = contratos_1m.cpf9_espec
        and pub_inicial.cnpj_espec = contratos_1m.cnpj_espec
        and pub_inicial.safra = contratos_1m.safra;





















with pub_inicial as (

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
            

), contratos_def as (        
	SELECT DISTINCT
             contratos.cnpj_espec
            ,contratos.safra
            
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_contratos_1m
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_contratos_3m
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_contratos_6m
            
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.politica_micro = 'Novos' THEN 1 ELSE 0 END) as qtd_cntrt_novo_6m
            
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.politica_micro = 'Renov_Interna' THEN 1 ELSE 0 END) as qtd_cntrt_renov_int_6m
            
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_1m 
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_3m 
            ,SUM(CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.politica_micro = 'Renov_Mercado' THEN 1 ELSE 0 END) as qtd_cntrt_renov_merc_6m 
            
			,AVG(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.plano ELSE NULL END) as avg_plano_cntrt_1m            
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.plano ELSE NULL END) as avg_plano_cntrt_3m
            ,AVG(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.plano ELSE NULL END) as avg_plano_cntrt_6m            

			,AVG(CASE WHEN contratos.defasagem_cntrt < 1 THEN contratos.idade ELSE NULL END) as avg_idade_clientes_1m
			,AVG(CASE WHEN contratos.defasagem_cntrt < 3 THEN contratos.idade ELSE NULL END) as avg_idade_clientes_3m
			,AVG(CASE WHEN contratos.defasagem_cntrt < 6 THEN contratos.idade ELSE NULL END) as avg_idade_clientes_6m            

            ,SUM(CASE WHEN contratos.defasagem_cntrt > 1 AND contratos.defasagem_cntrt < 3 AND contratos.saldo_bacen_pf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt > 1 AND contratos.defasagem_cntrt < 5 AND contratos.saldo_bacen_pf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_3m           
            ,SUM(CASE WHEN contratos.defasagem_cntrt > 1 AND contratos.defasagem_cntrt < 8 AND contratos.saldo_bacen_pf > 0 THEN 1 ELSE 0 END) as qtd_cntrts_sld_pos_bc_6m

			,SUM(CASE WHEN contratos.defasagem_cntrt > 1 AND contratos.defasagem_cntrt < 3 THEN contratos.saldo_bacen_pf ELSE 0 END) as vlr_cntrts_sld_pos_bc_1m
            ,SUM(CASE WHEN contratos.defasagem_cntrt > 1 AND contratos.defasagem_cntrt < 5 THEN contratos.saldo_bacen_pf ELSE 0 END) as vlr_cntrts_sld_pos_bc_3m
            ,SUM(CASE WHEN contratos.defasagem_cntrt > 1 AND contratos.defasagem_cntrt < 8 THEN contratos.saldo_bacen_pf ELSE 0 END) as vlr_cntrts_sld_pos_bc_6m

            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_quit is NULL or contratos.defasagem_quit < 0 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_cntrts_em_aberto_1m
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_quit is NULL or contratos.defasagem_quit < 2 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_cntrts_em_aberto_3m            
            ,COUNT(DISTINCT (CASE WHEN contratos.defasagem_quit is NULL or contratos.defasagem_quit < 5 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_cntrts_em_aberto_6m


			,AVG(CASE WHEN contratos.defasagem_quit > 0 AND contratos.defasagem_quit < 2 THEN contratos.mob_quit_contrato ELSE NULL END) as avg_mob_quit_cntrt_1
            ,AVG(CASE WHEN contratos.defasagem_quit > 0 AND contratos.defasagem_quit < 4 THEN contratos.mob_quit_contrato ELSE NULL END) as avg_mob_quit_cntrt_3m
            ,AVG(CASE WHEN contratos.defasagem_quit > 0 AND contratos.defasagem_quit < 7 THEN contratos.mob_quit_contrato ELSE NULL END) as avg_mob_quit_cntrt_6m

			,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 1 AND contratos.flag_contrato_renegociado = 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_cntrt_reneg_1m
			,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.flag_contrato_renegociado = 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_cntrt_reneg_3m
			,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.flag_contrato_renegociado = 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_cntrt_reneg_6m

			,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.status_fpd_reneg = 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_fpd_reneg_1m
			,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 3 AND contratos.status_fpd_reneg = 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_fpd_reneg_3m
			,COUNT(DISTINCT (CASE WHEN contratos.defasagem_cntrt < 6 AND contratos.status_fpd_reneg = 1 THEN contratos.num_contrato_atual ELSE NULL END)) as qtd_fpd_reneg_6m
            
            FROM contratos 
            GROUP BY 1,2

)            
	SELECT DISTINCT
	
			pub_inicial.*
            
            ,contratos_def.qtd_contratos_1m
            ,contratos_def.qtd_contratos_3m
            ,contratos_def.qtd_contratos_6m
            
            ,contratos_def.qtd_cntrt_novo_1m
            ,contratos_def.qtd_cntrt_novo_3m
            ,contratos_def.qtd_cntrt_novo_6m
            
            ,contratos_def.qtd_cntrt_renov_int_1m
            ,contratos_def.qtd_cntrt_renov_int_3m
            ,contratos_def.qtd_cntrt_renov_int_6m
            
            ,contratos_def.qtd_cntrt_renov_merc_1m 
            ,contratos_def.qtd_cntrt_renov_merc_3m 
            ,contratos_def.qtd_cntrt_renov_merc_6m 
            
			,contratos_def.avg_plano_cntrt_1m            
            ,contratos_def.avg_plano_cntrt_3m
            ,contratos_def.avg_plano_cntrt_6m            

			,contratos_def.avg_idade_clientes_1m
			,contratos_def.avg_idade_clientes_3m
			,contratos_def.avg_idade_clientes_6m            

            ,contratos_def.qtd_cntrts_sld_pos_bc_1m
            ,contratos_def.qtd_cntrts_sld_pos_bc_3m           
            ,contratos_def.qtd_cntrts_sld_pos_bc_6m

			,contratos_def.vlr_cntrts_sld_pos_bc_1m
            ,contratos_def.vlr_cntrts_sld_pos_bc_3m
            ,contratos_def.vlr_cntrts_sld_pos_bc_6m

            ,contratos_def.qtd_cntrts_em_aberto_1m
            ,contratos_def.qtd_cntrts_em_aberto_3m            
            ,contratos_def.qtd_cntrts_em_aberto_6m
			
            ,contratos_def.avg_mob_quit_cntrt_1
            ,contratos_def.avg_mob_quit_cntrt_3m
            ,contratos_def.avg_mob_quit_cntrt_6m

			,contratos_def.qtd_cntrt_reneg_1m
			,contratos_def.qtd_cntrt_reneg_3m
			,contratos_def.qtd_cntrt_reneg_6m

			,contratos_def.qtd_fpd_reneg_1m
			,contratos_def.qtd_fpd_reneg_3m
			,contratos_def.qtd_fpd_reneg_6m
			
			,CASE WHEN contratos_def.qtd_contratos_1m IS NOT NULL AND contratos_def.qtd_contratos_1m > 0
				THEN CAST(contratos_def.qtd_cntrt_reneg_1m AS DOUBLE)/contratos_def.qtd_contratos_1m
				ELSE 0
			 END as pct_cntrts_reneg_1m
			,CASE WHEN contratos_def.qtd_contratos_3m IS NOT NULL AND contratos_def.qtd_contratos_3m > 0
				THEN CAST(contratos_def.qtd_cntrt_reneg_3m AS DOUBLE)/contratos_def.qtd_contratos_3m
				ELSE 0
			 END as pct_cntrts_reneg_3m
			,CASE WHEN contratos_def.qtd_contratos_6m IS NOT NULL AND contratos_def.qtd_contratos_6m > 0
				THEN CAST(contratos_def.qtd_cntrt_reneg_6m AS DOUBLE)/contratos_def.qtd_contratos_6m
				ELSE 0
			 END as pct_cntrts_reneg_6m

			 ,CASE WHEN contratos_def.qtd_contratos_6m IS NOT NULL AND contratos_def.qtd_contratos_6m > 0
				THEN CAST(contratos_def.qtd_contratos_3m AS DOUBLE)/contratos_def.qtd_contratos_6m
				ELSE 0
			 END as rz_qtd_contratos_3m6m
			 ,CASE WHEN contratos_def.qtd_contratos_6m IS NOT NULL AND contratos_def.qtd_contratos_6m > 0
				THEN CAST(contratos_def.qtd_contratos_1m AS DOUBLE)/contratos_def.qtd_contratos_6m
				ELSE 0
			 END as rz_qtd_contratos_1m6m
			 ,CASE WHEN contratos_def.qtd_contratos_3m IS NOT NULL AND contratos_def.qtd_contratos_3m > 0
				THEN CAST(contratos_def.qtd_contratos_1m AS DOUBLE)/contratos_def.qtd_contratos_3m
				ELSE 0
			 END as rz_qtd_contratos_1m3m
			 			 
            FROM pub_inicial
            LEFT JOIN contratos_def
            ON pub_inicial.cnpj_espec = contratos_def.cnpj_espec 
            	AND pub_inicial.safra = contratos_def.safra;
















DROP TABLE tms_mdl_espec_mdl_prod_especialista;

CREATE TABLE IF NOT EXISTS tms_mdl_espec_mdl_prod_especialista (
    cpf9_espec bigint,
    SAFRA integer,
    SAFRA_MOD integer,
    flag_pjampliada integer,
    cnpj_espec bigint,
    status_espec text
);

INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202401,202312,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202402,202401,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202403,202402,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202404,202403,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202405,202404,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202406,202405,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202407,202406,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (123456789,202408,202407,0,12345678,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202307,202306,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202308,202307,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202309,202308,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202310,202309,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202311,202310,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202312,202311,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202401,202312,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202402,202401,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202403,202402,1,87654321,"Habilitado a Produzir");
INSERT INTO tms_mdl_espec_mdl_prod_especialista VALUES (987654321,202404,202403,1,87654321,"Habilitado a Produzir");






DROP TABLE historica_contratos;

CREATE TABLE IF NOT EXISTS historica_contratos (
    cpf9_espec bigint,
    cnpj_espec bigint,
    SAFRA integer,
    num_contrato_atual integer,
    flag_contrato_renegociado integer,
    data_operacao text,
    data_quitacao_contrato text,
    politica_micro text,
    idade integer,
    saldo_bacen_pf double,
    plano integer,
    mob_quit_contrato integer,
    status_fpd_reneg integer
);


INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202305,1,0,DATE('2023-05-12'),DATE('2024-05-12'),"Novos",35,NULL,12,12,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202401,2,1,DATE('2024-01-12'),NULL,"Novos",32,500,12,NULL,0);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202401,3,0,DATE('2024-01-18'),DATE('2024-07-26'),"Renov_Mercado",35,NULL,6,6,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202402,4,0,DATE('2024-02-10'),NULL,"Novos",76,257,8,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202402,5,0,DATE('2024-02-17'),DATE('2024-06-18'),"Novos",53,NULL,4,4,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202403,6,0,DATE('2024-03-01'),NULL,"Renov_Interna",24,851,10,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202403,7,0,DATE('2024-03-07'),NULL,"Novos",56,15874,10,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202404,8,0,DATE('2024-04-10'),NULL,"Novos",75,NULL,8,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202404,9,0,DATE('2024-04-28'),NULL,"Renov_Interna",43,583,8,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202405,10,0,DATE('2024-05-18'),NULL,"Renov_Interna",45,421,8,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202405,11,1,DATE('2024-05-25'),NULL,"Novos",62,NULL,12,NULL,1);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202406,12,1,DATE('2024-06-13'),NULL,"Novos",49,785,10,NULL,0);
INSERT INTO HISTORICA_CONTRATOS VALUES (123456789,12345678,202406,13,0,DATE('2024-06-21'),NULL,"Novos",65,158,8,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202305,14,0,DATE('2023-05-12'),DATE('2024-01-12'),"Novos",35,0,8,8,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202306,15,0,DATE('2023-06-12'),NULL,"Novos",32,500,10,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202307,16,0,DATE('2023-07-12'),NULL,"Renov_Mercado",35,NULL,12,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202308,17,0,DATE('2023-08-12'),NULL,"Renov_Mercado",76,257,12,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202309,18,0,DATE('2023-09-12'),DATE('2024-03-12'),"Novos",53,NULL,6,6,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202309,19,1,DATE('2023-09-12'),NULL,"Renov_Interna",24,851,8,NULL,0);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202310,20,1,DATE('2023-10-12'),NULL,"Novos",56,15874,6,NULL,1);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202311,21,1,DATE('2023-11-12'),DATE('2024-03-12'),"Novos",75,NULL,4,4,0);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202312,22,1,DATE('2023-12-12'),NULL,"Renov_Interna",43,583,6,NULL,1);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202312,23,0,DATE('2023-12-12'),NULL,"Renov_Interna",45,421,8,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202401,24,0,DATE('2024-01-12'),NULL,"Novos",62,NULL,8,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202401,25,0,DATE('2024-01-12'),NULL,"Novos",49,785,12,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202402,26,0,DATE('2024-02-12'),NULL,"Novos",65,158,10,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202403,27,0,DATE('2024-03-12'),NULL,"Novos",53,NULL,10,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202403,28,0,DATE('2024-03-12'),NULL,"Novos",24,0,12,NULL,NULL);
INSERT INTO HISTORICA_CONTRATOS VALUES (987654321,87654321,202403,29,0,DATE('2024-03-12'),NULL,"Novos",56,200,12,NULL,NULL);





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
        
        ,CASE WHEN A.flag_contrato_renegociado = 0 
            THEN strftime('%Y', A.data_operacao)*100 + strftime('%m', A.data_operacao)
            ELSE NULL 
        END AS SAFRA_CNTRT
        
        ,CASE WHEN A.flag_contrato_renegociado = 0 
            THEN floor((julianday(date(SUBSTR(CAST(pub_inicial.safra_mod as TEXT),1,4)||'-'||
                                       SUBSTR(CAST(pub_inicial.safra_mod as TEXT),5,2)||'-01'))
                        - julianday(A.data_operacao,'start of month'))/30)
            ELSE NULL
        END AS defasagem_cntrt
        
        
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

), contratos_cntrt as (     

	SELECT DISTINCT
        contratos.cpf9_espec
        ,contratos.cnpj_espec
        ,contratos.flag_pjampliada
        ,contratos.safra
        ,contratos.defasagem_cntrt AS defasagem
        ,contratos.num_contrato_atual

        ,TRIM(contratos_cntrt.politica_micro) as politica_micro
        ,contratos_cntrt.idade
        ,contratos_cntrt.saldo_bacen_pf
        ,contratos_cntrt.plano

        FROM contratos
        JOIN CONTRATOS as contratos_cntrt
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_cntrt.cnpj_espec as bigint)
            AND contratos.num_contrato_atual = contratos_cntrt.num_contrato_atual
            AND contratos.safra_mod >= contratos_cntrt.safra_cntrt
            AND contratos_cntrt.defasagem_cntrt < 6
        WHERE contratos.flag_contrato_renegociado = 0
        	  AND contratos.defasagem_cntrt BETWEEN 0 AND 5
        	  
), contratos_quit as (

    SELECT DISTINCT
        contratos.cpf9_espec
        ,contratos.cnpj_espec
        ,contratos.flag_pjampliada
        ,contratos.safra
        ,contratos.defasagem_quit AS defasagem
        ,contratos.num_contrato_atual

        ,contratos_quit.data_quitacao_contrato
        ,contratos_quit.mob_quit_contrato

        FROM contratos
        JOIN CONTRATOS as contratos_quit
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_quit.cnpj_espec as bigint)
            AND CAST (contratos.num_contrato_atual as bigint) = CAST(contratos_quit.num_contrato_atual as bigint)
            AND contratos.safra_mod >= contratos_quit.safra_quit
            AND contratos_quit.defasagem_quit between 0 AND 5
        WHERE contratos.data_quitacao_contrato IS NOT NULL
        	  AND contratos.defasagem_quit BETWEEN 0 AND 5

)--, contratos_reneg as (

    SELECT DISTINCT
        contratos.cpf9_espec
        ,contratos.cnpj_espec
        ,contratos.flag_pjampliada
        ,contratos.safra
        ,contratos.defasagem_reneg AS defasagem
        ,contratos.num_contrato_atual

        ,contratos_reneg.flag_contrato_renegociado
        ,contratos_reneg.status_fpd_reneg

        FROM contratos
        LEFT JOIN CONTRATOS as contratos_reneg
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_reneg.cnpj_espec as bigint)
            AND CAST (contratos.num_contrato_atual as bigint) = CAST(contratos_reneg.num_contrato_atual as bigint)
            AND contratos.safra_mod >= contratos_reneg.safra_reneg
        WHERE contratos.flag_contrato_renegociado = 1
        	  AND contratos.defasagem_reneg BETWEEN 0 AND 5











