import yaml
import os.path
import gc, math, logging


from rfe import RFE
from engines import Engine
from datasources import DataSourceGroup, DataSource

import pandas as pd
from time import time
from getpass import getpass

from jinja2 import Environment, FileSystemLoader
from typing import Tuple, Dict
from enum import EnumMeta
from schema import And, Or, Optional, SchemaError, Schema
from typing import Any

#from tqdm import tqdm
#from sklearn.model_selection import train_test_split
#from sklearn.metrics import f1_score, precision_score, recall_score, classification_report, confusion_matrix
#from lightgbm import LGBMClassifier
#import bifrost
#from bifrost import Hadoop
#pd.set_option('display.max_rows', None) 
#pd.set_option('display.max_columns', None)
#import pyarrow as pa
#import seaborn as sns
#import fastparquet as fp
#import pyarrow.parquet as pq
#import matplotlib.pyplot as plt

# Create Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create stream handler
handler = logging.StreamHandler() 
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s|%(name)s|%(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

#Add handler to Logger
logger.addHandler(handler)



class InferenceModel():
    """
    
    """

    __rfe_agent: RFE
    __engines_enum: EnumMeta
    __data_sources_group: DataSourceGroup


    def __init__(self, cfg_file_path: str):
        params_rfe, engines_params, data_srcs_params = self.__load_config(cfg_file_path)        
        self.__rfe_agent = RFE(params_rfe)    
        self.__data_sources_group = DataSourceGroup(data_srcs_params, {'physical_name': params_rfe['public_tbl'], 
                                                                    'technology': params_rfe['public_tbl_eng'],
                                                                    'schema': params_rfe['public_tbl_schm'],
                                                                    'public_tbl_db': params_rfe['public_tbl_db']}, engines_params)
        self.__engines_enum = self.__data_sources_group.get_engines_enum()


    #Reads YAML config file
    def __load_config(self, cfg_file_name: str) -> Tuple[Dict[Any, Any], Dict[Any, Any], Dict[Any, Any]]:
        """
            Loads configuration file containing multiple module parameters.

            Returns:
                Dict(str, str]: Dictionary with the literal parameters.
        """
        
        with open(cfg_file_name) as file:
            yaml_config= yaml.load(file, Loader=yaml.FullLoader) 
            if "parameters" not in yaml_config.keys():
                raise ValueError("The node 'parameters' is required in the config file")

            if "engines" not in yaml_config.keys(): 
                raise ValueError("The node 'engines' is required in the config file")

            if "datasources" not in yaml_config.keys():
                raise ValueError("The node 'datasources' is required in the config file")

            schema = Schema(
                {
                "parameters": {
                    "description": str, 
                    "public_tbl": str,
                    "public_tbl_eng": str,
                    "public_tbl_schm": str,
                    "public_tbl_db": str,
                    "mob": int,
                    "approved_column": str, 
                    "approved_value": Or(str, int),
                    "target_column": str,
                    "remove_bc": bool,
                    "n_features": int
                },
                "engines": {
                    str: {
                        "conn_vars": dict
                    }
                }, 
                "datasources": {
                    str: {
                        'alias': str,
                        'source': {
                            'technology': str, 
                            'schema': str, 
                            'physical_name': str, 
                            Optional('remove_fields'): Or(None, [str])
                        }
                    }
                }
                #Optional ("variaveis"): And(dict),
            })
            

            try:
                schema.validate(yaml_config)

                parameters = yaml_config.get("parameters") 
                engines_params = yaml_config.get("engines") 
                data_srcs_params = yaml_config.get("datasources") 
            except SchemaError as e: 
                raise ValueError(f"The config file is invalid! \nMessage: {e.args[0]}")
                
        return parameters, engines_params, data_srcs_params

    #Validate config file
    def __validate_config(self):
        pass

    #Recursive feature elimination implementation
    def rfe(self):        
        #Uses the RFE object instantiated during the class's initialization
        rfe_obj = self.__rfe_agent

        #Get df_public from DB and store in memory
        df_public = self.__get_public_df()

        #Get df_public index to use later
        public_idx = df_public.ds_data['PK_RIZNUMDOC_XX'].to_list()

        #Loops through each data source specified on the config file        
        for current_ds in self.__data_sources_group:
            #Trigger DB join pub + book
            joined_df = self.__data_sources_group.get_data_filtered_public(current_ds, rfe_obj.max_n_feats_join, rfe_obj.mob)


            #Identify the 'n_candidate_features' best var candidates from each data source (univariate analysis)
            rfe_obj.narrow_down_candidates_univar(df_public, data_sources_group)

            #Identify the 'n_final_features' best var candidates from each data source (multivariate analysis)
            rfe_obj.choose_top_features_multivar() 
            
            #Consolidates all the chosen variables into a single dataframe
            rfe_obj.get_best_feats_df()

        #Runs the RFE() algorithm against the best set of features identified in previous steps
        rfe_obj.get_rfe_results()

        pass

 

    #Reevaluates features discardaded during the previous analysis step
    def eval_data_sources(self): 
        pass

    def __get_public_df(self) -> DataSource: 
        return self.__data_sources_group.get_df_public()
    
    #Retrocompatibility
    def get_features (self):
        return self.eval_data_sources()
    
    
    def get_results(self): 
        pass