"""FastAPI application entry point."""
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from autoquery.api.routes.auth import router as auth_router
from autoquery.api.routes.events import router as events_router
from autoquery.api.routes.matching import router as matching_router
from autoquery.api.routes.optout import router as optout_router
from autoquery.api.routes.upload import router as upload_router

app = FastAPI(title="AutoQuery API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(matching_router)
app.include_router(upload_router)
app.include_router(events_router)
app.include_router(optout_router)


@app.middleware("http")
async def session_cookie_middleware(request: Request, call_next):
    """Set a UUID session cookie if not present, and store on request state."""
    if "session_id" not in request.cookies:
        new_id = str(uuid.uuid4())
        request.state.generated_session_id = new_id
    else:
        request.state.generated_session_id = None

    response: Response = await call_next(request)

    if request.state.generated_session_id:
        response.set_cookie(
            key="session_id",
            value=request.state.generated_session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 365,  # 1 year
        )
    return response


@app.get("/health")
async def health(detailed: bool = False):
    if not detailed:
        return {"status": "ok"}

    from sqlalchemy.orm import Session

    from autoquery.database.db import SessionLocal
    from autoquery.monitoring.health import check_system_health

    db: Session = SessionLocal()
    try:
        return check_system_health(db)
    finally:
        db.close()
