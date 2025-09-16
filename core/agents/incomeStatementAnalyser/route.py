from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from authx import TokenPayload
from core.settings import auth
from core.services.prisma import prisma
from prisma.models import User
from .service import upload_comparison_file_service, get_chart_accounts_service
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

income_statement_analyser_router = APIRouter(prefix="/income-statement-analyser", tags=["Income Statement Analyser Agent"])
auth_scheme = HTTPBearer()

@income_statement_analyser_router.post("/upload-comparison-file")
async def upload_comparison_file(
    year: int,
    file: UploadFile = File(...),
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)
):
    user_id = payload.sub
    
    return await upload_comparison_file_service(user_id=user_id, year=year, file=file)



@income_statement_analyser_router.get("/chart-accounts")
async def get_chart_accounts(
    take: int,
    number_page: int,
    include_cee: bool = False,
    token: HTTPAuthorizationCredentials = Depends(auth_scheme),
    payload: TokenPayload = Depends(auth.access_token_required)
):
    if number_page < 1:
        raise HTTPException(status_code=400, detail="Number Page must be greater than 0")
    if take < 0:
        raise HTTPException(status_code=400, detail="Take must be greater than or equal to 0")
    
    user_id = payload.sub

    return await get_chart_accounts_service(user_id, take, number_page, include_cee)