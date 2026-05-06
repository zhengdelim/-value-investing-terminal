from fastapi import APIRouter
from ..schemas.stock import InsidersResponse
from ..services import yf_service as yf

router = APIRouter()


@router.get("/{ticker}/insiders", response_model=InsidersResponse)
async def get_insiders(ticker: str):
    return await yf.get_insiders(ticker)
