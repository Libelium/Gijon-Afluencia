from abc import ABC, abstractmethod
from typing import Dict, List, TypedDict

class ParamDescription(TypedDict):
    """
    Description of a parameter
    """

    type: type
    description: str
    required: bool
    default: str

ServiceParamDescription = Dict[str, ParamDescription]


class ConfigurableService(ABC):
    """
    Generic configurable service
    """

    @abstractmethod
    def __init__(self, **kwargs):
        """
        Initialize the service. Needed parameters should match kwargs_description
        method.
        """
        pass

    @abstractmethod
    def params_description() -> ServiceParamDescription:
        """
        Description of the needed kwargs
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Return true if the service is ready to be used, throw an exception otherwise
        """
        pass
