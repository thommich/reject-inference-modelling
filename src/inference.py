import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os.path
from lightgbm import LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, classification_report, confusion_matrix
from time import time
import logging
import gc from tqdm import tqdm
#from tqdm.auto import tqdm
from jinja2 import Environment, FileSystemLoader
import math
from getpass import getpass
#from teradataml.dataframe.dataframe import DataFrame
from teradataml import DataFrame, fastexport
from teradataml.dataframe.copy_to import copy_to_sql
from teradataml.context.context import create_context, remove_context, get_context
from teradataml.table_operators.Script import Script 
from sqlalchemy.sql.expression import extract
from teradatasqlalchemy.types import *
from teradataml.dataframe.fastload import fastload
from teradataml.dataframe.dataframe import in_schema

import pyarrow as pa
import pyarrow.parquet as pq
import fastparquet as fp

import bifrost
from bifrost import Hadoop

pd.set_option('display.max_rows', None) 
pd.set_option('display.max_columns', None)

# Create Logger
logger logging.getLogger(_name_
logger.setLevel(logging.INFO)

# Create stream handler
handler logging.StreamHandler() handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s % (name)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

#Add handler to Logger
Logger.addHandler(handler)

#Open Teradata connection
#if input('Ambiente: \n 1 - Garagem In 2 - SageMaker \n') == '1':
# con=create_context(
host="10.225.1.30",
username= 'thommic', #username=input('Usuário Teradata:'),
password='Sofi2606', #password=getpass('Senha:'),
Logmech='LDAP'


from .rfe import RFE

class InferenceModel:

    def __init_(self, cfg_file_path: str): 
        self.__cfg_file = cfg_file_path 
        
#        parameters, technologies_params, data_srcs_params = self.__load_config()
#        self.__rfe_agent = RFE(parameters, technologies_params, data_srcs_params) 
        
        self.__rfe_agent = RFE(self.__load_config())    


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

            if "technologies" not in yaml_config.keys(): 
                raise ValueError("The node 'technologies' is required in the config file")

            if "sources" not in yaml_config.keys(): 
                raise ValueError("The node 'sources' is required in the config file")

            schema = Schema(
                {
                    "parameters": And({
                        "description": And(str), "public_tbl": And(str),
                        "mob": And(int),
                        "approved_column": And(str), "approved_value": And (Or(str, int)),
                        "target_column": And([str]),
                        "remove_bc": And([bool]),
                        "n_features": And([str])
                    }),
                    "technologies": And({
                        str: And(dict)
                    }), 
                    "datasources": And({
                        str: And({
                            'alias': And(str),
                            'sources': And([{
                                'technology': And(str), 
                                'schema': And(str), 
                                'physical_name': And(str), 
                                Optional('remove_fields'): And([str]), 
                                Optional('qry_override'): And(str)
                            }])
                        })
                    })
                    #Optional ("variaveis"): And(dict),
                }
            )

            try:
                schema.validate(yaml_config)

                parameters = yaml_config.get("parameters") 
                technologies_params = yaml_config.get("technologies") 
                data_srcs_params = yaml_config.get("sources") 
            except SchemaError as e: 
                raise ValueError(f"The config file is invalid! \nMessage: {e.args[0]}")
                
        return parameters, technologies_params, data_srcs_params                                


    #Recursive feature elimination implementation
    def rfe(self):
        #Initializes RFE object as an instance attribute
        rfe_obj = RFE(self.parameters, self.__data_srcs_params)
        
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