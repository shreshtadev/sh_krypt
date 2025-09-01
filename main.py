import uvicorn
from app.config import IS_DEBUG

if __name__ == "__main__":
    uvicorn.run(
        "app.api:app",
        port=9090,
        reload_delay=3.0 if IS_DEBUG else 0.0,
        reload=IS_DEBUG,
        workers=1 if IS_DEBUG else 4,
        log_level="debug" if IS_DEBUG else "error",
    )
