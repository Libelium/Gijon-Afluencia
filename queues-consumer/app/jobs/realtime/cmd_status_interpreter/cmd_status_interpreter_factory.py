from jobs.realtime.cmd_status_interpreter.cmd_status_interpreter import (
    CmdStatusInterpreter,
)
from jobs.realtime.cmd_status_interpreter.one_cmd_status_interpreter import (
    OneCmdStatusInterpreter,
)


class CmdStatusInterpreterFactory:
    """
    Factory class for creating CmdStatusInterpreter instances.
    As we extend the types, it will be more useful, for now, it only
    creates OneCmdStatusInterpreter instances.
    """


    _type_mapper = {"LibeliumOne": OneCmdStatusInterpreter}

    def build_interpreter(self, entity_type: str) -> CmdStatusInterpreter:
        """
        Builds the interpreter for the commands of the given entity type.
        """
        target_class = self._type_mapper.get(entity_type)

        if target_class is None:
            return None

        return target_class()
