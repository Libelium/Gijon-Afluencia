"""
DLQ Recovery Job

Auto-terminating process that consumes messages from DLQ and republishes them to the original queue.
Uses direct Kombu consumer to avoid task conflicts.
"""

import sys
import time
import socket
from typing import Tuple
from config.config import settings
from config.logging import appLogging as logging
from config.celery import app as celery_app
from config.queues import SYNC_CB_NOTIFICATION_DLQ_NAME, SYNC_CB_NOTIFICATION_QUEUE_NAME
from kombu import Queue


def _extract_message_info(message) -> Tuple[str, str]:
    """
    Extract task name and task ID from message for logging purposes.
    Safe extraction that never fails - returns 'unknown' if info cannot be extracted.

    Args:
        message: Kombu message object

    Returns:
        Tuple of (task_name, task_id)
    """
    task_name = "unknown"
    task_id = "unknown"

    try:
        if hasattr(message, "headers") and message.headers:
            task_name = message.headers.get("task", "unknown")
            task_id = message.headers.get("id", "unknown")
    except Exception:
        pass

    return task_name, task_id


def _check_queue_status(dlq_queue, conn) -> int:
    """
    Check the number of pending messages in the DLQ.

    Args:
        dlq_queue: Kombu Queue object
        conn: Kombu connection

    Returns:
        Number of pending messages
    """
    queue_state = dlq_queue(conn).queue_declare(passive=True)
    return queue_state.message_count


def _republish_message(message, target_queue_name: str) -> None:
    """
    Republish a message from DLQ to the target queue.
    Preserves original message body, headers, and properties.

    Args:
        message: Kombu message object
        target_queue_name: Name of the queue to republish to
    """
    with celery_app.producer_or_acquire() as producer:
        body = message.body if hasattr(message, "body") else message.payload

        producer.publish(
            body,
            exchange="",
            routing_key=target_queue_name,
            headers=message.headers if hasattr(message, "headers") else {},
            content_type=(
                message.content_type
                if hasattr(message, "content_type")
                else "application/json"
            ),
            content_encoding=(
                message.content_encoding
                if hasattr(message, "content_encoding")
                else "utf-8"
            ),
        )


def _handle_idle_timeout(
    idle_time: float, idle_timeout: int, check_interval: int, processed_count: int
) -> bool:
    """
    Check if idle timeout is reached and log countdown.

    Args:
        idle_time: Current idle time in seconds
        idle_timeout: Maximum idle time before termination
        check_interval: Interval for logging countdown
        processed_count: Total messages processed

    Returns:
        True if should terminate, False otherwise
    """
    if idle_time >= idle_timeout:
        logging.info(
            f"DLQ empty for {idle_timeout}s. "
            f"Total messages processed: {processed_count}. Exiting."
        )
        return True

    remaining = idle_timeout - idle_time
    if remaining > 0 and int(idle_time) % check_interval == 0:
        logging.info(f"DLQ empty. Terminating in {remaining:.0f}s...")

    return False


def run_dlq_recovery():
    """
    Main DLQ recovery loop.
    Consumes messages from DLQ and republishes them to the original queue.
    Auto-terminates when no messages for idle_timeout seconds.
    """
    idle_timeout = settings.DLQ_RECOVERY_IDLE_TIMEOUT_SECONDS
    check_interval = settings.DLQ_RECOVERY_CHECK_INTERVAL_SECONDS
    last_activity = time.time()
    processed_count = 0

    logging.info(f"DLQ Recovery Job started. Idle timeout: {idle_timeout}s")

    with celery_app.connection_or_acquire() as conn:
        dlq_queue = Queue(SYNC_CB_NOTIFICATION_DLQ_NAME)

        while True:
            try:
                pending = _check_queue_status(dlq_queue, conn)

                if pending == 0:
                    idle_time = time.time() - last_activity

                    if _handle_idle_timeout(
                        idle_time, idle_timeout, check_interval, processed_count
                    ):
                        sys.exit(0)

                    time.sleep(check_interval)
                    continue

                message = dlq_queue(conn).get(no_ack=False)

                if message is None:
                    time.sleep(1)
                    continue

                task_name, task_id = _extract_message_info(message)

                _republish_message(message, SYNC_CB_NOTIFICATION_QUEUE_NAME)

                message.ack()

                processed_count += 1
                last_activity = time.time()

                logging.info(
                    f"Republished message to {SYNC_CB_NOTIFICATION_QUEUE_NAME}. "
                    f"Task: {task_name}, ID: {task_id}, Total processed: {processed_count}"
                )

            except (socket.timeout, socket.error, OSError) as conn_error:
                logging.error(f"Connection error processing DLQ: {conn_error}")
                time.sleep(5)
                continue
            except Exception as e:
                logging.error(f"Error processing DLQ message: {e}", exc_info=True)
                time.sleep(1)
                continue
