"""
Modelos SQLAlchemy de las tablas de alarmas y de sus acciones.

Viven junto al motor porque es su unico consumidor: el resto de la aplicacion no
lee estas tablas. El esquema es el que crean las migraciones del backend
(alarms, alarm_conditions, inactivity_alarm_conditions, actions,
alarm_has_actions y las tablas action_*).
"""

from enum import Enum

from db.session import Base
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func


class AlarmType(str, Enum):
    BASIC = "basic"
    INACTIVITY = "inactivity"


class AlarmTrigger(str, Enum):
    """Valor de alarm_has_actions.type: a que transicion responde la accion."""

    UP = "up"
    DOWN = "down"


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    name = Column(String)
    type = Column(String)
    function = Column(String)
    up = Column(Boolean)
    disabled = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AlarmCondition(Base):
    __tablename__ = "alarm_conditions"

    id = Column(Integer, primary_key=True, index=True)
    alarm_id = Column(Integer)
    entity_id = Column(Integer)
    measure = Column(String)
    condition = Column(String)
    # El backend guarda los umbrales unidos por '#' (AlarmCondition::setThresholdAttribute).
    threshold = Column(String)
    period = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class InactivityAlarmCondition(Base):
    __tablename__ = "inactivity_alarm_conditions"

    id = Column(Integer, primary_key=True, index=True)
    alarm_id = Column(Integer)
    entity_id = Column(Integer)
    # Nulo significa "cualquier medida de la entidad".
    measure = Column(String)
    timeout_s = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    user_id = Column(Integer)
    # Relacion polimorfica de Laravel: 'action_telegram', 'action_sms', ...
    actionable_type = Column(String)
    actionable_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AlarmHasAction(Base):
    __tablename__ = "alarm_has_actions"

    alarm_id = Column(Integer, primary_key=True)
    action_id = Column(Integer, primary_key=True)
    type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ActionTelegram(Base):
    __tablename__ = "action_telegram"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ActionSms(Base):
    __tablename__ = "action_sms"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ActionWhatsapp(Base):
    __tablename__ = "action_whatsapp"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String)
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ActionEmail(Base):
    __tablename__ = "action_email"

    id = Column(Integer, primary_key=True, index=True)
    # El backend guarda los destinatarios unidos por '#' (ActionEmail::setDestinationAttribute).
    destination = Column(String)
    subject = Column(String)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ActionHttpPush(Base):
    __tablename__ = "action_http_push"

    id = Column(Integer, primary_key=True, index=True)
    url_template = Column(JSONB)
    method = Column(String)
    authorization = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ActionEntityCommand(Base):
    __tablename__ = "action_entity_command"

    id = Column(Integer, primary_key=True, index=True)
    # { "<entity_id>": { "<comando>": "<valor>", ... }, ... }
    commands = Column(JSONB)
    meta = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
