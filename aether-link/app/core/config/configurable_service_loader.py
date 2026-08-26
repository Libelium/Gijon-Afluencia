"""
This module loads a configurable service
"""

from app.core.configurable_service.configurable_service import (
    ConfigurableService,
    ServiceParamDescription,
)
from dotenv import load_dotenv
from typing import Dict
import os

load_dotenv()

ConfigurableServiceClassMappping = Dict[str, type]


class ConfigurableServiceLoader:
    def __init__(self, service_mapping: ConfigurableServiceClassMappping):
        self.__service_mapping = service_mapping

    def __get_system_kwargs_from_params_description(
        self, description: ServiceParamDescription
    ) -> Dict:

        def get_env_param(
            param_name: str, param_type: type, required: bool, default: str
        ):

            param_value = os.getenv(param_name)

            if param_value is None and required:
                raise Exception(f"Missing required parameter {param_name}")

            if param_value is None:
                return param_type(default)

            return param_type(param_value)

        """
        Get the kwargs from the description
        """

        return {
            param_name: get_env_param(
                param_name, param["type"], param["required"], param["default"]
            )
            for param_name, param in description.items()
        }

    def load(self, service_name: str) -> ConfigurableService:
        service_class = self.__service_mapping.get(service_name)

        if service_class is None:
            raise Exception(
                f"Service {service_name} not found. Available services: {self.__service_mapping.keys()}"
            )

        # load env variables to configure the selected data source
        kwargs = self.__get_system_kwargs_from_params_description(
            service_class.params_description()
        )

        return service_class(**kwargs)
