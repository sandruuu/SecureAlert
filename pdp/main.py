import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import database
from routers import auth, admin, user, vpn, agent

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("auth_service")

app = FastAPI(title="Zero Trust Auth Service")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    logger.info("Application starting up...")
    database.init_db()
    logger.info("Application startup complete.")

# Include Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(user.router)
app.include_router(vpn.router)
app.include_router(agent.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
