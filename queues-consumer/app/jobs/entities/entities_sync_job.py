from datetime import datetime
from typing import List, Optional

from schemas.entity_data_notification import EntityDataNotification
from jobs.job import Job
from sqlalchemy.orm import Session
from db.session_helpers import main_session, realtime_session
from schemas.fiware_subscription_schema import TypeSubscriptionMessage
from tasks.sync import save_realtime_job, save_timeseries_job
from config.config import settings
import models.crud.crud_entity as crud_entity
import helpers.aether_link.aether_link_helper as aether_link_helper
from utils.ngsi.cb_notification_translator.cb_notification_translator import (
    CBNotificationTranslator,
)
from config.logging import appLogging as logging
import models.crud.crud_status_update as crud_status_update


class FiwareEntitiesSync(Job):
    """
    Syncs FIWARE entities from the context broker into the Platform DB.
    Manages type subscriptions and fetches entities for the given tenant/scope.
    """

    def __init__(
        self,
        payload: TypeSubscriptionMessage,
        main_db: Optional[Session] = None,
        realtime_db: Optional[Session] = None,
    ):
        self.payload: TypeSubscriptionMessage = payload
        self._injected_main = main_db
        self._injected_realtime = realtime_db
        self.main_db: Optional[Session] = None
        self.realtime_db: Optional[Session] = None

    def __sync_entity(
        self,
        entity_raw: dict,
        translator: CBNotificationTranslator,
        force_resync: bool = False,
    ) -> None:
        """
        Syncs the entity with the database.
        If force_resync is True, dispatches realtime+timeseries even for entities
        that already exist in the database.
        """

        entity_data: EntityDataNotification = translator.translate_entity(
            entity=entity_raw,
            tenant=self.payload.tenant,
            scope=self.payload.scope,
            default_timestamp=datetime.now(),
        )

        entity_model, created = crud_entity.get_or_create_entity(
            payload={
                "urn": entity_data.urn,
                "datamodel": entity_data.type,
                "tenant": entity_data.tenant,
                "scope": entity_data.scope,
            },
            db=self.main_db,
            creation_check=True,
        )

        if not entity_model:
            logging.warning(
                f"Entity {entity_data.urn} ({entity_data.type}) could not be retrieved or created"
            )
            return

        if not created and not force_resync:
            logging.debug(
                f"Entity {entity_data.urn} already exists, skipping dispatch"
            )
            return

        entity_data.db_id = entity_model.id

        action = "Created" if created else "Force-resyncing"
        logging.info(f"{action} entity {entity_data.urn} ({entity_data.type})")

        save_realtime_job.delay(entity_data)
        save_timeseries_job.delay(entity_data)

    def __manage_subscriptions(self, old_subs: List[str]) -> List[str]:
        """
        Handles subscription/unsubscription in the broker and local DB.
        Returns the list of newly added subscription types.
        """
        if self.payload.create_new_subscriptions and self.payload.subscribe_types:
            logging.info(
                f"Subscribing to types {self.payload.subscribe_types}"
                + (f", unsubscribing from {self.payload.unsubscribe_types}" if self.payload.unsubscribe_types else "")
                + f" for tenant: {self.payload.tenant}, scope: {self.payload.scope}"
            )
            aether_link_helper.update_platform_type_subscriptions(
                self.payload.subscribe_types,
                self.payload.unsubscribe_types,
                self.payload.tenant,
                self.payload.scope,
            )

            new_subs = list(set(self.payload.subscribe_types) - set(old_subs))
            if new_subs:
                logging.info(f"New subscriptions added: {new_subs}")
            return new_subs

        if self.payload.unsubscribe_types:
            logging.info(
                f"Unsubscribing from types {self.payload.unsubscribe_types}"
                f" for tenant: {self.payload.tenant}, scope: {self.payload.scope}"
            )
            aether_link_helper.update_platform_type_subscriptions(
                [],
                self.payload.unsubscribe_types,
                self.payload.tenant,
                self.payload.scope,
            )

        return []

    def __resolve_types_to_sync(
        self, old_subs: List[str], new_subs: List[str]
    ) -> List[str]:
        """
        Determines which entity types need their entities fetched and synced.
        """
        if not self.payload.filter_types and not self.payload.sync_existing:
            return new_subs

        all_subs = set(old_subs) | set(new_subs)

        if self.payload.filter_types:
            return [t for t in self.payload.filter_types if t in all_subs]
        return list(all_subs)

    def __fetch_and_sync_entities(self, types_to_sync: List[str]) -> None:
        """
        For each type, fetches entities from the broker (paginated)
        and syncs them to the local DB. Errors on one type do not
        block the others.
        """
        force_resync = self.payload.sync_existing
        translator = settings.CB_NOTIFICATION.get_translator()

        logging.info(
            f"Syncing entities for types: {types_to_sync} in tenant: {self.payload.tenant}, "
            f"scope: {self.payload.scope} (force_resync={force_resync})"
        )

        for entity_type in types_to_sync:
            try:
                for entity in aether_link_helper.get_entities_by_type_paginated(
                    [entity_type], self.payload.tenant, self.payload.scope
                ):
                    self.__sync_entity(entity, translator, force_resync=force_resync)
            except Exception as e:
                logging.error(
                    f"Failed to sync type {entity_type} for tenant: {self.payload.tenant}, "
                    f"scope: {self.payload.scope}: {e}"
                )
                continue

    def __handle(self) -> None:
        if (
            not self.payload.subscribe_types
            and not self.payload.unsubscribe_types
            and not self.payload.auto_discovery
            and not self.payload.sync_existing
            and not self.payload.filter_types
        ):
            logging.info(
                f"Nothing to do for tenant: {self.payload.tenant}, scope: {self.payload.scope} — no types or actions specified"
            )
            return

        logging.info(
            f"Handling FiwareEntitiesSync for tenant: {self.payload.tenant}, scope: {self.payload.scope} "
            f"with payload: {self.payload.dict()}"
        )

        old_subs = aether_link_helper.get_platform_type_subscriptions(
            self.payload.tenant, self.payload.scope
        )

        logging.info(
            f"Current subscriptions for tenant: {self.payload.tenant}, scope: {self.payload.scope}: {old_subs}"
        )

        if self.payload.auto_discovery:
            discovered_types = aether_link_helper.get_data_types(
                self.payload.tenant, self.payload.scope
            )
            logging.info(
                f"Auto discovery for tenant: {self.payload.tenant}, scope: {self.payload.scope} "
                f"found types: {discovered_types}"
            )
            self.payload.subscribe_types = list(
                set(discovered_types) | set(self.payload.subscribe_types or [])
            )

        new_subs = self.__manage_subscriptions(old_subs)
        types_to_sync = self.__resolve_types_to_sync(old_subs, new_subs)
        if not types_to_sync:
            logging.info(
                f"No new types to sync for tenant: {self.payload.tenant}, scope: {self.payload.scope}"
            )
            return

        self.__fetch_and_sync_entities(types_to_sync)

    def handle(self) -> None:
        logging.info(
            f"FiwareEntitiesSync started for tenant: {self.payload.tenant}, scope: {self.payload.scope}"
        )
        with (
            main_session(self._injected_main) as main_db,
            realtime_session(self._injected_realtime) as realtime_db,
        ):
            self.main_db = main_db
            self.realtime_db = realtime_db

            error = None
            try:
                self.__handle()
            except Exception as e:
                logging.error(f"Error handling FiwareEntitiesSync: {e}")
                error = e

        logging.info(
            f"FiwareEntitiesSync finished for tenant: {self.payload.tenant}, scope: {self.payload.scope}"
            f" — status: {'error' if error else 'success'}"
        )

        crud_status_update.create_status_update(
            {
                "user_id": self.payload.user_id,
                "source": "DatamodelSubscription",
                "status": {
                    "request": self.payload.dict(),
                    "status": "error" if error else "success",
                    "error": str(error) if error else None,
                },
            },
            self.realtime_db,
        )
