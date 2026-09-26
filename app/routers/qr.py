# [DB CONNECTION] collection: qr_codes
import io
from datetime import datetime, timezone

import qrcode
import qrcode.image.svg
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import get_db
from app.dependencies import require_ops

router = APIRouter(prefix="/api/qr", tags=["qr"])
now = lambda: datetime.now(timezone.utc)


def _svg(payload: str) -> bytes:
    buf = io.BytesIO()
    img = qrcode.make(payload, image_factory=qrcode.image.svg.SvgPathImage,
                      box_size=12, border=2)
    img.save(buf)
    return buf.getvalue()


@router.get("/{code}/svg")
def qr_svg(code: str):
    qr = get_db().qr_codes.find_one({"code": code})
    if not qr:
        raise HTTPException(404, "Unknown QR code")
    if qr.get("expires_at") and qr["expires_at"] < now():
        raise HTTPException(410, "QR code expired")
    return Response(content=_svg(qr["code"]), media_type="image/svg+xml")


@router.post("/{code}/scan")
def scan(code: str, ops: dict = Depends(require_ops)):
    db = get_db()
    qr = db.qr_codes.find_one({"code": code})
    if not qr:
        raise HTTPException(404, "Unknown QR code")
    if qr["status"] != "ACTIVE":
        raise HTTPException(409, f"QR already {qr['status']}")
    db.qr_codes.update_one({"_id": qr["_id"]},
                           {"$set": {"status": "SCANNED", "scanned_at": now()}})
    return {"code": code, "entity_type": qr["entity_type"],
            "entity_id": str(qr["entity_id"])}