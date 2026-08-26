from datetime import datetime, timezone
from typing import Dict, List

import jobs.timeseries.timescale.contants as constants
from config.logging import appLogging as logging
from jobs.job import Job
from jobs.timeseries.timescale.models.entity_data_model import build_entity_data_model
import jobs.timeseries.timescale.session as ts_session
from jobs.timeseries.timescale.sql_template_loader import check_schema_template
from schemas.entity_data_notification import EntityAttr, EntityDataNotification
from sqlalchemy import Column, Tuple, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session


class TimescaleSyncJob(Job):
    """
    This job saves the timeseries data to the timescale database.
    """

    def __init__(self, entity_data: EntityDataNotification):
        self.entity_data: EntityDataNotification = entity_data

    def handle(self):
        try:
            for i in range(len(ts_session.ts_session_locals)):
                db = next(ts_session.get_session(i))
                try:
                    self.single_handle(db, i)
                    logging.info(f"Entity data saved to timescale database {i}")
                finally:
                    db.close()
        except Exception as e:
            logging.error(f"CRITICAL: Failed to save data into timescale: {e}")
            raise e

    def single_handle(self, db: Session = None, db_idx: int = 0):
        schema = f"{constants.SCHEMA_PREFIX}{self.entity_data.tenant}"
        self.__ensure_schema(schema, db, db_idx)
        entity_datas = self.__notification_to_entity_data(self.entity_data)

        if entity_datas:
            self.__bulk_save(entity_datas, schema, db)

    def __bulk_save(self, entity_datas: List[dict], schema: str, db: Session = None):
        """
        Save the entity data in bulk.
        """
        try:
            table = build_entity_data_model(ts_session.metadata, schema)

            insert_stmt = insert(table).values(entity_datas)
            on_conflict_stmt = insert_stmt.on_conflict_do_nothing(
                index_elements=["time", "entity_id", "attr_id", "scope_id"]
            )
            db.execute(on_conflict_stmt)

            db.commit()
        except Exception as e:
            logging.error(f"Error saving entity data: {e}")
            raise e

    def __ensure_schema(self, schema: str, db: Session = None, db_idx: int = 0):
        """
        Create the schema if it does not exist, as well as the table
        and the indexes. This is all done by a single SQL template script.
        """
        if schema in ts_session._confirmed_schemas.get(db_idx, set()):
            return

        logging.info(f"[schema_cache] schema '{schema}' not in cache for DB {db_idx}, running schema check")
        script = check_schema_template.render(schema=schema)

        try:
            db.execute(text(script))
            db.commit()
            ts_session._confirmed_schemas.setdefault(db_idx, set()).add(schema)
        except Exception as e:
            logging.error(f"Error creating schema {schema}: {e}")
            raise e

    def __notification_to_entity_data(
        self, notification: EntityDataNotification
    ) -> List[dict]:
        """
        Transform the notification to the entity data model.
        """

        entity_datas = []

        for attr in notification.data:

            entity_data = {
                "time": datetime.fromtimestamp(attr.timestamp, tz=timezone.utc),
                "entity_id": notification.urn,
                "entity_type": notification.type,
                "attr_id": attr.name,
                "scope_id": notification.scope,
                **self.__get_attr_value_col(attr),
            }

            entity_datas.append(entity_data)

        return entity_datas

    def __get_attr_value_col(self, attr: EntityAttr) -> dict:
        """
        Get the correct attribute value column, based on the attribute type.
        It returns a dict to be directly unpacked in the EntityData constructor.
        """

        # Define a mapping from Python types to column names and value types
        type_to_column: Dict[type, Tuple[str, Column]] = {
            None: ("none", "attr_string_value"),
            bool: ("boolean", "attr_boolean_value"),
            int: ("double", "attr_double_value"),
            float: ("double", "attr_double_value"),
            list: ("json", "attr_json_value"),
            dict: ("json", "attr_json_value"),
            str: ("string", "attr_string_value"),
        }

        value_data_type = type(attr.value) if attr.value is not None else None

        value_type, column = type_to_column.get(
            value_data_type, ("json", "attr_json_value")
        )

        all_columns = [val[1] for val in type_to_column.values() if val[1] != column]

        return {
            "attr_value_type": value_type,
            column: attr.value,
            **{col: None for col in all_columns},
        }
