import yaml
import logging


from rfe import RFE
from datasources.dsgroup import DataSourcesGroup

import pandas as pd
from time import time
from getpass import getpass

from jinja2 import Environment, FileSystemLoader
from typing import Tuple, Dict
from schema import And, Or, Optional, SchemaError, Schema
from typing import Any

# from tqdm import tqdm
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import f1_score, precision_score, recall_score, classification_report, confusion_matrix
# from lightgbm import LGBMClassifier
# import bifrost
# from bifrost import Hadoop
# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# import pyarrow as pa
# import seaborn as sns
# import fastparquet as fp
# import pyarrow.parquet as pq
# import matplotlib.pyplot as plt

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


class InferenceModel():
    """

    """

    _rfe_agent: RFE
    _data_sources_group: DataSourcesGroup

    #SHOULD GO IN THE CONFIG
    cut_threshold: int
    max_br_reduction: float

    def __init__(self, cfg_file_path: str):
        params_rfe, engines_params, data_srcs_params = self._load_config(cfg_file_path)
        self._rfe_agent = RFE(params_rfe)
        self._data_sources_group = DataSourcesGroup(data_srcs_params, engines_params)
        
        
    # Reads YAML config file
    def _load_config(self, cfg_file_name: str) -> Tuple[Dict[Any, Any], Dict[Any, Any], Dict[Any, Any]]:
        """
            Loads configuration file containing multiple module parameters.

            Returns:
                Dict(str, str]: Dictionary with the literal parameters.
        """        
        with open(cfg_file_name) as file:
            yaml_config = yaml.load(file, Loader=yaml.FullLoader)
            if "parameters" not in yaml_config.keys():
                raise ValueError(
                    "The node 'parameters' is required in the config file")

            if "engines" not in yaml_config.keys():
                raise ValueError(
                    "The node 'engines' is required in the config file")

            if "datasources" not in yaml_config.keys():
                raise ValueError(
                    "The node 'datasources' is required in the config file")

            schema = Schema(
                {
                    "parameters": {
                        "description": str,
                        "mob": int,
                        "approved_column": str,
                        "approved_value": Or(str, int),
                        "target_column": str,
                        "remove_subpop": Or(bool,None,[],[str]),
                        "n_features_1st_eval": int,
                        "n_features_final": int,                        
                        "book_cols_batch_size": int
                    },
                    "engines": {
                        str: {
                            "conn_vars": dict
                        }
                    },
                    "datasources": {
                        'AUDIENCE_TABLE': {
                            'audience_pk': Or([str], str),
                            'alias': str,
                            'ds_details': {
                                'engine': str,
                                'schema': str,
                                'physical_name': str,
                                Optional('fields_to_remove'): Or(None, [str])
                            }
                        },
                        str: {
                            'alias': str,
                            'ds_details': {
                                'engine': str,
                                'schema': str,
                                'physical_name': str,
                                Optional('fields_to_remove'): Or(None, [str])
                            }
                        }
                    }
                    # Optional ("variaveis"): And(dict),
                })

            try:
                schema.validate(yaml_config)

                parameters = yaml_config.get("parameters")
                engines_params = yaml_config.get("engines")
                data_srcs_params = yaml_config.get("datasources")
            except SchemaError as e:
                raise ValueError(
                    f"The config file is invalid! \nMessage: {e.args[0]}")

        return parameters, engines_params, data_srcs_params

    # Validate config file
    def _validate_config(self):
        pass

    # Recursive feature elimination implementation
    def rfe(self):
        # Uses the RFE object instantiated during the class's initialization
        rfe_obj = self._rfe_agent
        ds_group = self._data_sources_group

        data_sources = ds_group.data_sources

        # Get df_audience from DB and store in memory
        df_audience = ds_group.df_audience

        # Loops through each data source specified on the config file
        for features_book in data_sources:
            # Associates current data_source to a property of data_sources_group
            setattr(ds_group, 'current_ds', features_book)
            current_ds = data_sources[features_book]

            # Identify the 'n_candidate_features' best var candidates from each data source (univariate analysis)
            candidate_features = rfe_obj.narrow_down_feat_candidates_univar(ds_group)

            # Identify the 'n_final_features' best var candidates from each data source (multivariate analysis)
            top_features = rfe_obj.select_top_features_multivar(df_audience, candidate_features, current_ds.alias)

            data_sources[features_book].top_rnkd_feats = top_features


        # Consolidates all the chosen variables into a single dataframe
        df_rfe = rfe_obj.get_best_feats_df(ds_group)

        # Runs the RFE algorithm against the best set of features identified in previous steps
        self.result = rfe_obj.recursive_feature_elimination(ds_group, df_rfe)

        return


    # Reevaluates features discardaded during the previous analysis step
    def double_check_eliminated(self):
        
        ds_group = self._data_sources_group
        rfe_obj = self._rfe_agent

        best_feats = [ds.top_rnkd_feats for ds in ds_group.data_sources]

        df_rfe = rfe_obj.get_best_feats_df(ds_group.df_audience)

        features = [feat for feat in df_rfe.columns.to_list() if feat not in ds_group.df_audience.get_columns()]
        
        self.final_features = rfe_obj.eval_br_reduction(self.result, self.cut_threshold, self.max_br_reduction, features, ds_group)

        return 


    def final_results(self):
        ds_group = self._data_sources_group
        rfe_obj = self._rfe_agent

        rfe_obj.get_final_results(ds_group)

        
    # Retrocompatibility
    def get_features(self):
        return self.double_check_eliminated()
    
    def get_results(self):
        return self.final_results()