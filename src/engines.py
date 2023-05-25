from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Dict



class Engine(ABC):
    """

    """
    def __init__(self, engines_config: Dict):
        self.__engines_enum = self.__set_engines_enum(engines_config)

    #Binds the engines parameters to a different instance of Engine each
    def __set_engines_enum(self, engines_config: Dict) -> Enum:
        engines_dict = {}        

        for ec in engines_config:
            engines_dict[ec] = globals()[ec.capitalize() + 'Engine']
        
        return Enum('EnginesEnum', engines_dict)


class TeradataEngine(Engine):
    pass


class HadoopEngine(Engine):
    pass