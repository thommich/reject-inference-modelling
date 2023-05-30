from __future__ import annotations

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
        self.mob = parameters['mob']
        self.target_column
        self.approved_column
        self.approved_value
        self.n_features_1st_eval



    def _read_data_from_pqfile(self, ds_alias: str, ds_candidate_features: List[str], audience_cols: List) -> Tuple[pd.DataFrame, List[str]]:
        #formats the name of the parquet file that will hold the persisted data
        parquet_file_path = '/temp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, ds_alias.upper(), '.parquet'])

        #Read batch of data from DBMS
        df = pd.read_parquet(parquet_file, columns=ds_candidate_features)

        #CHECK IF ANY DTYPE CONVERSION WILL BE NECESSARY

        #Filter analytical columns
        analytical_vars = [col for col in df.columns.to_list() if col in df.columns and col not in audience_cols]
        #Add target and approved columns
        df = df[analytical_vars + [self.approved_column, self.target_column]]

        return df, analytical_vars


    def _prepare_training_datasets(self, df: pd.DataFrame) -> Tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
        ##PREPARE TRAIN AND TEST DATA
        #Creates a boolean series to identify "approved" individuals using the "approved_column" parameter 
        df[self.approved_column] = df[self.approved_column].astype(str) 
        approved = df[self.approved_column].str.lstrip().str.rstrip() == str(self.approved_value)
        data=df[approved]

        #Creates train and test datasets
        df_train, df_test = train_test_split(data, test_size=0.2, random_state=42) 
        df_neg = df[~approved]

        return df_train, df_test, df_neg #type: ignore
    

    def _univariate_evaluation(self, analytical_vars: List[str], ds: DataSource, df: pd.DataFrame) -> pd.DataFrame:
        ##PREPARE TRAIN AND TEST DATA
        df_train, df_test, df_neg = self._prepare_training_datasets(df)

        #Instantiates a LightGBM classifier
        clf = LGBMClassifier(randon_state=23, n_estimators=1, max_depth=5, num_leaves = 25) 
        pred = {'inf_treino': [], 'inf_sem_perf': []}
        
        # Loop through every feature and calculate train and inferred predictions 
        for feat in tqdm(analytical_vars, leave=False, desc=' '.join(['Evaluating features from ', ds.alias])): 
            clf.fit(df_train[feat].to_numpy().reshape(-1, 1), df_train[self.target_column])
            
            pred_treino = clf.predict_proba(df_test[feat].to_numpy().reshape(-1, 1))[:, 1].mean() 
            pred_sem_perf = clf.predict_proba(df_neg[feat].to_numpy().reshape(-1, 1))[:, 1].mean()
            
            pred['inf_treino'].append(pred_treino) 
            pred['inf_sem_perf'].append(pred_sem_perf)

        results = pd.concat((pd.DataFrame({'feature': analytical_vars}), pd.DataFrame(pred)), axis = 1)
        results['diff'] = results['inf_sem_perf'] / (results['inf_treino'] + results['inf_sem_perf'])

        return results

    
    def _multivariate_evaluation(self, pre_selected_feats: List[str], df: pd.DataFrame) -> List[str]:
        ##PREPARE TRAIN AND TEST DATA
        df_train, _, _ = self._prepare_training_datasets(df) 

        #Trains a LightGBM classifier
        clf = LGBMClassifier(randon_state=23, num_leaves = 40) 
        clf.fit(df_train[pre_selected_feats], df_train[self.target_column])
        boost = clf.booster_
        
        n_features = pd.DataFrame(
            {'features': boost.feature_name(),
             'importance': clf.feature_importances_}
        ).sort_values('importance', ascending = False).iloc[:self.n_features]['features'].values.tolist()
        
        # ##PREPARE TRAIN AND TEST DATA
        # df_train, _, _ = self._prepare_training_datasets(df)

        # #Now, a new model is trained with the final set of features
        # clf = LGBMClassifier(randon_state=23, num_leaves = 40) 
        # clf.fit(df_train[pre_selected_feats], df_train[self.target_column])
        # boost = clf.booster_

        return n_features
    

    def _persist_parquet_file(self, sorted_results: pd.DataFrame, results: pd.DataFrame, alias: str, df: pd.DataFrame) -> List[str]:
        #Formats the name of the parquet file that will hold the persisted data
        parquet_file_path = '/temp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, alias.upper(), '.parquet'])

        if not sorted_results:
            sorted_results = results.sort_values(by = 'diff', ascending = False)
            fp.write(parquet_file, df, compression='SNAPPY')
        else:
            concat_dfs = pd.concat([sorted_results, results]).sort_values(by = 'diff', ascending = False)
            sorted_results = concat_dfs
            fp.write(parquet_file, df, compression='SNAPPY', append=True)
            
        filtered_feats_list = sorted_results.iloc[:self.n_features_1st_eval]['features'].to_list()
        return filtered_feats_list


    #Select the 'n_features_batch' best feature candidates from each data source (univariate analysis)
    # based on the capacity to discriminate those individuals with observed performance against the ones
    # who have been denied. Here, higher default rates are expected for inferred/denied individuals when
    # in comparision to the other group.
    def narrow_down_feat_candidates_univar(self, ds_group: DataSourceGroup) -> List[str]:
        ##INITIALIZE LOOP VARIABLES
        #Create variables for the main DataFrames to be passed around
        data_source: DataSource = getattr(ds_group, 'current_ds')
        
        #Calculate total number of batches and start reading data from the DB
        num_total_batches = len(data_source.get_columns()) - len(ds_group.get_df_audience().get_columns())/self._book_cols_batch_size

        #Trigger DB join pub + book
        ds_group.left_join_audience_tb(data_source, self.mob)

        #Initialize list to hold intermediate/final results
        sorted_results = pd.DataFrame()
        #Iterates through each batch of columns
        for index in tqdm(range(num_total_batches), leave=False):
            columns_to_read = data_source.columns[index*self._book_cols_batch_size: (index+1)*self._book_cols_batch_size]

            #READS DATA FROM THE DATABASE
            df = ds_group.get_data_batch(columns_to_read)

            #Filter analytical columns and add target and approved columns
            analytical_vars = [col for col in df.columns.to_list() if col in df.columns and col not in ds_group.audience_pk]
            df = df[analytical_vars + [self.approved_column, self.target_column]]

            ##INSTANTIATES A MODEL AND LOOPS THROUGH EVERY FEATURE FITTING, TRAINING AND EVALUATING
            results = self._univariate_evaluation(analytical_vars, data_source, df)

            ##PERSISTS THE READ DATAFRAME IN A PARQUET FILE
            candidate_features = self._persist_parquet_file(sorted_results, results, data_source.alias, df)

            #ATTACHES THE BEST FEATURES FOUND UNTIL THIS MOMENT TO THE DATA_SOURCE OBJ
            data_source.candidate_features = candidate_features
        
        return data_source.candidate_features


    def select_top_features_multivar(self, df_audience: DataSource, ds_candidate_features: List[str], ds_alias: str) -> List[str]:
        #_read_data_from_db
        df, analytical_vars = self._read_data_from_pqfile(ds_alias, ds_candidate_features, df_audience.columns)

        #_selected_features_evaluation
        n_features = self._multivariate_evaluation(analytical_vars, df)

        return n_features
    

    def get_rfe_df(self, ds_group: DataSourceGroup) -> pd.DataFrame: 
        
        audience = ds_group.df_audience
        
        df_aud, _ = self._read_data_from_pqfile(audience.alias, audience.columns, ds_group.audience_pk)

        df_rfe = df_aud
        for feature_book in ds_group.data_sources:
            ds_group.current_ds = ds_group.data_sources[feature_book]
            ds = ds_group.current_ds

            df, _ = self._read_data_from_pqfile(ds.alias, ds.top_rnkd_feats, ds_group.get_df_audience().get_columns())

            df_rfe = df_rfe.join(df.set_index(ds_group.audience_pk))
        
        return df_rfe


    def execute_rfe(self):
        ...


    def plot_results(self): 
        pass

    def get_features(self): 
        pass


    def get_final_results(self): 
        pass
    