import uvicorn
from bot.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "admin.main:app",
        host="0.0.0.0",
        port=settings.admin_port,
        reload=False,
    )
