from fastapi import APIRouter
from fastapi.security import HTTPBearer


strategy_router = APIRouter(prefix="/areas/strategy", tags=["areas-strategy"])
strategy_scheme = HTTPBearer()