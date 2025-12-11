from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
from pathlib import Path

from backend.src.api.routes import router
from backend.src.core.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for managing lifecycle events"""
    # Startup
    await redis_client.initialize()
    print("🚀 GitHub Issues Creator Pro started successfully")
    print("📁 Current directory:", os.getcwd())
    print("🔗 API available at: http://localhost:8000")
    print("📚 API documentation: http://localhost:8000/docs")
    print("🔍 Debug mode: ON")
    yield
    # Shutdown
    await redis_client.close()
    print("👋 Application shutdown")


app = FastAPI(
    title="GitHub Issues Creator Pro",
    description="Advanced GitHub issue management with templates and repository management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get absolute path to frontend
current_dir = Path(__file__).parent
frontend_dir = current_dir.parent.parent / "frontend"
print(f"📂 Frontend directory: {frontend_dir}")

# Check if frontend directory exists
if frontend_dir.exists():
    print("✅ Frontend directory found")
    # Mount frontend
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
else:
    print("⚠️  Frontend directory not found, serving API only")

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend application"""
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    else:
        return {
            "message": "GitHub Issues Creator Pro API",
            "status": "running",
            "version": "2.0.0",
            "docs": "/docs",
            "api_endpoints": [
                "/api/test",
                "/api/templates",
                "/api/verify",
                "/api/verify-token",
                "/api/issues/create",
                "/api/create-issue"
            ]
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        redis_status = await redis_client.ping()
        status = "healthy" if redis_status else "degraded"
    except Exception as e:
        print(f"Health check error: {e}")
        redis_status = False
        status = "unhealthy"

    return {
        "status": status,
        "version": "2.0.0",
        "services": {
            "redis": "connected" if redis_status else "disconnected",
            "api": "running"
        },
        "endpoints": {
            "templates": "/api/templates",
            "verify": "/api/verify",
            "create_issue": ["/api/issues/create", "/api/create-issue"],
            "docs": "/docs"
        }
    }


@app.get("/favicon.ico")
async def favicon():
    """Favicon endpoint to prevent 404 errors"""
    return {"message": "No favicon"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("ENVIRONMENT", "development") == "development"

    print(f"🌐 Starting server on {host}:{port}")
    print(f"🔄 Auto-reload: {reload}")
    print(f"🐍 Python version: {os.sys.version}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload
    )
