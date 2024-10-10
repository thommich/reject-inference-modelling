from __future__ import annotations
from typing import Dict, List, Any, Tuple, Type
from teradataml import create_context, remove_context
from teradataml.dataframe.dataframe import DataFrame, in_schema
from getpass import getpass
import pandas as pd
import teradatasql
from engines.engines import EnginesInterface
from log_utils import setup_logging, log_func

logger = setup_logging(name=__name__)
module_logger = log_func(__name__)


class TeradataEngine(EnginesInterface, name='TERADATA'): 

    @module_logger
    def __init__(self, conn_vars: Dict[str,str]):
        self.conn_vars = conn_vars
        self._conn = None

    @property
    def name(cls):
        return cls.name
    
    #@classmethod
    @property
    def conn(self):
        return self._conn

    #Creates a new connection with the database and passes it to the function caller
    def get_db_connection(self) -> None:#teradatasql.TeradataConnection:
        
        # try:
        #     self._conn = teradatasql.connect(
        #         host = self.conn_vars['host'],
        #         user = self.conn_vars['username'] if self.conn_vars['username'] is not None else getpass("Teradata User: "), 
        #         password = self.conn_vars['password'] if self.conn_vars['password'] is not None else getpass("Teradata PWD: "),
        #         logmech = self.conn_vars['logmech'] 
        #     )
        # except ConnectionError as err:
        #     raise ConnectionError(err)
        
        # return self._conn
        pass 


    #Closes the connection with the database
    def close_db_connection(self) -> None:
        # try:
        #     self.conn.close()
        # except ConnectionError as err:
        #     raise ConnectionError(err)
        pass
    
    #Executes queries on Teradata
    def execute_query(self, query: str) -> None:
        #self.conn.cursor().execute(query)
        return 

    
    #Returns a tuple containing a table's shape (num_rows, num_cols)
    def get_table_shape(self, table_schema: str, table_name: str) -> Tuple[int,int]:
        # cursor = self.conn.cursor()
        
        # rows_query = f"SELECT COUNT(*) FROM {table_schema}.{table_name}"
        # rows_num = cursor.execute(rows_query).fetchall()
        
        rows_num = (50000, 120)        
        columns = self.get_table_columns(table_schema, table_name)
                
        return (rows_num[0], len(columns))
    
    
    #Returns a list containing a table's columns names
    def get_table_columns(self, table_schema: str, table_name: str) -> List[str]:
        # cursor = self.conn.cursor()
        
        # columns_query = f"SELECT * FROM {table_schema}.{table_name} SAMPLE 1"
        
        # cursor.execute(columns_query)
        # columns = [desc[0] for desc in cursor.description]
        
        columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', table_schema, table_name]
        
        return columns

    
    def read_data_from_db(self, query: str) -> pd.DataFrame: 
        # cursor = self.conn.cursor()
        
        # fastexport_query = ' '.join(['{fn teradata_try_fastexport}', query])
        
        # data = cursor.execute(fastexport_query).fetchall()
        # columns = [desc[0] for desc in cursor.description] #type: ignore

        columns = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', query]
        data = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7, 'i': 8}
        
        return pd.DataFrame(data, columns = columns)
    
    def join_aud_ds_query(self, **kwargs) -> None:        
        aud_ds_physical_name = kwargs.get('audience_tb')
        ds_schema = kwargs.get('ds_schema')
        ds_alias = kwargs.get('ds_alias')
        ds_physical_name = kwargs.get('ds_physical_name')
        mob = kwargs.get('mob')
        
        query = f"""
            CREATE TABLE {ds_schema}.BASE_INFERENCIA_MLTOOLS_{ds_alias} AS (
                SELECT 
                    B.*
                FROM {ds_schema}.{aud_ds_physical_name} AS A
                LEFT JOIN {ds_schema}.{ds_physical_name} AS B
                    ON A.PK_RIZNUMDOC_XX = B.RIZNUMDOC_XX
                    AND A.PK_DATREF_XX = ADD_MONTHS(B.PK_DATREF_XX, {mob})
                    AND A.PK_TPP_XX = B.PK_TPP_XX
            ) WITH DATA PRIMARY INDEX (PK_RIZNUMDOC_XX,PK_DATREF_XX)
        """
        
        return self.execute_query(query)
        

    def read_data_batch(self, **kwargs) -> None:
        pass    
