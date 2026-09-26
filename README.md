# MallHaul - Shop every store. One cart, one delivery.

Full-stack Layer 1 mall marketplace: multi-store unified cart, one wallet
payment split per store internally, store fulfillment, mall hub consolidation,
QR-verified handover, courier assignment via quantum-inspired optimization.

Stack: FastAPI (Python) + MongoDB + vanilla HTML/CSS/JS frontend.

## Run
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    copy .env.example .env        (set MONGODB_URI - Atlas or local replica set)
    python -m database.migrations.runner
    python -m database.seed_demo
    uvicorn app.main:app --reload

Open http://localhost:8000  (frontend) and http://localhost:8000/docs (API).

## Demo login
    demo@mallhaul.co.za / Demo1234!   (wallet pre-loaded R1500)

## Where the backend connects to the database
    app/core/database.py  <- the ONLY driver-level connection point.
    Every service imports get_db() from there; each service file starts with
    a [DB CONNECTION] banner listing the collections it touches.

## Security
    docs/SSDLC.md  - Secure System Development Lifecycle, controls mapped to code.
    frontend/security.html - in-app summary page.