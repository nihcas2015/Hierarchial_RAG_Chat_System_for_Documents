from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import routers
from auth import router as auth_router
from documents import router as documents_router
from messages import router as messages_router
from database import Base, engine

load_dotenv()

# Create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    yield
    # Shutdown
    print("Shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chat System API",
    description="Backend API for Hierarchical RAG Chat System",
    version="1.0.0",
    lifespan=lifespan
)

# ===== CORS Configuration =====
# Allow frontend to communicate with backend
ALLOWED_ORIGINS = [
    "http://localhost:3000",      # React dev server
    "http://localhost:8000",      # HTTP server
    "http://localhost:5000",      # FastAPI
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Trusted Host middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

# ===== Include Routers =====
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(messages_router)

# ===== Root Endpoint =====
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "RAG Chat System API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

# ===== Health Check =====
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RAG Chat API"
    }

# ===== Run Application =====
if __name__ == "__main__":
    import uvicorn
    
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", 5000))
    DEBUG = os.getenv("DEBUG", "True") == "True"
    
    print(f"Starting RAG Chat API on {HOST}:{PORT}")
    print(f"API Documentation: http://localhost:{PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )
