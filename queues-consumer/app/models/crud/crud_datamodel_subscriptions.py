from models.datamodel_subscription_model import DatamodelSubscription
from models.fiware_scope_model import FiwareScope
from models.fiware_tenant_model import FiwareTenant
from sqlalchemy.orm import Session
from config.config import images_storage
from sqlalchemy.sql import func


def get_subscription(datamodel: str, tenant: str, scope: str, db: Session) -> bool:
    """
    Check if a subscription already exists
    """
    return (
        db.query(DatamodelSubscription)
        .join(FiwareScope, FiwareScope.id == DatamodelSubscription.fiware_scope_id)
        .join(FiwareTenant, FiwareTenant.id == FiwareScope.fiware_tenant_id)
        .filter(
            DatamodelSubscription.datamodel == datamodel,
            FiwareTenant.name == tenant,
            FiwareScope.name == scope,
        )
        .first()
    )


def create_datamodel_subscription(payload: dict, db: Session) -> DatamodelSubscription:

    fiware_scope = (
        db.query(FiwareScope)
        .join(FiwareTenant, FiwareTenant.id == FiwareScope.fiware_tenant_id)
        .filter(FiwareTenant.name == payload.get("tenant"))
        .filter(FiwareScope.name == payload.get("scope"))
        .first()
    )

    if not fiware_scope:
        return None

    datamodel_subscription = DatamodelSubscription(
        datamodel=payload["datamodel"],
        fiware_scope_id=fiware_scope.id,
        created_at=func.now(),
        updated_at=func.now(),
    )
    db.add(datamodel_subscription)
    db.commit()
    db.refresh(datamodel_subscription)
    return datamodel_subscription


def remove_datamodel_subscription(
    datamodel: str, tenant: str, scope: str, db: Session
) -> DatamodelSubscription:

    datamodel_subscription: DatamodelSubscription = (
        db.query(DatamodelSubscription)
        .join(FiwareScope, FiwareScope.id == DatamodelSubscription.fiware_scope_id)
        .join(FiwareTenant, FiwareTenant.id == FiwareScope.fiware_tenant_id)
        .filter(
            DatamodelSubscription.datamodel == datamodel,
            FiwareTenant.name == tenant,
            FiwareScope.name == scope,
        )
        .first()
    )

    if not datamodel_subscription:
        return None

    if datamodel_subscription.image:
        images_storage.delete_file(datamodel_subscription.image)

    db.delete(datamodel_subscription)
    db.commit()

    return datamodel_subscription
