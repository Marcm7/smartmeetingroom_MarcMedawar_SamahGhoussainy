import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load secrets from .env.secrets (acts like a simple secrets manager)
load_dotenv(".env.secrets")

# 1) read DB url
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./smartmeetingroom.db"  # safe, non-secret fallback
)




print("DB URL =", DATABASE_URL)

engine = create_engine(DATABASE_URL)

# 2) import Bases AND models so metadata is populated
from services.rooms_service.database import Base as RoomsBase
from services.rooms_service import models as rooms_models

from services.users_service.database import Base as UsersBase
from services.users_service import models as users_models

from services.bookings_service.database import Base as BookingsBase
from services.bookings_service import models as bookings_models

from services.reviews_service.database import Base as ReviewsBase
from services.reviews_service import models as reviews_models


# 3) create tables for each service base
RoomsBase.metadata.create_all(bind=engine)
UsersBase.metadata.create_all(bind=engine)
BookingsBase.metadata.create_all(bind=engine)
ReviewsBase.metadata.create_all(bind=engine)

print("✅ DB tables created successfully")
