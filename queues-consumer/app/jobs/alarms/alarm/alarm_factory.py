"""
Fabrica de alarmas: traduce lo que hay en la base de datos a alarmas listas
para evaluarse, resolviendo por el camino los valores que no venian en la
notificacion.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import dateutil.parser
import helpers.aether_link.aether_link_helper as aether_helper
import jobs.alarms.queries as queries
import models.crud.crud_custom_datamodels as crud_custom_datamodels
import models.crud.crud_entity as crud_entity
import models.crud.crud_entity_properties as crud_entity_properties
import models.crud.crud_preferences as crud_preferences
import models.crud.crud_tenant_scope as crud_tenant_scope
from config.logging import appLogging as logging
from jobs.alarms.alarm.alarm import Alarm
from jobs.alarms.alarm.basic_alarm_builder import BasicAlarmBuilder
from jobs.alarms.alarm.inactivity_alarm_builder import InactivityAlarmBuilder
from models.preferences_model import PreferenceType
from schemas.entity_data_notification import EntityDataNotification
from sqlalchemy.orm import Session

# Modelo de datos con el que la plataforma guarda el historico de las alarmas.
ALARM_DATAMODEL = "PlatformAlarm"


class AlarmFactory:

    def __init__(self):
        # Cache por pasada: (apikey, resource) del IoT Agent de cada usuario.
        self.__users_iota_service: Dict[int, Tuple[Optional[str], Optional[str]]] = {}

    def get_alarms(
        self,
        measure_ids: List[str],
        entity_data: EntityDataNotification,
        db: Session,
    ) -> List[Alarm]:
        """
        Alarmas de umbral que pueden dispararse o rearmarse con los valores que
        trae la notificacion.
        """
        return self.__build_basic_alarms(entity_data, measure_ids, db)

    def get_inactivity_alarms(
        self, current_time: datetime, db: Session, realtime_db: Session
    ) -> List[Alarm]:
        """
        Todas las alarmas de inactividad del sistema.
        """
        return self.__build_inactivity_alarms(current_time, db, realtime_db)

    def __get_user_iota_service(
        self, user_id: int, db: Session
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Servicio del IoT Agent por el que se publica el historico de las alarmas
        del usuario. Es opcional: si el servicio no esta dado de alta, la alarma
        se evalua igual y solo se pierde su serie temporal, asi que se devuelve
        (None, None) en vez de propagar el error.
        """
        if user_id in self.__users_iota_service:
            return self.__users_iota_service[user_id]

        service: Tuple[Optional[str], Optional[str]] = (None, None)

        try:
            scope_id = crud_preferences.get_user_preference(
                user_id=user_id,
                preference_name=PreferenceType.PLATFORM_DATA_SCOPE,
                db=db,
            )

            if not scope_id:
                raise ValueError(f"El usuario {user_id} no tiene ambito de datos")

            tenant, scope = crud_tenant_scope.get_tenant_scope(scope_id, db)

            if not scope:
                raise ValueError(f"El ambito {scope_id} no existe")

            service = aether_helper.get_datamodel_apikey_resource(
                tenant=tenant, scope=scope, datamodel=ALARM_DATAMODEL
            )

        except Exception as e:
            logging.warning(
                f"Sin servicio del IoT Agent para las alarmas del usuario {user_id}: {e}"
            )

        self.__users_iota_service[user_id] = service

        return service

    def __build_basic_alarms(
        self,
        entity_data: EntityDataNotification,
        measure_ids: List[str],
        db: Session,
    ) -> List[Alarm]:
        if entity_data.db_id is None:
            logging.warning(
                f"La notificacion de {entity_data.urn} no trae el id de la entidad: "
                "sus alarmas de umbral no se pueden evaluar"
            )
            return []

        alarms_info = queries.get_related_basic_alarms(
            entity_data.urn, measure_ids, db
        )

        if not alarms_info or not entity_data.data:
            return []

        max_timestamp = datetime.fromtimestamp(
            max(attr.timestamp for attr in entity_data.data)
        )

        builders: Dict[int, BasicAlarmBuilder] = {}
        # Medidas que una condicion necesita y esta notificacion no trae,
        # indexadas por id de entidad en la base de datos (no por urn).
        needed_measures: Dict[int, Set[str]] = {entity_data.db_id: set()}

        for alarm, condition in alarms_info:
            if condition.entity_id != entity_data.db_id or (
                condition.measure not in measure_ids
            ):
                needed_measures.setdefault(condition.entity_id, set()).add(
                    condition.measure
                )

            builder = builders.get(alarm.id)

            if builder is None:
                apikey, resource = self.__get_user_iota_service(alarm.user_id, db)
                builder = (
                    BasicAlarmBuilder()
                    .set_alarm(alarm)
                    .set_timestamp(max_timestamp)
                    .set_db(db)
                    .set_iota_service(apikey, resource)
                )
                builders[alarm.id] = builder

            builder.set_condition(condition)

        related_measures, id_to_urn_map = self.__get_not_updated_measures(
            needed_measures, max_timestamp, db
        )

        # Y encima, los valores que si traia la notificacion.
        related_measures.setdefault(entity_data.db_id, {})
        id_to_urn_map.setdefault(entity_data.db_id, entity_data.urn)

        for value in entity_data.data:
            related_measures[entity_data.db_id][value.name] = value.value

        for builder in builders.values():
            # No hace falta filtrar: cada constructor usa solo lo que necesita.
            builder.set_measures(related_measures)
            builder.set_id_to_urn_map(id_to_urn_map)

        return self.__build_all(builders.values())

    def __get_not_updated_measures(
        self,
        needed_measures: Dict[int, Set[str]],
        current_time: datetime,
        db: Session,
    ) -> Tuple[Dict[int, Dict[str, object]], Dict[int, str]]:
        """
        Ultimo valor anterior a current_time de las medidas que la notificacion
        no trae, preguntando a la serie temporal a traves del aether-link.
        """
        entity_uts_by_id = crud_entity.get_entity_urns_for_ids(
            list(needed_measures.keys()), db
        )
        id_to_urn_map = {
            entity_id: uts[0] for entity_id, uts in entity_uts_by_id.items()
        }

        requests = []
        id_by_entity_uts = {}

        for entity_id, measures in needed_measures.items():
            if not measures:
                continue

            entity_uts = entity_uts_by_id.get(entity_id)

            if entity_uts is None:
                logging.error(f"La entidad con id {entity_id} no esta en la base")
                continue

            entity_urn, tenant, scope = entity_uts
            id_by_entity_uts[(entity_urn, tenant, scope)] = entity_id

            requests.append(
                {
                    "device_ids": [entity_urn],
                    "measure_ids": list(measures),
                    "options": {
                        "limit": 2,
                        "end_date": current_time.isoformat(),
                        "tenant": tenant,
                        "scope": scope,
                    },
                }
            )

        if not requests:
            return {}, id_to_urn_map

        try:
            response = aether_helper.get_time_series(requests)
            parsed_response = self.__parse_time_series_response(response, current_time)

            measures_by_id = {}
            for entity_uts, measures in parsed_response.items():
                entity_id = id_by_entity_uts.get(entity_uts)

                if entity_id is None:
                    logging.error(f"La entidad {entity_uts} no esta en la base")
                    continue

                measures_by_id[entity_id] = measures

            return measures_by_id, id_to_urn_map

        except Exception as e:
            logging.error(f"Error leyendo la serie temporal de las alarmas: {e}")

        return {}, id_to_urn_map

    def __parse_time_series_response(
        self, response_list: List[dict], newer_before: datetime
    ) -> Dict[Tuple[str, str, str], Dict[str, object]]:
        """
        Deja la respuesta del aether-link como
        {(urn, tenant, scope): {medida: ultimo valor anterior a newer_before}}.
        """
        entities: Dict[Tuple[str, str, str], Dict[str, list]] = {}

        for response in response_list:
            options = response.get("options", {})
            entity_uts_base = (options.get("tenant", ""), options.get("scope", ""))

            for measure in response.get("time_series", []):
                entity_uts = (measure["device_id"], *entity_uts_base)
                entities.setdefault(entity_uts, {}).setdefault(
                    measure["measure_id"], []
                ).extend(measure["values"])

        last_values: Dict[Tuple[str, str, str], Dict[str, object]] = {}

        for entity_uts, measures in entities.items():
            for measure_id, values in measures.items():
                previous_values = sorted(
                    (
                        value
                        for value in values
                        if self.__to_datetime(value["timestamp"]) < newer_before
                    ),
                    key=lambda value: self.__to_datetime(value["timestamp"]),
                    reverse=True,
                )

                if previous_values:
                    last_values.setdefault(entity_uts, {})[measure_id] = (
                        previous_values[0]["value"]
                    )

        return last_values

    @staticmethod
    def __to_datetime(date_string: str) -> datetime:
        date = dateutil.parser.isoparse(date_string)
        return date.replace(tzinfo=None)

    def __build_inactivity_alarms(
        self, current_time: datetime, db: Session, realtime_db: Session
    ) -> List[Alarm]:
        inactivity_alarms = queries.get_inactivity_alarms(db)

        if not inactivity_alarms:
            return []

        builders: Dict[int, InactivityAlarmBuilder] = {}
        id_urn_map: Dict[int, str] = {}
        required_measures: Dict[str, Set[Optional[str]]] = {}
        measures: Set[str] = set()

        for urn, alarm, condition in inactivity_alarms:
            id_urn_map[condition.entity_id] = urn
            required_measures.setdefault(urn, set()).add(condition.measure)

            if condition.measure:
                measures.add(condition.measure)

            builder = builders.get(alarm.id)

            if builder is None:
                apikey, resource = self.__get_user_iota_service(alarm.user_id, db)
                builder = (
                    InactivityAlarmBuilder()
                    .set_alarm(alarm)
                    .set_current_timestamp(current_time)
                    .set_db(db)
                    .set_iota_service(apikey, resource)
                )
                builders[alarm.id] = builder

            builder.set_condition(condition)

        last_reports: Dict[str, Dict[Optional[str], datetime]] = {}
        for entity_urn, measure, timestamp in queries.get_last_reports(
            required_measures, realtime_db
        ):
            last_reports.setdefault(entity_urn, {})[measure] = timestamp

        entity_names = {
            entity_property.entity_id: entity_property.value
            for entity_property in crud_entity_properties.get_entity_property_bulk(
                list(id_urn_map.keys()), "name", realtime_db
            )
        }

        measure_names = {
            datamodel.command: datamodel.name
            for datamodel in crud_custom_datamodels.get_custom_datamodel_by_command_bulk(
                list(measures), db
            )
        }

        # Los datos comunes se resuelven de una vez, fuera del bucle anterior, y
        # se reparten aqui entre todos los constructores.
        for builder in builders.values():
            builder.set_id_urn_map(id_urn_map)
            builder.set_last_reports(last_reports)
            builder.set_entity_names(entity_names)
            builder.set_measure_names(measure_names)

        return self.__build_all(builders.values())

    @staticmethod
    def __build_all(builders) -> List[Alarm]:
        """
        Monta las alarmas descartando las que no se puedan construir: una mal
        configurada no debe impedir que se evaluen las demas.
        """
        alarms = []

        for builder in builders:
            try:
                alarms.append(builder.build())

            except Exception as e:
                logging.error(f"Alarma no construible: {e}")

        return alarms
