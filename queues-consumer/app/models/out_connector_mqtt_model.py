from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from db.session import Base
from sqlalchemy.dialects.postgresql import JSONB

# Payload types built from a periodic snapshot of the linked models instead of from each
# ingestion notification: one message holds every reading.
READINGS_PAYLOAD_TYPES = ("occupancy_readings", "flow_readings")
INVENTORY_PAYLOAD_TYPES = ("device_inventory",)
SNAPSHOT_PAYLOAD_TYPES = READINGS_PAYLOAD_TYPES + INVENTORY_PAYLOAD_TYPES


class MqttConnector(Base):
    __tablename__ = "mqtt_connector"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ipAddress = Column(String)
    port = Column(Integer)
    username = Column(String)
    password = Column(String)
    clientId = Column(String)
    sslCert = Column(Text)
    ssl = Column(Boolean)
    topicTemplate = Column(JSONB)
    payload_config = Column(JSONB)
    payload_type = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    class Config:
        orm_mode = True