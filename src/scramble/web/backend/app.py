from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .handlers import ConnectionManager

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)
