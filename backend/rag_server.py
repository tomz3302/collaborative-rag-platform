import os
import logging
import contextlib
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Import Routers
from routers import chat, documents, spaces
# Import Auth
from users import auth_backend, fastapi_users
from schemas import UserRead, UserCreate, UserUpdate

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG_Server")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

# Lifespan event to create Auth Tables on startup and cleanup on shutdown
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create the Auth Tables (Users) if they don't exist
    from db import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Application started successfully")
    
    yield  # Server runs here
    
    # Shutdown: Close database connections gracefully
    logger.info("Shutting down gracefully...")
    await engine.dispose()
    logger.info("Database connections closed")

# --- FastAPI App ---
app = FastAPI(title="Clark", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. MOUNT AUTH ROUTERS ---
# Login/Logout
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
# Registration
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
# Email Verification
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
# Users (for /users/me endpoint)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# --- 2. MOUNT API ROUTERS ---
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(spaces.router, prefix="/api", tags=["spaces"])


# --- 3. SERVE FRONTEND ---
@app.get("/")
async def read_root():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Clark API Server Running"}

if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    print("Starting Clark...")
    uvicorn.run(app, host="0.0.0.0", port=8000)