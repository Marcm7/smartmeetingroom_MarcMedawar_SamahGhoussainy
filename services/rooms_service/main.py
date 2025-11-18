from fastapi import FastAPI, status
from .schemas import RoomCreate, RoomResponse

app = FastAPI(title="Rooms Service")

rooms: list[RoomResponse] = []


@app.post(
    "/api/rooms",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,  
)
def create_room(room: RoomCreate) -> RoomResponse:
    new_id = len(rooms) + 1
    room_obj = RoomResponse(id=new_id, **room.model_dump())
    rooms.append(room_obj)
    return room_obj


@app.get(
    "/api/rooms",
    response_model=list[RoomResponse],
)
def list_rooms() -> list[RoomResponse]:
    return rooms
