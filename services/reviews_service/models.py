from sqlalchemy import Column, Integer, String, Float
from .database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)
    comment = Column(String, nullable=True)
