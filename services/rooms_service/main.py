from fastapi import FastAPI, Depends, status
from sqlalchemy.orm import Session

from .schemas import RoomCreate, RoomResponse
from . import models
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rooms Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rooms"}



@app.post(
    "/api/rooms",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_room(room: RoomCreate, db: Session = Depends(get_db)) -> RoomResponse:
    db_room = models.Room(**room.model_dump())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return RoomResponse.model_validate(db_room)


@app.get(
    "/api/rooms",
    response_model=list[RoomResponse],
)
def list_rooms(db: Session = Depends(get_db)) -> list[RoomResponse]:
    rooms = db.query(models.Room).all()
    return [RoomResponse.model_validate(r) for r in rooms]
