from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.database import close_client, get_client
from app.routers import (auth, cart, catalog, checkout, demo, ops, orders,
                         qr, wallet)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_client().admin.command("ping")   # fail fast if MongoDB unreachable
    yield
    close_client()


app = FastAPI(title="MallHaul API", version="1.0.0", lifespan=lifespan)

for r in (auth, catalog, cart, checkout, orders, wallet, ops, qr, demo):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Frontend (strictly HTML/CSS/vanilla JS) served same-origin so the session
# cookie flows automatically. [SSDLC: no CORS surface in production]
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")