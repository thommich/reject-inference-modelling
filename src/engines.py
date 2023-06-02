from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, EnumMeta
from typing import Dict, Any, List, Union, Type
from teradataml import create_context, remove_context
from teradataml.dataframe.dataframe import DataFrame, in_schema
from getpass import getpass
import pandas as pd
import teradatasql
from enum import Enum



class Engine():
    """

    """

    engines_config: Dict
    
    def __init__(self, engines_config: Dict[str,Dict[Any, Any]]):
        #self.engines_enum = self._init_engines_enum(engines_config)4
        #self.engines_enum = EnginesEnum()
        self.engines_config = engines_config
        
    #@classmethod
    def get_engine_instance(self, type: str) -> Type[Engine]:
        engine = EnginesEnum(type)
        return engine

    # @classmethod
    # #Binds the engines parameters to a different instance of Engine each
    # def _init_engines_enum(cls, engines_config: Dict) -> Type[EnginesEnum]:
    #     engines_dict = {}        

    #     for ec in engines_config:
    #         engines_dict[ec] = globals()[ec.capitalize() + 'Engine']
        
    #     EnginesEnum = Enum('EnginesEnum', engines_dict, module=__name__, qualname='src.EnginesEnum')
    #     #list(EnginesEnum)
    #     return EnginesEnum
    

    @abstractmethod
    def get_db_connection(self):
        ...


    @abstractmethod
    def close_db_connection(self):
        ...


    @abstractmethod
    def execute_query(self, query: str):
        ...

    @abstractmethod
    def read_data_from_db(self, query: str) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_table_shape(self, table_schema: str, table_name: str) -> tuple:
        ...


    @abstractmethod
    def get_table_columns(self, table_schema: str, table_name: str) -> List[str]:
        ...








class TeradataEngine(Engine):

    conn: teradatasql.TeradataConnection

    def __init__(self, engines_cfg: Dict[str,dict], type: str):
        self.__conn_vars = engines_cfg['conn_vars'][type]
        #super().__init__(engines_cfg)


    #Creates a new connection with the database and passes it to the function caller
    def get_db_connection(self) -> teradatasql.TeradataConnection:
        if self.conn:
            return self.conn

        try:
            self.conn = teradatasql.connect(
                host = self.__conn_vars['host'],
                username = self.__conn_vars['username'] if self.__conn_vars['username'] is not None else getpass("Teradata User: "), 
                password = self.__conn_vars['password'] if self.__conn_vars['password'] is not None else getpass("Teradata PWD: "),
                logmech = self.__conn_vars['logmech'] 
            )
        except ConnectionError as err:
            raise ConnectionError(err)
        
        return self.conn


    #Closes the connection with the database
    def close_db_connection(self) -> None:
        try:
            remove_context()
        except ConnectionError as err:
            raise ConnectionError(err)
    
    
    #Executes queries on Teradata
    def execute_query(self, query: str) -> None:
        self.get_db_connection().cursor().execute(query)
        return 

    
    #Returns a tuple containing a table's shape (num_rows, num_cols)
    def get_table_shape(self, table_schema: str, table_name: str) -> tuple:
        table_metadata = DataFrame.from_table(in_schema(table_schema, table_name))
        return table_metadata.shape
    
    
    #Returns a list containing a table's columns names
    def get_table_columns(self, table_schema: str, table_name: str) -> List[str]:
        table_metadata = DataFrame.from_table(in_schema(table_schema, table_name))
        return table_metadata.columns

    
    def read_data_from_db(self, query: str) -> pd.DataFrame: 
        fastexport_query = ' '.join(['{fn teradata_try_fastexport}', query])
        cursor = self.get_db_connection().cursor()
        
        data = cursor.execute(fastexport_query).fetchall()
        columns = [desc[0] for desc in cursor.description] #type: ignore

        return pd.DataFrame(data, columns = columns)
        



class HadoopEngine(Engine):
    pass



class EnginesEnum(Enum):
    TERADATA = TeradataEngine
    HADOOP = HadoopEngine

    def __getitem__(self, item: str) -> Union[Engine,None]:
        EnginesEnum.__members__.items()
        return self.__dict__.get(item)
