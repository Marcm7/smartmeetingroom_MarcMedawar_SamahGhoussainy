from sqlalchemy import Column, Integer, String, Index
from .database import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    capacity = Column(Integer)

    __table_args__ = (
        Index("idx_rooms_name", "name"),
        Index("idx_rooms_location", "location"),
    )
