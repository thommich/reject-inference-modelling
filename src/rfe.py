import yaml
from pydantic import BaseModel from abc import ABC, abstractmethod
from enum import Enum from Type import List
from typing import Dict, Tuple, List, Any

from .datasources import DataSourceGroup


class RFE():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        
        Args:
            Iname (str): 0 nome lógico da tabela (nome legível por humanos)
            schema (str): O nome do schema no qual esta tabela reside.. 
            pname (str): O nome físico da tabela (nome real no banco de dados) 
            alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    def __init__( self,
        parameters: Dict,
        engines_params: Dict,
        data_srcs_params: Dict
    ):
        self.parameters = parameters
        self.data_sources_group = DataSourceGroup(data_srcs_params)
        self.engines = Engines(engines_params)

    #Select the 'n_features_batch' best feature candidates from each data source (univariate analysis)
    def __narrow_down_candidates_univar(self, chunk_size: int):
        #Get df_public from DB and store in memory

        #Get df_public index to use later

        #Loops through each data source specified on the config file        
        for ds in self.data_sources_group:
            #Trigger DB join pub + book

            #Estimate total number of batches and start reading data from the DB
            num_total_batches = ds.get_total_batches(chunk_size)
            for i in tqdm(range(num_total_batches), leave=False):
                #Read batch of data from DBMS
                data_batch = ds.read_batch(chunk_size)

                #Transform data
                #Train model 
                #Obtain feature importances
                #Merge results with current best candidates, sort in desc order, keep only top n_features

        #Write best candidates to .parquet file
        pass



df_impfeat = pd.read_parquet('./model_files/' + file_name, columns=['PK_RIZNUMDOC_XX'] + vars_list[i*vars_batch_n: (1+1)*vars_batch_n])
df_impfeat.columns 
df_impfeat.columns.str.upper() 
df_impfeat = df_impfeat[[col for col in df_impfeat.columns.str.upper().to_list() if col not in ['FLG_CNTRTC']]]
df_impfeat = df_impfeat[df_impfeat['PK_RIZNUMDOC_XX'].isin(idx_public)]
df_impfeat.set_index(['PK_RIZNUMDOC_XX'], inplace=True)

df_pub = self.df_public[self.df_public['PK_RIZNUMDOC_XX'].isin(idx_public)] 
df_pub.set_index(['PK_RIZNUMDOC_xx'], inplace=True)
setattr(self, 'merged_df', pd.merge(df_impfeat, df_pub, left_index=True, right_index=True))

del df_impfeat
del df_pub
gc.collect()
#print(self.merged_df.head())
imp_feat_batch = self._get_important_features (self.merged_df, vars list, 'Avaliando variáveis do(a) setattr(self, 'df feats eval book', pd.concat([getattr(self, 'df_feats_eval_book'), imp_feat_batch])) +bk_name)








    def get_public_df(self): # -> List[str]: 
        pass
    
    def get_rfe_df(self): # -> List[str]: 
        pass
    
    def plot_results(self): 
        pass