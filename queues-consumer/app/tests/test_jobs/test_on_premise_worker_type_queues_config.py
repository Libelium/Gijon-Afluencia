from config.config import settings
from unittest.mock import patch
from config.queues import ALL_QUEUES, NOT_NEEDED_ON_PREMISE_QUEUES
from config.queue_worker_type import WorkerType
import pytest


class TestOnPremiseWorkerTypeQueuesConfig:

    # Check that the number of queues for the universal on-premise worker type is correct
    NUMBER_OF_UNIVERSAL_QUEUES = len(WorkerType.UNIVERSAL.get_queues())
    EXPECTED_NUMBER_OF_ON_PREMISE_QUEUES = len(ALL_QUEUES) - len(
        NOT_NEEDED_ON_PREMISE_QUEUES
    )
    EXPECTED_NUMBER_OF_DIFFERENT_QUEUES = (
        NUMBER_OF_UNIVERSAL_QUEUES - EXPECTED_NUMBER_OF_ON_PREMISE_QUEUES
    )

    def test_get_queues_for_universal_on_premise_worker_type(self):
        with patch(
            "config.config.settings.WORKER_TYPE", WorkerType.UNIVERSAL_ON_PREMISE
        ):
            queues = settings.WORKER_TYPE.get_queues()
            expected_queues = [
                queue
                for queue in ALL_QUEUES
                if queue not in NOT_NEEDED_ON_PREMISE_QUEUES
            ]
            assert (
                queues == expected_queues
                and len(queues) == self.EXPECTED_NUMBER_OF_ON_PREMISE_QUEUES
            )
