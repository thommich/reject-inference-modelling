import yaml

from tqdm import tqdm
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Tuple, List, Any, Union

import pandas as pd
from datasources import DataSourceGroup, DataSource
from engines import Engine


class RFE():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        
        Args:
            Iname (str): 0 nome lógico da tabela (nome legível por humanos)
            schema (str): O nome do schema no qual esta tabela reside.. 
            pname (str): O nome físico da tabela (nome real no banco de dados) 
            alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    __parameters: Dict[Any, Any]
    approved_column: str
    approved_value: Union[int, str]
    target_column: str 
    remove_bc: bool
    n_features: int
    max_n_feats_join: int
    mob: int


    def __init__( self, parameters: Dict) -> None:
        self.__parameters = parameters       


    #Select the 'n_features_batch' best feature candidates from each data source (univariate analysis)
    def narrow_down_candidates_univar(self, df_public: pd.DataFrame, data_sources_group: DataSourceGroup):


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

            # df_impfeat = pd.read_parquet('./model_files/' + file_name, columns=['PK_RIZNUMDOC_XX'] + vars_list[i*vars_batch_n: (1+1)*vars_batch_n])
            # df_impfeat.columns 
            # df_impfeat.columns.str.upper() 
            # df_impfeat = df_impfeat[[col for col in df_impfeat.columns.str.upper().to_list() if col not in ['FLG_CNTRTC']]]
            # df_impfeat = df_impfeat[df_impfeat['PK_RIZNUMDOC_XX'].isin(idx_public)]
            # df_impfeat.set_index(['PK_RIZNUMDOC_XX'], inplace=True)

            # df_pub = self.df_public[self.df_public['PK_RIZNUMDOC_XX'].isin(idx_public)] 
            # df_pub.set_index(['PK_RIZNUMDOC_xx'], inplace=True)
            # setattr(self, 'merged_df', pd.merge(df_impfeat, df_pub, left_index=True, right_index=True))

            # del df_impfeat
            # del df_pub
            # gc.collect()
            # #print(self.merged_df.head())
            # imp_feat_batch = self._get_important_features (self.merged_df, vars list, 'Avaliando variáveis do(a) setattr(self, 'df feats eval book', pd.concat([getattr(self, 'df_feats_eval_book'), imp_feat_batch])) +bk_name)

    
    def get_rfe_df(self): # -> List[str]: 
        pass
    
    def plot_results(self): 
        pass