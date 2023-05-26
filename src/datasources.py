from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, EnumMeta
from typing import Dict, Tuple, List, Any
from dataclasses import dataclass
from teradataml.context.context import create_context, remove_context
from teradataml import DataFrame, fastexport
from teradataml.dataframe.dataframe import in_schema
import yaml
import pandas as pd
import math
from engines import Engine


class DataSourceGroup():
    """
        Esta classe representa um conjunto de fontes de dados de entrada que será iterado durante o processo de recursive feature elimination.
        
        Args:
        name (str): Nome do grupo conceitual. concepts (Dict[str, str]): Dicionário mapeando o conceito literal (que será usado para geração automática de nome de recurso) e o conceito real.
        ds_config: Dict[]
    """

    data_sources: List[DataSource]
    df_public: DataSource
    engines_enum: EnumMeta


    def __init__(self, ds_config: Dict, pub_ds_config: Dict, engines_config: Dict):
        self.data_sources = self.__init_data_sources(ds_config)
        self.engines_enum = self.__init_engines(engines_config)
        self.df_public = self.__init_public_df(pub_ds_config)


    def __iter__(self):
        yield from self.data_sources


    #Binds the data source parameters to a different instance of DataSource each
    def __init_data_sources (self, ds_config: Dict) -> List [DataSource]:
        data_sources_lst = []

        for ds_info in ds_config:
            data_sources_lst.append(DataSource(ds_config[ds_info], self.engines_enum))

        return data_sources_lst


    # Returns the entity containing data about the public used for modelling
    def __init_public_df(self, pub_ds_config: Dict) -> DataSource:
        pub_ds_dict = {}
        
        pub_ds_dict['alias'] = 'PUB'
        pub_ds_dict['sources'] = [{'technology': pub_ds_config['technology'],
                                    'schema': pub_ds_config['schema'],
                                    'physical_name': pub_ds_config['physical_name'],
                                    'remove_fields': [],
                                    'override_qry': None}]
        
        
                                    
        return DataSource(pub_ds_dict, self.engines_enum)


    def __init_engines(self, eng_params: dict) -> EnumMeta:
        return Engine(eng_params).get_engines_enum()

    #Return the public data
    def get_df_public(self) -> DataSource:
        return self.df_public       
    

    def get_engines_enum(self) -> EnumMeta:
        return self.engines_enum


    #Executes a join between a given datasource and the public in analysis
    def get_data_filtered_public(self, current_ds: DataSource, max_batch_size: int, mob: int) -> pd.DataFrame:
        #Triggers a join operation between the public table and the datasource table
        current_ds.left_join_public_tb(self.df_public, mob)


        
        return pd.DataFrame()
    
    #Asks the current datasource for the next batch of data
    df_batch = current_ds.read_batch_of_data(max_batch_size)
        
        

    #Return list with all datasources
    def get_ds_group(self, ds_config: str) -> List[DataSource]:
        return self.data_sources


    #Returns a consolidated dataframe with the top variables selected from each source through the RFE algorithm
    def get_rfe_df(self, ds_config: str) -> DataSource:
        return DataSource({})








class DataSource():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        Args:
        schema (str): O nome do schema no qual esta tabela reside..
        pname (str): 0 nome fisico da tabela (nome real no banco de dados) Iname (str): O nome lógico da tabela (nome legível por humanos)
        alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    __alias: str
    __source: Dict[str , str]
    __engine: Engine
    ds_data: pd.DataFrame
    ds_columns: List[str]


    def __init__(self, ds_info: dict, engine_enum: EnumMeta) -> None:
        self.__alias = ds_info['alias']
        self.__technology = ds_info['source']['technology']
        self.__schema = ds_info['source']['schema']
        self.__physical_name = ds_info['source']['physical_name']
        self.__remove_fields = ds_info['source']['remove_fields']
        self.__qry_override = ds_info['source']['qry_override']
        self.__engine = engine_enum.__getitem__(self.__source['technology']).value 
        self.__ds_columns = self.ds_data.columns.to_list()


    def set_engine(self, engine_enum: EnumMeta) -> Engine:
         engine_enum.__getitem__(source['technology']).value


    #Read data from DBMS
    def read_batch_of_data(self, batch_size: int):
        self.ds_data = 
        
#df_impfeat = pd.read_parquet('./model_files/' + file_name, columns=['PK_RIZNUMDOC_XX'] + vars_list[i*vars_batch_n: (1+1)*vars_batch_n])
    #Read data from DBMS
    def read_from_src(self):
        connection = get_db_connection(self.engine)
        connection.execute()
        pass

    

    def left_join_public_tb(self, df_public: DataSource, mob: int) -> None:
        query = f"""
            CREATE TABLE MESB_T.BASE_INFERENCIA_MLTOOLS_{self.__alias} AS (
                SELECT 
                    A.*
                FROM {df_public.get_schema}.{df_public.get_physical_name()} AS B
                LEFT JOIN {self.__schema}.{self.__physical_name} AS A
                    ON A.PK_RIZNUMDOC_XX = B.RIZNUMDOC_XX
                    AND A.PK_DATREF_XX = ADD_MONTHS(B.PK_DATREF_XX, {mob})
                    AND A.PK_TPP_XX = B.PK_TPP_XX
            ) WITH DATA PRIMARY INDEX (PK_RIZNUMDOC_XX,PK_DATREF_XX)
        """
        self.__engine().execute_query(query)


    def get_total_batches(self, chunk_size: int):
    #    self.get_db_connection(self.engine, self.schema, self.database)
        table_meta = DataFrame.from_table(in_schema(self.schema, self.database))
        return math.ceil(len(table_meta.columns)/chunk_size)

    def get_schema(self):
        return self.__schema
    
    def get_physical_name(self):
        return self.__physical_name


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