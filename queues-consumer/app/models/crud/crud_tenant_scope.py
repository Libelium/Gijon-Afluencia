from typing import List, Tuple
from models.fiware_tenant_model import FiwareTenant
from models.fiware_scope_model import FiwareScope

from sqlalchemy.orm import Session


def create_tenant(tenant_name: str, db: Session) -> FiwareTenant:
    tenant = FiwareTenant(name=tenant_name)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    return tenant


def create_scope(scope_name: str, tenant_name: str, db: Session) -> FiwareScope:

    tenant = db.query(FiwareTenant).filter(FiwareTenant.name == tenant_name).first()
    if not tenant:
        tenant = create_tenant(tenant_name, db)

    scope = FiwareScope(name=scope_name, fiware_tenant_id=tenant.id)
    db.add(scope)
    db.commit()
    db.refresh(scope)

    return scope


def get_tenant_scope(scope_id: int, db: Session) -> Tuple[str, str]:

    scope_model = db.query(FiwareScope).filter(FiwareScope.id == scope_id).first()

    if not scope_model:
        return (None, None)

    tenant_model = (
        db.query(FiwareTenant)
        .filter(FiwareTenant.id == scope_model.fiware_tenant_id)
        .first()
    )

    return (tenant_model.name, scope_model.name)
