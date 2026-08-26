from typing import Any, List, Optional, Tuple

from models.user_model import User
from models.organization_model import Organization, OrganizationHasResource
from models.fiware_scope_model import FiwareScope
from models.fiware_tenant_model import FiwareTenant
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_


def get_organization_by_id(organization_id: int, db: Session) -> Optional[Organization]:
    """
    Gets an organization by its ID. Returns None if not found.
    """
    return db.query(Organization).filter(Organization.id == organization_id).first()


def get_user_organization(user_id: int, db: Session) -> Organization:
    """
    Gets the user organization
    """

    return (
        db.query(Organization)
        .join(User, User.organization_id == Organization.id)
        .filter(User.id == user_id)
        .first()
    )


def assign_resource_to_organization(
    organization_id: int, resource: Any, db: Session
) -> OrganizationHasResource:
    """
    Assigns the given resource to the organization with the given id,
    """

    ohr = OrganizationHasResource(
        organization_id=organization_id,
        resource_type=resource.__tablename__,
        resource_id=resource.id,
    )

    db.add(ohr)

    return ohr


def get_organizations_scopes(
    organizations: List[int],
    db: Session,
) -> Tuple[str, str]:
    """
    Returns the organization tenant and scopes as list of (tenant, scope) tuples
    An organization has a scope if it has the tenant or the scope through organization_has_resource
    """

    tenant_scopes = (
        db.query(
            OrganizationHasResource.resource_type, OrganizationHasResource.resource_id
        )
        .filter(OrganizationHasResource.organization_id.in_(organizations))
        .filter(
            or_(
                OrganizationHasResource.resource_type == "fiware_tenants",
                OrganizationHasResource.resource_type == "fiware_scopes",
            )
        )
        .all()
    )

    scope_ids = []
    tenant_ids = []
    for resource_type, resource_id in tenant_scopes:
        if resource_type == "fiware_tenants":
            tenant_ids.append(resource_id)
        else:
            scope_ids.append(resource_id)

    # now get the tenant and scope names
    names = (
        db.query(FiwareScope.name, FiwareTenant.name)
        .join(FiwareTenant, FiwareTenant.id == FiwareScope.fiware_tenant_id)
        .filter(
            or_(
                FiwareScope.id.in_(scope_ids),
                FiwareTenant.id.in_(tenant_ids),
            )
        )
        .distinct(FiwareScope.name, FiwareTenant.name)
        .all()
    )

    return [(tenant_name, scope_name) for scope_name, tenant_name in names]
