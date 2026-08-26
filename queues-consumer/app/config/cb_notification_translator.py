from utils.ngsi.cb_notification_translator.cb_notification_translator import CBNotificationTranslator
from dotenv import load_dotenv
import os

# Load the env file
load_dotenv()


class CBNotificationTranslatorSettings:
    """
    Class that holds all the relevant configuration to the CBNotificationTranslator
    """

    DEFAULT_NOTIFICATION_FORMAT: str = os.getenv(
        "DEFAULT_NOTIFICATION_FORMAT", "ngsild"
    )

    def __init__(self):
        from utils.ngsi.cb_notification_translator.smart_notification_translator import (
            NgsiLdNormalizedNotificationTranslator,
            NgsiV2NormalizedNotificationTranslator,
            SmartNotificationTranslator,
        )

        translator_map = {
            "ngsild": NgsiLdNormalizedNotificationTranslator,
            "ngsiv2": NgsiV2NormalizedNotificationTranslator,
        }

        self.default_translator = translator_map.get(
            self.DEFAULT_NOTIFICATION_FORMAT, NgsiLdNormalizedNotificationTranslator
        )

        self.cb_notification_translator = SmartNotificationTranslator(
            default_translator=self.default_translator
        )

    def get_translator(self) -> CBNotificationTranslator:
        return self.cb_notification_translator
