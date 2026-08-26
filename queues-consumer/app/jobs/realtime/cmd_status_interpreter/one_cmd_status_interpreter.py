from typing import Any
from schemas.ngsi_cmd_info_schema import NgsiCmdInfo
from jobs.realtime.cmd_status_interpreter.cmd_status_interpreter import (
    CmdStatusInterpreter,
)


class OneCmdStatusInterpreter(CmdStatusInterpreter):
    def interpret_status(self, cmd: NgsiCmdInfo) -> (bool, Any):
        """
        Interprets the current status of a command for a LibeliumOne device.
        In this case, the cmd_info is like
            {
                "status": "PENDING" | "SENT"
                "value": Any
            }

        So it is pending only if the status is PENDING, and the value is the value! (if any)
        """

        info = cmd.cmd_info

        if info is None:
            return (False, None)

        if not isinstance(info, dict):
            return (False, None)

        info_status = info.get("status")
        info_value = info.get("value")

        pending = info_status == "PENDING"

        return (pending, info_value)
