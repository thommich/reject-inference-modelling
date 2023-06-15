from typing import Dict
from getpass import getpass
import pandas as pd
from engines.engines import EnginesInterface 


class HadoopEngine():
    conn: str = 'CONN'
    name: str = 'HADOOP'

    def __init__(self, engines_cfg: Dict[str,dict]):
        self.conn = self.get_db_connection(engines_cfg['conn_vars'][self.name])


    def get_db_connection(self, conn_vars: Dict[str,str]):
        return f'jdbc:teradata://{conn_vars["host"]}:{conn_vars["port"]}/{conn_vars["database"]}'


class HadoopEngineBuilder():
    def __init__(self):
        self._instance = None


    def __call__(self, engines_cfg: Dict, flavour: str) -> HadoopEngine:
        if not self._instance:
            self._instance = HadoopEngine(engines_cfg)
        return self._instance