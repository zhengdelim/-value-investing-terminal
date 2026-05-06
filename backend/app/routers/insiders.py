import asyncio
from fastapi import APIRouter
from ..schemas.stock import InsidersResponse
from ..services import sec_edgar

router = APIRouter()


@router.get("/{ticker}/insiders", response_model=InsidersResponse)
async def get_insiders(ticker: str):
    transactions, gurus = await asyncio.gather(
        sec_edgar.get_insider_transactions(ticker),
        sec_edgar.get_guru_holdings(ticker),
    )
    return {"transactions": transactions, "gurus": gurus}
