from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func
from db.session import Base


class Virtualizations(Base):

    __tablename__ = "virtualizations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    mapping_schema_id = Column(Integer, nullable=False)

    destination_entity_id = Column(Integer, nullable=False)

    virtualization_id = Column(Integer, nullable=False)
    virtualization_type = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    class Config:
        orm_mode = True

    def __repr__(self):
        return (
            f"<Virtualization id={self.id} "
            f"mapping_schema_id={self.mapping_schema_id} "
            f"virtualization_type={self.virtualization_type!r} "
            f"virtualization_id={self.virtualization_id}>"
        )
