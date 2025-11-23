from sqlalchemy import Column, Integer, DateTime, Index
from .database import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, nullable=False)   # ❌ no ForeignKey
    user_id = Column(Integer, nullable=False)   # ❌ no ForeignKey
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_bookings_room_id", "room_id"),
        Index("idx_bookings_user_id", "user_id"),
        Index("idx_bookings_start_time", "start_time"),
        Index("idx_bookings_room_date", "room_id", "start_time"),
    )
