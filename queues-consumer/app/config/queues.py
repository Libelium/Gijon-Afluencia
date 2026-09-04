from __future__ import annotations

import uuid

from config.config import settings
from kombu import Exchange, Queue

# main exchange
PLATFORM_EXCHANGE = Exchange("platform", type="direct")

# some preficex for the queues
QUEUE_PREFIX = "platform"
SYNC_PREFIX = "sync"
DATA_PREFIX = "data"
ALARMS_PREFIX = "alarms"
CROWD_PREFIX = "crowd"
DATA_CACHE_PREFIX = "data-cache"


"""
ALL QUEUES IN THE APPLICATION
"""

ALL_QUEUES = []


"""
SYNC QUEUES
"""
SYNC_CB_NOTIFICATION_QUEUE_NAME = f"{QUEUE_PREFIX}.{SYNC_PREFIX}.cb_notification"
SYNC_CB_NOTIFICATION_DLQ_NAME = f"{SYNC_CB_NOTIFICATION_QUEUE_NAME}.dlq"
SYNC_TIMESERIES_QUEUE_NAME = f"{QUEUE_PREFIX}.{SYNC_PREFIX}.timeseries"
SYNC_REALTIME_QUEUE_NAME = f"{QUEUE_PREFIX}.{SYNC_PREFIX}.realtime"
SYNC_NEW_CB_SUBSCRIPTION_QUEUE_NAME = f"{QUEUE_PREFIX}.{SYNC_PREFIX}.new_cb_subscription"
SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE_NAME = (
    f"{QUEUE_PREFIX}.{SYNC_PREFIX}.auto_subscription_sync"
)
SYNC_CB_NOTIFICATION_DLQ = Queue(
    name=SYNC_CB_NOTIFICATION_DLQ_NAME,
    routing_key=SYNC_CB_NOTIFICATION_DLQ_NAME,
    exchange=PLATFORM_EXCHANGE,
)

SYNC_CB_NOTIFICATION_QUEUE = Queue(
    name=SYNC_CB_NOTIFICATION_QUEUE_NAME,
    routing_key=SYNC_CB_NOTIFICATION_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_CB_NOTIFICATION_QUEUE_NAME, "priority"
        )
    },
)

SYNC_NEW_CB_SUBSCRIPTION_QUEUE = Queue(
    name=SYNC_NEW_CB_SUBSCRIPTION_QUEUE_NAME,
    routing_key=SYNC_NEW_CB_SUBSCRIPTION_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_NEW_CB_SUBSCRIPTION_QUEUE_NAME, "priority"
        )
    },
)

SYNC_TIMESERIES_QUEUE = Queue(
    name=SYNC_TIMESERIES_QUEUE_NAME,
    routing_key=SYNC_TIMESERIES_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_TIMESERIES_QUEUE_NAME, "priority"
        )
    },
)

SYNC_REALTIME_QUEUE = Queue(
    name=SYNC_REALTIME_QUEUE_NAME,
    routing_key=SYNC_REALTIME_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_REALTIME_QUEUE_NAME, "priority"
        )
    },
)

SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE = Queue(
    name=SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE_NAME,
    routing_key=SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE_NAME, "priority"
        )
    },
)

SYNC_QUEUES = [
    SYNC_CB_NOTIFICATION_QUEUE,
    SYNC_NEW_CB_SUBSCRIPTION_QUEUE,
    SYNC_TIMESERIES_QUEUE,
    SYNC_REALTIME_QUEUE,
    SYNC_AUTO_SUBSCRIPTION_SYNC_QUEUE,
]

ALL_QUEUES += SYNC_QUEUES

"""
ALARMS QUEUES
"""
ALARMS_ENTITY_DATA_CHECK_QUEUE_NAME = f"{QUEUE_PREFIX}.{ALARMS_PREFIX}.entity_data_check"
ALARMS_CHECK_INACTIVITY_QUEUE_NAME = f"{QUEUE_PREFIX}.{ALARMS_PREFIX}.check_inactivity"

ALARMS_ENTITY_DATA_CHECK_QUEUE = Queue(
    name=ALARMS_ENTITY_DATA_CHECK_QUEUE_NAME,
    routing_key=ALARMS_ENTITY_DATA_CHECK_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            ALARMS_ENTITY_DATA_CHECK_QUEUE_NAME, "priority"
        )
    },
)

ALARMS_CHECK_INACTIVITY_QUEUE = Queue(
    name=ALARMS_CHECK_INACTIVITY_QUEUE_NAME,
    routing_key=ALARMS_CHECK_INACTIVITY_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            ALARMS_CHECK_INACTIVITY_QUEUE_NAME, "priority"
        )
    },
)

ALARMS_QUEUES = [ALARMS_ENTITY_DATA_CHECK_QUEUE, ALARMS_CHECK_INACTIVITY_QUEUE]

ALL_QUEUES += ALARMS_QUEUES

"""
DATA QUEUES
"""
DATA_IMPORTATION_QUEUE_NAME = f"{QUEUE_PREFIX}.{DATA_PREFIX}.importation"
DATA_IMPORTATION_QUEUE = Queue(
    name=DATA_IMPORTATION_QUEUE_NAME,
    routing_key=DATA_IMPORTATION_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            DATA_IMPORTATION_QUEUE_NAME, "priority"
        )
    },
)

DATA_QUEUES = [DATA_IMPORTATION_QUEUE]

ALL_QUEUES += DATA_QUEUES

"""
CROWD QUEUES
"""
CROWD_QUEUE_PROCESS_VISITORS_NAME = f"{QUEUE_PREFIX}.{CROWD_PREFIX}.process_visitors"
CROWD_QUEUE_PROCESS_VISITORS = Queue(
    name=CROWD_QUEUE_PROCESS_VISITORS_NAME,
    routing_key=CROWD_QUEUE_PROCESS_VISITORS_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_PROCESS_VISITORS_NAME, "priority"
        )
    },
)


CROWD_QUEUE_PROCESS_VISITORS_ALL_NAME = (
    f"{QUEUE_PREFIX}.{CROWD_PREFIX}.process_visitors_all"
)
CROWD_QUEUE_PROCESS_VISITORS_ALL = Queue(
    name=CROWD_QUEUE_PROCESS_VISITORS_ALL_NAME,
    routing_key=CROWD_QUEUE_PROCESS_VISITORS_ALL_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_PROCESS_VISITORS_ALL_NAME, "priority"
        )
    },
)

CROWD_QUEUE_CLASSIFICATION_NAME = f"{QUEUE_PREFIX}.{CROWD_PREFIX}.classification"
CROWD_QUEUE_CLASSIFICATION = Queue(
    name=CROWD_QUEUE_CLASSIFICATION_NAME,
    routing_key=CROWD_QUEUE_CLASSIFICATION_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_CLASSIFICATION_NAME, "priority"
        )
    },
)

CROWD_QUEUE_CLASIFICATION_ALL_NAME = f"{QUEUE_PREFIX}.{CROWD_PREFIX}.classification_all"
CROWD_QUEUE_CLASIFICATION_ALL = Queue(
    name=CROWD_QUEUE_CLASIFICATION_ALL_NAME,
    routing_key=CROWD_QUEUE_CLASIFICATION_ALL_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_CLASIFICATION_ALL_NAME, "priority"
        )
    },
)

CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME = f"{QUEUE_PREFIX}.{CROWD_PREFIX}.flows_municipality"
CROWD_QUEUE_FLOWS_MUNICIPALITY = Queue(
    name=CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME,
    routing_key=CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_FLOWS_MUNICIPALITY_NAME, "priority"
        )
    },
)

CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL_NAME = (
    f"{QUEUE_PREFIX}.{CROWD_PREFIX}.flows_municipality_all"
)
CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL = Queue(
    name=CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL_NAME,
    routing_key=CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL_NAME, "priority"
        )
    },
)
CROWD_QUEUE_UNIQUE_VISITORS_ALL_NAME = (
    f"{QUEUE_PREFIX}.{CROWD_PREFIX}.unique_visitors_all_job"
)
CROWD_QUEUE_UNIQUE_VISITORS_ALL = Queue(
    name=CROWD_QUEUE_UNIQUE_VISITORS_ALL_NAME,
    routing_key=CROWD_QUEUE_UNIQUE_VISITORS_ALL_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_UNIQUE_VISITORS_ALL_NAME, "priority"
        )
    },
)
CROWD_QUEUE_UNIQUE_VISITORS_NAME = f"{QUEUE_PREFIX}.{CROWD_PREFIX}.unique_visitors"
CROWD_QUEUE_UNIQUE_VISITORS = Queue(
    name=CROWD_QUEUE_UNIQUE_VISITORS_NAME,
    routing_key=CROWD_QUEUE_UNIQUE_VISITORS_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            CROWD_QUEUE_UNIQUE_VISITORS_NAME, "priority"
        )
    },
)

CROWD_QUEUES = [
    CROWD_QUEUE_PROCESS_VISITORS,
    CROWD_QUEUE_PROCESS_VISITORS_ALL,
    CROWD_QUEUE_CLASSIFICATION,
    CROWD_QUEUE_CLASIFICATION_ALL,
    CROWD_QUEUE_FLOWS_MUNICIPALITY,
    CROWD_QUEUE_FLOWS_MUNICIPALITY_ALL,
    CROWD_QUEUE_UNIQUE_VISITORS,
    CROWD_QUEUE_UNIQUE_VISITORS_ALL,
]

ALL_QUEUES += CROWD_QUEUES

"""
QUEUES NOT NEEDED FOR THE ON-PREMISE INSTALLATION
"""
NOT_NEEDED_ON_PREMISE_QUEUES = [SYNC_TIMESERIES_QUEUE]


"""
DATA CACHE QUEUES
"""
DATA_CACHE_QUEUE_CROWD_NAME = f"{QUEUE_PREFIX}.{DATA_CACHE_PREFIX}.crowd"
DATA_CACHE_QUEUE_CROWD = Queue(
    name=DATA_CACHE_QUEUE_CROWD_NAME,
    routing_key=DATA_CACHE_QUEUE_CROWD_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            DATA_CACHE_QUEUE_CROWD_NAME, "priority"
        )
    },
)


DATA_CACHE_QUEUE_CROWD_ALL_NAME = f"{QUEUE_PREFIX}.{DATA_CACHE_PREFIX}.crowd_all"
DATA_CACHE_QUEUE_CROWD_ALL = Queue(
    name=DATA_CACHE_QUEUE_CROWD_ALL_NAME,
    routing_key=DATA_CACHE_QUEUE_CROWD_ALL_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={
        "x-priority": settings.QUEUE_TASK_CONFIG.get_config_param(
            DATA_CACHE_QUEUE_CROWD_ALL_NAME, "priority"
        )
    },
)

DATA_CACHE_QUEUES = [
    DATA_CACHE_QUEUE_CROWD,
    DATA_CACHE_QUEUE_CROWD_ALL,
]

ALL_QUEUES += DATA_CACHE_QUEUES

"""
TEST QUEUES
WARNING: this queue is only for testing purposes,
so by default it is not included in the ALL_QUEUES list.
Whenever you use this, make sure to delete it afterwards
(specially in production environments)
"""

LOCAL_ID = str(uuid.getnode())

TEST_QUEUE_NAME = f"{QUEUE_PREFIX}.test.{LOCAL_ID}"

TEST_QUEUE = Queue(
    name=TEST_QUEUE_NAME,
    routing_key=TEST_QUEUE_NAME,
    exchange=PLATFORM_EXCHANGE,
    consumer_arguments={"x-priority": 10},
)

"""
CUSTOM QUEUES
"""

# This is only for testing purposes
# CUSTOM_QUEUES = [SYNC_CB_NOTIFICATION_QUEUE]
CUSTOM_QUEUES = []
