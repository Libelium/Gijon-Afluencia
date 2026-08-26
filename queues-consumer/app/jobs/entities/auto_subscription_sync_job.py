from schemas.fiware_subscription_schema import TypeSubscriptionMessage
from jobs.job import Job

from schemas.auto_subscription_request_schema import AutoSubscriptionRequestSchema
from sqlalchemy.orm import Session
from models.preferences_model import PreferenceType
import models.crud.crud_preferences as crud_preferences
import models.crud.crud_organizations as crud_organizations
from config.logging import appLogging as logging


class AutoSubscriptionSyncJob(Job):
    """
    This jobs syncronizes the entities from the Fiware Context Broker for
    an organization, of for all the organizations of the platform.

    For an organization, it syncs all the scopes that are property of
    the organization.
    """

    def __init__(self, request: AutoSubscriptionRequestSchema, main_db: Session):
        self.request: AutoSubscriptionRequestSchema = request
        self.main_db: Session = main_db

    def handle(self):
        from tasks.sync import fiware_type_subscription_job

        # the auto sync preference for all organizations
        to_auto_sync = self.request.organizations

        if not to_auto_sync:

            prefs = crud_preferences.get_organizations_preference(
                PreferenceType.SUBSCRIPTION_AUTO_SYNC, self.main_db
            )

            to_auto_sync = [key for key, value in prefs.items() if value == "true"]

        # get the scopes for the organizations
        scopes = crud_organizations.get_organizations_scopes(to_auto_sync, self.main_db)

        logging.info(
            f"Auto sync for scopes scopes: {scopes}, triggered by organizations: {to_auto_sync}"
        )

        for tenant_name, scope_name in scopes:
            fiware_type_subscription_job.delay(
                TypeSubscriptionMessage(
                    subscribe_types=[],
                    unsubscribe_types=[],
                    tenant=tenant_name,
                    scope=scope_name,
                    auto_discovery=True,
                    sync_existing=True,
                    create_new_subscriptions=self.request.create_new_subscriptions,
                    filter_types=self.request.types,
                    user_id=self.request.user_id,
                )
            )
