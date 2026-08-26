import logging
import sys
from celery import current_task


class CeleryLoggingAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        if current_task:
            request = getattr(current_task, "request", None)
            if request:
                task_id = getattr(request, "id", "UnknownTaskID")
            else:
                task_id = "UnknownTaskID"
            task_name = getattr(current_task, "name", "UnknownTask")
            return f"[{task_name} @ {task_id}] - {msg}", kwargs

        return msg, kwargs


# Create a logger
root = logging.getLogger()
root.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
root.addHandler(handler)

# Create an adapter that includes task name and ID
appLogging = CeleryLoggingAdapter(root, {})
