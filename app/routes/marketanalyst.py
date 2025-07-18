from fastapi import APIRouter
from app.agents.market_analyst import handle_query

router = APIRouter()

@router.post("/marketanalyst")
def route_func(query: str):
    return { "response": handle_query(query) }
