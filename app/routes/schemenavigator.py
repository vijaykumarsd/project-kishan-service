from fastapi import APIRouter
from app.agents.scheme_navigator import handle_query

router = APIRouter()

@router.post("/schemenavigator")
def route_func(query: str):
    return { "response": handle_query(query) }
