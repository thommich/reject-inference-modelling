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


class DataSourceGroup():
    """
        Esta classe representa um conjunto de fontes de dados de entrada que será iterado durante o processo de recursive feature elimination.
        
        Args:
        name (str): Nome do grupo conceitual. concepts (Dict[str, str]): Dicionário mapeando o conceito literal (que será usado para geração automática de nome de recurso) e o conceito real.
        ds_config: Dict[]
    """

    data_sources: List[DataSource]
    df_audience: DataSource
    engines_enum: EnumMeta


    def __init__(self, ds_config: Dict, pub_ds_config: Dict, engines_config: Dict):
        self._engines_config = engines_config
        self._pub_ds_config = pub_ds_config
        self._ds_config = ds_config
        self.data_sources = self.__init_data_sources(ds_config)
        self.engines_enum = self.__init_engines_enum(engines_config)
        self.df_audience = self.__init_audience_df(pub_ds_config)


    def __iter__(self):
        yield from self.data_sources


    #Binds the data source parameters to a different instance of DataSource each
    def __init_data_sources (self, ds_config: Dict) -> List [DataSource]:
        data_sources_lst = []

        for ds_info in ds_config:
            config_dict = ds_config[ds_info]
            ds_technology = config_dict['technology']

            data_sources_lst.append(DataSource(config_dict, Engine(self._engines_config).get_engine_instance(ds_technology)))

        return data_sources_lst


    # Returns the entity containing data about the audience used for modelling
    def __init_audience_df(self, pub_ds_config: Dict) -> DataSource:
        pub_ds_dict = {}
        
        pub_ds_dict['alias'] = 'PUB'
        pub_ds_dict['sources'] = [{'technology': pub_ds_config['technology'],
                                    'schema': pub_ds_config['schema'],
                                    'physical_name': pub_ds_config['physical_name'],
                                    'remove_fields': [],
                                    'override_qry': None}]
                                    
        return DataSource(pub_ds_dict, self.get_engines_enum().get_engine_instance(pub_ds_dict['technology']))


    #Initializes the possible engines Enumeration
    def __init_engines_enum(self, eng_params: dict) -> EnumMeta:
        return Engine(eng_params).engines_enum
    

    #Return the audience data
    def get_df_audience(self) -> DataSource:
        return self.df_audience       
    

    #Returns the engines enumeration
    def get_engines_enum(self) -> EnumMeta:
        return self.engines_enum


    #Returns the list with all the datasources
    def get_ds_group(self, ds_config: str) -> List[DataSource]:
        return self.data_sources


    #Returns a consolidated dataframe with the top variables selected from each source through the RFE algorithm
    def get_rfe_df(self, ds_config: str) -> DataSource:
        return DataSource({}, Engine({'':{}}))








class DataSource():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        Args:
        schema (str): O nome do schema no qual esta tabela reside..
        pname (str): 0 nome fisico da tabela (nome real no banco de dados) Iname (str): O nome lógico da tabela (nome legível por humanos)
        alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    alias: str
    _technology: str
    _schema: str
    _physical_name: str
    _remove_fields: List[Union[str,None]]
    _qry_override: str
    _engine: Engine
    columns: List[str]
    data_batch: pd.DataFrame
    candidate_features: List[str]
    top_chosen_features: List[str]


    def __init__(self, ds_info: dict, ds_engine: Engine) -> None:
        self.alias = ds_info['alias']
        self._technology = ds_info['source']['technology']
        self._schema = ds_info['source']['schema']
        self._physical_name = ds_info['source']['physical_name']
        self._remove_fields = ds_info['source']['remove_fields']
        self._qry_override = ds_info['source']['qry_override']
        self._engine = ds_engine
        self.shape = self._engine.get_table_shape(self.get_schema(), self.get_physical_name())
        self._columns = self._engine.get_table_columns(self.get_schema(), self.get_physical_name())
        self.data_batch = pd.DataFrame()
        self.candidate_features = []
        self.top_chosen_features = []

    def get_schema(self):
        return self._schema


    def get_physical_name(self):
        return self._physical_name


    def get_shape(self) -> tuple:
        return self.shape


    def get_columns(self) -> List[str]:
        return self.columns


    def has_data(self) -> bool:
        return True if hasattr(self, 'ds_data') else False


    def left_join_audience_tb(self, df_audience: DataSource, mob: int) -> None:
        query = f"""
            CREATE TABLE {self._schema}.BASE_INFERENCIA_MLTOOLS_{self.alias} AS (
                SELECT 
                    A.*
                FROM {df_audience.get_schema()}.{df_audience.get_physical_name()} AS B
                LEFT JOIN {self._schema}.{self._physical_name} AS A
                    ON A.PK_RIZNUMDOC_XX = B.RIZNUMDOC_XX
                    AND A.PK_DATREF_XX = ADD_MONTHS(B.PK_DATREF_XX, {mob})
                    AND A.PK_TPP_XX = B.PK_TPP_XX
            ) WITH DATA PRIMARY INDEX (PK_RIZNUMDOC_XX,PK_DATREF_XX)
        """
        self._engine.execute_query(query)


    #Read data from DBMS
    def read_batch_of_data(self, index: int, batch_size: int) -> None:
        columns_to_read = self.columns[index*batch_size: (index+1)*batch_size]

        env = Environment(loader=FileSystemLoader('/templates'))
        query = env.get_template('read_batch_of_cols').render(columns_list=columns_to_read,
                                                              table_schema = self._schema,
                                                              table_name = self._physical_name,
                                                              primary_key = 'PK_RIZNUMDOC_XX')
        
        try:
            data_batch = self._engine.read_data_from_db(query)
        except Exception as err:
            raise err
        
        return data_batch


























class DataSourceEnum(Enum):
    """
        Este Enum lista todos os books de variáveis já incorporados ao código de eliminação recursiva de features. O algoritmo tem por objetivo 
        a seleção de features com alto poder de discriminação e que estejam de acordo com as premissas estabelecidas para o modelo de inferência 
        em desenvolvimento.    
    """

    BC = 'BACEN'
    BX = 'APONTAMENTOS'
    BVS = 'BOAVISTA'
    QUOD_IND = 'QUOD INDICADORES'
    QUOD_SCORE = 'QUOD_SCORE'

    @classmethod
    def from_teradata(cls): 
        return [cls.BC, cls.BX, cls.BVS]
    
    @classmethod
    def from_cdp(cls):
        return [cls.QUOD_IND, cls.QUOD_SCORE]