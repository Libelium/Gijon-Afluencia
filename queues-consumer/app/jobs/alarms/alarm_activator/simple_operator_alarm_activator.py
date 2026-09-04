from enum import Enum
from typing import Any, Callable, List

from jobs.alarms.alarm_activator.alarm_activator import AlarmActivator


class SimpleOperator(str, Enum):
    """
    Operadores que admite una condicion de alarma (alarm_conditions.condition).
    """

    EQUAL = "eq"
    NOT_EQUAL = "ne"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "ge"
    LESS_THAN_OR_EQUAL = "le"
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"

    def get_operator(self) -> Callable[[List], bool]:
        operator = OPERATOR_FUNCTIONS.get(self)

        if operator is None:
            raise Exception(f"Operator {self} not supported")

        return operator

    def get_template_summary(self) -> Callable[[str, str, List, bool], str]:
        summary_function = SUMMARY_FUNCTIONS.get(self)

        if summary_function is None:
            raise Exception(f"Operator {self} not supported")

        return summary_function


OPERATOR_FUNCTIONS = {
    SimpleOperator.EQUAL: lambda operands: operands[0] == operands[1],
    SimpleOperator.NOT_EQUAL: lambda operands: operands[0] != operands[1],
    SimpleOperator.GREATER_THAN: lambda operands: operands[0] > operands[1],
    SimpleOperator.LESS_THAN: lambda operands: operands[0] < operands[1],
    SimpleOperator.GREATER_THAN_OR_EQUAL: lambda operands: operands[0] >= operands[1],
    SimpleOperator.LESS_THAN_OR_EQUAL: lambda operands: operands[0] <= operands[1],
    SimpleOperator.BETWEEN: lambda operands: operands[1]
    <= operands[0]
    <= operands[2],
    SimpleOperator.NOT_BETWEEN: lambda operands: operands[0] < operands[1]
    or operands[0] > operands[2],
}


def _comparison_summary(
    comparison: str,
) -> Callable[[str, str, List, bool], str]:
    def summary(
        reporter: str, main_operand_name: str, operands: List, negate: bool
    ) -> str:
        return (
            f"El ultimo {main_operand_name} reportado ({operands[0]}) por {reporter} "
            f"{'no ' if negate else ''}{comparison} {operands[1]}"
        )

    return summary


def _between_summary(
    reporter: str, main_operand_name: str, operands: List, negate: bool
) -> str:
    return (
        f"El ultimo {main_operand_name} reportado ({operands[0]}) por {reporter} "
        f"{'no ' if negate else ''}estaba entre {operands[1]} y {operands[2]}"
    )


def _not_between_summary(
    reporter: str, main_operand_name: str, operands: List, negate: bool
) -> str:
    return _between_summary(reporter, main_operand_name, operands, not negate)


SUMMARY_FUNCTIONS = {
    SimpleOperator.EQUAL: _comparison_summary("era igual a"),
    SimpleOperator.NOT_EQUAL: _comparison_summary("era distinto de"),
    SimpleOperator.GREATER_THAN: _comparison_summary("era mayor que"),
    SimpleOperator.LESS_THAN: _comparison_summary("era menor que"),
    SimpleOperator.GREATER_THAN_OR_EQUAL: _comparison_summary("era mayor o igual que"),
    SimpleOperator.LESS_THAN_OR_EQUAL: _comparison_summary("era menor o igual que"),
    SimpleOperator.BETWEEN: _between_summary,
    SimpleOperator.NOT_BETWEEN: _not_between_summary,
}


class SimpleOperatorAlarmActivator(AlarmActivator):
    """
    Activador de una unica condicion de umbral: compara el ultimo valor de la
    medida con los umbrales configurados.
    """

    def __init__(
        self,
        reporter_name: str,
        main_operand: Any,
        main_operand_name: str,
        aux_operands: List,
        operator: SimpleOperator,
    ):
        self.simple_operator = operator
        self.main_operand_name = main_operand_name
        self.reporter_name = reporter_name
        self.operands = self.__to_uniform_type([main_operand, *aux_operands])
        self.catched_result: bool = operator.get_operator()(self.operands)

    def __to_boolean(self, operands: List) -> List[bool]:
        boolean_operands = []

        for operand in operands:
            if isinstance(operand, bool):
                boolean_operands.append(operand)

            elif isinstance(operand, str) and operand.lower() in ["true", "false"]:
                boolean_operands.append(operand.lower() == "true")

            elif isinstance(operand, int):
                boolean_operands.append(operand == 1)

            else:
                raise ValueError(f"Cannot convert operand {operand} to boolean")

        return boolean_operands

    def __to_number(self, operands: List) -> List[float]:
        number_operands = []

        for operand in operands:
            if isinstance(operand, bool):
                number_operands.append(1.0 if operand else 0.0)

            elif isinstance(operand, (int, float, str)):
                number_operands.append(float(operand))

            else:
                raise ValueError(f"Cannot convert operand {operand} to number")

        return number_operands

    def __to_uniform_type(self, operands: List) -> List:
        """
        Los umbrales llegan siempre como texto y el valor de la medida con el
        tipo que trajo la notificacion: hay que igualarlos antes de comparar.
        """
        for converter in (self.__to_number, self.__to_boolean):
            try:
                return converter(operands)
            except (TypeError, ValueError):
                continue

        return [str(operand) for operand in operands]

    def activated(self) -> bool:
        return self.catched_result

    def summary(self) -> str:
        return self.simple_operator.get_template_summary()(
            self.reporter_name,
            self.main_operand_name,
            self.operands,
            not self.catched_result,
        )
