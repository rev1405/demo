# [DB CONNECTION] collections: wallets, wallet_transactions
from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.dependencies import get_current_user, rate_limit
from app.schemas import TopUpIn
from app.services import wallet_service
from app.utils import clean

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


@router.get("")
def my_wallet(u: dict = Depends(get_current_user)):
    db = get_db()
    w = wallet_service.get_wallet(db, u["_id"])
    txs = list(db.wallet_transactions.find({"user_id": u["_id"]})
               .sort("created_at", -1).limit(30))
    return clean({"balance": w["balance"], "currency": w["currency"],
                  "transactions": txs})


@router.post("/topup")
def topup(data: TopUpIn, u: dict = Depends(get_current_user),
          _rl: None = Depends(rate_limit(limit=6))):
    # [SSDLC] Simulated gateway. Production: PSP redirect/checkout,
    # never card data here.
    w = wallet_service.top_up(get_db(), u["_id"], data.amount, actor_id=u["_id"])
    return clean({"balance": w["balance"]})