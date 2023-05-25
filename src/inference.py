import yaml
import os.path
import gc, math, logging

#import numpy as np
import pandas as pd
#import pyarrow as pa
#import seaborn as sns
#import fastparquet as fp
#import pyarrow.parquet as pq
#import matplotlib.pyplot as plt

from rfe import RFE
from time import time
#from tqdm import tqdm
from getpass import getpass
#from lightgbm import LGBMClassifier
from jinja2 import Environment, FileSystemLoader
from typing import Tuple, Dict
#from sklearn.model_selection import train_test_split
#from teradataml import DataFrame, fastexport, fastload, in_schema, create_context, remove_context
#from sklearn.metrics import f1_score, precision_score, recall_score, classification_report, confusion_matrix
from schema import And, Or, Optional, SchemaError, Schema

#import bifrost
#from bifrost import Hadoop
#pd.set_option('display.max_rows', None) 
#pd.set_option('display.max_columns', None)

# Create Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create stream handler
handler = logging.StreamHandler() 
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s|%(name)s|%(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

#Add handler to Logger
logger.addHandler(handler)

#Open Teradata connection
#if input('Ambiente: \n 1 - Garagem In 2 - SageMaker \n') == '1':
# con=create_context(
# host="10.225.1.30",
# username= 'thommic', #username=input('Usuário Teradata:'),
# password='Sofi2606', #password=getpass('Senha:'),
# Logmech='LDAP'




class InferenceModel():
    """
    
    """

    def __init__(self, cfg_file_path: str): 
        self.__cfg_file = cfg_file_path         
        self.__rfe_agent = RFE(*self.__load_config())    


    #Reads YAML config file
    def __load_config(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
            Loads configuration file containing multiple module parameters.

            Returns:
                Dict(str, str]: Dictionary with the literal parameters.
        """
        
        file_name = self.__cfg_file
        with open(file_name) as file:
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
                        "conn_vars": [dict]
                    }
                }, 
                "datasources": {
                    str: {
                        'alias': str,
                        'sources': [{
                            'technology': str, 
                            'schema': str, 
                            'physical_name': str, 
                            Optional('remove_fields'): Or(None, [str]),
                            Optional('qry_override'): Or(None, str) 
                        }]
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
        #Uses the RFE object instantiated during initialization of the class
        rfe_obj = self.__rfe_agent

        #Identify the 'n_candidate_features' best var candidates from each data source (univariate analysis)
        rfe_obj.narrow_down_candidates_univar()

        #Identify the 'n_final_features' best var candidates from each data source (multivariate analysis)
        rfe_obj.choose_top_features_multivar() 
        
        #Consolidates all the chosen variables into a single dataframe
        rfe_obj.get_df_rfe()

        self.__rfe = rfe_obj
        pass


    #Reevaluates features discardaded during the previous analysis step
    def eval_data_sources(self): 
        pass

    #Retrocompatibility
    def get_features (self):
        return self.eval_data_sources()
    
    
    def get_results(self): 
        pass