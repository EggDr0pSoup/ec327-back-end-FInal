import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()
# In production, you would want to set this to False in .env
RELOAD = os.getenv("RELOAD", "0").lower() in ("true", "1")

if __name__ == "__main__":
    uvicorn.run("app.app:app", host="0.0.0.0", log_level="info", reload=RELOAD)
