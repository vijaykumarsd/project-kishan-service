from fastapi import APIRouter
from app.agents.agronomist import handle_query

router = APIRouter()

@router.post("/agronomist")
def route_func(query: str):
    return { "response": handle_query(query) }
