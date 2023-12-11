from __future__ import annotations

from tqdm import tqdm
from typing import Dict, Tuple, List, Union, Callable

import numpy as np
import pandas as pd
from datasources.dsgroup import DataSourcesGroup
from datasources.dsmodel import DataSource
import fastparquet as fp

from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score
from lightgbm import LGBMClassifier, Booster
from functools import partial
import copy
import math
from log_utils import setup_logging, log_func
import matplotlib.pyplot as plt

logger = setup_logging(name=__name__)
module_logger = log_func(__name__)


class RFE():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        
        Args:
            Iname (str): 0 nome lógico da tabela (nome legível por humanos)
            schema (str): O nome do schema no qual esta tabela reside.. 
            pname (str): O nome físico da tabela (nome real no banco de dados) 
            alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    @module_logger
    def __init__(self, parameters: Dict) -> None:
        self.mob: int = parameters['mob']
        self.approved_column: str = parameters['approved_column']
        self.approved_value: Union[str,List,List[str]] = parameters['approved_value']
        self.target_column: str = parameters['target_column']
        self.remove_subpop: Union[bool, None, List, List[str]] = parameters['remove_subpop']
        self.book_cols_batch_size: int = parameters['book_cols_batch_size']
        self.n_features_1st_eval: int = parameters['n_features_1st_eval']
        self.n_features_final: int = parameters['n_features_final']        
        

    @module_logger
    def _read_data_from_pqfile(self, ds_alias: str, ds_candidate_features: List[str]) -> pd.DataFrame:
        
        #formats the name of the parquet file that will hold the persisted data
        parquet_file_path = './tmp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, ds_alias.upper(), '.parquet'])
        columns_to_read = ds_candidate_features + [self.approved_column, self.target_column]

        df = pd.read_parquet(parquet_file, columns=columns_to_read) 

        #CHECK IF ANY DTYPE CONVERSION WILL BE NECESSARY

        return df


    #@module_logger
    def _prepare_training_datasets(self, df: pd.DataFrame) -> Tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
        ##PREPARE TRAIN AND TEST DATA
        #Creates a boolean series to identify "approved" individuals using the "approved_column" parameter 
        df[self.approved_column] = df[self.approved_column].astype(str) 
        approved = df[self.approved_column].str.lstrip().str.rstrip() == str(self.approved_value)
        data=df[approved]

        #Creates train and test datasets
        df_train, df_test = train_test_split(data, test_size=0.2, random_state=42) 
        df_neg = df[~approved]

        return df_train, df_test, df_neg
    

    @module_logger
    def _univariate_evaluation(self, bk_features: List[str], ds: DataSource, df: pd.DataFrame) -> pd.DataFrame:
        ##PREPARE TRAIN AND TEST DATA
        df_train, df_test, df_neg = self._prepare_training_datasets(df)

        #Instantiates a LightGBM classifier
        clf = LGBMClassifier(random_state=23, n_estimators=1, max_depth=5, num_leaves = 25) 
        pred = {'inf_treino': [], 'inf_sem_perf': []}
        
        # Loop through every feature and calculate train and inferred predictions 
        for feat in tqdm(bk_features, leave=False, desc=' '.join(['Evaluating features from ', ds.alias])): 
            clf.fit(df_train[feat].to_numpy().reshape(-1, 1), df_train[self.target_column])
            
            pred_treino = clf.predict_proba(df_test[feat].to_numpy().reshape(-1, 1))[:,1].mean()  # pyright: ignore
            pred_sem_perf = clf.predict_proba(df_neg[feat].to_numpy().reshape(-1, 1))[:,1].mean() # pyright: ignore
            
            pred['inf_treino'].append(pred_treino) 
            pred['inf_sem_perf'].append(pred_sem_perf)

        results = pd.concat((pd.DataFrame({'feature': bk_features}), pd.DataFrame(pred)), axis = 1)
        results['diff'] = results['inf_sem_perf'] / (results['inf_treino'] + results['inf_sem_perf'])

        return results

    
    @module_logger
    def _multivariate_evaluation(self, pre_selected_feats: List[str], df: pd.DataFrame) -> List[str]:
        ##PREPARE TRAIN AND TEST DATA
        df_train, _, _ = self._prepare_training_datasets(df) 

        #Trains a LightGBM classifier
        clf = LGBMClassifier(random_state=23, num_leaves = 40) 
        clf.fit(df_train[pre_selected_feats], df_train[self.target_column])
        boost = clf._Booster
        
        n_features = pd.DataFrame(
            {'features': boost.feature_name(),
             'importance': clf.feature_importances_}
        ).sort_values('importance', ascending = False).iloc[:self.n_features_final]['features'].values.tolist()
    
        return n_features
    

    @module_logger
    def _persist_parquet_file(self, sorted_results: pd.DataFrame, results: pd.DataFrame, alias: str, df: pd.DataFrame) -> List[str]:
        #Formats the name of the parquet file that will hold the persisted data
        parquet_file_path = './tmp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, alias.upper(), '.parquet'])

        if sorted_results.empty:
            sorted_results = results.sort_values(by = 'diff', ascending = False)
            fp.write(parquet_file, df, compression='SNAPPY')
        else:
            concat_dfs = pd.concat([sorted_results, results]).sort_values(by = 'diff', ascending = False)
            sorted_results = concat_dfs
            fp.write(parquet_file, df, compression='SNAPPY', append=True)
        
        filtered_feats_list = sorted_results.iloc[:self.n_features_1st_eval]['feature'].to_list()
        return filtered_feats_list


    #Select the 'n_features_batch' best feature candidates from each data source (univariate analysis)
    # based on the capacity to discriminate those individuals with observed performance against the ones
    # who have been denied. Here, higher default rates are expected for inferred/denied individuals when
    # in comparision to the other group.ds_details
    @module_logger
    def narrow_down_feat_candidates_univar(self, ds_group: DataSourcesGroup) -> List[str]:
        #Calculate total number of batches and start reading data from the DB
        num_total_batches = math.ceil((ds_group.current_ds.get_columns_count() - 
                                       ds_group.df_audience.get_columns_count())/self.book_cols_batch_size)
        
        #Trigger DB join pub + book
        ds_group.left_join_audience_tb(ds_group.current_ds, self.mob, self.approved_column, self.target_column)

        #Initialize list to hold intermediate/final results
        sorted_results = pd.DataFrame()
        analytical_vars = [self.approved_column, self.target_column]
        #Iterates through each batch of columns
        for index in tqdm(range(num_total_batches), leave=False):
            columns_to_read = ds_group.current_ds.columns[index*self.book_cols_batch_size: (index+1)*self.book_cols_batch_size]

            #READS DATA FROM THE DATABASE
            df = ds_group.get_data_batch(columns_to_read + analytical_vars, ds_group.current_ds.schema,'BASE_INFERENCIA_MLTOOLS_' + ds_group.current_ds.alias)

            #Filter analytical columns and add target and approved columns
            bk_features = [col for col in df.columns.to_list() if col not in ds_group.df_audience.columns + analytical_vars]

            ##INSTANTIATES A MODEL AND LOOPS THROUGH EVERY FEATURE FITTING, TRAINING AND EVALUATING
            results = self._univariate_evaluation(bk_features, ds_group.current_ds, df)

            ##PERSISTS THE READ DATAFRAME IN A PARQUET FILE
            candidate_features = self._persist_parquet_file(sorted_results, results, ds_group.current_ds.alias, df)

            #ATTACHES THE BEST FEATURES FOUND UNTIL THIS MOMENT TO THE DATA_SOURCE OBJ
            ds_group.current_ds.candidate_features = candidate_features
        
        #Creates a boolean series to identify "approved" individuals using the "approved_
        return ds_group.current_ds.candidate_features


    @module_logger
    def select_top_features_multivar(self, df_audience: DataSource, ds_candidate_features: List[str], ds_alias: str) -> List[str]:
        #_read_data_from_db
        df = self._read_data_from_pqfile(ds_alias, ds_candidate_features)

        #Filter analytical columns
        bk_features = [col for col in df.columns.to_list() if col not in df_audience.get_columns()]
        
        #Add target and approved columns
        df = df[bk_features + [self.approved_column, self.target_column]]

        #_selected_features_evaluation
        n_features = self._multivariate_evaluation(bk_features, df)

        return n_features
    

    @module_logger
    def get_best_feats_df(self, ds_group: DataSourcesGroup) -> pd.DataFrame: 
        join_cols = ds_group.audience_pk
        
        audience = ds_group.df_audience
        
        df_aud = self._read_data_from_pqfile(audience.alias, ds_group.top_ranked_feats + ds_group.audience_pk)  

        df_rfe = df_aud
        for feature_book in ds_group.data_sources:
            ds_group.current_ds = ds_group.data_sources[feature_book]
            ds = ds_group.current_ds

            df = self._read_data_from_pqfile(ds.alias, ds.top_rnkd_feats + ds_group.audience_pk)

            intersec_cols = [col for col in df_rfe if col in df and col not in join_cols]
            if len(intersec_cols) > 0:
                df.drop(columns=intersec_cols, inplace=True)

            df_rfe = pd.merge(df_rfe, df, how='left', on=join_cols)
            #df_rfe = df_rfe.join(df.set_index(ds_group.audience_pk))
        
        #setattr(ds_group, 'df_rfe', df_rfe.copy())

        return df_rfe


    #@module_logger
    def _get_prediction_results(self,
                                feature: str,
                                df_train: pd.DataFrame, 
                                df_test: pd.DataFrame, 
                                df_neg: pd.DataFrame,
                                features: List[str]) -> List[Union[float, str, List]]:
        
        # Generate x and y dataframes
        X_train = df_train[features]
        y_train = df_train[self.target_column]
        X_test = df_test[features] 
        y_test = df_test[self.target_column]
        X_test_neg = df_neg[features] 

        clf = LGBMClassifier(random_state=42, 
                             n_estimators=20, 
                             max_depth=10, 
                             num_leaves = 128)
          
        clf.fit(X_train, y_train)

        pred = pd.Series(clf.predict(X_test))
        pred_neg = pd.Series(clf.predict(X_test_neg))
        
        result = [
            feature,
            f1_score(y_test, pred), 
            y_test.mean(),
            pred.mean(),
            pred_neg.mean(), 
            pred.mean() - pred_neg.mean()
        ]
        
        return result


    @module_logger
    def recursive_feature_elimination(self, ds_group: DataSourcesGroup, df_rfe: pd.DataFrame) -> pd.DataFrame:
        # Creates a list to append each step of elimitation
        remove = []
        
        # Train, test split
        df_train, df_test, df_neg = self._prepare_training_datasets(df_rfe)

        # List of selected features
        features = [feat for feat in df_rfe.columns.to_list() if feat not in ds_group.df_audience.columns]

        # Get first results with all features
        # filter_df = partial(pd.DataFrame.filter, items=features)
        result = self._get_prediction_results('TODAS', df_train, df_test, df_neg, features)
        remove.append(result)

        # Loop through all features and eliminates the ones that makes denieds worst then approved 
        for j in tqdm(range(len(features)-1), desc='Executando a eliminação recursiva de features'):
            # List to track results if we eliminate a feature
            results = []

            # Loop through remaining features to calculate results
            logger.debug(f'   Evaluating {len(features)} features: {features}')
            for feature in features: # Initialize X with remaining features                
                # Calculate results
                # Loop through remaining features to calculate results
                feats = [x for x in features if x not in [feature]]
                result = self._get_prediction_results(feature, df_train, df_test, df_neg, feats)
                logger.debug(f'    _get_prediction_results returned: {result}')
                results.append(result)

            # Create a DF with results and sort by diff
            df_result = pd.DataFrame(results, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff' ])
            df_result = df_result.sort_values('diff')
                        
            # Append eliminated feature on this round
            remove.append(df_result.head(1).values.tolist()[0])
            features.remove(list(df_result.head(1)['feature'])[0])
            
        # Consolidate features by elimitation order
        result = pd.DataFrame(remove, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff'])
        
        self.plot_results(result)
        
        return result

    @module_logger
    def plot_results(self, result: pd.DataFrame):
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        
        x = result.index.to_list()[1:]
        print(x)
        ax1.plot(x, result.br_neg.to_list()[1:],label='BR Inferidos', color='r')  
        ax1.plot(x, result.br_inf.to_list()[1:],label='BR Contratos', color='g')        
        ax2.plot(x, result.f1_score.to_list()[1:],label='F1 Score', color='b')

        ax1.legend(loc="lower left")
        ax2.legend(loc="lower right")        
        
        fig.savefig('results_featsel.png',dpi=300)

        return result


    @module_logger
    def eval_br_reduction(self, 
                          prev_result: pd.DataFrame, 
                          features: List[str], 
                          ds_group: DataSourcesGroup, 
                          cut_threshold: int, 
                          max_br_reduction: float) -> List[str]:
        
        # Features before/after cut_point
        before_features = prev_result.iloc[1:cut_threshold+1].feature.to_list() 
        after_features = [f for f in features if f not in before_features]

        df_rfe = self.get_best_feats_df(ds_group)[features + [self.approved_column, self.target_column]]

        df_train, df_test, df_neg = self._prepare_training_datasets(df_rfe)
        
        # Get results with only last features 
        results = []
        results.append(self._get_prediction_results('APENAS ÚLTIMAS', df_train, df_test, df_neg, after_features))
        final_results = copy.deepcopy(results)   

        for feature in tqdm(before_features, desc='Avaliando a perfomance das features removidas'):
            # Calculate results
            result = self._get_prediction_results(feature, df_train, df_test, df_neg, after_features+[feature]) 
            results.append(result)
            
        # Create a DF with results and sort by br_neg
        df_result = pd.DataFrame(results, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff'])
        df_result = df_result.sort_values('br_neg', ascending=False)
        
        final_features = after_features

        for feature in tqdm(df_result.drop(0).feature.to_list(), desc='Devolvendo as features que não impactam os negados'): 
            # Calculate results
            #filter_df = partial(pd.DataFrame.filter, items=[final_features + [feature]])
            result = self._get_prediction_results(feature, df_train, df_test, df_neg, final_features+[feature])
            
            if result[4] > (1-max_br_reduction) * df_result.iloc[0].br_neg: 
                final_features.append(feature)
                final_results.append(result)

        self.final_features = final_features
        self.final_result = pd.DataFrame(final_results, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff'])
        
        return final_features 


    @module_logger
    def get_final_results(self, ds_group: DataSourcesGroup):
        df_rfe = self.get_best_feats_df(ds_group)
        
        df_rfe[self.approved_column] = df_rfe[self.approved_column].astype(str) 
        approved = df_rfe[self.approved_column].str.lstrip().str.rstrip() == str(self.approved_value)
        df_ap = df_rfe[approved]

        clf = LGBMClassifier(random_state=42, num_leaves = 40)
        clf.fit(df_ap[self.final_features], df_ap[self.target_column])
        threshold = self._get_threshold(df_ap[self.target_column], clf.predict_proba(df_ap[self.final_features])[:, 1]) # pyright: ignore
        
        df_rfe = self.get_best_feats_df(ds_group)
        df_rfe['INF'] = (clf.predict_proba(self.get_best_feats_df(ds_group)[self.final_features])[:, 1] > threshold) * 1 # type: ignore

        x = np.sort(df_rfe.PK_DATREF_XX.unique())
        print(x)
        print(df_rfe[approved].groupby('PK_DATREF_XX').INF.mean().sort_index().values)
        fig, ax = plt.subplots()
        ax.plot(x, df_rfe[approved].groupby('PK_DATREF_XX').INF.mean().sort_index().values, label = 'Contratos Inf', color='g')
        ax.plot(x, df_rfe[approved].groupby('PK_DATREF_XX').INF.mean().sort_index().values, label = 'Contratos Obs', color='b')
        ax.plot(x, df_rfe[approved].groupby('PK_DATREF_XX').INF.mean().sort_index().values, label = 'Negados Inf', color='r')
        fig.savefig('final_results.svg', dpi=300)
        
        
        

    @module_logger
    def _get_threshold(self, y_true, y_prob): 
        # initialize a list for score store
        values = []

        # iterate over 100 points and calculate scores
        for t in range(0, 99, 1):
            precision = precision_score(y_true, y_prob > t/100) 
            recall = recall_score(y_true, y_prob > t/100)
            
            values.append([t/100, precision, recall])
        
        values = np.array(values) # to array
        values = np.delete(values, np.where((values == 0))[0], axis=0) # removes precision and recall equal to zer
        # pick point of minimum distance between precision and recall
        cross_point = np.argmin(np.abs(values[:, 1] - values[:, 2]))
        
        return cross_point/100

    