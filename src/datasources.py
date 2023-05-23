import yaml
from pydantic import BaseModel
from abc import ABC, abstractmethod
from enum import Enum
from Type import List
from typing import Dict, Tuple, List, Any
from dataclasses import dataclass


class DataSourceGroup():
    """
        Esta classe representa um conjunto de fontes de dados de entrada que será iterado durante o processo de recursive feature elimination.
        
        Args:
        name (str): Nome do grupo conceitual. concepts (Dict[str, str]): Dicionário mapeando o conceito literal (que será usado para geração automática de nome de recurso) e o conceito real.
        ds_config: Dict[]
    """


    def get_ds_group(self, ds_config: str) -> List[DataSource]:
        data sources = []
        for ds in ds_config:
        data_sources.append(DataSource(ds.schema, ds.database, ds.technology, ds.parquet_file))


class DataSource():
    """
        As tabelas no Loom usam gerenciadores de contexto para sinalizar aos campos quais tabelas eles estão sendo criados em.
        Args:
        schema (str): O nome do schema no qual esta tabela reside..
        pname (str): 0 nome fisico da tabela (nome real no banco de dados) Iname (str): O nome lógico da tabela (nome legível por humanos)
        alias (str, optional): Um alias a ser usado ao gerar consultas envolvendo essa mesa. Se não for especificado, o nome físico será usado.
    """

    def __init__(
        self,
        schema: str,
        database: str,
        technology: str,
        pq_file: str
    ):
        self._schema: str = schema
        self._database: str = database
        self._technology: str = technology
        self._pq_file: str = pq_file



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