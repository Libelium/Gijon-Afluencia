import importlib

from config.config import settings

for _module in settings.WORKER_TYPE.get_task_modules():
    importlib.import_module(_module)
