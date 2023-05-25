import yaml
from pydantic import BaseModel
from abc import ABC, abstractmethod
from enum import Enum
from Type import List
from typing import Dict, Tuple, List, Any
from dataclasses import dataclass
from teradataml.context.context import create_context, remove_context
from teradataml import DataFrame
import math


class DataSourceGroup():
    """
        Esta classe representa um conjunto de fontes de dados de entrada que será iterado durante o processo de recursive feature elimination.
        
        Args:
        name (str): Nome do grupo conceitual. concepts (Dict[str, str]): Dicionário mapeando o conceito literal (que será usado para geração automática de nome de recurso) e o conceito real.
        ds_config: Dict[]
    """

    def __init__(self, ds_config: Dict):
        #self.__data_srcs_params = ds_config
        self.__data_sources = __set_data_sources(ds_config)


    #Binds the data source parameters to a different instance of DataSource each
    def __set_data_sources (self) -> List [DataSource]:
        data_sources = []

        for ds in ds_config:
            data_sources.append(DataSource(ds.schema, ds.database, ds.technology, ds.parquet_file_name))
        
        return data_sources

    
    #Return list with all datasources
    def get_ds_group(self, ds_config: str) -> List[DataSource]:
        return self.data_sources

    
    #Returns the entity containing data about the public used for modelling
    def get_public_df(self, ds_config: str) -> DataSource:
        pass

    #Returns a consolidated dataframe with the top variables selected from each source through the RFE algorithm
    def get_rfe_df(self, ds_config: str) -> DataSource:
        pass



@dataclass
class DataSource():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        Args:
        schema (str): O nome do schema no qual esta tabela reside..
        pname (str): 0 nome fisico da tabela (nome real no banco de dados) Iname (str): O nome lógico da tabela (nome legível por humanos)
        alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    schema: str
    database: str
    engine: str
    pq_file_name: str
    all_features: List[str]

    def __init__()

    #Read data from DBMS
    def read_batch_of_data(self, batch_size: int):
        pass

    #Read data from DBMS
    def read_from_src(self):
        connection = get_db_connection(self.engine)
        connection.execute()
        pass

    def get_db_connection(self, engine: str, schema: str, database: str):
        try:
            con = create_context(
                host = "",
                username = "",
                password = "",
                logmech = "" 
            )
        except:
        
        return con

    def merge_with_public_df(self, public_df):
        pass


    def get_total_batches(self, chunk_size: int):
    #    self.get_db_connection(self.engine, self.schema, self.database)
        table_meta = DataFrame.from_table(in_schema(self.schema, self.database))
        return math.ceil(len(table_meta.columns)/chunk_size)



class DataSourceEnum(Enum):
    """
        Este Enum lista todos os books de variáveis já incorporados ao código de eliminação recursiva de features. O algoritmo tem por objetivo 
        a seleção de features com alto poder de discriminação e que estejam de acordo com as premissas estabelecidas para o modelo de inferência 
        em desenvolvimento.    
    """

    BC = 'BACEN'
    BX = APONTAMENTOS'
    BVS = BOAVISTA'
    QUOD IND = 'QUOD INDICADORES'
    QUOD SCORE = 'QUOD_SCORE'

    @classmethod
    def from_teradata(cls): 
        return [cls.BC, cls.BX, cls.BVS]
    
    @classmethod
    def from_cdp(cls):
        return [cls.QUOD IND, cls.QUOD_SCORE]