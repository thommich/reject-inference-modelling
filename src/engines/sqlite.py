from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import pandas as pd
#from engines.engines import EnginesInterface
from engines.engines import EnginesInterface#, Engines
import sqlite3
from jinja2 import Environment, FileSystemLoader
from log_utils import setup_logging, log_func

logger = setup_logging(name=__name__)
module_logger = log_func(__name__)


class SQLiteEngine(EnginesInterface, name="SQLITE"):
    
    @module_logger
    def __init__(self):
        self.conn_vars = super().engines_cfg[self.name]['conn_vars']
        self._conn = None

    @property
    def name(cls):
        return cls.name

    #@classmethod
    #@module_logger
    @property
    def conn(self):
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(self.conn_vars.get('db_name'))
                self._conn.row_factory = sqlite3.Row
            except ConnectionError:
                raise ConnectionError(f"Failed to retrieve a connection for the {self.name} DBMS!")
            
        return self._conn

    
    #Creates a new connection with the database and passes it to the function caller
    #@module_logger
    def get_db_connection(self) -> Optional[sqlite3.Connection]:#teradatasql.TeradataConnection:
        return self.conn


    #Closes the connection with the database
    #@module_logger
    def close_db_connection(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        else:
            raise sqlite3.ProgrammingError("Trying to operate on a closed or inexistent Connection!")

    
    #Queries the databse
    #@module_logger
    def execute_query(self, query: str) -> None:
        try:
            #print(query)
            self.conn.execute(query)
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as err:
            if isinstance(err, sqlite3.OperationalError):
                raise sqlite3.OperationalError("The Database is unable to execute the request at the moment")

    
    #Returns a tuple containing a table's shape (num_rows, num_cols)
    #@module_logger
    def get_table_shape(self, table_schema: str, table_name: str) -> Tuple[int,int]:
        rows_query = f"SELECT COUNT(*) FROM {table_name}"
        rows_num = self.conn.execute(rows_query).fetchone()
             
        columns = self.get_table_columns(table_schema, table_name)
                
        return (rows_num[0], len(columns))
    
    
    #Returns a list containing a table's columns names
    @module_logger
    def get_table_columns(self, table_schema: str, table_name: str) -> List[str]:
        
        cursor = self.conn.cursor()
        
        columns_query = f"SELECT * FROM {table_name} LIMIT 1"
        
        r = cursor.execute(columns_query).fetchone()
        
        return list(r.keys())

    
    @module_logger
    def read_data_from_db(self, query: str) -> pd.DataFrame: 
        # cursor = self.conn.cursor()
        
        # fastexport_query = ' '.join(['{fn teradata_try_fastexport}', query])
        
        # data = cursor.execute(fastexport_query).fetchall()
        
        cursor = self.conn.cursor()
        
        data = cursor.execute(query).fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        return pd.DataFrame(data, columns = columns)
    
    
    @module_logger
    def join_aud_ds_query(self, **kwargs) -> str:
        aud_ds_physical_name = kwargs.get('aud_ds_physical_name')
        audience_pk  = kwargs.get('audience_pk')
        ds_alias = kwargs.get('ds_alias')
        ds_physical_name = kwargs.get('ds_physical_name')
        bk_features = kwargs.get('bk_features')
        approved_column = kwargs.get('approved_column')
        target_column = kwargs.get('target_column')
        mob = kwargs.get('mob')        
        
        
        env = Environment(loader=FileSystemLoader('templates/SQLite/'))
        query = env.get_template('left_join_aud_table_sqlite .jinja').render(aud_ds_physical_name = aud_ds_physical_name,
                                                                            ds_physical_name = ds_physical_name,
                                                                            ds_alias = ds_alias,
                                                                            approved_column = approved_column,
                                                                            target_column = target_column,
                                                                            audience_pk = audience_pk,
                                                                            bk_features = bk_features,
                                                                            mob=mob)
        
        return query
    
    
    @module_logger
    def read_data_batch(self, **kwargs) -> str:
        columns_list = kwargs.get('columns_list')
        table_name = kwargs.get('table_name')
        #table_schema = kwargs.get('table_schema')
        #primary_key = kwargs.get('primary_key')
        
        env = Environment(loader=FileSystemLoader('templates/SQLite/'))
        query = env.get_template('read_batch_of_cols_sqlite.jinja').render(columns_list=columns_list,
                                                                            table_name = table_name)
                                                                            #primary_key = primary_key)
        
        return query
    
