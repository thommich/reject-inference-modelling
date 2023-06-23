from __future__ import annotations

from tqdm import tqdm
from typing import Dict, Tuple, List, Any, Union, Callable, MutableSequence, Optional

import numpy as np
import pandas as pd
from datasources.dsgroup import DataSourcesGroup
from datasources.dsmodel import DataSource
import fastparquet as fp

from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score
from lightgbm import LGBMClassifier
from functools import partial
import copy
import math
import logging

# Create Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create stream handler
handler = logging.StreamHandler()
    
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s|%(name)s|%(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# Add handler to Logger
logger.addHandler(handler)


class RFE():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        
        Args:
            Iname (str): 0 nome lógico da tabela (nome legível por humanos)
            schema (str): O nome do schema no qual esta tabela reside.. 
            pname (str): O nome físico da tabela (nome real no banco de dados) 
            alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    def __init__(self, parameters: Dict) -> None:
        self.mob: int = parameters['mob']
        self.approved_column: str = parameters['approved_column']
        self.approved_value: Union[str,List,List[str]] = parameters['approved_value']
        self.target_column: str = parameters['target_column']
        self.remove_subpop: Union[bool, None, List, List[str]] = parameters['remove_subpop']
        self.book_cols_batch_size: int = parameters['book_cols_batch_size']
        self.n_features_1st_eval: int = parameters['n_features_1st_eval']
        self.n_features_final: int = parameters['n_features_final']        
        


    def _read_data_from_pqfile(self, ds_alias: str, ds_candidate_features: List[str], audience_cols: List[str]) -> Tuple[pd.DataFrame, List[str]]:
        
        #formats the name of the parquet file that will hold the persisted data
        parquet_file_path = '/temp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, ds_alias.upper(), '.parquet'])

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

        return df_train, df_test, df_neg
    

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
        ).sort_values('importance', ascending = False).iloc[:self.n_features_final]['features'].values.tolist()
    
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
    # in comparision to the other group.ds_details
    def narrow_down_feat_candidates_univar(self, ds_group: DataSourcesGroup) -> List[str]:
        ##INITIALIZE LOOP VARIABLES
        #Create variables for the main DataFrames to be passed around

        #Calculate total number of batches and start reading data from the DB
        num_total_batches = math.ceil((ds_group.current_ds.get_columns_count() - ds_group.df_audience.get_columns_count())/self.book_cols_batch_size)
        
        #Trigger DB join pub + book
        ds_group.left_join_audience_tb(ds_group.current_ds, self.mob)

        #Initialize list to hold intermediate/final results
        sorted_results = pd.DataFrame()
        #Iterates through each batch of columns
        for index in tqdm(range(num_total_batches), leave=False):
            columns_to_read = ds_group.current_ds.columns[index*self.book_cols_batch_size: (index+1)*self.book_cols_batch_size]

            #READS DATA FROM THE DATABASE
            df = ds_group.current_ds.read_data_batch(columns_to_read, ds_group.get_audience_pk())

            #Filter analytical columns and add target and approved columns
            analytical_vars = [col for col in df.columns.to_list() if col in df.columns and col not in ds_group.df_audience()]
            df = df[analytical_vars + [self.approved_column, self.target_column]]

            ##INSTANTIATES A MODEL AND LOOPS THROUGH EVERY FEATURE FITTING, TRAINING AND EVALUATING
            results = self._univariate_evaluation(analytical_vars, ds_group.get_current_ds(), df)

            ##PERSISTS THE READ DATAFRAME IN A PARQUET FILE
            candidate_features = self._persist_parquet_file(sorted_results, results, ds_group.get_current_ds().alias, df)

            #ATTACHES THE BEST FEATURES FOUND UNTIL THIS MOMENT TO THE DATA_SOURCE OBJ
            ds_group.get_current_ds().candidate_features = candidate_features
        
        return ds_group.get_current_ds().candidate_features


    def select_top_features_multivar(self, df_audience: DataSource, ds_candidate_features: List[str], ds_alias: str) -> List[str]:
        #_read_data_from_db
        df, analytical_vars = self._read_data_from_pqfile(ds_alias, ds_candidate_features, df_audience.get_columns())

        #_selected_features_evaluation
        n_features = self._multivariate_evaluation(analytical_vars, df)

        return n_features
    

    def get_best_feats_df(self, ds_group: DataSourcesGroup) -> pd.DataFrame: 
        
        audience = ds_group.df_audience()
        
        df_aud, _ = self._read_data_from_pqfile(audience.alias, ds_group.top_ranked_feats, audience.get_columns()) 

        df_rfe = df_aud
        for feature_book in ds_group.data_sources:
            ds_group.current_ds = ds_group.data_sources[feature_book]
            ds = ds_group.current_ds

            df, _ = self._read_data_from_pqfile(ds.alias, ds.top_rnkd_feats, ds_group.get_df_audience().get_columns())

            df_rfe = df_rfe.join(df.set_index(ds_group.get_audience_pk()))
        
        #setattr(ds_group, 'df_rfe', df_rfe.copy())

        return df_rfe


    def _get_prediction_results(self,
                                func: Callable, 
                                df_train: pd.DataFrame, 
                                df_test: pd.DataFrame, 
                                df_neg: pd.DataFrame) -> List[Union[float, str, List]]:
        
        # Generate x and y dataframes
        X_train = df_train.apply(func).apply(pd.to_numeric)
        y_train = df_train[self.target_column]
        X_test = df_test.apply(func).apply(pd.to_numeric) 
        y_test = df_test[self.target_column]
        X_test_neg = df_neg.apply(func).apply(pd.to_numeric) 

        # X_train = X_train
        # X_test = X_test.apply(pd.to_numeric)
        # X_test_neg = X_test_neg.apply(pd.to_numeric)

        clf = LGBMClassifier(random_state=42, 
                             n_estimators=20, 
                             max_depth=10, 
                             num_leaves = 128)
        
        clf.fit(X_train, y_train)

        pred = clf.predict(X_test) 
        pred_neg = clf.predict(X_test_neg)
        
        result = [  
            f1_score(y_test, pred), 
            y_test.mean(),
            pred.mean(),
            pred_neg.mean(), 
            pred.mean() - pred_neg.mean()
        ]
        
        return result


    def recursive_feature_elimination(self, ds_group: DataSourcesGroup, df_rfe: pd.DataFrame) -> pd.DataFrame:
        # Creates a list to append each step of elimitation
        remove = []
        
        # Train, test split
        df_train, df_test, df_neg = self._prepare_training_datasets(df_rfe)

        # List of selected features
        features = [feat for feat in df_rfe.columns.to_list() if feat not in ds_group.get_df_audience().get_columns()]

        # Get first results with all features
        filter_df = partial(pd.DataFrame.filter, items=features)
        result = self._get_prediction_results(filter_df, df_train, df_test, df_neg)
        remove.append(result)

        # Loop through all features and eliminates the ones that makes denieds worst then approved 
        for j in tqdm(range(len(features)-1), desc='Executando a eliminação recursiva de features'):
            # List to track results if we eliminate a feature
            results = []

            # Loop through remaining features to calculate results
            for feature in features: # Initialize X with remaining features                
                # Calculate results
            # Loop through remaining features to calculate results
                result = self._get_prediction_results(filter_df, df_train, df_test, df_neg)
                results.append(result)

            # Create a DF with results and sort by diff
            df_result = pd.DataFrame(results, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff' ])
            df_result = df_result.sort_values('diff')
                        
            # Append eliminated feature on this round
            remove.append(df_result.head(1).values.tolist()[0])
            features.remove(list(df_result.head (1)['feature'])[0])
            
        # Consolidate features by elimitation order
        result = pd.DataFrame(remove, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff'])
        
        return result


    def plot_results(self, result: pd.DataFrame):
        ax1 = result.br_neg.plot(label='BR Inferidos', color='r')
        ax1.set_ylabel('Bad Rate')
        ax2 = result.br_inf.plot(label='BR Contratos', color='g')

        # Create another axis and plot f1_score
        ax3 = ax1.twinx()
        ax3.set_ylabel('F1 Score')
        ax3.spines['right'].set_position(('axes', 1.0)) 
        result.f1_score.plot(ax=ax3, color='b', label='F1 Score')

        # Legend
        ax1.legend(loc="lower left");
        ax3.legend(loc="lower right");

        return result


    def eval_br_reduction(self, 
                          prev_result: pd.DataFrame, 
                          cut_threshold: int, 
                          max_br_reduction: float, 
                          features: List[str],
                          ds_group: DataSourcesGroup):
        
        # Features before/after cut_point
        before_features = prev_result.iloc[1:cut_threshold+1].feature.to_list() 
        after_features = [f for f in features if f not in before_features]

        df_rfe = self.get_best_feats_df(ds_group)[features]
        df_train, df_test, df_neg = self._prepare_training_datasets(df_rfe)
        
        # Get results with only last features 
        filter_df = partial(pd.DataFrame.filter, items=after_features)
        results = self._get_prediction_results(filter_df, df_train, df_test, df_neg)
        final_results = copy.deepcopy(results)   

        for feature in tqdm(before_features, desc='Avaliando a perfomance das features removidas'):
            # Calculate results
            filter_df = partial(pd.DataFrame.filter, items=[after_features + [feature]])
            result = self._get_prediction_results(filter_df, df_train, df_test, df_neg) 
            results.append(result)
            
        # Create a DF with results and sort by br_neg
        df_result = pd.DataFrame(results, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff'])
        df_result = df_result.sort_values('br_neg', ascending=False)
        
        final_features = after_features

        for feature in tqdm(df_result.drop(0).feature.to_list(), desc='Devolvendo as features que não impactam os negados'): 
            # Calculate results
            filter_df = partial(pd.DataFrame.filter, items=[final_features + [feature]])
            result = self._get_prediction_results(filter_df, df_train, df_test, df_neg)
            
            if result[4] > (1-max_br_reduction) * df_result.iloc[0].br_neg: 
                final_features.append(feature)
                final_results.append(result)

        self.final_features = final_features
        self.final_result = pd.DataFrame(final_results, columns=['feature', 'f1_score', 'br_real', 'br_inf', 'br_neg', 'diff'])
        
        return final_features 


    def get_final_results(self, ds_group: DataSourcesGroup):
        df_rfe = self.get_best_feats_df(ds_group)
        
        approved = df_rfe[self.approved_column].str.lstrip().str.rstrip() == str(self.approved_value)
        df_ap = df_rfe[approved]

        clf = LGBMClassifier(random_state=42, num_leaves = 40)
        clf.fit(df_ap[self.final_features], df_ap[self.target_column])
        threshold = self._get_threshold(df_ap[self.target_column], clf.predict_proba(df_ap[self.final_features])[:, 1])
        
        df_rfe = self.get_best_feats_df(ds_group)
        df_rfe['INF'] = (clf.predict_proba(self.get_best_feats_df(ds_group)[self.final_features])[:, 1] > threshold) * 1
        data = pd.DataFrame({
                'Inf Contratos': df_rfe[approved].groupby('PK_DATREF_XX').INF.mean(),
                'Contratos': df_rfe[approved].groupby('PK_DATREF_XX')[self.target_column].mean(), 
                'Inf Inferidos': df_rfe[approved].groupby('PK_DATREF_XX').INF.mean()
        })
        data.plot()


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

    