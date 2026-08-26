from typing import Any, Dict, List
from models.organization_model import Organization
from models.preferences_model import (
    Preference,
    Preferencable,
    OrganizationPreference,
    PreferenceType,
)
from models.user_model import User
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from config.logging import appLogging as logging


def get_user_preference(
    user_id: int, preference_name: PreferenceType, db: Session
) -> str:
    """
    Returns the value of the user preference with the given name,
    or the organization preference if the user preference is not set,
    or the default preference if the organization preference is not set.
    """
    pref_model = db.query(Preference).filter(Preference.name == preference_name).first()

    if not pref_model:
        return None

    user_pref_model = (
        db.query(Preferencable)
        .filter(Preferencable.user_id == user_id)
        .filter(Preferencable.preference_id == pref_model.id)
        .first()
    )

    if user_pref_model:
        return user_pref_model.value

    # then get the organization preference
    user = db.query(User).filter(User.id == user_id).first()
    organization_pref_model = (
        db.query(OrganizationPreference)
        .filter(OrganizationPreference.organization_id == user.organization_id)
        .filter(OrganizationPreference.preference_id == pref_model.id)
        .first()
    )

    if organization_pref_model:
        return organization_pref_model.value

    return pref_model.default_value


def get_organization_preference(
    organization_id: int, preference_name: PreferenceType, db: Session
) -> str:
    pref_model = db.query(Preference).filter(Preference.name == preference_name).first()

    if not pref_model:
        return None

    organization_pref_model = (
        db.query(OrganizationPreference)
        .filter(OrganizationPreference.organization_id == organization_id)
        .filter(OrganizationPreference.preference_id == pref_model.id)
        .first()
    )

    if organization_pref_model:
        return organization_pref_model.value

    return pref_model.default_value


def get_organizations_preference(
    preference_name: PreferenceType, db: Session
) -> Dict[int, str]:
    """
    Returns the value of the preference with the given name for all organizations,
    and returns a dictionary with organization_id: preference_value.
    """
    pref_model = db.query(Preference).filter(Preference.name == preference_name).first()

    # fancy optimized query to get all organizations and the selected preference
    org_prefs = (
        db.query(Organization.id, OrganizationPreference.value)
        .join(
            OrganizationPreference,
            and_(
                Organization.id == OrganizationPreference.organization_id,
                OrganizationPreference.preference_id == pref_model.id,
            ),
            isouter=True,
        )
        .filter(
            or_(
                OrganizationPreference.preference_id == None,
                OrganizationPreference.preference_id == pref_model.id,
            )
        )
        .all()
    )

    return {
        organization_id: pref_value if pref_value else pref_model.default_value
        for organization_id, pref_value in org_prefs
    }


def get_user_preferences(user_id: int, db: Session) -> Dict[str, Any]:
    """
    Returns the user preferences as preference_name: preference_value dictionary.
    The preferences are user default preferences + organization preferences + user preferences,
    the latest overwriting the previous ones.
    """

    user = db.query(User).filter(User.id == user_id).first()

    organization_prefs = get_organization_preferences(user.organization_id, db)

    user_pref_models = db.query(Preferencable).filter(Preferencable.user_id == user_id)

    user_prefs = {pref.preference.name: pref.value for pref in user_pref_models}

    return {**organization_prefs, **user_prefs}


def get_organization_preferences(organization_id: int, db: Session) -> Dict[str, Any]:
    """
    Returns the organization preferences as preference_name: preference_value dictionary.
    The preferences are organization default preferences + organization preferences,
    the latest overwriting the previous ones.
    """

    default_prefs = get_default_preferences(db)

    organization_pref_models = db.query(OrganizationPreference).filter(
        OrganizationPreference.organization_id == organization_id
    )

    organization_prefs = {pref.name: pref.value for pref in organization_pref_models}

    return {**default_prefs, **organization_prefs}


def get_default_preferences(db: Session) -> Dict[str, Any]:
    """
    Returns the default preferences as preference_name: preference_value dictionary.
    """

    preferences = db.query(Preference).all()

    return {preference.name: preference.default_value for preference in preferences}
