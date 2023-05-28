import yaml

from tqdm import tqdm
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Tuple, List, Any, Union

import gc
import pandas as pd
from datasources import DataSourceGroup, DataSource
from engines import Engine
import fastparquet as fp

from sklearn.model_selection import train_test_split
from lightgbm import LGBMClassifier

class RFE():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        
        Args:
            Iname (str): 0 nome lógico da tabela (nome legível por humanos)
            schema (str): O nome do schema no qual esta tabela reside.. 
            pname (str): O nome físico da tabela (nome real no banco de dados) 
            alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    _parameters: Dict[Any, Any]
    approved_column: str
    approved_value: Union[int, str]
    target_column: str 
    remove_bc: bool
    n_features: int
    n_features_1st_eval: int
    max_n_feats_join: int
    _mob: int


    def __init__(self, parameters: Dict) -> None:
        self._parameters = parameters
        self._book_cols_batch_size = parameters['book_cols_batch_size']
        self._mob = parameters['mob']
        self.target_column
        self.approved_column
        self.approved_value
        self.n_features_1st_eval



    #Select the 'n_features_batch' best feature candidates from each data source (univariate analysis)
    # based on the capacity to discriminate those individuals with observed performance against the ones
    # who have been denied. Here, higher default rates are expected for inferred/denied individuals when
    # in comparision to the other group.
    def narrow_down_feat_candidates_univar(self, df_audience: DataSource, data_source: DataSource) -> None:
        ##INITIALIZE LOOP VARIABLES
        #Trigger DB join pub + book
        data_source.left_join_audience_tb(df_audience, self._mob)

        #Calculate total number of batches and start reading data from the DB
        num_total_batches = len(data_source.get_columns()) - len(df_audience.get_columns())/self._book_cols_batch_size

        #Initialize list to hold intermediate/final results
        sorted_results = []

        for i in tqdm(range(num_total_batches), leave=False):
            #READS DATA FROM THE DATABASE
            df, analytical_vars = self._read_data_from_db(data_source, df_audience.columns, i)

            ##PREPARE TRAIN AND TEST DATA
            df_train, df_test, df_neg = self._prepare_training_datasets(df)

            ##INSTANTIATES A MODEL AND LOOPS THROUGH EVERY FEATURE FITTING, TRAINING AND EVALUATING
            results = self._univar_feature_evaluation(analytical_vars, data_source, df_train, df_test, df_neg)

            ##PERSISTS THE READ DATAFRAME IN A PARQUET FILE
            candidate_features = self._persist_parquet_file(sorted_results, results, data_source.alias, data_source, df)

            data_source.candidate_features = candidate_features
        
        return


    def _read_data_from_db(self, data_source: DataSource, audience_cols: List, index: int):
        #Read batch of data from DBMS
        data_source.read_batch_of_data(index, self._book_cols_batch_size)
        df = data_source.data_batch
        df['PK_DATREF_XX'] = pd.to_datetime(df['PK_DATREF_XX'])
        df['PK_DATVER_XX'] = pd.to_datetime(df['PK_DATVER_XX'])

        #Filter analytical columns
        analytical_vars = [col for col in df.columns.to_list() if col in df.columns and col not in audience_cols]
        #Add target and approved columns
        df = df[analytical_vars + [self.approved_column, self.target_column]]

        return df, analytical_vars


    def _prepare_training_datasets(self, df: pd.DataFrame):
        ##PREPARE TRAIN AND TEST DATA
        #Creates a boolean series to identify "approved" individuals using the "approved_column" parameter 
        df[self.approved_column] = df[self.approved_column].astype(str) 
        approved = df[self.approved_column].str.lstrip().str.rstrip() == str(self.approved_value)
        data=df[approved]

        #Creates train and test datasets
        df_train, df_test = train_test_split(data, test_size=0.2, random_state=42) 
        df_neg = df[~approved]

        return df_train, df_test, df_neg
    

    def _univar_feature_evaluation(self,
                                   analytical_vars: List[str],
                                   data_source: DataSource,
                                   df_train: pd.DataFrame,
                                   df_test:pd.DataFrame,
                                   df_neg: pd.DataFrame):
        #Instantiates a LightGBM classifier
        clf = LGBMClassifier(randon_state=23, n_estimators=1, max_depth=5, num_leaves = 25) 
        pred = {'inf_treino': [], 'inf_sem_perf': []}
        
        # Loop through every feature and calculate train and inferred predictions 
        for feat in tqdm(analytical_vars, leave=False, desc=' '.join(['Evaluating features from ', data_source.alias])): 
            clf.fit(df_train[feat].to_numpy().reshape(-1, 1), df_train[self.target_column])
            
            pred_treino = clf.predict_proba(df_test[feat].to_numpy().reshape(-1, 1))[:, 1].mean() 
            pred_sem_perf = clf.predict_proba(df_neg[feat].to_numpy().reshape(-1, 1))[:, 1].mean()
            
            pred['inf_treino'].append(pred_treino) 
            pred['inf_sem_perf'].append(pred_sem_perf)

        results = pd.concat((pd.DataFrame({'feature': analytical_vars}), pd.DataFrame(pred)), axis = 1)
        results['diff'] = results['inf_sem_perf'] / (results['inf_treino'] + results['inf_sem_perf'])

        return results


    def _persist_parquet_file(self, sorted_results: List, results: pd.DataFrame, alias: str, df: pd.DataFrame):
        #formats the name of the parquet file that will hold the persisted data
        parquet_file_path = '/temp'
        parquet_file = ''.join([parquet_file_path, alias, '.parquet'])

        if not sorted_results:
            sorted_results = results.sort_values(by = 'diff', ascending = False).iloc[:self.n_features_1st_eval]['features'].to_list()
            fp.write(parquet_file, df, compression='SNAPPY')
        else:
            concat_dfs = pd.concat([sorted_results, results]) #type: ignore
            sorted_results = concat_dfs.concat_dfs.sort_values(by = 'diff', ascending = False).iloc[:self.n_features_1st_eval]['features'].to_list()
            fp.write(parquet_file, df, compression='SNAPPY', append=True)
            #current_top_candidates = fp.ParquetFile(parquet_file).columns
            #DECIDED TO KEEP ALL FEATURES ON THE PARQUET FILE SINCE IT CAN BE REUSED FOR LATER EXPERIMENTS
        
        return sorted_results



    def choose_top_features_multivar(self, data_source: DataSource) -> None:
        #_read_data_from_db
        #_prepare_training_datasets
        #_selected_features_evaluation
        #_reatrain the model
        return
    
    def get_rfe_df(self): # -> List[str]: 
        pass
    
    def plot_results(self): 
        pass

