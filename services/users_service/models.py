#services/users_service/models.py
from sqlalchemy import Column, Integer, String
from .database import Base
from sqlalchemy import Index

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="regular")  # roles: "regular", "admin", "facility_manager"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    building = Column(String)

    __table_args__ = (
        Index("idx_rooms_name", "name"),
        Index("idx_rooms_building", "building"),
    )