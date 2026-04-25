import sqlite3
import random
import math

from tqdm import tqdm
from log_utils import setup_logging, log_func
from sklearn.datasets import make_classification
import numpy as np
import pandas as pd

logger = setup_logging(name=__name__)
module_logger = log_func(__name__)


@module_logger
def create_test_database():
    logger.debug('Creating test data')

    n_samp = 400000
    prop_bad = 0.6
    num_feats = 75
    num_inf = 20
    random.seed(42)
    X, y = make_classification(n_samples=n_samp, 
                               flip_y=0,
                               shuffle=False, 
                               class_sep=2,
                               n_features=num_feats,
                               n_informative=num_inf,
                               n_redundant=0,
                               n_classes=2,
                               n_clusters_per_class=2,
                               weights=[1-prop_bad, prop_bad],
                               random_state=42) 
    
#                                                                           60% = 890.000                                           60% = 240.000
#                            DECISAO_PROP    FLG_CNTRTC  BAD_90_12  %POP.   VOL         BAD_0       BAD_1         BASE INF.: %POP.  VOL         BAD_0       BAD_1   BAD_N/A   
#    PROP|APRV|CNTRT_IT      1               1           0.02       0.1     160.000     156.800      3.200                   0.4    160.000     156.800      3.200        0  
#    PROP|APRV|CNTRT_BC      1               1           0.07       0.2     320.000     297.600     22.400                   ~0.6    86.292      80.252      6.040        0
#    PROP|APRV|SEM_CNTRT     1               0            N/A       0.2     320.000         N/A        N/A                   ~0.6    86.292           0          0   86.292               
#    PROP|NEG|CNTRT_BC       0               1           0.11       0.01     16.000      14.240      1.760                   ~0.6     4.314       3.839        475        0
#    PROP|NEG|SEM_CNTRT      0               0            N/A       0.14    234.000         N/A        N/A                   ~0.6    63.102           0          0   63.102
#    SEM_PROP|CNTRT_BC       N/A             1           0.09       0.35    550.000     500.500     49.500                   0                  

# BAD_90_12         FLG_CNTRTC  DECISAO_PROP
#    0: 240.891     1           1: 237.052/0:  3.839
#    1:   9.715     1           1:   9.240/0:    475 
#  N/A: 149.394     0           1:  86.292/0: 63.102

#    0: 240.891     1           1: 156.800/0: 84.091
#    1:   9.715     1           1:   3.200/0:  6.515   
#  N/A: 149.394     0           1:       0/0: 63.102+86.292

  
    cpf = [x for x in range(n_samp)]
    #random.shuffle(cpf)
    tp_pes = ["F"]*n_samp
    safras = [random.choice([x for x in (list(range(202106,202113))) + list(range(202201,202213))]) for _ in range(n_samp)]
    anos = [math.floor(year/100) for year in safras]
    meses = [(year%100) for year in safras]
    dias = [15]*n_samp
    anomesdia = [f"{year}-{month:02}-{day:02}" for year,month,day in zip(anos,meses,dias)]
    anomesdia_bk = [f"{year+1}-{month:02}-{day:02}" for year,month,day in zip(anos,meses,dias)]
    anomesdiautc = [f"{year}-{month:02}-{day:02}" for year,month,day in zip(anos,meses,dias)]
    #flg_cntrtc = [1]*250606 + [0]*149394
    #decisao_prop = [1]*237052 + [0]*3839 + [1]*9240 + [0]*475 + [1]*86292 + [0]*63102
    #bad_90_12 = [0]*240891 + [1]*9715 + [np.nan]*149394    
    flg_cntrtc = [1]*250606 + [0]*149394
    bad_90_12 = [0]*240891 + [1]*9715 + [np.nan]*149394    
    decisao_prop = [1]*156800 + [0]*84091 + [1]*3200 + [0]*6515 + [0]*86292 + [0]*63102
        
    
    logger.debug('Creating test databases')    
    name = "AUDIENCE_TABLE"
    columns = {"PK_RIZNUMDOC_XX": cpf, #np.asarray(cpf),
               "PK_TPP_XX": tp_pes, #np.asarray(tp_pes),
               "PK_DATREF_XX": anomesdia, #np.asarray(anomesdia),
               "PK_DATVER_XX": anomesdiautc, #np.asarray(anomesdiautc),
               "SAFRA_MDL": safras, #np.asarray(safras),
               "FLG_CNTRTC": flg_cntrtc,#np.asarray(flags_cntrtc),
               "DECISAO_PROP": decisao_prop,#np.asarray(flags_cntrtc),
               "BAD_90_12": bad_90_12 #np.asarray(y)
               }
   

    #df_aud = pd.DataFrame(columns)
    
    #df_aud_good = df_aud[df_aud.BAD_90_12 == 0] #7800
    #df_aud_bad_neg = df_aud[df_aud.BAD_90_12 == 1] #2200 

    #bad_as_is = prop_bad*n_samp #200
    #bad_to_be = prop_bad*(n_samp-(prop_neg*n_samp)) #160    
    #df_aud_bad = df_aud_bad_neg.sample(n=int(prop_bad*n_samp)) #200
    #df_aud_bad['BAD_90_12'] = random.shuffle([0]*(int(bad_as_is-bad_to_be)) + [1]*int(bad_to_be))
    
    #df_aud_neg = df_aud_bad_neg[~df_aud_bad_neg.PK_RIZNUMDOC_XX.isin(df_aud_bad.PK_RIZNUMDOC_XX)] #200
    #df_aud_neg['BAD_90_12'] = pd.Series([np.nan]*int(prop_neg*n_samp))
    #df_aud_neg['FLG_CNTRTC'] = pd.Series([0]*int(prop_neg*n_samp))
    #df_aud_neg['DECISAO_PROP'] = pd.Series([0]*int(prop_neg*n_samp))    
    #np.where(df_aud['BAD_90_12']==1, 0, 1).tolist()
    #aud = pd.concat([df_aud_good, df_aud_neg, df_aud_bad], ignore_index=True)
    #aud.sort_values(by='PK_RIZNUMDOC_XX')
    
    #for i, col in enumerate(list(columns.keys())):
        #logger.debug(f'i: {i}   col: {col}')
        #columns[str(col)] = aud.iloc[:,i].to_list()
    
    logger.debug(f'List cols df: {list(columns.keys())}')
    #logger.debug(f'df: {columns}')


    name2 = "BOOK_BACEN"
    columns2 = {"PK_RIZNUMDOC_XX": cpf,#np.asarray(cpf),
               "PK_TPP_XX": tp_pes,#np.asarray(tp_pes),
               "PK_DATREF_XX": anomesdia_bk}#np.asarray(anomesdia_bk)#,
    
    list_cols = [f'COL_{str(x)}' for x in range(num_feats)]
    for i, col in enumerate(list_cols):
        columns2[str(col)] = X[:,i].tolist()
    
    logger.debug(f'List cols df 2: {list_cols}')    
    
    data = {name: columns, name2:columns2}
    
    logger.debug('Opening DB connection')
    con = sqlite3.connect('inference_modelling_test.db')
       
    for x in data.items():
        logger.debug('Creating table: %s' % x[0])
        
        con.cursor().execute(
            f'''CREATE TABLE  IF NOT EXISTS {x[0]} ({",".join(x[1].keys())})''')
        logger.debug(f'    List cols: ({",".join(x[1].keys())})')
        columns_names = list(x[1].keys())

        #for idx in range(n_samp):
        #    query = f'''INSERT INTO {x[0]} VALUES {tuple([x[1][column][idx] for column in columns_names])}'''
        #    if idx == 0:
        #        logger.debug(f'    Query: ({query})')read_data_from_db
        #        
        #    con.cursor().execute(query)
        #    con.commit()
            
            
        lst_rows = []
        for idx in range(n_samp):        
            lst_rows.append(tuple([x[1][column][idx] for column in columns_names]))
        
        query_sql = f'''INSERT INTO {x[0]} VALUES ({",".join(['?']*(len(x[1].keys())))})'''
        logger.debug(f'    Query: ({query_sql})')
        logger.debug(f'    Sample Vals: ({lst_rows[0:5]})')
        
        con.cursor().executemany(query_sql,lst_rows)
        con.commit()

    logger.debug('Closing DB connection')
    con.close()