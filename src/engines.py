from abc import ABC
from dataclasses import dataclass
import enum



class Engine(ABC):
    """

    """
    def __init__(self, engines_config: Dict):
        self.__engines_enum = __set_engines_enum(engines_config['engines'])


    #Binds the engines parameters to a different instance of Engine each
    def __set_engines_enum(self, engines_config: Dict): -> Enum [Engine]:
        engines_dict = {}        

        for ec in engines_config:
            engines_dict[ec] = globals()[ec.capitalize() + 'Engine']
        
        return enum.Enum('EnginesEnum', enum.Enum('EngineEnum', engines_dict))


class TeradataEngine(Engine):
    pass


class HadoopEngine(Engine):
    pass