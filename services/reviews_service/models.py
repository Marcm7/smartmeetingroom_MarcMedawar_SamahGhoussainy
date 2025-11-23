from sqlalchemy import Column, Integer, Index
from .database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, nullable=False)  # ❌ no ForeignKey
    room_id = Column(Integer, nullable=False)     # ❌ no ForeignKey
    rating = Column(Integer, nullable=False)
    comment = Column(Integer, nullable=True)  # or String if comment text

    __table_args__ = (
        Index("idx_reviews_booking_id", "booking_id"),
        Index("idx_reviews_room_id", "room_id"),
    )
