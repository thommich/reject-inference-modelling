from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, EnumMeta
from typing import Dict, Any, List, ClassVar, Union
from teradataml import create_context, remove_context
from getpass import getpass

class Engine():
    """

    """

    engines_enum: EnumMeta

    def __init__(self, engines_config: Dict[str,Dict[Any, Any]]):
        self.__engines_config = engines_config
        self.engines_enum = self.__set_engines_enum(engines_config)


    #Binds the engines parameters to a different instance of Engine each
    def __set_engines_enum(self, engines_config: Dict) -> Any:
        engines_dict = {}        

        for ec in engines_config:
            engines_dict[ec] = globals()[ec.capitalize() + 'Engine']
        
        return Enum('EnginesEnum', engines_dict)
    

    def get_engines_enum(self):
        return self.engines_enum
    
    @classmethod
    def get_engine_instance(cls, type: str) -> EnumMeta:
        return self.engines_enum.__getitem__(type).value(self.__engines_config) #type: ignore


    def get_db_connection(self):
        pass




#teradataml.DataFrame.from_table(in_schema())
class TeradataEngine(Engine):

    def __init__(self, engines_cfg: Dict[str,dict], type: str):
        self.__conn_vars = engines_cfg['conn_vars'][type]
        #super().__init__(engines_cfg)

    #Creates a new connection with the database and passes it to the function caller
    def get_db_connection(self) -> Any:
        if self.conn:
            return self.conn

        try:
            self.conn = create_context(
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
        self.get_db_connection().execute(query)


class HadoopEngine(Engine):
    #raise NotImplementedError("Engine has still to be implemented")
    pass


if __name__ == "__main__":
    engines_cfg = {'TERADATA': {'conn_vars': {'host': '10.225.1.30', 'username': None, 'password': None, 'logmech': 'LAPD'}}, 'HADOOP': {'conn_vars': {'host': None, 'database': None, 'user': None, 'password': None, 'datahub': None}}}
    #engine_cfg = {'conn_vars': {'host': '10.225.1.30', 'username': None, 'password': None, 'logmech': 'LAPD'}}
    te = Engine(engines_cfg)
    enum = te.get_engines_enum()
    print(enum.__getitem__('HADOOP').value)