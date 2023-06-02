from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, EnumMeta
from typing import Dict, Tuple, List, Any, Union
from dataclasses import dataclass
from teradataml.context.context import create_context, remove_context
from teradataml import DataFrame, fastexport
from teradataml.dataframe.dataframe import in_schema
import yaml
import pandas as pd
import math
from engines import Engine
from jinja2 import Environment, FileSystemLoader, Template
import fastparquet as fp
import copy


class DataSourceGroup():
    """
        Esta classe representa um conjunto de fontes de dados de entrada que será iterado durante o processo de recursive feature elimination.
        
        Args:
        name (str): Nome do grupo conceitual. concepts (Dict[str, str]): Dicionário mapeando o conceito literal (que será usado para geração automática de nome de recurso) e o conceito real.
        ds_config: Dict[]
    """


    current_ds: DataSource
    df_rfe: pd.DataFrame

    def __init__(self, ds_config: Dict, engines_config: Dict):
        self.engine: Engine = self.__init_engines_enum(engines_config)
        self._df_audience, self.data_sources = self.__init_data_sources(ds_config)


    def __iter__(self):
        yield from self.data_sources


    #Binds the data source parameters to a different instance of DataSource each
    def __init_data_sources (self, ds_config: Dict) -> Tuple[DataSource,Dict[str,DataSource]]:
        ds_audience = self.__init_audience_df(ds_config['AUDIENCE_TABLE'])
        
        data_sources_dict = {ds_audience.alias: ds_audience.ds_details}
        

        for ds_info in ds_config:
            config_dict = ds_config[ds_info]
            ds_engine = config_dict['engine']

            new_ds = DataSource(config_dict, Engine.engines_enum[ds_engine]) #type: ignore

            data_sources_dict[new_ds.alias] = new_ds

        return ds_audience, data_sources_dict


    # Returns the entity containing data about the audience used for modelling
    def __init_audience_df(self, pub_ds_config: Dict) -> DataSource:
        aud_ds = DataSource(pub_ds_config, self.engine.get_engine_instance([pub_ds_config['ds_details']['engine']])) #type:ignore
        setattr(aud_ds, 'audience_pk', pub_ds_config['audience_pk'])

        parquet_file_path = '/temp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, aud_ds.alias.upper(), '.parquet'])
        fp.write(parquet_file, aud_ds.data_batch, compression='SNAPPY', append=True)

        return aud_ds


    #Initializes the possible engines Enumeration
    def __init_engines_enum(self, eng_params: dict) -> Engine:
        return Engine(eng_params)
    

    #Return the audience data
    def get_df_audience(self) -> DataSource:
        return copy.deepcopy(self._df_audience)       
    

    def get_audience_pk(self) -> List[str]:
        return getattr(self.get_df_audience(), 'audience_pk')
    
    def get_data_batch(self, columns_to_read: List[str]) -> pd.DataFrame:
        data_source: DataSource = getattr(self, 'current_ds')
        
        df = data_source.read_data_batch(columns_to_read, self.get_audience_pk())

        df['PK_DATREF_XX'] = pd.to_datetime(df['PK_DATREF_XX'])
        df['PK_DATVER_XX'] = pd.to_datetime(df['PK_DATVER_XX'])

        return df


    def left_join_audience_tb(self, data_source: DataSource, mob: int) -> None:
        return data_source.left_join_audience_tb(self.get_df_audience(), mob)

    # #Returns the engines enumeration
    # def get_engines_enum(self) -> EnginesEnum:
    #     return self.engines_enum


    #Returns the list with all the datasources
    def get_ds_group(self, ds_config: str) -> Dict[str,DataSource]:
        return self.data_sources


    #Returns a consolidated dataframe with the top variables selected from each source through the RFE algorithm
    def get_df_rfe(self) -> pd.DataFrame:
        return copy.deepcopy(self.df_rfe)








class DataSource():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        Args:
        schema (str): O nome do schema no qual esta tabela reside..
        pname (str): 0 nome fisico da tabela (nome real no banco de dados) Iname (str): O nome lógico da tabela (nome legível por humanos)
        alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """


    def __init__(self, ds_info: dict, ds_engine: Engine) -> None:
        self.alias = ds_info['alias']
        self.ds_details = ds_info['ds_details']
        self.engine_name = self.ds_details['engine']
        self.schema = self.ds_details['schema']
        self.physical_name = self.ds_details['physical_name']
        self.fields_to_remove = self.ds_details['fields_to_remove']
        #self._qry_override = ds_info['ds_details']['qry_override']
        self._engine = ds_engine
        self.shape = self._engine.get_table_shape(table_schema=self.schema, table_name=self.physical_name)
        self.columns = self._engine.get_table_columns(table_schema=self.schema, table_name=self.physical_name)
        self.data_batch = pd.DataFrame()
        self.candidate_features = []
        self.top_rnkd_feats = []


    def get_schema(self) -> str:
        return self.schema


    def get_physical_name(self) -> str:
        return self.physical_name


    def get_shape(self) -> tuple:
        return self.shape


    def get_columns(self) -> List[str]:
        return self.columns


    def has_data(self) -> bool:
        return True if hasattr(self, 'ds_data') else False


    def left_join_audience_tb(self, df_audience: DataSource, mob: int) -> None:
        query = f"""
            CREATE TABLE {self.schema}.BASE_INFERENCIA_MLTOOLS_{self.alias} AS (
                SELECT 
                    A.*
                FROM {df_audience.get_schema()}.{df_audience.get_physical_name()} AS B
                LEFT JOIN {self.schema}.{self.physical_name} AS A
                    ON A.PK_RIZNUMDOC_XX = B.RIZNUMDOC_XX
                    AND A.PK_DATREF_XX = ADD_MONTHS(B.PK_DATREF_XX, {mob})
                    AND A.PK_TPP_XX = B.PK_TPP_XX
            ) WITH DATA PRIMARY INDEX (PK_RIZNUMDOC_XX,PK_DATREF_XX)
        """
        self._engine.execute_query(query)


    #Read data from DBMS
    def read_data_batch(self, columns_to_read: List[str], audience_pk: List[str]) -> pd.DataFrame:         

        env = Environment(loader=FileSystemLoader('/templates'))
        query = env.get_template('read_batch_of_cols').render(columns_list=columns_to_read,
                                                              table_schema = self.schema,
                                                              table_name = self.physical_name,
                                                              primary_key = audience_pk)
        
        try:
            data_batch = self._engine.read_data_from_db(query)
        except Exception as err:
            raise err
        
        return data_batch