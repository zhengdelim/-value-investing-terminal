from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.stock import InsiderRecord

router = APIRouter()


@router.get("/{ticker}/insiders", response_model=list[InsiderRecord])
async def get_insiders(ticker: str, db: Session = Depends(get_db)):
    # Insider trading endpoint requires a paid FMP plan.
    return []
