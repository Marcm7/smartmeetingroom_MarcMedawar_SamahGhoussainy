from fastapi import FastAPI
from . import models
from .database import engine
from .routes import router as users_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Users Service")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "users"}


app.include_router(users_router)
