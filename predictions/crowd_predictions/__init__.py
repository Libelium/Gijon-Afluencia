"""
LIDAR + Smart Spot sensor fusion and crowd forecasting for the platform.

Everything importable lives here. scripts/ holds the entry points: run_daily.py is
the one the CronJob calls (train + predict) and run_ote.py the one for the LIDAR raw
ingestion, while main.py/train.py/predict.py stay runnable on their own.

No FIELD reads configuration at import time - see config/settings.py for why that
matters. (load_dotenv() does run at import, and it finds the .env by walking up from
the module's own directory, not from the cwd.)
"""
