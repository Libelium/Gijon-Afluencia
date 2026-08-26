from abc import abstractmethod
from typing import Any
from datetime import datetime

from schemas.ngsi_cmd_info_schema import NgsiCmdInfo


class CmdStatusInterpreter:
    """
    Abstract class for interpreting the status of a command.
    The status of a command is goind to depend on the device type,
    so for each one (or group of them) we need to implement a different
    interpreter.
    """

    @abstractmethod
    def interpret_status(self, cmd: NgsiCmdInfo) -> (bool, Any):
        """
        Interprets the current status of a command. This can be:
            - The command is pending (not yet executed), then we get as result:
              (False, PendingCommandValue) PendingCommandValue is the value that
              is going to be executed for the command, if the command requires a value
            - The command has been executed, then we get as result: (True, None)

        Returns:
            (bool, Any): (isPending?, pendingValue)
                - isPending: True if the command is pending, False otherwise
                - pendingValue: The value that is going to be executed for the command,
                  if the command requires a value (false if the command is not pending, or
                  if the command does not require a value)
        """
        pass
