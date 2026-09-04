"""Deterministic environment for the test suite.

The Celery app is configured at import time, and the secure default
(`RABBITMQ_SECURITY=amqps`) makes that resolve a CA bundle from the system trust
store: a machine without one at OpenSSL's default path — a CI runner, a slim
image — cannot even collect the tests. Nothing here talks to a broker, so the
suite pins the plain protocol. A configured environment still wins, because
`setdefault` does not override what is already set.
"""

import os

os.environ.setdefault("RABBITMQ_SECURITY", "amqp")
