from pydantic import BaseModel, ConfigDict

class RoomBase(BaseModel):
    name: str
    location: str
    capacity: int

class RoomCreate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
