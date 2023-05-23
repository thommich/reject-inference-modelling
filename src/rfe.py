import yaml
from pydantic import BaseModel from abc import ABC, abstractmethod
from enum import Enum from Type import List
from typing import Dict, Tuple, List, Any


class RFE():
    """
    As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
    Args:
    Iname (str): 0 nome lógico da tabela (nome legível por humanos)
    schema (str): O nome do schema no qual esta tabela reside.. pname (str): O nome físico da tabela (nome real no banco de dados) alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    def __init__( self,
        schema: str,
        database: str,
        technology: str,
        pq_file: str,
        #config: Optional [str] = None
        self._parameters = self._load config_(config)
        self._variables = self._load_variables_(config)
    ):
    
    def get_public_df(self): # -> List[str]: 
        pass
    
    def get_rfe_df(self): # -> List[str]: 
        pass
    
    def plot_results(self): 
        pass