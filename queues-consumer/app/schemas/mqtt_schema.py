from enum import IntEnum


class MqttConnectRC(IntEnum):
    SUCCESS = 0
    INCORRECT_PROTOCOL_VERSION = 1
    INVALID_CLIENT_ID = 2
    SERVER_UNAVAILABLE = 3
    BAD_CREDENTIALS = 4
    NOT_AUTHORIZED = 5

    def error_message(self) -> str:
        messages = {
            self.INCORRECT_PROTOCOL_VERSION: "Incorrect protocol version",
            self.INVALID_CLIENT_ID: "Invalid client identifier",
            self.SERVER_UNAVAILABLE: "Server unavailable",
            self.BAD_CREDENTIALS: "Bad username or password",
            self.NOT_AUTHORIZED: "Not authorized",
        }
        return messages.get(self, "Unknown connection error")
