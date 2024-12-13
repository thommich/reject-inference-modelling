with puh inicial as ( -- 1 linha por cpf9_espec, safra

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
        END AS SAFRA RENEG
    
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

        FROM pub_incial
        LEFT JOIN HISTORICA_CONTRATOS as A
        ON CAST (pub_inicial.cnpj_espec as bigint) = CAST(A.cnpj_espec as bigint)
            AND CAST (pub_inicial.cpf9_espec as bigint) = CAST(A.cpf9_espec as bigint)
            AND pub_inicial.safra_mod = A.safra
        
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
        LEFT JOIN CONTRATOS as contratos_cntrt
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_cntrt.cnpj_espec as bigint)
            AND CAST (contratos.cpf9_espec as bigint) = CAST(contratos_cntrt.cpf9_espec as bigint)
            AND contratos.safra_mod >= contratos_cntrt.safra_cntrt
            AND contratos_cntrt.defasagem_cntrt < 6
        WHERE contratos_cntrt.SAFRA_CNTRT IS NOT NULL

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
        LEFT JOIN CONTRATOS as contratos_quit
        ON CAST (contratos.cnpj_espec as bigint) = CAST(contratos_quit.cnpj_espec as bigint)
            AND CAST (contratos.cpf9_espec as bigint) = CAST(contratos_quit.cpf9_espec as bigint)
            AND contratos.safra_mod >= contratos_quit.safra_cntrt
            AND contratos_quit.defasagem_quit < 6
        WHERE contratos_quit.SAFRA_quit IS NOT NULL

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
            AND contratos.safra_mod >= contratos_reneg.safra_cntrt
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